"""Full-screen hatch storyboard v2 (owner 2026-11-16: 'looks boring ... compare with other famous games ... actual paint splashing on
the egg, and the egg breaking should be cooler'). Decision aid, not game art: 960x540 frames from our egg / dino renders and a Studio
picture of the island; paint, cracks, shards and buckets are drawn here only to show the beats (the game gets Blender / generated art).

    python tools/hatch_storyboard_v2.py <art root> <out.html> <world.jpg>
"""
import base64
import io
import math
import random
import sys

from PIL import Image

ROOT, OUT, WORLD = sys.argv[1], sys.argv[2], sys.argv[3]


def u(p, maxs=None, absolute=False):
    im = Image.open(p if absolute else ROOT + '/' + p).convert('RGBA')
    if maxs:
        im.thumbnail((maxs, maxs))
    b = io.BytesIO()
    if absolute:
        im.convert('RGB').save(b, 'JPEG', quality=70)
        return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()
    im.save(b, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()


K, I, D, E = 'resources/ui/v2/toybox/final/', 'resources/ui/v2/icons/', 'resources/ui/v2/dinos/v3/', 'resources/ui/v2/stage/eggs/'
V = {'bg': u(K + 'button-green.png'), 'bgr': u(K + 'button-grey.png'), 'bgo': u(K + 'button-gold.png'), 'cry': u(I + 'notify-crystal-v1.png', 96),
     'trice': u(D + 'triceratops.png', 420), 'trex': u(D + 't-rex.png', 460), 'compy': u(D + 'compy.png', 200), 'raptor': u(D + 'raptor.png', 200),
     'egg': u(E + 'egg-03_normal.png', 320), 'world': u(WORLD, 1300, absolute=True)}
css = ':root{' + ';'.join(f'--{k}:url({v})' for k, v in V.items()) + '}'
STYLE = """
body{margin:0;background:#2f4a2a;font-family:Fredoka,sans-serif;color:#2e261e;padding:22px;width:1000px}
h1{color:#fff;margin:0 0 4px;font-size:30px;-webkit-text-stroke:1px #1c1a12}
.sub{color:#e9f3d8;font-size:15px;margin-bottom:10px;line-height:1.35}
.lbl{color:#fff;font-size:17px;font-weight:600;margin:16px 0 6px}
.note{color:#d7e7c4;font-size:13.5px;margin:6px 2px 0;line-height:1.35}
.scr{position:relative;width:960px;height:540px;border:4px solid #1c1a12;border-radius:12px;overflow:hidden;background:var(--world) center/cover}
.blur{position:absolute;inset:-20px;background:var(--world) center/cover;filter:blur(10px) saturate(.85)}
.veil{position:absolute;inset:0}
.rays{position:absolute;left:50%;top:48%;width:1600px;height:1600px;transform:translate(-50%,-50%);border-radius:50%}
.vign{position:absolute;inset:0;background:radial-gradient(ellipse at 50% 48%,rgba(0,0,0,0) 35%,rgba(0,0,0,.55) 100%)}
.ow{color:#fff;-webkit-text-stroke:2.5px #1c1a12;paint-order:stroke fill;font-weight:700;text-shadow:0 5px 0 #1c1a12}
.chip{display:inline-flex;align-items:center;gap:6px;background:#fff7e3;border:3px solid #2e261e;border-radius:9px;padding:4px 14px;font-weight:600;font-size:19px;color:#2e261e}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;height:54px;min-width:150px;padding:0 20px;border-image:var(--bg) 22 fill / 22px stretch;color:#fff;font-weight:700;font-size:21px;-webkit-text-stroke:1.5px #1c1a12;paint-order:stroke fill}
.btn.gr{border-image-source:var(--bgr)} .btn.go{border-image-source:var(--bgo)} .btn.sm{height:44px;min-width:110px;font-size:17px}
.i{display:inline-block;width:26px;height:26px;background:center/contain no-repeat}
.cry{position:absolute;top:12px;right:14px}
.egg{position:absolute;left:50%;top:47%;width:400px;height:500px;transform:translate(-50%,-50%);background:var(--egg) center/contain no-repeat;filter:drop-shadow(0 10px 8px rgba(0,0,0,.35))}
.paint{position:absolute;left:50%;top:47%;width:400px;height:500px;transform:translate(-50%,-50%);-webkit-mask:var(--egg) center/contain no-repeat;mask:var(--egg) center/contain no-repeat}
.bucket{position:absolute;width:96px;height:96px}
.bucket .b{position:absolute;inset:14px 10px 0 10px;background:linear-gradient(90deg,#c9ccd2,#f1f2f4 40%,#a9adb5);border:4px solid #2e261e;border-radius:6px 6px 16px 16px}
.bucket .l{position:absolute;left:6px;right:6px;top:6px;height:18px;border:4px solid #2e261e;border-radius:50%}
.word{position:absolute;left:0;right:0;text-align:center}
.banner{position:absolute;left:50%;transform:translateX(-50%);padding:6px 34px 10px;border:4px solid #1c1a12;border-radius:16px;box-shadow:0 6px 0 #1c1a12}
.queue{position:absolute;bottom:14px;left:16px;display:flex;align-items:flex-end;gap:6px;background:#fff7e3;border:3px solid #2e261e;border-radius:12px;padding:6px 10px}
.queue .q{width:26px;height:34px;background:var(--egg) center/contain no-repeat}.queue .q.now{width:40px;height:52px}.queue .q.done{opacity:.35}
.bot{position:absolute;bottom:14px;right:16px;display:flex;gap:12px}
.card{position:absolute;left:50%;transform:translateX(-50%);background:#fff7e3;border:4px solid #2e261e;border-radius:18px;box-shadow:0 6px 0 #1c1a12}
"""

RNG = random.Random(4)


def blobs(color, n, spread=1.0, seed=0, size=(26, 70)):
    r = random.Random(seed)
    out = ''
    for _ in range(n):
        x, y = r.uniform(110, 290), r.uniform(120, 390) * spread
        w = r.uniform(*size)
        out += f'<div style="position:absolute;left:{x - w / 2:.0f}px;top:{y - w / 2:.0f}px;width:{w:.0f}px;height:{w * r.uniform(.7, 1.1):.0f}px;background:{color};border-radius:{r.randint(38, 60)}% {r.randint(38, 60)}% {r.randint(38, 60)}% {r.randint(38, 60)}%"></div>'
    return out


def droplets(color, cx, cy, n, seed, reach=150, up=True):
    r = random.Random(seed)
    out = ''
    for i in range(n):
        a = r.uniform(-160, -20) if up else r.uniform(0, 360)
        d = r.uniform(40, reach)
        s = r.uniform(8, 20)
        x, y = cx + math.cos(math.radians(a)) * d, cy + math.sin(math.radians(a)) * d
        out += f'<div style="position:absolute;left:{x:.0f}px;top:{y:.0f}px;width:{s:.0f}px;height:{s * 1.2:.0f}px;background:{color};border:2px solid #2e261e;border-radius:50% 50% 50% 50%/60% 60% 40% 40%"></div>'
    return out


def bucket(x, y, rot, paint):
    return (f'<div class="bucket" style="left:{x}px;top:{y}px;transform:rotate({rot}deg)"><div class="b"></div><div class="l"></div>'
            f'<div style="position:absolute;left:14px;right:14px;top:14px;height:14px;background:{paint};border-radius:50%"></div></div>')


def stage(veil='rgba(0,0,0,.25)', rays='', inner='', cry=True):
    return ('<div class="scr"><div class="blur"></div><div class="veil" style="background:' + veil + '"></div>'
            + (f'<div class="rays" style="{rays}"></div>' if rays else '') + '<div class="vign"></div>' + inner
            + ('<div class="cry chip"><span class="i" style="background-image:var(--cry)"></span>12,450</div>' if cry else '') + '</div>')


WHITE_RAYS = 'background:repeating-conic-gradient(from 0deg,rgba(255,255,255,.22) 0 7deg,rgba(255,255,255,0) 7deg 18deg)'
BLUE_RAYS = 'background:repeating-conic-gradient(from 3deg,rgba(90,180,255,.55) 0 7deg,rgba(90,180,255,0) 7deg 16deg)'
GOLD_RAYS = 'background:repeating-conic-gradient(from 3deg,rgba(255,205,70,.65) 0 7deg,rgba(255,170,40,0) 7deg 15deg)'
Q = '<div class="queue"><div class="q now"></div><div class="q"></div><div class="q"></div></div>'
SKIP = '<div class="bot"><span class="btn gr sm">SKIP</span></div>'

GREEN, ORANGE = '#4fbf5a', '#ff9a3c'

F1 = stage(rays=WHITE_RAYS, inner='<div class="egg" style="top:44%"></div>'
           '<div style="position:absolute;left:50%;top:76%;width:170px;height:26px;transform:translate(-50%,-50%);background:rgba(0,0,0,.25);border-radius:50%"></div>'
           '<div class="word" style="top:24px"><span class="chip">Egg 1 of 3</span></div>' + Q + SKIP)
F2 = stage(rays=WHITE_RAYS, inner=bucket(250, 120, 38, GREEN) + bucket(615, 120, -38, ORANGE)
           + '<div class="egg"></div>'
           + f'<div class="paint">{blobs(GREEN, 9, seed=1, size=(40, 90))}</div>'
           + f'<div style="position:absolute;left:330px;top:150px;width:150px;height:40px;background:{GREEN};border:3px solid #2e261e;border-radius:40px;transform:rotate(28deg)"></div>'
           + droplets(GREEN, 470, 270, 12, 3) + '<div class="word" style="top:24px"><span class="chip">Egg 1 of 3</span></div>' + Q + SKIP)
F3 = stage(rays=WHITE_RAYS, inner=bucket(615, 120, -48, ORANGE)
           + f'<div class="egg"></div><div class="paint" style="background:{GREEN}">{blobs(ORANGE, 11, seed=7, size=(22, 46))}</div>'
           + droplets(ORANGE, 480, 250, 10, 5)
           + '<div class="word" style="top:24px"><span class="chip">Green</span> <span class="chip">Orange spots</span></div>' + Q + SKIP)

CRACKS = ('<svg style="position:absolute;left:385px;top:175px" width="190" height="245"><g fill="none" stroke-linejoin="round">'
          '<polyline points="20,120 55,100 75,130 100,92 125,128 150,104 175,124" stroke="#fff7c0" stroke-width="12" opacity=".8"/>'
          '<polyline points="20,120 55,100 75,130 100,92 125,128 150,104 175,124" stroke="#2e261e" stroke-width="4"/>'
          '<polyline points="100,92 92,60 108,34" stroke="#fff7c0" stroke-width="9" opacity=".8"/><polyline points="100,92 92,60 108,34" stroke="#2e261e" stroke-width="3"/></g></svg>')
F4 = stage(veil='rgba(0,20,60,.55)', rays=BLUE_RAYS, inner=f'<div class="egg" style="transform:translate(-50%,-50%) rotate(-7deg)"></div><div class="paint" style="background:{GREEN};transform:translate(-50%,-50%) rotate(-7deg)">{blobs(ORANGE, 11, seed=7, size=(22, 46))}</div>'
           + CRACKS + '<div style="position:absolute;left:50%;top:47%;width:340px;height:340px;transform:translate(-50%,-50%);border-radius:50%;background:radial-gradient(circle,rgba(150,210,255,.0) 40%,rgba(150,210,255,.5) 55%,rgba(150,210,255,0) 70%)"></div>'
           + '<div class="word" style="top:24px"><span class="chip">Something rare...</span></div>' + Q + SKIP)

SHARDS = ''
for k in range(12):
    a = k * 30 + RNG.uniform(-10, 10)
    d = RNG.uniform(150, 260)
    x, y = 480 + math.cos(math.radians(a)) * d, 255 + math.sin(math.radians(a)) * d
    c = GREEN if k % 3 else ORANGE
    SHARDS += (f'<div style="position:absolute;left:{x:.0f}px;top:{y:.0f}px;width:{RNG.uniform(34, 56):.0f}px;height:{RNG.uniform(30, 48):.0f}px;'
               f'background:{c};border:3px solid #2e261e;clip-path:polygon(0 20%,60% 0,100% 45%,70% 100%,10% 85%);transform:rotate({RNG.uniform(0, 360):.0f}deg)"></div>')
F5 = stage(veil='rgba(255,255,255,.55)', rays=BLUE_RAYS, inner='<div style="position:absolute;left:50%;top:47%;width:300px;height:300px;transform:translate(-50%,-50%);border-radius:50%;background:radial-gradient(circle,#fff 0,#fff 35%,rgba(160,215,255,.85) 55%,rgba(160,215,255,0) 72%)"></div>'
           + '<div style="position:absolute;left:50%;top:47%;width:520px;height:520px;transform:translate(-50%,-50%);border-radius:50%;border:10px solid rgba(160,215,255,.8)"></div>' + SHARDS, cry=False)
F6 = stage(veil='rgba(0,20,60,.45)', rays=BLUE_RAYS, inner='<div class="banner" style="top:30px;background:#3d8bfd"><span class="ow" style="font-size:46px">RARE!</span></div>'
           + '<div style="position:absolute;left:50%;top:50%;width:400px;height:300px;transform:translate(-50%,-50%);background:var(--trice) center/contain no-repeat;filter:drop-shadow(0 12px 10px rgba(0,0,0,.35))"></div>'
           + ''.join(f'<div style="position:absolute;left:{x}px;top:{y}px;width:16px;height:16px;background:#fff;clip-path:polygon(50% 0,62% 38%,100% 50%,62% 62%,50% 100%,38% 62%,0 50%,38% 38%)"></div>' for x, y in [(250, 170), (700, 200), (300, 380), (690, 360), (420, 120)])
           + '<div class="word" style="top:404px"><span class="chip" style="font-size:24px">Triceratops</span> <span class="chip">Green · Orange spots</span> <span class="chip">1 in 770 eggs</span></div>' + Q
           + '<div class="bot"><span class="btn gr sm">SKIP</span><span class="btn">NEXT EGG</span></div>')
F7 = stage(veil='rgba(10,0,40,.82)', rays='', inner=''.join(
    f'<svg style="position:absolute;left:{x}px;top:{y}px" width="120" height="200"><polyline points="60,0 40,70 72,80 30,200" fill="none" stroke="#ffe27a" stroke-width="8" stroke-linejoin="round"/><polyline points="60,0 40,70 72,80 30,200" fill="none" stroke="#fff" stroke-width="3"/></svg>'
    for x, y in [(250, 60), (600, 40), (380, 280), (560, 300)])
    + f'<div class="egg" style="filter:drop-shadow(0 0 30px #ffd34d)"></div><div class="paint" style="background:#7a4bd6">{blobs("#ffd34d", 10, seed=11, size=(22, 46))}</div>'
    + '<div class="word" style="top:24px"><span class="chip">The egg is glowing gold...</span></div>' + SKIP, cry=False)
F8 = stage(veil='rgba(60,30,0,.35)', rays=GOLD_RAYS, inner='<div class="banner" style="top:26px;background:#f0a500;transform:translateX(-50%) rotate(-3deg)"><span class="ow" style="font-size:58px">LEGENDARY!</span></div>'
           + ''.join(f'<div style="position:absolute;left:{x}px;top:{y}px;width:12px;height:18px;background:{c};border:2px solid #2e261e;border-radius:3px;transform:rotate({r}deg)"></div>'
                     for x, y, c, r in [(180, 140, '#ff6b6b', 20), (250, 330, '#4fc3f7', -30), (720, 150, '#9ccc65', 40), (790, 340, '#ffd54f', -10), (140, 400, '#ba68c8', 60), (830, 230, '#ff8a65', 15), (330, 110, '#ffd54f', -40), (640, 430, '#4fc3f7', 30)])
           + '<div style="position:absolute;left:50%;top:55%;width:460px;height:360px;transform:translate(-50%,-50%);background:var(--trex) center/contain no-repeat"></div>'
           + '<div class="word" style="top:450px"><span class="chip" style="font-size:24px">T-Rex</span> <span class="chip" style="background:#ffd36b">Shiny ✦</span> <span class="chip">1 in 4,000 eggs</span></div>'
           + '<div class="bot"><span class="btn go">AWESOME!</span></div>')
F9 = stage(veil='rgba(0,0,0,.35)', rays=WHITE_RAYS, inner='<div class="card" style="top:40px;width:620px;height:360px">'
           '<div style="position:absolute;top:-30px;left:50%;transform:translateX(-50%)"><span class="ow" style="font-size:40px;white-space:nowrap">You got 3 dinos!</span></div>'
           + ''.join(f'<div style="position:absolute;left:{x}px;top:50px;width:180px;height:220px;border:4px solid {b};border-radius:14px;background:#fffdf5">'
                     f'<div style="position:absolute;inset:10px 10px 50px;background:var(--{p}) center/contain no-repeat"></div>'
                     f'<div style="position:absolute;bottom:10px;left:0;right:0;text-align:center"><span class="chip" style="font-size:15px;background:{c};color:#fff;-webkit-text-stroke:1px #2e261e">{w}</span></div></div>'
                     for x, p, w, c, b in [(14, 'compy', 'Common', '#9aa3ad', '#2e261e'), (214, 'trice', 'Rare', '#3d8bfd', '#3d8bfd'), (414, 'trex', 'Legendary', '#f0a500', '#f0a500')])
           + '<div style="position:absolute;bottom:16px;left:0;right:0;display:flex;justify-content:center;gap:14px"><span class="btn gr sm">SEE DINOS</span><span class="btn">HATCH AGAIN</span><span class="btn sm">x3</span></div></div>')

BODY = f"""<h1>Be Dino! hatch, storyboard v2</h1>
<div class="sub">From 4 top-game videos (Pet Simulator 99, Adopt Me, Bubble Gum Simulator Infinity): one big hero egg, a build-up that grows with rarity, a
white flash before every reveal, shell shards bursting out, the pet huge with its name banner above, bigger shows for rarer eggs (PS99 rare = a dark
cut-scene with lightning). Ours adds what they don't have: <b>paint buckets that splash the egg's real colours and pattern on it</b>. Full screen, kit buttons.
Paint, cracks, shards and buckets here are sketches of the beats; the game gets Blender / generated art.</div>
<div class="lbl">1 (0.0 s) A plain egg drops in and bounces, full screen, world blurred and darkened at the edges</div>{F1}
<div class="note">Egg ~45% of the screen height (the hero), soft shadow, slow white rays. Egg counter chip top, egg queue bottom-left, SKIP bottom-right (grey kit button).</div>
<div class="lbl">2 (0.6-1.6 s) Bucket 1 tips in and SPLASHES: real blobs of paint hit the egg and spread to colour 1, drops fly off</div>{F2}
<div class="note">3D bucket model (new), a paint stream, 4-6 splat blobs landing one after another, each hit squashes the egg; droplets arc away with gravity and fade.</div>
<div class="lbl">3 (1.6-2.6 s) Bucket 2 splashes the second colour as the PATTERN (spots / stripes / bands), colour + pattern chips pop</div>{F3}
<div class="lbl">4 (2.6-4.5 s) Charge: the egg shakes harder and faster, cracks spread with light leaking through, the screen tints to the rarity colour</div>{F4}
<div class="note">The rarity shows here first (blue = Rare): background colour, light ring, a gentle push-in of the camera. A hint chip builds tension.</div>
<div class="lbl">5 (4.5 s) BURST: white flash (0.15 s), painted shell shards fly out, a coloured shock ring</div>{F5}
<div class="note">The shards wear the egg's own paint. The flash is soft (no strobe), 0.15 s like PS99 / Bubble Gum Simulator.</div>
<div class="lbl">6 (4.7 s) Reveal: the dino pops in BIG (about 60% of the screen), the rarity banner drops in above it, chips below</div>{F6}
<div class="note">Banner = rarity colour plate with the outlined word (like PS99's name banner). NEXT EGG green, SKIP grey. Common: auto-next after ~1.5 s.</div>
<div class="lbl">7 Legendary / Mythic build-up: a dark cut-scene, lightning, the egg glowing gold (about 6-8 s instead of 4)</div>{F7}
<div class="lbl">8 Legendary reveal: gold rays, confetti, tilted gold banner, one big gold AWESOME! button (no auto-skip)</div>{F8}
<div class="lbl">9 End of the batch: a cream card with every dino, HATCH AGAIN (and x3) green, SEE DINOS grey</div>{F9}
<div class="note">Timing ladder: Common ~3 s total (paint 1 s, crack 0.5 s), Uncommon ~3.5 s, Rare ~5 s, Epic ~6 s, Legendary ~8 s, Mythic ~10 s. SKIP always works; Reduce Motion: no shake, no lightning, fades instead of bursts.</div>"""

html = ('<!doctype html><html><head><meta charset="utf-8">'
        '<link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&display=swap" rel="stylesheet">'
        '<style>' + css + STYLE + '</style></head><body>' + BODY + '</body></html>')
open(OUT, 'w', encoding='utf-8').write(html)
print(OUT, len(html))
