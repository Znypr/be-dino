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
-- BD-120 admin: start an event now for `seconds`; the normal cycle resumes after it ends.
function Clock.force(state,now: number,event,seconds: number)
    state.current=event state.endsAt=now+seconds
end
-- BD-120 admin: end the current event now; the next random event is a full interval away.
function Clock.clear(state,now: number)
    state.current=nil state.endsAt=0 state.nextAt=now+Config.WeatherInterval
end
return Clock
