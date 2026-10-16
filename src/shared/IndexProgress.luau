--!strict
-- BD-269: "Collected X of Y" percent bar with milestone ticks for the Dino Index. Pure; tested by
-- tools/verify_odds_copy.py. Milestones are display-only markers (no reward is promised here).
local Progress = {}
Progress.Milestones = {25, 50, 75, 100}
Progress.state = {page = 1} -- current Index page (client only; avoids a new top-level local in Bootstrap)

function Progress.summary(found: number, total: number)
    total = math.max(0, math.floor(total))
    found = math.clamp(math.floor(found), 0, total)
    local fraction = if total > 0 then found / total else 0
    local percent = math.floor(fraction * 100 + 1e-9)
    local ticks = {}
    for _, m in Progress.Milestones do
        table.insert(ticks, {percent = m, fraction = m / 100, reached = percent >= m})
    end
    return {
        found = found, total = total, fraction = fraction, percent = percent, ticks = ticks,
        text = string.format("Collected %d of %d  (%d%%)", found, total, percent),
    }
end

-- Paging for long lists so only one page of cards is built at a time (phone budget).
function Progress.page(count: number, perPage: number, page: number)
    perPage = math.max(1, math.floor(perPage))
    local pages = math.max(1, math.ceil(count / perPage))
    page = math.clamp(math.floor(page), 1, pages)
    local first = (page - 1) * perPage + 1
    return {page = page, pages = pages, first = first, last = math.min(count, first + perPage - 1)}
end

-- BD-332: card sizes for the Dino Index list (design pixels). The roomy card (name, odds, big dino, counts, VIEW DINO button)
-- is 242 + button tall, so a 326 px list showed about one row. When two roomy rows do not fit, use the compact card: the whole
-- card is the button (no VIEW DINO bar), a shorter dino and smaller text, sized so two full rows always fit the list.
function Progress.cardLayout(viewportScale: number, listHeight: number)
    local button = math.max(45, 45 / math.max(0.05, viewportScale))
    local roomy = 242 + button
    if listHeight >= 2 * roomy + 12 then
        return {compact = false, cardHeight = roomy, rowHeight = roomy + 12, buttonHeight = button, heroY = 70, heroHeight = 128, detailY = 201}
    end
    local card = math.max(120, math.floor((listHeight - 12) / 2))
    return {compact = true, cardHeight = card, rowHeight = card + 12, buttonHeight = 0, heroY = 50, heroHeight = card - 50 - 26, detailY = card - 24}
end

return Progress
