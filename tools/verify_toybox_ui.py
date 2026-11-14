#!/usr/bin/env python3
"""BD-1177 (docs/228 board 1, docs/230): the "Toybox" UI skin behind Config.ToyboxUIEnabled.

What is checked, with the pinned Luau runtime and the REAL src/shared/ToyboxKit.luau, ToyboxSkin.luau, UITheme.luau, TextStyle.luau and
AssetSlots.luau (an engine mock stands in for Roblox; nothing is drawn):
  1. the flag: false in Config and the default profile, ON in the playtest profile, in the rehearsal list; UITheme loads ToyboxSkin only
     behind the flag; ModalCompact, FusionMenu and the button path ask Theme.Toybox; Bootstrap only hands the screen name to ModalCompact;
     no server file knows the feature; ToyboxKit touches no engine service;
  2. flag off = today's look: the window and the buttons are built instance for instance, property for property as by the same files
     with every Toybox line removed, and ToyboxSkin is never required;
  3. the kit numbers: every place gets its header colour (amber shop, green potions, blue dinos, purple fusion, cream eggs, dark
     settings), every screen name the client opens has a place and none uses the red header; the nearest gloss button for each Theme
     colour; text outline 3 px, 4 px from 28 px text; text never under 14 px; the X never under 48 px on screen;
  4. the pictures (Pillow): every file of resources/ui/v2/toybox/final is in the kit with its real size and nothing else is in the
     folder; every 9-slice rect keeps the rounded corners out of the stretching centre, and the centre really is stretchable (no shine
     stripe of a header and no stud of a card inside it; a header never stretches up or down);
  5. the skin with bound ids (engine mock): a button gets the gloss picture of its colour with the kit's slice rect, its word moves to
     a label that follows text, size (floor 14 px), colour and dimming; a colour change swaps the picture; the window gets frame, tiled
     studs, the header of each screen's place, a title drop and a square X of at least 48 px on screen; the Fusion Menu stays purple;
  6. the empty-id fallback: with no id bound (today's state) the flag adds no picture and hides nothing; a half-bound group is skipped;
     an invented-looking id is refused; the 23 slots exist in AssetSlots, empty or valid;
  7. mutants put each defect back and the checks must fail.
NOT Studio evidence: how the skin looks in the game (desktop, phone, 516x481, 1280x720) is unverified, and the ids are not bound yet.
Usage: python tools/verify_toybox_ui.py --runner luau.exe [--no-mutants]
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
KIT = 'src/shared/ToyboxKit.luau'
SKIN = 'src/shared/ToyboxSkin.luau'
THEME = 'src/shared/UITheme.luau'
STYLE = 'src/shared/TextStyle.luau'
SLOTS = 'src/shared/AssetSlots.luau'
MOTION = 'src/shared/UIMotion.luau'
COMPACT = 'src/client/ModalCompact.luau'
FUSION = 'src/client/FusionMenu.luau'
BOOT = 'src/client/Bootstrap.client.luau'
CONFIG = 'src/shared/Config.luau'
PROFILES = 'tools/release_profiles.py'
ART = 'resources/ui/v2/toybox/final'
# BD-1178 (docs/231): the Crystal Shop in the Toybox look reads the kit through its own verifier, tools/verify_toybox_shop.py
CRYSTAL_SHOP = ('src/shared/ToyboxShop.luau', 'src/client/ShopToyboxCard.luau', 'src/client/ShopCards.luau', 'src/client/ShopScreens.luau')

# The hook lines. Removing them gives "today's files"; check 2 compares the flag-off build against that.
THEME_HOOKS = [
    'Theme.Toybox = if (Config :: any).ToyboxUIEnabled == true then require(script.Parent.ToyboxSkin) else nil\n',
    'if Theme.Toybox then Theme.TextStyle.SkinThickness = Theme.Toybox.Kit.stroke end\n',
    '        if Theme.Toybox then Theme.Toybox.button(object, border) end -- BD-1177: the gloss button picture\n',
]
STYLE_HOOKS = [
    'TextStyle.SkinThickness = nil :: ((textSize: number) -> number)?\n',
    '    if TextStyle.SkinThickness then stroke.Thickness = TextStyle.SkinThickness(label.TextSize) end -- BD-1177\n',
    '    if TextStyle.SkinThickness and stroke.Parent == label then stroke.Thickness = TextStyle.SkinThickness(label.TextSize) end -- BD-1177\n',
]
COMPACT_PLACE = '    if screen and Theme.Toybox then Theme.Toybox.place(screen) end\n'
COMPACT_WINDOW = '    if Theme.Toybox then Theme.Toybox.window({panel = context.panel, header = context.header, heading = context.heading, closeButton = context.closeButton, scale = context.scale}) end -- BD-1177\n'
FUSION_WINDOW = '    if Theme.Toybox then Theme.Toybox.window({panel = frame, header = header, heading = titleLabel, closeButton = closeX, place = "fusion"}) end -- BD-1177: purple header, stud body, red gloss X\n'
BOOT_HOOK = '    require(script.Parent.ModalCompact).layout(name)\n'

# The owner's six places (docs/228) and one screen of each: independent of the kit's own table.
OWNER_PLACES = {'auras': 'amber', 'potions': 'green', 'collection': 'blue', 'fusion': 'purple', 'eggs': 'cream', 'settings': 'dark'}
SIZES = {'header': (512, 128), 'button': (256, 112), 'card': (256, 320), 'close': (128, 128), 'panel': (256, 256), 'studs': (256, 256)}


def reader(mutant=None):
    def read(path):
        text = (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')
        if mutant and mutant[0] == path:
            assert text.count(mutant[1]) == 1, 'mutant anchor must match once in %s: %r' % (path, mutant[1])
            text = text.replace(mutant[1], mutant[2])
        return text
    return read


def strip(text, hooks):
    for hook in hooks:
        assert text.count(hook) == 1, 'hook line must be there once: %r' % hook
        text = text.replace(hook, '')
    return text


def code_only(text):
    return '\n'.join(line.split('--', 1)[0] for line in text.splitlines())


def screens(read):
    """Every screen name the client can open in the menu window."""
    names = set()
    for path in ('src/client/ShopScreens.luau', 'src/client/SmallScreens.luau', 'src/client/DinoIndexScreens.luau'):
        table = re.search(r'\.names = \{(.*?)\}', read(path), re.S)
        assert table, 'screen name table in ' + path
        names.update(re.findall(r'(\w+) = true', table.group(1)))
    boot = read(BOOT)
    body = boot[boot.index('render=function(name: string)'):]
    names.update(re.findall(r'^    (?:if|elseif) name=="(\w+)" then', body, re.M))
    for file in sorted((ROOT / 'src/client').glob('*.luau')):
        names.update(re.findall(r'\bopen\("(\w+)"\)', file.read_text(encoding='utf-8')))
    return sorted(names)


def static_checks(read):
    cfg = read(CONFIG)
    assert len(re.findall(r'^    ToyboxUIEnabled = false,$', cfg, re.M)) == 1, 'ToyboxUIEnabled ships false in Config (once)'
    profiles = read(PROFILES)
    assert '_flag_off("ToyboxUIEnabled",' in profiles, 'the default profile pins the flag off'
    assert 'Rule("ToyboxUIEnabled", "set", True,' in profiles, 'the playtest profile sets it on (owner decision 2026-11-13)'
    assert '("ToyboxUIEnabled", "BD-1177' in profiles, 'the rehearsal list has it'
    assert '"ToyboxUIEnabled"' in read('tools/release_playtest.py'), 'the playtest manifest records it'
    kit = code_only(read(KIT))
    for needle in ('game', 'Instance', 'TweenService', 'task.', 'os.', 'tick(', 'math.random', 'require(', 'Enum.', 'Color3', 'UDim'):
        assert needle not in kit, 'ToyboxKit is pure (no engine, clock or RNG): ' + needle
    skin = code_only(read(SKIN))
    for needle in ('TweenService', 'FireServer', 'InvokeServer', 'task.', 'Config', 'UIGradient', 'Instance.new("Frame")'):
        assert needle not in skin, 'ToyboxSkin only places pictures and labels: ' + needle
    made = set(re.findall(r'Instance\.new\("(\w+)"\)', skin))
    assert made == {'ImageLabel', 'TextLabel', 'UIStroke', 'UICorner', 'UITextSizeConstraint'}, 'ToyboxSkin draws nothing itself (no code-built art): %s' % sorted(made)
    theme = read(THEME)
    for hook in THEME_HOOKS:
        assert theme.count(hook) == 1, 'UITheme hook: %r' % hook
    assert theme.count('ToyboxSkin') == 2 and theme.count('require(script.Parent.ToyboxSkin)') == 1, 'UITheme requires ToyboxSkin once, behind the flag'
    assert code_only(theme).count('Toybox') == 7, 'UITheme mentions Toybox only in its three hook lines'
    style = read(STYLE)
    for hook in STYLE_HOOKS:
        assert style.count(hook) == 1, 'TextStyle hook: %r' % hook
    assert code_only(style).count('SkinThickness') == 5 and 'require(' not in code_only(style), 'TextStyle only reads its own SkinThickness (nil by default)'
    compact = read(COMPACT)
    assert compact.count('function M.layout(screen: string?)\n    local c = ctx\n    if not c then return end\n' + COMPACT_PLACE) == 1, 'ModalCompact.layout recolours the header only when it is given a screen name'
    assert compact.count(COMPACT_WINDOW + '    M.layout()\n') == 1, 'ModalCompact.attach skins the menu window (flag on only)'
    assert code_only(compact).count('Toybox') == 4, 'ModalCompact mentions Toybox only in its two hook lines'
    fusion = read(FUSION)
    assert fusion.count(FUSION_WINDOW) == 1 and code_only(fusion).count('Toybox') == 2, 'the Fusion Menu window asks Theme.Toybox once, with the place "fusion"'
    boot = read(BOOT)
    assert boot.count(BOOT_HOOK) == 1 and boot.count('ModalCompact).layout(') == 2, 'open(name) hands the screen name to ModalCompact.layout'
    assert boot.index('    body:ClearAllChildren()\n' + BOOT_HOOK) < boot.index('    render(name)\n'), 'the header is recoloured before the screen is drawn'
    assert 'Toybox' not in boot, 'Bootstrap itself knows nothing of the skin (size ceiling)'
    for file in (ROOT / 'src').rglob('*.luau'):
        rel = file.relative_to(ROOT).as_posix()
        text = file.read_text(encoding='utf-8')
        if rel.startswith('src/server'):
            for word in ('Toybox', 'toybox_'):
                assert word not in text, 'no server change: %s in %s' % (word, rel)
        elif rel not in (KIT, SKIN, THEME, COMPACT, FUSION, CONFIG, SLOTS, STYLE) + CRYSTAL_SHOP and 'Toybox' in text:
            raise AssertionError('only UITheme, ModalCompact, FusionMenu and the Crystal Shop files reach the skin: ' + rel)
    slots = read(SLOTS)
    found = re.findall(r'^    (toybox_\w+) = "([^"]*)",$', slots, re.M)
    assert len(found) == 23 and len({name for name, _ in found}) == 23, 'AssetSlots has the 23 toybox slots (found %d)' % len(found)
    for name, value in found:
        assert value == '' or re.fullmatch(r'rbxassetid://[1-9][0-9]{4,18}', value), 'slot %s holds an empty or a real id, never an invented one: %r' % (name, value)
    workflow = (ROOT / '.github/workflows/build-generated-place.yml').read_text(encoding='utf-8')
    assert 'python tools/verify_toybox_ui.py --runner /tmp/luau/luau' in workflow, 'CI runs this check'


def wrap(source):
    return 'function()\n' + source + '\nend'


def run(runner, source, name):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / (name + '.luau')
        path.write_text(source, encoding='utf-8')
        done = subprocess.run([runner, str(path)], capture_output=True, text=True, timeout=120)
    return done.returncode == 0, (done.stdout + done.stderr)


PURE = r'''
local Kit = (__KIT__)()
local function eq(a, b, what) assert(a == b, what .. ": got " .. tostring(a) .. ", want " .. tostring(b)) end
-- ---- floors and text
eq(Kit.MinText, 14, "text floor") eq(Kit.MinClose, 48, "X floor")
eq(Kit.stroke(14), 3, "small text outline") eq(Kit.stroke(27), 3, "27 px outline") eq(Kit.stroke(28), 4, "28 px outline") eq(Kit.stroke(60), 4, "big text outline")
eq(Kit.stroke(0 / 0), 3, "a broken size still gets an outline")
for _, size in {1, 8, 13, 13.9} do eq(Kit.textSize(size), 14, "text under the floor") end
eq(Kit.textSize(14), 14, "floor itself") eq(Kit.textSize(23), 23, "bigger text keeps its size") eq(Kit.textSize(0 / 0), 14, "a broken size")
for _, size in {1, 14, 20, 28, 40, 80} do local s = Kit.stroke(size) assert(s >= 3 and s <= 4, "outline is 3..4 px") end
assert(Kit.DropPixels >= 2 and Kit.DropPixels <= 4, "a small drop")
-- ---- the X: a square of the button's short side, never under 48 px on screen
eq(Kit.closeSide(80, 62, 1), 62, "desktop X") eq(Kit.closeSide(48, 37, 0.6), 80, "a 37 px X grows to 48 px on screen (80 design px at 60%)")
for _, case in {{80, 62, 1}, {48, 37, 0.6}, {30, 30, 0.8}, {0, 0, 0.56}, {200, 90, 1.4}, {46, 46, 1}} do
    local side = Kit.closeSide(case[1], case[2], case[3])
    assert(side * case[3] >= 48 - 1e-6, "X at least 48 px on screen") assert(side * case[3] <= math.max(48, math.min(case[1], case[2])) + 1e-6, "X no bigger than the button's short side")
end
eq(Kit.closeSide(60, 60, 0), 60, "a broken scale counts as 1")
-- ---- places
__PLACES__
for place, colour in Kit.PlaceHeader do
    assert(colour ~= "red", "red is for the X only") assert(Kit.Assets["toybox_header_" .. colour] ~= nil, "a header picture for " .. place)
end
local count = 0 for _ in Kit.PlaceHeader do count += 1 end eq(count, 6, "six places")
local seen = {} for _, colour in Kit.PlaceHeader do assert(not seen[colour], "one colour per place") seen[colour] = true end
eq(Kit.placeSlot("fusion"), "toybox_header_purple", "the Fusion Menu window") eq(Kit.placeSlot("nonsense"), "toybox_header_blue", "an unknown place = blue")
eq(Kit.headerSlot(nil), "toybox_header_blue", "no screen = blue") eq(Kit.headerSlot("somethingNew"), "toybox_header_blue", "an unknown screen = blue (today's header colour)")
for screen, place in Kit.ScreenPlace do assert(Kit.PlaceHeader[place] ~= nil, "screen " .. screen .. " names a real place") end
-- ---- buttons: each Theme colour becomes its own gloss button
for key, rgb in {green = {93, 237, 31}, gold = {255, 210, 43}, blue = {46, 206, 255}, purple = {194, 86, 255}, red = {247, 57, 48}, dark = {61, 58, 73}, grey = {128, 142, 158}} do
    eq(Kit.buttonKey(rgb[1], rgb[2], rgb[3]), key, "button for " .. key) eq(Kit.buttonSlot(rgb[1], rgb[2], rgb[3]), "toybox_button_" .. key, "slot for " .. key)
end
eq(Kit.buttonKey(42, 40, 53), "dark", "the panel colour is a dark button") eq(Kit.buttonKey(0, 0, 0), "dark", "black") eq(Kit.buttonKey(255, 255, 255), "grey", "white")
eq(Kit.buttonKey(70, 200, 40), "green", "a darker green") eq(Kit.buttonKey(230, 60, 60), "red", "another red")
-- ---- ids: empty or malformed = nil, a group needs every id
local images = {}
for slot in Kit.Assets do images[slot] = "" end
for _, group in Kit.Groups do assert(not Kit.ready(images, group), "nothing bound: " .. group .. " is not ready") end
assert(not Kit.ready(images, "nonsense") and not Kit.ready({}, "button"), "an unknown group or a missing table is never ready")
eq(Kit.image(images, "toybox_close"), nil, "an empty id is no id")
for _, bad in {"123456", "rbxassetid://", "rbxassetid://abc", "http://x/1", 123456} do images.toybox_close = bad eq(Kit.image(images, "toybox_close"), nil, "a malformed id is no id") end
images.toybox_close = "rbxassetid://123456" eq(Kit.image(images, "toybox_close"), "rbxassetid://123456", "a real id") assert(Kit.ready(images, "close"), "close ready")
eq(Kit.image({not_a_slot = "rbxassetid://123456"}, "not_a_slot"), nil, "only kit slots")
local buttons = Kit.slots("button") eq(#buttons, 7, "seven buttons")
for index, slot in buttons do images[slot] = "rbxassetid://20000" .. index if index < 7 then assert(not Kit.ready(images, "button"), "six of seven is not ready") end end
assert(Kit.ready(images, "button") and not Kit.ready(images, "header") and not Kit.ready(images, "panel"), "groups are separate")
eq(#Kit.slots("header"), 7, "seven headers") eq(#Kit.slots("card"), 6, "six cards") eq(#Kit.slots("panel"), 2, "frame and studs")
local total = 0 for _, group in Kit.Groups do total += #Kit.slots(group) end
local assets = 0 for _ in Kit.Assets do assets += 1 end eq(total, 23, "23 slots in groups") eq(assets, 23, "23 pictures")
-- ---- slice scale
eq(Kit.sliceScale("toybox_header_amber", 852, 78), 78 / 128, "a header never stretches up or down") eq(Kit.sliceScale("toybox_header_blue", 500, 64), 0.5, "phone header")
eq(Kit.sliceScale("toybox_button_green", 200, 60), 0.5, "button at half size") eq(Kit.sliceScale("toybox_panel_frame", 860, 520), 0.5, "frame at half size")
assert(math.abs(Kit.sliceScale("toybox_button_green", 40, 20) - 20 / 44) < 1e-9, "a tiny button shrinks its caps to fit")
eq(Kit.sliceScale("toybox_close", 60, 60), 1, "the X is not sliced") eq(Kit.sliceScale("toybox_studs_tile", 60, 60), 1, "the tile is not sliced")
for slot, asset in Kit.Assets do
    local s = asset.slice
    print(string.format("ASSET %s %s %d %d %s %s", slot, asset.file, asset.w, asset.h, if s then string.format("%d,%d,%d,%d", s[1], s[2], s[3], s[4]) else "-", asset.fit or "-"))
end
print("FOLDER " .. Kit.Folder)
print("toybox kit ok")
'''

# An engine mock big enough for the real UITheme, TextStyle and ToyboxSkin: instances with children, property signals and a dump.
ENGINE = r'''
local function signal()
    local s = {handlers = {}}
    function s:Connect(f) table.insert(self.handlers, f) return {Disconnect = function() end} end
    function s:Once(f) table.insert(self.handlers, f) end
    function s:Fire(...) for _, h in table.clone(self.handlers) do h(...) end end
    return s
end
local function names(path)
    local cache = {}
    return setmetatable({}, {__index = function(_, k)
        if cache[k] == nil then cache[k] = names(path .. "." .. tostring(k)) end
        return cache[k]
    end, __tostring = function() return path end})
end
local Enum = names("Enum")
local UDim2 = {}
local udim2 = {
    __add = function(a, b) return UDim2.new(a.X.Scale + b.X.Scale, a.X.Offset + b.X.Offset, a.Y.Scale + b.Y.Scale, a.Y.Offset + b.Y.Offset) end,
    __eq = function(a, b) return a.X.Scale == b.X.Scale and a.X.Offset == b.X.Offset and a.Y.Scale == b.Y.Scale and a.Y.Offset == b.Y.Offset end,
    __tostring = function(a) return string.format("UDim2(%g,%g,%g,%g)", a.X.Scale, a.X.Offset, a.Y.Scale, a.Y.Offset) end,
}
function UDim2.new(xs, xo, ys, yo) return setmetatable({X = {Scale = xs or 0, Offset = xo or 0}, Y = {Scale = ys or 0, Offset = yo or 0}}, udim2) end
function UDim2.fromOffset(x, y) return UDim2.new(0, x, 0, y) end
function UDim2.fromScale(x, y) return UDim2.new(x, 0, y, 0) end
local plain = {__tostring = function(a) local out = {} for _, k in a.keys do table.insert(out, string.format("%g", a[k])) end return a.kind .. "(" .. table.concat(out, ",") .. ")" end,
    __eq = function(a, b) if a.kind ~= b.kind then return false end for _, k in a.keys do if a[k] ~= b[k] then return false end end return true end}
local function value(kind, keys, ...) local v = {kind = kind, keys = keys} for i, k in keys do v[k] = (select(i, ...)) or 0 end return setmetatable(v, plain) end
local UDim = {new = function(s, o) return value("UDim", {"Scale", "Offset"}, s, o) end}
local Vector2 = {new = function(x, y) return value("Vector2", {"X", "Y"}, x, y) end}
Vector2.zero = Vector2.new(0, 0)
local Rect = {new = function(a, b, c, d) return value("Rect", {"x0", "y0", "x1", "y1"}, a, b, c, d) end}
local Color3 = {new = function(r, g, b) return value("Color3", {"R", "G", "B"}, r, g, b) end}
function Color3.fromRGB(r, g, b) return Color3.new(r / 255, g / 255, b / 255) end
function Color3.fromHex(_h) return Color3.new(0, 0, 0) end
local ColorSequence = {new = function(...) return "ColorSequence" end}
local TweenInfo = {new = function(seconds) return {seconds = seconds} end}
local GUI = {Frame = true, TextLabel = true, TextButton = true, ImageLabel = true, ScrollingFrame = true}
local SIGNALS = {MouseEnter = true, MouseLeave = true, SelectionGained = true, SelectionLost = true, InputBegan = true, InputEnded = true,
    Destroying = true, Activated = true, ChildAdded = true, Changed = true}
local required = {}
local isInstance = setmetatable({}, {__mode = "k"})
local function instance(class)
    local props = {ClassName = class, Name = class}
    local attributes, signals, changed, children = {}, {}, {}, {}
    local self
    local methods = {
        IsA = function(_, c) return c == class or (c == "GuiObject" and GUI[class] == true) or c == "Instance" end,
        GetAttribute = function(_, name) return attributes[name] end,
        SetAttribute = function(_, name, v) attributes[name] = v end,
        GetChildren = function() return table.clone(children) end,
        FindFirstChild = function(_, name) for _, c in children do if c.Name == name then return c end end return nil end,
        FindFirstChildOfClass = function(_, c) for _, child in children do if child.ClassName == c then return child end end return nil end,
        GetPropertyChangedSignal = function(_, name) if not changed[name] then changed[name] = signal() end return changed[name] end,
        ClearAllChildren = function() table.clear(children) end,
    }
    self = setmetatable({}, {
        __index = function(_, k)
            if methods[k] then return methods[k] end
            if SIGNALS[k] then if not signals[k] then signals[k] = signal() end return signals[k] end
            if k == "__children" then return children end
            if k == "__attributes" then return attributes end
            if k == "__props" then return props end
            return props[k]
        end,
        __newindex = function(_, k, v)
            local old = props[k]
            props[k] = v
            if k == "Parent" then
                if old and old ~= v and type(old) == "table" and old.__children then local list = old.__children local at = table.find(list, self) if at then table.remove(list, at) end end
                if v and type(v) == "table" and v.__children then table.insert(v.__children, self) v.ChildAdded:Fire(self) end
                return
            end
            if old ~= v and changed[k] then changed[k]:Fire() end
        end,
    })
    isInstance[self] = true
    return self
end
local DEFAULTS = {
    GuiObject = {BackgroundTransparency = 0, Visible = true, ZIndex = 1, Rotation = 0},
    Text = {Text = "", TextSize = 8, TextTransparency = 0, TextStrokeTransparency = 1, TextScaled = false, TextWrapped = false, RichText = false, LineHeight = 1},
}
local Instance = {new = function(class)
    local i = instance(class)
    local p = i.__props
    if GUI[class] then
        for k, v in DEFAULTS.GuiObject do p[k] = v end
        p.Size, p.Position, p.AnchorPoint, p.AbsoluteSize = UDim2.new(0, 0, 0, 0), UDim2.new(0, 0, 0, 0), Vector2.new(0, 0), Vector2.new(0, 0)
        p.BackgroundColor3 = Color3.fromRGB(163, 162, 165)
    end
    if class == "TextLabel" or class == "TextButton" then for k, v in DEFAULTS.Text do p[k] = v end p.TextColor3 = Color3.new(0, 0, 0) end
    if class == "ImageLabel" then p.Image, p.ImageTransparency, p.SliceScale = "", 0, 1 end
    if class == "UIStroke" then p.Enabled, p.Thickness, p.Transparency = true, 1, 0 end
    if class == "UIScale" then p.Scale = 1 end
    if class == "NumberValue" then p.Value = 0 end
    if class == "UIPadding" then p.PaddingLeft, p.PaddingRight, p.PaddingTop, p.PaddingBottom = UDim.new(0, 0), UDim.new(0, 0), UDim.new(0, 0), UDim.new(0, 0) end
    if class == "UITextSizeConstraint" then p.MinTextSize, p.MaxTextSize = 1, 100 end
    return i
end}
local TweenService = {Create = function(_, target, info, goals)
    local tween = {Completed = signal()}
    function tween:Play() end
    function tween:Cancel() end
    return tween
end}
local task = {delay = function() end}
local game = {GetService = function(_, name) assert(name == "TweenService", "asked for " .. tostring(name)) return TweenService end}
local script = {Parent = setmetatable({}, {__index = function(_, k) return k end})}
local function show(v)
    if type(v) == "table" and isInstance[v] then return "<" .. v.ClassName .. ">" end
    if type(v) == "number" then return string.format("%g", v) end
    return tostring(v)
end
local function dump(node, indent, out)
    local keys = {}
    for k in node.__props do if k ~= "Parent" then table.insert(keys, k) end end
    table.sort(keys)
    local parts = {}
    for _, k in keys do table.insert(parts, k .. "=" .. show(node.__props[k])) end
    local attrs = {}
    for k, v in node.__attributes do table.insert(attrs, k .. "=" .. tostring(v)) end
    table.sort(attrs)
    table.insert(out, indent .. table.concat(parts, " ") .. (if #attrs > 0 then " @" .. table.concat(attrs, " @") else ""))
    for _, child in node.__children do dump(child, indent .. "  ", out) end
    return out
end
local function count(node, test)
    local n = if test(node) then 1 else 0
    for _, child in node.__children do n += count(child, test) end
    return n
end
'''

# Loads the real modules behind a require() like the game's, then builds what Bootstrap builds: the window and a few buttons.
SCENE = ENGINE + r'''
local FLAG, BOUND = __FLAG__, "__BOUND__"
local require -- the modules below ask this one, like the game's
local sources = {
    ToyboxKit = __KIT__,
    ToyboxSkin = __SKIN__,
    AssetSlots = __SLOTS__,
    TextStyle = __STYLE__,
    UIMotion = __MOTION__,
}
local loaded = {}
function require(key)
    if loaded[key] ~= nil then return loaded[key] end
    local module
    if key == "Config" then module = {ToyboxUIEnabled = FLAG, MotionPresetsEnabled = false}
    elseif sources[key] then
        required[key] = true
        module = sources[key]()
        if key == "AssetSlots" then
            local n = 0
            for name in module.Images do
                if string.sub(name, 1, 7) == "toybox_" then
                    n += 1
                    local group = string.match(name, "^toybox_(%a+)")
                    local bind = BOUND == "all" or (BOUND == "close" and name == "toybox_close") or (BOUND == "nobutton" and group ~= "button")
                        or (BOUND == "sixbuttons" and name ~= "toybox_button_dark" and group == "button") or (BOUND == "invented" and true)
                    module.Images[name] = if not bind then "" elseif BOUND == "invented" then "12345" .. n else "rbxassetid://9000" .. (100 + n)
                end
            end
            assert(n == 23, "23 toybox slots in AssetSlots, got " .. n)
        end
    else module = {} end
    loaded[key] = module
    return module
end
local Theme = (__THEME__)()
local Slots = require("AssetSlots")
local C = Theme.Colors
local function box(parent, w, h, color, z)
    local b = Instance.new("Frame")
    b.Size, b.BackgroundColor3, b.ZIndex, b.Parent = UDim2.fromOffset(w, h), color, z, parent
    Theme.decorate(b, 5)
    return b
end
local function button(parent, text, w, h, color, size)
    local b = Instance.new("TextButton")
    b.Size, b.BackgroundColor3 = UDim2.fromOffset(w, h), color
    b.Text, b.TextColor3, b.TextSize, b.ZIndex, b.Parent = text, C.text, size or 23, 3, parent
    Theme.decorate(b, 4)
    return b
end
local function window()
    local shade = Instance.new("TextButton")
    local panel = box(shade, 860, 520, C.panel, 21)
    Theme.texture(panel, 860, 520)
    local scale = Instance.new("UIScale")
    scale.Parent = panel
    local header = box(panel, 852, 78, C.blue, 22)
    Theme.texture(header, 852, 78)
    local heading = Instance.new("TextLabel")
    heading.Size, heading.Position, heading.TextSize, heading.Text, heading.TextColor3, heading.ZIndex = UDim2.fromOffset(730, 68), UDim2.fromOffset(22, 4), 40, "Dino Index", C.text, 23
    heading.Parent = header
    Theme.TextStyle.outlined(heading, "title")
    local body = Instance.new("Frame")
    body.ZIndex, body.Parent = 23, panel
    local closeButton = button(header, "X", 80, 76, C.red)
    closeButton.AbsoluteSize = Vector2.new(80, 62)
    return {shade = shade, panel = panel, header = header, heading = heading, closeButton = closeButton, scale = scale, body = body}
end
local w = window()
-- the hook of ModalCompact.attach, as written there
if Theme.Toybox then Theme.Toybox.window({panel = w.panel, header = w.header, heading = w.heading, closeButton = w.closeButton, scale = w.scale}) end
local buy = button(w.body, "Buy", 200, 60, C.accent, 10)
local card = Instance.new("TextLabel")
card.TextSize, card.Text, card.TextColor3, card.Parent = 16, "470", C.text, w.body
Theme.TextStyle.outlined(card, "card")
local big = Instance.new("TextLabel")
big.TextSize, big.Text, big.TextColor3, big.Parent = 30, "RARE!", C.text, w.body
Theme.TextStyle.apply(big)
local function isToybox(node) return node.ClassName == "ImageLabel" or string.sub(tostring(node.Name), 1, 6) == "Toybox" end
local function strokeOf(label) return label:FindFirstChildOfClass("UIStroke").Thickness end
for _, line in dump(w.shade, "", {}) do print("DUMP " .. line) end
__CHECKS__
print("scene ok: flag " .. tostring(FLAG) .. ", ids " .. BOUND)
'''

CHECK_OFF = r'''
assert(Theme.Toybox == nil and Theme.TextStyle.SkinThickness == nil, "flag off: no skin")
assert(not required.ToyboxSkin and not required.ToyboxKit, "flag off: ToyboxSkin and ToyboxKit are never required")
assert(count(w.shade, isToybox) == 0, "flag off: no picture, no Toybox instance")
assert(strokeOf(card) == 2 and strokeOf(big) == 3 and strokeOf(w.heading) == 3, "flag off: text outline 2..3 px as today")
'''

# Flag on, no id bound (today's state): only the text outline changes.
CHECK_EMPTY = r'''
assert(Theme.Toybox ~= nil and required.ToyboxSkin, "flag on: the skin is loaded")
assert(count(w.shade, isToybox) == 0, "no id bound: no picture and no Toybox instance anywhere")
assert(w.panel.BackgroundTransparency == 0 and w.header.BackgroundTransparency == 0 and buy.BackgroundTransparency == 0, "no id bound: nothing is hidden")
assert(w.panel:FindFirstChild("FossilTexture").Visible and w.header:FindFirstChild("FossilTexture").Visible, "no id bound: the old texture stays")
assert(buy.TextTransparency == 0 and buy:FindFirstChildOfClass("UIStroke").Enabled and w.closeButton.TextTransparency == 0, "no id bound: buttons keep their own word and edge")
assert(strokeOf(card) == 3 and strokeOf(big) == 4 and strokeOf(w.heading) == 4, "flag on: text outline 3 px, 4 px from 28 px text")
Theme.Toybox.place("auras") -- no header strip: must not error
'''

CHECK_PARTIAL = r'''
local Kit = Theme.Toybox.Kit
if BOUND == "close" then
    local face = w.closeButton:FindFirstChild("ToyboxFace")
    assert(face and face.Image == Slots.Images.toybox_close and count(w.shade, isToybox) == 3, "only the X id bound: only the X is skinned")
    assert(w.panel.BackgroundTransparency == 0 and w.header.BackgroundTransparency == 0 and buy:FindFirstChild("ToyboxFace") == nil, "the rest keeps today's look")
elseif BOUND == "sixbuttons" then
    assert(count(w.shade, isToybox) == 0, "six of seven button ids: no button is skinned, no half kit")
elseif BOUND == "nobutton" then
    assert(buy:FindFirstChild("ToyboxFace") == nil and buy.BackgroundTransparency == 0 and buy.TextTransparency == 0, "no button ids: buttons keep today's look")
    assert(w.panel:FindFirstChild("ToyboxFrame") and w.header:FindFirstChild("ToyboxHeader") and w.closeButton:FindFirstChild("ToyboxFace"), "the window groups are bound and used")
elseif BOUND == "invented" then
    assert(count(w.shade, isToybox) == 0, "ids that are not rbxassetid://N are refused: nothing is skinned")
end
'''

CHECK_BOUND = r'''
local Kit = Theme.Toybox.Kit
local ids = Slots.Images
local function rect(image, want) local r = image.SliceCenter return r.x0 == want[1] and r.y0 == want[2] and r.x1 == want[3] and r.y1 == want[4] end
-- ---- a button
local face, word, drop = buy:FindFirstChild("ToyboxFace"), buy:FindFirstChild("ToyboxText"), buy:FindFirstChild("ToyboxTextDrop")
assert(face and word and drop, "a decorated button gets the gloss picture, its word label and the drop")
assert(face.ClassName == "ImageLabel" and face.Image == ids.toybox_button_green and face.Image ~= "", "the green button picture")
assert(face.ScaleType == Enum.ScaleType.Slice and rect(face, {24, 20, 232, 88}) and face.SliceScale == 0.5, "button 9-slice: the measured rect at half size")
assert(face.Size == UDim2.fromScale(1, 1) and face.BackgroundTransparency == 1, "the picture fills the button")
assert(face.ZIndex < drop.ZIndex and drop.ZIndex < word.ZIndex and word.ZIndex < 1, "picture under drop under word, all under what the screen puts on the button")
assert(buy.BackgroundTransparency == 1 and buy.TextTransparency == 1 and buy.TextStrokeTransparency == 1, "the flat colour and the button's own word are hidden")
assert(buy:FindFirstChildOfClass("UIStroke").Enabled == false, "the old edge is off: the picture has its own")
assert(word.Text == "Buy" and drop.Text == "Buy" and word.TextTransparency == 0, "the word is on the label")
assert(word.TextSize == 14 and drop.TextSize == 14, "a 10 px word is raised to the 14 px floor")
assert(strokeOf(word) == 3 and strokeOf(drop) == 3, "3 px outline")
assert(drop.Position == UDim2.fromOffset(0, Kit.DropPixels) and tostring(drop.TextColor3) ~= tostring(word.TextColor3), "the drop is a dark copy under the word")
buy.Text = "Sold"
assert(word.Text == "Sold" and drop.Text == "Sold", "the label follows the button's Text")
buy.TextSize = 30
assert(word.TextSize == 30 and strokeOf(word) == 4 and strokeOf(drop) == 4, "30 px text: 4 px outline")
buy.TextTransparency = .25
assert(word.TextTransparency == .25 and drop.TextTransparency == .25 and buy.TextTransparency == 1, "a dimmed word dims the label; the button's own word stays hidden")
for key, color in {dark = C.card, red = C.red, gold = C.gold, blue = C.blue, purple = C.purple, grey = Theme.RarityColors[1], green = C.accent} do
    buy.BackgroundColor3 = color
    assert(face.Image == ids["toybox_button_" .. key], "a colour change swaps the picture: " .. key)
end
buy.Size = UDim2.fromOffset(40, 20)
assert(math.abs(face.SliceScale - 20 / 44) < 1e-9, "a tiny button shrinks the caps")
local padded = button(w.body, "Use", 200, 50, C.accent)
local pad = Instance.new("UIPadding") pad.PaddingLeft = UDim.new(0, 40) pad.Parent = padded
local paddedFace = padded:FindFirstChild("ToyboxFace")
assert(paddedFace.Position == UDim2.fromOffset(-40, 0) and paddedFace.Size == UDim2.new(1, 40, 1, 0), "a padding on the button does not shrink the picture")
local ghost = Instance.new("TextButton") ghost.BackgroundTransparency, ghost.Parent = 1, w.body
Theme.decorate(ghost, 4)
assert(ghost:FindFirstChild("ToyboxFace") == nil, "an invisible touch area gets no picture")
-- ---- the window
local frame, studs = w.panel:FindFirstChild("ToyboxFrame"), w.panel:FindFirstChild("ToyboxStuds")
assert(frame and frame.Image == ids.toybox_panel_frame and frame.ScaleType == Enum.ScaleType.Slice and rect(frame, {36, 36, 220, 220}) and frame.SliceScale == 0.5, "window frame: 9-slice")
assert(studs and studs.Image == ids.toybox_studs_tile and studs.ScaleType == Enum.ScaleType.Tile and studs.TileSize == UDim2.fromOffset(128, 128), "stud body: tiled")
assert(studs.Position == UDim2.fromOffset(5, 5) and studs.Size == UDim2.new(1, -10, 1, -12) and studs:FindFirstChildOfClass("UICorner") ~= nil, "the studs stay inside the frame edge")
assert(frame.ZIndex < studs.ZIndex and studs.ZIndex < 1, "frame under studs under the window content")
assert(w.panel.BackgroundTransparency == 1 and w.panel:FindFirstChild("FossilTexture").Visible == false and w.panel:FindFirstChildOfClass("UIStroke").Enabled == false, "the flat panel, its code-built dots and its edge are hidden")
local strip = w.header:FindFirstChild("ToyboxHeader")
assert(strip and strip.Image == ids.toybox_header_blue and strip.ScaleType == Enum.ScaleType.Slice and rect(strip, {150, 30, 224, 98}), "header strip: blue before a screen is shown, 9-slice")
assert(strip.SliceScale == 78 / 128, "the header strip never stretches up or down")
w.header.Size = UDim2.fromOffset(600, 64)
assert(strip.SliceScale == 0.5, "a shorter (phone) header rescales the strip")
assert(w.header.BackgroundTransparency == 1 and w.header:FindFirstChild("FossilTexture").Visible == false, "the flat header is hidden")
__HEADERS__
Theme.Toybox.place("somethingNew")
assert(strip.Image == ids.toybox_header_blue, "an unknown screen = blue")
w.header.BackgroundColor3 = C.gold -- what a screen does today: the picture, not the flat colour, shows
assert(w.header.BackgroundTransparency == 1, "a screen's flat header colour stays hidden")
local title = w.header:FindFirstChild("ToyboxDrop")
assert(title and title.Text == "Dino Index" and title.ZIndex < w.heading.ZIndex and title.Position == w.heading.Position + UDim2.fromOffset(0, 3), "the title has its drop, 3 px under it")
w.heading.Text = "Eggs"
assert(title.Text == "Eggs" and title.TextSize == 40 and strokeOf(title) == 4 and strokeOf(w.heading) == 4, "the drop follows the title; 4 px outline")
-- ---- the X
local x = w.closeButton:FindFirstChild("ToyboxFace")
assert(x and x.Image == ids.toybox_close and x.ScaleType == Enum.ScaleType.Fit, "the red gloss X, drawn whole")
assert(x.Size == UDim2.fromOffset(62, 62), "desktop: a square of the button's short side")
assert(w.closeButton:FindFirstChild("ToyboxText").Visible == false and w.closeButton.TextTransparency == 1, "the X is in the picture, the letter is hidden")
w.scale.Scale = 0.6
w.closeButton.AbsoluteSize = Vector2.new(48, 37)
assert(x.Size.X.Offset == x.Size.Y.Offset and x.Size.X.Offset * 0.6 >= 48 - 1e-6, "small window: the X is still a square of at least 48 px on screen")
w.closeButton.BackgroundColor3 = C.card
assert(x.Image == ids.toybox_close, "the X never becomes a plain button")
-- ---- the Fusion Menu window: a fixed place
local f = window()
Theme.Toybox.window({panel = f.panel, header = f.header, heading = f.heading, closeButton = f.closeButton, place = "fusion"})
local fusionStrip = f.header:FindFirstChild("ToyboxHeader")
assert(fusionStrip.Image == ids.toybox_header_purple, "Fusion is purple")
Theme.Toybox.place("auras")
assert(fusionStrip.Image == ids.toybox_header_purple and strip.Image == ids.toybox_header_amber, "the menu window follows the screen, the Fusion Menu stays purple")
-- ---- every picture the skin placed is a bound kit picture, every text at least 14 px
local function walk(node)
    if node.ClassName == "ImageLabel" then
        local slot = node:GetAttribute("ToyboxSlot")
        assert(slot and Kit.Assets[slot] and node.Image == ids[slot] and string.match(node.Image, "^rbxassetid://%d+$"), "a placed picture is a bound kit picture: " .. tostring(node.Name))
    end
    if (node.ClassName == "TextLabel") and string.sub(node.Name, 1, 6) == "Toybox" then assert(node.TextSize >= 14, "skin text at least 14 px") end
    for _, child in node.__children do walk(child) end
end
walk(w.shade) walk(f.shade)
'''


def scene(read, flag, bound, checks, theme=None, style=None):
    source = SCENE.replace('__CHECKS__', checks)
    for key, value in (('__FLAG__', flag), ('__BOUND__', bound), ('__KIT__', wrap(read(KIT))), ('__SKIN__', wrap(read(SKIN))),
                       ('__SLOTS__', wrap(read(SLOTS))), ('__STYLE__', wrap(style if style is not None else read(STYLE))),
                       ('__MOTION__', wrap(read(MOTION))), ('__THEME__', wrap(theme if theme is not None else read(THEME)))):
        source = source.replace(key, value)
    return source


def dump_of(text):
    return [line for line in text.splitlines() if line.startswith('DUMP ')]


PNG_CACHE = {}


def png_one(file, slot, w, h, rect, fit):
    """Measures one picture against its kit line. Cached: the mutants re-check the same pictures."""
    key = (file, slot, w, h, rect, fit)
    if key not in PNG_CACHE:
        try:
            png_measure(file, slot, w, h, rect, fit)
            PNG_CACHE[key] = None
        except AssertionError as error:
            PNG_CACHE[key] = str(error)
    if PNG_CACHE[key]:
        raise AssertionError(PNG_CACHE[key])


def png_checks(pure_out):
    assets = {}
    folder = None
    for line in pure_out.splitlines():
        if line.startswith('ASSET '):
            _tag, slot, file, w, h, rect, fit = line.split()
            assets[file] = (slot, int(w), int(h), None if rect == '-' else tuple(int(v) for v in rect.split(',')), fit)
        elif line.startswith('FOLDER '):
            folder = line.split()[1]
    assert folder == ART, 'the kit names the art folder ' + ART
    on_disk = sorted(p.name for p in (ROOT / ART).iterdir())
    assert on_disk == sorted(assets), 'the art folder holds exactly the kit pictures (no review sheet): extra %s, missing %s' % (
        sorted(set(on_disk) - set(assets)), sorted(set(assets) - set(on_disk)))
    for file, (slot, w, h, rect, fit) in sorted(assets.items()):
        png_one(file, slot, w, h, rect, fit)
    return len(assets)


def png_measure(file, slot, w, h, rect, fit):
    from PIL import Image
    if True:
        image = Image.open(ROOT / ART / file).convert('RGBA')
        assert image.size == (w, h), '%s is %s, the kit says %s' % (file, image.size, (w, h))
        kind = 'studs' if file == 'studs-tile.png' else 'panel' if file == 'panel-frame.png' else file.split('-')[0].replace('.png', '')
        assert image.size == SIZES[kind], '%s size' % file
        assert slot == 'toybox_' + file[:-4].replace('-', '_'), 'slot name of ' + file
        px = image.load()
        if rect is None:
            assert kind in ('close', 'studs'), file + ' must have a slice rect'
            return
        x0, y0, x1, y1 = rect
        assert 0 < x0 < x1 < w and 0 < y0 < y1 < h, '%s: slice rect inside the picture' % file

        def differ(a, b, tol=8):
            return max(abs(a[i] - b[i]) for i in range(4)) > tol
        # the rounded corners (see-through pixels) stay in the caps
        for y in range(h):
            for x in range(w):
                if px[x, y][3] < 128:
                    assert (x < x0 or x >= x1) and (y < y0 or y >= y1), '%s: a rounded corner pixel (%d,%d) is inside the stretching band' % (file, x, y)
        # stretching sideways: inside the centre columns every row is one flat colour (no stripe, no stud)
        for y in range(h):
            for x in range(x0, x1 - 1):
                assert not differ(px[x, y], px[x + 1, y]), '%s: row %d changes inside the centre columns %d..%d (a stripe or stud would stretch)' % (file, y, x0, x1)
        if fit == 'height':
            assert kind == 'header', 'only headers fit their height'
            return
        assert kind != 'header', 'a header must fit its height: its shine stripes cannot stretch up or down'
        # stretching up and down: inside the centre rows every column changes at most at one edge (two flat tones)
        for x in range(w):
            steps = [y for y in range(y0, y1 - 1) if differ(px[x, y], px[x, y + 1])]
            assert not steps or (kind == 'button' and steps[-1] - steps[0] <= 3), '%s: column %d changes inside the centre rows %d..%d' % (file, x, y0, y1)


def check(runner, mutant=None):
    read = reader(mutant)
    out = ''
    try:
        static_checks(read)
        names = screens(read)
        assert len(names) >= 24, 'the client opens at least 24 screens (found %d)' % len(names)
    except AssertionError as error:
        return False, 'static: %s\n' % error
    places = ''.join('eq(Kit.headerSlot("%s"), "toybox_header_%s", "the place of %s")\n' % (screen, colour, screen) for screen, colour in OWNER_PLACES.items())
    places += ''.join('assert(Kit.ScreenPlace["%s"] ~= nil, "screen %s has no place: add it to ToyboxKit.ScreenPlace")\n' % (name, name) for name in names)
    ok, text = run(runner, PURE.replace('__KIT__', wrap(read(KIT))).replace('__PLACES__', places), 'kit')
    out += '\n'.join(line for line in text.splitlines() if not line.startswith(('ASSET ', 'FOLDER '))) + '\n'
    if not ok:
        return False, out
    try:
        pictures = png_checks(text)
    except AssertionError as error:
        return False, out + 'pictures: %s\n' % error
    out += 'pictures ok: %d files measured against the kit\n' % pictures
    # flag off: the same build as the files without any Toybox line
    ok, real = run(runner, scene(read, 'false', 'all', CHECK_OFF), 'off')
    out += '\n'.join(line for line in real.splitlines() if not line.startswith('DUMP ')) + '\n'
    if not ok:
        return False, out
    ok, old = run(runner, scene(read, 'false', 'all', '', theme=strip(read(THEME), THEME_HOOKS), style=strip(read(STYLE), STYLE_HOOKS)), 'old')
    if not ok:
        return False, out + old
    if dump_of(real) != dump_of(old) or len(dump_of(real)) < 50:
        return False, out + 'flag off is NOT today\'s build: the window and buttons differ from the files without the Toybox lines\n'
    out += 'flag off = the build without the Toybox lines (%d instances compared)\n' % len(dump_of(real))
    headers = ''.join('Theme.Toybox.place("%s") assert(strip.Image == ids.toybox_header_%s, "screen %s shows the %s header")\n' % (s, c, s, c) for s, c in OWNER_PLACES.items())
    headers += ''.join('Theme.Toybox.place("%s") assert(strip.Image ~= ids.toybox_header_red and string.match(strip.Image, "^rbxassetid://%%d+$"), "screen %s has a header, never the red one")\n' % (n, n) for n in names)
    runs = [('true', 'none', CHECK_EMPTY), ('true', 'all', CHECK_BOUND.replace('__HEADERS__', headers))]
    runs += [('true', bound, CHECK_PARTIAL) for bound in ('close', 'sixbuttons', 'nobutton', 'invented')]
    for flag, bound, checks in runs:
        ok, text = run(runner, scene(read, flag, bound, checks), 'on_' + bound)
        out += '\n'.join(line for line in text.splitlines() if not line.startswith('DUMP ')) + '\n'
        if not ok:
            return False, out
    return True, out


MUTANTS = {
    # the flag
    'the flag ships on': (CONFIG, '    ToyboxUIEnabled = false,', '    ToyboxUIEnabled = true,'),
    'the default profile does not pin the flag off': (PROFILES, '_flag_off("ToyboxUIEnabled",', '_flag_off("ToyboxUIEnabledX",'),
    'the playtest profile does not set the flag': (PROFILES, 'Rule("ToyboxUIEnabled", "set", True,', 'Rule("ToyboxUIEnabled", "set", False,'),
    'the skin loads with the flag off': (THEME, 'Theme.Toybox = if (Config :: any).ToyboxUIEnabled == true then require(script.Parent.ToyboxSkin) else nil\n',
                                         'Theme.Toybox = if (Config :: any).ToyboxUIEnabled ~= true then require(script.Parent.ToyboxSkin) else nil\n'),
    'buttons are never skinned': (THEME, '        if Theme.Toybox then Theme.Toybox.button(object, border) end -- BD-1177: the gloss button picture\n', ''),
    'the text outline ignores the skin': (STYLE, '    if TextStyle.SkinThickness then stroke.Thickness = TextStyle.SkinThickness(label.TextSize) end -- BD-1177\n',
                                          '    if TextStyle.SkinThickness then stroke.Thickness = stroke.Thickness end -- BD-1177\n'),
    'a title keeps the 3 px outline': (STYLE, '    if TextStyle.SkinThickness and stroke.Parent == label then stroke.Thickness = TextStyle.SkinThickness(label.TextSize) end -- BD-1177\n',
                                       '    if TextStyle.SkinThickness and stroke.Parent == label then stroke.Thickness = math.min(3, TextStyle.SkinThickness(label.TextSize)) end -- BD-1177\n'),
    'the menu window is not skinned': (COMPACT, COMPACT_WINDOW, ''),
    'the header ignores the screen': (COMPACT, COMPACT_PLACE, ''),
    'Bootstrap does not hand over the screen name': (BOOT, BOOT_HOOK, '    require(script.Parent.ModalCompact).layout()\n'),
    'the Fusion Menu follows the menu window': (FUSION, 'closeButton = closeX, place = "fusion"})', 'closeButton = closeX})'),
    # the kit numbers
    'text floor 12 px': (KIT, 'Kit.MinText = 14', 'Kit.MinText = 12'),
    'X floor 40 px': (KIT, 'Kit.MinClose = 48', 'Kit.MinClose = 40'),
    'thin 2 px outline': (KIT, 'Kit.StrokeSmall, Kit.StrokeBig, Kit.StrokeBigFrom = 3, 4, 28', 'Kit.StrokeSmall, Kit.StrokeBig, Kit.StrokeBigFrom = 2, 4, 28'),
    'heavy 6 px outline': (KIT, 'Kit.StrokeSmall, Kit.StrokeBig, Kit.StrokeBigFrom = 3, 4, 28', 'Kit.StrokeSmall, Kit.StrokeBig, Kit.StrokeBigFrom = 3, 6, 28'),
    'the X ignores the window scale': (KIT, '    return math.max(short, Kit.MinClose) / s\n', '    return math.max(short, Kit.MinClose)\n'),
    'the Crystal Shop is green': (KIT, 'Kit.PlaceHeader = {shop = "amber",', 'Kit.PlaceHeader = {shop = "green",'),
    'Settings is blue': (KIT, 'fusion = "purple", eggs = "cream", settings = "dark"}', 'fusion = "purple", eggs = "cream", settings = "blue"}'),
    'Fusion is red': (KIT, 'fusion = "purple", eggs = "cream",', 'fusion = "red", eggs = "cream",'),
    'the Potion Shop counts as the Crystal Shop': (KIT, '    potions = "potions",', '    potions = "shop",'),
    'the Eggs screen has no place': (KIT, '    eggs = "eggs", hatch = "eggs",', '    hatch = "eggs",'),
    'a starter card screen without a place': (KIT, 'batchSummary = "eggs", starter = "eggs",', 'batchSummary = "eggs",'),
    'red and green buttons swapped': (KIT, '    green = {93, 237, 31}, grey = {128, 142, 158},', '    green = {247, 57, 48}, grey = {128, 142, 158},'),
    'an empty id counts as bound': (KIT, '    return type(id) == "string" and string.match(id, "^rbxassetid://%d+$") ~= nil\n', '    return type(id) == "string"\n'),
    'a half-bound group is used': (KIT, '    for _, slot in list do if Kit.image(images, slot) == nil then return false end end\n    return true\n',
                                   '    for _, slot in list do if Kit.image(images, slot) ~= nil then return true end end\n    return false\n'),
    'bare digits pass as an id': (KIT, 'string.match(id, "^rbxassetid://%d+$") ~= nil', 'string.match(id, "%d+$") ~= nil'),
    # the slice rects (measured against the PNGs)
    'header centre runs through a shine stripe': (KIT, 'local HEADER_SLICE, BUTTON_SLICE, CARD_SLICE, FRAME_SLICE = {150, 30, 224, 98},', 'local HEADER_SLICE, BUTTON_SLICE, CARD_SLICE, FRAME_SLICE = {100, 30, 224, 98},'),
    'header stretches up and down': (KIT, '512, 128, HEADER_SLICE, "height")', '512, 128, HEADER_SLICE)'),
    'button centre cuts the rounded corner': (KIT, '{24, 20, 232, 88}, {70, 34, 108, 92}', '{8, 20, 232, 88}, {70, 34, 108, 92}'),
    'button centre cuts the top edge': (KIT, '{24, 20, 232, 88}, {70, 34, 108, 92}', '{24, 2, 232, 88}, {70, 34, 108, 92}'),
    'card centre runs through the studs': (KIT, '{70, 34, 108, 92}, {36, 36, 220, 220}', '{70, 34, 180, 250}, {36, 36, 220, 220}'),
    'frame centre cuts the rounded corner': (KIT, '{70, 34, 108, 92}, {36, 36, 220, 220}', '{70, 34, 108, 92}, {12, 36, 220, 220}'),
    'a picture with the wrong size': (KIT, 'add("toybox_close", "close.png", 128, 128)', 'add("toybox_close", "close.png", 256, 256)'),
    'the review sheet is shipped as a kit picture': (KIT, 'add("toybox_studs_tile", "studs-tile.png", 256, 256)', 'add("toybox_studs_tile", "_sheet.png", 256, 256)'),
    # the skin
    'buttons are skinned before the ids are bound': (SKIN, '    if faces[button] or not ready("button") then return end\n', '    if faces[button] then return end\n'),
    'an invisible touch area gets a picture': (SKIN, '    if button.BackgroundTransparency >= 1 then return end\n    build(button, border)\n', '    build(button, border)\n'),
    'the button word is not raised to 14 px': (SKIN, '        local size = Kit.textSize(button.TextSize)\n', '        local size = button.TextSize\n'),
    'the old button edge stays': (SKIN, '    if border then border.Enabled = false end', '    if border then border.Enabled = true end'),
    'a colour change keeps the old picture': (SKIN, '        image.Image = id(nextSlot) or image.Image\n        image:SetAttribute("ToyboxSlot", nextSlot)\n', '        image:SetAttribute("ToyboxSlot", nextSlot)\n'),
    'a dimmed word shows twice': (SKIN, '        button.TextTransparency = 1\n    end\n    dim()', '    end\n    dim()'),
    'the label does not follow the Text': (SKIN, '    for _, property in TEXT_PROPERTIES do button:GetPropertyChangedSignal(property):Connect(text) end\n', ''),
    'a padding shrinks the picture': (SKIN, '        if added:IsA("UIPadding") and not face.close then', '        if false then'),
    'the X fills the button (not a square)': (SKIN, '        image.Size = UDim2.fromOffset(side, side)\n', '        image.Size = UDim2.fromScale(1, 1)\n'),
    'the X is sliced like a button': (SKIN, '    image.ScaleType, image.Image = Enum.ScaleType.Fit, closeId\n', '    image.Image = closeId\n'),
    'the X keeps its letter': (SKIN, '    face.word.Visible, face.drop.Visible = false, false -- the X is in the picture\n', ''),
    'the X becomes a plain button on a colour change': (SKIN, '        if face.close then return end\n', ''),
    'the studs are stretched, not tiled': (SKIN, '        studs.ScaleType, studs.TileSize = Enum.ScaleType.Tile, UDim2.fromOffset(Kit.StudTile, Kit.StudTile)\n', '        studs.TileSize = UDim2.fromOffset(Kit.StudTile, Kit.StudTile)\n'),
    'the code-built dots stay under the studs': (SKIN, '    if studs and studs:IsA("GuiObject") then studs.Visible = false end\n', ''),
    'the flat panel shows behind the frame': (SKIN, '    box.BackgroundTransparency = 1\n', ''),
    'the header keeps one colour for every screen': (SKIN, '    image.Image = id(slot) or image.Image\n', ''),
    'the Fusion header follows the menu window': (SKIN, '        if window.place == nil then mainHeader = strip end\n', '        mainHeader = strip\n'),
    'the title has no drop': (SKIN, '        if window.heading then Skin.drop(window.heading) end\n', ''),
    'the drop does not follow the word': (SKIN, '    for _, property in TEXT_PROPERTIES do label:GetPropertyChangedSignal(property):Connect(follow) end\n', ''),
    'the header strip stretches with the header': (SKIN, '    box:GetPropertyChangedSignal("Size"):Connect(fit)\n', ''),
    'the window is skinned with the panel ids missing': (SKIN, '    if ready("panel") then\n', '    if true then\n'),
    # the slots
    'an invented id in a slot': (SLOTS, '    toybox_close = "",', '    toybox_close = "rbxassetid://1",'),
    'a slot is missing': (SLOTS, '    toybox_studs_tile = "",\n', ''),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    ok, out = check(args.runner)
    print(out, end='')
    if not ok:
        raise SystemExit('Toybox UI check failed')
    print('Toybox UI wiring passed: flag off in Config and the default profile, on in the playtest profile, in the rehearsal list; no server file')
    if args.no_mutants:
        return
    from concurrent.futures import ThreadPoolExecutor
    names = list(MUTANTS)
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda n: check(args.runner, MUTANTS[n]), names))
    survived = [name for name, (passed, _out) in zip(names, results) if passed]
    assert not survived, 'MUTANT SURVIVED (the Toybox UI check did not notice): ' + '; '.join(survived)
    for name in names:
        print('  mutant caught: ' + name)
    print('Toybox UI passed: %d mutants caught' % len(MUTANTS))


if __name__ == '__main__':
    sys.exit(main())
