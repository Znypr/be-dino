"""Menu study mockups (docs/243): Be Dino windows in the grammar the top Roblox games share. Decision aid, not game art.

    python tools/menu_study_mock.py <dino cutout folder> <out.html>
    # then render: msedge --headless --screenshot=<out.png> --window-size=1920,1180 file:///<out.html>

Uses only the game's own art: the Toybox kit (resources/ui/v2/toybox/final: coloured glossy headers, the dark stud tile, rarity cards,
coloured buttons, the red X), item and icon art in resources/ui/v2, and the owner's V3 dino cutouts (folder given on the command line,
they live in the main checkout). Numbers and names are examples, not balance. Every paid line stays off: no Robux prices are shown.
"""
import base64
import io
import sys
from PIL import Image

DINOS, OUT = sys.argv[1].rstrip("/\\") + "/", sys.argv[2]
K, I, IT = "resources/ui/v2/toybox/final/", "resources/ui/v2/icons/", "resources/ui/v2/items/"


def u(path, maxs=None):
    im = Image.open(path).convert("RGBA")
    if maxs:
        im.thumbnail((maxs, maxs))
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


A = {n: u(K + n + ".png") for n in ["header-blue", "header-green", "header-purple", "header-amber", "studs-tile", "card-common",
                                     "card-uncommon", "card-rare", "card-epic", "card-legendary", "card-mythic", "button-green",
                                     "button-grey", "button-gold", "button-blue", "button-purple", "close"]}
for n in ["notify-crystal-v1", "egg-green-spotted-v1", "fusion", "index-tab-colours-v1", "index-tab-patterns-v1", "shop-tab-auras-v1",
          "shop-tab-trails-v1", "shop-tab-crystals-v1", "station-potions-v1", "egg-nest-single-v1"]:
    A[n] = u(I + n + ".png", 160)
for n in ["potion-growth-sip", "potion-lucky-sip", "potion-raptor-rush", "potion-hearty-brew", "potion-behemoth-brew", "potion-jackpot-elixir"]:
    A[n] = u(IT + n + ".png", 200)
for n in ["compy", "raptor", "triceratops", "stegosaurus", "ankylosaurus", "brachiosaurus", "dodo", "baryonyx", "dimorphodon"]:
    try:
        A[n] = u(DINOS + n + ".png", 260)
    except FileNotFoundError:
        A[n] = ""

CSS = """
*{box-sizing:border-box}body{margin:0;background:#1d2a1f;font-family:Fredoka,sans-serif;color:#fff}
.page{display:grid;grid-template-columns:1fr 1fr;gap:28px;padding:28px;width:1920px}
.lbl{font:600 22px Fredoka;color:#ffe9a8;margin:0 0 8px 4px}
.scr{position:relative;width:930px;height:523px;border-radius:14px;overflow:hidden;
 background:linear-gradient(#8fd6f5 0,#bfe9ff 38%,#7bc35a 38%,#5aa340 100%)}
.scr:before{content:"";position:absolute;inset:0;background:radial-gradient(ellipse at 30% 75%,#4f9638 0 18%,transparent 19%),radial-gradient(ellipse at 80% 70%,#3f8a2f 0 14%,transparent 15%)}
.ol{text-shadow:0 0 0 #000,2px 2px 0 #14161f,-2px 2px 0 #14161f,2px -2px 0 #14161f,-2px -2px 0 #14161f,0 3px 0 #14161f}
.win{position:absolute;border-radius:16px;background:#2c2f40;border:5px solid #14161f;box-shadow:0 8px 0 rgba(0,0,0,.35)}
.body{position:absolute;inset:62px 10px 10px 10px;border-radius:10px;background-color:#3a3d52;background-size:44px 44px}
.hdr{position:absolute;left:6px;right:6px;top:6px;height:52px;border-radius:10px;background-size:100% 100%;display:flex;align-items:center;padding:0 14px;gap:10px}
.hdr img{height:44px;margin-top:-14px;filter:drop-shadow(0 3px 0 #14161f)}
.hdr .t{font:700 30px Fredoka;letter-spacing:.5px}
.x{position:absolute;right:12px;top:10px;width:44px;height:44px;background-size:100% 100%}
.card{position:absolute;border-radius:12px;background-size:100% 100%;text-align:center}
.card .n{font:700 15px Fredoka;margin-top:6px}.card .r{font:700 13px Fredoka}
.card img{display:block;margin:2px auto 0;filter:drop-shadow(0 4px 0 rgba(0,0,0,.35))}
.btn{position:absolute;border-radius:10px;background-size:100% 100%;font:700 18px Fredoka;display:flex;align-items:center;justify-content:center;gap:6px}
.btn img{height:24px}
.pill{position:absolute;border-radius:999px;background:#14161f;font:700 15px Fredoka;padding:4px 12px;display:flex;gap:6px;align-items:center}
.pill img{height:20px}
.tab{position:absolute;width:76px;height:76px;border-radius:14px;border:4px solid #14161f;display:flex;flex-direction:column;align-items:center;justify-content:center;font:700 13px Fredoka}
.tab img{height:40px}
.sect{position:absolute;left:0;right:0;text-align:center;font:700 20px Fredoka;color:#ffd84a}
.bar{position:absolute;height:40px;border-radius:12px;background:#14161f;border:3px solid #14161f;overflow:hidden}
.bar i{position:absolute;left:0;top:0;bottom:0;border-radius:9px;background:linear-gradient(#7fd8ff,#2f9fe0)}
.bar b{position:relative;display:block;text-align:center;font:700 22px Fredoka;line-height:34px}
.lock{filter:brightness(0) opacity(.55)!important}
.cur:before{display:none}
.note{position:absolute;left:12px;bottom:10px;font:600 14px Fredoka;color:#fff;background:rgba(0,0,0,.45);padding:3px 10px;border-radius:8px}
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


def card(x, y, w, h, rar, name, art, size, extra="", lock=False):
    r = RAR[rar]
    return ('<div class="card" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx;%s">' % (x, y, w, h, bg(r[1]))
            + '<div class="n ol">' + (name if not lock else "???") + "</div>"
            + '<img src="' + A[art] + '" style="height:%dpx" class="%s">' % (size, "lock" if lock else "")
            + '<div class="r ol" style="color:' + r[2] + '">' + r[0] + "</div>" + extra + "</div>")


def btn(x, y, w, h, kind, words, icon=None):
    return ('<div class="btn ol" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx;%s">' % (x, y, w, h, bg(kind))
            + ('<img src="' + A[icon] + '">' if icon else "") + words + "</div>")


def tab(x, y, colour, icon, word, on=False):
    return ('<div class="tab ol" style="left:%dpx;top:%dpx;background:%s;%s"><img src="%s">%s</div>'
            % (x, y, colour, "outline:4px solid #fff;outline-offset:-9px" if on else "", A[icon], word))


# 1 Dino Index: blue header, biome card left, rarity cards with locked silhouettes, detail right, big found bar
cards = ""
dinos = [("compy", 0, False), ("dodo", 0, False), ("raptor", 1, False), ("stegosaurus", 2, False), ("triceratops", 3, True),
         ("ankylosaurus", 2, False), ("baryonyx", 4, True), ("brachiosaurus", 5, True)]
for i, (d, r, lock) in enumerate(dinos):
    cards += card(146 + (i % 4) * 106, 10 + (i // 4) * 150, 100, 142, r, d.capitalize() if d != "compy" else "Compy", d, 84, lock=lock)
index = win(24, 26, 790, 470, "header-blue", "Dino Index", "index-tab-colours-v1",
            '<div class="card" style="left:10px;top:10px;width:128px;height:292px;background:linear-gradient(#6fbf4a,#2f7a2a);border:4px solid #14161f">'
            '<div class="n ol" style="font-size:20px;margin-top:10px">Meadow</div><img src="' + A["egg-nest-single-v1"] + '" style="height:70px;margin-top:30px">'
            '<div class="ol" style="font:700 16px Fredoka;margin-top:40px">Find all:</div><div class="ol" style="font:700 18px Fredoka;color:#ffd84a">+50 crystals</div></div>'
            + cards
            + '<div class="card" style="left:574px;top:10px;width:180px;height:200px;' + bg("card-rare") + '"><div class="n ol" style="font-size:20px">Raptor</div>'
            '<img src="' + A["raptor"] + '" style="height:120px"><div class="r ol" style="color:#7fe4ff;font-size:16px">Uncommon</div></div>'
            + btn(582, 222, 164, 44, "button-gold", "CLAIM ALL") + btn(582, 274, 164, 44, "button-blue", "Variants 2/6")
            + '<div class="bar" style="left:10px;top:316px;width:744px"><i style="width:26%"></i><b class="ol">Found: 14 / 55</b></div>')
index_scr = '<div class="scr">' + index + tab(826, 70, "#3fa9f5", "index-tab-colours-v1", "Colours") + tab(826, 152, "#c45cf0", "index-tab-patterns-v1", "Patterns") + '<div class="note">World stays visible; tabs sit outside the window</div></div>'

# 2 Potion shop: purple header with a restock chip, rarity cards with a price button on EVERY card
pots = [("potion-growth-sip", 0, "Growth Sip", "+25% grow", 25), ("potion-lucky-sip", 1, "Lucky Sip", "+10% luck", 30),
        ("potion-raptor-rush", 2, "Raptor Rush", "+30% speed", 45), ("potion-hearty-brew", 3, "Hearty Brew", "+40% grow", 80),
        ("potion-behemoth-brew", 4, "Behemoth Brew", "+75% grow", 150), ("potion-jackpot-elixir", 5, "Jackpot", "x2 eggs", 300)]
pc = ""
for i, (art, r, name, line, price) in enumerate(pots):
    x, y = 12 + (i % 3) * 196, 46 + (i // 3) * 176
    pc += card(x, y, 186, 168, r, name, art, 70, '<div class="ol" style="font:700 14px Fredoka">' + line + "</div>")
    pc += btn(x + 18, y + 128, 150, 34, "button-green", str(price), "notify-crystal-v1")
shop = win(130, 20, 640, 482, "header-purple", "Potion Shop", "station-potions-v1",
           '<div class="pill ol" style="left:12px;top:8px"><img src="' + A["notify-crystal-v1"] + '">1,250</div>'
           '<div class="pill ol" style="right:12px;top:8px;color:#9dff6b">New potions in 4 min</div>' + pc)
shop_scr = ('<div class="scr">' + shop + tab(44, 60, "#9b5cf0", "station-potions-v1", "Potions", True) + tab(44, 142, "#f0b23a", "shop-tab-auras-v1", "Auras")
            + tab(44, 224, "#3fa9f5", "shop-tab-trails-v1", "Trails") + tab(44, 306, "#ffd84a", "shop-tab-crystals-v1", "Crystals")
            + '<div class="note">Every card has its own price button; rarity fills the card</div></div>')

# 3 Fusion: magenta-ish header, three slots, arrow lines to the result, one big green action
slots = ""
for i in range(3):
    x = 30 + i * 200
    slots += ('<div class="card" style="left:%dpx;top:48px;width:180px;height:120px;%s"><div class="n ol">Raptor</div><img src="%s" style="height:76px"></div>' % (x + 4, bg("card-rare"), A["raptor"]))
fusion = win(110, 22, 700, 480, "header-purple", "Fusion", "fusion",
             '<div class="sect ol" style="top:12px;color:#fff">Bring <span style="color:#ff6b6b">3</span> same dinos: the best one <span style="color:#9dff6b">grows a size</span>!</div>'
             + slots
             + '<div style="position:absolute;left:122px;top:168px;width:400px;height:26px;border:8px solid #14161f;border-top:none;border-radius:0 0 14px 14px"></div>'
             '<div style="position:absolute;left:318px;top:168px;width:8px;height:34px;background:#14161f"></div>'
             '<div class="card" style="left:252px;top:200px;width:140px;height:112px;' + bg("card-legendary") + '"><div class="n ol">Gold Raptor</div><img src="' + A["raptor"] + '" style="height:70px;filter:sepia(1) saturate(4) hue-rotate(-10deg) drop-shadow(0 4px 0 rgba(0,0,0,.35))"></div>'
             + btn(212, 326, 220, 50, "button-green", "FUSE!"))
fusion_scr = '<div class="scr">' + fusion + '<div class="note">One page tells the whole rule with pictures; big outlined words</div></div>'

# 4 Today (for comparison): the cream window from docs/240, described, not redrawn
CUR = sys.argv[3] if len(sys.argv) > 3 else "docs/evidence/2026-11-17-final-checks/phone-828x374-potion-shop.jpg"
cur = Image.open(CUR).convert("RGB")
cur.thumbnail((930, 523))
_b = io.BytesIO()
cur.save(_b, "JPEG", quality=80)
today = ('<div class="scr" style="background:#000 url(data:image/jpeg;base64,' + base64.b64encode(_b.getvalue()).decode() + ') center/contain no-repeat">'
         '<div class="note">Today: Studio capture of our Potion Shop (cream body, one look for every window)</div></div>').replace('class="scr"', 'class="scr cur"')
BODY = ('<div class="page">'
        '<div><div class="lbl">A. Dino Index in the top-game look</div>' + index_scr + "</div>"
        '<div><div class="lbl">B. Potion Shop in the top-game look</div>' + shop_scr + "</div>"
        '<div><div class="lbl">C. Fusion in the top-game look</div>' + fusion_scr + "</div>"
        '<div><div class="lbl">D. What we have today (for comparison)</div>' + today + "</div></div>")
html = ('<!doctype html><html><head><meta charset="utf-8"><link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&display=swap" rel="stylesheet">'
        "<style>" + CSS + "</style></head><body>" + BODY + "</body></html>")
open(OUT, "w", encoding="utf-8").write(html)
print(len(html))
