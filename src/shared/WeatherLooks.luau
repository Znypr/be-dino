--!strict
-- Weather v3 (docs/84): pure data and math for the client weather system. No Roblox types, so tools/verify_weather.py
-- can run it offline: look-table completeness, particle budgets, aurora palette and blend math.
-- Colours are {r,g,b} in 0..255; WeatherVisuals.client.luau converts them to Color3.
local Weather={}
export type Rgb={number}

local function rgb(r:number,g:number,b:number):Rgb return {r,g,b} end
export type Look={
    tint:Rgb,sat:number,contrast:number,bright:number,
    fog:Rgb,decay:Rgb,density:number,offset:number,haze:number,glare:number,
    bloom:number,rays:number,rayTint:Rgb,amb:Rgb?,shiftTop:Rgb,shiftBottom:Rgb,
    dof:number,dofFocus:number,exposure:number,lamp:number,glow:Rgb,glowBright:number,glowRange:number,
    vis:number,fogStart:number,stars:number,
    cloudCover:number,cloudDensity:number,cloudColor:Rgb,
}
local NONE=rgb(0,0,0) local WHITE=rgb(255,255,255)
local function look(t:{[string]:any}):Look
    return {
        tint=t.tint or WHITE,sat=t.sat or 0,contrast=t.contrast or 0,bright=t.bright or 0,
        fog=t.fog or rgb(199,214,230),decay=t.decay or rgb(106,112,125),density=t.density or 0,offset=t.offset or 0,haze=t.haze or 0,glare=t.glare or 0,
        bloom=t.bloom or 0,rays=t.rays or 0,rayTint=t.rayTint or WHITE,amb=t.amb,shiftTop=t.shiftTop or NONE,shiftBottom=t.shiftBottom or NONE,
        dof=t.dof or 0,dofFocus=t.dofFocus or 80,exposure=t.exposure or 0,lamp=t.lamp or 0,glow=t.glow or WHITE,glowBright=t.glowBright or 0,glowRange=t.glowRange or 40,
        vis=t.vis or 1000,fogStart=t.fogStart or 0,stars=t.stars or -1,
        -- BD-055: Terrain.Clouds cover/density 0..1 (cloudCover -1 = leave the place's own clouds alone) and the cloud colour
        cloudCover=t.cloudCover or -1,cloudDensity=t.cloudDensity or 0,cloudColor=t.cloudColor or WHITE,
    }
end

-- vis = Lighting.FogEnd: the distance in studs where scenery has fully faded into the fog colour; fogStart = where the fade begins.
-- Classic Lighting fog is the reliable view limiter (Studio test: Atmosphere.Density alone showed no fog); Atmosphere stays as an extra layer.
-- The near play area (25 studs) stays clear: fogStart >= 25 except in the blizzard whiteout.
-- BD-213 (owner 2026-10-15: "visibility randomly cuts off, it should fade like fog"): there is no opaque sky box any more; the far
-- view always dissolves into the classic fog ramp, which is capped inside the prop cull radius (Weather.fog) so props never pop.
-- Clear weather is crisp (owner 2026-10-16): a faint sky-blue fade far out, a barely positive grade (sat +.02, contrast 0 since BD-460), no DoF, no bloom.
Weather.Looks={
    clear=look({sat=.02,contrast=0,fog=rgb(176,205,232),fogStart=220,vis=1100}), -- BD-460: grade sat +.08 -> +.02 (-.06) and contrast +.04 -> 0: softer, less saturated greens; still no haze
    rain=look({cloudCover=.9,cloudDensity=.65,cloudColor=rgb(120,132,152),tint=rgb(150,182,232),sat=-.26,contrast=.14,bright=-.06,fog=rgb(120,134,156),decay=rgb(70,84,110),density=.5,offset=0,haze=2.6,bloom=.2,
        amb=rgb(92,106,130),dof=.35,dofFocus=90,exposure=-.35,lamp=.8,fogStart=40,vis=260}),
    thunder=look({cloudCover=1,cloudDensity=.95,cloudColor=rgb(52,48,92),tint=rgb(160,174,222),sat=-.2,contrast=.18,bright=-.08,fog=rgb(88,96,132),decay=rgb(46,50,90),density=.56,offset=0,haze=3,bloom=.5,
        amb=rgb(104,116,160),dof=.45,dofFocus=80,exposure=-.3,lamp=1.4,glow=rgb(160,140,255),glowBright=.6,glowRange=60,fogStart=40,vis=200}),
    blizzard=look({cloudCover=1,cloudDensity=.85,cloudColor=rgb(226,236,250),tint=rgb(214,232,255),sat=-.4,contrast=-.06,bright=.08,fog=rgb(226,234,246),decay=rgb(200,216,240),density=.8,offset=0,haze=4,bloom=.45,rays=.1,
        rayTint=rgb(220,235,255),amb=rgb(172,184,206),dof=.6,dofFocus=40,lamp=.4,fogStart=25,vis=110}),
    -- BD-256: soft embers, not a lava wash. The old glow light (1.4 at 60 studs), bloom .6 and a saturated amber ambient painted
    -- the whole ground and about a third of the screen orange; calmer values keep the warm mood and every dino and food readable.
    volcano=look({cloudCover=.85,cloudDensity=.85,cloudColor=rgb(92,58,48),tint=rgb(255,228,205),sat=.15,contrast=.1,bright=-.03,fog=rgb(150,84,56),decay=rgb(110,50,30),density=.4,offset=0,haze=2.4,glare=.2,bloom=.25,rays=.15,
        rayTint=rgb(255,170,100),amb=rgb(150,112,92),dof=.4,dofFocus=90,exposure=-.2,lamp=.5,glow=rgb(255,140,70),glowBright=.4,glowRange=36,fogStart=70,vis=300}),
    -- aurora colours (fog, decay, shifts, ambient, tint, glow) are overwritten every frame from Weather.aurora(); these are the mid values
    aurora=look({cloudCover=.12,cloudDensity=.2,cloudColor=rgb(150,220,210),tint=rgb(176,255,230),sat=.4,contrast=.1,bright=-.04,fog=rgb(40,200,170),decay=rgb(60,80,180),density=.32,offset=0,haze=1.4,bloom=1.2,rays=.05,
        rayTint=rgb(140,255,220),amb=rgb(70,130,120),dof=.2,dofFocus=120,exposure=-.2,lamp=.5,
        glow=rgb(60,255,170),glowBright=1.3,glowRange=60,fogStart=170,vis=400,stars=5000}),
    quake=look({cloudCover=.65,cloudDensity=.55,cloudColor=rgb(196,168,130),tint=rgb(232,200,156),sat=-.14,contrast=.16,bright=-.06,fog=rgb(198,176,146),decay=rgb(130,100,70),density=.45,offset=0,haze=3,bloom=.15,
        amb=rgb(150,126,96),dof=.35,dofFocus=70,lamp=.6,fogStart=40,vis=220}),
    bloodmoon=look({cloudCover=.8,cloudDensity=.8,cloudColor=rgb(120,24,40),tint=rgb(255,140,150),sat=.45,contrast=.18,bright=0,fog=rgb(66,14,24),decay=rgb(100,10,30),density=.4,offset=0,haze=2.8,glare=.5,bloom=.5,rays=.12,
        rayTint=rgb(255,60,80),amb=rgb(165,38,56),dof=.3,dofFocus=80,exposure=-.15,lamp=1.2,glow=rgb(255,40,70),glowBright=.5,glowRange=60,fogStart=100,vis=360}),
}
Weather.Ids=table.freeze({"rain","thunder","blizzard","volcano","aurora","quake","bloodmoon"})

-- Particle budget (desktop). rate = emitted per second for the whole group, life = {min,max} seconds; big = sprite size >= 30 studs (overdraw).
-- Phone density halves every rate. Concurrent particles of a group = rate * average lifetime.
export type Spec={rate:number,life:{number},big:boolean?}
local function spec(rate:number,a:number,b:number,big:boolean?):Spec return {rate=rate,life={a,b},big=big} end
Weather.Rigs={
    rain={streaks=spec(2100,.55,.7),near=spec(420,.35,.5),splash=spec(560,.22,.38),mist=spec(14,3,4.5,true),curtain=spec(10,1.2,1.6,true),bank=spec(12,9,12,true)},
    thunder={streaks=spec(2800,.55,.7),near=spec(520,.35,.5),splash=spec(700,.22,.38),mist=spec(16,3,4.5,true),curtain=spec(14,1.2,1.6,true),bank=spec(14,9,12,true)},
    blizzard={snow=spec(1300,3,4.2),gust=spec(50,1.4,2),drift=spec(16,2.6,3.4,true),bank=spec(16,7,9,true),flurry=spec(120,.9,1.3)},
    volcano={ash=spec(300,4,5.5),embers=spec(200,3,5),plume=spec(18,5,7,true),smoke=spec(12,8,11,true),haze=spec(5,10,12,true),bank=spec(8,9,11,true)},
    aurora={motes=spec(120,4,6),stars=spec(60,3,5),bank=spec(14,9,12,true)},
    quake={dust=spec(50,3,4.5),bank=spec(14,8,10,true)},
    bloodmoon={motes=spec(140,4,6),fog=spec(16,5,7,true),bank=spec(14,9,11,true)},
}
-- QA 2026-10-16 (docs/evidence 2026-10-16-weather-qa): the blood moon (core 60, halos up to 200) filled the top third of a phone-size view and the title
-- card sat on top of the "started" toast. The moon is smaller and higher; the title card sits below the toast and stays a soft, narrower banner.
Weather.Moon=table.freeze({core=44,halos=table.freeze({80,108,142}),distance=150})
-- BD-348 aurora: the ribbons start at the horizon (visible without looking up) and the horizon glows; BD-349 counts per level
Weather.Aurora=table.freeze({baseY=-6,step=16,alpha=.6,horizonGlow=.75})
-- BD-055 Reduce Motion fallback for thunder: no flashes or bolts, only a slow soft brightness swell (peak = share of a full flash).
Weather.Swell=table.freeze({rate=.7,peak=.1})
Weather.Title=table.freeze({y=.31,width=.6,height=.085})
Weather.Budget=table.freeze({concurrent=6000,bigConcurrent=500,bolts=4,bombs=6,beams=140,cracks=4,cracksPhone=2,rocksPerCrack=3})
-- Earthquake v2 (owner 2026-10-15): a WORLD event, not an aura. Ground cracks open at random spots in view (never under the dino),
-- grow over `grow` s, glow faintly amber, puff dust and kick a few rock chunks, then close. Tremor pulses every `pulseEvery` s
-- give a gentle camera rumble (`shake`, 0 with Reduce Motion) and a slight wobble of nearby small props.
Weather.Quake=table.freeze({
    grow=.5,life={3,4.5},close=.8,pulseEvery={3,5},pulseSeconds=.9,shake=.3,
    minDist=18,maxDist=70,viewCone=55,clearOfDino=12,segments=4,length={10,18},width={1.4,2.4},
    -- BD-348: a readable cue right at the dino: a dust puff at the feet and a flat crack decal a few studs ahead on every pulse
    -- (decal = the fx3 "rays" alpha texture tinted dark, flat on the ground); camera shake stays tiny and is 0 with Reduce Motion.
    feetPuff=6,feetPuffPhone=3,decalAhead={8,12},decalSize=14,decalLife=3.2,
    wobbleRadius=40,wobbleMax=10,wobbleDegrees=2.5,propMaxSize=9,
})
function Weather.concurrent(id:string):(number,number)
    local total,big=0,0
    for _,s in Weather.Rigs[id] do
        local c=s.rate*(s.life[1]+s.life[2])/2
        total+=c if s.big then big+=c end
    end
    return total,big
end

-- Aurora palette: green -> teal -> violet -> magenta -> back, cycling about every PERIOD seconds with slow noise.
Weather.AuroraPeriod=26
local STOPS={rgb(60,255,140),rgb(40,225,225),rgb(150,100,255),rgb(255,90,210),rgb(130,120,255),rgb(40,225,225)}
function Weather.palette(u:number):Rgb
    u=u%1 local x=u*#STOPS local i=math.floor(x) local f=x-i
    local a=STOPS[i%#STOPS+1] local b=STOPS[(i+1)%#STOPS+1]
    f=f*f*(3-2*f)
    return rgb(a[1]+(b[1]-a[1])*f,a[2]+(b[2]-a[2])*f,a[3]+(b[3]-a[3])*f)
end
-- time in seconds, offset 0..1 spreads hue over the sky; the noise term makes the cycle uneven and never identical twice
function Weather.aurora(time:number,offset:number):Rgb
    local noise=math.sin(time*.13+offset*6.1)*.5+math.sin(time*.31+offset*3.3)*.5
    return Weather.palette(time/Weather.AuroraPeriod+offset+noise*.05)
end

function Weather.mix(a:Rgb,b:Rgb,t:number):Rgb
    return rgb(a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t,a[3]+(b[3]-a[3])*t)
end
function Weather.scale(a:Rgb,s:number):Rgb return rgb(a[1]*s,a[2]*s,a[3]*s) end
-- ramp strength: Reduce Motion keeps only half of the grade (docs/72)
function Weather.strength(k:number,motion:boolean):number return if motion then k else k*.5 end
function Weather.lerp(a:number,b:number,t:number):number return a+(b-a)*t end

-- Soft-visibility rules (BD-213). CullMargin: FogEnd never passes this share of the device's prop cull radius, so props are
-- already fully dissolved in fog when they are detached or re-attached. SoftRatio: FogStart never passes this share of FogEnd,
-- so the fade always spans at least 55% of the view and never reads as a wall.
Weather.CullMargin=.85
Weather.SoftRatio=.45
function Weather.fogCap(cullRadius:number?):number
    return if cullRadius then cullRadius*Weather.CullMargin else math.huge
end
-- Clear-weather distance fade per device class (island daylight): far out so the mid-distance stays crisp. Phone has no entry and
-- keeps the tight cull-radius fog. The fog colour is the sky-horizon blue, so it reads as distance, not haze.
Weather.ClearFog={Desktop={fogStart=400,fogEnd=1400},Tablet={fogStart=250,fogEnd=700}}
-- Fog cap for a device class: the cull-radius cap, or that class's clear-weather fog end when that is farther.
function Weather.capFor(class:string,cullRadius:number?):number
    local cf=Weather.ClearFog[class]
    return math.max(Weather.fogCap(cullRadius),if cf then cf.fogEnd else 0)
end
-- Clear look for a device class with the far fog distances applied.
function Weather.clearFor(class:string):Look
    local cf=Weather.ClearFog[class]
    if not cf then return Weather.Looks.clear end
    local l=table.clone(Weather.Looks.clear) l.fogStart,l.vis=cf.fogStart,cf.fogEnd
    return l
end
-- Classic fog blend from the clear-weather haze to the event look: FogEnd is blended in 1/distance so the view closes in
-- smoothly instead of jumping at the start of the ramp. cap = Weather.fogCap(cull radius).
function Weather.fog(look:Look,t:number,base:Look,cap:number):(number,number)
    local fogEnd=math.min(1/Weather.lerp(1/base.vis,1/look.vis,t),cap)
    local fogStart=math.min(Weather.lerp(base.fogStart,look.fogStart,t),fogEnd*Weather.SoftRatio)
    return fogStart,fogEnd
end

return Weather
