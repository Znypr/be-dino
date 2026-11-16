#!/usr/bin/env python3
"""BD-1227 / BD-1228 / BD-1229 / BD-1233 / BD-1225 (docs/242 gaps 14, 17, 18): rare hatch news, friend bonus, badges, codes and the group gift
chest, ambient sound per zone. Each behind its own flag (RareHatchNewsEnabled, FriendBonusEnabled, BadgesEnabled, CodesEnabled, ZoneAmbienceEnabled).

Runs the REAL pure modules (Shared/RareHatch, FriendBonus, BadgeTable, CodeRules, ZoneAmbience with the real WorldV3) in the pinned Luau runtime:
the news line names the hatcher by a cleaned display name, an Epic is news-only and ranks under a Legendary, a secret keeps its species out, the
client re-check refuses junk names / kinds / tiers; the friend bonus is 0 without a friend and at least 1 with one, capped; badge keys per hatch
and Index step, a 0 id is skipped; codes normalize, expire and rate-limit wrong tries; zone loops crossfade and go quiet off the island or in a menu.
Source guards: every flag ships false, is pinned off in the default profile, ON in the playtest profile and in the rehearsal list; the services
start only behind their flags; the settlement adds the friend bonus BEFORE its transaction and protected; badges only from the settled outcome,
protected; the code table is server-only and the client sends words only; `redeemedCodes` is additive (never written on load); no badge id is
hard-coded anywhere else; every zone loop id is listed in docs/77; client pieces are small own scripts (no Bootstrap or hatch file touched).
Usage: python tools/verify_social.py --runner luau.exe"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FLAGS = ['RareHatchNewsEnabled', 'FriendBonusEnabled', 'BadgesEnabled', 'CodesEnabled', 'ZoneAmbienceEnabled']


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


def module(text):
    return '(function()\n' + text + '\nend)()'


LUAU = r'''
local fails = {}
local function check(ok, what) if not ok then table.insert(fails, what) end end
local names = {"Common", "Uncommon", "Rare", "Epic", "Legendary"}

-- BD-1227 news
local leg = R.classify({speciesId = "tyrannosaurus"}, 5, false)
check(R.newsLine("Mia", leg, "Legendary", "T-Rex") == "Mia hatched a Legendary T-Rex!", "news line")
check(R.newsLine("Ann", {kind = "epic", shiny = true}, "Epic", "Raptor") == "Ann hatched an Epic Shiny Raptor!", "an Epic, Shiny word")
check(R.newsLine("Sam", {kind = "secret", secret = true}, nil, "Hidden") == "Sam found a secret dino!", "secret keeps the species out")
check(R.newsLine("\n\tBo\0b  ", leg, "Legendary", "T-Rex") == "Bob hatched a Legendary T-Rex!", "control characters dropped")
check(#R.newsLine(string.rep("x", 40), leg, "Legendary", "T-Rex") <= R.MaxChatLine, "name cut")
check(R.epicNews({speciesId = "ankylosaurus"}, 4) ~= nil and R.epicNews({speciesId = "ankylosaurus"}, 4).kind == "epic", "Epic is news")
check(R.epicNews({failed = true}, 4) == nil, "a Cracked egg is never news")
check(R.epicNews({}, 3) == nil and R.epicNews({}, 5) == nil, "only tier 4 is epic news (5 is classify's)")
check(R.EpicScore < leg.score, "a Legendary beats an Epic in one burst")
local good = {k = "all", kind = "legendary", tier = 5, species = "T-Rex", name = "Mia"}
local n = R.newsFromPayload(good, names)
check(n ~= nil and n.title == "RARE FIND!" and n.line == "Mia hatched a Legendary T-Rex!", "payload with a name")
check(R.newsFromPayload({k = "all", kind = "epic", tier = 4, species = "Ankylosaurus", name = "Mia"}, names).line == "Mia hatched an Epic Ankylosaurus!", "epic payload")
for _, bad in {"<b>x</b>", "", string.rep("a", 21), " lead", "a\nb", 7} do
    local p = table.clone(good) p.name = bad
    check(R.newsFromPayload(p, names) == nil, "junk name refused: " .. tostring(bad))
end
local p2 = table.clone(good) p2.kind = "hack"
check(R.newsFromPayload(p2, names) == nil, "unknown kind refused")
local p3 = table.clone(good) p3.tier = 9
check(R.newsFromPayload(p3, names) == nil, "bad tier refused")
check(R.findFromPayload({kind = "epic", tier = 4, species = "Ankylosaurus"}, names).line == "An Epic Ankylosaurus was found!", "epic also reads in the no-name look")

-- BD-1228 friend bonus
check(F.crystals(100, 10, false) == 0, "no friend, no bonus")
check(F.crystals(100, 10, true) == 10, "10 percent")
check(F.crystals(3, 10, true) == 1, "at least 1")
check(F.crystals(0, 10, true) == 0, "nothing earned, nothing added")
check(F.crystals(100, 500, true) == F.MaxPercent, "capped")
check(F.crystals(100, -5, true) == 0 and F.crystals(100, 0/0, true) == 0, "junk percent")
check(F.label(10) == "Friend bonus +10%" and F.label(0) == "", "chip words")
local friends = {["1:2"] = true}
local function isF(a, b) return friends[F.pairKey(a, b)] == true end
check(F.hasFriend(1, {1, 2, 3}, isF) and F.hasFriend(2, {1, 2}, isF), "friend found both ways")
check(not F.hasFriend(3, {1, 2, 3}, isF) and not F.hasFriend(1, {1}, isF), "alone or strangers: no bonus")

-- BD-1229 badges
for _, key in B.Order do check(B.Ids[key] == 0, "ids stay 0 until the owner creates them: " .. key) check(B.idOf(key) == nil, "0 id skipped: " .. key) end
check(B.idOf("welcome", {welcome = 123}) == 123 and B.idOf("welcome", {welcome = 1.5}) == nil, "id check")
local function has(list, key) return table.find(list, key) ~= nil end
local k1 = B.forHatch({speciesId = "compy"}, 1, 1, 22)
check(#k1 == 1 and k1[1] == "first_hatch", "a Common: first hatch only")
local k2 = B.forHatch({shiny = true, eventMutationId = "frost"}, 5, 10, 22)
for _, key in {"first_hatch", "first_rare", "first_epic", "first_legendary", "first_shiny", "first_mutant", "index_5", "index_10"} do check(has(k2, key), "earned: " .. key) end
check(not has(k2, "index_all"), "not all yet")
check(has(B.forHatch({}, 1, 22, 22), "index_all"), "every species")
check(#B.forHatch({failed = true}, 5, 22, 22) == 0, "a failed egg earns nothing")

-- BD-1233 codes
check(C.normalize(" be-dino ") == "BEDINO" and C.normalize("hatch") == "HATCH", "normalize")
check(C.normalize("") == nil and C.normalize("<script>") == nil and C.normalize(string.rep("A", 21)) == nil and C.normalize(5) == nil, "junk is no code")
check(C.state({crystals = 50}, 100) == "ok" and C.state({crystals = 50, endsAt = 50}, 100) == "expired" and C.state(nil, 1) == "wrong" and C.state({crystals = 0}, 1) == "wrong", "code state")
check(C.message("applied", 50) == "You got 50 crystals!" and C.message("nope") == C.Words.busy, "kid words")
local times = {}
for i = 1, C.MaxWrongPerMinute do local kept, ok = C.allowTry(times, i) times = kept check(ok, "try " .. i) table.insert(times, i) end
local _, allowed = C.allowTry(times, 20)
check(not allowed, "too many wrong tries")
local _, later = C.allowTry(times, 200)
check(later, "allowed again after a minute")
for _, w in C.Words do check(#w <= 40, "short words: " .. w) end

-- BD-1225 zone ambience
check(Z.zoneFor(W.CenterX + 150, W.CenterZ, W) == "meadow", "east = meadow")
check(Z.zoneFor(W.CenterX, W.CenterZ + 200, W) == "forest", "north = forest")
check(Z.zoneFor(W.CenterX - 200, W.CenterZ - 60, W) == "beach", "west-south-west = beach")
check(Z.zoneFor(W.CenterX + 2000, W.CenterZ, W) == "beach", "out at sea = waves")
local volc = math.rad(275)
check(Z.zoneFor(W.CenterX + 200 * math.cos(volc), W.CenterZ + 200 * math.sin(volc), W) == "volcano", "volcano sector")
check(Z.zoneFor(0, 0, nil) == nil, "no world, no zone")
check(Z.zoneFor(W.CenterX, W.CenterZ, W) == "meadow" and Z.zoneFor(W.CenterX + 30, W.CenterZ - 40, W) == "meadow", "the spawn plaza is the meadow, never the volcano")
for _, name in Z.Order do
    local loop = Z.Loops[name]
    check(loop ~= nil and loop.volume > 0 and loop.volume <= .25, "quiet loop: " .. name)
    check(Z.normalizeId(loop.id) ~= nil, "loop id set: " .. name)
end
local t = Z.targets("beach", true, "", true)
check(t.beach == Z.Loops.beach.volume and t.meadow == 0, "active zone only")
for _, off in {Z.targets("beach", false, "", true), Z.targets("beach", true, "eggs", true), Z.targets("beach", true, "", false), Z.targets(nil, true, "", true)} do
    for _, name in Z.Order do check(off[name] == 0, "quiet off the island / in a menu / sound off / no zone") end
end
local lvl = 0
for _ = 1, 10 do lvl = Z.step(lvl, .2, .1, .2) end
check(math.abs(lvl - .2 / Z.FadeSeconds) < 1e-6, "linear fade")
check(Z.step(.2, 0, 100, .2) == 0 and Z.step(0, .2, 100, .2) == .2, "fade clamps")

if #fails > 0 then for _, f in fails do print("FAIL: " .. f) end error("social checks failed") end
print("Social checks passed")
'''


def static_checks():
    errors = []
    config = read('src/shared/Config.luau')
    profiles = read('tools/release_profiles.py')
    for flag in FLAGS:
        if len(re.findall(r'^\s*%s = false,' % flag, config, re.M)) != 1:
            errors.append('%s must ship false, once, in Config' % flag)
        if '_flag_off("%s"' % flag not in profiles or 'Rule("%s", "set", True' % flag not in profiles or '("%s", "' % flag not in profiles:
            errors.append('%s: off in default, ON in playtest, in the rehearsal list' % flag)
    if 'GameGroupId = 0,' not in config:
        errors.append('GameGroupId stays 0 until the owner gives the group id')
    social = read('src/server/SocialServices.luau')
    for flag, svc in (('FriendBonusEnabled', 'FriendBonusService'), ('BadgesEnabled', 'BadgeAwardService'), ('CodesEnabled', 'CodeService')):
        if 'if Config.%s == true then require(script.Parent.%s)' % (flag, svc) not in social:
            errors.append('SocialServices must start %s only behind %s' % (svc, flag))
    for svc, flag in (('FriendBonusService', 'FriendBonusEnabled'), ('BadgeAwardService', 'BadgesEnabled'), ('CodeService', 'CodesEnabled')):
        first = read('src/server/%s.luau' % svc).split('function Service.start', 1)[1].split('\n')[1]
        if not ('if not enabled() or started then return' in first or 'if Config.%s ~= true then return nil end' % flag in first):
            errors.append('%s.start must return at once with %s off' % (svc, flag))
    eggs = read('src/server/ProfileEggs.luau')
    fb = eggs.find('require(script.Parent.FriendBonusService).bonusFor(player, outcome.crystals)')
    tx = eggs.find('store:UpdateAsync', eggs.find('function ProfileRepository.commitRunSettlement'))
    if fb < 0 or tx < 0 or fb > tx or 'pcall(function() return require(script.Parent.FriendBonusService)' not in eggs:
        errors.append('the friend bonus joins the run crystals before the settlement transaction, protected')
    if 'if Config.FriendBonusEnabled == true then' not in eggs:
        errors.append('friend bonus behind its flag in the settlement')
    publish = eggs.split('local function publishHatch', 1)[1].split('\nend\n', 1)[0]
    if 'if Config.BadgesEnabled == true then' not in publish or 'pcall(function()' not in publish:
        errors.append('badges only from publishHatch (the settled outcome), behind the flag, protected')
    for path in (ROOT / 'src').rglob('*.luau'):
        rel = str(path.relative_to(ROOT)).replace('\\', '/')
        text = re.sub(r'--[^\n]*', '', read(rel))
        if re.search(r'AwardBadge\(', text) and rel != 'src/server/BadgeAwardService.luau':
            errors.append('only BadgeAwardService awards badges: %s' % rel)
        if 'CodeTable' in text and not rel.startswith('src/server/'):
            errors.append('the code table is server-only: %s' % rel)
        if 'redeemedCodes' in text and rel not in ('src/server/ProfileCodes.luau', 'src/shared/Config.luau', 'src/shared/CodeRules.luau'):
            errors.append('redeemedCodes is written only by ProfileCodes: %s' % rel)
    codes = read('src/server/ProfileCodes.luau')
    if 'if Config.CodesEnabled ~= true then return false, "disabled" end' not in codes or 'if used[token] ~= nil then status = "already" return nil end' not in codes:
        errors.append('ProfileCodes: inert with the flag off, one use per token')
    if 'profile.redeemedCodes = used' not in codes or codes.count('profile.redeemedCodes =') != 1:
        errors.append('redeemedCodes is created only by an applied code')
    panel = read('src/client/GiftsPanel.client.luau')
    if 'crystals' in re.sub(r'--.*', '', panel).split('InvokeServer', 1)[1][:200].lower():
        errors.append('the client sends words only, never an amount')
    for client, flag in (('src/client/GiftsPanel.client.luau', 'CodesEnabled'), ('src/client/FriendBonusChip.client.luau', 'FriendBonusEnabled'),
                         ('src/client/ZoneAmbience.client.luau', 'ZoneAmbienceEnabled')):
        head = '\n'.join(read(client).split('\n')[:12])
        if 'if Config.%s ~= true' % flag not in head:
            errors.append('%s returns on its first lines with %s off' % (client, flag))
    zone = read('src/client/ZoneAmbience.client.luau')
    if 'Mixer.attach(sound, "ambience")' not in zone or 'Theme.HatchSoundEnabled' not in zone:
        errors.append('zone loops go through the ambience group and the sound switch')
    registry = read('docs/77-asset-registry.md')
    for sid in re.findall(r'rbxassetid://(\d+)', read('src/shared/ZoneAmbience.luau')):
        if sid not in registry:
            errors.append('zone loop %s must be listed in docs/77' % sid)
    for path in ['src/client/Bootstrap.client.luau', 'src/client/HatchSequence.luau'] + [str(p.relative_to(ROOT)).replace('\\', '/') for p in (ROOT / 'src').rglob('HatchStage*.luau')]:
        text = read(path)
        for word in ('GiftsPanel', 'FriendBonus', 'ZoneAmbience', 'BadgeTable', 'HatchNewsChat'):
            if word in text:
                errors.append('%s must not mention %s' % (path, word))
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    problems = static_checks()
    for p in problems:
        print('FAIL:', p)
    parts = [('R', 'src/shared/RareHatch.luau'), ('F', 'src/shared/FriendBonus.luau'), ('B', 'src/shared/BadgeTable.luau'),
             ('C', 'src/shared/CodeRules.luau'), ('Z', 'src/shared/ZoneAmbience.luau'), ('W', 'src/shared/WorldV3.luau')]
    source = ''.join('local %s=%s\n' % (name, module(read(path))) for name, path in parts) + LUAU
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'social.luau'
        path.write_text(source, encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
    print(result.stdout, end='')
    if result.returncode or 'Social checks passed' not in result.stdout or problems:
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode or 1)


if __name__ == '__main__':
    main()
