"""docs/128: offline checks for the playtest feedback tool. Runs the pure shared/PlaytestFeedback in Luau (sanitize, rate limit,
log line, escaping, privacy), checks the server/client/flag wiring statically and feeds the output into tools/feedback_report.py.

    python tools/verify_feedback.py --runner /path/to/luau
"""
from pathlib import Path
import argparse, re, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import feedback_report as report

BODY = r'''
local F=PF
assert(F.sanitize(nil)==nil and F.sanitize("x")==nil and F.sanitize({})==nil,"empty payload rejected")
local c=F.sanitize({fun=3,level=9,looks=-1,text=string.rep("a",5000)})
assert(c.fun==3 and c.level==0 and c.looks==0 and #c.text<=F.MaxTextLength*4,"clamped")
assert(F.sanitize({text=123,fun=0})==nil,"non-string text ignored")
assert(F.sanitize({fun=2}).fun==2)
-- rate limit: 1 per 2 min, 10 per session
local s=F.newSession()
assert(F.allow(s,0)) local ok,why=F.allow(s,119) assert(not ok and why=="wait")
assert(F.allow(s,120))
local n=2 for i=1,30 do if F.allow(s,120+i*121) then n+=1 end end
assert(n==10,"session cap "..n)
local ok2,why2=F.allow(s,1e6) assert(not ok2 and why2=="limit")
-- BD-441: button hidden on minute zero, shown after a run ended or for a returning player outside a run
assert(not F.showButton(nil) and not F.showButton({}) and not F.showButton({runActive=true,foundEgg=true}))
assert(not F.showButton({foundEgg=false,runActive=false,sawRunEnd=false}))
assert(F.showButton({sawRunEnd=true,runActive=false}) and F.showButton({foundEgg=true,runActive=false}))
-- event and line: whitelisted keys, escaping, no ids
local e=F.event({fun=3,level=2,looks=1,filteredText='say "hi" \\ ###\nnew',runs=3,location="Run",species="trex",extra="x"})
assert(e.location=="Run" and e.runs==3 and e.species=="trex" and e.extra==nil)
local bad=F.event({fun=2,level=2,looks=2,filteredText=nil,runs=0/0,location="<b>",species="<script>"})
assert(bad.location=="Hub" and bad.species=="script" and bad.text=="" and bad.runs==0)
local allowed={event=1,fun=1,level=1,looks=1,runs=1,location=1,species=1,text=1}
for k in e do assert(allowed[k],"unexpected field "..k) end
local line=F.line(e)
assert(line:sub(1,#F.LogPrefix)==F.LogPrefix and not line:lower():find("userid"))
assert(not line:find("\n"),"one line")
local long=F.event({fun=1,level=1,looks=1,filteredText=string.rep("b",500),runs=1,location="Hub",species="compy"})
assert(utf8.len(long.text)==F.MaxTextLength)
print(F.line(e))
print(F.line(F.event({fun=1,level=3,looks=2,filteredText="",runs=1,location="Hub",species="compy"})))
print("Feedback passed")
'''

def static():
    cfg = (ROOT / 'src/shared/Config.luau').read_text(encoding='utf-8')
    assert '    PlaytestFeedbackEnabled = false,' in cfg, 'flag is false in source'
    svc = (ROOT / 'src/server/FeedbackService.luau').read_text(encoding='utf-8')
    assert 'PlaytestFeedbackEnabled' in svc and 'FilterStringAsync' in svc and 'Feedback.allow' in svc and 'pcall' in svc
    for banned in ('DataStore', 'ProfileRepository', 'SetAttribute', 'tostring(player'):
        assert banned not in svc, f'FeedbackService must stay anonymous and read-only ({banned})'
    # the only print is the line built from the FILTERED text; raw text only goes into the filter
    assert svc.count('print(') == 1 and 'filteredText = filtered(' in svc, 'only filtered text may be printed'
    assert svc.count('clean.text') == 1, 'raw text is used once, as the filter input'
    cl = (ROOT / 'src/client/FeedbackClient.client.luau').read_text(encoding='utf-8')
    assert 'PlaytestFeedbackEnabled' in cl and 'UDim2.fromOffset(120, 48)' in cl, 'button >= 44 px and gated'
    for _, h in re.findall(r'fromOffset\((\d+), (\d+)\), UDim2\.fromOffset\(\d+, y\)', cl):
        assert int(h) >= 44
    assert 'open.Visible = false' in cl and 'Rules.showButton' in cl, 'BD-441 button hidden until first run ends'
    assert 'FeedbackService' in (ROOT / 'src/server/Bootstrap.server.luau').read_text(encoding='utf-8')
    prof = (ROOT / 'tools/release_profiles.py').read_text(encoding='utf-8')
    assert '_flag_off("PlaytestFeedbackEnabled"' in prof and 'Rule("PlaytestFeedbackEnabled", "set", True' in prof

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--runner', required=True); a = ap.parse_args()
    static()
    mod = '(function()\n' + (ROOT / 'src/shared/PlaytestFeedback.luau').read_text(encoding='utf-8') + '\nend)()'
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / 't.luau'; p.write_text(f'local PF={mod}\n{BODY}', encoding='utf-8')
        r = subprocess.run([a.runner, str(p)], capture_output=True, text=True)
    print(r.stdout, end=''); print(r.stderr, end='')
    if r.returncode: raise SystemExit(r.returncode)
    s = report.summarize(report.parse(r.stdout.splitlines()))
    assert s['count'] == 2 and s['fun']['average'] == 2.0 and s['level']['average'] == 2.5, s
    assert s['by_location'] == {'Run': 1, 'Hub': 1} and len(s['comments']) == 1 and '"hi"' in s['comments'][0]['text'], s
    print('Report check passed:', s['count'], 'entries')

main()
