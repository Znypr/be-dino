"""BD-175 egg memory view model (src/shared/EggOrigin.luau) with the pinned Luau runtime, plus static wiring guards for
the Eggs page redesign (BD-169) and the egg icon bindings (BD-176). Drawing is Studio-only."""
from pathlib import Path
import argparse
import json
import re
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]


def module(path):
    text = (ROOT / path).read_text(encoding='utf-8')
    text = re.sub(r'require\(script\.Parent\.(\w+)\)', r'MOD_\1', text)
    return '(function()\n' + text + '\nend)()'


BODY = r'''
local O, Sel = MOD_EggOrigin, MOD_FusionSelection
local catalog = Sel.buildCatalog(MOD_Config, MOD_ProgressionConfig, MOD_EggGenetics.Patterns)
local function cond(id) local c = MOD_EggGenetics.condition(id) return if c then c.name else nil end
local egg = {kind = "run_egg", readyAt = 1792000000, source = {kind = "run"},
    genes = {conditionId = "rainbow", primaryColorId = "white", secondaryColorId = "white", blend = 100, hatchSuccess = true, patternId = "01_blank"}}
local v = O.view({origin = {kind = "hatch", eggId = "e1"}, originalEgg = egg}, catalog, Sel, cond)
assert(v.kind == "egg" and v.conditionId == "rainbow" and v.source == "Run egg" and v.when ~= nil, "hatched copy shows its egg")
assert(v.lines[1] == "Egg look: " .. cond("rainbow") and v.lines[2] == "From: Run egg")
egg.source = {kind = "nest"} egg.kind = "nest_egg"
assert(O.view({origin = {kind = "hatch"}, originalEgg = egg}, catalog, Sel, cond).source == "Nest egg")
assert(O.view({origin = {kind = "legacy_unknown"}}, catalog, Sel, cond).title == "Unknown egg", "older copies: Unknown egg")
assert(O.view({origin = {kind = "hatch"}}, catalog, Sel, cond).kind == "unknown", "hatch without saved egg: Unknown egg")
assert(O.view(nil, catalog, Sel, cond).kind == "unknown")
assert(O.view({origin = {kind = "fusion"}}, catalog, Sel, cond).kind == "fusion")
assert(O.dateText(nil) == nil and O.dateText("x") == nil and O.dateText(5) == nil and O.dateText(0 / 0) == nil)
assert(O.dateText(1792000000) == "Oct 14, 2026", O.dateText(1792000000))
assert(O.view({origin = {kind = "hatch"}, originalEgg = egg, mutationId = "dewdrop"}, catalog, Sel, cond).mutationId == "dewdrop", "BD-352 mutation on view")
assert(O.view({origin = {kind = "hatch"}, originalEgg = egg, mutationId = ""}, catalog, Sel, cond).mutationId == nil)
assert(O.view({origin = {kind = "fusion"}, mutationId = "dewdrop"}, catalog, Sel, cond).mutationId == "dewdrop")
print("Egg origin checks passed")
'''


def script():
    out = ''
    for name in ['Config', 'ProgressionConfig', 'EggGenetics', 'FusionSelection', 'EggOrigin']:
        out += 'local MOD_%s=%s\n' % (name, module('src/shared/%s.luau' % name))
    return out + BODY


def static_checks():
    data = json.loads((ROOT / 'resources/ui/v2/icons/upload-bindings.json').read_text())
    ids = {a['key']: a.get('robloxAssetId') for a in data['assets']}
    assert ids['egg_green'] and ids['egg_nest_single'], 'egg icons are bound'
    assert 'eggs = "egg_green"' in (ROOT / 'src/shared/NavigationArtwork.luau').read_text()
    screen = (ROOT / 'src/client/EggsScreen.luau').read_text()
    assert 'egg_nest_single' in screen and 'EggPicture.add' in screen
    assert 'ViewportFrame' not in screen and 'EggPlaceholder' not in screen, 'no plain ellipse / 3D box on the Eggs page'
    panels = (ROOT / 'src/client/DinoIndexPanels.luau').read_text()
    assert 'EggPopup' in panels and '"egg_green"' in panels
    assert 'paintEggButton' in panels and 'EggPicture.baked(hit, genes, 40)' in panels, 'dex egg button shows the real original egg'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    static_checks()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'egg_origin.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)
