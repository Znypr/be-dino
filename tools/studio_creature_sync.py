"""Prepare current source scripts for the local Studio review build."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
paths=sorted((root/'src').rglob('*.luau'))
rows=[]
for p in paths:
    relative=p.relative_to(root/'src')
    folder={'shared':['ReplicatedStorage','Shared'],'server':['ServerScriptService','Server'],'client':['StarterPlayer','StarterPlayerScripts','Client'],'loading':['ReplicatedFirst','Loading']}[relative.parts[0]]
    folder+=list(relative.parts[1:-1])
    name=p.name.removesuffix('.client.luau').removesuffix('.server.luau').removesuffix('.luau')
    rows.append({'folder':folder,'name':name,'class':'LocalScript' if '.client.' in p.name else 'Script' if '.server.' in p.name else 'ModuleScript','source':p.read_text()})
(root.parent/'Dino_Models/studio-creature-sync.json').write_text(json.dumps(rows))
print('Prepared',len(rows),'scripts')
