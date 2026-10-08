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
    s='local Config='+wrap('src/shared/ProgressionConfig.luau')+'\nlocal script={Parent={}}\nlocal require=function()return Config end\nlocal Genetics='+wrap('src/shared/EggGenetics.luau')+'\n'
    s+='local data='+lua(data)+'\n'+'''
local current
local Assets={CreateEditableImage=function()return {WritePixelsBuffer=function(_,_,_,pixels) current=pixels end,Destroy=function()end}end}
local game={GetService=function(_,name)return if name=="AssetService" then Assets else {JSONDecode=function()return data end}end}
local script={Parent={EggGenetics="Genetics",FindFirstChild=function()return {FindFirstChild=function()return "Data" end}end}}
local require=function(id)return if id=="Genetics" then Genetics else "Data" end
local Vector2={new=function()return {}end,zero={}}
local Content={fromObject=function(x)return x end}
local Color3={new=function()return {}end}
local part={Parent=true,GetAttribute=function()return "brachiosaurus" end,GetChildren=function()return {}end,Destroying={Once=function()end}}
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
local legacy={conditionId="normal",hatchSuccess=true,primaryColorId="white",secondaryColorId="black",blend=80}
assert(Genetics.key(legacy)=="normal:white:black:80")
local invalid=table.clone(legacy);invalid.patternId="unknown";assert(not Genetics.valid(invalid))
print("Authored genes passed: 8 masks × 4 exact UV coverage ratios, fixed facial pixels, same-family contrast and legacy saved keys")
'''
    return s
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runner',required=True);args=p.parse_args()
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/'genes.luau';path.write_text(script());result=subprocess.run([args.runner,str(path)])
        raise SystemExit(result.returncode)
