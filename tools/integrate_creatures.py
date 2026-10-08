"""Package authored Blender runtime exports without changing game balance."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
rows=sorted((ROOT/'resources/creatures').glob('*.json'))
for path in rows:
    folder=ROOT/'src/shared'/('CreatureGenes' if path.stem.endswith('-genes') else 'CreatureData')
    folder.mkdir(exist_ok=True)
    name=path.stem.removesuffix('-genes')
    chunks=folder/'Chunks';chunks.mkdir(exist_ok=True)
    raw=path.read_text();parts=[raw[i:i+95000] for i in range(0,len(raw),95000)]
    for i,part in enumerate(parts):
        (chunks/(name+'_'+str(i+1)+'.luau')).write_text('return [==['+part+']==]\n',encoding='utf-8')
    (folder/(name+'.luau')).write_text('-- Generated from authored Blender source.\nreturn '+ '..'.join('require(script.Parent.Chunks.'+name+'_'+str(i+1)+')' for i in range(len(parts)))+'\n',encoding='utf-8')
print(f"Regenerated {len(rows)} authored data modules; catalog unchanged")
