"""Run actual Luau layout/data/envelope modules with lightweight value mocks.
Engine physics, replication and API permissions require Studio; this is numeric/data validation.
"""
from pathlib import Path
import argparse,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
def wrapped(path):return '(function()\n'+(ROOT/path).read_text()+'\nend)()'
def script():
 return 'local Config = '+wrapped('src/shared/Config.luau')+'\n'+'''
local script={Parent={Config=true}}
local require=function(_) return Config end
local workspace={Gravity=196.2}
local Vector2={new=function(x,y) return {Magnitude=math.sqrt(x*x+y*y)} end}
'''+ 'local Layout = '+wrapped('src/shared/IslandLayout.luau')+'\nlocal Envelope = '+wrapped('src/shared/MovementEnvelope.luau')+'\nlocal Geometry = '+wrapped('src/shared/ResourceGeometry.luau')+'\nlocal Icons = '+wrapped('src/shared/IconRaster.luau')+'\n'+'''
assert(Config.ArenaHalfWidth==260)
assert(Config.FoodSectorCount==16)
local high=0
for x=-260,260,4 do
 for z=-260,260,4 do
  local h=Layout.height(x,z)
  assert(h==h and h<Config.TerrainTop and h>-16, "height outside voxel region")
  high=math.max(high,h)
 end
end
assert(high>70,"mountains too low")
assert(Layout.height(0,30)<3,"spawn should be a low meadow")
-- All four authored mountains can be approached on a walking ramp.
for _,peak in Layout.Peaks do
 local last=Layout.height(peak.x-peak.radius,peak.z)
 local maxSlope=0
 for dx=-peak.radius+4,0,4 do
  local h=Layout.height(peak.x+dx,peak.z)
  maxSlope=math.max(maxSlope,math.abs(h-last)/4)
  last=h
 end
 assert(maxSlope<math.tan(math.rad(Config.MaxSlopeAngle)),"mountain route exceeds climb angle")
end
assert(Envelope.plausible({X=2,Y=5,Z=0},.1,2,2,50),"valid jump rejected")
assert(Envelope.plausible({X=2,Y=-7,Z=0},.1,2,2,-80),"valid fall rejected")
assert(not Envelope.plausible({X=45,Y=0,Z=0},.1,2,2,0),"horizontal teleport accepted")
assert(not Envelope.plausible({X=0,Y=50,Z=0},.1,2,2,10000),"vertical teleport accepted")
local meshCount=0
for id,data in Geometry do
 meshCount+=1
 for _,face in data.faces do
  assert(data.vertices[face[1]] and data.vertices[face[2]] and data.vertices[face[3]])
  assert(data.colors[face[4]],id.." missing material")
 end
end
assert(meshCount==13)
local iconCount=0
for name,runs in Icons do
 iconCount+=1
 local total=0
 for i=1,#runs,2 do
  assert(runs[i]>0 and runs[i]%1==0)
  total+=runs[i]
  assert(runs[i+1]>=0 and runs[i+1]<=4294967295)
 end
 assert(total==64*64,name.." raster buffer length")
end
assert(iconCount==14)
print("Luau execution passed: mountain bounds/routes, spawn, jump/fall rejection, 13 meshes, 14 icon rasters")
'''
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--runner',required=True);args=parser.parse_args()
 with tempfile.TemporaryDirectory() as tmp:
  path=Path(tmp)/'verify.luau';path.write_text(script());subprocess.run([args.runner,str(path)],check=True)
