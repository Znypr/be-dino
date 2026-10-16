"""Print the Studio command-bar snippet that starts a shot list on the client DemoDirector (docs/133).

    python tools/demo/run_shot.py hatching_showcase [--aspect 9:16]

Run the printed line in the CLIENT command bar (or the Roblox Studio MCP execute_luau on the client) while playtesting with
Config.DemoDirectorEnabled = true locally. The snippet is the only link between a shot file and Studio; nothing is published.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SHOTS = Path(__file__).resolve().parent / "shots"


def snippet(name: str, aspect: str | None = None) -> str:
    data = json.loads((SHOTS / f"{name}.json").read_text(encoding="utf-8"))
    if aspect:
        data["aspect"] = aspect
    payload = json.dumps(data, separators=(",", ":"))
    if "]==]" in payload:
        raise ValueError("shot list contains a Lua long-bracket terminator")
    return f'game.Players.LocalPlayer:WaitForChild("BeDinoDemoShot").Value = [==[{payload}]==]'


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", nargs="?", help="shot list file name without .json")
    ap.add_argument("--aspect", choices=["16:9", "9:16"])
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list or not args.name:
        print("\n".join(sorted(p.stem for p in SHOTS.glob("*.json"))))
        return 0
    print(snippet(args.name, args.aspect))
    return 0


if __name__ == "__main__":
    sys.exit(main())
