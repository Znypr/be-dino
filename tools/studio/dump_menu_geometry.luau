-- Menu spec check (tools/menu_spec_check.py): run in Studio PLAY, Client datamodel (execute_luau), with the menu open.
-- Every GuiObject the build marks with the attribute SpecId (e.g. "window", "card2.price", "rail.eggs") is reported with its screen
-- rect and the properties the checker compares: its own Text / font / size / colours, the first text label inside it ("innerText"),
-- UIStroke thickness and colour (on itself or on that label), background colour and UICorner. Returns one JSON string; save it as geom.json.
local Players = game:GetService("Players")
local GuiService = game:GetService("GuiService")
local HttpService = game:GetService("HttpService")

local function hex(c: Color3): string
	return string.format("#%02X%02X%02X", math.floor(c.R * 255 + .5), math.floor(c.G * 255 + .5), math.floor(c.B * 255 + .5))
end

local function textProps(t: Instance, into: {[string]: any}, prefix: string)
	if not (t:IsA("TextLabel") or t:IsA("TextButton") or t:IsA("TextBox")) then return end
	local tl = t :: TextLabel
	into[prefix .. "ext"] = tl.ContentText
	into[prefix .. "font"] = tostring(tl.FontFace.Family):match("([%w]+)%.json") or tostring(tl.Font)
	into[prefix .. "textSize"] = tl.TextScaled and math.floor(tl.TextBounds.Y + .5) or tl.TextSize
	into[prefix .. "textColor"] = hex(tl.TextColor3)
	local s = tl:FindFirstChildOfClass("UIStroke")
	if s then
		into[prefix .. "stroke"] = s.Thickness
		into[prefix .. "strokeColor"] = hex(s.Color)
	end
end

local gui = Players.LocalPlayer:WaitForChild("PlayerGui")
local out = {elements = {}}
local cam = workspace.CurrentCamera
out.viewport = {cam.ViewportSize.X, cam.ViewportSize.Y}
local inset = GuiService:GetGuiInset()
out.inset = {inset.X, inset.Y}
for _, o in gui:GetDescendants() do
	local id = o:GetAttribute("SpecId")
	if id and o:IsA("GuiObject") and o.Visible then
		local e: {[string]: any} = {rect = {o.AbsolutePosition.X, o.AbsolutePosition.Y, o.AbsoluteSize.X, o.AbsoluteSize.Y}}
		local sg = o:FindFirstAncestorOfClass("ScreenGui")
		if id == "window" and sg then out.ignoreInset = sg.IgnoreGuiInset end
		local t = {}
		textProps(o, t, "t")
		for k, v in t do e[(k == "text" and "text") or k:sub(2)] = v end
		if t.text then e.text = t.text end
		-- first text label inside (strip words, price, rail label)
		for _, d in o:GetDescendants() do
			if d:IsA("TextLabel") or d:IsA("TextButton") then
				e.innerText = (d :: TextLabel).ContentText
				local inner = {}
				textProps(d, inner, "i")
				e.innerFont, e.innerTextSize, e.innerStroke = inner.ifont, inner.itextSize, inner.istroke
				break
			end
		end
		if o.BackgroundTransparency < 1 then e.bg = hex(o.BackgroundColor3) end
		local corner = o:FindFirstChildOfClass("UICorner")
		if corner then e.corner = {corner.CornerRadius.Scale, corner.CornerRadius.Offset} end
		local stroke = o:FindFirstChildOfClass("UIStroke")
		if stroke and not e.stroke then e.stroke, e.strokeColor = stroke.Thickness, hex(stroke.Color) end
		if o:IsA("ImageLabel") or o:IsA("ImageButton") then e.image = (o :: ImageLabel).Image; e.imageLoaded = (o :: ImageLabel).IsLoaded end
		out.elements[id] = e
	end
end
if out.ignoreInset == nil then out.ignoreInset = true end
return HttpService:JSONEncode(out)
