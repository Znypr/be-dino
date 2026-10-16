"""Shared runner for the BD-239..241 combat verifiers (pure modules in src/shared, run with the luau runner)."""
import argparse, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MODULES = ['CombatConfig', 'CombatStats', 'CombatState', 'CombatTeamUp']


def module(name):
    return '(function()\n' + (ROOT / 'src/shared' / f'{name}.luau').read_text(encoding='utf-8') + '\nend)()'


def script(body):
    # require(script.Parent.X) is stubbed: script.Parent is a table of the loaded modules, require returns its argument.
    parts = ['local M={}', 'local script={Parent=M}', 'local require=function(x) return x end']
    for n in MODULES:
        parts.append(f'M.{n}={module(n)}')
    parts.append('local Cfg,Stats,State,TeamUp=M.CombatConfig,M.CombatStats,M.CombatState,M.CombatTeamUp')
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
