#!/usr/bin/env python3
"""BD-1261 soft blob shadow (Config.BlobShadowEnabled, src/shared/ContactShadowRules.luau Blob, docs/244 s2.14), owner 2026-11-17 phone test
("dino shadows are really low quality") and "Yes, build it" (first slice of the phone UI standard).

Runs the REAL ContactShadowRules in the pinned Luau runtime and checks: blobEnabled() needs BlobShadowEnabled; the blob is Roblox's built-in
glow.png; Decal transparency .25 on the ground and 1 (gone) 9 studs up; 1.25 x the BD-460 footprint, growing with VisualScale, NaN-safe.
Source guards: the flag ships false, is pinned off in the default profile, ON in the playtest profile and in the rehearsal list; the shadow
script reads the flag once and builds ONE blob part with ONE Decal only in newShadow (flag off: the three discs as before); Bootstrap.client is
untouched; docs/77 records the built-in texture; the before/after Studio close-ups exist.
Usage: python tools/verify_blob_shadow.py --runner luau.exe"""
from pathlib import Path
import argparse
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/evidence/2026-11-17-ui-world'
PICTURES = ('shadow-before.jpg', 'shadow-after.jpg')


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


LUAU = r'''
local fails = {}
local function check(ok, what) if not ok then table.insert(fails, what) end end
check(Shadow.blobEnabled({BlobShadowEnabled = true}) and not Shadow.blobEnabled({}) and not Shadow.blobEnabled(nil), "blob needs the flag")
check(Shadow.Blob.texture == "rbxasset://textures/glow.png", "built-in glow texture")
check(math.abs(Shadow.blobTransparency(1) - .25) < 1e-6 and Shadow.blobTransparency(0) == 1, "decal .25 on the ground, gone at 0")
check(Shadow.blobTransparency(Shadow.airborne(9)) == 1, "gone 9 studs up")
check(Shadow.blobTransparency(0 / 0) == 1, "nan opacity reads as gone")
local bw, bl = Shadow.blobSize(1, 1)
local fw, fl = Shadow.footprint(1)
check(math.abs(bw - 1.25 * fw) < 1e-6 and math.abs(bl - 1.25 * fl) < 1e-6, "1.25 x the footprint")
check(Shadow.blobSize(3, 1) > bw, "grows with the dino")
check(Shadow.blobSize(0 / 0, 1) == bw, "nan scale reads as 1")
check(Shadow.blobSize(1, .65) < bw, "smaller in the air")
if #fails > 0 then error("blob shadow FAILED:\n" .. table.concat(fails, "\n")) end
print("blob shadow passed")
'''


def scan(pictures=True):
    sys.path.insert(0, str(ROOT / 'tools'))
    import release_profiles as profiles
    cfg = read('src/shared/Config.luau')
    assert '    BlobShadowEnabled = false,\n' in cfg, 'the flag ships false'
    assert 'BlobShadowEnabled = true' in profiles.apply_profile(cfg, 'playtest')[0], 'ON in the playtest profile'
    assert 'BlobShadowEnabled' in [k for k, _ in profiles.REHEARSAL_ON], 'in the rehearsal list'
    assert profiles.verify_source(cfg, 'default').errors == [], 'default profile pins it off'
    shadow = read('src/client/ContactShadow.client.luau')
    assert 'local BLOB = Rules.blobEnabled(Config)' in shadow, 'the shadow reads the flag once'
    new = shadow[shadow.index('local function newShadow'):shadow.index('local function hide')]
    assert 'Instance.new("Decal")' in new and 'if BLOB then 1 else #Rules.Layers' in new, 'one blob part with a decal, built only in newShadow'
    assert shadow.count('Instance.new("Decal")') == 1, 'one decal'
    assert 'Blob' not in read('src/client/Bootstrap.client.luau'), 'no code in Bootstrap.client'
    reg = read('docs/77-asset-registry.md')
    assert '| contact_shadow_blob |' in reg and 'rbxasset://textures/glow.png' in reg, 'docs/77 records the built-in glow texture'
    if pictures:
        missing = [p for p in PICTURES if not (EVIDENCE / p).exists()]
        assert not missing, 'evidence pictures missing: ' + ', '.join(missing)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    scan()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'blob_shadow.luau'
        path.write_text('local Shadow=(function()\n' + read('src/shared/ContactShadowRules.luau') + '\nend)()\n' + LUAU, encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            sys.exit(1)
