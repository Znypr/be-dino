"""Full-screen hatch proposal v1 (owner 2026-11-16: 'research other famous roblox experiences ... i want a full screen effect for it').
Decision aid, not game art: 960x540 mockup frames built from our real kit pictures, dino renders, egg renders and a Studio picture of the V3 island.

    python tools/hatch_fullscreen_mock.py <repo root> <out.html> <world.jpg>
"""
import base64
import io
import sys

from PIL import Image

ROOT, OUT, WORLD = sys.argv[1], sys.argv[2], sys.argv[3]


def u(p, maxs=None, absolute=False, crop=None):
    im = Image.open(p if absolute else ROOT + '/' + p).convert('RGBA')
    if crop:
        im = im.crop(crop)
    if maxs:
        im.thumbnail((maxs, maxs))
    b = io.BytesIO()
    if absolute:
        im.convert('RGB').save(b, 'JPEG', quality=70)
        return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()
    im.save(b, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()


K, I, D, E = 'resources/ui/v2/toybox/final/', 'resources/ui/v2/icons/', 'resources/ui/v2/dinos/v3/', 'resources/ui/v2/stage/eggs/'
V = {'bg': u(K + 'button-green.png'), 'bgr': u(K + 'button-grey.png'), 'cry': u(I + 'notify-crystal-v1.png', 96),
     'compy': u(D + 'compy.png', 320), 'raptor': u(D + 'raptor.png', 200), 'stego': u(D + 'stegosaurus.png', 200),
     'trice': u(D + 'triceratops.png', 200), 'trex': u(D + 't-rex.png', 420), 'ptera': u(D + 'pteranodon.png', 200),
     'egg': u(E + 'egg-03_normal.png', 300), 'eggR': u(E + 'egg-04_rainbow.png', 300), 'eggA': u(E + 'egg-05_astra.png', 300),
     'world': u(WORLD, 1300, absolute=True, crop=(0, 60, 1914, 793))}

css = ':root{' + ';'.join(f'--{k}:url({v})' for k, v in V.items()) + '}'
STYLE = """
body{margin:0;background:#2f4a2a;font-family:Fredoka,sans-serif;color:#2e261e;padding:22px;width:1000px}
h1{color:#fff;margin:0 0 4px;font-size:30px;-webkit-text-stroke:1px #1c1a12}
.sub{color:#e9f3d8;font-size:15px;margin-bottom:16px;line-height:1.35}
.lbl{color:#fff;font-size:17px;font-weight:600;margin:16px 0 6px}
.note{color:#d7e7c4;font-size:13.5px;margin:6px 2px 0;line-height:1.35}
.scr{position:relative;width:960px;height:540px;border:4px solid #1c1a12;border-radius:12px;overflow:hidden;background:var(--world) center/cover}
.blur{position:absolute;inset:-20px;background:var(--world) center/cover;filter:blur(9px) saturate(.9)}
.veil{position:absolute;inset:0}
.rays{position:absolute;left:50%;top:46%;width:1500px;height:1500px;transform:translate(-50%,-50%);border-radius:50%}
.pool{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);border-radius:50%}
.ow{color:#fff;-webkit-text-stroke:2px #1c1a12;paint-order:stroke fill;font-weight:700;text-shadow:0 3px 0 #1c1a12}
.chip{display:inline-flex;align-items:center;gap:6px;background:#fff7e3;border:3px solid #2e261e;border-radius:999px;padding:3px 14px;font-weight:600;font-size:18px;color:#2e261e}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;height:46px;min-width:130px;padding:0 18px;border-image:var(--bg) 22 fill / 22px stretch;color:#fff;font-weight:700;font-size:19px;-webkit-text-stroke:1.5px #1c1a12;paint-order:stroke fill}
.btn.gr{border-image-source:var(--bgr)}
.i{display:inline-block;width:26px;height:26px;background:center/contain no-repeat}
.top{position:absolute;top:12px;left:0;right:0;display:flex;justify-content:center}
.cry{position:absolute;top:12px;right:14px}
.bot{position:absolute;bottom:14px;right:16px;display:flex;gap:10px}
.img{position:absolute;background:center/contain no-repeat}
.word{position:absolute;left:0;right:0;text-align:center}
.bar{width:300px;height:22px;background:#fff7e3;border:3px solid #2e261e;border-radius:12px;overflow:hidden;margin:6px auto 0}
.bar>div{height:100%;background:#f2c03c}
.queue{position:absolute;bottom:14px;left:16px;display:flex;align-items:flex-end;gap:6px;background:#fff7e3cc;border:3px solid #2e261e;border-radius:14px;padding:6px 10px}
.queue .q{width:30px;height:38px;background:var(--egg) center/contain no-repeat;opacity:.85}
.queue .q.now{width:44px;height:56px;opacity:1}
.queue .q.done{opacity:.35}
.card{width:150px;height:200px;background:#fff7e3;border:4px solid #2e261e;border-radius:16px;position:relative;box-shadow:0 5px 0 #1c1a12}
.card .pic{position:absolute;left:8px;right:8px;top:10px;height:130px;background:center/contain no-repeat}
.card .nm{position:absolute;bottom:34px;left:0;right:0;text-align:center;font-weight:700;font-size:17px}
.card .rw{position:absolute;bottom:8px;left:50%;transform:translateX(-50%);font-size:13px;font-weight:700;color:#fff;padding:2px 10px;border-radius:999px;border:2px solid #2e261e}
.phone{position:relative;width:640px;height:296px;border:10px solid #1c1a12;border-radius:36px;overflow:hidden;background:var(--world) center/cover}
"""

COMMON_RAYS = 'background:repeating-conic-gradient(from 0deg,rgba(255,255,255,.28) 0 8deg,rgba(255,255,255,0) 8deg 20deg)'
GOLD_RAYS = 'background:repeating-conic-gradient(from 4deg,rgba(255,210,80,.55) 0 7deg,rgba(255,170,40,0) 7deg 16deg)'


def stage(veil='rgba(255,248,230,.18)', rays='', pool='', inner=''):
    return ('<div class="scr"><div class="blur"></div><div class="veil" style="background:' + veil + '"></div>'
            + (f'<div class="rays" style="{rays}"></div>' if rays else '')
            + (f'<div class="pool" style="{pool}"></div>' if pool else '') + inner + '</div>')


CRY = '<div class="cry chip"><span class="i" style="background-image:var(--cry)"></span>12,450</div>'
QUEUE = '<div class="queue"><div class="q done"></div><div class="q now"></div><div class="q"></div><div class="q"></div><div class="q"></div></div>'

EGG = stage(rays=COMMON_RAYS, pool='width:420px;height:420px;background:radial-gradient(circle,rgba(255,250,225,.95),rgba(255,250,225,0) 70%)', inner=
            '<div class="top"><span class="chip">Egg 2 of 5</span></div>' + CRY
            + '<div class="img" style="left:375px;top:120px;width:210px;height:270px;background-image:var(--egg);transform:rotate(-6deg)"></div>'
            + '<div class="word" style="top:420px"><span class="chip" style="font-size:22px">Tap the egg!</span></div>'
            + QUEUE + '<div class="bot"><span class="btn gr">SKIP ALL</span></div>')

CRACK = stage(veil='rgba(255,248,230,.28)', rays='background:repeating-conic-gradient(from 0deg,rgba(150,120,255,.45) 0 6deg,rgba(150,120,255,0) 6deg 15deg)',
              pool='width:520px;height:520px;background:radial-gradient(circle,rgba(255,255,255,1),rgba(220,205,255,.7) 30%,rgba(255,255,255,0) 70%)', inner=
              '<div class="top"><span class="chip">Egg 4 of 5</span></div>' + CRY
              + '<div class="img" style="left:365px;top:110px;width:230px;height:290px;background-image:var(--eggA);transform:rotate(5deg)"></div>'
              + '<svg style="position:absolute;left:400px;top:170px" width="160" height="130"><polyline points="10,60 40,40 60,70 90,30 120,65 150,45" fill="none" stroke="#fff" stroke-width="7" stroke-linejoin="round"/><polyline points="10,60 40,40 60,70 90,30 120,65 150,45" fill="none" stroke="#2e261e" stroke-width="3"/></svg>'
              + '<div class="word" style="top:420px"><span class="chip" style="font-size:22px">Something rare...</span></div>'
              + QUEUE.replace('class="q now"', 'class="q done"', 1).replace('<div class="q"></div>', '<div class="q done"></div>', 1).replace('<div class="q"></div>', '<div class="q now"></div>', 1)
              + '<div class="bot"><span class="btn gr">SKIP ALL</span></div>')

COMMON = stage(rays=COMMON_RAYS, pool='width:460px;height:460px;background:radial-gradient(circle,rgba(255,255,255,.95),rgba(255,255,255,0) 68%)', inner=
               '<div class="word ow" style="top:26px;font-size:54px;color:#e8ecef">COMMON</div>' + CRY
               + '<div class="img" style="left:330px;top:95px;width:300px;height:280px;background-image:var(--compy)"></div>'
               + '<div class="word" style="top:378px"><span class="chip">Compy</span> <span class="chip">Blue · Spots</span> <span class="chip">26% of eggs</span></div>'
               + '<div class="word" style="top:420px;font-weight:600;font-size:15px">3 of 6 for Gold!<div class="bar"><div style="width:50%"></div></div></div>'
               + QUEUE + '<div class="bot"><span class="btn gr">SKIP ALL</span><span class="btn">NEXT EGG</span></div>')

LEGEND = stage(veil='rgba(60,30,0,.35)', rays=GOLD_RAYS, pool='width:560px;height:560px;background:radial-gradient(circle,rgba(255,236,150,1),rgba(255,190,60,.6) 35%,rgba(255,190,60,0) 70%)', inner=
               '<div class="word ow" style="top:14px;font-size:72px;color:#ffc93c;transform:rotate(-4deg)">LEGENDARY!</div>' + CRY
               + ''.join(f'<div style="position:absolute;left:{x}px;top:{y}px;width:12px;height:18px;background:{c};transform:rotate({r}deg);border:2px solid #2e261e;border-radius:3px"></div>'
                         for x, y, c, r in [(180, 120, '#ff6b6b', 20), (250, 300, '#4fc3f7', -30), (700, 140, '#9ccc65', 40), (780, 330, '#ffd54f', -10), (140, 380, '#ba68c8', 60), (820, 220, '#ff8a65', 15), (300, 90, '#ffd54f', -40), (640, 420, '#4fc3f7', 30)])
               + '<div class="img" style="left:290px;top:90px;width:380px;height:320px;background-image:var(--trex)"></div>'
               + '<div class="word" style="top:400px"><span class="chip">T-Rex</span> <span class="chip" style="background:#ffd36b">Shiny ✦</span> <span class="chip">BIG</span> <span class="chip">1 in 250 eggs</span></div>'
               + QUEUE + '<div class="bot"><span class="btn">NICE!</span></div>')

SUMMARY = stage(rays=COMMON_RAYS, inner=
                '<div class="word ow" style="top:24px;font-size:46px">You hatched 5 dinos!</div>' + CRY
                + '<div style="position:absolute;top:110px;left:0;right:0;display:flex;justify-content:center;gap:14px">'
                + ''.join(f'<div class="card" style="border-color:{b}"><div class="pic" style="background-image:var(--{p})"></div><div class="nm">{n}</div><div class="rw" style="background:{c}">{w}</div></div>'
                          for p, n, w, c, b in [('compy', 'Compy', 'Common', '#9aa3ad', '#2e261e'), ('raptor', 'Raptor', 'Common', '#9aa3ad', '#2e261e'),
                                                ('stego', 'Stego', 'Uncommon', '#5cb85c', '#2e261e'), ('ptera', 'Ptera', 'Rare', '#3d8bfd', '#2e261e'),
                                                ('trex', 'T-Rex', 'Legendary', '#f0a500', '#f0a500')])
                + '</div><div class="word" style="top:330px"><span class="chip">2 new colours · 1 new pattern</span></div>'
                + '<div class="bot"><span class="btn gr">SEE DINOS</span><span class="btn">PLAY AGAIN</span></div>')

PHONE = ('<div class="phone"><div class="blur"></div><div class="veil" style="background:rgba(255,248,230,.18)"></div>'
         '<div class="rays" style="' + COMMON_RAYS + ';width:900px;height:900px"></div>'
         '<div class="word ow" style="top:8px;font-size:34px;color:#e8ecef">COMMON</div>'
         '<div class="img" style="left:220px;top:50px;width:200px;height:170px;background-image:var(--compy)"></div>'
         '<div class="word" style="top:222px"><span class="chip" style="font-size:15px">Compy</span> <span class="chip" style="font-size:15px">Blue · Spots</span></div>'
         '<div style="position:absolute;right:10px;bottom:10px"><span class="btn" style="height:44px;min-width:110px;font-size:16px">NEXT</span></div>'
         '<div style="position:absolute;left:10px;bottom:10px"><span class="btn gr" style="height:44px;min-width:96px;font-size:16px">SKIP</span></div></div>')

BODY = """<h1>Be Dino! full-screen hatch, proposal v1</h1>
<div class="sub">The hatch takes the WHOLE screen, like the big pet games: the island stays visible behind a soft blur, the HUD hides (only crystals stay),
there is no window. The egg and the dino are REAL 3D models in front of the camera (real sparkles and light), the words are UI on top.
Calm and bubbly: no hard shake, no strobe, no slot-machine reel. Mockups from our own art; not the game yet.</div>
<div class="lbl">1 The egg arrives (0.0 s): it bounces in, wobbles, and waits for a tap</div>""" + EGG + """
<div class="note">Soft light pool and slow white rays behind it. "Egg 2 of 5" on top, the queue of eggs bottom-left (this one bigger), SKIP ALL bottom-right. Common eggs crack by themselves after about 1 s (fast commons).</div>
<div class="lbl">2 Tap: the egg cracks (rarer = longer build-up, coloured light leaks out)</div>""" + CRACK + """
<div class="note">Common: 1 crack and a soft flash (about 0.6 s). Rare and up: 2-3 crack steps, light in the rarity colour leaks through, a gentle push-in of the camera. A small hint like "Something rare..." tells the kid to watch.</div>
<div class="lbl">3 A Common pops out: quick and calm (about 2 s), then the next egg</div>""" + COMMON + """
<div class="note">Big outlined rarity word on top, the dino hops out and turns, cream chips: name, colour + pattern, the chance in kid words, then "3 of 6 for Gold!". NEXT EGG green, SKIP ALL grey.</div>
<div class="lbl">4 A Legendary: the full show (about 5 s)</div>""" + LEGEND + """
<div class="note">Gold rays, the world dims more, confetti, a sting sound, "LEGENDARY!" bounces in tilted, the dino rises on a light pool. Trait chips (Shiny, BIG, mutation) only when it has them. No auto-skip: one green NICE! button. Mythic = rainbow rays and a short camera orbit, plus a server toast.</div>
<div class="lbl">5 End of the batch: everything you got, on the same stage</div>""" + SUMMARY + """
<div class="note">The cards pop in one by one (0.1 s apart); the best one has its rarity-coloured border and glow. SEE DINOS grey, PLAY AGAIN green (BD-1199). Many eggs at once (8+): the cards wrap into two rows.</div>
<div class="lbl">6 Same Common reveal on a phone (landscape)</div>""" + PHONE + """
<div class="note">Buttons 44 px and up in the bottom corners (thumbs), words shrink to the phone scale, nothing in the top 40 px (Roblox buttons). Reduce Motion: no rays turning, no confetti falling, a fade instead of the pop.</div>
<div class="lbl">Rarity ladder</div>
<div class="note">Common white glow, plain pop · Uncommon green glow · Rare blue + sparkles · Epic purple + rays + longer wobble · Legendary gold + confetti + sting + slow-mo · Mythic rainbow + camera orbit + server toast. Shiny / BIG / mutation add a chip and a sparkle layer on top. Skip and fast options stay free.</div>"""

html = ('<!doctype html><html><head><meta charset="utf-8">'
        '<link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&display=swap" rel="stylesheet">'
        '<style>' + css + STYLE + '</style></head><body>' + BODY + '</body></html>')
open(OUT, 'w', encoding='utf-8').write(html)
print(OUT, len(html))
