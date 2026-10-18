"""tools/dev_env_check.py (docs/165): every probe is faked; the real probes must degrade without the tools."""
import io
import json
import os
import re
import socket
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dev_env_check as dec  # noqa: E402


class FakeProbes(dec.Probes):
    """Everything the machine could say, set by the test. Nothing here touches the real PC."""

    def __init__(self, base):
        super().__init__()
        self.windows_os = True
        self.localappdata = os.path.join(base, "Local")
        self.appdata = os.path.join(base, "Roaming")
        self.program_files = [os.path.join(base, "PF")]
        self.procs = [("blender.exe", 100), ("robloxstudiobeta.exe", 200), ("studiomcp.exe", 300), ("msedge.exe", 400)]
        self.ports = [(9876, 100), (13469, 300)]
        self.open_ports = {13469}
        self.ping = (True, "")
        self.wins = [{"title": "Place1 - Roblox Studio", "minimised": False}, {"title": "Some Other App", "minimised": False}]
        self.idle = 30.0
        self.power = {"VIDEOIDLE": 0, "STANDBYIDLE": 0, "HIDEIDLE": 0, "HIBERNATEIDLE": 0, "DISKIDLE": 0}
        self.scheme = "always on"
        self.tools = {"ffmpeg": "x", "gh": "x"}
        self.run_results = {}
        self.spawned = []
        self.free = 100.0
        self.ages = 3600.0

    def processes(self):
        return self.procs

    def listening(self):
        return self.ports

    def tcp_connect(self, port, timeout=1.0):
        return port in self.open_ports

    def blender_ping(self, port, timeout=3.0):
        return self.ping

    def windows(self, pids):
        return self.wins

    def idle_seconds(self):
        return self.idle

    def power_scheme(self):
        return self.scheme

    def power_ac_seconds(self, subgroup, setting):
        return self.power.get(setting)

    def which(self, name):
        return self.tools.get(name)

    def run(self, cmd, timeout=15):
        key = cmd[0] if cmd[0] != "git" or "worktree" not in cmd else "git-worktree"
        return self.run_results.get(key, (0, "ok 1.0\n"))

    def disk_free_gb(self, path):
        return self.free

    def idle_since(self, path):
        return self.ages

    def spawn(self, cmd):
        self.spawned.append(cmd)


def touch(path, text=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def build_machine(base):
    """A healthy machine on disk: Blender with the add-on, Edge with the Claude extension, Chrome without."""
    touch(os.path.join(base, "PF", "Blender Foundation", "Blender 4.2", "blender.exe"))
    touch(os.path.join(base, "PF", "Blender Foundation", "Blender 5.1", "blender.exe"))
    touch(os.path.join(base, "Roaming", "Blender Foundation", "Blender", "5.1", "scripts", "addons", "blender_mcp.py"))
    touch(os.path.join(base, "PF", "Google", "Chrome", "Application", "chrome.exe"))
    touch(os.path.join(base, "PF", "Microsoft", "Edge", "Application", "msedge.exe"))
    touch(os.path.join(base, "Local", "Google", "Chrome", "User Data", "Local State"), json.dumps({"background_mode": {"enabled": False}}))
    touch(os.path.join(base, "Local", "Microsoft", "Edge", "User Data", "Local State"), json.dumps({"background_mode": {"enabled": True}}))
    touch(os.path.join(base, "Local", "Microsoft", "Edge", "User Data", "Profile 1", "Extensions", dec.CLAUDE_EXTENSION_ID, "1.0", "manifest.json"), "{}")


def by_name(results, area, name):
    hits = [r for r in results if r["area"] == area and r["name"] == name]
    assert len(hits) == 1, (area, name, hits)
    return hits[0]


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = FakeProbes(self.tmp.name)
        build_machine(self.tmp.name)

    def run_all(self):
        return dec.run_checks(self.p)

    def status(self, area, name, results=None):
        return by_name(results or self.run_all(), area, name)["status"]

    def test_healthy_machine_has_no_failures(self):
        results = self.run_all()
        self.assertEqual([r for r in results if r["status"] == dec.FAIL], [])
        self.assertEqual(by_name(results, "Blender", "MCP port 9876")["status"], dec.PASS)
        self.assertIn("Blender 5.1", by_name(results, "Blender", "installed")["detail"])  # newest version wins

    def test_blender_not_running_skips_the_port(self):
        self.p.procs = [x for x in self.p.procs if x[0] != "blender.exe"]
        r = self.run_all()
        self.assertEqual(by_name(r, "Blender", "running")["status"], dec.FAIL)
        self.assertEqual(by_name(r, "Blender", "MCP port 9876")["status"], dec.SKIP)

    def test_blender_port_problems(self):
        self.p.ports = []
        self.assertEqual(self.status("Blender", "MCP port 9876"), dec.FAIL)
        self.p.ports = [(9876, 999)]
        self.assertEqual(self.status("Blender", "MCP port 9876"), dec.WARN)
        self.p.ports = [(9876, 100)]
        self.p.ping = (False, "no answer in 3 s (Blender busy?)")
        r = by_name(self.run_all(), "Blender", "MCP port 9876")
        self.assertEqual(r["status"], dec.FAIL)
        self.assertIn("busy", r["detail"])

    def test_blender_not_installed(self):
        for base in self.p.program_files:
            for root, _d, files in os.walk(os.path.join(base, "Blender Foundation")):
                for f in files:
                    os.remove(os.path.join(root, f))
        self.assertEqual(self.status("Blender", "installed"), dec.FAIL)

    def test_studio_minimised_window_fails_and_names_it(self):
        self.p.wins = [{"title": "Place1 - Roblox Studio", "minimised": True}]
        r = by_name(self.run_all(), "Studio", "window")
        self.assertEqual(r["status"], dec.FAIL)
        self.assertIn("MINIMISED", r["detail"])

    def test_only_studio_window_titles_are_reported(self):
        details = " ".join(r["detail"] for r in self.run_all())
        self.assertIn("Place1 - Roblox Studio", details)
        self.assertNotIn("Some Other App", details)

    def test_studio_not_running(self):
        self.p.procs = [x for x in self.p.procs if x[0] not in ("robloxstudiobeta.exe", "studiomcp.exe")]
        r = self.run_all()
        self.assertEqual(by_name(r, "Studio", "running")["status"], dec.FAIL)
        self.assertEqual(by_name(r, "Studio", "MCP plugin")["status"], dec.WARN)

    def test_studio_mcp_port_closed(self):
        self.p.open_ports = set()
        self.assertEqual(self.status("Studio", "MCP plugin"), dec.WARN)

    def test_locked_pc_fails(self):
        self.p.procs.append(("logonui.exe", 500))
        self.assertEqual(self.status("Studio", "PC locked"), dec.FAIL)

    def test_displays_asleep_heuristic(self):
        self.p.power["VIDEOIDLE"] = 600
        self.p.idle = 900
        self.assertEqual(self.status("Studio", "displays asleep"), dec.WARN)
        self.p.idle = 100
        self.assertEqual(self.status("Studio", "displays asleep"), dec.PASS)
        self.p.power["VIDEOIDLE"] = 0
        self.p.idle = 99999
        self.assertEqual(self.status("Studio", "displays asleep"), dec.PASS)

    def test_browsers(self):
        r = self.run_all()
        self.assertEqual(by_name(r, "Browsers", "edge Claude extension")["status"], dec.PASS)
        self.assertIn("Profile 1", by_name(r, "Browsers", "edge Claude extension")["detail"])
        self.assertEqual(by_name(r, "Browsers", "chrome Claude extension")["status"], dec.INFO)
        # Chrome has the setting off, but it does not hold the Claude extension, so only INFO
        self.assertEqual(by_name(r, "Browsers", "chrome keep running in background")["status"], dec.INFO)
        self.assertEqual(by_name(r, "Browsers", "edge keep running in background")["status"], dec.PASS)

    def test_extension_holder_not_running_or_background_off_warns(self):
        self.p.procs = [x for x in self.p.procs if x[0] != "msedge.exe"]
        self.assertEqual(self.status("Browsers", "edge running"), dec.WARN)
        touch(os.path.join(self.tmp.name, "Local", "Microsoft", "Edge", "User Data", "Local State"), json.dumps({"background_mode": {"enabled": False}}))
        self.assertEqual(self.status("Browsers", "edge keep running in background"), dec.WARN)

    def test_background_setting_missing_means_default_on(self):
        touch(os.path.join(self.tmp.name, "Local", "Microsoft", "Edge", "User Data", "Local State"), "{}")
        self.assertEqual(self.status("Browsers", "edge keep running in background"), dec.PASS)

    def test_claude_extension_nowhere_fails(self):
        import shutil
        shutil.rmtree(os.path.join(self.tmp.name, "Local", "Microsoft", "Edge", "User Data", "Profile 1"))
        self.assertEqual(self.status("Browsers", "Claude extension anywhere"), dec.FAIL)

    def test_tools(self):
        r = self.run_all()
        self.assertEqual(by_name(r, "Tools", "ffmpeg")["status"], dec.PASS)
        self.assertEqual(by_name(r, "Tools", "gh logged in")["status"], dec.PASS)
        self.p.run_results["gh"] = (1, "You are not logged into any GitHub hosts")
        self.p.tools = {}
        r = self.run_all()
        self.assertEqual(by_name(r, "Tools", "gh logged in")["status"], dec.FAIL)

    def test_gh_text_is_never_copied_into_results(self):
        self.p.run_results["gh"] = (0, "Logged in to github.com account SECRETNAME (token)")
        self.assertNotIn("SECRETNAME", json.dumps(self.run_all()))

    def test_hygiene_and_disk(self):
        main = os.path.join(self.tmp.name, "repo").replace("\\", "/")
        wt = main + "/.claude/worktrees/agent-1"
        os.makedirs(wt)
        os.makedirs(main + "/.claude/worktrees/leftover-folder")
        gd = os.path.join(self.tmp.name, "gd")
        os.makedirs(gd)
        touch(wt + "/.git", "gitdir: %s\n" % gd)
        self.p.run_results["git-worktree"] = (0, "worktree %s\nHEAD abc\n\nworktree %s\nHEAD def\nprunable gitdir missing\n" % (main, wt))
        self.p.ages = 10 * 86400
        r = self.run_all()
        d = by_name(r, "Repo", "stale worktrees")
        self.assertEqual(d["status"], dec.WARN)
        self.assertIn("1 of 1", d["detail"])
        self.assertIn("1 folders", d["detail"])
        self.p.free = 3
        self.assertEqual(self.status("Repo", "disk free"), dec.FAIL)
        self.p.free = 10
        self.assertEqual(self.status("Repo", "disk free"), dec.WARN)

    def test_power_compare(self):
        r = self.run_all()
        self.assertEqual(by_name(r, "Power", "monitor-timeout-ac")["status"], dec.PASS)
        self.p.power["DISKIDLE"] = 1200
        d = by_name(self.run_all(), "Power", "disk-timeout-ac")
        self.assertEqual(d["status"], dec.WARN)
        self.assertIn("20 min", d["detail"])

    def test_a_crashing_probe_does_not_hide_the_rest(self):
        def boom(*a, **k):
            raise RuntimeError("x")
        self.p.power_scheme = boom
        r = self.run_all()
        self.assertEqual(by_name(r, "Power", "check")["status"], dec.WARN)
        self.assertEqual(by_name(r, "Blender", "running")["status"], dec.PASS)

    def test_no_home_folder_in_output(self):
        home = os.path.expanduser("~").replace("\\", "/")
        self.assertNotIn(home, dec.tidy(home + "/x"))


class LaunchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = FakeProbes(self.tmp.name)
        build_machine(self.tmp.name)
        self.p.procs = []

    def test_blender_starts_with_the_enable_script(self):
        ok, msg = dec.launch(self.p, "blender")
        self.assertTrue(ok, msg)
        self.assertEqual(len(self.p.spawned), 1)
        self.assertEqual(self.p.spawned[0][1], "--python")
        self.assertTrue(self.p.spawned[0][2].endswith("enable_mcp_addon.py"))
        self.assertTrue(dec.ENABLE_SCRIPT.exists())

    def test_browsers_start_plain(self):
        for name in ("chrome", "edge"):
            self.p.spawned.clear()
            ok, _ = dec.launch(self.p, name)
            self.assertTrue(ok)
            self.assertEqual(len(self.p.spawned[0]), 1)

    def test_running_program_is_never_started_twice(self):
        self.p.procs = [("blender.exe", 1), ("chrome.exe", 2), ("msedge.exe", 3)]
        for name in ("blender", "chrome", "edge"):
            ok, msg = dec.launch(self.p, name)
            self.assertTrue(ok)
            self.assertIn("already running", msg)
        self.assertEqual(self.p.spawned, [])

    def test_dry_run_and_missing_program_start_nothing(self):
        ok, msg = dec.launch(self.p, "blender", dry_run=True)
        self.assertTrue(ok)
        self.assertIn("dry run", msg)
        self.assertEqual(self.p.spawned, [])
        self.p.program_files = []
        self.p.tools = {}
        ok, msg = dec.launch(self.p, "blender")
        self.assertFalse(ok)
        self.assertEqual(self.p.spawned, [])

    def test_no_launch_option_for_studio(self):
        with self.assertRaises(SystemExit), redirect_stdout(io.StringIO()), open(os.devnull, "w") as dn:
            old, sys.stderr = sys.stderr, dn
            try:
                dec.main(["--launch", "studio"], probes=self.p)
            finally:
                sys.stderr = old
        self.assertEqual(self.p.spawned, [])

    def test_unknown_process_list_means_nothing_starts(self):
        self.p.processes = lambda: None
        ok, _ = dec.launch(self.p, "chrome")
        self.assertFalse(ok)
        self.assertEqual(self.p.spawned, [])


class MainTests(unittest.TestCase):
    def test_table_json_and_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = FakeProbes(tmp)
            build_machine(tmp)
            out_json = os.path.join(tmp, "out.json")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = dec.main(["--json", out_json], probes=p)
            self.assertEqual(rc, 0)
            self.assertIn("Nothing was changed on this PC", buf.getvalue())
            doc = json.loads(Path(out_json).read_text(encoding="utf-8"))
            self.assertEqual(doc["summary"]["FAIL"], 0)
            self.assertTrue(all(set(r) == {"area", "name", "status", "detail"} for r in doc["results"]))
            p.procs = []
            with redirect_stdout(io.StringIO()):
                self.assertEqual(dec.main([], probes=p), 1)


class RealProbeTests(unittest.TestCase):
    def test_real_probes_degrade_on_a_machine_without_the_tools(self):
        p = dec.Probes()
        p.windows_os = False  # pretend: no Windows, no tasklist, no powercfg
        p.localappdata = p.appdata = ""
        p.program_files = []
        p.which = lambda name: None
        p.run = lambda cmd, timeout=15: None
        p.listening = lambda: None
        results = dec.run_checks(p)
        self.assertTrue(results)
        self.assertFalse([r for r in results if "crashed" in r["detail"]], results)
        self.assertEqual(by_name(results, "Power", "power plan")["status"], dec.SKIP)
        self.assertEqual(by_name(results, "Studio", "running")["status"], dec.SKIP)

    def test_real_ping_to_a_closed_port_is_a_plain_false(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        ok, why = dec.Probes().blender_ping(port, timeout=0.5)
        self.assertFalse(ok)
        self.assertIn("cannot connect", why)
        self.assertFalse(dec.Probes().tcp_connect(port, timeout=0.5))

    def serve_once(self, reply):
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        seen = []

        def go():
            c, _ = srv.accept()
            seen.append(json.loads(c.recv(4096).decode("utf-8")))
            if reply is not None:
                c.sendall(reply)
            c.close()
            srv.close()
        t = threading.Thread(target=go, daemon=True)
        t.start()
        return srv.getsockname()[1], seen, t

    def test_real_ping_sends_only_ping_and_reads_pong(self):
        port, seen, t = self.serve_once(json.dumps({"status": "success", "result": {"pong": True}}).encode())
        ok, _ = dec.Probes().blender_ping(port, timeout=2)
        t.join(3)
        self.assertTrue(ok)
        self.assertEqual(seen, [{"type": "ping"}])

    def test_real_ping_with_a_wrong_answer(self):
        port, _seen, t = self.serve_once(b'{"status": "error"}')
        ok, why = dec.Probes().blender_ping(port, timeout=2)
        t.join(3)
        self.assertFalse(ok)
        self.assertIn("not with pong", why)

    def test_real_probes_on_this_machine_never_raise(self):
        p = dec.Probes()
        for fn in (p.processes, p.listening, p.idle_seconds, p.power_scheme):
            fn()
        p.windows({1})
        p.power_ac_seconds("SUB_VIDEO", "VIDEOIDLE")


class SafetyTests(unittest.TestCase):
    """The tool must stay read-only: no window, process or setting API in its source."""

    def source(self):
        text = (ROOT / "tools" / "dev_env_check.py").read_text(encoding="utf-8")
        return re.sub(r'"""[\s\S]*?"""', "", text, count=1)  # the module docstring names what it never does

    def test_no_forbidden_api(self):
        src = self.source()
        for word in ("SetForegroundWindow", "ShowWindow", "SetWindowPos", "BringWindowToTop", "SwitchToThisWindow", "PostMessage",
                     "SendMessage", "SendInput", "keybd_event", "mouse_event", "TerminateProcess", "taskkill", "os.kill", ".kill(",
                     ".terminate(", "ImageGrab", "BitBlt", "PrintWindow", "screenshot", "winreg", "setx", "/setactive", "/change", "/hibernate"):
            self.assertNotIn(word, src, word)

    def test_powercfg_is_only_queried(self):
        for m in re.finditer(r'\["powercfg",\s*"([^"]+)"', self.source()):
            self.assertIn(m.group(1), ("/query", "/getactivescheme"))

    def test_enable_script_never_saves_preferences(self):
        text = (ROOT / "tools" / "blender" / "enable_mcp_addon.py").read_text(encoding="utf-8")
        self.assertNotIn("save_userpref", text)
        self.assertNotIn("save_mainfile", text)


if __name__ == "__main__":
    unittest.main()
