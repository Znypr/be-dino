--!strict
-- Weather audio layer (docs/85): a quiet looping bed per event that fades in and out with the weather, plus one-shot accents
-- (thunder strike and roll, eruption boom, quake burst) fired by WeatherVisuals through the WeatherSounds cue bus.
-- Every sound id is empty until the owner uploads the briefed sounds; empty ids are skipped silently.
local RunService=game:GetService("RunService")
local SoundService=game:GetService("SoundService")
local Shared=game:GetService("ReplicatedStorage").Shared
local Theme=require(Shared.UITheme)
local WS=require(Shared.WeatherSounds)
local Mixer=require(Shared.AudioMixer)

local folder=Instance.new("Folder") folder.Name="WeatherAudio" folder.Parent=SoundService
local beds:{[string]:Sound}={}
local levels:{[string]:number}={}
local accents:{[string]:{sound:Sound,last:number}}={}

-- create every sound that has a valid id once, at start (no Instance creation while playing)
for name,entry in WS.Sounds do
    local assetId=WS.normalizeId(entry.id)
    if assetId then
        local sound=Instance.new("Sound") sound.Name=name sound.SoundId=assetId sound.Volume=0 sound.Looped=entry.loop
        sound.RollOffMaxDistance=0 sound.Parent=folder
        Mixer.attach(sound,"ambience") -- weather beds and accents follow the Weather slider
        if entry.loop then beds[name]=sound levels[name]=0 else accents[name]={sound=sound,last=-100} end
    end
end

local activeId="clear" local k=0
local function soundOn():boolean return Theme.HatchSoundEnabled~=false end

RunService.Heartbeat:Connect(function(dt)
    local id=workspace:GetAttribute("WeatherId") or "clear"
    if id==activeId then k=math.min(1,k+dt/WS.FadeSeconds) else k=math.max(0,k-dt/WS.FadeSeconds) if k<=0 then activeId=id end end
    local on=soundOn()
    for name,sound in beds do
        local level=WS.step(levels[name],WS.bedTarget(name,activeId,k,on),dt)
        levels[name]=level
        sound.Volume=level
        if level>.002 then if not sound.IsPlaying then sound:Play() end elseif sound.IsPlaying then sound:Stop() end
    end
end)

WS.connect(function(cueName:string)
    if not soundOn() then return end
    local id=workspace:GetAttribute("WeatherId") or "clear"
    for _,item in WS.cue(id,cueName) do
        local name,delay=item[1] :: string,item[2] :: number
        local accent=accents[name]
        if accent then
            task.delay(delay,function()
                local entry=WS.Sounds[name]
                local now=os.clock()
                if now-accent.last<(entry.gap or 0) then return end
                accent.last=now
                accent.sound.Volume=entry.volume
                accent.sound.TimePosition=0
                accent.sound:Play()
            end)
        end
    end
end)
