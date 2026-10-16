"""BD-306/BD-309: offline guards for the low-poly bake budget and fallback chain.
Measured in a Play client (docs/105 s3): EditableImage and EditableMesh share ONE 80 MiB budget per client; a mesh costs about
1 KiB per face. So the bakes are sized per part (body/head 256 px, others 128 px), the caps are checked in BYTES against the
budget, no EditableMesh may be kept alive, source reads are throttled, a nil image/mesh fails the bake (never blank), failed
reads retry, Bootstrap gains no locals and the flag stays off. Pure parts of the pipeline are covered by
tools/verify_lowpoly_patterns.py; the byte maths here runs in the pinned Luau runtime too."""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]


def module(path):
    return '(function()\n' + (ROOT / path).read_text(encoding='utf-8') + '\nend)()'


BODY = r'''
-- a distinct dino = 2 big + 5 small bakes (7 parts); 24 such dinos must fit the caps with nothing on the tint
local dinoMiB = (2 * BIG * BIG + 5 * SMALL * SMALL) * 4 / 1048576
assert(dinoMiB < 1, "a dino costs " .. dinoMiB .. " MiB")
assert(BIGCAP >= 2 * 24 and SMALLCAP >= 5 * 24, "caps hold 24 distinct dinos")
local capMiB = (BIGCAP * BIG * BIG + SMALLCAP * SMALL * SMALL) * 4 / 1048576
local inFlight = MAXREADS * (4 + 5.5) -- 1024 px source image + the biggest transient position-map mesh (5,524 faces)
assert(capMiB + inFlight <= BUDGET / 2, string.format("bakes %.1f + reads %.1f MiB over half the %d MiB budget", capMiB, inFlight, BUDGET))
assert(MAXREADS >= 1 and MAXREADS <= 3, "read throttle")
-- the cache never exceeds its cap and a full cache denies instead of blanking (PatternAtlasCache contract)
local c = Cache.new(3, function() end)
for i = 1, 3 do assert(c:reserve()) c:insert("k" .. i, {}) end
assert(not c:reserve() and c.denied == 1 and c.live == 3)
print("lowpoly budget maths passed")
'''


def static_checks():
    tex = (ROOT / 'src/shared/LowPolyTexture.luau').read_text(encoding='utf-8')
    code = '\n'.join(line for line in tex.splitlines() if not line.strip().startswith('--'))
    assert 'CreateMeshPartAsync' not in code and 'ApplyMesh' not in code, "no remapped meshes: an EditableMesh shares the image budget"
    assert re.search(r'mesh:Destroy\(\)\s*\n\s*return tris', tex), "the position-map mesh must be transient (destroyed before returning)"
    assert 'if not img then error("no image' in tex and 'if not mesh then error("no mesh' in tex, "nil image/mesh (budget or permission) must fail the read"
    assert 'if not img then return nil end' in tex, "nil bake image must deny, never blank"
    assert 'failedAt = os.clock()' in tex and 'Texture.RetryAfter' in tex, "failed reads retry later"
    assert 'while reading >= Texture.MaxReads do task.wait' in tex, "source reads throttled"
    assert 'LowPolyDenyEditable' in tex and 'denied("mesh")' in tex and 'denied("image")' in tex, "BD-309 deny hook for both APIs"
    assert 'Cache.new(Texture.BigCap' in tex and 'Cache.new(Texture.SmallCap' in tex and 'Destroying:Once' in tex
    key = re.search(r'function Texture\.key\(textureId: string, spec: Spec\): string\n(.*?)\nend', tex, re.S).group(1)
    for field in ("textureId", "spec.patternId", "spec.primary", "spec.secondary", "spec.same", "spec.primaryShare", "spec.tier"):
        assert field in key, f"cache key ignores {field}"
    assert 'Texture.key(textureId, spec) .. "@" .. size' in tex, "bakes of different sizes never share an image"
    dinos = (ROOT / 'src/shared/LowPolyDinos.luau').read_text(encoding='utf-8')
    assert 'Texture.sizeFor(role)' in dinos, "parts baked at their role size"
    assert 't.part.TextureID = t.textureId' in dinos and 'tintColor(' not in dinos, "tint fallback keeps the model's own texture (MeshPart.Color is ignored on textured parts)"
    assert 'not motionEnabled()' in dinos, "BD-308 Reduce Motion: no sparkle"
    assert 'own = true' in dinos and 'if spec.own then' in tex and '"|own"' in tex, "a fused tier without genes still bakes over the species' own colour (Index / fusion tiles, BD-326)"
    assert 'Enum.Material.Plastic, 0' in dinos and 'Tier.MaxReflectance' in dinos
    for name in ('LowPolyAtlasMesh', 'LowPolyAtlasLayout'):
        assert not (ROOT / f'src/shared/{name}.luau').exists(), f"{name} was measured and rejected (docs/105 s3)"
    config = (ROOT / 'src/shared/Config.luau').read_text(encoding='utf-8')
    assert re.search(r'^\s*LowPolyDinos = false,', config, re.M), "Config.LowPolyDinos must default to false"
    boot = (ROOT / 'src/client/Bootstrap.client.luau').read_text(encoding='utf-8')
    assert 'LowPoly' not in boot, "Bootstrap must not gain low-poly locals"
    return {
        'BIG': int(re.search(r'Texture\.BigSize = Pattern\.Size', tex) and 256),
        'SMALL': int(re.search(r'Texture\.SmallSize = (\d+)', tex).group(1)),
        'BIGCAP': int(re.search(r'Texture\.BigCap = (\d+)', tex).group(1)),
        'SMALLCAP': int(re.search(r'Texture\.SmallCap = (\d+)', tex).group(1)),
        'BUDGET': int(re.search(r'Texture\.BudgetMiB = (\d+)', tex).group(1)),
        'MAXREADS': int(re.search(r'Texture\.MaxReads = (\d+)', tex).group(1)),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    values = static_checks()
    pattern = (ROOT / 'src/shared/LowPolyPattern.luau').read_text(encoding='utf-8')
    assert re.search(r'Pattern\.Size = 256', pattern)
    head = ''.join(f'local {k}={v}\n' for k, v in values.items())
    src = head + 'local Cache=' + module('src/shared/PatternAtlasCache.luau') + '\n' + BODY
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'lowpoly_budget.luau'
        path.write_text(src, encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)
    print("low-poly bake budget + fallback guards ok")
