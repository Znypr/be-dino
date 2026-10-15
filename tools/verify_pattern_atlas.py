"""BD-pattern-atlas: offline proof of the pattern texture cache (pure module, cap/LRU/refcount/fallback)."""
import argparse,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LUA='''
local Cache=(function()
'''+(ROOT/'src/shared/PatternAtlasCache.luau').read_text()+'''
end)()
local destroyed=0
local function new(cap) destroyed=0 return Cache.new(cap,function() destroyed+=1 end) end
-- helper mimicking PatternGenes.paint: returns entry or nil (flat)
local function paint(c,key)
    local e=c:acquire(key) if e then return e end
    if not c:reserve() then return nil end
    return c:insert(key,{})
end
-- 1. identical genes share one image; refs count
local c=new(30)
local a=paint(c,"k1");local b=paint(c,"k1")
assert(a==b and a.refs==2 and c.live==1 and c.hits==1 and c.misses==1)
c:release(a);c:release(b);assert(a.refs==0 and c.live==1,"released entries stay warm")
assert(paint(c,"k1")==a and a.refs==1,"warm entry revived without repaint")
c:release(a)
-- 2. cap is never exceeded; warm entries are evicted oldest first
c=new(5)
local es={}
for i=1,5 do es[i]=paint(c,"w"..i) end
assert(c.live==5 and not paint(c,"w6"),"all pinned: new texture denied, never over cap")
assert(c.denied==1)
c:release(es[2]);c:release(es[4])
local n=paint(c,"w6");assert(n and c.live==5 and c.evictions==1 and destroyed==1)
assert(c.entries["w2"]==nil and c.entries["w4"]~=nil,"oldest-released warm entry evicted first (LRU)")
assert(c:hasRoom(),"w4 still warm -> room")
c:release(es[1]);c:release(es[3]);c:release(es[5]);c:release(n)
for i=1,20 do assert(paint(c,"x"..i),"warm entries always make room");c:release(c.entries["x"..i]) end
assert(c.live<=5)
-- 3. 12 distinct 7-part legacy dinos on cap 30: all-or-nothing per dino (free() check): 4 fully textured, 8 fully
--    flat, never half; freeing a dino lets a flat one upgrade whole.
c=new(30)
local texturedDinos,flatDinos,held=0,0,{}
local function dino(d)
    if c:free()<7 then return false end
    local mine={}
    for p=1,7 do table.insert(mine,assert(paint(c,"dino"..d.."|part"..p))) end
    held[d]=mine;return true
end
for d=1,12 do if dino(d) then texturedDinos+=1 else flatDinos+=1 end end
assert(c.live<=30 and texturedDinos==4 and flatDinos==8,"tex "..texturedDinos.." flat "..flatDinos)
for _,e in held[1] do c:release(e) end
assert(c:free()>=7 and dino(5),"flat dino upgrades whole after a dino leaves")
-- warm dino 1 is evicted as needed; 20 more cycles never exceed the cap
for d=13,40 do local ok=dino(d);if ok then for _,e in held[d] do c:release(e) end end assert(c.live<=30) end
-- 4. identical copies cost nothing: 40 dinos of one gene = 7 images
c=new(30)
for d=1,40 do for p=1,7 do paint(c,"same|part"..p) end end
assert(c.live==7 and c.hits==40*7-7)
local s=c:stats();assert(s.cap==30 and s.pinned==7 and s.warm==0)
-- 5. remove drops dead entries
c=new(2);local r=paint(c,"r");c:remove(r);assert(c.live==0)
print("Pattern atlas cache passed: sharing, refcount, warm LRU, hard cap, 12-dino degradation, upgrade after release")
'''
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runner',required=True);args=p.parse_args()
    with tempfile.TemporaryDirectory() as f:
        path=Path(f)/'atlas.luau';path.write_text(LUA)
        raise SystemExit(subprocess.run([args.runner,str(path)]).returncode)
