-- Objectives e2e (BD-078): read-only GUI probe (Client datamodel). Prints the objectives panel texts, the goal line, the wallet text and the
-- panel rects. No clicks, no state changes. Used between steps; the run was driven only through the same remotes the UI uses.
local Players = game:GetService("Players")
local player = Players.LocalPlayer
local gui = player.PlayerGui:FindFirstChild("BeDinoUI")
local out = {}
local function add(s) table.insert(out, s) end
if not gui then return "no BeDinoUI" end
add("attrs ObjectivesRect=" .. tostring(gui:GetAttribute("ObjectivesRect")) .. " ObjectivesOpenRect=" .. tostring(gui:GetAttribute("ObjectivesOpenRect")))
local goal = gui:FindFirstChild("NextGoal", true)
if goal then -- NextGoal is a Frame: its text is in a TextLabel child
	add("GOAL FRAME visible=" .. tostring(goal.Visible) .. " abs=" .. tostring(goal.AbsolutePosition) .. " size=" .. tostring(goal.AbsoluteSize))
	for _, d in goal:GetDescendants() do if d:IsA("TextLabel") then add("  goal text '" .. d.Text .. "' textBounds=" .. tostring(d.TextBounds) .. " label=" .. tostring(d.AbsoluteSize)) end end
end
for _, d in gui:GetDescendants() do
	if (d:IsA("TextLabel") or d:IsA("TextButton")) and d.Text ~= "" then
		local vis = d.Visible
		local p = d.Parent
		while p and p ~= gui do if p:IsA("GuiObject") and not p.Visible then vis = false end p = p.Parent end
		if vis then
			local t = d.Text
			if string.find(t, "crystal") or string.find(t, "CLAIM") or string.find(t, "TASKS") or string.find(t, "tasks") or string.find(t, "Done") or string.find(t, "/") or string.find(t, "Eat ") or string.find(t, "Hatch") or string.find(t, "Finish") or string.find(t, "Claim") then
				add(string.format("%s '%s' pos=(%d,%d) size=(%d,%d)", d.ClassName, t, d.AbsolutePosition.X, d.AbsolutePosition.Y, d.AbsoluteSize.X, d.AbsoluteSize.Y))
			end
		end
	end
end
return table.concat(out, "\n")
