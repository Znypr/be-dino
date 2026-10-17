"""BD-426: offline checks for the run/session telemetry. Runs the pure shared/RunTelemetry in Luau (event shape, privacy,
rate limit, session accounting), checks the flag wiring statically, and feeds the log lines into tools/telemetry_report.py.

    python tools/verify_telemetry.py --runner /path/to/luau
"""
from pathlib import Path
import argparse, subprocess, sys, tempfile
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
    runs, sessions = report.parse(r.stdout.splitlines())
    s = report.summarize(runs, sessions)
    assert s['runs'] == 4 and s['sessions'] == 1, s
    first = report.summarize(runs[2:], sessions)
    assert first['eggs_per_5min'] == 13.5 and first['food_source'] == 'derived', first
    assert first['food_per_min'] == round((625 + 500) * 60 / 600, 1) and first['end_reasons'] == {'ManualExit': 1, 'Death': 1}, first
    assert first['runs_per_session'] == 2 and first['hub_share'] == round(120 / 460, 3), first
    print('Report check passed:', first['eggs_per_5min'], 'eggs per 5 min,', first['food_per_min'], 'derived food per min')
    check_report_columns(runs, sessions)

main()
