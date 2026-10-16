--!strict
-- BD-333 verification helper (also used from Studio execute_luau): walks every descendant of a GUI root and lists the
-- TextLabels/TextButtons whose rendered text is under the docs/72 floor (14 px) and the buttons under 44 px. Rendered size =
-- design TextSize times every UIScale above the object. Read-only; creates nothing and is not called during normal play.
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local PhoneScale = require(Shared:WaitForChild("PhoneScale"))

local UiScan = {}

local function chainScale(object: Instance, root: Instance): number
    local scale = 1
    local node: Instance? = object
    while node and node ~= root.Parent do
        local u = node:FindFirstChildOfClass("UIScale")
        if u then scale *= u.Scale end
        node = node.Parent
    end
    return scale
end

local function shown(object: GuiObject, root: Instance): boolean
    local node: Instance? = object
    while node and node ~= root.Parent do
        if node:IsA("GuiObject") and not node.Visible then return false end
        if node:IsA("ScreenGui") and not node.Enabled then return false end
        node = node.Parent
    end
    return true
end

-- Returns {texts = {{path, px, text}}, buttons = {{path, w, h, text}}, counts = {text, button}}
function UiScan.scan(root: Instance, minText: number?, minButton: number?)
    local floorText, floorButton = minText or PhoneScale.MinText, minButton or PhoneScale.MinButton
    local texts, buttons = {}, {}
    local textCount, buttonCount = 0, 0
    for _, d in root:GetDescendants() do
        if d:IsA("GuiObject") and shown(d, root) then
            if (d:IsA("TextLabel") or d:IsA("TextButton")) and d.Text ~= "" and d.TextTransparency < 1 then
                textCount += 1
                local scale = chainScale(d, root)
                -- TextScaled text: the used size is about TextBounds.Y of one line (measured: a 14 px label reports 14).
                local lines = select(2, string.gsub(d.Text, "\n", "")) + 1
                local px = if d.TextScaled then d.TextBounds.Y / lines else d.TextSize * scale
                if px < floorText - 0.01 then
                    table.insert(texts, {path = d:GetFullName(), px = math.floor(px * 10 + 0.5) / 10, text = string.sub(d.Text, 1, 24)})
                end
            end
            if d:IsA("TextButton") or d:IsA("ImageButton") then
                local a = d.AbsoluteSize
                if a.X > 4 and a.Y > 4 and (d:IsA("ImageButton") or d.BackgroundTransparency < 1) then
                    buttonCount += 1
                    if math.min(a.X, a.Y) < floorButton - 0.01 then
                        table.insert(buttons, {path = d:GetFullName(), w = math.floor(a.X), h = math.floor(a.Y), text = if d:IsA("TextButton") then string.sub(d.Text, 1, 24) else ""})
                    end
                end
            end
        end
    end
    return {texts = texts, buttons = buttons, counts = {text = textCount, button = buttonCount}}
end

-- One-line summary plus the worst few offenders, for execute_luau logs.
function UiScan.report(root: Instance, label: string): string
    local r = UiScan.scan(root)
    local out = {string.format("%s: %d texts (%d under 14 px), %d buttons (%d under 44 px)", label, r.counts.text, #r.texts, r.counts.button, #r.buttons)}
    table.sort(r.texts, function(a, b) return a.px < b.px end)
    table.sort(r.buttons, function(a, b) return math.min(a.w, a.h) < math.min(b.w, b.h) end)
    for i = 1, math.min(8, #r.texts) do table.insert(out, string.format("  text %.1f px '%s' %s", r.texts[i].px, r.texts[i].text, r.texts[i].path)) end
    for i = 1, math.min(8, #r.buttons) do table.insert(out, string.format("  button %dx%d '%s' %s", r.buttons[i].w, r.buttons[i].h, r.buttons[i].text, r.buttons[i].path)) end
    return table.concat(out, "\n")
end

return UiScan
