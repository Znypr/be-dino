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
local allowed={event=1,duration_s=1,reason=1,food=1,food_is_estimate=1,eggs=1,nests=1,crystals=1,total_s=1,runs=1,hub_s=1,run_s=1}
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

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--runner', required=True); a = ap.parse_args()
    static()
    mod = '(function()\n' + (ROOT / 'src/shared/RunTelemetry.luau').read_text(encoding='utf-8') + '\nend)()'
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / 't.luau'; p.write_text(f'local RT={mod}\n{BODY}', encoding='utf-8')
        r = subprocess.run([a.runner, str(p)], capture_output=True, text=True)
    print(r.stdout, end=''); print(r.stderr, end='')
    if r.returncode: raise SystemExit(r.returncode)
    runs, sessions = report.parse(r.stdout.splitlines())
    s = report.summarize(runs, sessions)
    assert s['runs'] == 2 and s['sessions'] == 1 and s['eggs_per_5min'] == 13.5, s
    assert s['food_per_min'] == round((625 + 500) * 60 / 600, 1) and s['end_reasons'] == {'ManualExit': 1, 'Death': 1}, s
    assert s['runs_per_session'] == 2 and s['hub_share'] == round(120 / 460, 3), s
    print('Report check passed:', s['eggs_per_5min'], 'eggs per 5 min,', s['food_per_min'], 'food per min')

main()
