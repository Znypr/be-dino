"""Run the actual artwork assembler with UI stubs; Studio rendering is still required."""
from pathlib import Path
import argparse,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
def module(path):return '(function()\n'+(ROOT/path).read_text()+'\nend)()'
def script():
 return '''local Vector2={new=function(x,y)return {X=x,Y=y}end}
local UDim2={fromScale=function(x,y)return {X=x,Y=y}end,fromOffset=function(x,y)return {X=x,Y=y}end}
local Enum={ScaleType={Fit="Fit"}}
local created={}
local Instance={new=function(kind)local o={kind=kind} table.insert(created,o) return o end}
local Assets='''+module('src/shared/ArtworkAssets.luau')+'''\nlocal Layout='''+module('src/shared/ArtworkLayout.luau')+'''
local script={Parent={ArtworkAssets="Assets",ArtworkLayout="Layout"}}
local require=function(id)return if id=="Assets" then Assets else Layout end
local Artwork='''+module('src/shared/Artwork.luau')+'''
local nativeCalls={}
local function native(parent,id)table.insert(nativeCalls,id) return {Parent=parent} end
local parent={ZIndex=20}
-- Exercise fallback explicitly even after production bindings are populated.
for key in Assets do Assets[key]="" end
local Navigation='''+module('src/shared/NavigationArtwork.luau')+'''
assert(Navigation.auras=="aura_meadow" and Navigation.potions=="potion_speed")
local root=Artwork.build(parent,Navigation.auras,native)
assert(root.Parent==parent and #nativeCalls==2 and nativeCalls[1]=="aura" and nativeCalls[2]=="dinos")
nativeCalls={}
Artwork.build(parent,Navigation.potions,native)
assert(#nativeCalls==1 and nativeCalls[1]=="speed")
assert(Artwork.build(parent,"weather",native)==nil)
-- Stub IDs are fixtures only, never written to the upload mapping.
for key in Assets do Assets[key]="fixture://"..key end
created={} nativeCalls={}
root=Artwork.build(parent,"aura_tidal",native)
local rings,clips,center=0,0,0
for _,o in created do
 if o.Name=="RingClip" then clips+=1 assert(o.ClipsDescendants) end
 if o.kind=="ImageLabel" and o.Name=="aura_tidal_ring" then
  rings+=1
  local clip=o.Parent
  assert(math.abs(o.Size.X-Layout.ringSize)<1e-9)
  assert(math.abs(o.Size.Y*clip.Size.Y-Layout.ringSize)<1e-9)
  assert(math.abs(o.Position.Y*clip.Size.Y+clip.Position.Y-Layout.ringPosition.Y)<1e-9)
 elseif o.Name=="fossil_centerpiece" then center+=1 assert(o.ZIndex>root.ZIndex+1 and o.ZIndex<root.ZIndex+4) end
end
assert(rings==2 and clips==2 and center==1 and #nativeCalls==0)
nativeCalls={}
Artwork.build(parent,"potion_growth",native)
assert(#nativeCalls==1 and nativeCalls[1]=="leaf")
nativeCalls={}
Artwork.build(parent,Navigation.potions,native)
assert(#nativeCalls==1 and nativeCalls[1]=="speed")
created={}
Artwork.build(parent,"catches",native)
local marks=0
for _,o in created do if o.Name=="catches_mark" then marks+=1 end end
assert(marks==3)
print("Artwork assembly passed: native fallback, registered rear/front ring clips, independent centerpiece, both bottle overlays and repeated catches mark")
'''
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--runner',required=True);args=p.parse_args()
 with tempfile.TemporaryDirectory() as temp:
  path=Path(temp)/'artwork.luau';path.write_text(script())
  result=subprocess.run([args.runner,str(path)],capture_output=True,text=True)
  print(result.stdout,end='');print(result.stderr,end='');raise SystemExit(result.returncode)
