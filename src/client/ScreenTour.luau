--!strict
-- BD-1191 polish loop (docs/234): Studio only, a screen tour for the lead's captures: a BindableFunction "BeDinoScreenTour" under the player.
-- Invoke(name) opens that menu screen ("close" closes the menu) and returns the open screen's name. Bootstrap calls attach once, only when
-- RunService:IsStudio(), so it never exists in a live server. Lives here because Bootstrap.client is at its size ceiling (docs/150).
local Tour = {}

function Tour.attach(player: Instance, open: (string) -> (), close: () -> (), active: () -> string)
    if not game:GetService("RunService"):IsStudio() then return end
    local tour = Instance.new("BindableFunction")
    tour.Name = "BeDinoScreenTour"
    tour.OnInvoke = function(name)
        if name == "close" then close() else open(name) end
        return active()
    end
    tour.Parent = player
end

return Tour
