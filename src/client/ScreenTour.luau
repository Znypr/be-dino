--!strict
-- BD-1191 polish loop (docs/234): a Studio-only screen tour for the lead's captures. Bootstrap calls this only when
-- RunService:IsStudio(), so it never exists in a live server. Invoke(name) opens a screen of the shared window; "close" closes it.
return function(player: Player, open: (string) -> (), close: () -> (), active: () -> string)
    local tour = Instance.new("BindableFunction")
    tour.Name = "BeDinoScreenTour"
    tour.OnInvoke = function(name: string)
        if name == "close" then close() else open(name) end
        return active()
    end
    tour.Parent = player
end
