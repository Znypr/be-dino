"""BD-426: offline checks for the run/session telemetry. Runs the pure shared/RunTelemetry in Luau (event shape, privacy,
rate limit, session accounting), checks the flag wiring statically, and feeds the log lines into tools/telemetry_report.py.

    python tools/verify_telemetry.py --runner /path/to/luau
"""
from pathlib import Path
import argparse, re, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import telemetry_report as report

BODY = r'''
local T=RT
-- run_end: bounded, whitelisted, estimate flagged
local e=T.runEnd({runSeconds=301.4,reason="ManualExit",eggs=15,nests=1,crystals=30,foodCatchRate=12/500})
assert(e.duration_s==301 and e.eggs==15 and e.nests==1 and e.crystals==30 and e.reason=="ManualExit")
assert(e.food==625 and e.food_is_estimate==true,"food = eggs / rate, flagged as an estimate")
assert(T.runEnd({runSeconds=1,reason="<script>",eggs=0,nests=0,crystals=0}).reason=="Other","unknown reason collapses")
local bad=T.runEnd({runSeconds=-5,reason=nil,eggs="x",nests=0/0,crystals=1e99})
assert(bad.duration_s==0 and bad.eggs==0 and bad.nests==0 and bad.crystals==10000000,"garbage is clamped")
assert(T.runEnd({runSeconds=60,reason="Death",eggs=3,nests=0,crystals=0,food=77}).food_is_estimate==false)
-- privacy: only whitelisted keys, no ids or names can appear
local allowed={event=1,duration_s=1,reason=1,food=1,food_is_estimate=1,food_raw=1,eggs_food=1,weather_s=1,eggs=1,nests=1,crystals=1,total_s=1,runs=1,hub_s=1,run_s=1}
for k in e do assert(allowed[k],"unexpected field "..k) end
local line=T.line(e)
assert(line:sub(1,#T.LogPrefix)==T.LogPrefix and not line:lower():find("user") and not line:lower():find("name"))
-- session: hub vs run time and run count
local s=T.newSession(0,"Sanctuary")
T.moved(s,40,"Island") T.moved(s,340,"Sanctuary") T.runFinished(s)
T.moved(s,360,"Island") T.moved(s,400,"Sanctuary") T.runFinished(s)
local se=T.sessionEnd(s,460)
assert(se.runs==2 and se.run_s==340 and se.hub_s==120 and se.total_s==460,"session accounting")
-- rate limit: burst capped at the bucket, refills over time, per-session cap
local lim,sess=T.newLimiter(),T.newSession(0,"Sanctuary")
local ok=0 for i=1,100 do if T.allow(lim,sess,0) then ok+=1 end end
assert(ok==T.MaxEventsPerMinute,"burst capped: "..ok)
assert(not T.allow(lim,sess,0)) assert(T.allow(lim,sess,2),"refills")
local lim2,sess2=T.newLimiter(),T.newSession(0,"Sanctuary") local n=0
for i=1,1000 do if T.allow(lim2,sess2,i*3) then n+=1 end end
assert(n==T.MaxEventsPerSession,"per-session cap "..n)
-- BD-575: real raw food, eggs from food at x1 and weather seconds, recorded beside the derived legacy field
do
 local rate=12/500
 local stats=T.newRunStats("run-1")
 local sum,ticks=0,0
 -- a simulated run: 300 ticks, each eating a few pickups of 1/4/15/50 points; noteFood is called ONCE per tick with that tick's sum
 local seed=7 local function rnd(n) seed=(seed*1103515245+12345)%2147483648 return (seed//65536)%n end
 local kinds={1,4,15,50}
 for tick=1,300 do
  local raw,eaten=0,rnd(5)
  for _=1,eaten do raw+=kinds[rnd(4)+1] end
  if raw>0 then T.noteFood(stats,raw,raw,rate) ticks+=1 end
  sum+=raw
 end
 assert(sum>500 and stats.foodRaw==sum and stats.ticks==ticks,"real food equals the sum of the pickups")
 assert(math.abs(stats.eggsFood-sum*rate)<1e-6,"eggs from food = food x rate, no multiplier")
 -- admin multiplier x2: gained doubles the eggs, the raw food does not
 local adm=T.newRunStats("a") T.noteFood(adm,100,200,rate)
 assert(adm.foodRaw==100 and math.abs(adm.eggsFood-4.8)<1e-9,"admin multiplier changes eggs, not raw food")
 -- garbage never corrupts a run
 local g=T.newRunStats("g") T.noteFood(g,0/0,5,rate) T.noteFood(g,-3,5,rate) T.noteFood(g,"x" :: any,5,rate) T.noteFood(g,10,0/0,rate)
 assert(g.foodRaw==10 and g.eggsFood==0,"garbage ignored")
 -- weather: a thunderstorm (eggs x1.4) inflates the DERIVED food, never the real one
 local eggs=math.floor(sum*rate*1.4)
 local ev=T.runEnd({runSeconds=300,reason="ManualExit",eggs=eggs,nests=1,crystals=30,foodCatchRate=rate,foodRaw=stats.foodRaw,eggsFood=stats.eggsFood,weatherSeconds=180})
 assert(ev.food_raw==sum,"food_raw is the real food")
 assert(ev.food>ev.food_raw,"the derived field overstates in weather: "..ev.food.." vs "..ev.food_raw)
 assert(math.abs(ev.food/ev.food_raw-1.4)<0.02,"derived food is inflated by about the weather multiplier")
 assert(ev.food_is_estimate==true and ev.eggs_food==math.floor(stats.eggsFood+0.5) and ev.weather_s==180)
 assert(T.runEnd({runSeconds=100,reason="Death",eggs=1,nests=0,crystals=0,weatherSeconds=9999}).weather_s==100,"weather seconds never exceed the run")
 local plain=T.runEnd({runSeconds=60,reason="Death",eggs=1,nests=0,crystals=0})
 assert(plain.food_raw==nil and plain.eggs_food==nil and plain.weather_s==nil,"untracked fields are absent, not guessed")
 -- weather log: events -> seconds overlapping the run
 local log=T.newWeatherLog()
 T.weatherChanged(log,nil,0) T.weatherChanged(log,"clear",10)
 T.weatherChanged(log,"thunder",100) T.weatherChanged(log,"thunder",110) -- repeated id is not a new interval
 T.weatherChanged(log,"clear",220)
 T.weatherChanged(log,"rain",400)
 assert(T.weatherSeconds(log,0,300)==120,"closed interval inside the run")
 assert(T.weatherSeconds(log,150,300)==70,"run starts inside the event")
 assert(T.weatherSeconds(log,0,450)==120+50,"an open event counts up to the run end")
 assert(T.weatherSeconds(log,230,390)==0 and T.weatherSeconds(log,5,5)==0 and T.weatherSeconds(log,9,3)==0)
 T.weatherChanged(log,"",500)
 assert(T.weatherSeconds(log,0,600)==120+100,"empty id also ends an event")
 local big=T.newWeatherLog()
 for i=1,200 do T.weatherChanged(big,"rain",i*10) T.weatherChanged(big,"clear",i*10+5) end
 assert(#big.closed==T.MaxWeatherIntervals,"the weather log is bounded")
 -- golden lines for the python report check (real food in a weather run beside a calm run)
 print(T.line(T.runEnd({runSeconds=300,reason="ManualExit",eggs=97,nests=4,crystals=183,foodCatchRate=rate,foodRaw=3710,eggsFood=89,weatherSeconds=120})))
 print(T.line(T.runEnd({runSeconds=300,reason="Disconnect",eggs=15,nests=1,crystals=30,foodCatchRate=rate,foodRaw=625,eggsFood=15,weatherSeconds=0})))
end
-- BD-649..653: counters, labels, errors, visit, funnel steps, server id, budgets
do
 local C=T.newCounters()
 assert(T.bump(C,"movement_rejects",nil,1) and T.bump(C,"rate_limited","Chest",1) and T.bump(C,"rate_limited","Chest",1) and T.bump(C,"rate_limited","Gift",1))
 assert(not T.bump(C,"user_id","Chest",1) and not T.bump(C,"hatches","Chest",0) and not T.bump(C,"hatches","Chest",0/0),"unknown names and empty amounts are refused")
 assert(T.bump(C,"rate_limited","bad \"label\"",1) and T.bump(C,"rate_limited",string.rep("x",50),1),"a bad label becomes Other")
 local taken=T.takeCounts(C)
 local seen={} for _,it in taken do seen[it.name.."|"..(it.service or "")]=it.value end
 assert(seen["movement_rejects|"]==1 and seen["rate_limited|Chest"]==2 and seen["rate_limited|Gift"]==1 and seen["rate_limited|Other"]==2,"counts per service")
 assert(#T.takeCounts(C)==0 and C.keys==0,"flush resets")
 -- a spammer or a hostile label cannot grow the table: keys are capped, the rest folds into Other
 for i=1,500 do T.bump(C,"rate_limited","S"..i,1) end
 assert(C.keys<=T.MaxCounterKeys+1,"bounded keys: "..C.keys)
 local total=0 for _,it in T.takeCounts(C) do total+=it.value end
 assert(total==500,"nothing lost when folded: "..total)
 local ce=T.countEvent("rate_limited",12,"Chest")
 assert(T.line(ce)=='[BD-TELEMETRY] {"event":"count","name":"rate_limited","service":"Chest","value":12}',T.line(ce))
 -- visit at join and the random per-server id
 local id=T.serverId(function(lo,hi) return 4660 end)
 assert(id=="12341234" and #id==8 and T.cleanId(id)==id and T.cleanId("a\"b")==nil and T.cleanId(string.rep("a",17))==nil and T.cleanId(5)==nil)
 local vline=T.line(T.visit(id,1760000000))
 assert(vline=='[BD-TELEMETRY] {"event":"visit","server":"12341234","at":1760000000}',vline)
 assert(T.visit("bad id",nil).server==nil,"a bad id never reaches the line")
 -- funnel steps: seconds since join, set once, unknown steps ignored
 local s2=T.newSession(100,"Sanctuary")
 T.noteStep(s2,"run",112) T.noteStep(s2,"food",130) T.noteStep(s2,"food",999) T.noteStep(s2,"egg",400.4) T.noteStep(s2,"bogus",5)
 local e2=T.sessionEnd(s2,700,{server=id,at=1760000600})
 assert(e2.first_run_s==12 and e2.first_food_s==30 and e2.first_egg_s==300 and e2.first_hatch_s==nil and e2.server==id and e2.at==1760000600,"steps in session_end")
 local fl=T.line(e2)
 assert(fl:find('"first_run_s":12',1,true) and fl:find('"server":"12341234"',1,true))
 -- privacy: every key of every new event is on the whitelist, no id or name can be put into a line
 local okKeys={event=1,server=1,at=1,name=1,service=1,value=1,script=1,text=1,total_s=1,runs=1,hub_s=1,run_s=1,first_run_s=1,first_food_s=1,first_egg_s=1,first_hatch_s=1,first_shop_s=1}
 for _,ev in {T.visit(id,1),ce,e2,T.errorEvent(T.newErrorState(),"boom",nil,nil) :: any} do
  for k in ev do assert(okKeys[k],"unexpected field "..k) end
 end
 -- script errors: scrubbed, bounded, deduplicated
 local E=T.newErrorState()
 local msg="ServerScriptService.Bootstrap:123: attempt to index nil with 'x' for Workspace.BobTheBuilder.Humanoid user 1234567890 \"q\" \\ {}"
 local ev1=T.errorEvent(E,msg,nil,{"BobTheBuilder","ab"})
 assert(ev1 and ev1.event=="script_error" and ev1.script=="Other",ev1 and ev1.text)
 assert(not ev1.text:find("BobTheBuilder") and not ev1.text:find("1234567890") and not ev1.text:find('"') and not ev1.text:find("\\",1,true) and ev1.text:find("<p>",1,true),ev1.text)
 assert(T.errorEvent(E,msg,nil,{"BobTheBuilder"})==nil,"the same text is logged once")
 assert(T.errorEvent(T.newErrorState(),"x","Boot",nil).script=="Boot" and T.errorEvent(T.newErrorState(),"x","a b",nil).script=="Other")
 assert(#T.scrub(string.rep("a",500),nil)==T.MaxErrorTextLength,"text is cut")
 assert(T.scrub("line one\nline two with Bob",{"Bob"})=="line one","only the first line")
 assert(T.scrub("hello ab",{"ab"})=="hello ab","names under 3 characters are not scrubbed (they would eat normal words)")
 for i=1,100 do T.errorEvent(E,"different error number "..string.rep("z",i),nil,nil) end
 assert(E.distinct==T.MaxErrorTexts,"distinct texts are bounded per server: "..E.distinct)
 assert(T.errorEvent(T.newErrorState(),"",nil,nil)==nil,"empty text is not logged")
 -- log volume budget: the count / error bucket holds 20 a minute and 300 a server; one hour with 24 services spamming still stays under it
 local cl=T.newLimiter(T.MaxCountLinesPerServer,T.MaxCountLinesPerMinute)
 local lines,C2=0,T.newCounters()
 for t=0,3600*6,T.RollupSeconds do
  for i=1,24 do T.bump(C2,"rate_limited","Svc"..i,1000) end
  for _,n in {"movement_rejects","script_errors","shop_purchases","hatches","fusions"} do T.bump(C2,n,nil,5) end
  for _ in T.takeCounts(C2) do if T.allow(cl,nil,t) then lines+=1 end end
  for i=1,T.MaxErrorTexts*3 do if T.allow(cl,nil,t) then lines+=1 end end
 end
 assert(lines==T.MaxCountLinesPerServer,"count lines stop at the cap over six hours: "..lines)
 assert(#T.takeCounts(T.newCounters())==0,"a quiet server prints nothing")
 -- the main event bucket is untouched by the count bucket
 local mainLim=T.newLimiter()
 assert(T.allow(mainLim,nil,0),"run_end budget is separate")
 -- golden lines for the python report check (prefixed NEW|, read by playtest_report.py)
 local gsess=T.newSession(0,"Sanctuary")
 print("NEW|"..T.line(T.visit(id,1760000000)))
 T.noteStep(gsess,"run",20) T.noteStep(gsess,"food",35) T.noteStep(gsess,"egg",340) T.noteStep(gsess,"hatch",360) T.noteStep(gsess,"shop",400)
 T.moved(gsess,20,"Island") T.moved(gsess,320,"Sanctuary") T.runFinished(gsess)
 print("NEW|"..T.line(T.sessionEnd(gsess,500,{server=id,at=1760000500})))
 print("NEW|"..T.line(T.countEvent("movement_rejects",3,nil)))
 print("NEW|"..T.line(T.countEvent("rate_limited",7,"Chest")))
 print("NEW|"..T.line(T.countEvent("rate_limited",2,"Gift")))
 print("NEW|"..T.line(T.countEvent("shop_purchases",4,"buyPotion")))
 print("NEW|"..T.line(T.countEvent("hatches",9,"Egg")))
 print("NEW|"..T.line(T.errorEvent(T.newErrorState(),"ServerScriptService.Thing:9: attempt to index nil","Thing",nil) :: any))
end
-- emit the golden lines for the python report check
print(T.line(T.runEnd({runSeconds=300,reason="ManualExit",eggs=15,nests=1,crystals=30,foodCatchRate=12/500})))
print(T.line(T.runEnd({runSeconds=300,reason="Death",eggs=12,nests=1,crystals=20,foodCatchRate=12/500})))
print(T.line(se))
print("Telemetry passed")
'''

def static():
    cfg = (ROOT / 'src/shared/Config.luau').read_text(encoding='utf-8')
    assert '    RunTelemetryEnabled = false,' in cfg, 'flag is false in source'
    svc = (ROOT / 'src/server/TelemetryService.luau').read_text(encoding='utf-8')
    assert 'RunTelemetryEnabled' in svc and 'pcall' in svc and 'RunTelemetry.allow' in svc
    for banned in ('UserId', 'DataStore', 'ProfileRepository', 'SetAttribute', 'FireClient'):
        assert banned not in svc, f'TelemetryService must stay a read-only anonymous observer ({banned})'
    assert 'Telemetry.runSettled' in (ROOT / 'src/server/Bootstrap.server.luau').read_text(encoding='utf-8')
    for banned in ('GetUserIdFromNameAsync', 'JobId', 'HttpService'):
        assert banned not in svc, f'TelemetryService must not use {banned} (the server id is random, BD-653)'
    assert 'ScriptContext' in svc and 'BindToClose' in svc and 'MovementRejectCount' in svc and 'RunTelemetry.visit' in svc
    # BD-650/652: every counting hook is flag-gated and wrapped in a pcall (telemetry must never throw into gameplay)
    hooks = {'ChestService': 5, 'CollectionService': 2, 'MutationService': 2, 'GiftService': 2, 'ObjectiveService': 1, 'SkinService': 1,
             'FusionService': 2, 'ProgressionService': 1, 'ProfileRepository': 1}
    for name, expected in hooks.items():
        text = (ROOT / f'src/server/{name}.luau').read_text(encoding='utf-8')
        found = text.count('pcall(function() require(script.Parent.TelemetryHook).count(')
        assert found == expected, f'{name}: {found} telemetry hooks, expected {expected}'
        assert text.count('TelemetryHook') == found, f'{name}: every TelemetryHook use must be the pcall-wrapped call'
        assert len(re.findall(r'RunTelemetryEnabled\s*==\s*true', text)) >= found, f'{name}: hooks must be flag-gated'
    hook = (ROOT / 'src/server/TelemetryHook.luau').read_text(encoding='utf-8')
    assert 'RunTelemetryEnabled ~= true then return end' in hook and 'UserId' not in hook
    for name in ('ProfileCollection', 'ProfileEggs', 'ProfileFusion', 'ProfileObjectives', 'ProfileShop', 'ProfileSkins'):
        assert 'shared.admitAs("' + name + '")' in (ROOT / f'src/server/{name}.luau').read_text(encoding='utf-8'), name
    prof = (ROOT / 'tools/release_profiles.py').read_text(encoding='utf-8')
    assert '_flag_off("RunTelemetryEnabled"' in prof and 'Rule("RunTelemetryEnabled", "set", True' in prof

ZERO_COST = ('trackTelemetry = Config.RunTelemetryEnabled == true', 'if trackTelemetry then claim.candidate.raw', 'if trackTelemetry then telemetry().noteFood(')

def static_bd575():
    """BD-575: telemetry off = zero cost; the food hook is batched and memory-only. The dynamic proof (TelemetryService never even
    required with the flag off, one call per player per tick, raw = sum of pickups) runs in tools/verify_gameplay.py."""
    food = (ROOT / 'src/server/FoodService.luau').read_text(encoding='utf-8')
    for needle in ZERO_COST:
        assert needle in food, 'FoodService food hook missing: ' + needle
    assert food.count('Config.RunTelemetryEnabled ==') == 1, 'the flag is read once per tick, not per pickup'
    assert food.count('require(script.Parent.TelemetryService)') == 1, 'lazy require inside telemetry() only'
    top = food.split('function FoodService.start', 1)[0]
    assert top.count('TelemetryService') == 1 and 'local telemetryService: any = nil' in top, 'no top-level TelemetryService require'
    assert food.count('telemetry().noteFood(') == 1, 'one batched call per player per tick (candidate loop, not the claim loop)'
    claim_loop = food.split('for food, claim in claims do', 1)[1].split('for _, candidate in candidates do', 1)[0]
    assert 'noteFood(' not in claim_loop, 'no per-pickup telemetry call'
    svc = (ROOT / 'src/server/TelemetryService.luau').read_text(encoding='utf-8')
    for fn in ('function TelemetryService.noteFood', 'function TelemetryService.runSettled', 'function TelemetryService.start'):
        body = svc.split(fn, 1)[1].split('\nend\n', 1)[0]
        assert 'if not enabled() then return end' in body, fn + ' must return at once while the flag is off'
    boot = (ROOT / 'src/server/Bootstrap.server.luau').read_text(encoding='utf-8')
    assert 'Telemetry.runSettled(player, reason, runSeconds, settledOutcome, runId)' in boot, 'settlement passes the runId'
    assert '__mode = "k"' in svc, 'run stats are weak-keyed by Player'

def check_report_columns(runs, sessions):
    s = report.summarize(runs, sessions)
    text = report.render(s)
    for column in ('food/min', 'eggs/min', 'eggs/500 food', 'vs target (15 eggs / 5 min)', 'weather min', 'food-only vs target'):
        assert column in text, 'report column missing: ' + column
    assert 'derived' in text.lower(), 'the derived food field is marked in the report'
    rows = s['per_run']
    assert len(rows) == 4 and all(r['food_real'] for r in rows[:2]), rows
    a, b = rows[0], rows[1]
    assert a['food'] == 3710 and a['food_per_min'] == 742.0 and a['eggs_per_min'] == 19.4, a
    assert a['eggs_per_500_food'] == round(97 * 500 / 3710, 2) and a['weather_min'] == 2.0, a
    assert a['vs_target'] == round(97 / 15, 2) and a['vs_target_food_only'] == round(89 / 15, 2), a
    assert b['vs_target'] == 1.0 and b['food_per_min'] == 125.0, b
    # the two lines without food_raw (older logs) fall back to the derived food and are marked with ~
    assert rows[2]['food_real'] is False and '~625' in text, 'derived food carries a ~ mark'
    only_real = report.summarize(runs[:2], [])
    assert only_real['food_source'] == 'real' and only_real['food_per_min'] == round((3710 + 625) * 60 / 600, 1), only_real
    # the derived field stays reported and overstates when weather multiplies eggs (derived 97/0.024 = 4,042 vs real 3,710)
    assert only_real['food_per_min_derived'] > only_real['food_per_min'], only_real
    assert only_real['weather_share'] == round(120 / 600, 3), only_real
    assert s['food_source'] == 'mixed', s
    print('Report columns passed: food/min, eggs/min, eggs/500 food, vs target (15 eggs / 5 min), weather min; derived food marked')

def check_playtest_report(lines):
    """BD-649..653: the lines the REAL RunTelemetry module prints are read by tools/playtest_report.py, and the numbers the game now
    records are no longer 'not recorded yet'."""
    import playtest_report as pr
    assert len(lines) == 8 and all(x.startswith('[BD-TELEMETRY] {') for x in lines), lines
    data = pr.read_lines(lines)
    assert data['bad_lines'] == 0 and data['unknown_events'] == 0, data
    assert data['visits'] == 1 and data['servers'] == {'12341234'}, data
    assert data['counts'] == {'movement_rejects': 3, 'rate_limited': 9, 'shop_purchases': 4, 'hatches': 9}, data['counts']
    assert data['counts_by']['rate_limited'] == {'Chest': 7, 'Gift': 2}, data['counts_by']
    assert data['errors'] == [{'script': 'Thing', 'text': 'ServerScriptService.Thing:9: attempt to index nil'}], data['errors']
    s = data['sessions'][0]
    assert (s['first_run_s'], s['first_food_s'], s['first_egg_s'], s['first_hatch_s'], s['first_shop_s']) == (20, 35, 340, 360, 400), s
    report = pr.analyse(data, rate=(12.0, 500.0))
    open_gaps = [label for label, _ in report['gaps']]
    assert open_gaps == [pr.GAPS['crashes'][0], pr.GAPS['shop_opens'][0]] or sorted(open_gaps) == sorted([pr.GAPS['crashes'][0], pr.GAPS['shop_opens'][0]]), open_gaps
    assert report['game_recorded'] is True and report['visits'] == 1 and report['servers'] == 1
    print('Playtest report check passed: counts, per-service rate_limited, script error text, visit, funnel steps, server id read from the real lines')

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--runner', required=True); a = ap.parse_args()
    static()
    static_bd575()
    mod = '(function()\n' + (ROOT / 'src/shared/RunTelemetry.luau').read_text(encoding='utf-8') + '\nend)()'
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / 't.luau'; p.write_text(f'local RT={mod}\n{BODY}', encoding='utf-8')
        r = subprocess.run([a.runner, str(p)], capture_output=True, text=True)
    print(r.stdout, end=''); print(r.stderr, end='')
    if r.returncode: raise SystemExit(r.returncode)
    all_lines = r.stdout.splitlines()
    new_lines = [x[4:] for x in all_lines if x.startswith('NEW|')]
    check_playtest_report(new_lines)
    runs, sessions = report.parse([x for x in all_lines if not x.startswith('NEW|')])
    s = report.summarize(runs, sessions)
    assert s['runs'] == 4 and s['sessions'] == 1, s
    first = report.summarize(runs[2:], sessions)
    assert first['eggs_per_5min'] == 13.5 and first['food_source'] == 'derived', first
    assert first['food_per_min'] == round((625 + 500) * 60 / 600, 1) and first['end_reasons'] == {'ManualExit': 1, 'Death': 1}, first
    assert first['runs_per_session'] == 2 and first['hub_share'] == round(120 / 460, 3), first
    print('Report check passed:', first['eggs_per_5min'], 'eggs per 5 min,', first['food_per_min'], 'derived food per min')
    check_report_columns(runs, sessions)

main()
