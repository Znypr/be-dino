"""Tier coat templates (docs/115 "fused tier look", approach C): offline proof that the coat is authored at BUILD time and only cloned at runtime.

A SurfaceAppearance created by a script at runtime does not render in Roblox; one authored in the place and cloned does. Checks:
  1. Tier.Maps (real Luau table, pinned runtime) agrees with the build's reader (tools/tier_coat.py); every id is valid; every
     species key is a shipped low-poly species; other-species slots exist (empty is fine); the raptor Gold / Emerald / Diamond v2 maps are all bound;
     RoughnessMap is per tier (Gold shared crystal roughness, Emerald / Diamond gem roughness);
  2. the BUILT place has ReplicatedStorage.TierCoatTemplates with exactly one SurfaceAppearance per (species, part, tier) that has a
     ColorMap id, carrying ColorMap + NormalMap + RoughnessMap, MetalnessMap only when a valid id exists, AlphaMode Transparency;
  3. runtime code never creates a SurfaceAppearance with Instance.new (LowPoly*/tier files and every file that touches the tier shell);
  4. LowPolyDinos clones the template onto the shell, and keeps today's plain shell, rim Highlight, solid horns/claws and OFF glow when none exists;
  5. docs/77 registers every uploaded id, and docs/120 lists the missing metalness / emerald / diamond / other-species bakes.
"""
from pathlib import Path
import argparse
import importlib.util
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import tier_coat  # noqa: E402

errors = []


def err(msg):
    errors.append(msg)


tier_src = (ROOT / 'src/shared/LowPolyTier.luau').read_text(encoding='utf-8')
dinos = (ROOT / 'src/shared/LowPolyDinos.luau').read_text(encoding='utf-8')
maps = tier_coat.parse_maps(tier_src)
species = re.findall(r'^    ([a-z]+) = \{assetId', (ROOT / 'src/shared/LowPolyDinoAssets.luau').read_text(encoding='utf-8'), re.M)

# the owner-approved v2 uploads (lead, 2026-10-17): raptor gold / emerald / diamond, per part
RAPTOR = {
    'gold': {'body_geom': '113868438061791', 'head_geom': '119196351264262', 'tail_geom': '114805933076242', 'leftarm_geom': '108502097691899',
             'rightarm_geom': '74562471589272', 'leftleg_geom': '86776571809563', 'rightleg_geom': '132503186986022'},
    'emerald': {'body_geom': '91887976444107', 'head_geom': '139205170920711', 'tail_geom': '115308340243991', 'leftarm_geom': '115793210560706',
                'rightarm_geom': '135422632753928', 'leftleg_geom': '86333670904727', 'rightleg_geom': '122532010612751'},
    'diamond': {'body_geom': '103471745823320', 'head_geom': '103077245223921', 'tail_geom': '84005504864942', 'leftarm_geom': '84855073802443',
                'rightarm_geom': '71207892076730', 'leftleg_geom': '121179877021536', 'rightleg_geom': '110505346745303'},
}
# the superseded v1 gold ids: history only (docs/77), never in code
RAPTOR_GOLD_V1 = ['90178136236675', '109694992867474', '72434414127601', '136130436024752', '127842664163981', '110600068291712', '86375362214763']
NORMAL = '80731894232842'
ROUGHNESS = {'gold': '96432641754187', 'emerald': '134658233071230', 'diamond': '134658233071230'}  # gold: shared crystal; emerald / diamond: gem
FAILED_METAL = '98581639691267'  # the first test metalness map FAILED to fetch: it must never be bound

# 1. table sanity
if set(maps) != {'color', 'normal', 'roughness', 'metalness'}:
    err(f'Tier.Maps keys: {sorted(maps)}')
color = maps.get('color', {})
for sp in species:
    if sp not in color:
        err(f'Tier.Maps.color has no slot for species {sp} (add an empty one)')
for sp in color:
    if sp not in species:
        err(f'Tier.Maps.color.{sp} is not a shipped low-poly species')
for sp, parts in color.items():
    for part, tiers in parts.items():
        if sp == 'raptor' and set(tiers) != set(tier_coat.TIERS):
            err(f'raptor {part}: tier slots {sorted(tiers)} (want gold, emerald, diamond)')
        for tid, value in tiers.items():
            if tid not in tier_coat.TIERS:
                err(f'{sp}.{part}: unknown tier {tid}')
            if value and not tier_coat.valid_id(value):
                err(f'{sp}.{part}.{tid}: malformed asset id {value!r}')
for key in ('normal', 'metalness'):
    v = maps.get(key, '')
    if v and not tier_coat.valid_id(v):
        err(f'Tier.Maps.{key}: malformed asset id {v!r}')
if maps.get('normal') != 'rbxassetid://' + NORMAL:
    err(f'Tier.Maps.normal should be rbxassetid://{NORMAL}, is {maps.get("normal")!r}')
rough = maps.get('roughness')
if not isinstance(rough, dict) or set(rough) != set(tier_coat.TIERS):
    err(f'Tier.Maps.roughness must be a per-tier table {tier_coat.TIERS}, is {rough!r}')
else:
    for tid, want in ROUGHNESS.items():
        if rough.get(tid) != 'rbxassetid://' + want:
            err(f'Tier.Maps.roughness.{tid} should be rbxassetid://{want}, is {rough.get(tid)!r}')
    if rough['emerald'] != rough['diamond'] or rough['gold'] == rough['emerald']:
        err('gold keeps the shared roughness; emerald and diamond share the gem roughness')
if FAILED_METAL in repr(maps):
    err('the failed test metalness map 98581639691267 must not be bound')
for tid, by_part in RAPTOR.items():
    for part, want in by_part.items():
        got = color.get('raptor', {}).get(part, {}).get(tid)
        if got != 'rbxassetid://' + want:
            err(f'raptor {part} {tid} should be rbxassetid://{want}, is {got!r}')
for old in RAPTOR_GOLD_V1:
    if old in tier_src:
        err(f'the superseded v1 gold id {old} must not be in LowPolyTier.luau (history lives in docs/77)')
for sp, parts in color.items():  # only the raptor has bakes so far
    if sp != 'raptor' and any(i for tiers in parts.values() for i in tiers.values()):
        err(f'{sp} has a bound coat map; only the raptor has bakes (docs/120)')

# 2. the built place
spec = importlib.util.spec_from_file_location('packager', ROOT / 'tools/build.py')
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)
data, _ = packager.build()
root = ET.fromstring(data)
storage = [n for n in root.findall('Item') if n.attrib['class'] == 'ReplicatedStorage']
folders = [c for s in storage for c in s.findall('Item') if c.find("Properties/string[@name='Name']").text == tier_coat.FOLDER]
want = {t['name']: t for t in tier_coat.load_templates(ROOT)}
if len(folders) != 1:
    err(f'built place has {len(folders)} {tier_coat.FOLDER} folders in ReplicatedStorage (want 1)')
else:
    got = {}
    for sa in folders[0].findall('Item'):
        name = sa.find("Properties/string[@name='Name']").text
        if sa.attrib['class'] != 'SurfaceAppearance':
            err(f'{tier_coat.FOLDER}/{name} is a {sa.attrib["class"]}, not a SurfaceAppearance')
        if name in got:
            err(f'duplicate template {name}')
        got[name] = sa
    if set(got) != set(want):
        err(f'template names differ: missing {sorted(set(want) - set(got))}, extra {sorted(set(got) - set(want))}')
    n_want = sum(len(v) for v in RAPTOR.values())
    if len(want) != n_want or len(got) != n_want:
        err(f'expected {n_want} templates (raptor 7 parts x 3 tiers), the table yields {len(want)}, the place has {len(got)}')
    for name, sa in got.items():
        t = want.get(name)
        if not t:
            continue
        props = sa.find('Properties')
        urls = {c.attrib['name']: c.find('url').text for c in props.findall('Content')}
        for key in ('ColorMap', 'NormalMap', 'RoughnessMap', 'MetalnessMap'):
            if t[key]:
                if urls.get(key) != t[key]:
                    err(f'{name}.{key} is {urls.get(key)!r}, want {t[key]!r}')
            elif key in urls:
                err(f'{name} has {key} but no valid id exists')
        for key in ('ColorMap', 'NormalMap', 'RoughnessMap'):
            if key not in urls:
                err(f'{name} is missing {key}')
        if t and urls.get('RoughnessMap') != 'rbxassetid://' + ROUGHNESS[t['tier']]:
            err(f'{name}.RoughnessMap is {urls.get("RoughnessMap")!r}, want the {t["tier"]} roughness rbxassetid://{ROUGHNESS[t["tier"]]}')
        alpha = props.find("token[@name='AlphaMode']")
        if alpha is None or alpha.text != str(tier_coat.ALPHA_MODE_TRANSPARENCY):
            err(f'{name}: AlphaMode must be Transparency (1)')
    refs = [n.attrib['referent'] for n in root.iter('Item')]
    if len(refs) != len(set(refs)):
        err('duplicate referents in the built place')

# 3. no runtime-created SurfaceAppearance
creator = re.compile(r'Instance\s*\.\s*new\s*\(\s*["\']SurfaceAppearance["\']')
for path in sorted((ROOT / 'src').rglob('*.luau')):
    text = path.read_text(encoding='utf-8')
    scoped = path.name.startswith('LowPoly') or 'LPTierShell' in text or 'TierCoat' in text or 'Tier.Maps' in text
    if scoped and creator.search(text):
        err(f'{path.relative_to(ROOT)} creates a SurfaceAppearance with Instance.new (does not render at runtime; clone a build-time template)')
for forbidden in ('SurfaceAppearance.new', 'ColorMap =', 'ColorMap='):
    if forbidden in dinos:
        err(f'LowPolyDinos must not set {forbidden} (templates only)')

# 4. clone path + fallback + kept looks
tpl_call = dinos.find('local tpl = coatTemplate(')
plain = dinos.find('shell.Transparency = math.clamp(entry.shellTransparency')
if tpl_call < 0 or plain < 0 or plain > tpl_call:
    err('the plain translucent shell must be set first, then the template (fallback when none exists)')
if not re.search(r'if tpl then.*?local coat = tpl:Clone\(\).*?coat\.Parent = shell\s+end', dinos, re.S):
    err('LowPolyDinos must clone the template onto the shell only when one exists')
if 'ReplicatedStorage:FindFirstChild(Tier.TemplateFolder)' not in dinos or 'item:IsA("SurfaceAppearance")' not in dinos:
    err('coatTemplate must look in Tier.TemplateFolder and return nil when absent')
if 'Tier.UseGlowShells = false' not in tier_src:
    err('glow shells must stay OFF while the coat is tuned')
gold = re.search(r'gold = \{id = "gold".*?\n(?=    emerald)', tier_src, re.S).group(0)
if 'outline = {255, 225, 130}' not in gold:
    err('Gold Highlight must keep outline 255,225,130 (lead Studio tuning 2026-10-17)')
if 'entry.rimFill or Tier.HighlightFill, 0' not in dinos or 'Color3.fromRGB(o[1], o[2], o[3])' not in dinos:
    err('rim Highlight must use the entry outline / rimFill with OutlineTransparency 0')
for tid in ('gold', 'emerald', 'diamond'):  # all three use the template shell with an outline and a faint fill (the v2 maps carry the colour)
    block = re.search(tid + r' = \{id = "' + tid + r'".*?\n(?=    \w+ = \{id|\})', tier_src, re.S).group(0)
    if 'outline = {' not in block or 'rimFill = 0.85' not in block:
        err(f'{tid} needs an outline and rimFill = 0.85 (v2 maps carry the colour; the lead tunes the fill live)')
if 'Tier.regionColor' not in (ROOT / 'src/shared/LowPolyTexture.luau').read_text(encoding='utf-8'):
    err('horns / claws must stay painted in the solid tier ramp')

# 5. docs
reg = (ROOT / 'docs/77-asset-registry.md').read_text(encoding='utf-8')
for tid, by_part in RAPTOR.items():
    for part, i in by_part.items():
        if i not in reg:
            err(f'docs/77 does not register raptor {part} {tid} {i}')
for i in (NORMAL, *ROUGHNESS.values(), *RAPTOR_GOLD_V1):
    if i not in reg:
        err(f'docs/77 does not register shared map / v1 history id {i}')
checklist = (ROOT / 'docs/120-pending-owner-uploads-checklist.md').read_text(encoding='utf-8')
for needle in ('Tier.Maps.metalness', 'Tier.Maps.color.raptor', 'other species'):
    if needle not in checklist:
        err(f'docs/120 has no row mentioning {needle!r}')

# the pinned Luau runtime reads the real table: it must agree with the build's reader
LUA = r'''
local rows = {}
for species, parts in Tier.Maps.color do
    for part, tiers in parts do
        for tier, id in tiers do table.insert(rows, species .. "|" .. part .. "|" .. tier .. "|" .. id) end
    end
end
table.sort(rows)
print(table.concat(rows, "\n"))
print("SHARED|" .. Tier.Maps.normal .. "|" .. Tier.Maps.roughness.gold .. "|" .. Tier.Maps.roughness.emerald .. "|" .. Tier.Maps.roughness.diamond .. "|" .. Tier.Maps.metalness)
print("NAME|" .. Tier.templateName("raptor", "body_geom", "gold") .. "|" .. Tier.TemplateFolder)
-- the real low-poly part names carry brackets, quotes and spaces (lead Studio check 2026-10-17)
print("REAL|" .. Tier.templateName("raptor", '["body"]_geom', "gold") .. "|" .. Tier.templateName("raptor", '"left arm"_geom', "gold") .. "|" .. Tier.templateName("raptor", '"right leg"]_geom', "gold"))
'''


def luau_check(runner):
    src = 'local Tier=(function()\n' + tier_src + '\nend)()\n' + LUA
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / 'tier_coat.luau'
        p.write_text(src, encoding='utf-8')
        r = subprocess.run([runner, str(p)], capture_output=True, text=True, encoding='utf-8')
    if r.returncode:
        err('Luau could not run LowPolyTier: ' + r.stderr.strip()[:300])
        return
    lines = r.stdout.strip().split('\n')
    py_rows = sorted(f'{s}|{p_}|{t}|{i}' for s, parts in color.items() for p_, tiers in parts.items() for t, i in tiers.items())
    lu_rows = sorted(l for l in lines if l.count('|') == 3 and not l.startswith(('SHARED', 'NAME', 'REAL')))
    if py_rows != lu_rows:
        err('build reader and Luau disagree on Tier.Maps.color')
    r = maps['roughness']
    if f'SHARED|{maps["normal"]}|{r["gold"]}|{r["emerald"]}|{r["diamond"]}|{maps["metalness"]}' not in lines:
        err('build reader and Luau disagree on the shared maps')
    if 'REAL|raptor_body_geom_gold|raptor_leftarm_geom_gold|raptor_rightleg_geom_gold' not in lines:
        err('Tier.templateName must strip the brackets/quotes/spaces of real low-poly part names (no template would match in game)')
    if f'NAME|{tier_coat.template_name("raptor", "body_geom", "gold")}|{tier_coat.FOLDER}' not in lines:
        err('Tier.templateName / TemplateFolder differ from tools/tier_coat.py')


# Lead Studio tuning 2026-10-17: gold templates carry a warm Color tint (the v2 gold edge reads pale yellow without it)
if tier_coat.COAT_TINT.get('gold') != (255, 175, 45):
    err('gold coat tint must be 255,175,45 (lead Studio tuning)')
if 'tier_coat.COAT_TINT' not in (ROOT / 'tools/build.py').read_text(encoding='utf-8'):
    err('build.py must write the per-tier coat tint into the templates')


# Owner 2026-10-17: tier edges must glow (emissive mask from the coat ColorMap), all three tiers
_dinos = (ROOT / 'src/shared/LowPolyDinos.luau').read_text(encoding='utf-8')
_tier = (ROOT / 'src/shared/LowPolyTier.luau').read_text(encoding='utf-8')
if 'EmissiveMaskContent = Content.fromUri' not in _dinos or 'Tier.CoatGlow[entry.id]' not in _dinos:
    err('coat clone must set an emissive mask from its ColorMap (edge glow)')
for _t in ('gold', 'emerald', 'diamond'):
    if f'    {_t} = {{strength = 6' not in _tier:
        err(f'Tier.CoatGlow.{_t} strength 6 (lead Studio tuning)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    luau_check(parser.parse_args().runner)
    if errors:
        print('Tier coat check FAILED:\n  ' + '\n  '.join(errors))
        raise SystemExit(1)
    print(f'Tier coat OK: {len(want)} build-time SurfaceAppearance templates in {tier_coat.FOLDER}, runtime only clones, plain-shell fallback kept.')
