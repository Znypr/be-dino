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
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', required=True)
    args = ap.parse_args()
    parts = ['local script={Parent={}}', 'local Layout=' + wrapped('src/shared/CaveHubLayout.luau'),
             'local Props=' + wrapped('src/shared/CaveHubProps.luau'), 'local AP=' + wrapped('src/shared/AssetPalette.luau'),
             'local require=function() return Layout end', 'local Rules=' + wrapped('src/shared/CaveLightingRules.luau'), LUAU]
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
    print('verify_shop_crystals passed')


if __name__ == '__main__':
    main()
