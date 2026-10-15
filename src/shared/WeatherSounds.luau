--!strict
-- Weather audio table (docs/85). No sound is uploaded yet: every id is "" PROVISIONAL (do not invent ids) and an empty or malformed id is a
-- silent no-op, exactly like Sfx.luau. Pure data and math, checked offline by tools/verify_weather.py.
-- volume is the final in-game volume (kids' game: quiet beds 0.15-0.3, accents at most 0.5).
local Sounds={}
export type Entry={id:string,volume:number,loop:boolean,gap:number?}
Sounds.Sounds={
    rain_bed={id="",volume=.22,loop=true},
    thunder_bed={id="",volume=.24,loop=true},
    thunder_roll={id="",volume=.4,loop=false,gap=2},
    thunder_strike={id="",volume=.45,loop=false,gap=.6},
    blizzard_bed={id="",volume=.26,loop=true},
    volcano_bed={id="",volume=.26,loop=true},
    volcano_boom={id="",volume=.45,loop=false,gap=.8},
    quake_bed={id="",volume=.26,loop=true},
    quake_burst={id="",volume=.5,loop=false,gap=1},
    bloodmoon_bed={id="",volume=.2,loop=true},
    aurora_bed={id="",volume=.16,loop=true},
}:: {[string]:Entry}
-- bed = looping ambience for the whole event; cues = one-shots fired by WeatherVisuals (cue name -> list of {sound, delay seconds})
Sounds.Events={
    rain={bed="rain_bed"},
    thunder={bed="thunder_bed",cues={strike={{"thunder_strike",0},{"thunder_roll",.7}}}},
    blizzard={bed="blizzard_bed"},
    volcano={bed="volcano_bed",cues={eruption={{"volcano_boom",0}}}},
    aurora={bed="aurora_bed"},
    quake={bed="quake_bed",cues={quake={{"quake_burst",0}}}},
    bloodmoon={bed="bloodmoon_bed"},
}:: {[string]:{bed:string,cues:{[string]:{{any}}}?}}
Sounds.FadeSeconds=2.2
Sounds.MaxBed=.3
Sounds.MaxAccent=.5

-- Pure: "rbxassetid://N" or nil for empty/invalid ids
function Sounds.normalizeId(id:any):string?
    if type(id)=="number" and id>0 and id%1==0 then return "rbxassetid://"..string.format("%d",id) end
    if type(id)~="string" then return nil end
    local digits=string.match(id,"^rbxassetid://(%d+)$") or string.match(id,"^(%d+)$")
    if not digits or tonumber(digits)==0 then return nil end
    return "rbxassetid://"..digits
end
-- Pure: wanted bed volume for the current weather; 0 when sound is off
function Sounds.bedTarget(name:string,activeId:string,k:number,soundOn:boolean):number
    local event=Sounds.Events[activeId]
    local entry=Sounds.Sounds[name]
    if not soundOn or not event or not entry or event.bed~=name then return 0 end
    return entry.volume*math.clamp(k,0,1)
end
-- Pure: move a level toward a target, never faster than full volume per FadeSeconds
function Sounds.step(level:number,target:number,dt:number):number
    local maxStep=dt/Sounds.FadeSeconds*Sounds.MaxBed
    return level+math.clamp(target-level,-maxStep,maxStep)
end
-- Pure: sounds (with delays) a cue starts during an event
function Sounds.cue(activeId:string,cueName:string):{{any}}
    local event=Sounds.Events[activeId]
    local list=if event and event.cues then event.cues[cueName] else nil
    return list or {}
end

-- Tiny cue bus shared by WeatherVisuals (fires) and WeatherAudio (listens); ModuleScripts are cached per client, so both see one table.
local listeners:{(string)->()}={}
function Sounds.connect(fn:(string)->())
    table.insert(listeners,fn)
end
function Sounds.fire(cueName:string)
    for _,fn in listeners do fn(cueName) end
end
return Sounds
