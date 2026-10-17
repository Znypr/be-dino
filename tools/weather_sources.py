"""Where the client weather code lives (docs/153), for the verifiers that read it as text.

src/client/WeatherVisuals.client.luau keeps the Lighting grade, atmosphere, clouds, lamp, the main loop and the camera shake. The rigs, sky props,
one-shots, quake and title card moved, unchanged, into sibling modules it requires (`local Rigs=require(script.Parent.WeatherRigs)`, ...), each a
`return function(ctx) ... end` factory built once in the original order. So:

  * `main_text()` is the main script only (use it where the check is about the per-frame loop: everything after `RunService.Heartbeat:Connect`);
  * `parts_text()` is every part, in require order;
  * `weather_text()` is the main script followed by every part: use it wherever a verifier used to read WeatherVisuals.client.luau as one text
    and looks for a function, a call or a string (the text of each moved function is what it was before the split);
  * `files()` lists the repo-relative paths.

The part list is read from the main script, so adding a part needs no change here.
"""
from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MAIN = "src/client/WeatherVisuals.client.luau"
_PART = re.compile(r"^local \w+=require\(script\.Parent\.(Weather\w+)\)\s*$", re.M)


def read(path: str | Path, root: Path = ROOT) -> str:
    return (root / path).read_text(encoding="utf-8")


def parts(root: Path = ROOT) -> list[str]:
    """Module names (files under src/client) the main script requires, in require order."""
    return _PART.findall(read(MAIN, root))


def main_text(root: Path = ROOT) -> str:
    return read(MAIN, root)


def parts_text(root: Path = ROOT) -> str:
    return "\n".join(read(f"src/client/{name}.luau", root) for name in parts(root))


def weather_text(root: Path = ROOT) -> str:
    """WeatherVisuals.client.luau followed by every part, one string (line endings normalised to LF)."""
    return main_text(root) + "\n" + parts_text(root)


def files(root: Path = ROOT) -> list[str]:
    """Repo-relative paths of the main script and every part."""
    return [MAIN] + [f"src/client/{name}.luau" for name in parts(root)]
