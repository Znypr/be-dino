"""BD-532 (docs/115 EG1): the playtest "BUY EGG" can never succeed, so the tile is greyed out BEFORE the tap, by the same rule the server uses.

Pure rule: src/shared/PaidRandomGate.luau (blocked / guards / ComingSoon), run in Luau for the full truth table.
Static wiring: ProfileRepository.progressionAction refuses buyEgg and upgradeCondition through that function only (no inline copy of the rule
left), the client (Bootstrap shop Eggs and Conditions tabs, ShopTiles landing subtitle) reads the SAME function with the same three inputs, a blocked
BUY EGG is a grey "Coming soon" button with no handler that opens the confirm, and the policy gate itself is NOT loosened (PaidRandomItemsEnabled stays
false, DeveloperProducts untouched, the server keeps the 'random_items_unavailable' refusal and the copy "Not available yet").
Run: python tools/verify_paid_random_gate.py --runner C:/path/to/luau.exe
"""
import argparse
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


LUAU = r'''
local Gate = (function()
''' + read('src/shared/PaidRandomGate.luau') + r'''
end)()
local products = {[1] = 500}
-- Robux products on sale: blocked unless the release gate is open AND the player is eligible.
assert(Gate.blocked(products, false, false) == true, "gate off, not eligible")
assert(Gate.blocked(products, false, true) == true, "gate off but eligible is still blocked")
assert(Gate.blocked(products, true, false) == true, "gate on, player not eligible")
assert(Gate.blocked(products, true, nil) == true, "gate on, eligibility unknown")
assert(Gate.blocked(products, true, true) == false, "gate on and eligible: allowed")
assert(Gate.blocked(products, "yes", "yes") == true, "only real booleans open the gate")
-- No Robux products on sale: nothing to gate.
assert(Gate.blocked({}, false, false) == false and Gate.blocked(nil, false, false) == false)
assert(Gate.guards("buyEgg") and Gate.guards("upgradeCondition"))
assert(not Gate.guards("buyAura") and not Gate.guards("buyPotion") and not Gate.guards("buyPerk"))
assert(Gate.ComingSoon == "Coming soon")
print("paid random gate: truth table ok")
'''


def static():
    gate = read('src/shared/PaidRandomGate.luau')
    for banned in ('game:GetService', 'Instance.new', 'workspace', 'require('):
        assert banned not in gate, 'PaidRandomGate stays pure: ' + banned
    repo = read('src/server/ProfileRepository.luau')
    body = repo[repo.index('function ProfileRepository.progressionAction'):]
    body = body[:body.index('local eggId=nil')]
    assert 'PaidRandomGate.guards(action) and PaidRandomGate.blocked(Config.DeveloperProducts, Config.PaidRandomItemsEnabled, PrivateState.get(player, "PaidRandomEligible"))' in body, \
        'progressionAction must refuse buyEgg / upgradeCondition through the shared gate'
    assert '"random_items_unavailable"' in body, 'the server refusal stays'
    assert 'next(Config.DeveloperProducts)' not in repo, 'no inline copy of the paid-random rule may remain on the server'
    assert 'local PaidRandomGate = require(ReplicatedStorage.Shared.PaidRandomGate)' in repo
    boot = read('src/client/Bootstrap.client.luau')
    assert 'PaidRandomGate.blocked(Config.DeveloperProducts,Config.PaidRandomItemsEnabled,require(script.Parent.PrivateState).get("PaidRandomEligible"))' in boot, \
        'the client must call the same function with the same three inputs as the server'
    assert 'next(Config.DeveloperProducts)' not in boot, 'no client copy of the rule'
    assert 'ShopTiles.info(p,ProgressionConfig.RandomEggPrice,num("Crystals"),randomBlocked)' in boot, 'the landing tile gets the blocked flag'
    block = boot[boot.index('if randomBlocked then -- BD-532: greyed out'):]
    block = block[:block.index('-- BD-391/405')]
    assert 'PaidRandomGate.ComingSoon' in block and 'C.card' in block and 'AutoButtonColor' in block, 'blocked BUY EGG is a grey Coming soon button'
    soon = block[:block.index('else')]
    assert 'open(' not in soon and 'transact(' not in soon, 'the greyed tile must not open the confirm or send anything'
    assert 'randomBlocked then upgradeText,upgradeOk=PaidRandomGate.ComingSoon,false' in boot, 'the condition upgrade shares the server gate'
    art = read('src/shared/ShopArt.luau')
    assert 'info.randomBlocked == 1 then "Coming soon"' in art, 'the landing tile subtitle says Coming soon'
    # the policy gate itself is not loosened
    config = read('src/shared/Config.luau')
    assert re.search(r'PaidRandomItemsEnabled = false', config), 'PaidRandomItemsEnabled must stay false'
    assert 'random_items_unavailable = "Not available yet"' in read('src/shared/NotifyQueue.luau'), 'server refusal copy untouched'
    doc = read('docs/115-decisions-log.md')
    assert re.search(r'\bEG1\b', doc), 'docs/115 records the lead decision EG1'
    print('paid random gate: static wiring ok (server and client use one function; policy gate not loosened)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'gate.luau'
        path.write_text(LUAU, encoding='utf-8')
        out = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        if out.returncode:
            raise SystemExit(out.stdout[-2000:] + out.stderr)
        print(out.stdout.strip())
    static()
