"""BD-400 / BD-401 palette check (docs/114 s5.3, owner 2026-10-16): shop / currency crystals are amber, never blue-purple.
Runs the real CaveHubProps, CaveLightingRules and AssetPalette in Luau. Checks: every currency crystal key (AssetPalette.Currency, the
hub_crystal_* meshes) has a flat Warm override with an amber hue (30-60 degrees, saturation >= 0.6, value >= 0.7); the crystal light colour
on the Style Grotto is amber; no shop station rows use the decoration crystal (rock_crystal); CaveProps applies the Warm override.
Decoration crystals (rock_crystal) are exempt and may stay lavender.
"""
from pathlib import Path
import argparse, subprocess, tempfile
ROOT = Path(__file__).resolve().parents[1]


def wrapped(path, prefix=''):
    return '(function()\n' + prefix + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


LUAU = r'''
local function hsv(c)
    local r,g,b=c[1]/255,c[2]/255,c[3]/255
    local mx,mn=math.max(r,g,b),math.min(r,g,b) local d=mx-mn
    local h=0
    if d>0 then
        if mx==r then h=60*(((g-b)/d)%6) elseif mx==g then h=60*((b-r)/d+2) else h=60*((r-g)/d+4) end
    end
    return h,(if mx==0 then 0 else d/mx),mx
end
local function amber(c,what)
    local h,s,v=hsv(c)
    assert(h>=30 and h<=60 and s>=.6 and v>=.7,string.format("%s %s,%s,%s is not amber (hue %.0f sat %.2f val %.2f)",what,c[1],c[2],c[3],h,s,v))
end
local n=0
for key in AP.Currency do
    if string.find(key,"crystal") then
        local warm=Props.Warm[key]
        assert(warm,key.." is a shop crystal and needs an amber Warm override (BD-400)")
        amber(warm.color,key) n+=1
    end
end
assert(n>=2,"hub_crystal_s and hub_crystal_l are covered")
amber(Rules.CrystalColor,"CaveLightingRules.CrystalColor (Style Grotto light)")
assert(not AP.Currency.rock_crystal and AP.DecorCrystal.rock_crystal,"rock_crystal stays decoration")
print("shop crystals amber:",n)
-- BD-546: the Crystals tab view follows the SAME flag the server reads (Config.CrystalPacksEnabled == true). Off, nil or any junk = one
-- Coming soon card and no R$ button; only a real true shows the pack grid.
for _,off in {false,nil,0,1,"true","yes",{}} do assert(SCS.packsView(off)==SCS.SoonView,"packs hidden unless exactly true: "..tostring(off)) end
assert(SCS.packsView(true)==SCS.PacksView and SCS.PacksView~=SCS.SoonView)
assert(SCS.SoonTitle=="Coming soon!" and #SCS.SoonLine<=40 and not string.find(SCS.SoonTitle..SCS.SoonLine,"R%$"),"soon card text is short and has no price")
print("crystals tab view: off = Coming soon card, on = packs")
'''


def static_crystals_tab(boot):
    """BD-546: while Config.CrystalPacksEnabled is off the Crystals tab draws NO R$ button. The branch decides by ShopCardState.packsView(Config.CrystalPacksEnabled),
    returns before the pack grid, the price lookup and every button exist, and R$ text can only come from ShopCardState.packButton (never a literal)."""
    start = boot.index('elseif cosmeticTab=="crystals" then')
    end = boot.index('require(script.Parent.ShopCards).forHeader', start)
    tab = boot[start:end]
    gate = tab.index('packsView(Config.CrystalPacksEnabled)')
    soon_return = tab.index('return', gate)
    grid = tab.index('local products=')
    assert gate < soon_return < grid, 'the Coming soon card returns before the pack grid is built'
    soon = tab[gate:soon_return]
    for banned in ('button(', 'packButton', 'R$', 'GetProductInfo', 'PromptProductPurchase', 'CrystalGrid'):
        assert banned not in soon, 'the Coming soon card must not draw a price button or look up prices: ' + banned
    assert 'cardRules.SoonTitle' in soon and 'cardRules.SoonLine' in soon, 'the card says the shared Coming soon text'
    assert 'Coming soon!' not in tab, 'no loose Coming soon line above R$ buttons'
    assert 'R$' not in tab, 'R$ text is only made by ShopCardState.packButton'
    assert tab.count('PromptProductPurchase') == 1 and 'Config.CrystalPacksEnabled==true' in tab, 'the purchase prompt stays gated by the flag too'
    repo = (ROOT / 'src/server/ProfileRepository.luau').read_text(encoding='utf-8')
    assert 'Config.CrystalPacksEnabled == true' in repo, 'the server reads the same flag the same way'
    cfg = (ROOT / 'src/shared/Config.luau').read_text(encoding='utf-8')
    assert 'CrystalPacksEnabled = false' in cfg, 'packs stay off for the playtest (docs/43)'
    print('crystals tab static: Coming soon card only while packs are off, no R$ button')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    args = ap.parse_args()
    parts = ['local script={Parent={}}', 'local Layout=' + wrapped('src/shared/CaveHubLayout.luau'),
             'local Props=' + wrapped('src/shared/CaveHubProps.luau'), 'local AP=' + wrapped('src/shared/AssetPalette.luau'),
             'local require=function() return Layout end', 'local Rules=' + wrapped('src/shared/CaveLightingRules.luau'),
             'local SCS=' + wrapped('src/shared/ShopCardState.luau'), LUAU]
    src = chr(10).join(parts)
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / 'c.luau'
        p.write_text(src, encoding='utf-8')
        out = subprocess.run([args.runner, str(p)], capture_output=True, text=True)
    print(out.stdout.strip())
    if out.returncode:
        raise SystemExit(out.stdout[-800:] + out.stderr[-1500:])
    cp = (ROOT / 'src/server/CaveProps.luau').read_text(encoding='utf-8')
    assert 'Props.Warm' in cp and 'mesh.Color = Color3.fromRGB(warm.color' in cp, 'CaveProps applies the amber override'
    layout = (ROOT / 'src/shared/CaveHubLayout.luau').read_text(encoding='utf-8')
    for line in layout.splitlines():
        if line.strip().startswith(('style =', 'potion =', 'shop =', 'crystals =')):
            assert 'rock_crystal' not in line, 'a shop station must not use the decoration crystal: ' + line.strip()[:60]
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text(encoding='utf-8')
    assert 'b.TextScaled=true' in boot and 'UITextSizeConstraint' in boot and 'packButton(nil)' in boot, 'BD-430: pack button text scales to fit, never "..."'
    assert 'button(card,"...",' not in boot, 'no "..." placeholder on a pack button'
    static_crystals_tab(boot)
    cue = (ROOT / 'src/client/GoCue.luau').read_text(encoding='utf-8')
    assert 'GoCueLabel' not in cue and 'SetAttribute("GoCue"' in cue and 'GoCueText' in boot, 'TAP TO GO! sits on the button face, no floating label'
    sm = (ROOT / 'src/client/SettingsMenu.luau').read_text(encoding='utf-8')
    assert 'if lab then break end' in sm, 'Sound lab page has no tab bar behind its BACK button'
    print('verify_shop_crystals passed')


if __name__ == '__main__':
    main()
