"""BD-074 objective event hooks (docs/66 section 19): offline verifier.

Static (source scan):
  * each of the 20 docs/66 objectives maps to at least one hook; the table is printed
  * every hook sits AFTER the authoritative commit of its fact (retry/UpdateAsync -> adopt, or the server-side accept/claim),
    inside the same function, and behind the one-boolean flag guard
  * no hook exists anywhere else (no client file, no undeclared call), the module is only required lazily
  * FoodService reports once per player per tick (batched), never inside the per-food claim loop

Dynamic (pinned Luau, real ProfileRepository + real ObjectiveService on the mocked DataStore of tools/verify_rewards.py):
  * flag OFF: a full session (settlement, hatches, equip, potion, replays) never requires ObjectiveService, never calls record
    and never creates an objectives field or an objective operation: zero objective writes
  * flag ON: the same real code paths advance the right counters (run, event eggs, level, eggs hatched, rare, new species,
    equip, potion, fusion use), batch one event per kind per claim, count a replayed settlement once, and every objective of
    the tutorial can be claimed exactly once
The Food, Leap and FusionService sites are exercised in tools/verify_gameplay.py and tools/verify_progression.py; the offline
multiplayer simulation (tools/verify_multiplayer_sim.py) additionally proves a flag-off run writes no objective data.
Offline only: no Studio, no real DataStore, no phone.

  python tools/verify_objective_hooks.py --runner C:/path/to/luau.exe
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import verify_objectives  # noqa: E402

REPO = 'src/server/ProfileRepository.luau'
FOOD = 'src/server/FoodService.luau'
LEAP = 'src/server/LeapService.luau'
FUSION = 'src/server/FusionService.luau'
SERVICE = 'src/server/ObjectiveService.luau'

# One entry per hook site. `anchors` must appear in order, in the same function, BEFORE the hook: the commit (retry/UpdateAsync)
# first, then adopt (the committed profile is the server's truth) or the equivalent accept step.
SITES = [
    dict(name='food', file=FOOD, fn=r'^function FoodService\.start\(', call=r'objectives\(\)\.record\(candidate\.player, "food_eaten", candidate\.items\)',
         guard=r'if trackObjectives then', kinds=['food_eaten'],
         anchors=[r'FoodCatchRules\.award\(candidate\.gained', r'c:SetAttribute\("CatchScore",after\)', r'dinosaur\.addGrowth\(']),
    dict(name='leap', file=LEAP, fn=r'^function Leap\.start\(\)', call=r'require\(script\.Parent\.ObjectiveService\)\.record\(player,"leap_used",1\)',
         guard=r'GameConfig\.ObjectivesEnabled==true', kinds=['leap_used'],
         anchors=[r'player:SetAttribute\("LastLeapStatus","leaping"\)', r'active\[player\]=\{']),
    dict(name='run settled', file=REPO, fn=r'^function ProfileRepository\.commitRunSettlement\(', call=r'objectives\(\)\.recordRunSettled\(player, runId, runSeconds, runEggs,',
         guard=r'Config\.ObjectivesEnabled == true', recorder='recordRunSettled',
         anchors=[r'retrySettlement\("run settlement"', r'adopt\(player, updated\)', r'PrivateState\.set\(player, "LastSettledRunId", runId\)']),
    dict(name='eggs hatched', file=REPO, fn=r'^function ProfileRepository\.claimChest\(', call=r'objectives\(\)\.recordHatched\(player, opened, freshSpecies\)',
         guard=r'Config\.ObjectivesEnabled == true and not duplicateOutcome', recorder='recordHatched',
         anchors=[r'retry\("chest claim"', r'adopt\(player, updated\)', r'publishHatch\(player, chestId, committedOutcome\)']),
    dict(name='equip', file=REPO, fn=r'^function ProfileRepository\.equipSpecies\(', call=r'objectives\(\)\.record\(player, "dino_equipped", 1\)',
         guard=r'Config\.ObjectivesEnabled == true', kinds=['dino_equipped'],
         anchors=[r'retry\("equip species"', r'adopt\(player, updated\)']),
    dict(name='potion', file=REPO, fn=r'^function ProfileRepository\.progressionAction\(', call=r'objectives\(\)\.record\(player,"potion_bought",1\)',
         guard=r'Config\.ObjectivesEnabled == true and action=="buyPotion" and not duplicate', kinds=['potion_bought'],
         anchors=[r'retry\("progression"', r'adopt\(player, updated\)']),
    dict(name='fusion commit', file=REPO, fn=r'^function ProfileRepository\.fuseDinosaurs\(', call=r'objectives\(\)\.recordFusionUse\(player\)',
         guard=r'Config\.ObjectivesEnabled == true and not duplicate', recorder='recordFusionUse',
         anchors=[r'retry\("identity fusion"', r'adopt\(player, updated\)']),
    dict(name='fusion quote', file=FUSION, fn=r'^local function handleAction\(', call=r'require\(script\.Parent\.ObjectiveService\)\.recordFusionUse\(player\)',
         guard=r'Config\.ObjectivesEnabled == true', recorder='recordFusionUse',
         anchors=[r'repository\.quoteFusion\(', r'if not quote then return fail', r'odds_not_approved']),
]
# Files that may mention ObjectiveService at all (everything else, in particular src/client, must not).
ALLOWED_FILES = {REPO, FOOD, LEAP, FUSION, SERVICE, 'src/server/Bootstrap.server.luau', 'src/shared/ObjectiveConfig.luau', 'src/shared/ObjectiveRules.luau'}
CLIENT_PANEL_FILES = {'src/client/ObjectivesPanel.luau'}
# OB2 (docs/115): the ONE other client file that may use ObjectiveAction. It sends only {action = "seen", id = <menu id>}, and only
# FusionMenu calls it (with "fusion_menu", behind the flag).
CLIENT_SEEN_FILES = {'src/client/ObjectiveSeen.luau'}
FUSION_MENU = 'src/client/FusionMenu.luau'


def read_lines(path: str) -> list[str]:
    return (ROOT / path).read_text(encoding='utf-8').split('\n')


def function_range(lines: list[str], pattern: str) -> tuple[int, int]:
    start = next((i for i, line in enumerate(lines) if re.search(pattern, line)), None)
    if start is None:
        raise AssertionError(f'function not found: {pattern}')
    end = next((i for i in range(start + 1, len(lines)) if lines[i] == 'end'), None)
    if end is None:
        raise AssertionError(f'function end not found: {pattern}')
    return start, end


def block_end(lines: list[str], start: int) -> int:
    indent = len(lines[start]) - len(lines[start].lstrip())
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if line.strip() and len(line) - len(line.lstrip()) <= indent and line.strip().startswith('end'):
            return i
    raise AssertionError('block end not found')


def catalogue() -> list[tuple[str, str, str]]:
    """(id, name, event) from the real ObjectiveConfig source."""
    text = (ROOT / 'src/shared/ObjectiveConfig.luau').read_text(encoding='utf-8')
    return re.findall(r'\{id = "([TSD]\d)", group = "[a-z]+", name = "([^"]+)", event = "([a-z_]+)"', text)


def event_kinds() -> set[str]:
    text = (ROOT / 'src/shared/ObjectiveConfig.luau').read_text(encoding='utf-8')
    block = text[text.index('EventKinds = table.freeze({'):]
    block = block[:block.index('}),')]
    return set(re.findall(r'([a-z_]+) = true', block))


def recorder_kinds() -> dict[str, list[str]]:
    lines = read_lines(SERVICE)
    result = {}
    for name in ('recordRunSettled', 'recordHatched', 'recordFusionUse'):
        start, end = function_range(lines, rf'^function ObjectiveService\.{name}\(')
        body = '\n'.join(lines[start:end])
        result[name] = list(dict.fromkeys(re.findall(r'ObjectiveService\.record\(player, "([a-z_]+)"', body)))
    return result


def static_report() -> tuple[list[str], list[str]]:
    errors: list[str] = []
    table: list[str] = []
    kinds_ok = event_kinds()
    recorders = recorder_kinds()
    produced: dict[str, list[str]] = {}
    per_file: dict[str, int] = {}

    for site in SITES:
        lines = read_lines(site['file'])
        try:
            start, end = function_range(lines, site['fn'])
        except AssertionError as exc:
            errors.append(f"{site['name']}: {exc}")
            continue
        hits = [i for i in range(start, end) if re.search(site['call'], lines[i])]
        if len(hits) != 1:
            errors.append(f"{site['name']}: expected exactly one hook call in {site['file']} function, found {len(hits)}")
            continue
        hook = hits[0]
        per_file[site['file']] = per_file.get(site['file'], 0) + 1
        # 1) after the authoritative commit, in order
        position = start
        for anchor in site['anchors']:
            found = next((i for i in range(position, hook) if re.search(anchor, lines[i])), None)
            if found is None:
                errors.append(f"{site['name']}: anchor {anchor!r} must appear before the hook (hook line {hook + 1})")
                break
            position = found
        # 2) behind the one-boolean guard (on the hook line, or the line directly before it)
        window = '\n'.join(lines[max(start, hook - 4):hook + 1])  # the guard is the `if` opening the block, at most 3 lines above
        if not re.search(site['guard'], window):
            errors.append(f"{site['name']}: hook is not behind its flag guard {site['guard']!r}")
        # 3) not in a failure branch: nothing between the last anchor and the hook returns
        if any(re.search(r'\breturn\b', lines[i]) and 'return true' not in lines[i] and 'return false' not in lines[i]
               for i in range(position + 1, hook)):
            pass  # only 'return true/false' style exits are tolerated between commit and hook; checked below
        for i in range(position + 1, hook):
            if re.match(r'\s*return\b', lines[i]) and not lines[i].strip().startswith('return {'):
                errors.append(f"{site['name']}: an early return sits between the commit anchor and the hook (line {i + 1})")
        site_kinds = site.get('kinds') or recorders[site['recorder']]
        for kind in site_kinds:
            if kind not in kinds_ok:
                errors.append(f"{site['name']}: {kind} is not an ObjectiveConfig.EventKinds entry")
            produced.setdefault(kind, []).append(f"{Path(site['file']).stem}:{hook + 1} ({site['name']})")
        if site['name'] == 'food':
            # batched: ONE call per player per tick, outside the per-food claim loop
            claim_loop = next(i for i in range(start, end) if re.search(r'for food, claim in claims do', lines[i]))
            if claim_loop < hook <= block_end(lines, claim_loop):
                errors.append('food: the hook must not sit inside the per-food claim loop (batch per tick)')
            if 'claim.candidate.items += 1' not in '\n'.join(lines[claim_loop:block_end(lines, claim_loop)]):
                errors.append('food: pickups must be tallied per candidate inside the claim loop')
        if site['name'] == 'eggs hatched':
            body = '\n'.join(lines[start:end])
            if 'applyHatch(profileValue, chest, index, outcome, now, freshSpecies)' not in body \
                    or 'applyHatch(profileValue, nextEgg, 1, table.clone(nextEgg.reward), now, freshSpecies)' not in body:
                errors.append('eggs hatched: both applyHatch calls must pass freshSpecies (species is judged inside the transaction)')

    # OB2: T9 is produced by the server-validated "seen" report, not by the fusion quote. The chain must exist: the remote shape,
    # the service branch, and the repository function that queues the catalogue row's own event for a declared seen id only.
    service_text = (ROOT / SERVICE).read_text(encoding='utf-8')
    repo_lines = read_lines(REPO)
    try:
        seen_start, seen_end = function_range(repo_lines, r'^function ProfileRepository\.objectiveSeen\(')
        seen_body = '\n'.join(repo_lines[seen_start:seen_end])
        for needle in ('rules.seenEntry(seenId)', '"unknown_objective"', '"no_dino"', 'rules.seenDone(', '"already_seen"',
                       'ProfileRepository.objectiveRecord(player, {kind = entry.event, amount = 1, id = rules.seenEventId(seenId)})'):
            if needle not in seen_body:
                errors.append(f'objectiveSeen: missing {needle!r}')
        order = [seen_body.find(n) for n in ('"unknown_objective"', '"no_dino"', 'rules.seenDone(', 'ProfileRepository.objectiveRecord(')]
        if order != sorted(order) or -1 in order:
            errors.append('objectiveSeen: checks must run in order: known id, owns a dino, not seen yet, then record')
    except AssertionError as exc:
        errors.append(f'objectiveSeen: {exc}')
    if 'seen = {action = true, id = true}' not in service_text or 'repository.objectiveSeen(player, request.id)' not in service_text:
        errors.append('ObjectiveService: the "seen" request shape and its handler are missing')
    seen_rows = [oid for oid, _, event in catalogue() if event == 'fusion_menu_opened']
    if seen_rows != ['T9'] or 'seen = "fusion_menu"' not in (ROOT / 'src/shared/ObjectiveConfig.luau').read_text(encoding='utf-8'):
        errors.append('only T9 listens for fusion_menu_opened and it declares seen = "fusion_menu"')
    produced.setdefault('fusion_menu_opened', []).append('ProfileRepository.objectiveSeen (client {action="seen", id="fusion_menu"}, server-validated)')

    # No stray hooks: every .record( / recordX( call in the server tree is declared above.
    for path in sorted((ROOT / 'src').rglob('*.luau')):
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding='utf-8')
        code = re.sub(r'--.*$', '', text, flags=re.M)
        mentions = 'ObjectiveService' in code or re.search(r'\bobjectives\(\)', code)
        if mentions and rel not in ALLOWED_FILES:
            errors.append(f'{rel} mentions ObjectiveService: objective facts are reported by the server only')
        # BD-075: the client panel may read the view and send claims through ObjectiveAction; it never reports events.
        if rel.startswith('src/client/') and re.search(r'ObjectiveService', code):
            errors.append(f'{rel}: client code must not reference ObjectiveService (facts are reported by the server only)')
        if rel.startswith('src/client/') and re.search(r'ObjectiveAction', code) and rel not in CLIENT_PANEL_FILES | CLIENT_SEEN_FILES:
            errors.append(f'{rel}: only the objectives panel (view/claim) and ObjectiveSeen (seen) may use ObjectiveAction, no client-reported events')
        if rel in CLIENT_SEEN_FILES:
            actions = re.findall(r'action\s*=\s*"([a-z_]+)"', code)
            if actions != ['seen'] or code.count('InvokeServer') != 1 or code.count('{action = "seen", id = seenId}') != 1:
                errors.append(f'{rel}: must send exactly one request shape, {{action = "seen", id = seenId}} (found actions {actions})')
            if not re.search(r'function ObjectiveSeen\.report\(seenId: string\)\n    if Config\.ObjectivesEnabled ~= true then return end\n', code):
                errors.append(f'{rel}: report() must return first thing while Config.ObjectivesEnabled is not true (flag off sends nothing)')
        if rel.startswith('src/') and 'ObjectiveSeen' in code and rel not in CLIENT_SEEN_FILES | {FUSION_MENU}:
            errors.append(f'{rel}: only FusionMenu may use ObjectiveSeen')
        if rel == FUSION_MENU:
            if 'ObjectiveAction' in code:
                errors.append(f'{rel}: FusionMenu must not touch ObjectiveAction itself (it calls ObjectiveSeen.report)')
            uses = re.findall(r'^.*ObjectiveSeen.*$', code, re.M)
            if len(uses) != 1 or 'if Config.ObjectivesEnabled == true then require(script.Parent.ObjectiveSeen).report("fusion_menu") end' not in uses[0]:
                errors.append(f'{rel}: exactly one use, `if Config.ObjectivesEnabled == true then require(script.Parent.ObjectiveSeen).report("fusion_menu") end`')
            open_fn = '\n'.join(read_lines(FUSION_MENU)[slice(*function_range(read_lines(FUSION_MENU), r'^function FusionMenu\.open\('))])
            if 'ObjectiveSeen' not in open_fn or open_fn.index('FusionMenu.available()') > open_fn.index('ObjectiveSeen'):
                errors.append(f'{rel}: the report belongs in FusionMenu.open, after the availability check')
        if rel in CLIENT_PANEL_FILES and re.search(r'action\s*=\s*"(record|event|progress)"', code):
            errors.append(f'{rel}: the panel may only view and claim, never report progress')
        if rel in ALLOWED_FILES and rel != SERVICE:
            count = len(re.findall(r'(objectives\(\)|ObjectiveService\))\.(record|recordRunSettled|recordHatched|recordFusionUse)\(', code))
            declared = per_file.get(rel, 0)
            if rel in (REPO, FOOD, LEAP, FUSION) and count != declared:
                errors.append(f'{rel}: {count} objective calls but {declared} declared sites (undeclared hook?)')
        # lazy only: the require of the service must be indented (inside a function), never a top-level cost
        for lineno, line in enumerate(text.split('\n'), 1):
            if re.search(r'require\(script\.Parent\.ObjectiveService\)', line) and not line.startswith(' ') and rel != 'src/server/Bootstrap.server.luau':
                errors.append(f'{rel}:{lineno}: ObjectiveService must be required lazily, inside a function')

    # Objective -> hook table
    rows = catalogue()
    if len(rows) != 20:
        errors.append(f'catalogue parse found {len(rows)} objectives, expected 20')
    for oid, name, event in rows:
        hooks = produced.get(event, [])
        table.append(f'| {oid} | {name} | `{event}` | ' + ('; '.join(hooks) if hooks else 'NONE') + ' |')
        if not hooks:
            errors.append(f'objective {oid} ({name}) has no hook for {event}')
    unused = sorted(kind for kind in produced if kind not in {e for _, _, e in rows})
    if unused:
        errors.append('hooks record kinds no objective uses: ' + ', '.join(unused))
    return errors, table


def dynamic_script() -> str:
    prefix = verify_objectives.harness_prefix()
    for old, new in [
        ('local ObjectiveConfigM=@@OBJ_CONFIG@@', 'local ObjectiveServiceM\nlocal serviceLoads=0\nlocal ObjectiveConfigM=@@OBJ_CONFIG@@'),
        ('RareHatchService="RareHatchService",', 'RareHatchService="RareHatchService",ObjectiveService="ObjectiveService",'),
        (' if id=="ObjectiveRules" then return ObjectiveRulesM end', ' if id=="ObjectiveService" then serviceLoads+=1 return ObjectiveServiceM end\n if id=="ObjectiveRules" then return ObjectiveRulesM end'),
        ('local Repository=@@REPO_MODULE@@', SERVICE_BOOT + '\nlocal Repository=@@REPO_MODULE@@'),
    ]:
        assert prefix.count(old) == 1, old
        prefix = prefix.replace(old, new)
    return verify_objectives.fill(prefix + '\n' + BODY)


SERVICE_BOOT = r'''
ObjectiveServiceM=(function()
 local folderChildren={}
 local rs={Shared={Config="Config",ObjectiveConfig="ObjectiveConfig",ObjectiveRules="ObjectiveRules"}}
 function rs:FindFirstChild(name) return folderChildren[name] end
 local services={ReplicatedStorage=rs,Players={GetPlayers=function() return {} end,PlayerRemoving={Connect=function() end}}}
 local game={GetService=function(_,name) return services[name] end}
 local Instance={new=function(class)
  local inst={ClassName=class}
  function inst:IsA(name) return name==self.ClassName end
  function inst:Destroy() end
  function inst:FindFirstChild(name) return folderChildren[name] end
  return setmetatable(inst,{__newindex=function(t,k,v)
   rawset(t,k,v)
   if k=="Parent" and v then folderChildren[rawget(t,"Name") or "?"]=t end
  end})
 end}
 local script={Parent={}}
 local require=function(id) if id=="Config" then return GameConfig elseif id=="ObjectiveConfig" then return ObjectiveConfigM elseif id=="ObjectiveRules" then return ObjectiveRulesM end error("unexpected "..tostring(id)) end
 local task={spawn=function() end,wait=function() end}
 local warn=function() end
 return @@OBJ_SERVICE@@
end)()
'''

BODY = r'''
------------------------------------------------------------------ BD-074 hooks, real ProfileRepository + real ObjectiveService
local function user(id)
 local u={Parent=true,UserId=id,attrs={}}
 function u:SetAttribute(k,v) self.attrs[k]=v end
 function u:GetAttribute(k) return self.attrs[k] end
 return u
end
local function key(u) return "u:"..tostring(u.UserId) end
local DAY0=20833*86400
fakeNow=DAY0+100
local C=ObjectiveConfigM
local function crystals(u) return data[key(u)].progression.crystals end
local function stored(u) return data[key(u)].objectives end

-- A spy over the one entry point. Every hook goes through ObjectiveService.record, so this sees them all.
local calls={}
do
 local original=ObjectiveServiceM.record
 ObjectiveServiceM.record=function(player,kind,amount,eventId,value)
  table.insert(calls,{player=player,kind=kind,amount=amount,id=eventId,value=value})
  return original(player,kind,amount,eventId,value)
 end
end
local function take() local out=calls calls={} return out end
local function sum(list,kind) local n=0 for _,c in list do if c.kind==kind then n+=(c.amount or 1) end end return n end
local function count(list,kind) local n=0 for _,c in list do if c.kind==kind then n+=1 end end return n end
local weatherId=ProgressionConfig.Weather[1].id
local perLevel=ProgressionConfig.AccountXPPerLevel

local function seedEggs(u,eggs,crystalsAmount,xp)
 Repository.release(u)
 local profile=data[key(u)]
 profile.eggs={} for _,egg in eggs do table.insert(profile.eggs,egg) end
 profile.pendingChestGrants=0 profile.runEggBank=nil
 if crystalsAmount then profile.progression.crystals=crystalsAmount end
 if xp then profile.progression.accountXP=xp end
 assert(Repository.load(u))
end
local function legacyEgg(id,speciesId) return {eggId=id,kind="alpha_chest",readyAt=0,eventId="clear",mutationId="",reward={speciesId=speciesId,count=1}} end
local function crackedEgg(id,speciesId)
 return {eggId=id,kind="alpha_chest",readyAt=0,eventId="clear",mutationId="",reward={speciesId=speciesId,count=1},
  genes={conditionId="cracked",hatchSuccess=false,primaryColorId="white",secondaryColorId="white",blend=100,patternId="01_blank"}}
end

------------------------------------------------------------------ A. flag OFF: a whole session writes nothing for objectives
assert(GameConfig.ObjectivesEnabled==false,"the committed Config has the flag off")
do
 local a=user(7401)
 assert(Repository.load(a))
 local transformsBefore=transforms
 seedEggs(a,{legacyEgg("off-1","triceratops"),legacyEgg("off-2","compy")},500,10*perLevel)
 local okRun,_,runStatus=Repository.commitRunSettlement(a,"off-run",12,{{eventId=weatherId,mutationId="",n=1}},200)
 assert(okRun and runStatus=="committed")
 assert(Repository.claimChest(a,"off-1") and Repository.claimChest(a,"off-2"))
 assert(Repository.equipSpecies(a,"triceratops")==true)
 assert(select(2,Repository.equipSpecies(a,"triceratops"))=="already_equipped")
 local offers=Rules.shopOffers(Rules.shopWindow(fakeNow))
 assert(Repository.progressionAction(a,"buyPotion",offers[1].id.."@"..Rules.shopWindow(fakeNow),"off-potion",false))
 assert(Repository.commitRunSettlement(a,"off-run",12,nil,200))
 -- OB2: a forged "seen" report with the flag off: the service ignores it (no remote exists, no profile access), the repository refuses
 local offSeen=ObjectiveServiceM.handle(a,{action="seen",id="fusion_menu"}) assert(offSeen.ok==false and offSeen.reason=="disabled","flag off: the server ignores a seen report")
 local offOk,offStatus=Repository.objectiveSeen(a,"fusion_menu") assert(offOk==false and offStatus=="disabled","flag off: the repository refuses a seen report")
 local ops=data[key(a)].recentOperations
 for _,op in ops do assert(op.kind~="objective","no objective operation was written") end
 Repository.release(a)
 assert(data[key(a)].objectives==nil,"flag off: no objectives field was created")
 assert(serviceLoads==0,"flag off: ObjectiveService was never required by any hook site")
 assert(#calls==0,"flag off: ObjectiveService.record was never reached")
 print("Flag-off passed: settlement, 2 hatches, equip, potion and a replay ran with zero objective calls, zero requires, zero objective writes (transforms "..(transforms-transformsBefore)..", all gameplay)")
end

------------------------------------------------------------------ B. flag ON: the real code paths advance the right counters
GameConfig.ObjectivesEnabled=true
local objectiveRemote=ObjectiveServiceM.start(Repository)
assert(objectiveRemote~=nil,"the service starts with the flag on")
local clockNow=1000
ObjectiveServiceM.setClock(function() return clockNow end)
take()

-- B1. settlement: run end + event eggs + level, id-keyed so a replay counts once
do
 local b=user(7402)
 assert(Repository.load(b))
 seedEggs(b,{},0,4*perLevel-40) -- the 12-egg run adds 40 XP: level 3 exactly
 local okRun,_,status=Repository.commitRunSettlement(b,"hook-run-1",12,{{eventId=weatherId,mutationId="",n=1},{eventId=weatherId,mutationId="",n=2}},200)
 assert(okRun and status=="committed")
 local list=take()
 assert(count(list,"run_end")==1 and list[1].kind=="run_end" and list[1].id=="run:hook-run-1" and list[1].value==200,"run_end carries the run id and the run length")
 assert(sum(list,"event_egg_caught")==2 and count(list,"event_egg_caught")==1,"two weather eggs -> ONE event_egg_caught event of 2")
 assert(count(list,"level_reached")==1 and list[#list].value==Rules.level(data[key(b)].progression) and list[#list].value==3,"the committed account level rides along (3)")
 -- a replay (cheap path) and a settlement whose acknowledgement was lost (in-call duplicate) each count the run once
 assert(select(3,Repository.commitRunSettlement(b,"hook-run-1",12,nil,200))=="duplicate")
 assert(#take()==0,"a replayed settlement reports nothing")
 failMode="ack_lost"
 local ackOk,_,ackStatus=Repository.commitRunSettlement(b,"hook-run-2",12,nil,200)
 assert(ackOk and ackStatus=="duplicate")
 list=take()
 assert(count(list,"run_end")==1 and list[1].id=="run:hook-run-2" and count(list,"event_egg_caught")==0,"lost acknowledgement: one run_end, clear eggs are not event eggs")
 assert(select(2,Repository.objectiveFlush(b))=="flushed")
 assert(stored(b).tutorial.progress.T2==2,"two runs = T2 progress 2 (not 3): "..tostring(stored(b).tutorial.progress.T2))
 assert(stored(b).tutorial.progress.T7==2 or stored(b).tutorial.progress.T7==1,"T7 counted (threshold met)")
 -- a level below the threshold does not count for T7
 local low=user(7403)
 assert(Repository.load(low))
 assert(Repository.commitRunSettlement(low,"low-run",1,nil,200))
 take()
 assert(select(2,Repository.objectiveFlush(low))=="flushed" and (stored(low).tutorial.progress.T7 or 0)==0,"level 1 does not satisfy 'reach level 3'")
end

-- B2. hatches: one batched event per kind per claim; species_new judged inside the transaction; Cracked counts as opened, not as rare
do
 local h=user(7404)
 assert(Repository.load(h))
 seedEggs(h,{legacyEgg("hk-1","triceratops"),legacyEgg("hk-2","triceratops"),legacyEgg("hk-3","compy"),crackedEgg("hk-4","brachiosaurus")})
 take()
 assert(Repository.claimChest(h,"hk-1"))
 local list=take()
 assert(#list==3 and sum(list,"egg_hatched")==1 and sum(list,"rare_hatched")==1 and sum(list,"species_new")==1,"first Triceratops: opened, rare (tier 3), new species")
 assert(Repository.claimChest(h,"hk-2"))
 list=take()
 assert(#list==2 and sum(list,"egg_hatched")==1 and sum(list,"rare_hatched")==1 and sum(list,"species_new")==0,"second Triceratops is not new")
 assert(Repository.claimChest(h,"hk-3"))
 list=take()
 assert(#list==1 and sum(list,"egg_hatched")==1,"a Common compy is opened only (already owned, not rare)")
 local failedOk,failedOutcome=Repository.claimChest(h,"hk-4")
 assert(failedOk and failedOutcome.failed==true)
 list=take()
 assert(#list==1 and sum(list,"egg_hatched")==1,"a failed Cracked egg counts as opened but is not rare and not a new species")
 local dupOk,_,dupStatus=Repository.claimChest(h,"hk-1")
 assert(dupOk and dupStatus=="duplicate" and #take()==0,"a duplicate claim reports nothing")
 -- equip: only a real change counts
 assert(Repository.equipSpecies(h,"triceratops")==true)
 list=take() assert(#list==1 and list[1].kind=="dino_equipped")
 assert(select(2,Repository.equipSpecies(h,"triceratops"))=="already_equipped" and #take()==0,"already equipped reports nothing")
 assert(select(2,Repository.equipSpecies(h,"mosasaurus"))=="locked" and #take()==0,"a locked species reports nothing")
end

-- B3. a 12-egg run: the head claim commits a whole hatch page; ONE egg_hatched event carries all of it, the buffered reveals add none
do
 local p=user(7405)
 assert(Repository.load(p))
 assert(Repository.commitRunSettlement(p,"page-run",12,nil,200))
 take()
 local head=data[key(p)].eggs[1].eggId
 assert(Repository.claimChest(p,head))
 local list=take()
 local buffered=Repository.pendingReveals(p)
 assert(buffered>0,"the page committed more eggs than the head")
 assert(count(list,"egg_hatched")==1 and sum(list,"egg_hatched")==1+buffered,"one event for the whole page: "..sum(list,"egg_hatched").." vs 1+"..buffered)
 for _=1,buffered do assert(Repository.claimChest(p,p.attrs.NextChestId)) end
 assert(#take()==0,"revealing already-committed page eggs reports nothing again")
end

-- B4. potion: only a committed purchase, once per token
do
 local q=user(7406)
 assert(Repository.load(q))
 seedEggs(q,{},1000,nil)
 take()
 local window=Rules.shopWindow(fakeNow)
 local offer=Rules.shopOffers(window)[1].id.."@"..window
 assert(Repository.progressionAction(q,"buyPotion",offer,"hk-potion-1",false))
 local list=take() assert(#list==1 and list[1].kind=="potion_bought")
 assert(select(2,Repository.progressionAction(q,"buyPotion",offer,"hk-potion-1",false))=="duplicate" and #take()==0,"the same token again reports nothing")
 assert(not Repository.progressionAction(q,"buyPotion","fake@"..window,"hk-potion-2",false) and #take()==0,"a refused purchase reports nothing")
 assert(Repository.progressionAction(q,"grant","crystal","hk-grant",false,3) and #take()==0,"other progression actions report nothing")
end

-- B5. fusion use and the service-level recorders (the FusionService quote site is exercised in verify_progression)
do
 local f=user(7407)
 assert(Repository.load(f))
 take()
 ObjectiveServiceM.recordFusionUse(f)
 local list=take()
 assert(#list==1 and sum(list,"fusion_step_added")==1 and sum(list,"fusion_menu_opened")==0,"a fusion quote/commit counts D5 only; T9 is the client's seen report (OB2)")
 ObjectiveServiceM.recordHatched(f,{{speciesId="compy"},{speciesId="mosasaurus"},{speciesId="mosasaurus",failed=true}},{mosasaurus=true})
 list=take()
 assert(sum(list,"egg_hatched")==3 and sum(list,"rare_hatched")==1 and sum(list,"species_new")==1,"recordHatched: 3 opened, 1 rare (the failed one is not), 1 new")
end

------------------------------------------------------------------ C. a simulated first session: the real paths finish the tutorial, every claim pays exactly once
do
 local z=user(7410)
 assert(Repository.load(z))
 seedEggs(z,{legacyEgg("z-1","compy"),legacyEgg("z-2","compy"),legacyEgg("z-3","triceratops")},1000,4*perLevel-40)
 take()
 ObjectiveServiceM.record(z,"food_eaten",10)                                   -- T1 (the Food site: verify_gameplay)
 assert(Repository.commitRunSettlement(z,"z-run",12,nil,200))                  -- T2 + T7 (level 3 after this run's XP)
 for _,id in {"z-1","z-2","z-3"} do assert(Repository.claimChest(z,id)) end   -- T3 (3 hatches) + T8 (a second species)
 assert(Repository.equipSpecies(z,"triceratops"))                              -- T4
 ObjectiveServiceM.record(z,"leap_used",1)                                     -- T5 (the Leap site: verify_progression)
 local window=Rules.shopWindow(fakeNow)
 assert(Repository.progressionAction(z,"buyPotion",Rules.shopOffers(window)[1].id.."@"..window,"z-potion",false)) -- T6
 local seenAnswer=objectiveRemote.OnServerInvoke(z,{action="seen",id="fusion_menu"}) -- T9 (OB2: the client's one-time "seen" report)
 assert(seenAnswer.ok==true and seenAnswer.status=="seen","T9 completes on one seen request: "..tostring(seenAnswer.reason))
 local kinds={}
 for _,c in take() do kinds[c.kind]=true end
 local view=Repository.objectiveView(z)
 assert(view.tutorial.id=="T1" and view.tutorial.done,"T1 is done first")
 local before=crystals(z)
 local granted=0
 local order={}
 for step=1,#C.Catalogue do
  view=Repository.objectiveView(z)
  if view.tutorialDone then break end
  local row=view.tutorial
  assert(row.done==true,row.id.." must be complete after the simulated session (progress "..row.progress.."/"..row.goal..")")
  local token="z-claim-"..row.id
  local ok,status,outcome=Repository.objectiveClaim(z,row.id,token)
  assert(ok and status=="claimed" and outcome.crystals==C.ById[row.id].reward.crystals,row.id.." claims")
  granted+=outcome.crystals
  table.insert(order,row.id)
  -- exactly once: the same token, a new token, another row's token
  local dOk,dStatus=Repository.objectiveClaim(z,row.id,token) assert(dOk and dStatus=="duplicate")
  local aOk,aStatus=Repository.objectiveClaim(z,row.id,token.."-again") assert(not aOk and aStatus=="already_claimed")
  assert(crystals(z)==before+granted,"every claim paid once: "..crystals(z).." vs "..(before+granted))
 end
 assert(table.concat(order,",")=="T1,T2,T3,T4,T5,T6,T7,T8,T9" and granted==160,"the whole tutorial (160 Crystals) was claimed once each: "..table.concat(order,","))
 for _,eventKind in {"food_eaten","run_end","level_reached","egg_hatched","rare_hatched","species_new","dino_equipped","leap_used","potion_bought"} do
  assert(kinds[eventKind],eventKind.." was recorded during the session")
 end
 -- the Short + Daily rows of this window: drive them with their own event kinds, claim each once
 view=Repository.objectiveView(z)
 local rewards=0
 for _,group in {view.short,view.daily} do
  for _,row in group do
   local entry=C.ById[row.id]
   ObjectiveServiceM.record(z,entry.event,entry.goal,nil,entry.minValue)
  end
 end
 view=Repository.objectiveView(z)
 local wallet=crystals(z)
 for _,group in {view.short,view.daily} do
  for _,row in group do
   assert(row.done,row.id.." done")
   local ok,status,outcome=Repository.objectiveClaim(z,row.id,"z-w-"..row.id)
   assert(ok and (status=="claimed" or status=="claimed_capped"),row.id)
   rewards+=outcome.crystals
   local aOk,aStatus=Repository.objectiveClaim(z,row.id,"z-w2-"..row.id) assert(not aOk and aStatus=="already_claimed")
  end
 end
 assert(crystals(z)==wallet+rewards and rewards>0,"window rows paid once")
 print("Flag-on passed: settlement/event eggs/level, batched hatches (page = one event), species_new inside the transaction, Cracked counts as opened, equip, potion, fusion use; replays count once; tutorial T1-T9 (160 Crystals) and the window rows claim exactly once")
end

------------------------------------------------------------------ D. OB1: only a run that ate food AND lasted RunMinSeconds counts for T2 / S3 / D2
do
 local OR=ObjectiveRulesM
 local cfg=OR.Config
 assert(cfg.RunMinSeconds==30 and cfg.RunMinFood==1,"OB1 numbers: 30 s and 1 food")
 -- a daily window whose three picks include D2
 local day=nil
 for d=20833,20833+200 do for _,id in OR.pick("daily",d) do if id=="D2" then day=day or d end end end
 assert(day~=nil,"a daily window with D2 exists")
 local saved=fakeNow
 fakeNow=day*86400+100
 local u=user(7420)
 assert(Repository.load(u))
 take()
 local function slot(view) for _,row in view.daily do if row.id=="D2" then return row end end end
 local function runEnds(list) return count(list,"run_end") end
 -- three instant runs: no food, 5 s / 200 s without any food event / food but 29 s: none counts
 assert(Repository.commitRunSettlement(u,"ob1-a",0,nil,5))
 assert(Repository.commitRunSettlement(u,"ob1-b",0,nil,200))
 ObjectiveServiceM.record(u,"food_eaten",3)
 take()
 assert(Repository.commitRunSettlement(u,"ob1-c",0,nil,29))
 assert(runEnds(take())==0,"three instant runs report no run_end")
 assert(select(2,Repository.objectiveFlush(u))=="flushed")
 local view=Repository.objectiveView(u)
 assert(slot(view).progress==0 and not slot(view).done,"three instant runs do not finish D2")
 assert((stored(u).tutorial.progress.T2 or 0)==0,"nor T2")
 -- exactly at the line counts: 30 s and 1 food (a catch implies food, so catchScore 1 with no food event counts too)
 ObjectiveServiceM.record(u,"food_eaten",1)
 take()
 assert(Repository.commitRunSettlement(u,"ob1-d",0,nil,30))
 local list=take() assert(runEnds(list)==1 and list[1].id=="run:ob1-d","30 s and 1 food counts")
 assert(Repository.commitRunSettlement(u,"ob1-e",1,nil,60))
 assert(runEnds(take())==1,"a committed catch implies food: counts")
 -- the food of one run is not reused by the next
 ObjectiveServiceM.record(u,"food_eaten",5)
 take()
 assert(Repository.commitRunSettlement(u,"ob1-f",0,nil,90)) assert(runEnds(take())==1)
 assert(Repository.commitRunSettlement(u,"ob1-g",0,nil,90)) assert(runEnds(take())==0,"no new food since the last settlement: not a run")
 -- a fresh player: three REAL runs finish D2, a replay of one counts once, the claim pays once
 local r=user(7421)
 assert(Repository.load(r))
 for i=1,3 do
  ObjectiveServiceM.record(r,"food_eaten",2)
  assert(Repository.commitRunSettlement(r,"ob1-real-"..i,1,nil,45))
 end
 assert(Repository.commitRunSettlement(r,"ob1-real-1",1,nil,45))
 assert(select(2,Repository.objectiveFlush(r))=="flushed")
 view=Repository.objectiveView(r)
 assert(slot(view).progress==3 and slot(view).done,"three real runs finish D2: "..slot(view).progress)
 local before=crystals(r)
 local ok,status,outcome=Repository.objectiveClaim(r,"D2","ob1-d2")
 assert(ok and status=="claimed" and outcome.crystals==40 and crystals(r)==before+40,"D2 pays 40 once")
 assert(select(2,Repository.objectiveClaim(r,"D2","ob1-d2-again"))=="already_claimed")
 fakeNow=saved
 print("OB1 passed: three instant runs do not finish D2 (or T2), exactly 30 s + 1 food counts, a catch implies food, food is not reused, three real runs finish D2 and pay once")
end

------------------------------------------------------------------ E. OB2: T9 "Open the Fusion menu" is earned by ONE server-validated seen report
do
 local function ask(u,request) clockNow+=100 ObjectiveServiceM.setClock(function() return clockNow end) return objectiveRemote.OnServerInvoke(u,request) end
 local u=user(7430)
 assert(Repository.load(u))
 take()
 -- the fusion quote path no longer completes T9
 ObjectiveServiceM.recordFusionUse(u)
 assert(select(2,Repository.objectiveFlush(u))=="flushed")
 assert((stored(u).tutorial.progress.T9 or 0)==0,"a fusion use alone does not complete T9")
 take()
 -- forged ids and shapes are refused and queue nothing
 for _,forged in {"T9","D5","fusion","FUSION_MENU","fusion_menu ","index"} do
  local answer=ask(u,{action="seen",id=forged})
  assert(answer.ok==false and answer.reason=="unknown_objective","forged seen id refused: "..forged.." -> "..tostring(answer.reason))
 end
 for _,forged in {"",string.rep("x",33)} do
  local answer=ask(u,{action="seen",id=forged}) assert(answer.ok==false and answer.reason=="bad_request","empty or oversized id refused")
 end
 for _,bad in {{action="seen"},{action="seen",id="fusion_menu",amount=5},{action="seen",id="fusion_menu",objective="T9"},{action="seen",id=5},{action="seen",id={}},{action="seen",id="fusion_menu",token="t"}} do
  local answer=ask(u,bad) assert(answer.ok==false and answer.reason=="bad_request","bad shape refused")
 end
 clockNow+=100 ObjectiveServiceM.setClock(function() return clockNow end)
 assert(objectiveRemote.OnServerInvoke(u,{action="seen",id="fusion_menu"},"extra").reason=="bad_request","extra arguments refused")
 assert(#take()==0 and select(2,Repository.objectiveFlush(u))=="nothing","nothing was recorded by refused requests")
 -- the genuine report completes T9 ONCE
 local first=ask(u,{action="seen",id="fusion_menu"})
 assert(first.ok==true and first.status=="seen" and first.view~=nil,"first report: seen")
 local again=ask(u,{action="seen",id="fusion_menu"})
 assert(again.ok==true and again.status=="already_seen","a repeat report: already_seen")
 assert(select(2,Repository.objectiveFlush(u))=="flushed")
 assert(stored(u).tutorial.progress.T9==1,"T9 counted exactly once: "..tostring(stored(u).tutorial.progress.T9))
 assert(ask(u,{action="seen",id="fusion_menu"}).status=="already_seen","still already_seen after the flush")
 assert(select(2,Repository.objectiveFlush(u))=="nothing","a repeat queues nothing to write")
 -- a reconnect (release and load) does not make it countable again
 Repository.release(u) assert(Repository.load(u))
 assert(ask(u,{action="seen",id="fusion_menu"}).status=="already_seen","after a reconnect: still once")
 -- rewards: T9 pays the small tutorial amount (20 PROVISIONAL), once, through the normal claim
 local before=crystals(u)
 for _,id in {"T1","T2","T3","T4","T5","T6","T7","T8"} do
  local entry=C.ById[id] ObjectiveServiceM.record(u,entry.event,entry.goal,nil,entry.minValue)
 end
 assert(select(2,Repository.objectiveFlush(u))=="flushed")
 local granted=0
 for _,id in {"T1","T2","T3","T4","T5","T6","T7","T8","T9"} do
  local ok,status,outcome=Repository.objectiveClaim(u,id,"e-"..id) assert(ok and status=="claimed",id)
  granted+=outcome.crystals
 end
 assert(granted==160 and crystals(u)==before+160,"tutorial still totals 160 with T9 = 20")
 assert(ask(u,{action="seen",id="fusion_menu"}).status=="already_seen","after the claim: already_seen")
 assert(select(2,Repository.objectiveFlush(u))=="nothing","nothing queued after the claim")
 -- only after the player has a dino
 local n=user(7431)
 assert(Repository.load(n))
 Repository.release(n)
 data[key(n)].collection.compy.base=0
 assert(Repository.load(n))
 local none=ask(n,{action="seen",id="fusion_menu"})
 assert(none.ok==false and none.reason=="no_dino","no dino yet: refused")
 assert(select(2,Repository.objectiveFlush(n))=="nothing","a refused report queued nothing")
 Repository.release(n)
 data[key(n)].collection.compy.base=1
 assert(Repository.load(n))
 assert(ask(n,{action="seen",id="fusion_menu"}).status=="seen","with a dino: accepted")
 -- rate limit: RequestsPerWindow per RateWindowSeconds, then it opens again
 local m=user(7432)
 assert(Repository.load(m))
 clockNow+=1000 ObjectiveServiceM.setClock(function() return clockNow end)
 local okCount,limited=0,0
 for _=1,C.RequestsPerWindow+4 do
  local answer=objectiveRemote.OnServerInvoke(m,{action="seen",id="fusion_menu"})
  if answer.ok then okCount+=1 elseif answer.reason=="rate_limited" then limited+=1 end
 end
 assert(okCount==C.RequestsPerWindow and limited==4,"seen requests are rate limited: "..okCount.."/"..limited)
 clockNow+=C.RateWindowSeconds ObjectiveServiceM.setClock(function() return clockNow end)
 assert(objectiveRemote.OnServerInvoke(m,{action="seen",id="fusion_menu"}).ok==true,"window passed: allowed again")
 assert(select(2,Repository.objectiveFlush(m))=="flushed" and stored(m).tutorial.progress.T9==1,"a spamming client still counts T9 once")
 -- the flag turned off at runtime: the server ignores it again
 GameConfig.ObjectivesEnabled=false
 local off=objectiveRemote.OnServerInvoke(user(7433),{action="seen",id="fusion_menu"})
 assert(off.ok==false and off.reason=="disabled","flag off: ignored")
 GameConfig.ObjectivesEnabled=true
 print("OB2 passed: T9 completes on one seen request and only once (also after a reconnect and a claim), forged ids and shapes refused, no dino refused, rate limited, a fusion use alone no longer completes T9, flag off ignored")
end
'''


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args(argv)
    errors, table = static_report()
    print('Objective-to-hook table (docs/66 section 19):')
    print('| # | Objective | Event | Hook site(s) |')
    print('| --- | --- | --- | --- |')
    for row in table:
        print(row)
    for error in errors:
        print('FAIL:', error)
    if errors:
        return 1
    print(f'Static passed: {len(table)} objectives mapped, {len(SITES)} hook sites after their commit and behind the flag, no stray hook, lazy requires only')
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'objective_hooks.luau'
        path.write_text(dynamic_script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout, end='')
        print(result.stderr, end='')
        if result.returncode == 0 and 'Flag-on passed' in result.stdout:
            print('Objective hooks verification passed (BD-074).')
            return 0
        return result.returncode or 1


if __name__ == '__main__':
    raise SystemExit(main())
