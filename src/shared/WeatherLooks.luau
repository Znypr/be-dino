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
    vis:number,fogStart:number,dome:number,stars:number,
}
local NONE=rgb(0,0,0) local WHITE=rgb(255,255,255)
local function look(t:{[string]:any}):Look
    return {
        tint=t.tint or WHITE,sat=t.sat or 0,contrast=t.contrast or 0,bright=t.bright or 0,
        fog=t.fog or rgb(199,214,230),decay=t.decay or rgb(106,112,125),density=t.density or 0,offset=t.offset or 0,haze=t.haze or 0,glare=t.glare or 0,
        bloom=t.bloom or 0,rays=t.rays or 0,rayTint=t.rayTint or WHITE,amb=t.amb,shiftTop=t.shiftTop or NONE,shiftBottom=t.shiftBottom or NONE,
        dof=t.dof or 0,dofFocus=t.dofFocus or 80,exposure=t.exposure or 0,lamp=t.lamp or 0,glow=t.glow or WHITE,glowBright=t.glowBright or 0,glowRange=t.glowRange or 40,
        vis=t.vis or 1000,fogStart=t.fogStart or 0,dome=t.dome or .15,stars=t.stars or -1,
    }
end

-- vis = Lighting.FogEnd: the distance in studs where scenery has fully faded into the fog colour; fogStart = where the fade begins.
-- Classic Lighting fog is the reliable view limiter (Studio test: Atmosphere.Density alone showed no fog); Atmosphere stays as an extra layer.
-- The near play area (25 studs) stays clear: fogStart >= 25 except in the blizzard whiteout.
Weather.Looks={
    clear=look({}),
    rain=look({tint=rgb(168,190,226),sat=-.22,contrast=.14,bright=-.06,fog=rgb(120,134,156),decay=rgb(70,84,110),density=.5,offset=0,haze=2.6,bloom=.2,
        amb=rgb(92,106,130),dof=.35,dofFocus=90,exposure=-.35,lamp=.8,fogStart=40,dome=.12,vis=260}),
    thunder=look({tint=rgb(160,174,222),sat=-.2,contrast=.18,bright=-.08,fog=rgb(88,96,132),decay=rgb(46,50,90),density=.56,offset=0,haze=3,bloom=.5,
        amb=rgb(104,116,160),dof=.45,dofFocus=80,exposure=-.3,lamp=1.4,glow=rgb(160,140,255),glowBright=.6,glowRange=60,fogStart=40,dome=.1,vis=200}),
    blizzard=look({tint=rgb(214,232,255),sat=-.4,contrast=-.06,bright=.08,fog=rgb(226,234,246),decay=rgb(200,216,240),density=.8,offset=0,haze=4,bloom=.45,rays=.1,
        rayTint=rgb(220,235,255),amb=rgb(172,184,206),dof=.6,dofFocus=40,lamp=.4,fogStart=25,dome=.08,vis=110}),
    volcano=look({tint=rgb(255,214,180),sat=.25,contrast=.12,bright=-.03,fog=rgb(150,84,56),decay=rgb(110,50,30),density=.4,offset=0,haze=2.4,glare=.3,bloom=.6,rays=.3,
        rayTint=rgb(255,150,70),amb=rgb(165,84,44),dof=.4,dofFocus=90,exposure=-.2,lamp=.5,glow=rgb(255,120,40),glowBright=1.4,glowRange=60,fogStart=70,dome=.15,vis=300}),
    -- aurora colours (fog, decay, shifts, ambient, tint, glow) are overwritten every frame from Weather.aurora(); these are the mid values
    aurora=look({tint=rgb(176,255,230),sat=.4,contrast=.1,bright=-.04,fog=rgb(40,200,170),decay=rgb(60,80,180),density=.32,offset=0,haze=1.4,bloom=1.2,rays=.05,
        rayTint=rgb(140,255,220),amb=rgb(70,130,120),dof=.2,dofFocus=120,exposure=-.2,lamp=.5,
        glow=rgb(60,255,170),glowBright=1.3,glowRange=60,fogStart=270,dome=.45,vis=330,stars=5000}),
    quake=look({tint=rgb(232,200,156),sat=-.14,contrast=.16,bright=-.06,fog=rgb(198,176,146),decay=rgb(130,100,70),density=.45,offset=0,haze=3,bloom=.15,
        amb=rgb(150,126,96),dof=.35,dofFocus=70,lamp=.6,fogStart=40,dome=.12,vis=220}),
    bloodmoon=look({tint=rgb(255,140,150),sat=.45,contrast=.18,bright=0,fog=rgb(66,14,24),decay=rgb(100,10,30),density=.4,offset=0,haze=2.8,glare=.5,bloom=.8,rays=.12,
        rayTint=rgb(255,60,80),amb=rgb(165,38,56),dof=.3,dofFocus=80,exposure=-.15,lamp=1.2,glow=rgb(255,40,70),glowBright=.5,glowRange=60,fogStart=100,dome=.18,vis=300}),
}
Weather.Ids=table.freeze({"rain","thunder","blizzard","volcano","aurora","quake","bloodmoon"})

-- Particle budget (desktop). rate = emitted per second for the whole group, life = {min,max} seconds; big = sprite size >= 30 studs (overdraw).
-- Phone density halves every rate. Concurrent particles of a group = rate * average lifetime.
export type Spec={rate:number,life:{number},big:boolean?}
local function spec(rate:number,a:number,b:number,big:boolean?):Spec return {rate=rate,life={a,b},big=big} end
Weather.Rigs={
    rain={streaks=spec(1400,.55,.7),splash=spec(320,.22,.38),mist=spec(14,3,4.5,true),curtain=spec(10,1.2,1.6,true),bank=spec(12,9,12,true)},
    thunder={streaks=spec(2000,.55,.7),splash=spec(420,.22,.38),mist=spec(16,3,4.5,true),curtain=spec(14,1.2,1.6,true),bank=spec(14,9,12,true)},
    blizzard={snow=spec(1300,3,4.2),gust=spec(50,1.4,2),drift=spec(16,2.6,3.4,true),bank=spec(16,7,9,true),flurry=spec(120,.9,1.3)},
    volcano={ash=spec(300,4,5.5),embers=spec(200,3,5),plume=spec(18,5,7,true),smoke=spec(12,8,11,true),haze=spec(5,10,12,true),bank=spec(8,9,11,true)},
    aurora={motes=spec(120,4,6),stars=spec(60,3,5),bank=spec(6,9,12,true)},
    quake={dust=spec(110,3,4.5),rubble=spec(120,1.2,1.8),bank=spec(14,8,10,true)},
    bloodmoon={motes=spec(140,4,6),fog=spec(16,5,7,true),bank=spec(14,9,11,true)},
}
Weather.Budget=table.freeze({concurrent=6000,bigConcurrent=500,bolts=4,bombs=6,beams=140})
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

-- Classic fog blend: FogEnd is blended in 1/distance so the view closes in smoothly instead of jumping at the start of the ramp.
function Weather.fog(look:Look,t:number,baseStart:number,baseEnd:number):(number,number)
    local inv=Weather.lerp(1/baseEnd,1/look.vis,t)
    return Weather.lerp(baseStart,look.fogStart,t),1/inv
end

return Weather
