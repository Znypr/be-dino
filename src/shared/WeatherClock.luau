--!strict
local Config=require(script.Parent.ProgressionConfig)
local Clock={}
function Clock.new(now: number)
    return {current=nil,endsAt=0,nextAt=now+Config.WeatherInterval}
end
function Clock.step(state,now: number,choose): boolean
    if state.current and now>=state.endsAt then
        state.current=nil state.endsAt=0 state.nextAt=now+Config.WeatherInterval
        return true
    elseif not state.current and now>=state.nextAt then
        state.current=choose() state.endsAt=now+Config.WeatherDuration
        return true
    end
    return false
end
return Clock
