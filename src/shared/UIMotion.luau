--!strict
-- BD-1182 (docs/228 board 6, docs/229): the UI motion presets as named numbers and pure timing functions. No Roblox service, no Instance,
-- no clock, no RNG: every function takes its time or its index as an argument, so tools/verify_ui_motion.py runs this file offline.
-- The part that moves things (TweenService through Theme.animate) lives in src/shared/UITheme.luau (button press) and
-- src/client/MotionFx.luau (window open / close), behind Config.MotionPresetsEnabled (default false, on only in the playtest profile).
-- Every preset takes `reduce` (Reduce Motion = not Theme.MotionEnabled): true gives the end state at once, 0 seconds, no movement.
-- Numbers marked "docs/228" are the proposal's; numbers marked PROVISIONAL are the lead's fill-ins where docs/228 names no number.
local M = {}

-- Window (docs/228): opens in 0.3 s with a back-out that peaks at 103%, then rests at 100%; closes in 0.15 s.
M.WindowOpenSeconds = 0.3
M.WindowOpenPeak = 1.03
M.BackOvershoot = 1.70158 -- the constant of the standard "Back" easing (Roblox Enum.EasingStyle.Back): Out peaks 10% of the travel past the goal
M.WindowCloseSeconds = 0.15
M.WindowCloseShrink = 0.96 -- today's close shrink, kept (PROVISIONAL: docs/228 says "fade"; the panel is no CanvasGroup, see docs/229)
M.WindowHideGap = 0.01 -- the window is hidden this long after the close tween (today: .12 tween, .13 hide)
-- Cards (docs/228): 70 ms apart, 0.4 s each, at most 8 staggered; cards after the 8th appear with the 8th.
M.CardStaggerSeconds = 0.07
M.CardSeconds = 0.4
M.CardStaggerMax = 8
-- Button (docs/228): a press sinks 5 px in 80 ms, the release pops to 103%.
M.PressSinkPixels = 5
M.PressSeconds = 0.08
M.ReleasePop = 1.03
M.ReleaseSettleSeconds = 0.12 -- PROVISIONAL: back from 103% to rest
-- News line (docs/228): top centre, 2.5 s; the same line again while it shows stacks as "x2", "x3".
M.NewsSeconds = 2.5
M.NewsStackMax = 99 -- PROVISIONAL: the counter stops at "x99"
-- Reward (docs/228): flies to the wallet in 0.5 s, the wallet bumps to 118%, the number counts up.
M.RewardFlySeconds = 0.5
M.WalletBump = 1.18
M.WalletBumpSeconds = 0.25 -- PROVISIONAL: up and back down
M.CountUpSeconds = 0.5 -- PROVISIONAL: starts when the reward lands
-- Shimmer (docs/228): every 2.8 s on Legendary and above.
M.ShimmerEverySeconds = 2.8
M.ShimmerSweepSeconds = 0.6 -- PROVISIONAL: one sweep, then rest until the next period
M.ShimmerMinRarity = 5 -- rank in Config.SpeciesRarityNames: 5 = Legendary (6 = Mythic)

-- The standard back-out curve: 0 at t = 0, 1 at t = 1, peaks at 1.10 near t = 0.58.
function M.backOut(t: number): number
    t = math.clamp(t, 0, 1)
    local s, u = M.BackOvershoot, t - 1
    return 1 + (s + 1) * u * u * u + s * u * u
end

local function backPeak(): number -- how far past the goal back-out goes, as a share of the travel (0.10 for the standard constant)
    local s = M.BackOvershoot
    local u = -2 * s / (3 * (s + 1))
    return (s + 1) * u * u * u + s * u * u
end

type Tween = {from: number, to: number, seconds: number, style: string}

-- Window open: one back-out tween of the window scale. `from` is chosen so that the overshoot peaks at WindowOpenPeak.
function M.windowOpen(reduce: boolean): Tween
    if reduce then return {from = 1, to = 1, seconds = 0, style = "None"} end
    return {from = 1 - (M.WindowOpenPeak - 1) / backPeak(), to = 1, seconds = M.WindowOpenSeconds, style = "Back"}
end

-- The window scale `t` seconds after it opened (1 = full size).
function M.windowOpenScale(t: number, reduce: boolean): number
    local plan = M.windowOpen(reduce)
    if plan.seconds <= 0 or t >= plan.seconds then return plan.to end
    return plan.from + (plan.to - plan.from) * M.backOut(math.max(t, 0) / plan.seconds)
end

-- Window close: tween seconds, the scale it ends at, and when to hide the window.
function M.windowClose(reduce: boolean): {seconds: number, shrink: number, hideAfter: number}
    if reduce then return {seconds = 0, shrink = 1, hideAfter = 0} end
    return {seconds = M.WindowCloseSeconds, shrink = M.WindowCloseShrink, hideAfter = M.WindowCloseSeconds + M.WindowHideGap}
end

-- Card number `index` (1 = first): when it starts and how long it takes. Cards after CardStaggerMax start with that card.
function M.card(index: number, reduce: boolean): {delay: number, seconds: number}
    if reduce then return {delay = 0, seconds = 0} end
    local slot = math.clamp(math.floor(index), 1, M.CardStaggerMax)
    return {delay = (slot - 1) * M.CardStaggerSeconds, seconds = M.CardSeconds}
end

-- When the last of `count` cards has arrived.
function M.cardsDone(count: number, reduce: boolean): number
    if count < 1 then return 0 end
    local last = M.card(count, reduce)
    return last.delay + last.seconds
end

-- Button press: how far it sinks (px) and how long that takes.
function M.press(reduce: boolean): {sink: number, seconds: number}
    if reduce then return {sink = 0, seconds = 0} end
    return {sink = M.PressSinkPixels, seconds = M.PressSeconds}
end

-- Button release: back up, a pop to ReleasePop, then back to rest.
function M.release(reduce: boolean): {pop: number, popSeconds: number, settleSeconds: number}
    if reduce then return {pop = 1, popSeconds = 0, settleSeconds = 0} end
    return {pop = M.ReleasePop, popSeconds = M.PressSeconds, settleSeconds = M.ReleaseSettleSeconds}
end

-- News line. One line at a time; the state is a plain table. `now` is any clock in seconds.
type News = {text: string?, count: number, shownAt: number}

function M.newsNew(): News
    return {text = nil, count = 0, shownAt = 0}
end

function M.newsVisible(state: News, now: number): boolean
    return state.text ~= nil and now - state.shownAt < M.NewsSeconds
end

-- A line arrives. "stack" = the same line is still showing: its counter goes up and its 2.5 s start again. "new" = a fresh line.
function M.newsPush(state: News, text: string, now: number): string
    if M.newsVisible(state, now) and state.text == text then
        state.count = math.min(state.count + 1, M.NewsStackMax)
        state.shownAt = now
        return "stack"
    end
    state.text, state.count, state.shownAt = text, 1, now
    return "new"
end

-- The words on screen: "AURORA SKY!", then "AURORA SKY! x2", "AURORA SKY! x3". nil when nothing shows.
function M.newsText(state: News, now: number): string?
    if not M.newsVisible(state, now) then return nil end
    local text = state.text :: string
    return if state.count >= 2 then text .. " x" .. state.count else text
end

-- How the line arrives: a short drop from above (PROVISIONAL 12 px in 0.2 s); under Reduce Motion it is simply there.
function M.newsDrop(reduce: boolean): {offset: number, seconds: number}
    if reduce then return {offset = 0, seconds = 0} end
    return {offset = 12, seconds = 0.2}
end

-- Reward: the flight to the wallet, then the wallet bump.
function M.reward(reduce: boolean): {flySeconds: number, bump: number, bumpSeconds: number, countSeconds: number}
    if reduce then return {flySeconds = 0, bump = 1, bumpSeconds = 0, countSeconds = 0} end
    return {flySeconds = M.RewardFlySeconds, bump = M.WalletBump, bumpSeconds = M.WalletBumpSeconds, countSeconds = M.CountUpSeconds}
end

-- The wallet scale `t` seconds after the reward landed: 1 -> WalletBump at the half-way point -> 1.
function M.walletScale(t: number, reduce: boolean): number
    local plan = M.reward(reduce)
    if plan.bumpSeconds <= 0 or t <= 0 or t >= plan.bumpSeconds then return 1 end
    local half = plan.bumpSeconds / 2
    local share = if t <= half then t / half else (plan.bumpSeconds - t) / half
    return 1 + (plan.bump - 1) * share
end

-- The number the wallet shows `t` seconds after the reward landed: a whole number that never passes `to`, eases out, and is exactly
-- `to` from CountUpSeconds on (and at once under Reduce Motion). Works downward too (a purchase).
function M.countUp(from: number, to: number, t: number, reduce: boolean): number
    local seconds = M.reward(reduce).countSeconds
    if seconds <= 0 or t >= seconds then return to end
    local share = math.clamp(t / seconds, 0, 1)
    local eased = 1 - (1 - share) * (1 - share)
    local value = from + (to - from) * eased
    return if to >= from then math.min(to, math.floor(value)) else math.max(to, math.ceil(value))
end

-- Shimmer: only Legendary and above.
function M.shimmerEligible(rarityRank: number): boolean
    return rarityRank >= M.ShimmerMinRarity
end

-- When shimmer number `n` (1 = first) starts, counted from when the card appeared. nil under Reduce Motion: no shimmer at all.
function M.shimmerAt(n: number, reduce: boolean): number?
    if reduce or n < 1 then return nil end
    return math.floor(n) * M.ShimmerEverySeconds
end

-- Where the shine is `t` seconds after the card appeared: 0..1 across the card during a sweep, nil while it rests (and always nil
-- under Reduce Motion or below Legendary).
function M.shimmerPhase(t: number, rarityRank: number, reduce: boolean): number?
    if reduce or not M.shimmerEligible(rarityRank) or t < M.ShimmerEverySeconds then return nil end
    local into = t % M.ShimmerEverySeconds
    if into >= M.ShimmerSweepSeconds then return nil end
    return into / M.ShimmerSweepSeconds
end

return M
