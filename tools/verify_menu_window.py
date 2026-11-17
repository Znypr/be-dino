#!/usr/bin/env python3
"""BD-1266 + BD-1267 + BD-1270 (docs/244 s2.12 to s2.14, owner 2026-11-17 "Yes, build it"): the ONE standard menu window.
Runs the REAL Shared/MenuWindowRules in the pinned Luau runtime and checks, at a phone (960 x 450), a short PC window and a 1080p desktop:
  * the window sizes are the shares of docs/244 s2.14 (long 58 % w x 67 % h within 540..1100 px, item 43 % w x 56 % h), centred 3 % h low;
  * title bar 10 % h, title 4.5 % h cap, red X 8 % h (never under 44 px), section 3.8 % h, offer card 28 % h, item card 44 % h, price button
    6.6 % h, tabs: icon 9.5 % h and word 3 % h, 1.5 % h apart, OUTSIDE the window on the right, every tab at least 44 px tall;
  * offer cards 2 per row on a phone, 3 on a desktop; item cards 3 per row; card parts stay inside their card; text never under 14 px;
  * the colour map (green Crystal Shop, purple Potion Shop) and the header picture of each colour; rarity colours from docs/114 s5;
  * "-- AURAS --" section words, the green key number of a card line, prices with commas and never an R$ / Robux word;
  * the Crystals (Robux packs) tab never shows; Featured first only with its flag;
  * BD-1270: the weekly pick is deterministic, the same all week, changes on Monday 00:00 UTC, only priced (crystal) items, never more than 3;
    "3 days left" / "1 day left" / "Last day", never seconds.
Source guards: both flags ship false and are pinned off by default; StandardMenuEnabled is ON in the playtest profile, ShopFeaturedEnabled stays
off everywhere until the owner approves the window (owner 2026-11-18); both are in the rehearsal list and the manifest; the
routes are registered only behind StandardMenuEnabled; Bootstrap.client is untouched; the window and the pages build no art (only the allowed
instance classes), use Chip.apply, send nothing themselves (only through ShopScreens' transact), and have no Robux, gift or crossed-out price.
Mutants put a defect back and the checks must fail.
NOT Studio evidence: the pictures are in docs/evidence/2026-11-17-ui-windows/.
Usage: python tools/verify_menu_window.py --runner luau.exe [--no-mutants]"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RULES = 'src/shared/MenuWindowRules.luau'
WINDOW = 'src/client/MenuWindow.luau'
PAGES = 'src/client/ShopWindowPages.luau'


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


def code_only(text):
    return '\n'.join(line.split('--', 1)[0] for line in text.splitlines())


LUAU = r'''
local fails = {}
local function check(ok, what) if not ok then table.insert(fails, what) end end
local function near(a, b, tol) return math.abs(a - b) <= tol end
local screens = {{960, 450, "phone"}, {1280, 560, "short PC"}, {1920, 1080, "desktop"}}
for _, s in screens do
    local W, H, tag = s[1], s[2], s[3]
    local long = R.rect(W, H, "long")
    check(near(long.w, math.clamp(W * .58, 540, 1100), 1), tag .. ": long window 58 % w")
    check(near(long.h, H * .67, 1), tag .. ": long window 67 % h")
    check(near(long.x + long.w / 2, W / 2, 1), tag .. ": centred across")
    check(near(long.y + long.h / 2, H / 2 + H * .03, 1), tag .. ": centred 3 % h below the middle")
    local item = R.rect(W, H, "item")
    check(near(item.h, H * .56, 1) and item.w <= long.w, tag .. ": item window 56 % h, narrower")
    check(near(R.px(H, R.H.titleBar), H * .10, 1), tag .. ": title bar 10 % h")
    check(near(R.textSize(H, R.H.title) * R.CapRatio, math.max(H * .045, 14 * R.CapRatio), 1), tag .. ": title 4.5 % h cap")
    check(math.max(R.px(H, R.H.close), R.MinTarget) >= 44, tag .. ": X at least 44 px")
    check(near(R.px(H, R.H.offerCard), H * .28, 1) and near(R.px(H, R.H.itemCard), H * .44, 1), tag .. ": card heights")
    for _, share in {R.H.title, R.H.section, R.H.offerTitle, R.H.offerLine, R.H.itemName, R.H.itemRarity, R.H.itemEffect, R.H.tabWord, R.H.smallest} do
        check(R.textSize(H, share) >= 14, tag .. ": text never under 14 px")
    end
    local t = R.tabs(W, H, "long", 4)
    check(t.x >= long.x + long.w, tag .. ": tabs OUTSIDE the window on the right")
    check(near(t.x - (long.x + long.w), H * .02, 1), tag .. ": tab column 2 % h right of the window")
    check(near(t.icon, H * .095, 1) and near(t.word, H * .03, 1) and near(t.pitch - t.tabH, H * .015, 1), tag .. ": tab icon / word / gap")
    check(t.tabH >= 44 and t.tabW >= 44, tag .. ": every tab is a 44 px target")
    check(R.columns("offer", H) == (if H < 600 then 2 else 3), tag .. ": offer columns")
    check(R.columns("item", H) == 3, tag .. ": item cards 3 per row")
    local cw = R.cell(long.w - 40, 2, R.px(H, R.H.gap))
    local o = R.offerParts(cw, H)
    for _, key in {"icon", "title", "line", "button"} do
        local r = o[key]
        check(r.x >= 0 and r.y >= 0 and r.x + r.w <= cw + 0.5 and r.y + r.h <= o.h + 0.5, tag .. ": offer part inside the card: " .. key)
    end
    check(o.button.h >= 44, tag .. ": price button 44 px")
    check(o.icon.x + o.icon.w <= o.title.x, tag .. ": the icon is left of the words")
    local i = R.itemParts(R.cell(item.w - 40, 3, R.px(H, R.H.gap)), H)
    for _, key in {"name", "rarity", "render", "strip", "button"} do
        local r = i[key]
        check(r.y >= 0 and r.y + r.h <= i.h + 0.5, tag .. ": item part inside the card: " .. key)
    end
    check(i.render.y + i.render.h <= i.strip.y and i.strip.y + i.strip.h <= i.button.y, tag .. ": render, strip, button in order")
    check(i.button.h >= 44, tag .. ": item button 44 px")
    local n = R.itemParts(100, H, nil, true)
    check(n.strip.y + n.strip.h + 8 >= n.h - 8, tag .. ": a card without a button has the strip at its foot")
end
check(R.textSize(200, R.H.smallest) == 14 and R.textSize(0 / 0, R.H.title) >= 14, "a tiny screen still gets 14 px text")
check(R.Screens.crystalShop.colour == "green" and R.Screens.crystalShop.kind == "long", "Crystal Shop: green, long")
check(R.Screens.potionShop.colour == "purple" and R.Screens.potionShop.kind == "item", "Potion Shop: purple, item cards")
check(R.headerSlot("green") == "toybox_header_green" and R.headerSlot("yellow") == "toybox_header_amber" and R.headerSlot("cyan") == "toybox_header_blue", "header pictures")
check(R.headerSlot("nope") == "toybox_header_dark", "unknown colour = grey (dark header)")
local spec = {Common = {128, 142, 158}, Uncommon = {93, 237, 31}, Rare = {46, 206, 255}, Epic = {194, 86, 255}, Legendary = {255, 210, 43}, Mythic = {247, 57, 48}}
for name, c in spec do
    local got = R.rarityColour(name)
    check(got[1] == c[1] and got[2] == c[2] and got[3] == c[3], "rarity colour " .. name)
    check(R.cardSlot(string.lower(name)) == "toybox_card_" .. string.lower(name), "card picture " .. name)
end
check(R.cardSlot(nil) == "toybox_card_common", "unknown rarity = Common")
check(R.section("Auras") == "-- AURAS --", "section words")
check(R.highlight("Speed +20% - 5 min") == 'Speed <font color="#7CFF4A">+20%</font> - 5 min', "the key number is green: " .. R.highlight("Speed +20% - 5 min"))
check(R.highlight("Looks <cool>") == "Looks &lt;cool&gt;", "no number = plain, escaped")
check(R.price(3700) == "3,700" and R.price(17000) == "17,000" and R.price(60) == "60", "price commas")
for _, state in {"buy", "short", "owned", "equipped", "use", "locked", "soldout", "chances", "max", "soon"} do
    local b = R.button(state, 1234, 5)
    check(not string.find(b.text, "R%$") and not string.find(string.lower(b.text), "robux"), "no Robux on a button: " .. state)
end
check(R.button("buy", 60).green and R.button("buy", 60).icon and R.button("buy", 60).text == "60", "buy = green crystal number")
check(not R.button("short", 60).green, "not enough crystals = grey")
check(not R.button("soldout").active, "sold out cannot be pressed")
local tabs = R.shopTabs({"auras", "trails", "eggs", "conditions", "crystals"}, true)
check(tabs[1] == "featured" and #tabs == 5, "Featured first")
for _, t in tabs do check(t ~= "crystals", "no Robux pack tab") end
check(R.shopTabs({"auras", "crystals"}, false)[1] == "auras" and #R.shopTabs({"auras", "crystals"}, false) == 1, "no Featured without its flag")
check(R.firstTab({"featured", "auras"}, "auras") == "auras" and R.firstTab({"featured", "auras"}, "gone") == "featured", "the kept tab, else the first")
for key in R.TabWords do check(R.TabArt[key] ~= nil, "every tab has an art slot: " .. key) end
-- BD-1270
local pool = {{id = "a", price = 60}, {id = "free", price = 0}, {id = "b", price = 100}, {id = "c", price = 200}, {id = "d", price = 300}}
local monday = R.WeekStart + 2900 * R.Week
local p1 = R.featured(pool, monday)
check(#p1 == 3, "three picks")
for _, item in p1 do check(item.price > 0, "only priced crystal items") end
for h = 0, 7 * 24 - 1, 13 do
    local again = R.featured(pool, monday + h * 3600)
    check(again[1].id == p1[1].id and again[2].id == p1[2].id, "the same all week")
end
check(R.featured(pool, monday + R.Week)[1].id ~= p1[1].id, "next Monday a new pick")
check(R.featured(pool, monday - 1)[1].id ~= p1[1].id, "the week turns over on Monday 00:00 UTC")
local seen = {}
for w = 0, 3 do seen[R.featured(pool, monday + w * R.Week)[1].id] = true end
local count = 0 for _ in seen do count += 1 end
check(count == 4, "every priced item gets its week")
check(#R.featured({{id = "x", price = 0}}, monday) == 0, "nothing priced = nothing featured")
check(R.daysLeft(monday) == "7 days left", "a fresh week: " .. R.daysLeft(monday))
check(R.daysLeft(monday + 5 * 86400) == "2 days left", "two days")
check(R.daysLeft(monday + 6 * 86400 - 1) == "1 day left", "one day")
check(R.daysLeft(monday + 6 * 86400 + 3600) == "Last day", "the last day")
for h = 0, 7 * 24 - 1 do check(not string.find(R.daysLeft(monday + h * 3600), "%d+ ?s"), "never seconds") end
if #fails > 0 then for _, f in fails do print("FAIL: " .. f) end error("menu window checks failed") end
print("menu window checks passed")
'''


def run(runner, rules_text):
    script = 'local R=(function()\n' + rules_text + '\nend)()\n' + LUAU
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'verify_menu_window.luau'
        path.write_text(script, encoding='utf-8')
        out = subprocess.run([runner, str(path)], capture_output=True, text=True)
        return out.returncode == 0, (out.stdout + out.stderr).strip()


def static_checks(files=None):
    files = files or {}
    get = lambda path: files.get(path) or read(path)  # noqa: E731
    errors = []
    config, profiles = get('src/shared/Config.luau'), get('tools/release_profiles.py')
    if 'Rule("ShopFeaturedEnabled", "set", True,' in profiles:
        errors.append('ShopFeaturedEnabled stays off in every profile until the owner approves the standard window (owner 2026-11-18)')
    for flag, row in (('StandardMenuEnabled', 'BD-1266'), ('ShopFeaturedEnabled', 'BD-1270')):
        if len(re.findall(r'^    %s = false,$' % flag, config, re.M)) != 1:
            errors.append('Config.%s must ship false exactly once' % flag)
        wanted = ('_flag_off("%s",' % flag, '("%s", "%s' % (flag, row)) + (('Rule("%s", "set", True,' % flag,) if flag == 'StandardMenuEnabled' else ())
        for needle in wanted:
            if needle not in profiles:
                errors.append('release_profiles.py is missing %s' % needle)
        if '"%s"' % flag not in get('tools/release_playtest.py') or '"%s"' % flag not in get('tests/test_rehearsal.py'):
            errors.append('%s must be in the playtest manifest and the rehearsal list' % flag)
    shop = get('src/client/ShopScreens.luau')
    if 'if Config.StandardMenuEnabled==true then Shop.standardRoutes() end' not in shop:
        errors.append('ShopScreens registers the standard window routes only behind StandardMenuEnabled')
    if shop.count('Guard.Routes[name]=') != 1 or 'Pages.Names' not in shop:
        errors.append('ShopScreens routes exactly the page names of ShopWindowPages')
    guard = get('src/client/ModalGuard.luau')
    if 'local route = Guard.Routes[name]' not in guard or 'if Guard.onOther then Guard.onOther() end' not in guard:
        errors.append('ModalGuard asks the routes, and closes the standard window before any other screen')
    pages = get(PAGES)
    if 'Config.ShopFeaturedEnabled == true' not in pages:
        errors.append('the Featured tab shows only with ShopFeaturedEnabled')
    boot = read('src/client/Bootstrap.client.luau')
    for word in ('MenuWindow', 'ShopWindowPages', 'StandardMenu'):
        if word in boot:
            errors.append('Bootstrap.client must not change: %s' % word)
    window = get(WINDOW)
    made = set(re.findall(r'Instance\.new\("(\w+)"\)', code_only(window) + code_only(pages)))
    allowed = {'Frame', 'ImageLabel', 'ImageButton', 'TextLabel', 'TextButton', 'ScrollingFrame', 'UIStroke', 'UICorner', 'UIScale',
               'UITextSizeConstraint', 'UIListLayout', 'UIGridLayout', 'BlurEffect', 'ScreenGui'}
    if not made <= allowed:
        errors.append('the window draws no art: only placing classes are allowed, found %s' % sorted(made - allowed))
    if 'UIGradient' in code_only(window + pages) or 'Path2D' in window:
        errors.append('no code-drawn gradients or shapes in the window')
    if 'Chip.apply' not in window:
        errors.append('the fallbacks use the one chip style (Chip.apply)')
    for name, text in ((WINDOW, window), (PAGES, pages)):
        body = code_only(text)
        for banned in ('FireServer', 'InvokeServer', 'MarketplaceService', 'PromptProductPurchase', 'DataStore'):
            if banned in body:
                errors.append('%s sends nothing itself: %s' % (name, banned))
        for banned in ('R$', 'Robux', 'robux', 'Gift', 'gift', 'worth', 'RichText = true and "<s>', '<s>'):
            if banned in body:
                errors.append('%s: no Robux, gift or crossed-out price (%s)' % (name, banned))
    if 'MenuWindowRules' not in window or 'Blur' not in window or 'Rules.Blur' not in window:
        errors.append('the window blurs the world with Rules.Blur')
    if 'ModalScrim' in window or 'BackgroundTransparency = .42' in window:
        errors.append('no dark scrim: the HUD stays visible')
    return errors


MUTANTS = {
    'the long window is the item width': (RULES, 'long = {w = 0.58,', 'long = {w = 0.43,'),
    'the window sits in the middle': (RULES, 'below = 0.03,', 'below = 0,'),
    'the title bar is 6 % h': (RULES, 'titleBar = 0.10,', 'titleBar = 0.06,'),
    'tiny tab words': (RULES, 'tabWord = 0.03,', 'tabWord = 0.015,'),
    'the tabs sit inside the window': (RULES, 'x = win.x + win.w + R.px(H, R.H.tabLeft)', 'x = win.x + win.w - R.px(H, R.H.tabIcon)'),
    'offer cards 3 per row on a phone': (RULES, 'return if sane(screenH, 480) < R.PhoneMaxH then 2 else 3 end', 'return 3'),
    'the Robux pack tab shows': (RULES, 'if tab ~= "crystals" and tab ~= "featured" then', 'if tab ~= "featured" then'),
    'Featured is last': (RULES, '    if featured then table.insert(out, "featured") end\n', ''),
    'free items get featured': (RULES, 'item.price > 0 then table.insert(priced, item)', 'item.price >= 0 then table.insert(priced, item)'),
    'the pick changes every day': (RULES, 'local start = R.week(now) % n', 'local start = math.floor(now / 86400) % n'),
    'the last day counts down in seconds': (RULES, 'return "Last day"', 'return math.floor(ends - t) .. " s left"'),
    'the key number is not green': (RULES, "'<font color=\"' .. R.hex(R.Green) .. '\">'", "'<font color=\"#FFFFFF\">'"),
    'a Robux sign on the price': (RULES, 'return {text = R.price(price), green = true, active = true, icon = true}', 'return {text = "R$ " .. R.price(price), green = true, active = true, icon = true}'),
    'text under 14 px': (RULES, 'return math.max(R.MinText, math.floor(', 'return math.max(1, math.floor('),
    'Mythic is purple': (RULES, 'Mythic = {247, 57, 48},', 'Mythic = {194, 86, 255},'),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    parser.add_argument('--no-mutants', action='store_true')
    args = parser.parse_args()
    rules = read(RULES)
    ok, out = run(args.runner, rules)
    print(out.splitlines()[-1] if out else '')
    if not ok:
        print(out)
        raise SystemExit('menu window rules failed')
    errors = static_checks()
    if errors:
        raise SystemExit('\n'.join('FAIL: ' + e for e in errors))
    caught = 0
    if not args.no_mutants:
        for name, (path, old, new) in MUTANTS.items():
            text = read(path)
            assert text.count(old) == 1, 'mutant anchor must match once: %s' % name
            bad, _ = run(args.runner, text.replace(old, new))
            if bad:
                raise SystemExit('mutant NOT caught: ' + name)
            caught += 1
        static_mutants = {
            'the routes ignore the flag': ('src/client/ShopScreens.luau', 'if Config.StandardMenuEnabled==true then Shop.standardRoutes() end', 'Shop.standardRoutes()'),
            'Featured ignores its flag': (PAGES, 'Config.ShopFeaturedEnabled == true', 'true'),
            'the window sends a remote itself': (PAGES, 'local function now(): number return workspace:GetServerTimeNow() end', 'local function now(): number game:GetService("ReplicatedStorage").X:FireServer() return 0 end'),
            'the window draws a gradient': (WINDOW, 'Chip.apply(back, rgb(Rules.Body))', 'Chip.apply(back, rgb(Rules.Body)) Instance.new("UIGradient").Parent = back'),
        }
        for name, (path, old, new) in static_mutants.items():
            text = read(path)
            assert text.count(old) == 1, 'mutant anchor must match once: %s' % name
            if not static_checks({path: text.replace(old, new)}):
                raise SystemExit('mutant NOT caught: ' + name)
            caught += 1
    print('Menu window passed: rules at 3 screen sizes, Featured weekly pick, source guards, %d mutants caught' % caught)


if __name__ == '__main__':
    main()
