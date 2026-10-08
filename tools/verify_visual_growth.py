"""Run actual character visual refresh logic; growth must retain mesh allocation."""
import argparse,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def script():
    source=(ROOT/'src/client/ResourceVisuals.client.luau').read_text()
    refresh=source[source.index('local function characterVisual('):source.index('local function watchCharacter(')]
    return '''
local clones,paints=0,0
local frame=setmetatable({},{__mul=function()return frame end})
local CFrame={new=function()return frame end}
local Enum={HumanoidRigType={R6="R6"}}
local character={Parent=true,attrs={SpeciesId="brachiosaurus",VisualScale=1,MutationVisual="base",GenesJson="null"}}
local root={Parent=true,Size={Y=2},CFrame=frame,IsA=function(_,c)return c=="BasePart"end}
local humanoid={HipHeight=2,RigType="R15"}
function character:GetAttribute(key)return self.attrs[key]end
function character:FindFirstChild(name)return if name=="HumanoidRootPart" then root elseif name=="LocalMeshVisual" then self.visual else nil end
function character:FindFirstChildOfClass()return humanoid end
local ReplicatedStorage={FindFirstChild=function()return nil end}
local Http={JSONDecode=function(_,value)return if value=="null" then nil else {} end}
local Appearance={apply=function()paints+=1 end}
local weld={Enabled=true,IsA=function(_,c)return c=="WeldConstraint"end}
local Instance={new=function()return weld end}
local Resources={clone=function()
 clones+=1
 local part={IsA=function(_,c)return c=="BasePart"end}
 local model={attrs={}}
 function model:GetAttribute(k)return self.attrs[k]end
 function model:SetAttribute(k,v)self.attrs[k]=v end
 function model:GetDescendants()return {part,weld}end
 function model:ScaleTo(s)self.scale=s;assert(not self.Parent or not weld.Enabled,"growth resized a live weld") end
 function model:PivotTo()end
 function model:Destroy()self.destroyed=true end
 return setmetatable(model,{__newindex=function(t,k,v)rawset(t,k,v);if k=="Parent" then character.visual=t end end})
end}
'''+refresh+'''
characterVisual(character)
local first=character.visual
for i=1,100 do character.attrs.VisualScale=1+i/100;characterVisual(character);assert(character.visual==first) end
assert(clones==1 and first.scale==2 and weld.Enabled)
character.attrs.GenesJson="genes-a";characterVisual(character)
assert(character.visual==first and clones==1 and paints==1)
character.attrs.GenesJson="genes-b";characterVisual(character)
assert(character.visual==first and clones==1 and paints==2)
character.attrs.GenesJson="null";characterVisual(character)
assert(clones==2 and first.destroyed)
character.attrs.SpeciesId="mosasaurus";characterVisual(character)
assert(clones==3)
print("Visual growth passed: 100 size changes retain one mesh; genes repaint in place; null genes/species changes rebuild safely")
'''
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runner',required=True);args=p.parse_args()
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/'growth.luau';path.write_text(script());result=subprocess.run([args.runner,str(path)])
        raise SystemExit(result.returncode)
