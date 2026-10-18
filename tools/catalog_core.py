"""Shared helpers for the team catalogue (BD-1052, docs/188): load the real game data, find pictures, collect gaps.

Nothing here knows a game number. Numbers come from the Luau data modules through the pinned runner (tools/catalog_dump.luau),
from tools/release_profiles.py (flag states) or from the repository file list (pictures).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

# The data modules the catalogue reads. Their own requires are followed automatically.
REQUESTED_MODULES = [
    "Config", "ProgressionConfig", "EggGenetics", "SecretSpeciesConfig", "ScaleLadder", "CombatConfig", "MutationLook",
    "AssetSlots", "LowPolyDinoAssets", "LowPolyPattern", "SpecialFoods", "BiomeMap", "BiomePlacement", "WorldKitData",
    "WorldKitMeshAssets", "CaveHubProps", "RarityCurve", "UIIconAssets", "ArtworkAssets", "IdentityFusion", "FusionOdds",
    "WeatherLooks", "ClassInfo", "ShopOdds", "EggOutcomeOdds", "RewardMath", "FoodCatchRules",
]
REQUIRED_MODULES = ["Config", "ProgressionConfig", "EggGenetics", "SecretSpeciesConfig", "ScaleLadder", "CombatConfig",
                    "MutationLook", "AssetSlots", "LowPolyDinoAssets", "ClassInfo", "ShopOdds"]

DEFAULT_RUNNERS = [
    "C:/Users/znypr/AppData/Local/Temp/bd057/luau/luau.exe",
    "/tmp/luau/luau",
]


# ---------------------------------------------------------------- the Luau runner and the data dump
def find_runner(explicit: Optional[str] = None) -> str:
    candidates = [explicit, os.environ.get("LUAU_RUNNER"), shutil.which("luau")] + DEFAULT_RUNNERS
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise SystemExit("No Luau runner found. Pass --runner PATH or set LUAU_RUNNER (docs/160 section 3 lists the pinned runner).")


def _module_files(root: Path) -> dict[str, Path]:
    modules: dict[str, Path] = {}
    for folder in ("src/shared", "src/server"):
        for path in sorted((root / folder).glob("*.luau")):
            if path.name.endswith((".server.luau", ".client.luau")):
                continue
            modules[path.stem] = path
    return modules


def _closure(root: Path) -> list[str]:
    files = _module_files(root)
    seen: list[str] = []
    todo = list(REQUESTED_MODULES)
    while todo:
        name = todo.pop()
        if name in seen or name not in files:
            continue
        seen.append(name)
        for match in re.finditer(r"require\(\s*([A-Za-z_.]+)\s*\)", files[name].read_text(encoding="utf-8")):
            todo.append(match.group(1).split(".")[-1])
    return sorted(seen)


def dump_data(root: Path, runner: str) -> dict[str, Any]:
    """Run catalog_dump.luau with the real module sources pasted in. Returns {'data':..., 'calls':..., 'errors':...}."""
    files = _module_files(root)
    parts = []
    for name in _closure(root):
        text = files[name].read_text(encoding="utf-8")
        parts.append(f"SOURCES.{name} = function(script, require, typeof, Color3, game)\n{text}\nend")
    template = (root / "tools" / "catalog_dump.luau").read_text(encoding="utf-8")
    script = template.replace("--@MODULES@", "\n".join(parts))
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "catalog_dump.luau"
        path.write_text(script, encoding="utf-8")
        result = subprocess.run([runner, str(path)], capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0 or not result.stdout.strip():
        raise SystemExit("The Luau data dump failed (runner %s):\n%s%s" % (runner, result.stdout[-500:], result.stderr[-1500:]))
    dump = json.loads(result.stdout)
    for key in ("data", "calls", "errors"):
        if not dump.get(key):
            dump[key] = {}
    for name in REQUIRED_MODULES:
        if dump["data"].get(name) is None:
            raise SystemExit("Required game module %s could not be loaded: %s" % (name, dump["errors"].get(name)))
    return dump


# ---------------------------------------------------------------- flags (release profiles)
FLAGS = [
    ("SecretSpeciesEnabled", "Secret species"),
    ("SpecialFoodsEnabled", "Golden Drumstick (special food)"),
    ("IdentityFusionPreviewEnabled", "Fusion"),
    ("PerDinoCosmeticsEnabled", "Auras and trails bought per dino"),
    ("CaveHub", "Cave hub (statues, stations)"),
    ("LowPolyDinos", "Low-poly dinosaur models"),
    ("HatchV2", "New hatch screen"),
    ("ClassMovementEnabled", "Class moves (glide, dash)"),
    ("CombatEnabled", "Fights"),
    ("DinoSkinsEnabled", "Dino skins"),
    ("ObjectivesEnabled", "Goals"),
    ("FastTravelPerk", "Fast travel perk"),
    ("CrystalPacksEnabled", "Crystal packs (Robux)"),
    ("PaidRandomItemsEnabled", "Paid random items (Robux)"),
]


def flag_states(root: Path) -> dict[str, dict[str, Any]]:
    """{flag: {'default': bool|None, 'playtest': bool|None}} from Config.luau and tools/release_profiles.py."""
    import release_profiles  # type: ignore

    source = (root / "src/shared/Config.luau").read_text(encoding="utf-8")
    playtest_source, _ = release_profiles.apply_profile(source, "playtest")
    default_entries = release_profiles.config_entries(source)
    playtest_entries = release_profiles.config_entries(playtest_source)
    states: dict[str, dict[str, Any]] = {}
    for key, _label in FLAGS:
        def value(entries: dict) -> Any:
            found = entries.get(key)
            return found[-1][1] if found else None
        states[key] = {"default": value(default_entries), "playtest": value(playtest_entries)}
    return states


# ---------------------------------------------------------------- repository files (pictures)
class Files:
    """The tracked files of the repository (git ls-files, so CI and a clean worktree agree). Falls back to a walk."""

    def __init__(self, root: Path):
        self.root = root
        names: list[str] = []
        try:
            out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, check=True).stdout
            names = [n for n in out.decode("utf-8", "replace").split("\0") if n]
        except (OSError, subprocess.CalledProcessError):
            for folder in ("resources", "docs", "assets"):
                for path in (root / folder).rglob("*"):
                    if path.is_file():
                        names.append(path.relative_to(root).as_posix())
        self.names = set(names)

    def has(self, path: str) -> bool:
        return path in self.names

    def newest_version(self, stem: str, extensions: Iterable[str] = ("png", "jpg", "jpeg", "webp")) -> Optional[str]:
        """'resources/ui/v2/icons/weather-rain' -> the highest '-vN' file that exists, else the plain name."""
        best: tuple[int, str] | None = None
        for ext in extensions:
            pattern = re.compile(re.escape(stem) + r"-v(\d+)\." + ext + "$")
            for name in self.names:
                match = pattern.match(name)
                if match and (best is None or int(match.group(1)) > best[0]):
                    best = (int(match.group(1)), name)
            if self.has(f"{stem}.{ext}") and best is None:
                best = (0, f"{stem}.{ext}")
        return best[1] if best else None

    def by_basename(self, basename: str) -> Optional[str]:
        found = sorted(n for n in self.names if n.rsplit("/", 1)[-1] == basename)
        return found[0] if found else None


# ---------------------------------------------------------------- gaps ("Missing")
@dataclass
class Gap:
    kind: str  # picture, icon, asset id, model id, mask, registry line, not in code
    category: str
    item: str
    anchor: str  # "Page#anchor" of the section
    what: str
    folder: str
    file: str
    note: str = ""


@dataclass
class Gaps:
    rows: list[Gap] = field(default_factory=list)

    def add(self, kind: str, category: str, item: str, anchor: str, what: str, folder: str = "", file: str = "", note: str = "") -> None:
        self.rows.append(Gap(kind, category, item, anchor, what, folder, file, note))

    def by_kind(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in self.rows:
            counts[row.kind] = counts.get(row.kind, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


# ---------------------------------------------------------------- number and text formatting
def num(value: float, sig: int = 4) -> str:
    """A short plain number: 26, 0.0366, 1,200. Never an exponent."""
    if value == int(value) and abs(value) < 1e15:
        return f"{int(value):,}"
    text = f"{value:.{sig}g}"
    if "e" in text or "E" in text:
        text = f"{value:.10f}".rstrip("0").rstrip(".")
    elif "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def pct(percent: float, sig: int = 4) -> str:
    """percent is already 0..100."""
    return num(percent, sig) + "%"


def plus(multiplier: float) -> str:
    """1.2 -> '+20%' (docs/72: kids read '+20%', not 'x1.2')."""
    p = (multiplier - 1) * 100
    return ("+" if p >= 0 else "-") + num(abs(p), 3) + "%"


def one_in(percent: float) -> str:
    if percent <= 0:
        return "never"
    n = 100.0 / percent
    if n < 1.05:
        return "every time"
    return "1 in " + (f"{round(n):,}" if n >= 10 else num(n, 3))


def kebab(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def title_from_id(identifier: str) -> str:
    """'02_emerald_islands' -> 'Emerald islands'; 'bloodmoon' -> 'Bloodmoon'."""
    text = re.sub(r"^\d+_", "", identifier).replace("_", " ")
    return text[:1].upper() + text[1:]


def hex_rgb(rgb: Iterable[int]) -> str:
    r, g, b = [int(round(v)) for v in rgb]
    return "#%02X%02X%02X" % (r, g, b)


def md_cell(text: Any) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def table(header: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    for row in rows:
        out.append("| " + " | ".join(md_cell(cell) for cell in row) + " |")
    return "\n".join(out)
