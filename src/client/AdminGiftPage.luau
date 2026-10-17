--!strict
-- BD-452 (docs/134 s5, docs/79): the admin panel's "Gift" page. Built by AdminPanel ONLY when the server created the AdminGiftAction remote,
-- i.e. when GiftClaimEnabled, AdminGiftsEnabled and AdminPanelEnabled are all on (pinned off). Every button here only ASKS; the server
-- (AdminGifts) re-checks the admin, the person, the item, the amount and the message. The label is always GiftRules.TeamLine.
-- Developer tool, no new art: UITheme colours, plain buttons (>= 44 px high) and text (>= 14 px). The avatar is Roblox's own head shot of
-- the person being confirmed.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Shared = ReplicatedStorage:WaitForChild("Shared")
local Theme = require(Shared:WaitForChild("UITheme"))
local GiftRules = require(Shared:WaitForChild("GiftRules"))
local PageRules = require(Shared:WaitForChild("AdminGiftRules"))
local C = Theme.Colors

local AdminGiftPage = {}

local function label(parent: Instance, value: string, size: number, height: number): TextLabel
    local item = Instance.new("TextLabel")
    item.BackgroundTransparency, item.Size, item.Text = 1, UDim2.new(1, 0, 0, height), value
    item.TextSize = size
    item.Font, item.TextColor3 = Enum.Font.FredokaOne, C.text
    item.TextStrokeTransparency, item.TextXAlignment, item.TextWrapped = 0, Enum.TextXAlignment.Left, true
    item.Parent = parent
    return item
end
local function button(parent: Instance, value: string, color: Color3, size: UDim2): TextButton
    local item = Instance.new("TextButton")
    item.Size, item.BackgroundColor3, item.Text, item.TextColor3 = size, color, value, C.text
    item.TextSize = 18
    item.Font, item.TextWrapped, item.AutoButtonColor = Enum.Font.FredokaOne, true, false
    item.Parent = parent
    Theme.decorate(item, 8)
    return item
end
local function box(parent: Instance, hint: string, size: UDim2): TextBox
    local item = Instance.new("TextBox")
    item.Size, item.BackgroundColor3, item.Text, item.PlaceholderText = size, C.card, "", hint
    item.TextSize = 18
    item.Font, item.TextColor3, item.PlaceholderColor3 = Enum.Font.FredokaOne, C.text, Color3.fromRGB(170, 170, 185)
    item.ClearTextOnFocus, item.TextXAlignment = false, Enum.TextXAlignment.Left
    item.Parent = parent
    Theme.decorate(item, 8)
    return item
end

-- `panel` is the admin panel frame, `top` the pixel row where its pages start (below the tab row).
function AdminGiftPage.build(panel: Frame, remote: RemoteFunction, top: number): ScrollingFrame
    local page = Instance.new("ScrollingFrame")
    page.Name, page.Visible = "AdminGiftPage", false
    page.BackgroundTransparency, page.BorderSizePixel, page.ScrollBarThickness = 1, 0, 6
    page.Position, page.Size = UDim2.fromOffset(10, top), UDim2.new(1, -20, 1, -(top + 8))
    page.AutomaticCanvasSize, page.CanvasSize = Enum.AutomaticSize.Y, UDim2.new()
    page.Parent = panel
    local padding = Instance.new("UIPadding") padding.PaddingRight = UDim.new(0, 12) padding.Parent = page
    local list = Instance.new("UIListLayout")
    list.Padding, list.SortOrder = UDim.new(0, 8), Enum.SortOrder.LayoutOrder
    list.Parent = page
    local order = 0
    local function place<T>(object: T): T
        order += 1
        (object :: any).LayoutOrder = order
        return object
    end
    local function section(title: string)
        local header = place(label(page, title, 24, 34))
        header.TextColor3 = C.gold
        local line = Instance.new("Frame")
        line.BackgroundColor3, line.BorderSizePixel, line.Position, line.Size, line.Parent = C.gold, 0, UDim2.new(0, 0, 1, -3), UDim2.new(1, 0, 0, 2), header
    end
    local function grid(cellHeight: number): Frame
        local holder = place(Instance.new("Frame"))
        holder.BackgroundTransparency, holder.AutomaticSize, holder.Size, holder.Parent = 1, Enum.AutomaticSize.Y, UDim2.new(1, 0, 0, 0), page
        local layout = Instance.new("UIGridLayout")
        layout.CellSize, layout.CellPadding = UDim2.new(0.5, -4, 0, cellHeight), UDim2.fromOffset(8, 8)
        layout.SortOrder, layout.Parent = Enum.SortOrder.LayoutOrder, holder
        return holder
    end
    local function row(height: number): Frame
        local holder = place(Instance.new("Frame"))
        holder.BackgroundTransparency, holder.Size, holder.Parent = 1, UDim2.new(1, 0, 0, height), page
        local layout = Instance.new("UIListLayout")
        layout.FillDirection, layout.Padding = Enum.FillDirection.Horizontal, UDim.new(0, 8)
        layout.Parent = holder
        return holder
    end

    place(label(page, "Free gift", 28, 36))
    local teamLine = place(label(page, "They see: " .. GiftRules.TeamLine, 18, 46))
    teamLine.TextColor3 = C.gold
    local status = place(label(page, "Pick who, pick a gift, tap Send.", 18, 46))
    status.TextColor3 = C.gold
    local function say(text: string, good: boolean)
        status.Text = text
        status.TextColor3 = if good then C.accent else C.red
    end
    local busy = false
    -- One request at a time; a throw or a bad answer becomes the code "error".
    local function ask(request: {[string]: any}): any
        if busy then return {ok = false, reason = "busy"} end
        busy = true
        local ok, response = pcall(remote.InvokeServer, remote, request)
        busy = false
        if not ok or type(response) ~= "table" then return {ok = false, reason = "error"} end
        return response
    end

    -- ------------------------------------------------------------ who
    section("Who")
    local chosen: {userId: number, displayName: string, username: string}? = nil
    local isConfirmed = false
    local selectedItem: string? = nil
    local selectedMsg: string? = nil
    local armedRevoke = 0
    local revokeItem: string? = nil
    local refreshSummary: () -> () = function() end

    place(label(page, "Players here", 18, 26))
    local playerGrid = grid(44)
    local card = Instance.new("Frame") -- placed (LayoutOrder) under the typed-name row below
    card.BackgroundColor3, card.Size, card.Visible, card.Parent = C.card, UDim2.new(1, 0, 0, 148), false, page
    Theme.decorate(card, 8)
    local avatar = Instance.new("ImageLabel")
    avatar.BackgroundColor3, avatar.Position, avatar.Size, avatar.Parent = C.panel, UDim2.fromOffset(10, 10), UDim2.fromOffset(64, 64), card
    local cardName = label(card, "", 20, 64)
    cardName.Position, cardName.Size = UDim2.fromOffset(86, 10), UDim2.new(1, -96, 0, 64)
    local confirmRow = Instance.new("Frame")
    confirmRow.BackgroundTransparency, confirmRow.Position, confirmRow.Size, confirmRow.Parent = 1, UDim2.fromOffset(10, 90), UDim2.new(1, -20, 0, 48), card
    local confirmLayout = Instance.new("UIListLayout")
    confirmLayout.FillDirection, confirmLayout.Padding = Enum.FillDirection.Horizontal, UDim.new(0, 8)
    confirmLayout.Parent = confirmRow
    local yes = button(confirmRow, "Yes, that's them", C.accent, UDim2.new(0.6, -4, 1, 0))
    local no = button(confirmRow, "No", C.card, UDim2.new(0.4, -4, 1, 0))

    local function showCard(who: {userId: number, displayName: string, username: string})
        chosen, isConfirmed = who, false
        card.Visible, confirmRow.Visible = true, true
        cardName.Text = who.displayName .. "\n@" .. who.username
        avatar.Image = ""
        task.spawn(function()
            local ok, image = pcall(function()
                return Players:GetUserThumbnailAsync(who.userId, Enum.ThumbnailType.HeadShot, Enum.ThumbnailSize.Size100x100)
            end)
            if ok and chosen == who then avatar.Image = image end
        end)
        refreshSummary()
    end

    local function refreshPlayers()
        for _, child in playerGrid:GetChildren() do
            if child:IsA("TextButton") then child:Destroy() end
        end
        local shown = 0
        for _, other in Players:GetPlayers() do
            shown += 1
            if shown > 16 then break end
            local pick = button(playerGrid, other.DisplayName, C.card, UDim2.new())
            pick.LayoutOrder = shown
            pick.Activated:Connect(function()
                local answer = ask({action = "pick", userId = other.UserId})
                if answer.ok == true then
                    showCard({userId = answer.userId, displayName = answer.displayName, username = answer.username})
                    say("Is this the right player?", true)
                else
                    say(PageRules.explain(answer.reason), false)
                end
            end)
        end
    end
    refreshPlayers()
    Players.PlayerAdded:Connect(refreshPlayers)
    Players.PlayerRemoving:Connect(function() task.defer(refreshPlayers) end)

    place(label(page, "Or type a username", 18, 26))
    local nameRow = row(48)
    local nameBox = box(nameRow, "Username", UDim2.new(0.62, -4, 1, 0))
    local find = button(nameRow, "Find", C.blue, UDim2.new(0.38, -4, 1, 0))
    find.Activated:Connect(function()
        if not PageRules.validName(nameBox.Text) then say(PageRules.explain("bad_name"), false) return end
        say("Looking...", true)
        local answer = ask({action = "lookup", name = nameBox.Text})
        if answer.ok == true then
            showCard({userId = answer.userId, displayName = answer.displayName, username = answer.username})
            say("Is this the right player?", true)
        else
            say(PageRules.explain(answer.reason), false)
        end
    end)
    place(card)
    local userBox: TextBox? = nil
    local giftIdBox: TextBox? = nil
    local recipientBox: TextBox? = nil
    yes.Activated:Connect(function()
        local who = chosen
        if who == nil then return end
        local answer = ask({action = "confirm", userId = who.userId})
        if answer.ok == true then
            isConfirmed = true
            confirmRow.Visible = false
            cardName.Text = who.displayName .. "\n@" .. who.username .. "  (ready)"
            if userBox then userBox.Text = tostring(who.userId) end
            if recipientBox then recipientBox.Text = tostring(who.userId) end
            say("Now pick a gift.", true)
            refreshSummary()
        else
            say(PageRules.explain(answer.reason), false)
        end
    end)
    no.Activated:Connect(function()
        chosen, isConfirmed = nil, false
        card.Visible = false
        say("Pick someone else.", true)
        refreshSummary()
    end)

    -- ------------------------------------------------------------ gift
    section("Gift")
    local itemGrid = grid(44)
    local itemButtons: {[TextButton]: string} = {}
    local amountHolder = place(Instance.new("Frame"))
    amountHolder.BackgroundTransparency, amountHolder.AutomaticSize, amountHolder.Size, amountHolder.Visible, amountHolder.Parent = 1, Enum.AutomaticSize.Y, UDim2.new(1, 0, 0, 0), false, page
    local amountLayout = Instance.new("UIListLayout")
    amountLayout.Padding, amountLayout.SortOrder, amountLayout.Parent = UDim.new(0, 8), Enum.SortOrder.LayoutOrder, amountHolder
    local amountBox = box(amountHolder, "How many crystals (1 to 50,000)", UDim2.new(1, 0, 0, 48))
    amountBox.LayoutOrder = 1
    local chips = Instance.new("Frame")
    chips.BackgroundTransparency, chips.AutomaticSize, chips.Size, chips.LayoutOrder, chips.Parent = 1, Enum.AutomaticSize.Y, UDim2.new(1, 0, 0, 0), 2, amountHolder
    local chipLayout = Instance.new("UIGridLayout")
    chipLayout.CellSize, chipLayout.CellPadding = UDim2.new(1 / 3, -6, 0, 44), UDim2.fromOffset(8, 8)
    chipLayout.SortOrder, chipLayout.Parent = Enum.SortOrder.LayoutOrder, chips
    for index, amount in PageRules.CrystalChips do
        local chip = button(chips, string.format("%d", amount), C.card, UDim2.new())
        chip.LayoutOrder = index
        chip.Activated:Connect(function() amountBox.Text = tostring(amount) refreshSummary() end)
    end
    amountBox:GetPropertyChangedSignal("Text"):Connect(function() refreshSummary() end)

    local function paint()
        for b, id in itemButtons do b.BackgroundColor3 = if id == selectedItem then C.accent else C.card end
        amountHolder.Visible = selectedItem == GiftRules.CustomCrystalsId
    end
    for index, choice in PageRules.choices() do
        local b = button(itemGrid, choice.label, C.card, UDim2.new())
        b.LayoutOrder = index
        itemButtons[b] = choice.id
        b.Activated:Connect(function() selectedItem = choice.id paint() refreshSummary() end)
    end

    place(label(page, "Message", 18, 26))
    local msgGrid = grid(44)
    local msgButtons: {[TextButton]: string} = {}
    local function paintMsg()
        for b, id in msgButtons do b.BackgroundColor3 = if id == (selectedMsg or "") then C.blue else C.card end
    end
    local none = button(msgGrid, "No message", C.blue, UDim2.new())
    none.LayoutOrder = 0
    msgButtons[none] = ""
    none.Activated:Connect(function() selectedMsg = nil paintMsg() end)
    for index, preset in GiftRules.Presets do
        local b = button(msgGrid, preset.text, C.card, UDim2.new())
        b.LayoutOrder = index
        msgButtons[b] = preset.id
        b.Activated:Connect(function() selectedMsg = preset.id paintMsg() end)
    end
    paint()
    paintMsg()

    local summary = place(label(page, "", 18, 46))
    summary.TextColor3 = C.text
    local send = place(button(page, "Send free gift", C.accent, UDim2.new(1, 0, 0, 56)))
    local function itemText(): string?
        local id = selectedItem
        if id == nil then return nil end
        if id == GiftRules.CustomCrystalsId then
            local amount = PageRules.parseAmount(amountBox.Text)
            return if amount then string.format("%d crystals", amount) else nil
        end
        local entry = GiftRules.ById[id]
        return if entry then entry.label else nil
    end
    refreshSummary = function()
        local item = itemText()
        local who = chosen
        local ready = who ~= nil and isConfirmed and item ~= nil
        if who == nil then
            summary.Text = "Pick a player first."
        elseif not isConfirmed then
            summary.Text = "Tap Yes on the player card."
        elseif item == nil then
            summary.Text = if selectedItem == GiftRules.CustomCrystalsId then "Type 1 to 50,000 crystals." else "Pick a gift."
        else
            summary.Text = item .. " to " .. who.displayName
        end
        send.BackgroundColor3 = if ready then C.accent else C.card
    end
    send.Activated:Connect(function()
        local who, item = chosen, selectedItem
        if who == nil or not isConfirmed then say(PageRules.explain("not_confirmed"), false) return end
        if item == nil then say(PageRules.explain("unknown_item"), false) return end
        local request: {[string]: any} = {action = "send", to = who.userId, item = item, msg = selectedMsg}
        if item == GiftRules.CustomCrystalsId then
            local amount = PageRules.parseAmount(amountBox.Text)
            if amount == nil then say(PageRules.explain("bad_amount"), false) return end
            request.crystals = amount
        end
        local answer = ask(request)
        if answer.ok == true then
            say(if answer.status == "duplicate" then PageRules.Done.duplicate else PageRules.Done.send, true)
            if type(answer.giftId) == "string" and giftIdBox then giftIdBox.Text = answer.giftId end
        else
            say(PageRules.explain(answer.reason), false)
        end
    end)
    refreshSummary()

    -- ------------------------------------------------------------ take back
    section("Take back a gift")
    giftIdBox = box(page, "Gift id", UDim2.new(1, 0, 0, 48))
    place(giftIdBox :: TextBox)
    recipientBox = box(page, "Player id", UDim2.new(1, 0, 0, 48))
    place(recipientBox :: TextBox)
    local take = place(button(page, "Take back", C.red, UDim2.new(1, 0, 0, 52)))
    take.Activated:Connect(function()
        local idBox, whoBox = giftIdBox :: TextBox, recipientBox :: TextBox
        local recipient = tonumber(whoBox.Text)
        if recipient == nil or not GiftRules.validUserId(recipient) or not GiftRules.validId(idBox.Text) then
            say(PageRules.explain("bad_request"), false)
            return
        end
        -- Two taps: the first arms the button, the second (within 6 seconds) does it.
        if os.clock() - armedRevoke > 6 then
            armedRevoke = os.clock()
            take.Text = "Tap again to take it back"
            say("Tap again within 6 seconds.", true)
            task.delay(6, function() if os.clock() - armedRevoke >= 6 then take.Text = "Take back" end end)
            return
        end
        armedRevoke = 0
        take.Text = "Take back"
        local request: {[string]: any} = {action = "revoke", to = recipient, giftId = idBox.Text}
        if revokeItem ~= nil then request.item = revokeItem end
        local answer = ask(request)
        if answer.ok == true then
            say(PageRules.Done[answer.status] or PageRules.Done.revoked, true)
        else
            say(PageRules.explain(answer.reason), false)
        end
    end)

    -- ------------------------------------------------------------ history
    section("Gift history")
    local historyRow = row(48)
    userBox = box(historyRow, "Player id", UDim2.new(0.62, -4, 1, 0))
    local show = button(historyRow, "Show", C.blue, UDim2.new(0.38, -4, 1, 0))
    local results = place(Instance.new("Frame"))
    results.BackgroundTransparency, results.AutomaticSize, results.Size, results.Parent = 1, Enum.AutomaticSize.Y, UDim2.new(1, 0, 0, 0), page
    local resultsLayout = Instance.new("UIListLayout")
    resultsLayout.Padding, resultsLayout.SortOrder, resultsLayout.Parent = UDim.new(0, 6), Enum.SortOrder.LayoutOrder, results
    show.Activated:Connect(function()
        local id = tonumber((userBox :: TextBox).Text)
        if id == nil or not GiftRules.validUserId(id) then say(PageRules.explain("bad_request"), false) return end
        local answer = ask({action = "audit", userId = id})
        for _, child in results:GetChildren() do
            if child:IsA("TextButton") then child:Destroy() end
        end
        if answer.ok ~= true then say(PageRules.explain(answer.reason), false) return end
        local events = answer.events
        if type(events) ~= "table" or #events == 0 then say("Nothing yet for that player.", true) return end
        say("Tap a line to fill the take-back boxes.", true)
        for index, event in events do
            local line = button(results, PageRules.historyLine(event), C.card, UDim2.new(1, 0, 0, 56))
            line.TextSize = 15
            line.TextXAlignment, line.LayoutOrder = Enum.TextXAlignment.Left, index
            line.Activated:Connect(function()
                if type(event.giftId) ~= "string" then return end
                (giftIdBox :: TextBox).Text = event.giftId
                if event.to ~= nil then (recipientBox :: TextBox).Text = tostring(event.to) end
                revokeItem = if type(event.item) == "string" then event.item else nil
                say("Filled in. Scroll up to take it back.", true)
            end)
        end
    end)

    return page
end

return AdminGiftPage
