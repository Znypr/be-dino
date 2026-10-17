#!/usr/bin/env python3
"""BD-004 id slot check (docs/148): tools/release_ids.json is the one place the owner's answer is recorded.

    python tools/verify_release_ids.py                   # CI: the slot is well formed (empty is allowed)
    python tools/verify_release_ids.py --require-filled  # release gate: fails while an id is empty

Slot fields: PlaytestUniverseId, PlaytestPlaceId (null or a positive integer), ExperienceKind ("new" or "legacy", required once the
ids are filled) and AnsweredOn (free text date).

When the ids are filled:
  * src/shared/Config.luau must hold the same two numbers (the build embeds Config's values, not the slot's);
  * if they belong to the LEGACY experience (ExperienceKind "legacy", or the ids docs/55 s2 names as legacy) and
    Config.DeveloperProducts still lists Robux product ids, that is a HARD STOP (docs/145 finding 6): flags only hide the
    prompts, a real developer product in a friends experience is still a paid-random and no-Robux-line breach.
    Clear the product ids (or remove the products in Creator Hub) first. Nothing here changes any id.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_profiles  # noqa: E402

SLOT_PATH = ROOT / "tools/release_ids.json"
CONFIG_PATH = ROOT / "src/shared/Config.luau"
# docs/55 s2 calls these two numbers the LEGACY private test experience (docs/42). The owner has not yet answered BD-004.
LEGACY_UNIVERSE_ID = 10769812255
LEGACY_PLACE_ID = 111259822927673
KINDS = ("new", "legacy")
FIELDS = ("PlaytestUniverseId", "PlaytestPlaceId", "ExperienceKind", "AnsweredOn")


def _is_id(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def load_slot(path: Path = SLOT_PATH) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must hold a JSON object")
    return data


def developer_product_ids(config_source: str) -> list[int]:
    value = release_profiles.config_entries(config_source).get("DeveloperProducts", [(0, None)])[-1][1]
    if value in (None, {}):
        return []
    return [int(n) for n in re.findall(r"\[(\d+)\]", str(value))]


def slot_state(slot: dict) -> str:
    """'empty', 'partial' or 'filled'."""
    present = [_is_id(slot.get("PlaytestUniverseId")), _is_id(slot.get("PlaytestPlaceId"))]
    return "filled" if all(present) else "empty" if not any(present) else "partial"


def slot_problems(slot: dict, config_source: str, require_filled: bool = False) -> tuple[list[str], list[str]]:
    """(errors, warnings). Pure: takes the parsed slot and the Config source text."""
    errors: list[str] = []
    warnings: list[str] = []
    for key in sorted(set(slot) - set(FIELDS) - {"_readme"}):
        errors.append(f"release_ids.json: unknown field {key!r}")
    for key in ("PlaytestUniverseId", "PlaytestPlaceId"):
        value = slot.get(key)
        if value is not None and not _is_id(value):
            errors.append(f"release_ids.json: {key} must be null or a positive integer, got {value!r}")
    kind = slot.get("ExperienceKind")
    if kind is not None and kind not in KINDS:
        errors.append(f"release_ids.json: ExperienceKind must be null, 'new' or 'legacy', got {kind!r}")
    if errors:
        return errors, warnings
    state = slot_state(slot)
    if state == "partial":
        errors.append("release_ids.json: only one of PlaytestUniverseId / PlaytestPlaceId is filled; record both")
        return errors, warnings
    if state == "empty":
        if require_filled:
            errors.append("BD-004 is not answered: tools/release_ids.json has empty PlaytestUniverseId / PlaytestPlaceId. "
                          "The owner must say which experience is the playtest one (docs/148 step 1), then the lead fills the slot "
                          "and the same two numbers in src/shared/Config.luau")
        return errors, warnings
    universe, place = slot["PlaytestUniverseId"], slot["PlaytestPlaceId"]
    if kind is None:
        errors.append("release_ids.json: ExperienceKind is empty; say 'new' or 'legacy' (the owner's BD-004 answer)")
    entries = release_profiles.config_entries(config_source)
    for key, wanted in (("PlaytestUniverseId", universe), ("PlaytestPlaceId", place)):
        actual = entries.get(key, [(0, None)])[-1][1]
        if actual != wanted:
            errors.append(f"Config.{key} = {actual!r} but release_ids.json says {wanted}: the build embeds Config's value; "
                          "change src/shared/Config.luau to match in the same PR (no other id may change)")
    is_legacy_id = universe == LEGACY_UNIVERSE_ID or place == LEGACY_PLACE_ID
    if kind == "new" and is_legacy_id:
        errors.append(f"ExperienceKind is 'new' but the ids {universe} / {place} are the legacy experience of docs/55 s2: "
                      "one of the two statements is wrong, ask the owner again")
    products = developer_product_ids(config_source)
    if kind == "legacy" or is_legacy_id:
        if products:
            errors.append("HARD STOP (docs/145 finding 6): the playtest experience is the LEGACY one and Config.DeveloperProducts still lists "
                          f"{len(products)} Robux product id(s) ({', '.join(str(p) for p in products)}). Clear them in Config (owner decision) "
                          "or remove the products in Creator Hub before publishing: a real developer product in a friends experience "
                          "breaks the no-Robux line (docs/43, AGENTS.md)")
        else:
            warnings.append("the playtest experience is the LEGACY one: it may still OWN developer products on Roblox's side. In Creator Hub > "
                            "Monetization > Developer Products make sure none is for sale before publishing (docs/148 step 2)")
    elif products:
        warnings.append(f"Config.DeveloperProducts lists {len(products)} product id(s); inert in a new experience (it does not own them). "
                        "Do not create developer products there")
    return errors, warnings


def check(slot_path: Path = SLOT_PATH, config_path: Path = CONFIG_PATH, require_filled: bool = False) -> tuple[list[str], list[str], str]:
    slot = load_slot(slot_path)
    errors, warnings = slot_problems(slot, config_path.read_text(encoding="utf-8"), require_filled)
    return errors, warnings, slot_state(slot)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--require-filled", action="store_true", help="fail while the BD-004 ids are empty (the release gate)")
    parser.add_argument("--slot", type=Path, default=SLOT_PATH)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    args = parser.parse_args(argv)
    errors, warnings, state = check(args.slot, args.config, args.require_filled)
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"Release id slot FAILED ({state}): {len(errors)} error(s).")
        return 1
    print(f"Release id slot ok ({state}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
