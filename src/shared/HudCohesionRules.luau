--!strict
-- BD-1213 (docs/240 step 2, style tile v2 board 1): the pure rules of the in-run HUD and the world labels on the style rules R1-R8, used by
-- src/client/HudCohesion.client.luau ONLY while Config.HudCohesionEnabled is on. Offline-tested by tools/verify_hud_cohesion.py.
local Rules = {}

-- R6 kid copy: the crystal count is a grouped number beside the crystal picture ("12,450"), never "1000000 Crystals".
function Rules.grouped(amount: number): string
    local whole = math.max(0, math.floor(amount + 0.5))
    local digits = tostring(whole)
    local out = ""
    local count = 0
    for i = #digits, 1, -1 do
        out = string.sub(digits, i, i) .. out
        count += 1
        if count % 3 == 0 and i > 1 then out = "," .. out end
    end
    return out
end

-- The number inside Bootstrap's "N Crystals" text; nil for anything else (an already grouped number is left alone, so the rewrite stops).
function Rules.crystalsFrom(text: string): number?
    local digits = string.match(text, "^(%d+) Crystals$")
    return if digits then tonumber(digits) else nil
end

-- R2 / R6: the three debug lines (build id, food count, Studio preview) leave the HUD; the preview warning becomes ONE small cream chip in kid words,
-- shown only in an unsaved Studio preview (never in a live game).
Rules.TestChip = "Test game: not saved"
Rules.TestChipW, Rules.TestChipH = 184, 26
-- The chip inside the old preview line's slot (w x h px): never wider or taller than the slot, never taller than the chip.
function Rules.chipSize(slotW: number, slotH: number): (number, number)
    return math.min(Rules.TestChipW, slotW), math.min(Rules.TestChipH, slotH)
end
Rules.PreviewMode = "Studio preview (not saved)"
function Rules.testChipVisible(profileMode: any): boolean
    return profileMode == Rules.PreviewMode
end

-- The text sizes of the HUD on the R6 scale (28 / 20 / 16 / 14).
Rules.Scale = {28, 20, 16, 14}
Rules.Text = {crystals = 20, goal = 16, chip = 14, worldLabel = 20}
function Rules.onScale(size: number): boolean
    return table.find(Rules.Scale, size) ~= nil
end

-- R8 "badges on words": the key badge (E / F) hangs on the TOP EDGE of its button, half above it, so it can never cover the word, which is
-- centred in the button. Returns the badge's anchor and offset from the top-right corner.
function Rules.badgeSpot(inset: number): (Vector2, number, number)
    return Vector2.new(1, 0.5), -inset, 0
end
-- Is the badge clear of a word of `word` px centred in a button `height` px high (the badge's lower half ends at badge / 2)?
function Rules.badgeClear(height: number, badge: number, word: number): boolean
    return badge / 2 <= (height - word) / 2
end

-- R8 world labels: "+3 Crystals" floats above the top of its pickup model (the model hid the middle of the words: "+3 C...tals").
Rules.LabelGap = 1.2
function Rules.labelLift(modelTop: number, anchorY: number): number
    return math.max(modelTop - anchorY, 0) + Rules.LabelGap
end

-- R3: one green main button. LEAP is the blue button today; it becomes grey like HOME, CHOMP stays the one green button.
function Rules.leapColour(current: Color3, blue: Color3, grey: Color3): Color3
    return if current == blue then grey else current
end

return Rules
