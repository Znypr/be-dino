"""BD-1120: find the places in src/client that put a rarity (tier) word on screen, and say which of them use Shared/RarityWord.

A "site" is a line that reads a tier word out of a table or a text builder: rarityNames[...], SpeciesRarityNames[...], .tierName, a rarity chip's text,
the odds lines, a trait line, the toast text, the auto-open text, a card's rarity. A site is PAINTED when the word RarityWord appears within
WINDOW lines of it (the screen asked RarityWord to colour the word or to give the colour). Every other site must be listed in
tools/rarity_words_allow.json with a reason (a count per file, like the small-text allowance: a new unpainted site fails, a stale entry fails).
Used by tools/verify_rarity_words.py. Pure Python, no Luau.
"""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
ALLOW_PATH = ROOT / 'tools' / 'rarity_words_allow.json'
WINDOW = 10
PATTERNS = [
    r'rarityNames\[', r'SpeciesRarityNames\[', r'\.tierName\b', r'data\.chip\.text\b',r'ShopOdds\.lines', r'traitLine\(', r'\bentry\.text\b',
    r'autoOpenText\(\)', r'\binfo\.tier\b', r'\bcard\.rarity\b', r'\bitem\.rarity\b.*(Text|label)', r'oddsLine\(',
]
SITE = re.compile('|'.join('(?:%s)' % p for p in PATTERNS))


def sites(root=None):
    """{relative path: [(line number, painted, text)]} for every site in src/client."""
    base = Path(root or ROOT)
    out = {}
    for path in sorted((base / 'src' / 'client').glob('*.luau')):
        lines = path.read_text(encoding='utf-8').splitlines()
        for i, line in enumerate(lines):
            code = line.split('--')[0]
            if not SITE.search(code):
                continue
            near = '\n'.join(lines[max(0, i - WINDOW):i + WINDOW + 1])
            out.setdefault(path.relative_to(base).as_posix(), []).append((i + 1, 'RarityWord' in near, line.strip()[:110]))
    return out


def load_allow():
    data = json.loads(ALLOW_PATH.read_text(encoding='utf-8'))
    assert 'unpainted' in data, 'rarity_words_allow.json lost its "unpainted" section'
    for path, item in data['unpainted'].items():
        assert item.get('reason') and isinstance(item.get('count'), int), 'unpainted entry %s needs "count" and a reason' % path
    return data


def check(allow, found=None):
    found = sites() if found is None else found
    problems = []
    declared = allow['unpainted']
    for path, rows in sorted(found.items()):
        loose = [r for r in rows if not r[1]]
        if loose and path not in declared:
            problems.append('%s:%d prints a rarity word without RarityWord (%s): paint it with RarityWord.set / apply / paintLabel, or list the file in tools/rarity_words_allow.json with a reason' % (path, loose[0][0], loose[0][2]))
        elif path in declared and declared[path]['count'] < len(loose):
            problems.append('%s has %d unpainted rarity site(s), the allowance says %d: new rarity text must use RarityWord (first one: line %d)' % (path, len(loose), declared[path]['count'], loose[0][0]))
        elif path in declared and declared[path]['count'] > len(loose):
            problems.append('%s has only %d unpainted rarity site(s), the allowance says %d: lower it in tools/rarity_words_allow.json' % (path, len(loose), declared[path]['count']))
    for path in declared:
        if not [r for r in found.get(path, []) if not r[1]]:
            problems.append('tools/rarity_words_allow.json lists %s but it has no unpainted rarity site any more: remove the entry' % path)
    return problems


if __name__ == '__main__':
    for path, rows in sites().items():
        for line, painted, text in rows:
            print('%-40s %4d %-9s %s' % (path, line, 'painted' if painted else 'UNPAINTED', text))
