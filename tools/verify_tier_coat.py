"""Tier coat templates (docs/115 "fused tier look", approach C): offline proof that the coat is authored at BUILD time and only cloned at runtime.

A SurfaceAppearance created by a script at runtime does not render in Roblox; one authored in the place and cloned does. Checks:
  1. Tier.Maps (real Luau table, pinned runtime) agrees with the build's reader (tools/tier_coat.py); every id is valid; every
     species key is a shipped low-poly species; emerald/diamond/other-species slots exist (empty is fine); raptor Gold is fully bound;
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

# the owner-approved test uploads (lead, 2026-10-16): raptor gold, per part
RAPTOR_GOLD = {
    'body_geom': '90178136236675', 'head_geom': '109694992867474', 'tail_geom': '72434414127601', 'leftarm_geom': '136130436024752',
    'rightarm_geom': '127842664163981', 'leftleg_geom': '110600068291712', 'rightleg_geom': '86375362214763',
}
SHARED = {'normal': '80731894232842', 'roughness': '96432641754187'}
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
for key in ('normal', 'roughness', 'metalness'):
    v = maps.get(key, '')
    if v and not tier_coat.valid_id(v):
        err(f'Tier.Maps.{key}: malformed asset id {v!r}')
for key, want in SHARED.items():
    if maps.get(key) != 'rbxassetid://' + want:
        err(f'Tier.Maps.{key} should be rbxassetid://{want}, is {maps.get(key)!r}')
if FAILED_METAL in repr(maps):
    err('the failed test metalness map 98581639691267 must not be bound')
for part, want in RAPTOR_GOLD.items():
    got = color.get('raptor', {}).get(part, {}).get('gold')
    if got != 'rbxassetid://' + want:
        err(f'raptor {part} gold should be rbxassetid://{want}, is {got!r}')
for sp, parts in color.items():  # emerald / diamond stay empty until their maps exist
    for part, tiers in parts.items():
        for tid in ('emerald', 'diamond'):
            if tiers.get(tid):
                err(f'{sp}.{part}.{tid} is bound; the shell look for it must be reviewed first')

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
    if len(want) != len(RAPTOR_GOLD):
        err(f'expected {len(RAPTOR_GOLD)} templates (raptor gold), the table yields {len(want)}')
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
if not re.search(r'if tpl then.*?tpl:Clone\(\)\.Parent = shell\s+end', dinos, re.S):
    err('LowPolyDinos must clone the template onto the shell only when one exists')
if 'ReplicatedStorage:FindFirstChild(Tier.TemplateFolder)' not in dinos or 'item:IsA("SurfaceAppearance")' not in dinos:
    err('coatTemplate must look in Tier.TemplateFolder and return nil when absent')
if 'Tier.UseGlowShells = false' not in tier_src:
    err('glow shells must stay OFF while the coat is tuned')
gold = re.search(r'gold = \{id = "gold".*?\n(?=    emerald)', tier_src, re.S).group(0)
if 'outline = {255, 230, 140}' not in gold or 'rimFill = 1' not in gold:
    err('Gold Highlight must be outline 255,230,140 with FillTransparency 1')
if 'entry.rimFill or Tier.HighlightFill, 0' not in dinos or 'Color3.fromRGB(o[1], o[2], o[3])' not in dinos:
    err('rim Highlight must use the entry outline / rimFill with OutlineTransparency 0')
for tid in ('emerald', 'diamond'):
    block = re.search(tid + r' = \{id = "' + tid + r'".*?\n(?=    \w+ = \{id|\})', tier_src, re.S).group(0)
    if 'outline =' in block or 'rimFill' in block:
        err(f'{tid} keeps its current rim look until its maps exist')
if 'Tier.regionColor' not in (ROOT / 'src/shared/LowPolyTexture.luau').read_text(encoding='utf-8'):
    err('horns / claws must stay painted in the solid tier ramp')

# 5. docs
reg = (ROOT / 'docs/77-asset-registry.md').read_text(encoding='utf-8')
for part, i in RAPTOR_GOLD.items():
    if i not in reg:
        err(f'docs/77 does not register raptor {part} gold {i}')
for i in SHARED.values():
    if i not in reg:
        err(f'docs/77 does not register shared map {i}')
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
print("SHARED|" .. Tier.Maps.normal .. "|" .. Tier.Maps.roughness .. "|" .. Tier.Maps.metalness)
print("NAME|" .. Tier.templateName("raptor", "body_geom", "gold") .. "|" .. Tier.TemplateFolder)
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
    lu_rows = sorted(l for l in lines if l.count('|') == 3 and not l.startswith(('SHARED', 'NAME')))
    if py_rows != lu_rows:
        err('build reader and Luau disagree on Tier.Maps.color')
    if f'SHARED|{maps["normal"]}|{maps["roughness"]}|{maps["metalness"]}' not in lines:
        err('build reader and Luau disagree on the shared maps')
    if f'NAME|{tier_coat.template_name("raptor", "body_geom", "gold")}|{tier_coat.FOLDER}' not in lines:
        err('Tier.templateName / TemplateFolder differ from tools/tier_coat.py')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    luau_check(parser.parse_args().runner)
    if errors:
        print('Tier coat check FAILED:\n  ' + '\n  '.join(errors))
        raise SystemExit(1)
    print(f'Tier coat OK: {len(want)} build-time SurfaceAppearance templates in {tier_coat.FOLDER}, runtime only clones, plain-shell fallback kept.')
