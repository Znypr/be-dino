--!strict
-- BD-1288 slice 1 (owner OK 2026-11-22, docs/evidence/2026-11-22-hatch-storyboard/storyboard-1-normal-flow.jpg): the numbers and words of the
-- hatch on the storyboard, as plain functions. No engine call, no clock, no RNG: tools/verify_hatch_storyboard.py runs this file with the
-- pinned Luau runtime. Used only while Config.HatchStoryboardEnabled (and HatchStageEnabled) are on: src/client/HatchStoryboard.luau draws,
-- src/shared/HatchTimeline.luau takes the paint plan and the tap wait from here. Presentation only: no odds, save or server value.
local R = {}

R.MinText = 19 -- every word on the storyboard stage is at least 19 px on screen (phones included)

-- Panel 1: the egg is the star, about 40 % of the screen height (critique #1: 35-45 %), on a glowing pedestal, under a kit bar.
R.EggShare = {min = .35, max = .45, want = .42}
R.EggCentreY = .5 -- the egg's centre, as a share of the screen height (under the bar, over the TAP)
R.FlatEggH = 248 -- design px of the flat egg at zoom 1 (HatchEggSize.flat().h: (383 - 107) * 460 / 512)
R.EggArtFill = .66 -- PROVISIONAL (Studio, docs/evidence/2026-11-22-hatch-slice1): share of a 256 px paint flipbook cell the egg fills
-- The multiplier on the egg's own zoom that makes an egg drawn `eggScreenH` px tall come out at `want` of the screen.
function R.eggBoost(eggScreenH: number, screenH: number): number
    if not (eggScreenH > 0 and screenH > 0) then return 1 end
    return math.clamp(screenH * R.EggShare.want / eggScreenH, .5, 3)
end
-- The side of the paint flipbook square so its egg is `want` of the screen tall.
function R.flipbookSide(screenH: number): number
    return screenH * R.EggShare.want / R.EggArtFill
end

-- The pace of storyboard 1 (critique #3 and #4): the pail splash names the colour and holds it about 0.9 s, the can splash names the
-- pattern and holds it about 0.9 s, then a 0.7 s crack build-up before the burst. Seconds from the start of the build-up clock.
-- Same fields as HatchTimeline.Paint; only the right bucket starts later so each name stays up long enough to read.
R.Paint = {leftStart = .35, rightStart = 1.25, window = .75, impact = .6, wash = .35, patternDelay = .05, patternWash = .4}
R.Hold = {colour = .9, pattern = .9}
R.BuildUp = .7
function R.plan()
    local p = R.Paint
    local leftImpact = p.leftStart + p.window * p.impact
    local rightImpact = p.rightStart + p.window * p.impact
    local buildUpAt = rightImpact + R.Hold.pattern
    return {leftImpact = leftImpact, rightImpact = rightImpact, buildUpAt = buildUpAt, build = buildUpAt + R.BuildUp,
        colourHold = rightImpact - leftImpact, patternHold = R.Hold.pattern, buildUp = R.BuildUp}
end
-- The egg waits for the TAP. A player who never taps still gets the egg after this many seconds (a batch never stalls).
R.TapWaitMax = 10

-- Words (kid words only: names and rarity words, never numbers or timers).
R.Words = {tap = "TAP!", next = "NEXT", best = "BEST FIND!", plain = "PLAIN", new = "NEW!"}
function R.colourWord(name: string?): string
    return string.upper(name or "")
end
function R.patternWord(name: string?, plain: boolean?): string
    if plain or name == nil or name == "" or name == "Plain" or name == "No pattern" then return R.Words.plain end
    return string.upper(name)
end
function R.tierWord(tierName: string?): string
    return string.upper(tierName or "Common")
end
-- "Egg 2 of 5" -> 2, 5 (nil, nil for anything else: one egg has no counter)
function R.counter(text: string?): (number?, number?)
    if type(text) ~= "string" then return nil, nil end
    local i, n = string.match(text, "(%d+)%s+of%s+(%d+)")
    if not i then return nil, nil end
    return tonumber(i), tonumber(n)
end

-- The top bar (storyboard: purple striped kit header across the top, a cream chip in the middle).
function R.topBar(w: number, h: number)
    local barH = math.clamp(math.floor(h * .13 + .5), 48, 110)
    local chipH = math.max(32, math.floor(barH * .66 + .5))
    local text = math.max(R.MinText, math.floor(chipH * .6 + .5))
    return {h = barH, chipW = math.max(150, math.floor(text * 7.4 + .5)), chipH = chipH, text = text, titleText = math.max(R.MinText + 5, math.floor(barH * .62 + .5))}
end

-- The big name plate of a splash (panel 2 / 3): right of the egg, the word in white outlined FredokaOne, the rarity chip under it.
-- FredokaOne capitals are about .68 em wide; the plate leaves half an em on each side.
function R.wordWidth(word: string, size: number): number
    return #word * size * .68
end
function R.label(w: number, h: number, eggCx: number, eggCy: number, eggH: number, word: string)
    local margin = 16
    local left = eggCx + eggH * .42 + math.max(12, eggH * .08)
    -- big (storyboard: about 12 % of the screen), but never wider than the room right of the egg
    local size = math.clamp(math.floor(h * .12 + .5), 30, 120)
    size = math.max(30, math.min(size, math.floor((w - margin - left) / (#word * .68 * 1.1 + 1.6))))
    local plateH = math.floor(size * 1.5 + .5)
    local plateW = math.floor(math.max(plateH * 2.4, R.wordWidth(word, size) * 1.1 + size * 1.6) + .5) -- room for the 3 px outline and the kit's rounded caps
    local chipH = math.max(30, math.floor(size * .78 + .5))
    local chipText = math.max(R.MinText, math.floor(chipH * .62 + .5))
    local chipW = math.floor(math.max(plateW * .8, R.wordWidth("UNCOMMON", chipText) + chipText) + .5)
    if left + plateW > w - margin then left = math.max(margin, w - margin - plateW) end
    local cx = left + plateW / 2
    local cy = eggCy - (plateH + 8 + chipH) / 2 + plateH / 2
    return {plate = {cx = cx, cy = cy, w = plateW, h = plateH, text = size}, chip = {cx = cx, cy = cy + plateH / 2 + 8 + chipH / 2, w = chipW, h = chipH, text = chipText}}
end

-- Panel 1: the TAP button under the egg, overlapping the pedestal (storyboard: big green kit button).
function R.tapButton(w: number, h: number, eggCy: number, eggH: number)
    local bh = math.clamp(math.floor(h * .15 + .5), 48, 120)
    local text = math.max(R.MinText + 5, math.floor(bh * .55 + .5))
    local cy = math.min(h - bh / 2 - 12, eggCy + eggH * .5 + bh * .55)
    return {cx = w / 2, cy = cy, w = math.floor(bh * 3.4 + .5), h = bh, text = text}
end
-- The glowing pedestal the egg stands on (the reveal's pedestal picture, 429 x 212).
function R.eggPedestal(w: number, h: number, eggCy: number, eggH: number)
    local pw = eggH * 1.25
    return {cx = w / 2, cy = eggCy + eggH * .46, w = pw, h = pw * 212 / 429}
end

-- Panel 4: the build-up rays take the rarity colour (rank 1..6); Common keeps a warm white. Legendary and Mythic keep their own gold build-up
-- (HatchStage.buildUp, later slices). `glow` = how far the glow grows and how bright it gets by the burst.
function R.buildUpLook(rank: number, reduceMotion: boolean)
    local r = math.clamp(math.floor(rank), 1, 6)
    return {lerpWhite = if r <= 1 then .7 else .2, raysTo = if r <= 1 then .35 else .12, glowGrow = if reduceMotion then 1 else 1.35,
        glowTo = .08, shake = not reduceMotion, own = r < 5}
end

-- Panel 5: the reveal stack, in shares of the screen height (the ribbon banner sits at the very top). The colour + pattern chips get their own
-- row between the name plate and NEXT. The dino view is 44 % of the screen tall (critique #1: 40-50 %), 48 % for Legendary and up.
R.Reveal = {dinoY = .38, dinoYBig = .37, dinoH = .48, dinoHBig = .5, pedestalY = .6, plateY = .685, chipsY = .79, nextY = .9}
R.NextScale = 1.25 -- the reveal's NEXT is a big kit button (storyboard panel 5)
function R.revealChips(w: number, h: number)
    local ch = math.clamp(math.floor(h * .05 + .5), 32, 46)
    local text = math.max(R.MinText, math.floor(ch * .58 + .5))
    return {h = ch, text = text, swatch = math.floor(ch * .62 + .5), gap = 10, y = h * R.Reveal.chipsY}
end
function R.chipWidth(word: string, text: number, swatch: number): number
    return math.floor(swatch + 8 + #word * text * .56 + 22 + .5)
end
-- The vertical stack on a screen: {name = {top, bottom}} with the same sizes HatchStage.reveal uses (plate and NEXT scale with fitY).
function R.revealStack(w: number, h: number)
    local fitY = math.min(1, h / 793)
    local plateW = math.min(w * .2, 300 * fitY)
    local plateH = plateW * 137 / 439
    local chips = R.revealChips(w, h)
    local nextH = 66 * fitY * R.NextScale
    local L = R.Reveal
    local dinoBottom = h * L.dinoY + h * L.dinoH / 2
    return {
        dino = {top = h * L.dinoY - h * L.dinoH / 2, bottom = dinoBottom},
        plate = {top = h * L.plateY - plateH / 2, bottom = h * L.plateY + plateH / 2},
        chips = {top = chips.y - chips.h / 2, bottom = chips.y + chips.h / 2},
        next = {top = h * L.nextY - nextH / 2, bottom = h * L.nextY + nextH / 2},
    }
end
-- NEW! when the colour / pattern / mutation is new (the server's LastChestNewJson) or the species was not in the collection before the batch.
function R.isNew(newFind: boolean?, newSpecies: boolean?): boolean
    return newFind == true or newSpecies == true
end

-- Panel 6: the best find of a batch = the highest rarity (a tie: the first one hatched). entries = {{rarity = n}, ...}; 0 when empty.
function R.best(entries: {any}): number
    local best, rank = 0, -1
    for i, e in entries do
        local r = if type(e.rarity) == "number" then e.rarity else 0
        if r > rank then best, rank = i, r end
    end
    return best
end
-- The summary shows a BEST FIND! only for a batch of 2 or more eggs (one egg already had its own reveal).
function R.wantsSummary(total: number?): boolean
    return type(total) == "number" and total >= 2
end
-- Layout: the best dino big on the left, the others as kit cards (256 x 320 -> w = .8 h) on the right, PLAY AGAIN / HOME at the bottom.
-- At most `maxCards` cards fit; the rest is one "+3" card. Cards never go under CardMinW px wide (their name stays >= 19 px).
R.CardMinW = 128
function R.summary(w: number, h: number, others: number)
    local bar = R.topBar(w, h)
    local buttonsY = h * .885
    local top, bottom = bar.h + h * .05, h * .79
    local areaL, areaR = w * .54, w - 16
    local gap = 10
    local minW = R.CardMinW
    local cols = math.max(1, math.min(3, math.floor((areaR - areaL + gap) / (minW + gap))))
    local rowsFit = math.max(1, math.floor((bottom - top + gap) / (minW / .8 + gap)))
    local maxCards = math.min(6, cols * rowsFit)
    local shown = math.min(others, maxCards)
    local more = others - shown
    if more > 0 then shown -= 1 more += 1 end -- the last cell becomes the "+N" card
    local cells = shown + (if more > 0 then 1 else 0)
    local useCols = math.max(1, math.min(cols, cells))
    local rows = math.max(1, math.ceil(cells / useCols))
    local cardW = math.min((areaR - areaL - (useCols - 1) * gap) / useCols, ((bottom - top - (rows - 1) * gap) / rows) * .8, h * .3 * .8)
    cardW = math.max(minW, cardW)
    local cardH = cardW / .8
    local gridW, gridH = useCols * cardW + (useCols - 1) * gap, rows * cardH + (rows - 1) * gap
    local x0, y0 = (areaL + areaR) / 2 - gridW / 2, (top + bottom) / 2 - gridH / 2
    local cards = {}
    for i = 1, cells do
        local c, r = (i - 1) % useCols, math.floor((i - 1) / useCols)
        table.insert(cards, {cx = x0 + c * (cardW + gap) + cardW / 2, cy = y0 + r * (cardH + gap) + cardH / 2, w = cardW, h = cardH})
    end
    local bigH = math.min(h * .46, bottom - top - h * .12)
    local nameText = math.max(R.MinText, math.floor(cardW * .17 + .5))
    return {bar = bar, big = {cx = w * .29, cy = (top + bottom) / 2 + h * .02, h = bigH}, cards = cards, shown = shown, more = more,
        buttonsY = buttonsY, cardText = nameText, chipText = R.MinText}
end

-- Inside a summary card, bottom up: the rarity chip, the name, the dino in the space left (never under each other).
function R.cardStack(w: number, h: number, text: number, chipText: number)
    local pad = math.max(5, math.floor(h * .04 + .5))
    local chipH = chipText + 10
    local chipCy = h - pad - chipH / 2
    local nameH = text + 6
    local nameCy = chipCy - chipH / 2 - 3 - nameH / 2
    local dinoTop, dinoBottom = pad, nameCy - nameH / 2 - 2
    return {chipCy = chipCy, chipH = chipH, nameCy = nameCy, nameH = nameH, dinoCy = (dinoTop + dinoBottom) / 2, dinoH = math.max(0, dinoBottom - dinoTop)}
end

return R
