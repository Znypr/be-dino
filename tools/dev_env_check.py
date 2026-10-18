#!/usr/bin/env python3
"""Morning health check for the lead's tools (docs/165, BD-645). READ-ONLY.

  python tools/dev_env_check.py                 # table on screen
  python tools/dev_env_check.py --json out.json # also write the same results as JSON
  python tools/dev_env_check.py --launch blender|chrome|edge [--dry-run]

The check part only looks. It never changes a setting, never kills a process, never moves, focuses,
minimises or restores a window, never takes an OS screenshot, and sends nothing to Blender except
the harmless {"type": "ping"} (the add-on answers "pong" and touches no scene data). Nothing is sent
to Studio at all: only a TCP connect to the Studio MCP port.

--launch may START Blender (with tools/blender/enable_mcp_addon.py), Chrome or Edge. It never stops
anything, and it refuses when that program is already running. There is NO option for Roblox Studio
on purpose (docs/160 section 6: Studio windows belong to the owner and to agent window rules).

Exit code: 1 if any line is FAIL, else 0. Every probe degrades to SKIP/WARN on a machine without the
tool (and on non-Windows), so the script never crashes.
"""
import argparse
import ctypes
import datetime
import glob
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENABLE_SCRIPT = ROOT / "tools" / "blender" / "enable_mcp_addon.py"
LUAU = "C:/Users/znypr/AppData/Local/Temp/bd057/luau/luau.exe"
FFMPEG_DIR = "C:/ffmpeg/bin"
CLAUDE_EXTENSION_ID = "fcoeoabgfenejglbffodgkkbkcdhcgfn"
BLENDER_PORT = 9876  # blender_mcp.py: BlenderMCPServer(host='localhost', port=9876), scene property blendermcp_port
# docs/158 section 3: the plugged-in values it tells the owner to set. 0 = never.
RECOMMENDED = [("monitor-timeout-ac", "SUB_VIDEO", "VIDEOIDLE"), ("standby-timeout-ac", "SUB_SLEEP", "STANDBYIDLE"),
               ("hibernate-timeout-ac", "SUB_SLEEP", "HIBERNATEIDLE"), ("disk-timeout-ac", "SUB_DISK", "DISKIDLE")]
PASS, FAIL, WARN, INFO, SKIP = "PASS", "FAIL", "WARN", "INFO", "SKIP"


def result(area, name, status, detail=""):
    return {"area": area, "name": name, "status": status, "detail": str(detail)}


def tidy(text):
    """Short, ASCII, and without the user's home folder name."""
    text = str(text).replace("\\", "/")
    home = os.path.expanduser("~").replace("\\", "/")
    if home and home != "~":
        text = text.replace(home, "~")
    return text.encode("ascii", "replace").decode("ascii")


def procs_text(n):
    return "%d process%s" % (n, "" if n == 1 else "es")


def minutes(seconds):
    seconds = int(seconds)
    return "%d min %d s" % (seconds // 60, seconds % 60) if seconds >= 60 else "%d s" % seconds


# ----------------------------------------------------------------------------------------------
# Probes: everything that touches the machine. Tests replace this class.
# ----------------------------------------------------------------------------------------------
class Probes:
    """Real probes. Each returns None when it cannot answer (wrong OS, tool missing, no rights)."""

    def __init__(self):
        self.windows_os = os.name == "nt"
        self.localappdata = os.environ.get("LOCALAPPDATA", "")
        self.appdata = os.environ.get("APPDATA", "")
        self.program_files = [p for p in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")) if p]

    def run(self, cmd, timeout=15):
        try:
            p = subprocess.run(cmd, capture_output=True, timeout=timeout, cwd=str(ROOT))
        except (OSError, subprocess.TimeoutExpired):
            return None
        return p.returncode, p.stdout.decode("utf-8", "replace") + p.stderr.decode("utf-8", "replace")

    def which(self, name):
        return shutil.which(name)

    def processes(self):
        """[(image name lower-case, pid)] or None."""
        if not self.windows_os:
            return None
        r = self.run(["tasklist", "/fo", "csv", "/nh"])
        if not r or r[0]:
            return None
        out = []
        for line in r[1].splitlines():
            m = re.match(r'"([^"]+)","(\d+)"', line)
            if m:
                out.append((m.group(1).lower(), int(m.group(2))))
        return out

    def listening(self):
        """[(port, pid)] of TCP listeners, or None."""
        r = self.run(["netstat", "-ano", "-p", "tcp"])
        if not r or r[0]:
            return None
        out = []
        for line in r[1].splitlines():
            m = re.match(r"\s*TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)", line)
            if m:
                out.append((int(m.group(1)), int(m.group(2))))
        return out

    def tcp_connect(self, port, timeout=1.0):
        """Open and close a connection to localhost:port. Sends nothing."""
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=timeout):
                return True
        except OSError:
            return False

    def blender_ping(self, port, timeout=3.0):
        """Send the add-on's harmless ping. Returns (True, '') or (False, reason)."""
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
        except OSError as e:  # refused, or timed out while connecting
            return False, "cannot connect (%s)" % e.__class__.__name__
        try:
            with s:
                s.settimeout(timeout)
                s.sendall(json.dumps({"type": "ping"}).encode("utf-8"))
                data = s.recv(4096)
        except socket.timeout:
            return False, "no answer in %g s (Blender busy?)" % timeout
        except OSError as e:
            return False, "connection dropped (%s)" % e.__class__.__name__
        try:
            ok = json.loads(data.decode("utf-8")).get("result", {}).get("pong") is True
        except ValueError:
            ok = False
        return (True, "") if ok else (False, "answered, but not with pong")

    def windows(self, pids):
        """Visible top-level windows of the given pids: [{'title', 'minimised'}], or None."""
        if not self.windows_os or not pids:
            return None if not self.windows_os else []
        try:
            from ctypes import wintypes
            u = ctypes.windll.user32
            u.IsWindowVisible.argtypes = u.IsIconic.argtypes = u.GetWindowTextLengthW.argtypes = [wintypes.HWND]
            u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
            u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
            proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            found = []

            def each(hwnd, _):
                pid = wintypes.DWORD()
                u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value in pids and u.IsWindowVisible(hwnd):
                    n = u.GetWindowTextLengthW(hwnd)
                    if n > 0:
                        buf = ctypes.create_unicode_buffer(n + 1)
                        u.GetWindowTextW(hwnd, buf, n + 1)
                        found.append({"title": buf.value, "minimised": bool(u.IsIconic(hwnd))})
                return True

            u.EnumWindows(proc(each), 0)
            return found
        except (OSError, AttributeError):
            return None

    def idle_seconds(self):
        if not self.windows_os:
            return None
        try:
            class LastInput(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
            info = LastInput()
            info.cbSize = ctypes.sizeof(LastInput)
            if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
                return None
            return ((ctypes.windll.kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000.0
        except (OSError, AttributeError):
            return None

    def power_scheme(self):
        r = self.run(["powercfg", "/getactivescheme"]) if self.windows_os else None
        if not r or r[0]:
            return None
        m = re.search(r"\((.+)\)\s*$", r[1].strip())
        return m.group(1) if m else r[1].strip()

    def power_ac_seconds(self, subgroup, setting):
        r = self.run(["powercfg", "/query", "SCHEME_CURRENT", subgroup, setting]) if self.windows_os else None
        if not r or r[0]:
            return None
        m = re.search(r"Current AC Power Setting Index:\s*0x([0-9a-fA-F]+)", r[1])
        return int(m.group(1), 16) if m else None

    def disk_free_gb(self, path):
        try:
            return shutil.disk_usage(str(path)).free / 1e9
        except OSError:
            return None

    def spawn(self, cmd):
        """Start a program and leave it running (detached). Never waits, never kills."""
        flags = 0x00000008 | 0x00000200 if self.windows_os else 0  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(cmd, creationflags=flags, close_fds=True, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def idle_since(self, path):
        try:
            return time.time() - os.path.getmtime(path)
        except OSError:
            return None


# ----------------------------------------------------------------------------------------------
# Checks. Each takes the probes and returns a list of result lines.
# ----------------------------------------------------------------------------------------------
def count(procs, name):
    return [pid for n, pid in procs if n == name]


def find_blender(p):
    hits = []
    for base in p.program_files:
        hits += glob.glob(os.path.join(base, "Blender Foundation", "Blender *", "blender.exe"))
    hits.sort(key=lambda s: [int(x) for x in re.findall(r"\d+", os.path.basename(os.path.dirname(s)))])
    return hits[-1] if hits else p.which("blender")


def check_blender(p, procs, listen, port=BLENDER_PORT):
    A = "Blender"
    out = []
    exe = find_blender(p)
    out.append(result(A, "installed", PASS if exe else FAIL, tidy(exe) if exe else "blender.exe not found"))
    pids = count(procs, "blender.exe") if procs is not None else None
    if pids is None:
        out.append(result(A, "running", SKIP, "cannot list processes on this machine"))
    else:
        out.append(result(A, "running", PASS if pids else FAIL, procs_text(len(pids)) if pids else "not running"))
    addon = glob.glob(os.path.join(p.appdata, "Blender Foundation", "Blender", "*", "scripts", "addons", "blender_mcp.py")) if p.appdata else []
    out.append(result(A, "MCP add-on file", PASS if addon else WARN, "blender_mcp.py is installed" if addon else "blender_mcp.py not found in the user add-ons folder"))
    if not pids:
        out.append(result(A, "MCP port %d" % port, SKIP, "Blender is not running"))
        return out
    owners = [pid for prt, pid in (listen or []) if prt == port]
    if listen is not None and not owners:
        out.append(result(A, "MCP port %d" % port, FAIL, "nobody is listening (add-on off? press Connect in the MCP panel)"))
        return out
    if owners and pids and not set(owners) & set(pids):
        out.append(result(A, "MCP port %d" % port, WARN, "port is held by another program, not Blender"))
        return out
    ok, why = p.blender_ping(port)
    out.append(result(A, "MCP port %d" % port, PASS if ok else FAIL, "add-on answered ping (pong)" if ok else why))
    return out


def check_studio(p, procs, listen, idle, monitor_timeout):
    A = "Studio"
    out = []
    if procs is None:
        return [result(A, "running", SKIP, "cannot list processes on this machine")]
    pids = count(procs, "robloxstudiobeta.exe")
    out.append(result(A, "running", PASS if pids else FAIL, procs_text(len(pids)) if pids else "RobloxStudioBeta is not running"))
    wins = p.windows(set(pids)) if pids else []
    if pids and wins is None:
        out.append(result(A, "windows", SKIP, "cannot read windows on this machine"))
    for w in wins or []:
        if "roblox studio" not in w["title"].lower():
            continue
        out.append(result(A, "window", FAIL if w["minimised"] else PASS,
                          "%s%s" % (tidy(w["title"]), "  MINIMISED (Studio draws 0 frames)" if w["minimised"] else "  open")))
    if pids and wins is not None and not any("roblox studio" in w["title"].lower() for w in wins):
        out.append(result(A, "windows", WARN, "Studio is running but no Studio window was found (still starting?)"))
    mcp = count(procs, "studiomcp.exe")
    ports = sorted({prt for prt, pid in (listen or []) if pid in mcp})
    if not mcp:
        out.append(result(A, "MCP plugin", WARN, "StudioMCP.exe is not running"))
    elif not ports:
        out.append(result(A, "MCP plugin", WARN, "%d StudioMCP processes, no listening port found" % len(mcp)))
    else:
        up = [prt for prt in ports if p.tcp_connect(prt)]
        out.append(result(A, "MCP plugin", PASS if up else WARN,
                          ("%d StudioMCP processes, port %s accepts a connection (connect only)" % (len(mcp), up[0])) if up
                          else "StudioMCP is running but port %s did not accept a connection" % ports[0]))
    if idle is None:
        out.append(result(A, "keyboard/mouse idle", SKIP, "cannot read"))
    else:
        out.append(result(A, "keyboard/mouse idle", INFO, minutes(idle)))
    locked = count(procs, "logonui.exe")
    out.append(result(A, "PC locked", FAIL if locked else PASS, "the lock screen is showing (0 frames)" if locked else "not locked"))
    if monitor_timeout is None:
        out.append(result(A, "displays asleep", SKIP, "power setting not readable"))
    elif monitor_timeout == 0:
        out.append(result(A, "displays asleep", PASS, "Windows never turns the displays off (setting is 0)"))
    elif idle is not None and idle > monitor_timeout:
        out.append(result(A, "displays asleep", WARN, "probably asleep: idle %s is longer than the %s display timeout" % (minutes(idle), minutes(monitor_timeout))))
    else:
        out.append(result(A, "displays asleep", PASS, "awake now; they would sleep after %s idle" % minutes(monitor_timeout)))
    return out


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def claude_profiles(user_data):
    """Profile folder names whose Extensions folder has the Claude extension."""
    hits = []
    for folder in sorted(glob.glob(os.path.join(user_data, "*", "Extensions", CLAUDE_EXTENSION_ID))):
        if os.path.isdir(folder):
            hits.append(os.path.basename(os.path.dirname(os.path.dirname(folder))))
    return hits


def check_browsers(p, procs):
    A = "Browsers"
    out = []
    local = p.localappdata
    spec = [("chrome", "chrome.exe", os.path.join(local, "Google", "Chrome", "User Data"), [os.path.join("Google", "Chrome", "Application", "chrome.exe")]),
            ("edge", "msedge.exe", os.path.join(local, "Microsoft", "Edge", "User Data"), [os.path.join("Microsoft", "Edge", "Application", "msedge.exe")])]
    holders = {}
    for key, image, user_data, rel in spec:
        installed = any(os.path.exists(os.path.join(b, r)) for b in p.program_files + [local] for r in rel if b)
        pids = count(procs, image) if procs is not None else None
        holders[key] = bool(local) and bool(claude_profiles(user_data))
        out.append(result(A, key + " installed", PASS if installed else WARN, "yes" if installed else "not found"))
        if pids is None:
            out.append(result(A, key + " running", SKIP, "cannot list processes"))
        else:
            out.append(result(A, key + " running", PASS if pids else (WARN if holders[key] else INFO),
                              procs_text(len(pids)) if pids else "not running" + (" (it holds the Claude extension)" if holders[key] else "")))
        state = read_json(os.path.join(user_data, "Local State")) if local else None
        bg = (state or {}).get("background_mode", {}).get("enabled") if state is not None else None
        if state is None:
            out.append(result(A, key + " keep running in background", SKIP, "Local State file not readable"))
        elif bg is None:
            out.append(result(A, key + " keep running in background", PASS, "not set, so the browser default (on) applies"))
        elif bg:
            out.append(result(A, key + " keep running in background", PASS, "on"))
        else:
            out.append(result(A, key + " keep running in background", WARN if holders[key] else INFO,
                              "off: closing the last window quits the browser" + (" and the Claude extension with it" if holders[key] else "")))
        profiles = claude_profiles(user_data) if local else []
        out.append(result(A, key + " Claude extension", PASS if profiles else INFO,
                          "installed (profile folder: %s)" % ", ".join(profiles) if profiles else "not installed"))
    if not any(holders.values()):
        out.append(result(A, "Claude extension anywhere", FAIL, "not found in Chrome or Edge"))
    return out


def check_tools(p):
    A = "Tools"
    out = []

    def versioned(name, cmd, first=True):
        r = p.run(cmd)
        path = p.which(cmd[0])
        if r is None or (r[0] != 0):
            return result(A, name, PASS if path else FAIL, tidy(path) + " (version not readable)" if path else "not found on PATH")
        line = (r[1].strip().splitlines() or [""])[0]
        return result(A, name, PASS, tidy(line)[:60])

    ff = p.which("ffmpeg")
    ff_dir = os.path.join(FFMPEG_DIR, "ffmpeg.exe")
    if ff:
        out.append(result(A, "ffmpeg", PASS, "on PATH"))
    elif os.path.exists(ff_dir):
        out.append(result(A, "ffmpeg", PASS, "found in %s (not on PATH, use the full path)" % FFMPEG_DIR))
    else:
        out.append(result(A, "ffmpeg", FAIL, "not on PATH and not in " + FFMPEG_DIR))
    out.append(versioned("git", ["git", "--version"]))
    if p.which("gh"):
        r = p.run(["gh", "auth", "status"])  # exit code only, the text may show account names
        out.append(result(A, "gh logged in", PASS if r and r[0] == 0 else FAIL, "yes" if r and r[0] == 0 else "run: gh auth login"))
    else:
        out.append(result(A, "gh logged in", FAIL, "gh is not on PATH"))
    out.append(result(A, "python", PASS, "%d.%d.%d" % sys.version_info[:3]))
    out.append(result(A, "luau runner", PASS if os.path.exists(LUAU) else FAIL, tidy(LUAU) if os.path.exists(LUAU) else "missing: " + tidy(LUAU)))
    return out


def git_worktrees(p):
    r = p.run(["git", "-C", str(ROOT), "worktree", "list", "--porcelain"], timeout=60)
    if not r or r[0]:
        return None
    items, cur = [], None
    for line in r[1].splitlines():
        if line.startswith("worktree "):
            cur = {"path": line[9:].strip(), "prunable": False}
            items.append(cur)
        elif line.startswith("prunable") and cur:
            cur["prunable"] = True
    return items


def gitdir_of(path):
    git = os.path.join(path, ".git")
    if os.path.isdir(git):
        return git
    try:
        with open(git, "r", encoding="utf-8") as f:
            m = re.match(r"gitdir:\s*(.+)", f.read().strip())
        return m.group(1).strip() if m else None
    except OSError:
        return None


def check_hygiene(p, stale_days=3):
    A = "Repo"
    out = []
    wts = git_worktrees(p)
    if wts is None:
        out.append(result(A, "worktrees", SKIP, "git could not list worktrees"))
    else:
        out.append(result(A, "worktrees", PASS if len(wts) <= 150 else WARN, "%d registered%s" % (len(wts), "" if len(wts) <= 150 else " (many: ask the lead to clean up)")))
        main = wts[0]["path"].replace("\\", "/").rstrip("/")
        base = main + "/.claude/worktrees/"
        under = [w for w in wts if w["path"].replace("\\", "/").startswith(base)]
        stale, oldest = 0, 0.0
        for w in under:
            gd = gitdir_of(w["path"])
            ages = [a for a in (p.idle_since(os.path.join(gd, n)) for n in ("HEAD", "index", "logs/HEAD")) if a is not None] if gd else []
            age = min(ages) if ages else None
            if w["prunable"] or age is None or age > stale_days * 86400:
                stale += 1
                oldest = max(oldest, age or 0)
        folders = len(glob.glob(base + "*")) if os.path.isdir(base) else 0
        orphans = max(0, folders - len(under))
        detail = "%d of %d under .claude/worktrees had no git activity for %d+ days (nothing is deleted by this tool)" % (stale, len(under), stale_days)
        if orphans:
            detail += "; %d folders there are not registered" % orphans
        out.append(result(A, "stale worktrees", PASS if stale == 0 and not orphans else WARN, detail))
    free = p.disk_free_gb(ROOT)
    if free is None:
        out.append(result(A, "disk free", SKIP, "cannot read"))
    else:
        out.append(result(A, "disk free", FAIL if free < 5 else WARN if free < 20 else PASS, "%.0f GB free on the repo drive" % free))
    return out


def check_power(p):
    A = "Power"
    scheme = p.power_scheme()
    out = []
    if scheme is None:
        return [result(A, "power plan", SKIP, "powercfg not readable on this machine")]
    out.append(result(A, "power plan", INFO, scheme))
    for label, sub, setting in RECOMMENDED:
        v = p.power_ac_seconds(sub, setting)
        if v is None:
            out.append(result(A, label, SKIP, "not readable"))
            continue
        now = "never" if v == 0 else minutes(v)
        out.append(result(A, label, PASS if v == 0 else WARN, "now %s; docs/158 recommends never%s" % (now, "" if v == 0 else " (how to set: docs/158 section 3)")))
    return out


def run_checks(p, stale_days=3, blender_port=BLENDER_PORT):
    procs, listen = p.processes(), p.listening()
    idle = p.idle_seconds()
    monitor = p.power_ac_seconds("SUB_VIDEO", "VIDEOIDLE")
    parts = [("Blender", lambda: check_blender(p, procs, listen, blender_port)),
             ("Studio", lambda: check_studio(p, procs, listen, idle, monitor)),
             ("Browsers", lambda: check_browsers(p, procs)),
             ("Tools", lambda: check_tools(p)),
             ("Repo", lambda: check_hygiene(p, stale_days)),
             ("Power", lambda: check_power(p))]
    out = []
    for area, fn in parts:
        try:
            out += fn()
        except Exception as e:  # a broken probe must not hide the other areas
            out.append(result(area, "check", WARN, "this check crashed: %s" % e.__class__.__name__))
    return out


# ----------------------------------------------------------------------------------------------
# Launch (never stops anything, never touches Studio)
# ----------------------------------------------------------------------------------------------
def find_browser(p, key):
    rel = {"chrome": os.path.join("Google", "Chrome", "Application", "chrome.exe"),
           "edge": os.path.join("Microsoft", "Edge", "Application", "msedge.exe")}[key]
    for base in p.program_files + ([p.localappdata] if p.localappdata else []):
        if os.path.exists(os.path.join(base, rel)):
            return os.path.join(base, rel)
    return p.which({"chrome": "chrome", "edge": "msedge"}[key])


def launch(p, target, dry_run=False):
    """Returns (ok, message)."""
    procs = p.processes()
    if procs is None:
        return False, "cannot list processes here, so I will not start anything"
    image = {"blender": "blender.exe", "chrome": "chrome.exe", "edge": "msedge.exe"}[target]
    if count(procs, image):
        return True, "%s is already running: nothing started (this tool never starts a second copy)" % target
    exe = find_blender(p) if target == "blender" else find_browser(p, target)
    if not exe:
        return False, "%s is not installed (program not found)" % target
    cmd = [exe] + (["--python", str(ENABLE_SCRIPT)] if target == "blender" else [])
    if dry_run:
        return True, "dry run, would start: " + tidy(" ".join(cmd))
    try:
        p.spawn(cmd)
    except OSError as e:
        return False, "could not start %s (%s)" % (target, e.__class__.__name__)
    return True, "started %s. A window opens in front; wait about 20 s, then run the check again." % target


# ----------------------------------------------------------------------------------------------
def table(results):
    marks = {PASS: "[ ok ]", FAIL: "[FAIL]", WARN: "[warn]", INFO: "[info]", SKIP: "[skip]"}
    wa = max(len(r["area"]) for r in results)
    wn = max(len(r["name"]) for r in results)
    return "\n".join("%s %-*s  %-*s  %s" % (marks[r["status"]], wa, r["area"], wn, r["name"], r["detail"]) for r in results)


def summary(results):
    counts = {k: sum(1 for r in results if r["status"] == k) for k in (PASS, FAIL, WARN, INFO, SKIP)}
    return counts


def main(argv=None, probes=None):
    ap = argparse.ArgumentParser(description="Read-only morning health check (docs/165).")
    ap.add_argument("--json", metavar="FILE", help="also write the results as JSON")
    ap.add_argument("--launch", choices=["blender", "chrome", "edge"], help="start this program (never stops anything; no Studio option)")
    ap.add_argument("--dry-run", action="store_true", help="with --launch: only say what would be started")
    ap.add_argument("--stale-days", type=int, default=3, help="a worktree with no git activity for this many days counts as stale")
    ap.add_argument("--blender-port", type=int, default=BLENDER_PORT)
    args = ap.parse_args(argv)
    p = probes or Probes()
    if args.launch:
        ok, msg = launch(p, args.launch, args.dry_run)
        print(msg)
        return 0 if ok else 1
    results = run_checks(p, args.stale_days, args.blender_port)
    print(table(results))
    counts = summary(results)
    print("\n%d ok, %d FAIL, %d warn, %d skipped. Nothing was changed on this PC." % (counts[PASS], counts[FAIL], counts[WARN], counts[SKIP]))
    if args.json:
        doc = {"generated": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "summary": counts, "results": results}
        Path(args.json).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return 1 if counts[FAIL] else 0


if __name__ == "__main__":
    sys.exit(main())
