"""Prepare a bounded Studio sync with expected source checks to prevent overwriting other edits."""
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
FILES={
    'src/shared/Config.luau':['ReplicatedStorage','Shared','Config'],
    'src/shared/UIIconAssets.luau':['ReplicatedStorage','Shared','UIIconAssets'],
    'src/shared/NavigationArtwork.luau':['ReplicatedStorage','Shared','NavigationArtwork'],
    'src/shared/UITheme.luau':['ReplicatedStorage','Shared','UITheme'],
    'src/server/ProfileRepository.luau':['ServerScriptService','Server','ProfileRepository'],
    'src/server/ChestService.luau':['ServerScriptService','Server','ChestService'],
    'src/server/RunLifecycle.luau':['ServerScriptService','Server','RunLifecycle'],
    'src/client/Bootstrap.client.luau':['StarterPlayer','StarterPlayerScripts','Client','Bootstrap'],
}
if __name__=='__main__':
    rows=[]
    for path,target in FILES.items():
        expected=subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT).decode('utf-8').replace('\r\n','\n')
        rows.append(dict(path=target,expected=expected,source=(ROOT/path).read_text(encoding='utf-8')))
    destination=ROOT/'resources/ui/v2/icons/.egg-nest-studio-sync.json'
    destination.write_text(json.dumps(rows),encoding='utf-8')
    print('Prepared',len(rows),'source-checked scripts')
