--!strict
-- BD-1120 (docs/202 R5): the rarity WORD in its colour, everywhere a rarity is named. ONE helper:
--   RarityWord(tier)  ->  word, colour        e.g. RarityWord(5) -> "Legendary", gold
-- tier is a rank 1..6 (Config.SpeciesRarityNames) or a name ("Rare"). The colour is NOT stored here: it is Theme.RarityColors (docs/114 s5.2), read when asked,
-- so the palette has one owner (tools/verify_rarity_words.py fails on a colour literal in this file).
-- Text that mixes a rarity word with other words ("Rare . 12% of eggs", "Best: Legendary Compy") goes through RarityWord.paint / RarityWord.set, which colour every whole
-- tier word and leave the rest alone (RichText). A rarity is never shown by colour alone: the word stays (docs/202 4.1 rule 5).
-- A chip that is FILLED with the tier colour (white word on it) already shows both; those places are listed in tools/rarity_words_allow.json.
local RarityWord = {}

RarityWord.Names = {"Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"}

local function palette(): any
    return (require(script.Parent.UITheme) :: any).RarityColors -- the one colour source
end

-- rank 1..6 of a tier given as a rank or a name (any case); nil when it is neither.
function RarityWord.index(tier: any): number?
    if type(tier) == "number" then
        local rank = math.floor(tier)
        if rank >= 1 and rank <= #RarityWord.Names then return rank end
        return nil
    end
    if type(tier) == "string" then
        local lower = string.lower(tier)
        for i, name in RarityWord.Names do
            if string.lower(name) == lower then return i end
        end
    end
    return nil
end

-- The word and its colour. An unknown tier answers Common (never an error on a screen).
function RarityWord.get(tier: any): (string, Color3)
    local rank = RarityWord.index(tier) or 1
    return RarityWord.Names[rank], (palette())[rank]
end

local function byte(v: number): number
    return math.clamp(math.floor(v * 255 + 0.5), 0, 255)
end

function RarityWord.hex(tier: any): string
    local _, colour = RarityWord.get(tier)
    return string.format("#%02X%02X%02X", byte(colour.R), byte(colour.G), byte(colour.B))
end

-- RichText for the one word: <font color="#RRGGBB">Legendary</font>
function RarityWord.rich(tier: any): string
    local word = RarityWord.get(tier)
    return string.format('<font color="%s">%s</font>', RarityWord.hex(tier), word)
end

local function escape(text: string): string
    return (string.gsub(string.gsub(string.gsub(string.gsub(string.gsub(text, "&", "&amp;"), "<", "&lt;"), ">", "&gt;"), '"', "&quot;"), "'", "&apos;"))
end

-- Does this text name a rarity (a whole word: "Rarer" and "Uncommonly" do not count)?
function RarityWord.has(text: string): boolean
    for _, name in RarityWord.Names do
        if string.find(text, "%f[%a]" .. name .. "%f[%A]") then return true end
    end
    return false
end

-- Plain text -> RichText with every whole tier word in its colour. The rest of the text is escaped, so a "<" in a name can never become markup.
-- Call it on PLAIN text only (painting painted text would nest tags).
function RarityWord.paint(text: string): string
    local out, i, n = {}, 1, #text
    while i <= n do
        local best: string? = nil
        for _, name in RarityWord.Names do -- the longest name that starts here as a whole word wins ("Uncommon" is one word, never "Common")
            if string.sub(text, i, i + #name - 1) == name then
                local before = if i > 1 then string.sub(text, i - 1, i - 1) else ""
                local after = string.sub(text, i + #name, i + #name)
                if not string.find(before, "^%a$") and not string.find(after, "^%a$") then best = name end
            end
        end
        if best then
            table.insert(out, RarityWord.rich(best))
            i += #best
        else
            table.insert(out, escape(string.sub(text, i, i)))
            i += 1
        end
    end
    return table.concat(out)
end

-- Put plain text on a label: with a tier word in it the label turns RichText and the word is coloured; without one the label keeps plain text.
function RarityWord.set(label: TextLabel | TextButton, text: string)
    if RarityWord.has(text) then
        label.RichText = true
        label.Text = RarityWord.paint(text)
    else
        label.RichText = false
        label.Text = text
    end
end

-- The label already holds its plain text: colour the tier words in it (for a label built by a helper that takes plain text).
function RarityWord.paintLabel(label: TextLabel | TextButton)
    RarityWord.set(label, label.Text)
end

-- A label that holds ONLY the word (a tier line on a card): the word and its colour, no markup.
function RarityWord.apply(label: TextLabel | TextButton, tier: any)
    local word, colour = RarityWord.get(tier)
    label.RichText = false
    label.Text = word
    label.TextColor3 = colour
end

setmetatable(RarityWord, {__call = function(_, tier: any): (string, Color3) return RarityWord.get(tier) end})

return RarityWord
