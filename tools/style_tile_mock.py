"""Style tile v2: full 960x540 screen mockups in the one look (BD-1206). Decision aid, not game art."""
import base64, io, sys
from PIL import Image

ROOT, OUT, WORLD = sys.argv[1], sys.argv[2], sys.argv[3]


def u(p, maxs=None, crop=None, absolute=False):
    im = Image.open(p if absolute else ROOT + '/' + p).convert('RGBA')
    if crop:
        im = im.crop(crop)
    if maxs:
        im.thumbnail((maxs, maxs))
    b = io.BytesIO()
    if absolute:
        im.convert('RGB').save(b, 'JPEG', quality=62)
        return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()
    im.quantize(colors=96, method=Image.Quantize.FASTOCTREE).save(b, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()


K, I, D, E = 'resources/ui/v2/toybox/final/', 'resources/ui/v2/icons/', 'resources/ui/v2/dinos/v3/', 'resources/ui/v2/stage/eggs/'
V = {'hdrA': u(K + 'header-amber.png'), 'hdrC': u(K + 'header-cream.png'), 'frame': u(K + 'panel-frame.png'),
     'studs': u(K + 'studs-tile.png'), 'bg': u(K + 'button-green.png'), 'bgr': u(K + 'button-grey.png'), 'x': u(K + 'close.png'),
     'cry': u(I + 'notify-crystal-v1.png', 96), 'egg': u(I + 'egg.png', 96), 'nest': u(I + 'egg-nest-single-v1.png', 120),
     'bite': u(I + 'hud-bite-v1.png', 96), 'star': u(I + 'notify-level-v1.png', 96), 'potion': u(I + 'station-potions-v1.png', 96),
     'dinos': u(I + 'station-index-v1.png', 96), 'shield': u(I + 'rarity-legendary-v1.png', 96), 'rare': u(I + 'rarity-rare-v1.png', 96),
     'trex': u(D + 't-rex.png', 360), 'compy': u(D + 'compy.png', 260), 'raptor': u(D + 'raptor.png', 200), 'stego': u(D + 'stegosaurus.png', 200),
     'trice': u(D + 'triceratops.png', 200), 'eggN': u(E + 'egg-03_normal.png', 260), 'eggR': u(E + 'egg-04_rainbow.png', 260),
     'world': u(WORLD, 1400, crop=(300, 150, 1620, 640), absolute=True)}
css = ':root{' + ''.join('--%s:url(%s);' % (k, v) for k, v in V.items()) + '}'

STYLE = """
body{margin:0;background:#2f4f27;font-family:Fredoka,sans-serif;padding:14px;width:968px;color:#3a2f1e}
h1{color:#fff;font-size:36px;margin:0 0 2px;-webkit-text-stroke:6px #1d1d1d;paint-order:stroke fill}
.sub{color:#e8f5dc;font-size:18px;margin-bottom:16px}
.grid{display:grid;grid-template-columns:960px;gap:22px}
.lbl{color:#fff;font-size:22px;font-weight:700;margin:0 0 6px;-webkit-text-stroke:4px #1d1d1d;paint-order:stroke fill}
.scr{width:960px;height:540px;position:relative;overflow:hidden;border-radius:14px;border:3px solid #111;background:var(--world) center/cover}
.dim::after{content:"";position:absolute;inset:0;background:rgba(20,30,20,.45)}
.ow{color:#fff;-webkit-text-stroke:5px #1d1d1d;paint-order:stroke fill;font-weight:700}
.ink{color:#3a2f1e;font-weight:700}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;height:48px;padding:0 24px;font-size:20px;font-weight:700;color:#fff;-webkit-text-stroke:5px #1d1d1d;paint-order:stroke fill;border-style:solid;border-width:10px 12px 12px 12px;box-sizing:border-box;border-image-slice:20 24 24 24 fill;border-image-width:10px 12px 12px 12px;white-space:nowrap}
.g{border-image-source:var(--bg)} .gr{border-image-source:var(--bgr)}
.chip{display:inline-flex;align-items:center;gap:6px;background:#fff7e3;border:3px solid #1d1d1d;border-radius:999px;padding:2px 12px;font-weight:700;font-size:16px;white-space:nowrap}
.plate{position:absolute;display:flex;align-items:center;gap:8px;background:#fff7e3;border:3px solid #1d1d1d;border-radius:14px;padding:5px 12px;font-weight:700;font-size:20px;box-shadow:0 4px 0 #1d1d1d;z-index:2}
.i{width:28px;height:28px;background:center/contain no-repeat;display:inline-block;flex:none}
.rib{display:inline-block;background:linear-gradient(#ffe27a,#f2b329);border:3px solid #1d1d1d;border-radius:10px;padding:2px 12px;font-weight:700;color:#fff;-webkit-text-stroke:4px #1d1d1d;paint-order:stroke fill;transform:rotate(-5deg);font-size:18px}
.rail{position:absolute;left:12px;top:150px;display:flex;flex-direction:column;gap:10px;z-index:2}
.rb{width:58px;height:58px;border-radius:14px;background:#fff7e3;border:3px solid #1d1d1d;box-shadow:0 4px 0 #1d1d1d;display:flex;align-items:center;justify-content:center}
.rb .i{width:40px;height:40px}
.bar{position:absolute;left:50%;top:14px;transform:translateX(-50%);display:flex;align-items:center;gap:8px;background:#fff7e3;border:3px solid #1d1d1d;border-radius:14px;padding:5px 10px;box-shadow:0 4px 0 #1d1d1d;z-index:2}
.track{width:240px;height:16px;border-radius:9px;background:#e7dcc2;border:3px solid #1d1d1d;overflow:hidden}
.fill{height:100%;width:38%;background:#5ded1f}
.goal{position:absolute;left:50%;top:70px;transform:translateX(-50%);z-index:2}
.stage{position:absolute;inset:0;overflow:hidden}
.rays{position:absolute;inset:-70%;background:repeating-conic-gradient(rgba(255,255,255,.33) 0 8deg,transparent 8deg 22deg)}
.center{position:absolute;left:50%;transform:translateX(-50%)}
.win{position:absolute;border:16px solid transparent;border-image:var(--frame) 36 fill / 16px round;background:var(--studs) 0 0/52px;background-clip:padding-box;border-radius:18px;z-index:3}
.wh{position:absolute;left:-6px;right:-6px;top:-6px;height:56px;border-style:solid;border-width:12px 34px 12px 34px;box-sizing:border-box;border-image:var(--hdrC) 30 288 30 150 fill / 13px 62px 13px 32px stretch;display:flex;align-items:center;font-size:26px}
.wx{position:absolute;right:6px;top:4px;width:44px;height:44px;background:var(--x) center/contain no-repeat}
.panel{position:absolute;background:#fff7e3;border:3px solid #1d1d1d;border-radius:14px}
.row{display:flex;justify-content:space-between;font-size:18px;padding:6px 0;border-bottom:2px dashed #e2d6b9}
.row span:first-child{color:#7a6a4e;font-weight:600}
.card{background:#fffdf6;border:3px solid #1d1d1d;border-radius:12px;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;padding:6px;box-sizing:border-box}
.dimg{width:100%;flex:1;background:center/contain no-repeat}
.toast{position:absolute;left:50%;top:18px;transform:translateX(-50%);display:flex;align-items:center;gap:10px;background:#fff7e3;border:3px solid #1d1d1d;border-radius:16px;padding:8px 16px;box-shadow:0 5px 0 #1d1d1d;z-index:4;font-size:20px}
"""

HUD = """
<div class="scr"><div class="plate" style="left:14px;top:14px"><span class="i" style="background-image:var(--egg)"></span>5 eggs</div>
<div class="plate" style="right:14px;top:14px"><span class="i" style="background-image:var(--cry)"></span>12,450</div>
<div class="bar"><span class="ink" style="font-size:16px">Size</span><div class="track"><div class="fill"></div></div><span class="ink" style="font-size:16px">3</span></div>
<div class="goal"><span class="chip"><span class="i" style="background-image:var(--star);width:22px;height:22px"></span>Eat 20 berries &middot; 12/20</span></div>
<div class="rail"><div class="rb"><span class="i" style="background-image:var(--dinos)"></span></div><div class="rb"><span class="i" style="background-image:var(--egg)"></span></div><div class="rb"><span class="i" style="background-image:var(--potion)"></span></div></div>
<div class="plate" style="right:14px;top:70px;font-size:16px">Storm in 4 min</div>
<div style="position:absolute;right:14px;bottom:14px;display:flex;gap:10px;z-index:2"><span class="btn gr" style="height:58px">LEAP</span><span class="btn g" style="height:58px"><span class="i" style="background-image:var(--bite)"></span>CHOMP</span></div>
<div style="position:absolute;left:50%;bottom:14px;transform:translateX(-50%);z-index:2"><span class="btn gr" style="height:52px">HOME</span></div>
</div>"""

EGG = """
<div class="scr dim"><div class="stage" style="z-index:3;background:radial-gradient(circle at 50% 45%,rgba(255,250,230,.95) 0,rgba(255,236,190,.85) 40%,rgba(120,100,60,.2) 75%)"><div class="rays" style="opacity:.5"></div>
<div class="center" style="top:26px"><span class="chip" style="font-size:18px">Egg 2 of 5</span></div>
<div class="center" style="top:90px;width:240px;height:280px;background:var(--eggN) center/contain no-repeat;transform:translateX(-50%) rotate(-6deg)"></div>
<div class="center" style="top:388px"><span class="chip" style="font-size:20px"><span class="i" style="background-image:var(--egg);width:22px;height:22px"></span>Tap to crack!</span></div>
<div style="position:absolute;right:16px;bottom:16px"><span class="btn gr">SKIP THE REST</span></div></div></div>"""

COMMON = """
<div class="scr dim"><div class="stage" style="z-index:3;background:radial-gradient(circle at 50% 45%,#ffffff 0,#dfe7ee 45%,rgba(120,130,140,.5) 85%)"><div class="rays" style="opacity:.35"></div>
<div class="center" style="top:20px"><span class="ow" style="font-size:40px;color:#9aa6b2">COMMON</span></div>
<div class="center" style="top:86px;width:300px;height:260px;background:var(--compy) center/contain no-repeat"></div>
<div style="position:absolute;right:120px;top:120px"><span class="rib">NEW!</span></div>
<div class="center" style="top:362px;display:flex;gap:8px"><span class="chip" style="font-size:20px">Compy</span><span class="chip">Blue &middot; Spots</span></div>
<div class="center" style="top:410px;width:340px"><div class="panel" style="position:relative;padding:6px 12px;font-size:16px"><span class="ink">3 of 6 for Gold!</span><div class="track" style="width:100%;margin-top:4px;height:12px"><div class="fill" style="width:50%;background:#ffd22b"></div></div></div></div>
<div style="position:absolute;right:16px;bottom:16px;display:flex;gap:10px"><span class="btn gr">SKIP</span><span class="btn g">NEXT EGG</span></div></div></div>"""

LEGEND = """
<div class="scr dim"><div class="stage" style="z-index:3;background:radial-gradient(circle at 50% 45%,#fff6c9 0,#f6c94a 40%,#c97a0e 100%)"><div class="rays"></div>
<div class="center" style="top:14px;transform:translateX(-50%) rotate(-5deg)"><span class="ow" style="font-size:58px;color:#ffe35a">LEGENDARY!</span></div>
<div class="center" style="top:96px;width:380px;height:280px;background:var(--trex) center/contain no-repeat"></div>
<div style="position:absolute;left:150px;top:150px;width:70px;height:70px;background:var(--shield) center/contain no-repeat"></div>
<div class="center" style="top:384px;display:flex;gap:8px"><span class="chip" style="font-size:22px">T-Rex</span><span class="chip" style="color:#b07800">Legendary</span><span class="chip">BIG</span></div>
<div class="center" style="top:430px"><span class="chip" style="font-size:16px">1 in 250 eggs</span></div>
<div style="position:absolute;right:16px;bottom:16px;display:flex;gap:10px"><span class="btn gr">SKIP</span><span class="btn g">NEXT EGG</span></div></div></div>"""

SUMMARY = """
<div class="scr dim"><div class="win" style="left:120px;right:120px;top:40px;bottom:40px"><div class="wh"><span class="ow" style="margin-left:8px">You hatched 5 dinos!</span></div><div class="wx"></div>
<div class="panel" style="left:12px;right:12px;top:64px;bottom:74px;padding:12px;display:grid;grid-template-columns:repeat(5,1fr);gap:12px">
<div class="card"><div class="dimg" style="background-image:var(--compy)"></div><span class="chip" style="font-size:14px">Compy</span></div>
<div class="card"><div class="dimg" style="background-image:var(--raptor)"></div><span class="chip" style="font-size:14px;color:#3aa10f">Raptor</span></div>
<div class="card" style="border-color:#2ecefe;border-width:4px"><div class="dimg" style="background-image:var(--stego)"></div><span class="chip" style="font-size:14px;color:#1590c0">Stego</span></div>
<div class="card" style="border-color:#c256ff;border-width:4px"><div class="dimg" style="background-image:var(--trice)"></div><span class="chip" style="font-size:14px;color:#9a3ad0">Trice</span></div>
<div class="card" style="border-color:#ffd22b;border-width:5px;background:#fff6c9"><span class="rib" style="margin-top:2px">BEST!</span><div class="dimg" style="background-image:var(--trex)"></div><span class="chip" style="font-size:14px;color:#b07800">T-Rex</span></div>
</div>
<div style="position:absolute;left:12px;right:12px;bottom:10px;display:flex;justify-content:flex-end;gap:10px"><span class="btn gr">SEE DINOS</span><span class="btn g">PLAY AGAIN</span></div></div></div>"""

RUNEND = """
<div class="scr dim"><div class="win" style="left:170px;right:170px;top:34px;bottom:34px"><div class="wh"><span class="ow" style="margin-left:8px">Great run!</span></div><div class="wx"></div>
<div class="panel" style="left:12px;width:250px;top:64px;bottom:74px;padding:12px;box-sizing:border-box">
<div class="row"><span>Food eaten</span><span class="ink">640</span></div><div class="row"><span>Eggs caught</span><span class="ink">15</span></div>
<div class="row"><span>Crystals</span><span class="ink">+30</span></div><div class="row"><span>Nest found</span><span class="ink">1</span></div>
<div class="row" style="border:0"><span>Run streak</span><span class="ink">2</span></div></div>
<div class="panel" style="left:274px;right:12px;top:64px;bottom:74px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;padding:8px;box-sizing:border-box;text-align:center">
<div style="display:flex;gap:4px"><span class="i" style="background-image:var(--egg);width:46px;height:46px"></span><span class="i" style="background-image:var(--egg);width:46px;height:46px"></span><span class="i" style="background-image:var(--egg);width:46px;height:46px"></span><span class="i" style="background-image:var(--nest);width:56px;height:46px"></span></div>
<span class="ink" style="font-size:22px">15 eggs are ready to hatch!</span><span class="chip">Next: Raptor 4 of 6 for Gold</span></div>
<div style="position:absolute;left:12px;right:12px;bottom:10px;display:flex;justify-content:flex-end;gap:10px"><span class="btn gr">HOME</span><span class="btn g">HATCH EGGS</span></div></div></div>"""

POPUPS = """
<div class="scr"><div class="toast"><span class="i" style="background-image:var(--star);width:36px;height:36px"></span><span class="ink">Level 4!</span><span class="chip" style="font-size:14px">+20 crystals</span></div>
<div class="scr dim" style="position:absolute;inset:0;border:0;border-radius:0"></div>
<div class="win" style="left:280px;right:280px;top:120px;bottom:90px"><div class="wh" style="border-image-source:var(--hdrA)"><span class="ow" style="margin-left:8px">Buy Royal Nova?</span></div><div class="wx"></div>
<div class="panel" style="left:12px;right:12px;top:64px;bottom:74px;display:flex;align-items:center;gap:14px;padding:12px">
<div style="width:110px;height:110px;background:var(--rare) center/contain no-repeat"></div>
<div><div class="ink" style="font-size:20px">Growth +70% for Compy</div><div style="font-size:16px;color:#7a6a4e;margin-top:4px">You have 12,450 crystals</div></div></div>
<div style="position:absolute;left:12px;right:12px;bottom:10px;display:flex;justify-content:flex-end;gap:10px"><span class="btn gr">NOT NOW</span><span class="btn g"><span class="i" style="background-image:var(--cry)"></span>3,700</span></div></div></div>"""

BODY = """<h1>Be Dino! style tile v2: the whole game in one look</h1>
<div class="sub">Same rules as v1 (cream surfaces + ink text, white outlined text only on colour or the world, one green button, rarity colour only on rarity things). Real kit pictures and dino art; mockups, not the game yet.</div>
<div class="grid">
<div><div class="lbl">1 Playing: HUD in the world</div>""" + HUD + """</div>
<div><div class="lbl">2 Hatch: the egg waits for a tap (no timer)</div>""" + EGG + """</div>
<div><div class="lbl">3 Hatch: a Common pops (quick, calm)</div>""" + COMMON + """</div>
<div><div class="lbl">4 Hatch: a Legendary (the full show)</div>""" + LEGEND + """</div>
<div><div class="lbl">5 After a batch: everything you got</div>""" + SUMMARY + """</div>
<div><div class="lbl">6 Run end: what you earned, play again</div>""" + RUNEND + """</div>
<div><div class="lbl">7 Reward toast + a confirm popup</div>""" + POPUPS + """</div>
</div>"""

html = ('<!doctype html><html><head><meta charset="utf-8">'
        '<link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&display=swap" rel="stylesheet">'
        '<style>' + css + STYLE + '</style></head><body>' + BODY + '</body></html>')
open(OUT, 'w', encoding='utf-8').write(html)
print(len(html))
