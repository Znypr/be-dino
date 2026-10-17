--!strict
-- Weather v3 (docs/84): client-local mood. Per event: Lighting grade, Atmosphere fog/haze, sky colour shift, bloom, depth of field,
-- distance fog banks, particle rigs that follow the player, pooled lightning, lava bombs, shock rings, quake ground cracks,
-- a full-sky aurora (rays + arcs + hue-cycling sky), blood moon with halos and a title card.
-- Data and math live in Shared/WeatherLooks (offline-checked by tools/verify_weather.py).
-- BD-131: each Blender weather texture (EffectAssets slot) is read through Shared/WeatherTextures; an EMPTY slot keeps the built-in sprite and
-- settings exactly as before, a valid id switches that rig to the texture, its flipbook layout and its own tuning.
-- Nothing here is authoritative or collides; the server only publishes WeatherId / WeatherName.
-- BD-627 (docs/153): the rigs, sky props, one-shots, quake and title card live in the sibling modules WeatherKit / WeatherRigs / WeatherSky /
-- WeatherStrikes / WeatherQuake / WeatherTitle (moved unchanged, built once below in the original order); this script keeps the Lighting grade,
-- atmosphere, clouds, the lamp, the main loop and the camera shake. Static checks read all of them through tools/weather_sources.py.
local Lighting=game:GetService("Lighting")
local Players=game:GetService("Players")
local RunService=game:GetService("RunService")
local UserInputService=game:GetService("UserInputService")
local Shared=game:GetService("ReplicatedStorage").Shared
local Theme=require(Shared.UITheme)
local WL=require(Shared.WeatherLooks)
local Cave=require(script.Parent.CaveAtmosphere) -- BD-286: cave-only look and weather stays outside (no-op while Config.CaveHub is false)
local player=Players.LocalPlayer
local random=Random.new()
local phone=UserInputService.TouchEnabled and not UserInputService.MouseEnabled
local Guards=require(Shared.PhoneGuards) -- BD-497: phone weather density .25 (docs/146 risk 5), tablet .5, desktop 1; Reduce Motion still emits nothing
local Kit=require(script.Parent.WeatherKit)
local Rigs=require(script.Parent.WeatherRigs)
local SkyProps=require(script.Parent.WeatherSky)
local Strikes=require(script.Parent.WeatherStrikes)
local Quake=require(script.Parent.WeatherQuake)
local Title=require(script.Parent.WeatherTitle)

local folder=Instance.new("Folder") folder.Name="LocalWeatherFX" folder.Parent=workspace

-- ---------------------------------------------------------------- post effects, atmosphere, sky
local grade=Instance.new("ColorCorrectionEffect") grade.Name="WeatherGrade" grade.Parent=Lighting
local bloom=Instance.new("BloomEffect") bloom.Name="WeatherBloom" bloom.Intensity,bloom.Size,bloom.Threshold=0,24,.9 bloom.Parent=Lighting
local rays=Instance.new("SunRaysEffect") rays.Name="WeatherRays" rays.Intensity,rays.Spread=0,.6 rays.Parent=Lighting
local dof=Instance.new("DepthOfFieldEffect") dof.Name="WeatherDof" dof.FarIntensity,dof.NearIntensity,dof.InFocusRadius,dof.FocusDistance=0,0,30,200
dof.Enabled=not phone dof.Parent=Lighting
local atmosphere=Lighting:FindFirstChildOfClass("Atmosphere")
if not atmosphere then
    atmosphere=Instance.new("Atmosphere") atmosphere.Density,atmosphere.Offset,atmosphere.Glare,atmosphere.Haze=0,0,0,0
    atmosphere.Name="WeatherAtmosphere" atmosphere.Parent=Lighting
end
local sky:Sky?=Lighting:FindFirstChildOfClass("Sky")
local baseAmbient,baseOutdoor=Lighting.Ambient,Lighting.OutdoorAmbient
local baseShiftTop,baseShiftBottom,baseExposure=Lighting.ColorShift_Top,Lighting.ColorShift_Bottom,Lighting.ExposureCompensation
-- BD-055 cloud cover: Terrain.Clouds follows the event look (cover, density, colour) with the same ramp as the grade. No texture is needed;
-- a place without Clouds gets one that starts invisible (cover 0), so clear weather looks exactly as before.
local clouds:Clouds=workspace.Terrain:FindFirstChildOfClass("Clouds") or Instance.new("Clouds")
if not clouds.Parent then clouds.Name="WeatherClouds" clouds.Cover,clouds.Density=0,.5 clouds.Parent=workspace.Terrain end
local baseCloud={cover=clouds.Cover,density=clouds.Density,color=clouds.Color}
local baseStars=if sky then sky.StarCount else 0
-- BD-213 soft visibility: clear weather keeps a gentle haze, and FogEnd stays inside this device's prop cull radius
-- (same device classes as WorldCulling.client.luau), so culled props are already lost in the haze and never pop.
local deviceClass=(function():string
    local size=workspace.CurrentCamera.ViewportSize
    return if not UserInputService.TouchEnabled then "Desktop" elseif math.min(size.X,size.Y)>=600 then "Tablet" else "Phone"
end)()
local DENSITY=if phone then Guards.weatherDensity(deviceClass) else 1 -- same classes as WorldCulling: touch + short side under 600 = Phone
local CLEAR=WL.clearFor(deviceClass) -- desktop/tablet: far clear fog, no 374-stud milky wall
local fogCap=(function():number
    local culling=require(Shared.Config).WorldCulling
    if not culling or not culling.Enabled then return WL.fogCap(nil) end
    return WL.capFor(deviceClass,culling[deviceClass].radius)
end)()
local baseAtmo={density=atmosphere.Density,offset=atmosphere.Offset,haze=atmosphere.Haze,glare=atmosphere.Glare,color=atmosphere.Color,decay=atmosphere.Decay}

-- ---------------------------------------------------------------- weather parts (docs/153); the flash / shake / pulse the one-shots raise are shared through fx
local fx={flash=0,shake=0,pulse=0}
local ctx:any={folder=folder,player=player,random=random,phone=phone,DENSITY=DENSITY,fx=fx,Cave=Cave}
local kit=Kit(ctx) ctx.kit=kit
local c3,volume,groundAt=kit.c3,kit.volume,kit.groundAt
local rigsMade=Rigs(ctx) ctx.curtainEmit=rigsMade.curtainEmit
local rig,rigParts,columns,COLUMN_OFFSETS=rigsMade.rig,rigsMade.rigParts,rigsMade.columns,rigsMade.COLUMN_OFFSETS

-- ---------------------------------------------------------------- lights that keep the near area bright and carry the event colour
local lampPart=volume(Vector3.one)
local lamp=Instance.new("PointLight") lamp.Name="WeatherLamp" lamp.Color,lamp.Range,lamp.Brightness,lamp.Shadows=Color3.fromRGB(255,244,226),32,0,false lamp.Parent=lampPart
local glow=Instance.new("PointLight") glow.Name="WeatherGlow" glow.Range,glow.Brightness,glow.Shadows=40,0,false glow.Parent=lampPart

local skyMade=SkyProps(ctx)
local updateAurora,updateMoon=skyMade.updateAurora,skyMade.updateMoon
local strikesMade=Strikes(ctx)
local bolt,lavaBomb,updateBolts,updateRings,updateBursts,updateBombs,stopOneShots=strikesMade.bolt,strikesMade.lavaBomb,strikesMade.updateBolts,strikesMade.updateRings,strikesMade.updateBursts,strikesMade.updateBombs,strikesMade.stopOneShots
local quakeMade=Quake(ctx)
local quakePulse,updateQuake,stopQuake=quakeMade.pulse,quakeMade.update,quakeMade.stop
local titleMade=Title(ctx)
local showTitle,softenTitle=titleMade.show,titleMade.soften

-- ---------------------------------------------------------------- main loop
local activeId="clear" local k=0 local shownId="clear"
local nextBolt=0 local nextDouble=0 local nextFar=0 local nextBomb=0 local nextQuakeBurst=0 local quakeUntil=0
local columnAnchors:{Vector3}?=nil
local colorClock=0 local starsSet=-1
local WHITE:{number}={255,255,255}
local lerpNum=WL.lerp
local function shiftOf(base:Color3,rgb:{number}):Color3
    if rgb[1]+rgb[2]+rgb[3]==0 then return base end
    return c3(rgb)
end

RunService.Heartbeat:Connect(function(dt)
    local now=os.clock()
    local id=workspace:GetAttribute("WeatherId") or "clear"
    local c=player.Character
    local rootPart=if c then c:FindFirstChild("HumanoidRootPart") else nil
    local root:Vector3?=if rootPart and rootPart:IsA("BasePart") then (rootPart::BasePart).Position else nil
    -- BD-398: inside the cave hall weather is nearly invisible: no rigs, bolts, bombs, cracks, moon, aurora, shake or title card
    local hall=Cave.inside() or Cave.amount()>.01
    if hall then softenTitle() end
    local motion=Theme.MotionEnabled and root~=nil and not hall
    -- fade current weather out, then switch; ramp the new one in
    if id==activeId then k=math.min(1,k+dt/2.4) else k=math.max(0,k-dt/1.1) if k<=0 then activeId=id columnAnchors=nil end end
    if activeId~=shownId and id==activeId and id~="clear" then
        shownId=activeId
        showTitle(id,workspace:GetAttribute("WeatherName") or id,hall) -- inside the cave only the small soft toast (text, not an effect; BD-398)
    elseif id=="clear" then shownId="clear" end

    local look=WL.Looks[activeId] or WL.Looks.clear
    local outside=1-Cave.amount() -- BD-383: weather grade, bloom, rays, haze, exposure and lamps fade to nothing inside the cave hall
    local t=WL.strength(k,Theme.MotionEnabled)*outside
    local animT=if Theme.MotionEnabled then now else 0
    fx.flash=math.max(0,fx.flash-dt*2.2) fx.pulse=math.max(0,fx.pulse-dt*.9)
    -- aurora recolours the whole sky from the hue cycle; every other event uses its fixed look
    local tint,fog,decay,shiftTop,shiftBottom,amb,glowRgb=look.tint,look.fog,look.decay,look.shiftTop,look.shiftBottom,look.amb,look.glow
    if activeId=="aurora" then
        fog=WL.scale(WL.aurora(animT,0),.3) decay=WL.scale(WL.aurora(animT,.45),.85)
        shiftTop=WL.scale(WL.aurora(animT,.25),.7) shiftBottom=WL.scale(WL.aurora(animT,.6),WL.Aurora.horizonGlow)
        amb=WL.scale(WL.aurora(animT,.1),.55) tint=WL.mix(WHITE,WL.aurora(animT,.35),.5) glowRgb=WL.aurora(animT,.7)
    end
    grade.TintColor=c3(WL.mix(WHITE,tint,t))
    grade.Saturation=lerpNum(0,look.sat,t)+CLEAR.sat*outside*(1-t) grade.Contrast=lerpNum(0,look.contrast,t)+CLEAR.contrast*outside*(1-t)
    grade.Brightness=lerpNum(0,look.bright,t)+(fx.flash*.5+fx.pulse*.12)*outside
    bloom.Intensity=lerpNum(0,look.bloom,t)+fx.flash*1.5*outside
    bloom.Threshold=lerpNum(.95,.72,t) bloom.Size=lerpNum(24,40,t)
    rays.Intensity=lerpNum(0,look.rays,t) rays.Spread=.7
    dof.FarIntensity=lerpNum(0,look.dof,t) dof.FocusDistance=lerpNum(250,look.dofFocus,t) dof.InFocusRadius=lerpNum(100,35,t)
    atmosphere.Density=lerpNum(baseAtmo.density,math.max(baseAtmo.density,look.density),t)
    atmosphere.Offset=lerpNum(baseAtmo.offset,look.offset,t)
    atmosphere.Haze=lerpNum(baseAtmo.haze,math.max(baseAtmo.haze,look.haze),t)
    atmosphere.Glare=lerpNum(baseAtmo.glare,math.max(baseAtmo.glare,look.glare),t)
    local fogStart,fogEnd=WL.fog(look,t,CLEAR,fogCap)
    local fogColor=c3(CLEAR.fog):Lerp(c3(fog),t)
    Lighting.FogStart,Lighting.FogEnd=fogStart,fogEnd Lighting.FogColor=fogColor
    atmosphere.Color=baseAtmo.color:Lerp(c3(fog),t)
    atmosphere.Decay=baseAtmo.decay:Lerp(c3(decay),t)
    -- sky treatment: colour shift on the sky dome and horizon, darker exposure, more stars
    Lighting.ColorShift_Top=baseShiftTop:Lerp(shiftOf(baseShiftTop,shiftTop),t)
    Lighting.ColorShift_Bottom=baseShiftBottom:Lerp(shiftOf(baseShiftBottom,shiftBottom),t)
    Lighting.ExposureCompensation=baseExposure+lerpNum(0,look.exposure,t)+fx.flash*.9*outside
    if look.cloudCover>=0 then
        clouds.Cover=lerpNum(baseCloud.cover,look.cloudCover,t) clouds.Density=lerpNum(baseCloud.density,look.cloudDensity,t)
        clouds.Color=baseCloud.color:Lerp(c3(look.cloudColor),t)
    else clouds.Cover,clouds.Density,clouds.Color=baseCloud.cover,baseCloud.density,baseCloud.color end
    if sky then sky.CelestialBodiesShown=activeId=="clear" or k<=0 or hall end
    if sky and look.stars>=0 then
        local want=math.floor(lerpNum(baseStars,look.stars,t)/100)*100
        if want~=starsSet then starsSet=want sky.StarCount=want end
    elseif sky and starsSet~=-1 then starsSet=-1 sky.StarCount=baseStars end
    -- world-wide light tint, so the whole scene (not just near the player) takes on the event mood
    local ambient=if amb then c3(amb) else baseAmbient
    Lighting.Ambient=baseAmbient:Lerp(ambient,t*.8) Lighting.OutdoorAmbient=baseOutdoor:Lerp(ambient,t)
    -- zoomed-out cameras see further: grow the particle volumes and keep their density
    local cam=workspace.CurrentCamera
    local zoom=if cam and root then math.clamp((cam.CFrame.Position-root).Magnitude/16,1,6) else 1
    -- near-area lamp (keeps the dino and food within about 25 studs bright) and the event-coloured glow
    if root then
        lampPart.Position=root+Vector3.new(0,7,0)
        lamp.Brightness=look.lamp*t
        glow.Color=c3(glowRgb) glow.Range=look.glowRange
        glow.Brightness=(look.glowBright*t+(if activeId=="thunder" then fx.flash*3*outside else 0))*(if Theme.MotionEnabled then 1 else .4)
    else lamp.Brightness=0 glow.Brightness=0 end

    -- particle rigs follow the player; only the active weather emits (BD-265: Settings Weather Full / Lite / Off; haze, light and title stay)
    local weatherFactor=require(Shared.SettingsModel).factor(require(Shared.SettingsModel).weather())
    for weatherId,list in rig do
        local on=motion and weatherId==activeId and k>0
        local scaleRate=math.min(zoom*zoom,5)
        for _,item in list do
            item.e.Enabled=on and weatherFactor>0 item.e.Rate=item.rate*k*weatherFactor*(if item.fixed then 1 else scaleRate)
        end
        if on and root then
            local parts=rigParts[weatherId]
            if parts then for _,p in parts do p.part.Size=Vector3.new(p.base.X*zoom,p.base.Y,p.base.Z*zoom) p.part.Position=root+p.offset end end
        end
    end
    local live=motion and root~=nil and not hall
    if not live then stopOneShots() end
    -- volcano: three far eruption columns + lava bombs
    if live and root and activeId=="volcano" and k>.3 then
        if not columnAnchors then
            local anchors:{Vector3}={}
            for i,offset in COLUMN_OFFSETS do anchors[i]=groundAt(root+offset) columns[i].Position=anchors[i] end
            columnAnchors=anchors
        end
        if now>=nextBomb then nextBomb=now+random:NextNumber(.45,1.1) lavaBomb(root) end
        fx.shake=math.max(fx.shake,.18)
    end
    -- thunder: forked bolts, double strikes and sheet-lightning flashes
    if live and root and activeId=="thunder" and k>.4 then
        if now>=nextBolt then
            nextBolt=now+random:NextNumber(2.2,5)
            if bolt(root) and random:NextNumber()<.35 then nextDouble=now+random:NextNumber(.15,.35) end
        end
        if nextDouble>0 and now>=nextDouble then nextDouble=0 bolt(root) end
        if now>=nextFar then nextFar=now+random:NextNumber(1.2,3) fx.flash=math.max(fx.flash,.3) end
    end
    -- thunder with Reduce Motion: no bolts or flashes, only a slow soft swell of light (never a strobe)
    if not Theme.MotionEnabled and not hall and activeId=="thunder" and k>.4 then
        fx.flash=math.max(fx.flash,WL.Swell.peak*(1+math.sin(now*WL.Swell.rate))/2)
    end
    -- quake: tremor pulses open ground cracks in view, with a gentle rumble synced to each pulse (none with Reduce Motion)
    if root and not hall and activeId=="quake" and k>.3 then
        if now>=nextQuakeBurst then
            nextQuakeBurst=now+random:NextNumber(WL.Quake.pulseEvery[1],WL.Quake.pulseEvery[2]) quakeUntil=now+WL.Quake.pulseSeconds
            quakePulse(root,Theme.MotionEnabled)
        end
        if motion and now<quakeUntil then fx.shake=math.max(fx.shake,WL.Quake.shake*math.sin(math.pi*(1-(quakeUntil-now)/WL.Quake.pulseSeconds))) end
    elseif activeId~="quake" or not root or hall then stopQuake() end
    -- blood moon sky props (WeatherSky.updateMoon)
    local moonOn=live and activeId=="bloodmoon" and k>0
    updateMoon(root,now,moonOn,k)
    -- aurora: full-sky rays and arcs, ground ring (hue colours refreshed 10 times a second)
    colorClock+=dt local recolor=colorClock>=.1 if recolor then colorClock=0 end
    local auroraOn=live and activeId=="aurora" and k>0
    updateAurora(root or Vector3.zero,now,auroraOn,recolor,k)
    -- pooled one-shot effects
    updateBolts(dt) updateRings(dt) updateBursts(dt) updateBombs(dt,root) updateQuake(dt)
    if hall then fx.shake=0 end -- BD-403: weather never touches the cave interior, not even a faint quake rumble
    if fx.shake>.01 and Theme.MotionEnabled then fx.shake=math.max(0,fx.shake-dt*1.1) end
    if not Theme.MotionEnabled then fx.shake=0 end
    Cave.step(dt) -- last: the cave look is written after the weather values above
end)
-- camera shake is applied after the camera script each frame, so it never fights the game's own camera offset
RunService:BindToRenderStep("WeatherShake",Enum.RenderPriority.Camera.Value+1,function()
    local camera=workspace.CurrentCamera
    if not camera or fx.shake<=.01 or not Theme.MotionEnabled then return end
    local n=os.clock()*38
    camera.CFrame*=CFrame.new(math.sin(n*1.3)*fx.shake*.45,math.cos(n*1.7)*fx.shake*.4,0)*CFrame.Angles(0,0,math.sin(n*.9)*fx.shake*.012)
end)
