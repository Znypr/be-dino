"""BD-1253 / BD-1254 (docs/243, owner 2026-11-17): menu windows in the top-game look behind Config.MenusTopLookEnabled.

Checks:
  * wiring: the flag ships false, is off in the default profile, on in the playtest profile, in the rehearsal list and the playtest manifest;
  * header colours: runs the REAL src/shared/ToyboxKit.luau with the pinned Luau runner. Flag off (no useTopLook) every place keeps the
    owner's 2026-11-13 colours; after Kit.useTopLook() the places follow the proposal sheet (green Shop, purple Potions and Fusion, blue Dinos,
    amber Eggs, dark Settings, green Home and Food guide, amber Go home? confirm);
  * scope: ToyboxLayout reads the flag once and darkens only inside a menu window (ModalScrim or FusionScrim); a tone() call without a host
    stays cream (the HUD, toasts and cues use it that way); ModalCompact lightens the cover only with the flag;
  * mutants: a wrong place colour or a window root that leaks to the HUD is caught.

    python tools/verify_menus_top_look.py --runner <luau.exe>
"""
from pathlib import Path
import argparse
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


BODY = r'''
local function slot(screen) return Kit.headerSlot(screen) end
-- flag off: the owner's places, unchanged
assert(slot("potions") == "toybox_header_green", "flag off: Potions green")
assert(slot("auras") == "toybox_header_amber", "flag off: Shop amber")
assert(slot("eggs") == "toybox_header_cream", "flag off: Eggs cream")
assert(slot("home") == "toybox_header_blue", "flag off: Home blue (dinos)")
assert(slot("exit") == "toybox_header_dark", "flag off: Go home? dark (settings)")
Kit.useTopLook()
local want = {potions = "purple", auras = "green", eggPurchase = "green", collection = "blue", detail = "blue", fusion = "purple",
    eggs = "amber", results = "amber", settings = "dark", home = "green", food = "green", exit = "amber"}
for screen, colour in want do
    assert(slot(screen) == "toybox_header_" .. colour, "top look: " .. screen .. " wants " .. colour .. ", got " .. slot(screen))
end
for _, colour in Kit.TopLookHeader do
    local known = false
    for _, c in Kit.HeaderColours do if c == colour then known = true end end
    assert(known, "top look uses a header the kit has: " .. colour)
    assert(colour ~= "red", "red stays for the X only")
end
print("MENUS_TOP_LOOK_KIT_OK")
'''


def kit_run(runner, kit_source):
    script = "local Kit = (function()\n" + kit_source + "\nend)()\n" + BODY
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "menus_top_look.luau"
        path.write_text(script, encoding="utf-8")
        r = subprocess.run([runner, str(path)], capture_output=True, text=True)
        return r.returncode == 0 and "MENUS_TOP_LOOK_KIT_OK" in r.stdout, (r.stdout + r.stderr)[-600:]


def static(layout, compact):
    errors = []
    if "local TOP = (require(script.Parent.Config) :: any).MenusTopLookEnabled == true" not in layout:
        errors.append("ToyboxLayout must read MenusTopLookEnabled once")
    if 'local WINDOW_ROOTS = {"ModalScrim", "FusionScrim"}' not in layout:
        errors.append("ToyboxLayout darkens only inside the two window roots")
    if "local useDark = if typeof(dark) == \"Instance\" then windowed(dark) else dark == true" not in layout:
        errors.append("tone(name) without a host must stay cream (HUD, toasts, cues)")
    if "if topLook and shade and shade:IsA(\"GuiObject\") then" not in compact or "M.TopLookCover = 0.82" not in compact:
        errors.append("ModalCompact lightens the cover only with the flag")
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runner", required=True)
    a = ap.parse_args()
    errors = []
    if "    MenusTopLookEnabled = false,\n" not in read("src/shared/Config.luau"):
        errors.append("Config.MenusTopLookEnabled must ship false")
    profiles = read("tools/release_profiles.py")
    if '_flag_off("MenusTopLookEnabled"' not in profiles or 'Rule("MenusTopLookEnabled", "set", True' not in profiles or '("MenusTopLookEnabled", "BD-1253' not in profiles:
        errors.append("MenusTopLookEnabled: off in default, on in playtest, in the rehearsal list")
    if '"MenusTopLookEnabled"' not in read("tools/release_playtest.py"):
        errors.append("the playtest manifest records MenusTopLookEnabled")
    for hud in ("src/client/HudToybox.luau", "src/client/HudCohesion.client.luau"):
        if "MenusTopLook" in read(hud):
            errors.append(hud + ": the HUD keeps its cream plates (no top look there)")
    kit = read("src/shared/ToyboxKit.luau")
    ok, out = kit_run(a.runner, kit)
    if not ok:
        errors.append("kit run failed: " + out)
    layout, compact = read("src/shared/ToyboxLayout.luau"), read("src/client/ModalCompact.luau")
    errors += static(layout, compact)
    # mutants: each must be caught
    caught = 0
    mutants = [
        ("Kit: Potions back to green", kit.replace('Kit.TopLookHeader = {shop = "green", potions = "purple"', 'Kit.TopLookHeader = {shop = "green", potions = "green"'), None),
        ("Kit: Go home? not mapped", kit.replace('exit = "confirm"}', '}'), None),
        ("Kit: red header used", kit.replace('confirm = "amber"}', 'confirm = "red"}'), None),
        ("Layout: HUD root leaks in", None, layout.replace('{"ModalScrim", "FusionScrim"}', '{"ModalScrim", "FusionScrim", "BeDinoUI"}')),
        ("Layout: host-less tone darkens", None, layout.replace('else dark == true', 'else TOP')),
    ]
    for name, mk, ml in mutants:
        if mk is not None:
            bad = not kit_run(a.runner, mk)[0]
        else:
            bad = bool(static(ml, compact))
        if bad:
            caught += 1
        else:
            errors.append("mutant not caught: " + name)
    if errors:
        print("\n".join(errors))
        raise SystemExit(1)
    print("Menus top look passed: wiring, header colours flag off and on (Luau), window-only dark body, %d mutants caught" % caught)


if __name__ == "__main__":
    main()
