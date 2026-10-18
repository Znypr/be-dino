"""Shared runner for the BD-239..241 combat verifiers (pure modules in src/shared, run with the luau runner)."""
import argparse, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MODULES = ['CombatConfig', 'CombatStats', 'CombatState', 'CombatTeamUp']

SIM = r"""
-- Offline fight sim (equal-rules team-up sim: plain Stats.hit, NOT the BD-1025 size-difference rule Stats.hitScored that CombatRules uses): 0.1 s steps, cooldown = Cfg.BiteCooldownSeconds, each fighter hits the first living enemy. a/b = lists of {c=class,s=scale}.
local function fight(a,b,crowd)
  local function mk(l) local o={} for i,f in l do o[i]={c=f.c,s=f.s,st=State.new(Stats.maxHp(f.c,f.s)),cd=0.1*i%Cfg.BiteCooldownSeconds,id=tostring(i)} end return o end
  local A,B=mk(a),mk(b); local LA,LB=TeamUp.newLedger(),TeamUp.newLedger()
  local t,firstDown=0,nil
  local function alive(l) local n=0 for _,f in l do if f.st.phase=="Alive" then n+=1 end end return n end
  local function first(l) for _,f in l do if f.st.phase=="Alive" then return f end end end
  while t<300 do
    t+=0.1
    for side=1,2 do
      local atk,def,led=if side==1 then A else B, if side==1 then B else A, if side==1 then LB else LA
      for _,f in atk do
        f.cd-=0.1
        local tg=first(def)
        if f.st.phase=="Alive" and f.cd<=0 and tg then
          f.cd=Cfg.BiteCooldownSeconds
          local x=if crowd then TeamUp.crowdMultiplier(led,t) else 1
          local _,down=State.damage(tg.st,Stats.hit(f.c,f.s,tg.c,tg.s,0,x),t)
          TeamUp.record(led,side..f.id,Stats.hit(f.c,f.s,tg.c,tg.s,0,x),t)
          if down and not firstDown then firstDown=t end
        end
      end
    end
    local na,nb=alive(A),alive(B)
    if na==0 or nb==0 then local rem=0 for _,f in (if nb==0 then A else B) do rem+=f.st.hp/f.st.maxHp end return (if nb==0 then "A" else "B"),t,(if nb==0 then na else nb),firstDown,rem end
  end
  return "none",t,0,firstDown
end
local function team(n,c,s) local l={} for i=1,n do l[i]={c=c,s=s} end return l end
local S1,S2,S3,S4=1,Stats.scale(1500),Stats.scale(8000),Stats.scale(25500)
"""


def module(name):
    return '(function()\n' + (ROOT / 'src/shared' / f'{name}.luau').read_text(encoding='utf-8') + '\nend)()'


def script(body):
    # require(script.Parent.X) is stubbed: script.Parent is a table of the loaded modules, require returns its argument.
    parts = ['local M={}', 'local script={Parent=M}', 'local require=function(x) return x end']
    for n in MODULES:
        parts.append(f'M.{n}={module(n)}')
    parts.append('local Cfg,Stats,State,TeamUp=M.CombatConfig,M.CombatStats,M.CombatState,M.CombatTeamUp')
    parts.append(SIM)
    parts.append(body)
    return '\n'.join(parts)


def run(body, name):
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / f'{name}.luau'
        path.write_text(script(body), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        print(result.stdout, end='')
        print(result.stderr, end='')
        raise SystemExit(result.returncode)
