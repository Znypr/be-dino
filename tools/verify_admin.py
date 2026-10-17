"""BD-120 owner admin panel checks (docs/79).

Executes the pure rules in src/shared/AdminRules.luau and the admin weather controls in
src/shared/WeatherClock.luau with the pinned Luau runtime, then statically checks that the
server handler authorizes before acting and never touches profile persistence.
Roblox Instances (remote, UI, Lighting) are not executed here; Studio checks are in docs/79.
"""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]


def module(path, requires=None):
    source = (ROOT / path).read_text(encoding='utf-8')
    for name, replacement in (requires or {}).items():
        source = source.replace(name, replacement)
    return '(function()\n' + source + '\nend)()'


BODY = r'''
-- Authorization: user owner, group rank 255, explicit list, unpublished Studio; nobody when disabled.
local function id(overrides)
 local t = {userId = 100, creatorType = "User", creatorId = 100, groupRank = nil, adminIds = {}, unpublishedStudio = false, enabled = true}
 for k, v in overrides do t[k] = v end
 return t
end
assert(Admin.isAdmin(id({})), "user creator is admin")
assert(not Admin.isAdmin(id({userId = 101})), "other players are not admins")
assert(not Admin.isAdmin(id({enabled = false})), "disabled panel admits nobody")
assert(not Admin.isAdmin(id({creatorId = 0, userId = 0})), "unpublished place outside Studio admits nobody")
assert(not Admin.isAdmin(id({creatorId = 0})), "creator 0 outside Studio admits nobody")
assert(Admin.isAdmin(id({creatorType = "Group", creatorId = 5, groupRank = 255})), "group owner is admin")
assert(not Admin.isAdmin(id({creatorType = "Group", creatorId = 5, groupRank = 254})), "group rank 254 is not admin")
assert(not Admin.isAdmin(id({creatorType = "Group", creatorId = 5, groupRank = nil})), "failed rank lookup is not admin")
assert(Admin.isAdmin(id({userId = 7, adminIds = {7}})), "listed id is admin")
assert(not Admin.isAdmin(id({userId = -7, adminIds = {-7}})), "negative ids only in unpublished Studio")
assert(Admin.isAdmin(id({userId = -1, creatorId = 0, unpublishedStudio = true})), "local Studio test server")
assert(not Admin.isAdmin(id({userId = "100"})), "non-number id")

-- Slider values are clamped, snapped and reject garbage.
assert(Admin.sanitize("foodMultiplier", 3) == 3)
assert(Admin.sanitize("foodMultiplier", 3.2) == 3)
assert(Admin.sanitize("foodMultiplier", 3.3) == 3.5)
assert(Admin.sanitize("foodMultiplier", 1e9) == 10)
assert(Admin.sanitize("foodMultiplier", -5) == 0.5)
assert(Admin.sanitize("foodMultiplier", 0/0) == nil)
assert(Admin.sanitize("foodMultiplier", math.huge) == nil)
assert(Admin.sanitize("foodMultiplier", "3") == nil)
assert(Admin.sanitize("crystals", 3) == nil and Admin.sanitize(nil, 3) == nil and Admin.sanitize({}, 3) == nil)
assert(Admin.sanitize("growthMultiplier", 9) == 5, "growth stays inside Dinosaur.addGrowth's x8 clamp")
assert(Admin.sanitize("speedMultiplier", 1.1) == 1 and Admin.sanitize("speedMultiplier", 1.2) == 1.25)
for _, key in Admin.SettingOrder do
 local spec = Admin.Settings[key]
 assert(Admin.sanitize(key, spec.default) == spec.default, key .. " default is on the grid")
 assert(Admin.fromFraction(key, 0) == spec.min and Admin.fromFraction(key, 1) == spec.max and Admin.fromFraction(key, 2) == spec.max)
 assert(Admin.toFraction(key, spec.min) == 0 and Admin.toFraction(key, spec.max) == 1)
 assert(Admin.fromFraction(key, Admin.toFraction(key, spec.default)) == spec.default)
end
-- Feel sliders: server-side clamps keep gravity/jump/leap in sane ranges (runtime only, never persisted).
assert(Admin.sanitize("gravity", 1e6) == 400 and Admin.sanitize("gravity", 0) == 150 and Admin.sanitize("gravity", 255) == 260)
assert(Admin.sanitize("jumpPower", 1e6) == 90 and Admin.sanitize("jumpPower", -1) == 40)
assert(Admin.sanitize("leapSpeed", 9) == 1.5 and Admin.sanitize("leapSpeed", 0) == 0.5)
assert(Admin.sanitize("turnLean", 99) == 3 and Admin.sanitize("moveResponsiveness", 99) == 2 and Admin.sanitize("moveResponsiveness", 0) == 0.5)
assert(Admin.sanitize("gravity", "250") == nil and Admin.sanitize("jumpPower", 0/0) == nil)
for _, key in {"gravity", "jumpPower", "moveResponsiveness", "turnLean", "leapSpeed"} do assert(Admin.Settings[key].group == "feel", key) end
assert(Admin.format(250, "gravity") == "250" and Admin.format(1.5, "leapSpeed") == "x1.5")
assert(Admin.format(2) == "x2" and Admin.format(0.5) == "x0.5" and Admin.format(1.25) == "x1.25")

-- Weather length.
assert(Admin.weatherSeconds(nil, 180) == 180)
assert(Admin.weatherSeconds(5, 180) == 15 and Admin.weatherSeconds(1e9, 180) == 1800 and Admin.weatherSeconds(60.7, 180) == 60)
assert(Admin.weatherSeconds(0/0, 180) == nil and Admin.weatherSeconds("60", 180) == nil)

-- Forced weather runs for its length, then the normal cycle resumes.
local rain = {id = "rain"}
local blood = {id = "bloodmoon"}
local state = Clock.new(0)
assert(state.current == nil and state.nextAt == 600)
Clock.force(state, 10, blood, 60)
assert(state.current == blood and state.endsAt == 70)
assert(not Clock.step(state, 69, function() return rain end), "forced event holds")
assert(Clock.step(state, 70, function() return rain end) and state.current == nil and state.nextAt == 670, "ends then waits a full interval")
Clock.force(state, 100, blood, 600)
Clock.clear(state, 120)
assert(state.current == nil and state.endsAt == 0 and state.nextAt == 720, "stop clears and delays the next random event")
assert(Clock.step(state, 720, function() return rain end) and state.current == rain, "random cycle continues")
-- BD-237 Mutation chance (playtest only): validation, default off, the 100% cap, and no effect without it.
local spec = Admin.Settings.mutationChanceMultiplier
assert(spec and spec.default == 1 and spec.min == 1 and spec.max == 10 and spec.step == 1, "default is off (x1)")
assert(table.find(Admin.SettingOrder, "mutationChanceMultiplier"), "panel lists it next to the other multipliers")
assert(spec.group == nil, "listed in the Run section, not under Feel")
assert(Admin.sanitize("mutationChanceMultiplier", 10) == 10 and Admin.sanitize("mutationChanceMultiplier", 5.4) == 5)
assert(Admin.sanitize("mutationChanceMultiplier", 1e9) == 10, "never above x10")
assert(Admin.sanitize("mutationChanceMultiplier", 0) == 1 and Admin.sanitize("mutationChanceMultiplier", -5) == 1, "never below x1")
assert(Admin.sanitize("mutationChanceMultiplier", 0/0) == nil and Admin.sanitize("mutationChanceMultiplier", math.huge) == nil)
assert(Admin.sanitize("mutationChanceMultiplier", "10") == nil and Admin.sanitize("mutationChanceMultiplier", {}) == nil)
assert(Admin.format(10, "mutationChanceMultiplier") == "x10")
-- Chance maths: the shipped chance is untouched unless a valid multiplier is passed; the result is capped at 100%.
for _, w in Config.Weather do
 assert(Rules.scaledChance(w.chance, nil) == w.chance, w.id .. " default is the shipped chance")
 assert(Rules.scaledChance(w.chance, 1) == w.chance)
 assert(math.abs(Rules.scaledChance(w.chance, 10) - w.chance * 10) < 1e-9 and Rules.scaledChance(w.chance, 10) <= 1, w.id .. " x10")
 assert(Rules.scaledChance(w.chance, 0.1) == w.chance and Rules.scaledChance(w.chance, -3) == w.chance, "a scale below 1 never lowers the chance")
 assert(Rules.scaledChance(w.chance, 0/0) == w.chance and Rules.scaledChance(w.chance, "10") == w.chance and Rules.scaledChance(w.chance, {}) == w.chance)
 assert(Rules.scaledChance(w.chance, math.huge) == 1, "capped at 100%")
 local roll = w.chance * 10 - 1e-6 -- just under the x10 chance
 assert(Rules.eventEgg(w.id, roll, 10).mutationId == w.mutation, w.id .. " mutates at x10")
 assert(Rules.eventEgg(w.id, roll).mutationId == "" and Rules.eventEgg(w.id, roll, 1).mutationId == "", w.id .. " does not mutate without it")
 assert(Rules.eventEgg(w.id, w.chance * 10 + 1e-6, 10).mutationId == "", w.id .. " x10 is not 100%")
end
assert(Rules.scaledChance(0.3, 10) == 1 and Rules.scaledChance(0.1, 10) == 1, "cap at 100%")
local certain = Rules.eventEgg("rain", 0.999999, 1e9)
assert(certain.eventId == "rain" and certain.mutationId == "dewdrop", "a huge scale is certain but still capped at 1")
assert(Rules.eventEgg("rain", 1, 1e9).mutationId == "", "the roll is [0,1): a cap of 100% never exceeds 'always'")
assert(Rules.eventEgg("clear", 0, 10).mutationId == "" and Rules.eventEgg("clear", 0, 10).eventId == "clear", "clear weather never mutates, even at x10")
assert(Rules.validEgg(Rules.eventEgg("volcano", 0, 10)), "a boosted egg is still a normal valid egg")
-- Run-egg tagging: one roll per earned egg; the multiplier changes only the chance, never the count or the tag format.
local function tagRun(scale)
 local calls = 0
 local events, hits = Tags.apply({}, "rain", 0, 20, function() calls += 1 return 0.15 end, scale)
 return events, hits, calls
end
local _, hitsOff, callsOff = tagRun(nil)
local eventsOn, hitsOn, callsOn = tagRun(10)
assert(hitsOff == 0 and callsOff == 20, "default (rain 2%): a 0.15 roll misses")
assert(hitsOn == 20 and callsOn == 20 and #eventsOn == 20, "x10 (rain 20%): a 0.15 roll hits, still one roll per egg")
assert(eventsOn[1].mutationId == "dewdrop" and eventsOn[1].eventId == "rain" and eventsOn[1].n == 1 and eventsOn[20].n == 20)
local clearEvents, clearHits, clearCalls = Tags.apply({}, "clear", 0, 20, function() return 0 end, 10)
assert(#clearEvents == 0 and clearHits == 0 and clearCalls == nil, "clear weather tags nothing at x10")
local _, noEggHits = Tags.apply({}, "rain", 5, 5, function() return 0 end, 10)
assert(noEggHits == 0, "a catch that adds no egg rolls nothing at x10")
-- BD-237 / docs/115: the multiplier is per player. Only the admin who set it rolls boosted; everyone else stays x1 in the same weather.
do
 local adminP, friend, other = {}, {}, {}
 local book = Scale.new()
 assert(Scale.get(book, adminP) == 1 and Scale.get(book, friend) == 1, "everyone starts at x1")
 Scale.set(book, adminP, 10)
 assert(Scale.get(book, adminP) == 10 and Scale.get(book, friend) == 1 and Scale.get(book, other) == 1, "x10 is the admin's alone")
 local rainChance = Config.Weather[1].id == "rain" and Config.Weather[1].chance or 0.02
 local function eggFor(p) local _, hits = Tags.apply({}, "rain", 0, 1, function() return rainChance * 5 end, Scale.get(book, p)) return hits end
 assert(eggFor(adminP) == 1 and eggFor(friend) == 0 and eggFor(other) == 0, "the admin's egg mutates, friends' eggs roll the shipped chance")
 Scale.set(book, adminP, 99) assert(Scale.get(book, adminP) == 10, "clamped to x10")
 Scale.set(book, friend, 0/0) assert(Scale.get(book, friend) == 1, "NaN means x1")
 Scale.set(book, friend, "10") assert(Scale.get(book, friend) == 1, "non-numbers mean x1")
 Scale.set(book, friend, -4) assert(Scale.get(book, friend) == 1, "never below x1")
 Scale.set(book, adminP, 1) assert(Scale.get(book, adminP) == 1 and next(book.scales) == nil, "x1 clears the entry")
 Scale.set(book, adminP, 7) Scale.set(book, friend, 3)
 Scale.clear(book, adminP)
 assert(Scale.get(book, adminP) == 1 and Scale.get(book, friend) == 3, "a leaving admin's scale is cleared without touching another admin's")
 Scale.clearAll(book)
 assert(Scale.get(book, friend) == 1 and next(book.scales) == nil, "reset / start clears every scale")
end
print("Admin panel checks passed")
'''


def static_checks():
    errors = []
    service = (ROOT / 'src/server/AdminService.luau').read_text(encoding='utf-8')
    handle = service[service.index('local function handle'):]
    first = handle.split('\n')[1]
    if 'admins[player] ~= true' not in first:
        errors.append('AdminService.handle must reject non-admins on its first line')
    if re.search(r'ProfileRepository|DataStore|commit|progressionAction', service):
        errors.append('AdminService must stay runtime-only (no profile/DataStore access)')
    if 'OnClientInvoke' in service or 'InvokeClient' in service:
        errors.append('AdminService must never invoke clients')
    # BD-237: the mutation multiplier is applied only from the admin-gated publish(), never read from profiles or remotes of players.
    if 'FoodService.setAdminMutationMultiplier(caller, value)' not in service:
        errors.append('AdminService.publish must forward mutationChanceMultiplier to FoodService for the calling admin only (per player, docs/115)')
    if 'publish(a, value, player)' not in service or 'clearAllAdminMutationMultipliers()' not in service:
        errors.append('AdminService must pass the caller to publish and clear every admin scale on reset / start')
    if 'clearAdminMutationMultiplier(player)' not in service:
        errors.append("AdminService must clear a leaving admin's mutation scale")
    food = (ROOT / 'src/server/FoodService.luau').read_text(encoding='utf-8')
    if 'adminMutationScales = AdminMutationScale.new()' not in food or 'AdminMutationScale.get(adminMutationScales, player)' not in food:
        errors.append('FoodService must keep the mutation scale per Player in an AdminMutationScale book (x1 by default)')
    if 'FoodService.adminMutationScale(candidate.player))' not in food:
        errors.append("FoodService must pass the catching player's own scale to RunEggTags.apply")
    if re.search(r'adminMutationMultiplier', food):
        errors.append('FoodService must not keep a server-wide mutation multiplier (BD-237 is per player, docs/115)')
    if 'AdminMutationScale.clear(adminMutationScales, player)' not in food:
        errors.append("FoodService must drop a leaving player's mutation scale")
    for name in ('src/client/EggsScreen.luau', 'src/client/Bootstrap.client.luau', 'src/client/IndexScreen.luau'):
        path = ROOT / name
        if path.exists() and re.search(r'mutationChanceMultiplier|Admin_mutation|scaledChance', path.read_text(encoding='utf-8')):
            errors.append(name + ' must not use the admin mutation multiplier (odds shown to players stay the shipped ones)')
    for name in ('src/server/ProfileRepository.luau', 'src/server/PlayerDataService.luau'):
        path = ROOT / name
        if path.exists() and re.search(r'mutationChanceMultiplier|adminMutationMultiplier|scaledChance', path.read_text(encoding='utf-8')):
            errors.append(name + ' must not know the admin mutation multiplier (never saved)')
    boot = (ROOT / 'src/server/Bootstrap.server.luau').read_text(encoding='utf-8')
    if 'AdminService' not in boot:
        errors.append('Bootstrap must start AdminService')
    client = (ROOT / 'src/client/AdminPanel.client.luau').read_text(encoding='utf-8')
    if 'GetAttribute("IsAdmin") ~= true' not in client:
        errors.append('AdminPanel must wait for the server IsAdmin flag before building UI')
    # UX (2026-10-15): all weather events pickable, a Start now / Stop pair, grouped sections, toasts told where the panel is.
    for needle in ('for index, event in ProgressionConfig.Weather do', '"Start now"', '"Stop"', 'section("Weather")', 'section("Run")',
                   'section("Debug")', 'AdminPanelRight'):
        if needle not in client:
            errors.append('AdminPanel is missing: ' + needle)
    config = (ROOT / 'src/shared/ProgressionConfig.luau').read_text(encoding='utf-8')
    start = config.index('Weather={') if 'Weather={' in config else config.index('Weather = {')
    events = re.findall(r'\{id="(\w+)",name="[^"]+",rarity="\w+",weight=\d+,growth=', config[start:start + 3000])
    if len(events) != 7:
        errors.append('expected 7 weather events for the admin picker, found %d' % len(events))
    return errors


def script():
    return ('local Config=' + module('src/shared/ProgressionConfig.luau') + '\n'
            + 'local Rules, Tags\n'
            + 'do\n'
            + ' local ProgressionConfig, Genetics = Config, {valid = function() return true end}\n'
            + ' local script = {Parent = {ProgressionConfig = "ProgressionConfig", EggGenetics = "Genetics", ProgressionRules = "Rules"}}\n'
            + ' local require = function(id) return if id == "Genetics" then Genetics elseif id == "Rules" then Rules else ProgressionConfig end\n'
            + ' Rules = ' + module('src/shared/ProgressionRules.luau') + '\n'
            + ' Tags = ' + module('src/shared/RunEggTags.luau') + '\n'
            + 'end\n'
            + 'local Admin=' + module('src/shared/AdminRules.luau') + '\n'
            + 'local Scale=' + module('src/shared/AdminMutationScale.luau') + '\n'
            + 'local Clock=' + module('src/shared/WeatherClock.luau',
                                      {'require(script.Parent.ProgressionConfig)': '{WeatherInterval=600,WeatherDuration=180}'})
            + '\n' + BODY)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    problems = static_checks()
    for problem in problems:
        print('FAIL:', problem)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'admin.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        if result.returncode or 'passed' not in result.stdout or problems:
            print(result.stderr)
            raise SystemExit(result.returncode or 1)
