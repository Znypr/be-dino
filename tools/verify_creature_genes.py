"""Run the actual pattern painter against authored masks and value-based engine mocks."""
import argparse,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def lua(value):
    if isinstance(value,dict):return '{'+','.join('[ '+lua(k)+' ]='+lua(v) for k,v in value.items())+'}'
    if isinstance(value,list):return '{'+','.join(lua(v) for v in value)+'}'
    if isinstance(value,str):return '[==['+value+']==]'
    return str(value)
def wrap(path):return '(function()\n'+(ROOT/path).read_text()+'\nend)()'
def script():
    data=json.loads((ROOT/'resources/creatures/brachiosaurus-genes.json').read_text())
    s='local Config='+wrap('src/shared/ProgressionConfig.luau')+'\nlocal script={Parent={}}\nlocal require=function()return Config end\nlocal Genetics='+wrap('src/shared/EggGenetics.luau')+'\nlocal Cache='+wrap('src/shared/PatternAtlasCache.luau')+'\n'
    s+='local data='+lua(data)+'\n'+'''
local current
local Assets={CreateEditableImage=function()return {WritePixelsBuffer=function(_,_,_,pixels) current=pixels end,Destroy=function()end}end}
local workspace={SetAttribute=function()end}
local game={GetService=function(_,name)return if name=="AssetService" then Assets else {JSONDecode=function()return data end,IsClient=function()return false end}end}
local script={Parent={PatternAtlasCache="Cache",EggGenetics="Genetics",FindFirstChild=function()return {FindFirstChild=function()return "Data" end}end}}
local require=function(id)return if id=="Genetics" then Genetics elseif id=="Cache" then Cache else "Data" end
local Vector2={new=function()return {}end,zero={}}
local Color3={new=function()return {}end,fromRGB=function()return {}end}
local Content={fromObject=function(x)return x end,none={}}
local part={Parent=true,GetAttribute=function()return "brachiosaurus" end,GetChildren=function()return {}end,SetAttribute=function()end,IsA=function()return true end,FindFirstAncestorOfClass=function()return nil end,IsDescendantOf=function()return false end,Destroying={Once=function()end}}
'''
    s+='local Pattern='+wrap('src/shared/PatternGenes.luau')+'\n'+'''
for name,mask in data.patterns do
 for _,blend in {1,20,50,99} do
  assert(Pattern.apply(part,{primaryColorId="teal",secondaryColorId="red",blend=blend,patternId=name}))
  local count,primary=0,0
  for p=0,128*128-1 do
   local rank=tonumber(mask:sub(p*2+1,p*2+2),16)
   if rank<254 then
    count+=1
    if buffer.readu8(current,p*4)==Genetics.color("teal").rgb[1] then primary+=1 end
   elseif rank==254 then
    for c=0,2 do assert(buffer.readu8(current,p*4+c)==tonumber(data.fixedRGB:sub(p*6+c*2+1,p*6+c*2+2),16),"fixed eye/mouth pixel tinted") end
   end
  end
  assert(primary==math.floor(count*blend/100),name.." coverage mismatch")
 end
 assert(Pattern.apply(part,{primaryColorId="black",secondaryColorId="black",blend=100,patternId=name}))
 local tones={}
 for p=0,128*128-1 do if tonumber(mask:sub(p*2+1,p*2+2),16)<254 then tones[buffer.readu8(current,p*4)]=true end end
 local n=0 for _ in tones do n+=1 end
 assert(n==2,name.." lost same-family tonal contrast")
end
-- Genes X must paint pattern X and colors X, never the old hard-coded green/white round spots.
local function snapshot(genes) assert(Pattern.apply(part,genes));return buffer.tostring(current) end
local defaultLook=snapshot({conditionId="normal",hatchSuccess=true,primaryColorId="green",secondaryColorId="white",blend=70,patternId="03_round_spots"})
local seen={}
for name in data.patterns do
 local look=snapshot({conditionId="normal",hatchSuccess=true,primaryColorId="red",secondaryColorId="blue",blend=50,patternId=name})
 assert(look~=defaultLook,name.." rendered like the default pattern")
 assert(not seen[look],name.." rendered identically to another pattern")
 seen[look]=true
end
local redLook=snapshot({conditionId="normal",hatchSuccess=true,primaryColorId="red",secondaryColorId="blue",blend=50,patternId="03_round_spots"})
local blueLook=snapshot({conditionId="normal",hatchSuccess=true,primaryColorId="blue",secondaryColorId="teal",blend=50,patternId="03_round_spots"})
assert(redLook~=blueLook and redLook~=defaultLook,"colors X must differ from other colors")
local legacy={conditionId="normal",hatchSuccess=true,primaryColorId="white",secondaryColorId="black",blend=80}
assert(Genetics.key(legacy)=="normal:white:black:80")
local invalid=table.clone(legacy);invalid.patternId="unknown";assert(not Genetics.valid(invalid))
print("Authored genes passed: 8 masks Ã— 4 exact UV coverage ratios, fixed facial pixels, same-family contrast and legacy saved keys")
'''
    return s
def check_wiring():
    """Static proof that real genes (not the default) reach every renderer."""
    def src(path): return (ROOT/path).read_text(encoding='utf8')
    a=src('src/shared/AuthoredCreatures.luau')
    assert a.count('patternId="03_round_spots"')==1 and 'if genes then genes else Creatures.DefaultGenes' in a,'authored clone must paint passed genes'
    assert 'Resources.clone(id,realGenes)' in src('src/client/ResourceVisuals.client.luau'),'character visual must pass genes'
    assert 'Resources.clone(speciesId,if traits then traits.genes else nil' in src('src/shared/DinosaurPreview.luau'),'previews must pass genes'  # extra trailing args (patient load) are allowed
    assert 'TextureContent=Content.none' in src('src/shared/ResourceModels.luau'),'Gold/Diamond must drop painted pattern'
    assert 'character:SetAttribute("GenesJson"' in src('src/server/Dinosaur.luau'),'equip must publish genes on the character'
    assert 'item.Transparency = 1' in src('src/client/ResourceVisuals.client.luau'),'server shell must stay hidden'
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runner',required=True);args=p.parse_args()
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/'genes.luau';path.write_text(script());result=subprocess.run([args.runner,str(path)])
        check_wiring();raise SystemExit(result.returncode)
