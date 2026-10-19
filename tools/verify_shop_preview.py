"""Execute the BD-142/BD-143/BD-083 pure rules (src/shared/ShopPreview.luau) with the pinned Luau runtime, and
statically check that the Fusion Menu and the shop cards never use text under 14 px (docs/72)."""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


BODY = r'''
local Config=Progression
local State=StateMod
-- speed words: no "x", no digits
for _,t in Config.Trails do
 local w=P.speedWords(t.speed)
 assert(not w:find("%d") and not w:find("x"),"speed words: "..w)
end
assert(P.speedWords(1)=="Normal speed" and P.speedWords(1.02)=="A little faster" and P.speedWords(1.08)=="Faster")
assert(P.speedWords(1.12)=="Much faster" and P.speedWords(1.18)=="Super fast")
-- rarity chips cover every rarity used by trails and auras
for _,list in {Config.Trails,Config.Auras} do for _,it in list do
 local c=P.rarityChip(it.rarity) assert(c.text==it.rarity and c.color==nil and P.RarityColors==nil,it.rarity)
end end
assert(P.rarityChip(nil).text=="Common")
-- icon slot: nil entries fall back to the live preview; only real asset ids pass
assert(Config.TrailIconAssetIds~=nil)
-- 2026-10-17: the ten icons are uploaded and bound; a trail icon is absent (live preview) OR one valid registered rbxassetid.
for _,t in Config.Trails do
 local got=P.trailIconId(Config.TrailIconAssetIds,t.id)
 assert(got==nil or (type(got)=="string" and got:match("^rbxassetid://%d+$")~=nil),"icon is empty or a valid id: "..t.id)
 assert(got==nil or got==Config.TrailIconAssetIds[t.id],"the helper returns the bound id unchanged: "..t.id)
end
assert(P.trailIconId({fern="rbxassetid://123"},"fern")=="rbxassetid://123")
assert(P.trailIconId({fern="junk"},"fern")==nil and P.trailIconId(nil,"fern")==nil)
-- trail card states
local fern=Config.Trails[2]
local locked=P.trailCard(fern,{owned=false,level=1})
assert(locked.kind=="locked" and locked.dim and locked.buttonText=="LEVEL 3" and locked.caption=="100 Crystals" and locked.levelText=="Level 3",locked.buttonText)
local buy=P.trailCard(fern,{owned=false,level=5})
assert(buy.kind=="normal" and buy.buttonText=="BUY" and buy.caption=="100 Crystals" and buy.levelText=="Level 3")
local owned=P.trailCard(fern,{owned=true,level=1})
assert(owned.kind=="owned" and owned.buttonText=="EQUIP" and owned.caption=="Owned" and not owned.dim)
local eq=P.trailCard(fern,{owned=true,equipped=true,level=9})
assert(eq.buttonText=="UNEQUIP" and eq.caption=="Equipped" and eq.tone=="equipped" and eq.equipped)
assert(P.trailCard(Config.Trails[1],{owned=true,level=1}).levelText=="Starter")
-- aura tiers and cards
assert(P.tierBadge("Common")=="T1" and P.tierBadge("Rare")=="T2" and P.tierBadge("Legendary")=="T3" and P.tierBadge("zzz")=="T1")
for i,a in Config.Auras do assert(P.auraTier(a.rarity)==i,a.id) end
local a=P.auraCard(Config.Auras[2],"Growth +35%",{owned=false})
assert(a.buttonText=="BUY" and a.growthText=="Growth +35%" and a.tier=="T2" and a.caption=="470 Crystals")
local ae=P.auraCard(Config.Auras[1],"Growth +15%",{owned=true,equipped=true})
assert(ae.caption=="Equipped" and ae.buttonText=="UNEQUIP")
assert(P.MinText>=14 and P.Touch>=44)
print("shop preview rules ok")
'''


def script():
    s = 'local Progression=' + module('src/shared/ProgressionConfig.luau') + '\n'
    s += 'local StateMod=' + module('src/shared/ShopCardState.luau') + '\n'
    s += 'script={Parent={ShopCardState="S"}}\nlocal _req=require\nrequire=function(_) return StateMod end\n'
    s += 'local P=' + module('src/shared/ShopPreview.luau') + '\n'
    return s + BODY


def static_text_sizes():
    """No hard-coded text size under 14 in the Fusion Menu, its widgets or the shop cards."""
    bad = []
    for path in ('src/client/FusionMenu.luau', 'src/client/ShopCards.luau'):
        for n, line in enumerate((ROOT / path).read_text(encoding='utf-8').splitlines(), 1):
            for m in re.finditer(r'W\.label\(.*?,\s*(\d+)(?:,\s*[\w.]+)*(?:,\s*true)?\)\s*$', line):
                if int(m.group(1)) < 14 and 'UDim2' not in m.group(1):
                    bad.append(f'{path}:{n} text size {m.group(1)}')
    widgets = (ROOT / 'src/client/FusionWidgets.luau').read_text(encoding='utf-8')
    if 'W.MinText = 14' not in widgets or 'maxSize, W.MinText' not in widgets:
        bad.append('FusionWidgets min text size is not 14')
    # QA 2026-10-16: dark text must not get a dark outline (GOLD / NEW GOLD / slot numbers became blobs).
    if 'if color == C.outline then' not in widgets or 'TextStrokeTransparency = 1' not in widgets:
        bad.append('FusionWidgets.label must drop the stroke for C.outline-coloured text')
    menu = (ROOT / 'src/client/FusionMenu.luau').read_text(encoding='utf-8')
    # The ScreenGui has no size when the grid is built, so the card size must come from the camera viewport.
    if 'CurrentCamera' not in menu or 'AbsoluteSize.Y < 520' in menu:
        bad.append('Fusion dino grid sizing must read workspace.CurrentCamera.ViewportSize')
    if 'Sel.sectionHeight(#section.chips' not in menu:
        bad.append('confirm-screen odds sections must be sized by Sel.sectionHeight (BD-344: heading + wrapped chip rows)')
    return bad


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    problems = static_text_sizes()
    for p in problems:
        print('FAIL', p)
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'shop_preview.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        print(result.stdout, end='')
        print(result.stderr, end='')
        raise SystemExit(1 if problems else result.returncode)
