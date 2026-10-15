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
-- 3. ONE image per dino (legacy dinos texture only their primary part; the other 6 parts are tinted neutral textures
--    that cost no EditableImage): 30 distinct patterned dinos of any species fit, the 31st is flat (never over cap),
--    and a flat dino upgrades after one leaves.
c=new(30)
local held,flatDinos={},0
local function dino(d)
    local key="dino"..d.."|primary"
    if c:need({key})>c:free() then return false end
    held[d]=assert(paint(c,key));return true
end
for d=1,40 do if not dino(d) then flatDinos+=1 end end
assert(c.live==30 and flatDinos==10,"live "..c.live.." flat "..flatDinos)
c:release(held[1]);assert(dino(41),"flat dino upgrades after a dino leaves")
for d=42,80 do local ok=dino(d);if ok then c:release(held[d]) end assert(c.live<=30) end
-- need(): distinct keys not already live; shared keys are free (the old per-part count over-counted a 7-part dino as 7)
c=new(30);paint(c,"a")
assert(c:need({"a","b","b","c"})==2,"a is live, b and c are new (b counted once)")
assert(c:need({})==0 and c:need({"a","a"})==0)
-- need() vs old over-count: a legacy dino costs 1, not its 7 parts
assert(c:need({"legacy|x"})==1)
-- 4. identical copies cost nothing: 40 dinos of one gene = 7 images
c=new(30)
for d=1,40 do paint(c,"same|primary") end
assert(c.live==1 and c.hits==39)
local s=c:stats();assert(s.cap==30 and s.pinned==1 and s.warm==0)
-- 5. remove drops dead entries
c=new(2);local r=paint(c,"r");c:remove(r);assert(c.live==0)
print("Pattern atlas cache passed: sharing, refcount, warm LRU, hard cap, need-count, 30-dino one-image-each, upgrade after release")
'''
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runner',required=True);args=p.parse_args()
    src=(ROOT/'src/shared/PatternGenes.luau').read_text()
    for needle in ('primaryOf(part)~=part','atlas:need({sharedKey})','Textures.apply(part)','PatternLOD","tint"'):
        assert needle in src,'PatternGenes lost the one-image-per-dino rule: '+needle
    assert 'groupFlat' not in src and '#groupParts' not in src,'old per-part over-count returned'
    assert 'Cache.new(30,' in src,'hard cap must stay 30'
    with tempfile.TemporaryDirectory() as f:
        path=Path(f)/'atlas.luau';path.write_text(LUA)
        raise SystemExit(subprocess.run([args.runner,str(path)]).returncode)
