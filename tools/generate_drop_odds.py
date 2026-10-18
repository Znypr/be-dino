"""Regenerates docs/85-drop-odds.md from the real code (RarityCurve, Config, ProgressionConfig), BD-184.
Usage: python tools/generate_drop_odds.py --runner path/to/luau.exe   (add --check to fail when the doc is stale)
"""
from pathlib import Path
import argparse,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/'docs'/'85-drop-odds.md'
def module(path):return '(function()\n'+(ROOT/path).read_text()+'\nend)()'
DUMP=r'''
local function out(...) print(table.concat({...},"|")) end
for i,n in Curve.Names do out("LADDER",n,Curve.weights(6)[i]*100,Curve.price(i-1,60),Curve.price(i-1,100)) end
for _,row in Config.ChestSpeciesWeights do out("SPECIES",Config.SpeciesDisplayNames[row.speciesId],Config.SpeciesRarityNames[Config.SpeciesRarities[row.speciesId]],row.weight) end
for _,c in Progression.EggColors do out("COLOR",c.name,c.rarity,100*c.weight/Progression.EggColorWeightScale) end
out("MUT",Config.BigChance*100,Config.ShinyChance*100,Config.NestLuckTiers[1].bigChance*100,Config.NestLuckTiers[1].shinyChance*100)
local total=0 for _,e in Progression.Weather do total+=e.weight end
for _,e in Progression.Weather do out("WEATHER",e.name,e.rarity,100*e.weight/total) end
out("CYCLE",Progression.WeatherInterval,Progression.WeatherDuration)
local pw=0 for _,r in Progression.PotionShop.Rarities do pw+=Progression.PotionShop.RarityWeights[r] end
for _,r in Progression.PotionShop.Rarities do out("POTION",r,100*Progression.PotionShop.RarityWeights[r]/pw) end
for _,po in Progression.Potions do out("POTIONPRICE",po.name,po.rarity,po.price) end
for _,a in Progression.Auras do out("AURA",a.name,a.rarity,a.price) end
for _,t in Progression.Trails do out("TRAIL",t.name,t.rarity,t.price) end
'''
PATTERNS=[('Blank','Common'),('Freckles','Common'),('Round spots','Common'),('Horizontal bands','Uncommon'),('Bold patches','Uncommon'),('Wavy stripes','Rare'),('Emerald islands','Epic'),('Diamond scales','Legendary')]
def pct(x):
    s=('%.4g'%x)
    return (s if 'e' not in s else '%.6f'%x).rstrip('0').rstrip('.') if '.' in s else s
def one_in(p):
    v=100/p
    return f'{v:.2f}' if v<10 else f'{round(v):,}'
def render(rows):
    g=lambda k:[r[1:] for r in rows if r[0]==k]
    L=[]
    L.append('# 85 Drop odds: every rarity table (generated)\n')
    L.append('Generated from the repo by `python tools/generate_drop_odds.py --runner <luau.exe>` (`RarityCurve`, `Config`, `ProgressionConfig`). Do not edit by hand.')
    L.append('All numbers are **provisional**. Rarity follows the **exponential ladder** of [88](88-exponential-rarity.md) (BD-184): each tier is 5 times rarer than the one below. **Exception, dinosaur species (BD-1032, owner 2026-10-18):** species are steeper at the top so new kinds take time; tier totals are 91 / 8.5 / 0.42 / 0.07 / 0.01 ([82](82-species-rarity-tiers.md), [186](186-pattern-colour-indexes-and-slower-species.md) section 3, handbook conflict C-54 in [116](116-handbook-conflicts.md)). Odds below are for **one purchased egg** (no run-size boost).\n')
    L.append('## The shared ladder (`src/shared/RarityCurve.luau`)\n')
    L.append('| Tier | Chance | About 1 in | Aura price (base 60) | Trail price (base 100) |\n|---|---:|---:|---:|---:|')
    for n,p,a,t in g('LADDER'): L.append(f'| {n} | {pct(float(p))}% | {one_in(float(p))} | {int(float(a)):,} | {int(float(t)):,} |')
    L.append('\nSystems with fewer tiers use the first N rows and renormalise (five tiers: 80.02 / 16 / 3.2 / 0.64 / 0.128). Prices grow x2.8 per tier, rounded to two figures. Species stop at Legendary.\n')
    L.append('## Dinosaurs (22 species)\n')
    L.append('| # | Dinosaur | Rarity | % |\n|---:|---|---|---:|')
    tot={}
    for i,(n,r,w) in enumerate(g('SPECIES'),1):
        L.append(f'| {i} | {n} | {r} | {pct(float(w))}% |'); k=tot.setdefault(r,[0,0.0]);k[0]+=1;k[1]+=float(w)
    L.append('\n| Rarity | Species | % total |\n|---|---:|---:|')
    for r,(c,w) in tot.items(): L.append(f'| {r} | {c} | {pct(w)}% |')
    L.append('\nRun and nest eggs: a run of up to 15 eggs (a normal 5 minute run) and a single bought egg use the odds above. Above 15 eggs the Rare, Epic and Legendary rows rise step by step to **2x** at 120 eggs (and for a nest); Common and Uncommon are not lifted (`EggRarityBoostFreeEggs`, `EggRarityBoostMaxEggs`, `SpeciesRunBoost`). At 3 eggs a minute the first Uncommon comes after about 3 minutes and the first Rare or better after about 46 minutes (median); run `python tools/simulate_species_timing.py` for the table.')
    L.append('\n## Patterns (8, eggs and the dinosaurs hatched from them)\n')
    L.append('All 8 are equally likely (owner 2026-10-15: fusion needs the same species and pattern, so odds stay uniform for now).\n')
    L.append('| # | Pattern | Label | % |\n|---:|---|---|---:|')
    for i,(n,r) in enumerate(PATTERNS,1): L.append(f'| {i} | {n} | {r} | 12.5% |')
    L.append('\n## Colors (9, tiers of the ladder)\n')
    L.append('Each egg has **two** color slots rolled independently. Tier chances come from the ladder (six tiers, renormalised) and split inside a tier by the old weights.\n')
    L.append('| # | Color | Tier | % per slot | Both slots this color |\n|---:|---|---|---:|---:|')
    for i,(n,r,w) in enumerate(g('COLOR'),1):
        w=float(w);both=(w/100)**2
        L.append(f'| {i} | {n} | {r} | {pct(w)}% | 1 in {one_in(both*100)} |')
    big,shiny,nbig,nshiny=[float(x) for x in g('MUT')[0]]
    L.append('\n## Mutations\n')
    L.append('| Mutation | Tier | Chance | In a nest (lucky) |\n|---|---|---:|---:|')
    L.append(f'| BIG (size 1.2x) | Rare | {pct(big)}% | {pct(nbig)}% |')
    L.append(f'| Shiny (earned eggs, irregular weather only) | Epic | {pct(shiny)}% | {pct(nshiny)}% |')
    iv,du=[int(x) for x in g('CYCLE')[0]]
    cycle=iv+du;perh=3600/cycle
    L.append('\n## Weather events (how often each is chosen)\n')
    L.append(f'A new event starts after `WeatherInterval` {iv} s of clear sky and lasts `WeatherDuration` {du} s: one event every {cycle} s = **{perh:.1f} events per hour** ({perh/2:.1f} in a 30 minute session). **Weather is an exception to the ladder** (weather is a show, not loot): labels follow the tiers and a higher tier is always rarer, but the weights are flat enough that every event is seen regularly (docs/88).\n')
    L.append('| Event | Tier | Chance per event | About one every |\n|---|---|---:|---:|')
    for n,r,p in g('WEATHER'):
        p=float(p);hours=100/(p*perh)
        L.append(f'| {n} | {r} | {pct(p)}% | {hours*60:.0f} min |' if hours<2 else f'| {n} | {r} | {pct(p)}% | {hours:.0f} hours |')
    L.append('\n## Potion shop (rarity of each offer slot)\n')
    L.append('| Tier | Chance |\n|---|---:|')
    for r,p in g('POTION'): L.append(f'| {r} | {pct(float(p))}% |')
    L.append('\n## Aura prices (crystals)\n')
    L.append('| Aura | Tier | Price |\n|---|---|---:|')
    for n,r,p in g('AURA'): L.append(f'| {n} | {r} | {int(float(p)):,} |')
    L.append('\n## Trail prices (crystals)\n')
    L.append('| Trail | Tier | Price |\n|---|---|---:|')
    for n,r,p in g('TRAIL'): L.append(f'| {n} | {r} | {int(float(p)):,} |')
    L.append('')
    return '\n'.join(L)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--runner',required=True);ap.add_argument('--check',action='store_true');a=ap.parse_args()
    s='local Curve='+module('src/shared/RarityCurve.luau')+'\nlocal Config='+module('src/shared/Config.luau')+'\nlocal Progression='+module('src/shared/ProgressionConfig.luau')+'\n'+DUMP
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/'dump.luau';p.write_text(s)
        r=subprocess.run([a.runner,str(p)],capture_output=True,text=True)
    if r.returncode: print(r.stdout+r.stderr);raise SystemExit(1)
    text=render([l.split('|') for l in r.stdout.splitlines() if '|' in l])
    if a.check:
        raise SystemExit(0 if DOC.read_text(encoding='utf-8')==text else 'docs/85-drop-odds.md is stale: run tools/generate_drop_odds.py')
    DOC.write_text(text,encoding='utf-8',newline='\n');print('wrote',DOC)
