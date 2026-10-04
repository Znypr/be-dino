"""Embed the exact OBJ/MTL sources and RGBA icon exports in reproducible Luau modules."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def lua(v):
 if isinstance(v,dict):return '{'+','.join('['+json.dumps(k)+']='+lua(x) for k,x in v.items())+'}'
 if isinstance(v,list):return '{'+','.join(lua(x) for x in v)+'}'
 return json.dumps(v)
def compile_geometry():
 assets={}
 for p in sorted((ROOT/'resources/models').glob('*.obj')):
  colors={};mat=None
  for line in p.with_suffix('.mtl').read_text().splitlines():
   if line.startswith('newmtl '):mat=line.split()[1]
   elif line.startswith('Kd '):colors[mat]=[float(x) for x in line.split()[1:]]
  vertices=[];faces=[];palette=list(colors);current=0
  for line in p.read_text().splitlines():
   if line.startswith('v '):vertices.append([float(x) for x in line.split()[1:]])
   elif line.startswith('usemtl '):current=palette.index(line.split()[1])+1
   elif line.startswith('f '):faces.append([*[int(x) for x in line.split()[1:]],current])
  assets[p.stem]={'vertices':vertices,'faces':faces,'colors':[colors[x] for x in palette]}
 (ROOT/'src/shared/ResourceGeometry.luau').write_text('--!strict\n-- Generated from resources/models OBJ/MTL.\nreturn '+lua(assets)+'\n')
 return assets

def compile_icons():
 from PIL import Image
 rasters={}
 for p in sorted((ROOT/'resources/ui/icons').glob('*.png')):
  im=Image.open(p).convert('RGBA').resize((64,64),Image.Resampling.LANCZOS);runs=[];prev=None;count=0
  for rgba in im.getdata():
   value=sum(c<<(8*i) for i,c in enumerate(rgba))
   if value==prev:count+=1
   else:
    if count:runs.extend([count,prev])
    prev=value;count=1
  runs.extend([count,prev]);rasters[p.stem]=runs
 (ROOT/'src/shared/IconRaster.luau').write_text('--!strict\n-- Generated from resources/ui/icons PNG files.\nreturn '+lua(rasters)+'\n')
 return rasters

def update_manifest():
 p=ROOT/'resources/manifest.json';manifest=json.loads(p.read_text());known={a['source'] for a in manifest['assets']}
 for file in sorted((ROOT/'resources/ui').rglob('*')):
  if file.suffix not in ('.png','.svg'):continue
  source=file.relative_to(ROOT/'resources').as_posix()
  if source in known:continue
  manifest['assets'].append({'logicalId':source.replace('/','_').replace('.','_'),'source':source,'robloxAssetId':None,'status':'ready for GitHub review; local raster/source asset','sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
 manifest['runtimeIntegration']='Original mesh and icon data embedded; client-local Mesh/Image APIs with permission-aware fallback. Published Roblox upload IDs remain optional bindings.'
 p.write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':
 geometry=compile_geometry();icons=compile_icons();update_manifest();print(f'Embedded {len(geometry)} model sources and {len(icons)} icons')
