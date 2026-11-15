"""v3 boards: every surface v2 did not cover. Reuses STYLE / V / u from the v2 generator (exec'd first)."""
import sys
exec(open(sys.argv[4], encoding='utf-8').read().split('\nHUD = """')[0])  # defines u, V, css, STYLE, ROOT, OUT, WORLD

V2 = {'food_b': u('resources/ui/v2/items/food-berry-v1.png', 120), 'food_f': u('resources/ui/v2/items/food-fruit-v1.png', 120),
      'food_e': u('resources/ui/v2/items/food-egg-v1.png', 120), 'food_a': u('resources/ui/v2/items/food-amber-v1.png', 120),
      'heart': u('resources/ui/v2/icons/hud-heart-v1.png', 96), 'warn': u('resources/ui/v2/icons/notify-warning-v1.png', 96),
      'dstar': u('resources/ui/v2/icons/notify-star-v1.png', 96), 'pouch': u('resources/ui/v2/icons/crystals-m-v1.png', 120),
      'gold': u('resources/ui/v2/icons/tier-gold-v1.png', 96) if False else u('resources/ui/v2/layers/mutation-gold-v1.png', 96),
      'bolt': u('resources/ui/v2/icons/mutation-charged-v1.png', 96)}
css2 = ':root{' + ''.join('--%s:url(%s);' % (k, v) for k, v in V2.items()) + '}'
EXTRA = """
.big{font-size:44px}
.step{background:#fff7e3;border:3px solid #1d1d1d;border-radius:14px;padding:10px;text-align:center;display:flex;flex-direction:column;align-items:center;gap:6px}
.num{width:40px;height:40px;border-radius:50%;background:#ffd76a;border:3px solid #1d1d1d;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:22px}
.day{width:84px;height:104px;background:#fff7e3;border:3px solid #1d1d1d;border-radius:12px;display:flex;flex-direction:column;align-items:center;justify-content:space-between;padding:6px;box-sizing:border-box;font-weight:700;font-size:15px}
.done{background:#dff7cf}.today{background:#ffd76a;box-shadow:0 0 0 4px #fff7e3,0 0 0 7px #1d1d1d}
.tag{position:absolute;display:flex;align-items:center;gap:6px;z-index:3}
.hp{width:90px;height:12px;border-radius:7px;background:#e7dcc2;border:3px solid #1d1d1d;overflow:hidden}.hp i{display:block;height:100%;width:70%;background:#5ded1f}
"""

LOADING = """<div class="scr" style="background:radial-gradient(circle at 50% 40%,#bfe88f 0,#5f9e3f 60%,#2f5f27 100%)">
<div class="center" style="top:120px"><span class="ow" style="font-size:84px;color:#ffd22b">Be Dino!</span></div>
<div class="center" style="top:236px;width:200px;height:160px;background:var(--compy) center/contain no-repeat"></div>
<div class="center" style="top:420px;width:420px"><div class="panel" style="position:relative;padding:8px 12px"><div class="track" style="width:100%;height:16px"><div class="fill" style="width:55%"></div></div><div class="ink" style="text-align:center;margin-top:6px;font-size:16px">Waking up your dinos...</div></div></div></div>"""

WELCOME = """<div class="scr dim"><div class="win" style="left:110px;right:110px;top:36px;bottom:36px"><div class="wh" style="border-image-source:var(--hdrC)"><span class="ow" style="margin-left:8px">Welcome to Be Dino!</span></div><div class="wx"></div>
<div class="panel" style="left:12px;right:12px;top:64px;bottom:74px;padding:12px;display:grid;grid-template-columns:repeat(3,1fr);gap:12px;box-sizing:border-box">
<div class="step"><div class="num">1</div><span class="i" style="background-image:var(--food_b);width:70px;height:70px"></span><span class="ink" style="font-size:20px">Eat and grow</span><span style="font-size:15px">Walk into food. Eat lots to find eggs!</span></div>
<div class="step"><div class="num">2</div><span class="i" style="background-image:var(--egg);width:70px;height:70px"></span><span class="ink" style="font-size:20px">Catch eggs</span><span style="font-size:15px">Bigger dinos find more eggs.</span></div>
<div class="step"><div class="num">3</div><span class="i" style="background-image:var(--dinos);width:70px;height:70px"></span><span class="ink" style="font-size:20px">Hatch and collect</span><span style="font-size:15px">Go home and see who hatches!</span></div></div>
<div style="position:absolute;left:12px;right:12px;bottom:10px;display:flex;justify-content:center"><span class="btn g">LET'S PLAY</span></div></div></div>"""

SANCT = """<div class="scr dim"><div class="win" style="left:110px;right:110px;top:36px;bottom:36px"><div class="wh" style="border-image-source:var(--hdrC)"><span class="ow" style="margin-left:8px">Home</span></div><div class="wx"></div>
<div class="panel" style="left:12px;width:270px;top:64px;bottom:74px;box-sizing:border-box;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;padding:10px;background:radial-gradient(circle at 50% 40%,#ffe9b8,#f6d58c)"><div style="flex:1;width:100%;background:var(--compy) center/contain no-repeat"></div><span class="chip">Compy &middot; Size 3</span></div>
<div class="panel" style="left:294px;right:12px;top:64px;bottom:74px;padding:14px;box-sizing:border-box">
<div class="ink" style="font-size:24px">Ready for an adventure?</div>
<div class="row"><span>Eggs waiting</span><span class="ink">5</span></div><div class="row"><span>Nest ready in</span><span class="ink">1 h</span></div><div class="row" style="border:0"><span>Today's goal</span><span class="ink">Eat 20 berries</span></div></div>
<div style="position:absolute;left:12px;right:12px;bottom:10px;display:flex;justify-content:flex-end;gap:10px"><span class="btn gr">HATCH EGGS</span><span class="btn g">EXPLORE</span></div></div></div>"""

ODDS = """<div class="scr dim"><div class="win" style="left:150px;right:150px;top:36px;bottom:36px"><div class="wh" style="border-image-source:var(--hdrA)"><span class="ow" style="margin-left:8px">What's in an egg?</span></div><div class="wx"></div>
<div class="panel" style="left:12px;right:12px;top:64px;bottom:74px;padding:12px;box-sizing:border-box">
<div class="row"><span><span class="chip" style="color:#6f7a86">Common</span> Compy, Raptor...</span><span class="ink">9 in 10</span></div>
<div class="row"><span><span class="chip" style="color:#3aa10f">Uncommon</span> Stego, Trice...</span><span class="ink">1 in 12</span></div>
<div class="row"><span><span class="chip" style="color:#1590c0">Rare</span> Spino...</span><span class="ink">1 in 250</span></div>
<div class="row"><span><span class="chip" style="color:#9a3ad0">Epic</span> Brachio...</span><span class="ink">1 in 1,200</span></div>
<div class="row" style="border:0"><span><span class="chip" style="color:#b07800">Legendary</span> T-Rex</span><span class="ink">1 in 5,000</span></div></div>
<div style="position:absolute;left:12px;right:12px;bottom:10px;display:flex;justify-content:flex-end;gap:10px"><span class="btn gr">EXACT %</span><span class="btn gr">BACK</span></div></div></div>"""

FOOD = """<div class="scr dim"><div class="win" style="left:110px;right:110px;top:36px;bottom:36px"><div class="wh" style="border-image-source:var(--hdrC)"><span class="ow" style="margin-left:8px">Food guide</span></div><div class="wx"></div>
<div class="panel" style="left:12px;right:12px;top:64px;bottom:74px;padding:12px;display:grid;grid-template-columns:repeat(4,1fr);gap:12px;box-sizing:border-box">
<div class="step"><span class="i" style="background-image:var(--food_b);width:90px;height:90px"></span><span class="ink" style="font-size:20px">Berries</span><span class="chip">+1 grow</span></div>
<div class="step"><span class="i" style="background-image:var(--food_f);width:90px;height:90px"></span><span class="ink" style="font-size:20px">Fruit</span><span class="chip">+4 grow</span></div>
<div class="step"><span class="i" style="background-image:var(--food_e);width:90px;height:90px"></span><span class="ink" style="font-size:20px">Eggs</span><span class="chip">+15 grow</span></div>
<div class="step"><span class="i" style="background-image:var(--food_a);width:90px;height:90px"></span><span class="ink" style="font-size:20px">Amber</span><span class="chip">+50 grow</span></div></div>
<div style="position:absolute;left:12px;right:12px;bottom:14px;text-align:center"><span class="chip" style="font-size:16px">Eat 500 food for about 12 eggs. Storms add more!</span></div></div></div>"""

WEATHER = """<div class="scr"><div class="center" style="top:96px;text-align:center"><span class="i" style="background-image:var(--bolt);width:90px;height:90px"></span><div><span class="ow big">THUNDERSTORM!</span></div><div style="margin-top:6px"><span class="chip" style="font-size:18px">Special eggs can drop!</span></div></div>
<div class="plate" style="right:14px;top:70px;font-size:16px"><span class="i" style="background-image:var(--bolt);width:22px;height:22px"></span>Storm: 2 min &middot; Eggs +40%</div></div>"""

WORLD = """<div class="scr"><div class="tag" style="left:420px;top:150px;flex-direction:column"><span class="chip" style="font-size:15px">Compy &middot; you</span><div class="hp"><i></i></div></div>
<div class="tag" style="left:150px;top:220px"><span class="ow" style="font-size:24px;color:#ffd22b">+3</span><span class="i" style="background-image:var(--cry);width:26px;height:26px"></span></div>
<div class="tag" style="left:690px;top:230px"><span class="ow" style="font-size:24px">+1 grow</span></div>
<div class="tag" style="left:600px;top:120px"><span class="chip" style="font-size:15px">Raptor &middot; bigger!</span><span class="i" style="background-image:var(--warn);width:26px;height:26px"></span></div>
<div class="tag" style="left:300px;top:330px"><span class="rib">EGG!</span></div></div>"""

STREAK = """<div class="scr dim"><div class="win" style="left:80px;right:80px;top:30px;bottom:30px"><div class="wh" style="border-image-source:var(--hdrA)"><span class="ow" style="margin-left:8px">Daily gifts</span></div><div class="wx"></div>
<div class="panel" style="left:12px;right:12px;top:64px;bottom:74px;padding:14px;box-sizing:border-box">
<div style="display:flex;gap:10px;justify-content:center">
<div class="day done">Day 1<span class="i" style="background-image:var(--cry);width:40px;height:40px"></span>+10</div><div class="day done">Day 2<span class="i" style="background-image:var(--cry);width:40px;height:40px"></span>+15</div>
<div class="day today">Day 3<span class="i" style="background-image:var(--egg);width:40px;height:40px"></span>Egg!</div><div class="day">Day 4<span class="i" style="background-image:var(--cry);width:40px;height:40px"></span>+20</div>
<div class="day">Day 5<span class="i" style="background-image:var(--potion);width:40px;height:40px"></span>Potion</div><div class="day">Day 6<span class="i" style="background-image:var(--cry);width:40px;height:40px"></span>+30</div>
<div class="day">Day 7<span class="i" style="background-image:var(--pouch);width:48px;height:48px"></span>Big gift</div></div>
<div class="ink" style="text-align:center;margin-top:14px;font-size:16px">Today's goals</div>
<div class="row"><span>Eat 50 berries</span><span class="ink">32/50</span></div><div class="row" style="border:0"><span>Hatch 5 eggs</span><span class="ink">5/5 &#10003;</span></div></div>
<div style="position:absolute;left:12px;right:12px;bottom:10px;display:flex;justify-content:flex-end;gap:10px"><span class="btn g">CLAIM DAY 3</span></div></div></div>"""

DEFEAT = """<div class="scr dim"><div class="win" style="left:240px;right:240px;top:90px;bottom:90px"><div class="wh" style="border-image-source:var(--hdrC)"><span class="ow" style="margin-left:8px">Oops, a bigger dino!</span></div><div class="wx"></div>
<div class="panel" style="left:12px;right:12px;top:64px;bottom:74px;padding:14px;box-sizing:border-box;display:flex;align-items:center;gap:14px">
<span class="i" style="background-image:var(--heart);width:80px;height:80px"></span><div><div class="ink" style="font-size:20px">Your eggs are safe!</div><div style="font-size:16px;color:#7a6a4e">12 eggs and 30 crystals are saved.</div></div></div>
<div style="position:absolute;left:12px;right:12px;bottom:10px;display:flex;justify-content:flex-end;gap:10px"><span class="btn gr">HOME</span><span class="btn g">PLAY AGAIN</span></div></div></div>"""

BOARDS = [('8 Loading: the game starts warm, not dark', LOADING), ('9 Welcome: three steps with pictures', WELCOME),
          ('10 Home (Sanctuary): your dino + what is waiting', SANCT), ('11 Egg chances in kid words (exact % one tap away)', ODDS),
          ('12 Food guide with the real food art', FOOD), ('13 Weather: one font, icon, cream info chip', WEATHER),
          ('14 World labels: pickups, names, health, warnings', WORLD), ('15 Daily gifts + goals (planned, BD-1197)', STREAK),
          ('16 Gentle defeat: eggs are safe', DEFEAT)]
BODY = '<h1>Be Dino! style tile v3: every other surface</h1><div class="sub">Same rules as v1/v2. Boards 1-7 are in v2; these cover the rest of the game. Numbers are examples, not balance.</div><div class="grid">' + ''.join(
    '<div><div class="lbl">%s</div>%s</div>' % (t, b) for t, b in BOARDS) + '</div>'
html = ('<!doctype html><html><head><meta charset="utf-8"><link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&display=swap" rel="stylesheet">'
        '<style>' + css + css2 + STYLE + EXTRA + '</style></head><body>' + BODY + '</body></html>')
open(OUT, 'w', encoding='utf-8').write(html)
print(len(html))
