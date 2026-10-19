#!/usr/bin/env python3
"""BD-1121 (docs/202 R6): the rare-find announcement as two lines with no panel (flag Config.RareFindBannerEnabled).

The server still decides and rate-limits (tools/verify_rare_hatch.py proves the rules: best egg per window, 45 s per hatcher, 4 per 10 s per server, names cut, Secret
keeps no species name, a Cracked egg is never rare). This check covers the new LOOK and WORDS:
  1. the pure words and payload checks (RareHatch.findTitle / findLine / findFromPayload / findPlan) run in verify_rare_hatch.py;
  2. the geometry mock (tools/rare_find_banner_smoke.luau) runs the REAL RareFindBanner, RarityWord, TextStyle: two lines, no background anywhere, a huge outlined title,
     the rarity word in its colour, no player name, a secret keeps its name out, bad payloads draw nothing, fades only without Reduce Motion, it goes away, one at a time;
  3. the flag: false in Config and in the default profile, ON in the playtest profile, the old strip is what the client draws with the flag off or a bad payload,
     the server sends the extra fields only with the flag on (the old payload is unchanged) and never a secret's name;
  4. mutants put each defect back (a panel, a name, no colour, a fade under Reduce Motion, the flag ignored, a secret name sent) and the checks must fail.
NOT Studio evidence: no font, no drawing. Usage: python tools/verify_rare_find_banner.py --runner luau.exe [--no-mutants]
"""
from pathlib import Path
import argparse
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import text_style_floors as tf  # noqa: E402

BODY = 'tools/rare_find_banner_smoke.luau'
EXTRA = {'RareFindBanner': 'src/client/RareFindBanner.luau', 'RareHatch': 'src/shared/RareHatch.luau'}


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def smoke(runner, replacements=None):
    return tf.run_smoke(runner, replacements, [], BODY, EXTRA)


MUTANTS = {
    'the banner has a dark panel behind it again': {
        'RareFindBanner': [('label.Name, label.BackgroundTransparency, label.BorderSizePixel = name, 1, 0 -- NO panel', 'label.Name, label.BackgroundTransparency, label.BorderSizePixel = name, 0.15, 0')],
    },
    'the root frame has a background': {
        'RareFindBanner': [('root.Name, root.BackgroundTransparency, root.BorderSizePixel, root.Active = Banner.Name, 1, 0, false', 'root.Name, root.BackgroundTransparency, root.BorderSizePixel, root.Active = Banner.Name, 0.5, 0, false')],
    },
    'the sentence is plain text (the rarity word is not coloured)': {
        'RareFindBanner': [('    RarityWord.set(line, find.line) -- the rarity word in its colour (RichText, whole words, the rest escaped)\n', '')],
    },
    'the banner shows the old text with the player name': {
        'RareFindBanner': [('    RarityWord.set(line, find.line) -- the rarity word in its colour (RichText, whole words, the rest escaped)\n', '    line.Text = tostring(data.text)\n')],
    },
    'the title is small': {
        'RareFindBanner': [('Banner.TitleMax, Banner.LineMax = 56, 30', 'Banner.TitleMax, Banner.LineMax = 28, 30')],
    },
    'the title has no outline': {
        'RareFindBanner': [('    TextStyle.outlined(label, kind) -- font, kind tag and the dark outline (title: 3 px)\n', '')],
    },
    'Reduce Motion fades like everything else': {
        'RareHatch': [('    if calm then return {fadeIn = 0, hold = R.FindFade.hold, fadeOut = 0} end\n', '')],
    },
    'the banner never goes away': {
        'RareFindBanner': [('            if root.Parent then root:Destroy() end\n', '')],
    },
    'a new find stacks on the old one': {
        'RareFindBanner': [('    if current and current.Parent then current:Destroy() end\n', '')],
    },
    'the secret name is shown': {
        'RareHatch': [('if info.secret == true or info.kind == "secret" then return "A secret dino was found!" end', 'if info.secret == true or info.kind == "secret" then return "A secret dino was found: " .. tostring(speciesName) .. "!" end')],
    },
    'a species name with markup is accepted': {
        'RareHatch': [('or not string.find(name, "^[%w][%w %-\'%.]*$") then return nil end', 'then return nil end')],
    },
    'a payload without a tier still draws (the old payload gets a made-up tier)': {
        'RareHatch': [('        if type(tier) ~= "number" or tier ~= math.floor(tier) or tier < 1 or tier > #tierNames then return nil end\n        tierName = tierNames[tier]', '        tierName = tierNames[tier] or "Common"')],
    },
}


def static_checks():
    cfg = read('src/shared/Config.luau')
    assert re.search(r'^\s*RareFindBannerEnabled = false,', cfg, re.M), 'RareFindBannerEnabled ships false in Config'
    profiles = read('tools/release_profiles.py')
    assert '_flag_off("RareFindBannerEnabled"' in profiles, 'the default profile pins the flag off'
    assert 'Rule("RareFindBannerEnabled", "set", True' in profiles, 'the playtest profile sets it on (docs/157 standing rule)'
    assert '("RareFindBannerEnabled",' in profiles, 'the rehearsal list has it'
    assert '"RareFindBannerEnabled"' in read('tools/release_playtest.py'), 'the playtest manifest records it'
    svc = read('src/server/RareHatchService.luau')
    cli = read('src/client/RareHatchClient.client.luau')
    banner = read('src/client/RareFindBanner.luau')
    assert svc.count('Config.RareFindBannerEnabled == true') == 1 and 'else\n                            event:FireClient(other, {k = "all", kind = out.info.kind, text = out.text})' in svc, 'flag off = the old payload'
    assert 'if info.secret then nil else speciesName' in svc, 'a secret species name never goes out'
    assert cli.count('Config.RareFindBannerEnabled == true and FindBanner.show(') == 1 and 'banner(data.text, false)' in cli, 'flag off or a refused payload = the old strip'
    for needle in ('DisplayName', 'data.text', 'OnServerEvent', 'FireServer'):
        assert needle not in banner, 'the new look must not use ' + needle
    assert not re.search(r'rbxassetid://\d+', banner), 'no asset ids'
    assert 'RareFind' not in read('src/client/Bootstrap.client.luau'), 'Bootstrap stays out of it (local-register limit)'
    # the limits of RareHatch.luau are exactly the ones of BD-428 (this change must not loosen them)
    rare = read('src/shared/RareHatch.luau')
    for needle in ('R.Window = 3', 'R.Cooldown = 45', 'R.GlobalMax = 4', 'R.GlobalWindow = 10', 'R.MaxName = 20'):
        assert needle in rare, 'rate limit changed: ' + needle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    static_checks()
    print('Rare find wiring passed: flag off by default and in the default profile, on in the playtest profile, old strip with the flag off or a refused payload, no secret name sent, limits unchanged')
    ok, out = smoke(args.runner)
    print(out, end='')
    if not ok:
        raise SystemExit('rare-find banner smoke failed')
    if args.no_mutants:
        return
    from concurrent.futures import ThreadPoolExecutor
    names = list(MUTANTS)
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda n: smoke(args.runner, MUTANTS[n]), names))
    for name, (passed, _out) in zip(names, results):
        assert not passed, 'MUTANT SURVIVED (the rare-find smoke did not notice): ' + name
        print('  mutant caught: ' + name)
    print('Rare find banner passed: %d mutants caught' % len(MUTANTS))


if __name__ == '__main__':
    main()
