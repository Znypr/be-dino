"""Menu proposal sheet (docs/243): every Be Dino window in the grammar the top Roblox games share. Decision aid, not game art.

    python tools/menu_study_mock.py <dino cutout folder> <out.html> [<today picture>]
    # render: msedge --headless=new --screenshot=<out.png> --window-size=1920,<height printed> file:///<out.html>

Only the game's own art: the Toybox kit (resources/ui/v2/toybox/final: coloured glossy headers, the dark stud tile, rarity cards,
coloured buttons, the red X), icons and items in resources/ui/v2, egg pictures in resources/ui/v2/stage/eggs and the owner's V3 dino
cutouts (folder on the command line; they live in the main checkout). Numbers and names are examples, not balance. No paid line,
no Robux price anywhere (docs/43). The rules the panels follow are docs/243 section 2 (G1-G10).
"""
import base64
import io
import sys
from PIL import Image

DINOS, OUT = sys.argv[1].rstrip("/\\") + "/", sys.argv[2]
CUR = sys.argv[3] if len(sys.argv) > 3 else "docs/evidence/2026-11-17-final-checks/phone-828x374-potion-shop.jpg"
K, I, IT, EG = "resources/ui/v2/toybox/final/", "resources/ui/v2/icons/", "resources/ui/v2/items/", "resources/ui/v2/stage/eggs/"


def u(path, maxs=None):
    im = Image.open(path).convert("RGBA")
    if maxs:
        im.thumbnail((maxs, maxs))
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


A = {}
for n in ["header-blue", "header-green", "header-purple", "header-amber", "header-red", "header-dark", "studs-tile", "card-common",
          "card-uncommon", "card-rare", "card-epic", "card-legendary", "card-mythic", "button-green", "button-grey", "button-gold",
          "button-blue", "button-purple", "button-red", "button-dark", "close"]:
    A[n] = u(K + n + ".png")
ICONS = ["notify-crystal-v1", "egg-green-spotted-v1", "fusion", "index-tab-colours-v1", "index-tab-patterns-v1", "shop-tab-auras-v1",
         "shop-tab-trails-v1", "shop-tab-conditions-v1", "station-potions-v1", "egg-nest-single-v1", "egg-nest-v1", "station-index-v1",
         "station-fusion-v1", "station-nests-v1", "station-settings-v1", "station-style-v1", "shop-tile-eggs-v1", "shop-tile-auras-v1",
         "shop-tile-trails-v1", "shop-tile-conditions-v1", "trophy", "home", "class-ground-v1", "mutation-ember-v1", "mutation-frost-v1",
         "mutation-aurora-v1", "notify-star-v1", "notify-level-v1", "trail-fern-v2", "trail-tidal-v2", "trail-ember-v2", "trail-solar-v2",
         "trail-nova-v2", "trail-astra-v2", "rarity-common-v1", "rarity-uncommon-v1", "rarity-rare-v1", "rarity-epic-v1",
         "rarity-legendary-v1", "rarity-mythic-v1", "weather-clear-v1", "paint-bucket-v1", "shield", "hud-heart-v1", "leap-v1"]
for n in ICONS:
    A[n] = u(I + n + ".png", 180)
for n in ["potion-growth-sip", "potion-lucky-sip", "potion-raptor-rush", "potion-hearty-brew", "potion-behemoth-brew", "potion-jackpot-elixir",
          "aura-meadow-v2", "aura-tidal-v2", "aura-royal-v2", "food-berry-v1", "food-fruit-v1", "food-egg-v1", "food-amber-v1"]:
    A[n] = u(IT + n + ".png", 220)
for n in ["egg-02_dirty", "egg-03_normal", "egg-04_rainbow", "egg-05_astra"]:
    A[n] = u(EG + n + ".png", 240)
for n in ["compy", "raptor", "triceratops", "stegosaurus", "ankylosaurus", "brachiosaurus", "dodo", "baryonyx", "t-rex", "spinosaurus",
          "parasaurolophus", "pteranodon"]:
    try:
        A[n] = u(DINOS + n + ".png", 300)
    except FileNotFoundError:
        A[n] = ""

CSS = """
*{box-sizing:border-box}body{margin:0;background:#1d2a1f;font-family:Fredoka,sans-serif;color:#fff}
h1{font:700 40px Fredoka;color:#ffe9a8;margin:28px 28px 4px}.sub{font:500 20px Fredoka;color:#d8e6cf;margin:0 28px 6px}
.page{display:grid;grid-template-columns:1fr 1fr;gap:26px 28px;padding:20px 28px 28px;width:1920px}
.lbl{font:600 22px Fredoka;color:#ffe9a8;margin:0 0 8px 4px}.lbl span{color:#9fd08a;font-weight:500;font-size:17px}
.scr{position:relative;width:930px;height:523px;border-radius:14px;overflow:hidden;
 background:linear-gradient(#8fd6f5 0,#bfe9ff 38%,#7bc35a 38%,#5aa340 100%)}
.scr:before{content:"";position:absolute;inset:0;background:radial-gradient(ellipse at 30% 75%,#4f9638 0 18%,transparent 19%),radial-gradient(ellipse at 80% 70%,#3f8a2f 0 14%,transparent 15%)}
.cur:before{display:none}
.ol{text-shadow:2px 2px 0 #14161f,-2px 2px 0 #14161f,2px -2px 0 #14161f,-2px -2px 0 #14161f,0 3px 0 #14161f}
.win{position:absolute;border-radius:16px;background:#2c2f40;border:5px solid #14161f;box-shadow:0 8px 0 rgba(0,0,0,.35)}
.body{position:absolute;inset:62px 10px 10px 10px;border-radius:10px;background-color:#3a3d52;background-size:44px 44px}
.hdr{position:absolute;left:6px;right:6px;top:6px;height:52px;border-radius:10px;background-size:100% 100%;display:flex;align-items:center;padding:0 14px;gap:10px}
.hdr img{height:50px;margin-top:-16px;filter:drop-shadow(0 3px 0 #14161f)}
.hdr .t{font:700 30px Fredoka;letter-spacing:.5px}
.x{position:absolute;right:12px;top:10px;width:44px;height:44px;background-size:100% 100%}
.card{position:absolute;border-radius:12px;background-size:100% 100%;text-align:center}
.card .n{font:700 15px Fredoka;margin-top:6px}.card .r{font:700 13px Fredoka}
.card img{display:block;margin:2px auto 0;filter:drop-shadow(0 4px 0 rgba(0,0,0,.35))}
.btn{position:absolute;border-radius:10px;background-size:100% 100%;font:700 18px Fredoka;display:flex;align-items:center;justify-content:center;gap:6px}
.btn img{height:24px}
.pill{position:absolute;border-radius:999px;background:#14161f;font:700 15px Fredoka;padding:4px 12px;display:flex;gap:6px;align-items:center;white-space:nowrap}
.pill img{height:20px}
.tab{position:absolute;width:76px;height:76px;border-radius:14px;border:4px solid #14161f;display:flex;flex-direction:column;align-items:center;justify-content:center;font:700 13px Fredoka}
.tab img{height:40px}
.sect{position:absolute;left:0;right:0;text-align:center;font:700 20px Fredoka;color:#ffd84a}
.bar{position:absolute;height:40px;border-radius:12px;background:#14161f;border:3px solid #14161f;overflow:hidden}
.bar i{position:absolute;left:0;top:0;bottom:0;border-radius:9px;background:linear-gradient(#7fd8ff,#2f9fe0)}
.bar i.g{background:linear-gradient(#b8ff7a,#4fc522)}
.bar b{position:relative;display:block;text-align:center;font:700 20px Fredoka;line-height:34px}
.plate{position:absolute;border-radius:10px;background:#252838;border:3px solid #14161f;display:flex;align-items:center;gap:10px;padding:0 12px;font:700 18px Fredoka}
.plate img{height:34px}.plate .v{margin-left:auto;font-size:22px}
.lock{filter:brightness(0) opacity(.55)!important}
.note{position:absolute;left:12px;bottom:10px;font:600 14px Fredoka;color:#fff;background:rgba(0,0,0,.5);padding:3px 10px;border-radius:8px}
.big{position:absolute;font:700 46px Fredoka}
.dim{position:absolute;inset:0;background:rgba(0,0,0,.25)}
"""
RAR = [("Common", "card-common", "#e9eef5"), ("Uncommon", "card-uncommon", "#9dff6b"), ("Rare", "card-rare", "#7fe4ff"),
       ("Epic", "card-epic", "#e9a6ff"), ("Legendary", "card-legendary", "#ffe066"), ("Mythic", "card-mythic", "#ff9db0")]


def bg(name):
    return "background-image:url(" + A[name] + ")"


def win(x, y, w, h, header, title, icon, inner):
    return ('<div class="win" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx">' % (x, y, w, h)
            + '<div class="hdr" style="' + bg(header) + '"><img src="' + A[icon] + '"><span class="t ol">' + title + '</span></div>'
            + '<div class="x" style="' + bg("close") + '"></div>'
            + '<div class="body" style="' + bg("studs-tile") + '">' + inner + "</div></div>")


def card(x, y, w, h, rar, name, art, size, extra="", lock=False, word=True):
    r = RAR[rar]
    return ('<div class="card" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx;%s">' % (x, y, w, h, bg(r[1]))
            + '<div class="n ol">' + (name if not lock else "???") + "</div>"
            + ('<img src="' + A[art] + '" style="height:%dpx" class="%s">' % (size, "lock" if lock else "") if art else "")
            + ('<div class="r ol" style="color:' + r[2] + '">' + r[0] + "</div>" if word else "") + extra + "</div>")


def btn(x, y, w, h, kind, words, icon=None, size=18):
    return ('<div class="btn ol" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx;font-size:%dpx;%s">' % (x, y, w, h, size, bg(kind))
            + ('<img src="' + A[icon] + '">' if icon else "") + words + "</div>")


def tab(x, y, colour, icon, word, on=False):
    return ('<div class="tab ol" style="left:%dpx;top:%dpx;background:%s;%s"><img src="%s">%s</div>'
            % (x, y, colour, "outline:4px solid #fff;outline-offset:-9px" if on else "", A[icon], word))


def pill(x, y, words, icon=None, colour="#fff", right=False):
    side = "right" if right else "left"
    return ('<div class="pill ol" style="%s:%dpx;top:%dpx;color:%s">' % (side, x, y, colour)
            + ('<img src="' + A[icon] + '">' if icon else "") + words + "</div>")


def plate(x, y, w, h, icon, words, value="", vcolour="#fff"):
    return ('<div class="plate ol" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx">' % (x, y, w, h)
            + ('<img src="' + A[icon] + '">' if icon else "") + words + '<span class="v" style="color:%s">%s</span></div>' % (vcolour, value))


def bar(x, y, w, frac, words, green=False):
    return ('<div class="bar" style="left:%dpx;top:%dpx;width:%dpx"><i class="%s" style="width:%d%%"></i><b class="ol">%s</b></div>'
            % (x, y, w, "g" if green else "", int(frac * 100), words))


def scr(inner, note, extra_class=""):
    return '<div class="scr ' + extra_class + '">' + inner + '<div class="note">' + note + "</div></div>"


P = []  # (label, sub, html)

# 1 Dino Index
cards = ""
for i, (d, r, lock) in enumerate([("compy", 0, False), ("dodo", 0, False), ("raptor", 1, False), ("stegosaurus", 2, False),
                                  ("triceratops", 3, True), ("ankylosaurus", 2, False), ("baryonyx", 4, True), ("brachiosaurus", 5, True)]):
    cards += card(146 + (i % 4) * 106, 10 + (i // 4) * 150, 100, 142, r, d.capitalize(), d, 84, lock=lock)
index = win(24, 26, 790, 470, "header-blue", "Dino Index", "station-index-v1",
            '<div class="card" style="left:10px;top:10px;width:128px;height:292px;background:linear-gradient(#6fbf4a,#2f7a2a);border:4px solid #14161f">'
            '<div class="n ol" style="font-size:20px;margin-top:10px">Meadow</div><img src="' + A["egg-nest-single-v1"] + '" style="height:70px;margin-top:30px">'
            '<div class="ol" style="font:700 16px Fredoka;margin-top:40px">Find all:</div><div class="ol" style="font:700 18px Fredoka;color:#ffd84a">+50 crystals</div></div>'
            + cards + card(574, 10, 180, 200, 1, "Raptor", "raptor", 120)
            + btn(582, 222, 164, 44, "button-gold", "CLAIM ALL") + btn(582, 274, 164, 44, "button-blue", "Variants 2/6")
            + bar(10, 316, 744, .26, "Found: 14 / 55"))
P.append(("Dino Index", "rarity cards, ??? silhouettes, region reward, fat progress",
          scr(index + tab(826, 70, "#3fa9f5", "index-tab-colours-v1", "Colours") + tab(826, 152, "#c45cf0", "index-tab-patterns-v1", "Patterns"),
              "Tabs sit outside the window; the world stays visible")))

# 2 Dino detail
detail = win(70, 26, 780, 470, "header-blue", "T-Rex", "station-index-v1",
             card(10, 10, 300, 330, 4, "T-Rex", "t-rex", 200, '<div class="ol" style="font:700 18px Fredoka;margin-top:8px">Gold &middot; Size 3</div>')
             + plate(326, 10, 410, 52, "class-ground-v1", "Class", "Ground")
             + plate(326, 72, 410, 52, "notify-level-v1", "Size", "3 of 5")
             + plate(326, 134, 410, 74, None, "Looks",
                     '<img src="' + A["mutation-ember-v1"] + '" style="height:44px"> <img src="' + A["mutation-frost-v1"] + '" style="height:44px"> <img src="' + A["mutation-aurora-v1"] + '" style="height:44px">')
             + bar(326, 220, 410, .5, "3 of 6 for Diamond", True)
             + btn(326, 278, 196, 60, "button-green", "EQUIP", size=24) + btn(540, 278, 196, 60, "button-purple", "FUSE", "fusion", 24))
P.append(("Dino detail", "the dino big on its rarity card, facts as dark plates, two actions",
          scr(detail, "Rarity fills the card; each fact gets an icon")))

# 3 Eggs (nests)
nests = ""
for i, (state, col) in enumerate([("Ready!", "#9dff6b"), ("3 min", "#fff"), ("Empty", "#aab"), ("Empty", "#aab"), ("Locked", "#ff9db0")]):
    art = "egg-nest-v1" if i < 2 else "egg-nest-single-v1"
    nests += ('<div class="card" style="left:%dpx;top:40px;width:140px;height:128px;%s"><img src="%s" style="height:74px;margin-top:8px;%s"><div class="ol" style="font:700 17px Fredoka;color:%s">%s</div></div>'
              % (10 + i * 150, bg("card-uncommon" if i == 0 else "card-common"), A[art], "filter:grayscale(1) opacity(.5)" if i >= 2 else "", col, state))
eggs = win(60, 20, 800, 482, "header-amber", "Eggs", "egg-green-spotted-v1",
           '<div class="sect ol" style="top:6px;text-align:left;left:12px">Nests <span style="color:#fff">2 / 5</span></div>'
           + pill(12, 6, "Lucky nests open one at a time", colour="#ffd84a", right=True) + nests
           + card(10, 182, 220, 200, 2, "Normal Egg", "egg-03_normal", 130)
           + '<div class="big ol" style="left:250px;top:186px;font-size:34px">Egg 1 of 3</div>'
           + '<div class="ol" style="position:absolute;left:252px;top:232px;font:700 18px Fredoka;color:#7fe4ff">Shell: Dirty &middot; Rare</div>'
           + btn(250, 270, 510, 64, "button-green", "OPEN EGG", size=28) + btn(250, 342, 200, 40, "button-grey", "Auto: off"))
P.append(("Eggs and nests", "nest slots as cards with live state, the egg big, one huge OPEN",
          scr(eggs, "Live state on every nest (Ready! / 3 min / Locked)")))

# 4 Shop landing
tiles = ""
for i, (icon, word, colour) in enumerate([("shop-tile-eggs-v1", "Eggs", "#ffd84a"), ("shop-tile-auras-v1", "Auras", "#ff7a6b"),
                                         ("shop-tile-trails-v1", "Trails", "#7fd8ff"), ("shop-tile-conditions-v1", "Colours", "#c98bff")]):
    tiles += ('<div class="card" style="left:%dpx;top:204px;width:178px;height:178px;background:%s;border:4px solid #14161f">'
              '<img src="%s" style="height:110px;margin-top:6px"><div class="ol" style="font:700 22px Fredoka">%s</div></div>' % (10 + i * 188, colour, A[icon], word))
shop = win(70, 20, 780, 482, "header-green", "Shop", "shop-tile-eggs-v1",
           '<div class="sect ol" style="top:4px">-- FEATURED --</div>'
           '<div class="card" style="left:10px;top:34px;width:744px;height:160px;' + bg("card-mythic") + '">'
           '<img src="' + A["egg-04_rainbow"] + '" style="position:absolute;left:24px;top:8px;height:140px">'
           '<div class="ol" style="position:absolute;left:180px;top:20px;font:700 34px Fredoka">Rainbow Egg</div>'
           '<div class="ol" style="position:absolute;left:182px;top:66px;font:700 18px Fredoka;color:#ffe066">Mythic dinos inside!</div></div>'
           + pill(24, 46, "New in 2 h", colour="#9dff6b", right=True) + btn(540, 124, 200, 54, "button-green", "500", "notify-crystal-v1", 24)
           + tiles + pill(12, 4, "1,250", "notify-crystal-v1"))
P.append(("Shop (landing)", "one featured offer on top, big coloured tiles below",
          scr(shop, "Featured banner + tiles in their own colours; crystals only, no Robux")))

# 5 Egg chances
rows = ""
for i, (r, odds, dino) in enumerate([(0, "1 in 2", "compy"), (1, "1 in 4", "raptor"), (2, "1 in 8", "stegosaurus"),
                                     (3, "1 in 20", "triceratops"), (4, "1 in 60", "t-rex"), (5, "1 in 250", "spinosaurus")]):
    rr = RAR[r]
    rows += ('<div class="card" style="left:%dpx;top:%dpx;width:366px;height:62px;%s">'
             '<img src="%s" style="position:absolute;left:8px;top:4px;height:54px;margin:0" class="%s">'
             '<div class="ol" style="position:absolute;left:78px;top:16px;font:700 22px Fredoka;color:%s">%s</div>'
             '<div class="ol" style="position:absolute;right:14px;top:12px;font:700 26px Fredoka">%s</div></div>'
             % (10 + (i // 3) * 376, 50 + (i % 3) * 72, bg(rr[1]), A[dino], "lock" if r >= 4 else "", rr[2], rr[0], odds))
chances = win(70, 24, 780, 474, "header-amber", "Egg chances", "egg-green-spotted-v1",
              plate(10, 4, 742, 40, "egg-green-spotted-v1", "Normal Egg: what can hatch", "")
              + rows + btn(10, 280, 360, 64, "button-green", "OPEN 1 &middot; 100", "notify-crystal-v1", 24)
              + btn(386, 280, 180, 64, "button-grey", "Exact %") + btn(582, 280, 170, 64, "button-blue", "OPEN 3", size=22))
P.append(("Egg chances", "every rarity on its own colour, kid odds in big numbers",
          scr(chances, "Odds always one tap away (docs/43); rare ones as silhouettes")))

# 6 Potion Shop
pc = ""
for i, (art, r, name, line, price) in enumerate([("potion-growth-sip", 0, "Growth Sip", "+25% grow", 25), ("potion-lucky-sip", 1, "Lucky Sip", "+10% luck", 30),
                                                 ("potion-raptor-rush", 2, "Raptor Rush", "+30% speed", 45), ("potion-hearty-brew", 3, "Hearty Brew", "+40% grow", 80),
                                                 ("potion-behemoth-brew", 4, "Behemoth Brew", "+75% grow", 150), ("potion-jackpot-elixir", 5, "Jackpot", "x2 eggs", 300)]):
    x, y = 12 + (i % 3) * 196, 46 + (i // 3) * 176
    pc += card(x, y, 186, 168, r, name, art, 70, '<div class="ol" style="font:700 14px Fredoka">' + line + "</div>")
    pc += btn(x + 18, y + 128, 150, 34, "button-green", str(price), "notify-crystal-v1")
potions = win(130, 20, 640, 482, "header-purple", "Potion Shop", "station-potions-v1",
              pill(12, 8, "1,250", "notify-crystal-v1") + pill(12, 8, "New potions in 4 min", colour="#9dff6b", right=True) + pc)
P.append(("Potion Shop", "a price button on every card, restock line in the top row",
          scr(potions + tab(44, 60, "#9b5cf0", "station-potions-v1", "Potions", True) + tab(44, 142, "#f0b23a", "shop-tab-auras-v1", "Auras")
              + tab(44, 224, "#3fa9f5", "shop-tab-trails-v1", "Trails") + tab(44, 306, "#c98bff", "shop-tab-conditions-v1", "Colours"),
              "Shop tabs as big tiles left of the window")))

# 7 Auras
ac = ""
for i, (art, r, name, line, state) in enumerate([("aura-meadow-v2", 0, "Meadow", "+5% grow", "EQUIPPED"), ("aura-tidal-v2", 2, "Tidal", "+10% speed", "EQUIP"),
                                                 ("aura-royal-v2", 4, "Royal", "+20% luck", "300"), (None, 5, "Mythic", "???", "Locked")]):
    x = 10 + i * 186
    ac += card(x, 10, 176, 300, r, name if art else "???", art, 150, '<div class="ol" style="font:700 17px Fredoka;margin-top:6px">' + (line if art else "") + "</div>", word=bool(art))
    if art is None:
        ac += '<div class="ol" style="position:absolute;left:%dpx;top:90px;width:176px;text-align:center;font:700 80px Fredoka;color:#14161f;text-shadow:none">?</div>' % x
    kind = {"EQUIPPED": "button-grey", "EQUIP": "button-green", "Locked": "button-dark"}.get(state, "button-green")
    ac += btn(x + 12, 318, 152, 50, kind, state, "notify-crystal-v1" if state.isdigit() else None, 20)
auras = win(70, 26, 768, 470, "header-red", "Auras", "shop-tab-auras-v1", ac)
P.append(("Auras", "big aura art on rarity cards, Equip / Equipped / price on each",
          scr(auras + tab(844, 70, "#f0b23a", "shop-tab-auras-v1", "Auras", True) + tab(844, 152, "#3fa9f5", "shop-tab-trails-v1", "Trails"),
              "Equipped is grey, everything you can do is green")))

# 8 Trails
tc = ""
for i, (art, r, name, price) in enumerate([("trail-fern-v2", 0, "Fern", "OWNED"), ("trail-tidal-v2", 1, "Tidal", "60"), ("trail-ember-v2", 2, "Ember", "120"),
                                           ("trail-solar-v2", 3, "Solar", "250"), ("trail-nova-v2", 4, "Nova", "500"), ("trail-astra-v2", 5, "Astra", "900")]):
    x, y = 10 + (i % 3) * 248, 10 + (i // 3) * 182
    tc += ('<div class="card" style="left:%dpx;top:%dpx;width:238px;height:172px;%s"><div class="n ol" style="font-size:18px">%s</div>'
           '<img src="%s" style="height:72px"><div class="r ol" style="color:%s">%s</div></div>' % (x, y, bg(RAR[r][1]), name, A[art], RAR[r][2], RAR[r][0]))
    tc += btn(x + 49, y + 128, 140, 36, "button-grey" if price == "OWNED" else "button-green", price, None if price == "OWNED" else "notify-crystal-v1", 16)
trails = win(70, 26, 768, 470, "header-blue", "Trails", "shop-tab-trails-v1", tc)
P.append(("Trails", "same card grammar as Auras, the trail picture in the middle",
          scr(trails + tab(844, 70, "#f0b23a", "shop-tab-auras-v1", "Auras") + tab(844, 152, "#3fa9f5", "shop-tab-trails-v1", "Trails", True),
              "One card grammar for every shop")))

# 9 Fusion
slots = "".join('<div class="card" style="left:%dpx;top:48px;width:180px;height:120px;%s"><div class="n ol">Raptor</div><img src="%s" style="height:76px"></div>'
                % (34 + i * 200, bg("card-rare"), A["raptor"]) for i in range(3))
fusion = win(110, 22, 700, 480, "header-purple", "Fusion", "fusion",
             '<div class="sect ol" style="top:12px;color:#fff">Bring <span style="color:#ff6b6b">3</span> same dinos: the best one <span style="color:#9dff6b">grows a size</span>!</div>'
             + slots + '<div style="position:absolute;left:122px;top:168px;width:400px;height:26px;border:8px solid #14161f;border-top:none;border-radius:0 0 14px 14px"></div>'
             '<div style="position:absolute;left:318px;top:168px;width:8px;height:34px;background:#14161f"></div>'
             '<div class="card" style="left:252px;top:200px;width:140px;height:112px;' + bg("card-legendary") + '"><div class="n ol">Gold Raptor</div><img src="'
             + A["raptor"] + '" style="height:70px;filter:sepia(1) saturate(4) hue-rotate(-10deg) drop-shadow(0 4px 0 rgba(0,0,0,.35))"></div>'
             + btn(212, 326, 220, 50, "button-green", "FUSE!", size=24))
P.append(("Fusion", "the whole rule told with pictures, one big FUSE", scr(fusion, "Slots, lines and the result you will get")))

# 10 Home (Sanctuary)
home = win(70, 26, 780, 470, "header-green", "Sanctuary", "home",
           card(10, 10, 300, 300, 0, "Compy", "compy", 220, '<div class="ol" style="font:700 16px Fredoka">Level 4</div>')
           + plate(326, 10, 410, 56, "egg-green-spotted-v1", "Eggs to open", "3", "#9dff6b")
           + plate(326, 76, 410, 56, "egg-nest-single-v1", "Nests", "2 of 5")
           + plate(326, 142, 410, 56, "trophy", "Best size", "4")
           + btn(326, 214, 410, 96, "button-green", "EXPLORE!", size=36)
           + btn(10, 320, 300, 50, "button-gold", "OPEN EGGS", "egg-green-spotted-v1", 22) + btn(326, 320, 410, 50, "button-blue", "Change dino", size=22))
P.append(("Home (Sanctuary)", "your dino big, three facts, a giant EXPLORE", scr(home, "The main action is the biggest thing in the window")))

# 11 Run complete
eggrow = "".join('<img src="%s" style="position:absolute;left:%dpx;top:96px;height:110px">' % (A["egg-03_normal" if i < 2 else "egg-04_rainbow"], 360 + i * 120) for i in range(3))
runend = win(90, 26, 740, 470, "header-amber", "Great run!", "trophy",
             '<img src="' + A["trophy"] + '" style="position:absolute;left:40px;top:8px;height:190px;filter:drop-shadow(0 6px 0 rgba(0,0,0,.35))">'
             + '<div class="sect ol" style="top:16px;left:340px;right:auto;color:#fff;font-size:26px">You found <span style="color:#ffd84a">3 eggs!</span></div>' + eggrow
             + plate(10, 222, 330, 56, "notify-crystal-v1", "Crystals", "+35", "#ffd84a") + plate(10, 286, 330, 56, "notify-star-v1", "Growth", "+120", "#9dff6b")
             + plate(350, 222, 360, 56, "egg-nest-single-v1", "Nest eggs", "+1") + plate(350, 286, 360, 56, "notify-level-v1", "Streak", "2 days")
             + btn(10, 352, 420, 46, "button-green", "OPEN EGGS", "egg-green-spotted-v1", 24) + btn(440, 352, 270, 46, "button-grey", "HOME", "home", 22))
P.append(("Run complete", "eggs as pictures, big numbers, open right away", scr(runend, "What you got, shown, not listed")))

# 12 Defeat
defeat = win(150, 40, 620, 440, "header-amber", "Oops! Good try!", "hud-heart-v1",
             '<div class="sect ol" style="top:16px;color:#9dff6b;font-size:30px">Your eggs are safe!</div>'
             + "".join('<img src="%s" style="position:absolute;left:%dpx;top:70px;height:120px">' % (A["egg-03_normal"], 150 + i * 110) for i in range(2))
             + plate(10, 214, 584, 52, "notify-crystal-v1", "Crystals kept", "+12", "#ffd84a")
             + '<div class="ol" style="position:absolute;left:0;right:0;top:282px;text-align:center;font:700 20px Fredoka">Eat more, grow bigger, and the big ones leave you alone.</div>'
             + btn(170, 314, 260, 50, "button-green", "PLAY AGAIN", size=24))
P.append(("Defeat", "gentle: the good news first, eggs shown safe", scr(defeat, "Never scary; the green line is the first thing you read")))

# 13 Settings
srows = ""
for i, (icon, word, val) in enumerate([("station-settings-v1", "Everything", .8), ("notify-star-v1", "Sounds", .7), ("weather-clear-v1", "Weather", .6)]):
    srows += plate(10, 10 + i * 66, 744, 56, icon, word, "")
    srows += '<div style="position:absolute;left:250px;top:%dpx;width:400px;height:18px;border-radius:9px;background:#14161f"><div style="width:%d%%;height:100%%;border-radius:9px;background:linear-gradient(#b8ff7a,#4fc522)"></div></div>' % (29 + i * 66, int(val * 100))
    srows += '<div style="position:absolute;left:%dpx;top:%dpx;width:34px;height:34px;border-radius:50%%;background:#ffd84a;border:4px solid #14161f"></div>' % (250 + int(400 * val) - 17, 21 + i * 66)
    srows += '<div class="ol" style="position:absolute;left:672px;top:%dpx;font:700 20px Fredoka">%d%%</div>' % (25 + i * 66, int(val * 100))
settings = win(130, 26, 784, 470, "header-dark", "Settings", "station-settings-v1",
               srows + plate(10, 208, 744, 56, "leap-v1", "Reduce motion", "") + btn(560, 214, 180, 44, "button-grey", "OFF")
               + plate(10, 274, 744, 56, "paint-bucket-v1", "Food guide", "") + btn(560, 280, 180, 44, "button-green", "OPEN"))
P.append(("Settings", "tabs as tiles, each row a dark plate with its icon",
          scr(settings + tab(40, 60, "#3fa9f5", "notify-star-v1", "Sound", True) + tab(40, 142, "#c98bff", "paint-bucket-v1", "Look")
              + tab(40, 224, "#f0b23a", "leap-v1", "Controls") + tab(40, 306, "#9dff6b", "egg-green-spotted-v1", "Help"),
              "Settings stays calm: dark header, no rarity colours")))

# 14 Food guide
fc = ""
for i, (art, r, name, grow) in enumerate([("food-berry-v1", 0, "Berries", "+1"), ("food-fruit-v1", 1, "Fruit", "+4"), ("food-egg-v1", 2, "Eggs", "+15"), ("food-amber-v1", 4, "Amber", "+50")]):
    fc += card(10 + i * 186, 10, 176, 250, r, name, art, 130, '<div class="ol" style="font:700 22px Fredoka;color:#9dff6b;margin-top:4px">' + grow + " grow</div>", word=False)
food = win(80, 30, 768, 460, "header-green", "Food &amp; growth", "food-berry-v1",
           fc + '<div class="plate ol" style="left:10px;top:272px;width:744px;height:56px;display:block;text-align:center;line-height:50px">Eat 500 food for about <span style="color:#ffd84a">12 eggs</span>. Storms add more!</div>'
           + btn(274, 340, 220, 44, "button-green", "GOT IT!", size=22))
P.append(("Food guide", "the food big on cards from plain to rare", scr(food, "Rarer food = rarer card colour")))

# 15 Buy confirm (small window over a dimmed screen)
confirm = ('<div class="dim"></div>' + win(255, 92, 420, 340, "header-amber", "Buy egg?", "egg-green-spotted-v1",
           card(10, 10, 150, 180, 2, "Normal Egg", "egg-03_normal", 110)
           + '<div class="ol" style="position:absolute;left:176px;top:20px;font:700 22px Fredoka">Random dino</div>'
           + '<div class="ol" style="position:absolute;left:176px;top:56px;font:700 18px Fredoka;color:#7fe4ff">Chances: 1 tap</div>'
           + '<div class="ol" style="position:absolute;left:176px;top:104px;font:700 30px Fredoka;color:#ffd84a"><img src="' + A["notify-crystal-v1"] + '" style="height:30px;vertical-align:-4px"> 100</div>'
           + btn(10, 204, 190, 54, "button-green", "BUY", size=24) + btn(210, 204, 180, 54, "button-grey", "CANCEL", size=22)))
P.append(("Confirm popup", "small, the thing you buy as a picture, BUY green / CANCEL grey", scr(confirm, "The only window that dims the world a little")))

# 16 Codes
codes = win(150, 40, 620, 440, "header-purple", "Codes", "notify-star-v1",
            '<div class="ol" style="position:absolute;left:14px;top:12px;font:700 22px Fredoka">Got a code?</div>'
            '<div style="position:absolute;left:12px;top:46px;width:420px;height:56px;border-radius:12px;background:#fff;border:4px solid #14161f;color:#9a8f7a;font:600 22px Fredoka;padding:12px 16px">Type it here</div>'
            + btn(446, 46, 138, 56, "button-green", "GO!", size=24)
            + card(12, 120, 572, 180, 4, "Group gift", "trophy", 100, '<div class="ol" style="font:700 16px Fredoka">Join our group, then open it for 50 crystals!</div>', word=False)
            + btn(212, 312, 172, 50, "button-green", "OPEN", size=22))
P.append(("Codes and gifts", "a white box to type in, the gift as a golden card", scr(codes, "Kid words, one box, one gift")))

# 17 Today (for comparison)
cur = Image.open(CUR).convert("RGB")
cur.thumbnail((930, 523))
_b = io.BytesIO()
cur.save(_b, "JPEG", quality=80)
today = ('<div class="scr cur" style="background:#000 url(data:image/jpeg;base64,' + base64.b64encode(_b.getvalue()).decode() + ') center/contain no-repeat">'
         '<div class="note">Today: our Potion Shop in Studio (cream body filling the screen, every card the same colour)</div></div>')
P.append(("Today, for comparison", "Studio capture 2026-11-17", today))

# 18 The rules
rules = ('<div class="scr cur" style="background:#2c2f40;padding:26px 34px;font:600 19px Fredoka;line-height:1.45">'
         '<div style="font:700 26px Fredoka;color:#ffe9a8;margin-bottom:8px">The rules every window follows (docs/243)</div>'
         'G1 About 70% of the screen wide; the world stays visible (only a confirm dims it).<br>'
         'G2 Each menu has its own header colour and its icon; title big, outlined, left.<br>'
         'G3 Dark studded body so the colours pop; cream only for small text plates.<br>'
         'G4 Rarity colour fills the card; locked things are ??? silhouettes.<br>'
         'G5 Every card has its own button: green = you can do it, grey = done, dark = locked.<br>'
         'G6 Tabs are big icon tiles outside the window.<br>'
         'G7 Progress in huge outlined numbers and fat bars.<br>'
         'G8 Live info in the top row: crystals, restock time.<br>'
         'G9 Red square X top right. Text at least 14 px, buttons at least 44 px on a phone.<br>'
         'G10 No Robux, no countdown pressure, odds one tap away.</div>')
P.append(("The rules", "what changes compared with docs/240", rules))

BODY = ('<h1>Be Dino: every menu in the top-game look (proposal)</h1><div class="sub">Built only from our own kit, icons and V3 dino art. '
        'Numbers are examples, not balance. The hatch stays a full stage (not a window). docs/243, BD-1252 to BD-1257.</div><div class="page">'
        + "".join('<div><div class="lbl">%d. %s <span>%s</span></div>%s</div>' % (i + 1, l, s, h) for i, (l, s, h) in enumerate(P)) + "</div>")
html = ('<!doctype html><html><head><meta charset="utf-8"><link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&display=swap" rel="stylesheet">'
        "<style>" + CSS + "</style></head><body>" + BODY + "</body></html>")
open(OUT, "w", encoding="utf-8").write(html)
rows_n = (len(P) + 1) // 2
print("height", 130 + rows_n * 583)
