--!strict
-- BD-pattern-atlas: pure cache of pattern textures under Roblox's ~32 live EditableImage cap.
-- One entry per (texture owner, gene) key, shared by every part with identical genes (reference counted).
-- Entries with no users stay WARM (still alive) so a dino that leaves and returns does not repaint; they are
-- the LRU eviction victims when a new texture needs room. Pinned (in use) entries are never evicted: when every
-- slot is pinned, acquire returns nil and the caller degrades to a flat colour (never blank, never a cube).
local Cache={}
Cache.__index=Cache
export type Entry={key:string,image:any,refs:number,tick:number}
function Cache.new(cap:number,destroy:(any)->())
    return setmetatable({cap=cap,destroy=destroy,entries={} :: {[string]:Entry},live=0,tick=0,hits=0,misses=0,evictions=0,denied=0},Cache)
end
-- Existing entry for key (pinned for the caller), or nil.
function Cache.acquire(self,key:string): Entry?
    local entry=self.entries[key]
    if not entry then return nil end
    self.tick+=1
    entry.tick=self.tick;entry.refs+=1;self.hits+=1
    return entry
end
-- True when a new image may be created (possibly after evicting the oldest warm entry).
function Cache.hasRoom(self): boolean
    if self.live<self.cap then return true end
    for _,entry in self.entries do if entry.refs<=0 then return true end end
    return false
end
-- Slots a new image could take right now: never-used plus warm (evictable).
function Cache.free(self): number
    local n=self.cap-self.live
    for _,entry in self.entries do if entry.refs<=0 then n+=1 end end
    return n
end
function Cache.evictOne(self): boolean
    local victim:Entry?=nil
    for _,entry in self.entries do
        if entry.refs<=0 and (not victim or entry.tick<victim.tick) then victim=entry end
    end
    if not victim then return false end
    self.entries[victim.key]=nil;self.live-=1;self.evictions+=1
    self.destroy(victim.image)
    return true
end
-- Make room for one new image. False (and a `denied` count) when every slot is pinned.
function Cache.reserve(self): boolean
    self.misses+=1
    while self.live>=self.cap do
        if not self:evictOne() then self.denied+=1;return false end
    end
    return true
end
-- Register a freshly created image (after a successful reserve), pinned once.
function Cache.insert(self,key:string,image:any): Entry
    self.tick+=1
    local entry={key=key,image=image,refs=1,tick=self.tick}
    self.entries[key]=entry;self.live+=1
    return entry
end
function Cache.release(self,entry:Entry)
    if entry.refs<=0 then return end
    entry.refs-=1
    self.tick+=1;entry.tick=self.tick
end
-- Drop an entry whose image died elsewhere (Destroying) or failed to paint.
function Cache.remove(self,entry:Entry)
    if self.entries[entry.key]==entry then self.entries[entry.key]=nil;self.live-=1 end
end
function Cache.stats(self)
    local pinned=0
    for _,entry in self.entries do if entry.refs>0 then pinned+=1 end end
    return {live=self.live,pinned=pinned,warm=self.live-pinned,cap=self.cap,hits=self.hits,misses=self.misses,evictions=self.evictions,denied=self.denied}
end
return Cache
