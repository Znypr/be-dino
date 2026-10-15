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
    return ('local Admin=' + module('src/shared/AdminRules.luau') + '\n'
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
