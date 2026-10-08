"""Compile every Luau source. This is a syntax check, not Roblox type analysis."""
from pathlib import Path
import argparse,subprocess
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--compiler',required=True);args=parser.parse_args()
 paths=sorted((ROOT/'src').rglob('*.luau'))
 for path in paths:subprocess.run([args.compiler,str(path)],stdout=subprocess.DEVNULL,check=True)
 print(f'Compiled {len(paths)} Luau sources successfully')
