#!/usr/bin/env python3
"""Synthesize the original Be Dino! sound-effect pack (no external samples).

Writes 16-bit mono 44.1 kHz WAVs + manifest.json to assets/audio/sfx/ and a
contact sheet to docs/evidence/2026-10-14-sfx-pack/sfx-overview.png.

  python tools/generate_sfx.py            # write everything
  python tools/generate_sfx.py --check    # regenerate in memory, compare to disk
"""
import argparse, io, json, sys, wave
from pathlib import Path
import numpy as np

SR = 44100
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "audio" / "sfx"
SHEET = ROOT / "docs" / "evidence" / "2026-10-14-sfx-pack" / "sfx-overview.png"
PEAK_DB = -3.0
TOL_LSB = 3  # cross-platform float tolerance for --check


def t_(d):
    return np.arange(int(d * SR)) / SR


def env(n, a=0.005, d=0.15, curve=4.0):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-curve * t / max(d, 1e-3))


def sine(f, d):
    return np.sin(2 * np.pi * f * t_(d))


def sweep(f0, f1, d):
    t = t_(d)
    f = f0 * (f1 / f0) ** (t / d)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def fm(fc, ratio, idx, d, decay=0.2):
    t = t_(d)
    i = idx * np.exp(-t / decay)
    return np.sin(2 * np.pi * fc * t + i * np.sin(2 * np.pi * fc * ratio * t))


def noise(rng, d):
    return rng.standard_normal(int(d * SR))


def lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    s = 0.0
    for i in range(len(x)):
        s = (1 - a) * x[i] + a * s
        y[i] = s
    return y


def hp(x, fc):
    return x - lp(x, fc)


def bp(x, lo, hi):
    return lp(hp(x, lo), hi)


def place(buf, x, at):
    i = int(at * SR)
    n = min(len(x), len(buf) - i)
    if n > 0:
        buf[i:i + n] += x[:n]


def tone(f, d, vol=1.0, a=0.004, dec=0.15, kind="sine"):
    x = sine(f, d)
    if kind == "bell":
        x = 0.7 * x + 0.3 * sine(f * 2.76, d) * np.exp(-t_(d) / (dec * 0.4))
    if kind == "soft":
        x = x + 0.25 * sine(2 * f, d)
    return vol * x * env(len(x), a, dec)


def reverb(rng, x, tail=0.4, mix=0.25):
    n = int(tail * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-6.5 * t / tail)
    ir[0] = 0
    ir = lp(ir, 5000)
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
    L = len(x) + n
    w = np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)
    y = np.zeros(L)
    y[:len(x)] += x
    return y + mix * w


def note(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def fade(x, i=0.004, o=0.02):
    x = x.copy()
    a = int(i * SR)
    b = int(o * SR)
    x[:a] *= np.linspace(0, 1, a, endpoint=False)
    x[-b:] *= np.linspace(1, 0, b)
    return x


# ---- sounds: each fn(rng) -> float array ----
def hatch_crack(r):
    b = np.zeros(int(0.45 * SR))
    for at, f, v in [(0, 2600, 1), (0.09, 3400, .8), (0.19, 2100, .9), (0.3, 4200, .6)]:
        n = int(.06 * SR)
        place(b, v * bp(noise(r, .06), f * .6, f * 1.4) * env(n, .0005, .02, 6), at)
        place(b, .4 * v * sine(f / 5, .05) * env(int(.05 * SR), .0005, .03), at)
    return b


def hatch_common(r):
    b = np.zeros(int(.5 * SR))
    for i, m in enumerate([72, 76]):
        place(b, tone(note(m), .4, .6, .004, .12, "soft"), i * .07)
    return reverb(r, b, .25, .15)


def hatch_rare(r):
    b = np.zeros(int(1.0 * SR))
    for i, m in enumerate([67, 71, 74, 79]):
        place(b, tone(note(m), .7, .5, .004, .25, "bell"), i * .08)
    place(b, bp(noise(r, .5), 5000, 9000) * env(int(.5 * SR), .1, .3, 3) * .12, .2)
    return reverb(r, b, .45, .3)


def hatch_legendary(r):
    b = np.zeros(int(2.0 * SR))
    place(b, sweep(180, 900, 1.1) * np.linspace(.1, .5, int(1.1 * SR)) ** 1.5, 0)
    place(b, bp(noise(r, 1.1), 2000, 7000) * np.linspace(0, .25, int(1.1 * SR)) ** 2, 0)
    for i, m in enumerate([60, 64, 67, 72, 76, 79]):
        place(b, tone(note(m), .8, .35, .004, .35, "bell"), .5 + i * .1)
    for m in (72, 76, 79, 84):
        place(b, tone(note(m), 1.4, .35, .006, .6, "bell"), 1.15)
    place(b, tone(note(48), 1.0, .5, .005, .3), 1.15)
    return reverb(r, b, .45, .3)


def shiny_bang(r):
    b = np.zeros(int(1.2 * SR))
    place(b, bp(noise(r, .15), 3000, 10000) * env(int(.15 * SR), .0005, .06, 5) * .8, 0)
    for _ in range(14):
        f = r.uniform(3500, 9500)
        at = r.uniform(0, .45)
        place(b, tone(f, .35, r.uniform(.12, .3), .002, .09, "bell"), at)
    place(b, tone(note(96), .9, .3, .003, .3, "bell"), .02)
    return reverb(r, b, .5, .3)


def big_thud(r):
    d = .6
    t = t_(d)
    k = np.sin(2 * np.pi * np.cumsum(45 + 90 * np.exp(-t / .05)) / SR) * np.exp(-t / .14)
    n = lp(noise(r, d), 400) * np.exp(-t / .04) * 3
    return k + .5 * n


def pickup(r, m=84):
    return tone(note(m), .14, 1, .002, .05) + tone(note(m + 12), .14, .15, .002, .03)


def pickup_hi(r):
    return pickup(r, 88)


def pickup_lo(r):
    return pickup(r, 80)


def run_start(r):
    b = np.zeros(int(.5 * SR))
    place(b, sweep(300, 1200, .22) * env(int(.22 * SR), .01, .3, 2.5) * .6, 0)
    place(b, bp(noise(r, .25), 800, 4000) * np.linspace(0, 1, int(.25 * SR)) * .1, 0)
    place(b, tone(note(79), .25, .5, .003, .12), .2)
    return b


def run_end(r):
    b = np.zeros(int(.8 * SR))
    for i, m in enumerate([79, 74, 67]):
        place(b, tone(note(m), .4, .45, .004, .2, "soft"), i * .12)
    return reverb(r, b, .3, .2)


def shop_buy(r):
    b = np.zeros(int(.6 * SR))
    place(b, fm(1568, 3.5, 2, .5, .1) * env(int(.5 * SR), .001, .2) * .5, 0)
    place(b, fm(2093, 3.5, 2, .5, .1) * env(int(.5 * SR), .001, .3) * .5, .07)
    return reverb(r, b, .2, .15)


def shop_refresh(r):
    b = np.zeros(int(.9 * SR))
    for i, m in enumerate([81, 88]):
        place(b, tone(note(m), .7, .5, .01, .3, "bell"), i * .13)
    return reverb(r, b, .5, .3)


def weather_start(r):
    d = 1.8
    x = bp(noise(r, d), 300, 1800)
    sw = np.sin(np.pi * np.linspace(0, 1, len(x))) ** 2
    pad = sum(sine(f, d) * .15 for f in (note(55), note(62), note(67)))
    return (x * .6 + pad) * sw


def level_up(r):
    b = np.zeros(int(1.0 * SR))
    for i, m in enumerate([72, 76, 79, 84]):
        place(b, tone(note(m), .5, .45, .003, .18, "bell"), i * .09)
    place(b, tone(note(91), .6, .3, .003, .3, "bell"), .36)
    return reverb(r, b, .4, .25)


def fusion_reveal(r):
    b = np.zeros(int(2.0 * SR))
    bt = 1.2
    n = int(bt * SR)
    place(b, sweep(120, 1400, bt) * np.linspace(.05, .5, n) ** 1.6, 0)
    for k in range(10):
        m = 60 + [0, 4, 7, 12, 16][k % 5] + 12 * (k // 5)
        place(b, tone(note(m), .12, .25, .002, .06), k * .11 + k * k * .004)
    place(b, bp(noise(r, bt), 1500, 6000) * np.linspace(0, .3, n) ** 2, 0)
    place(b, big_thud(r) * .8, bt)
    for m in (60, 64, 67, 72, 79):
        place(b, tone(note(m), .7, .3, .004, .4, "bell"), bt + .02)
    place(b, bp(noise(r, .5), 5000, 10000) * env(int(.5 * SR), .002, .3, 4) * .15, bt)
    return reverb(r, b, .4, .3)


def ui_click(r):
    return tone(1900, .05, 1, .0008, .012) + .5 * bp(noise(r, .05), 2000, 6000) * env(int(.05 * SR), .0003, .01)


SOUNDS = [
    # name, fn, volume, jitter, trigger
    ("hatch_crack", hatch_crack, .6, .08, "Egg starts cracking open (hatch sequence beat 1)."),
    ("hatch_common", hatch_common, .6, .05, "Common dino revealed; soft two-note chirp, safe to repeat every second."),
    ("hatch_rare", hatch_rare, .7, .04, "Rare dino revealed; brighter bell arpeggio."),
    ("hatch_legendary", hatch_legendary, .8, 0.0, "Legendary reveal; rising stinger with sparkle payoff. Use sparingly."),
    ("shiny_bang", shiny_bang, .65, .05, "Shiny / gold variant reveal; high sparkly shimmer layered on the hatch sound."),
    ("big_thud", big_thud, .7, .06, "Heavy landing, big dino stomp or boss egg drop; low punch."),
    ("pickup", pickup, .35, .12, "Food or item collected; very short, use rate jitter on every play."),
    ("pickup_hi", pickup_hi, .35, .1, "Pickup pitch variant (chain/combo, higher)."),
    ("pickup_lo", pickup_lo, .35, .1, "Pickup pitch variant (lower, alternate)."),
    ("run_start", run_start, .5, .04, "PvP/run round begins; rising whoosh and ping."),
    ("run_end", run_end, .5, .03, "Run ends; gentle descending three notes."),
    ("shop_buy", shop_buy, .55, .06, "Purchase confirmed; coin-like clink."),
    ("shop_refresh", shop_refresh, .45, .03, "Potion shop stock refreshed; soft chime."),
    ("weather_start", weather_start, .4, .03, "Weather event begins; soft wind swell."),
    ("level_up", level_up, .6, .02, "Player level up; short rising arpeggio."),
    ("fusion_reveal", fusion_reveal, .8, 0.0, "Fusion result reveal; ~2 s build-up then payoff hit."),
    ("ui_click", ui_click, .35, .08, "Any button press; tiny tick."),
]


def render(seed):
    out = {}
    for i, (name, fn, *_rest) in enumerate(SOUNDS):
        rng = np.random.default_rng([seed, i])
        x = np.nan_to_num(fn(rng))
        x = fade(x, .003, min(.03, len(x) / SR / 4))
        x = x / np.max(np.abs(x)) * 10 ** (PEAK_DB / 20)
        out[name] = np.round(x * 32767).astype("<i2")
    return out


def wav_bytes(pcm):
    bio = io.BytesIO()
    with wave.open(bio, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return bio.getvalue()


def manifest(pcms):
    items = []
    for name, _, vol, jit, trig in SOUNDS:
        p = pcms[name]
        items.append({
            "name": name, "file": f"{name}.wav",
            "durationSeconds": round(len(p) / SR, 3),
            "peakDbfs": round(float(20 * np.log10(np.max(np.abs(p.astype(float))) / 32768)), 2),
            "suggestedVolume": vol, "suggestedRateJitter": jit, "trigger": trig})
    return {"sampleRate": SR, "bitDepth": 16, "channels": 1, "sounds": items}


def sheet(pcms, path):
    from PIL import Image, ImageDraw
    cw, ch = 640, 150
    rows = (len(SOUNDS) + 1) // 2
    im = Image.new("RGB", (2 * cw, rows * ch), (24, 26, 34))
    d = ImageDraw.Draw(im)
    for k, (name, *_rest) in enumerate(SOUNDS):
        x0, y0 = (k % 2) * cw, (k // 2) * ch
        x = pcms[name].astype(float) / 32768
        d.text((x0 + 8, y0 + 4), f"{name}  {len(x) / SR:.2f}s", fill=(240, 240, 240))
        w, wy, wh = cw - 20, y0 + 20, 50
        for i, s in enumerate(np.array_split(np.abs(x), w)):
            h = int(wh / 2 * (s.max() if len(s) else 0))
            d.line([(x0 + 10 + i, wy + wh // 2 - h), (x0 + 10 + i, wy + wh // 2 + h)], fill=(110, 200, 255))
        n = 512
        hop = max(1, (len(x) - n) // w)
        win = np.hanning(n)
        sy = wy + wh + 6
        sh = ch - (sy - y0) - 6
        for i in range(w):
            fr = x[i * hop:i * hop + n]
            if len(fr) < n:
                break
            m = np.log10(np.abs(np.fft.rfft(fr * win))[:200] + 1e-6)
            for j in range(sh):
                v = float(np.clip((m[int(j / sh * 180)] + 2.5) / 3.5, 0, 1))
                d.point((x0 + 10 + i, sy + sh - 1 - j), fill=(int(255 * v), int(150 * v * v), int(440 * (1 - v) * v)))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=1014)
    ap.add_argument("--check", action="store_true", help="verify files on disk match regeneration")
    ap.add_argument("--no-sheet", action="store_true")
    a = ap.parse_args()
    pcms = render(a.seed)
    man = manifest(pcms)
    if a.check:
        bad = []
        for name, p in pcms.items():
            f = OUT / f"{name}.wav"
            if not f.exists():
                bad.append(f"missing {f.name}")
                continue
            with wave.open(str(f)) as w:
                q = np.frombuffer(w.readframes(w.getnframes()), "<i2")
            if len(q) != len(p) or np.max(np.abs(q.astype(int) - p.astype(int))) > TOL_LSB:
                bad.append(f"stale {f.name}")
        mf = OUT / "manifest.json"
        if not mf.exists() or [s["name"] for s in json.loads(mf.read_text())["sounds"]] != [s["name"] for s in man["sounds"]]:
            bad.append("stale manifest.json")
        print("\n".join(bad) or f"sfx pack OK ({len(pcms)} sounds)")
        return 1 if bad else 0
    OUT.mkdir(parents=True, exist_ok=True)
    for name, p in pcms.items():
        (OUT / f"{name}.wav").write_bytes(wav_bytes(p))
    (OUT / "manifest.json").write_text(json.dumps(man, indent=2) + "\n")
    if not a.no_sheet:
        sheet(pcms, SHEET)
    print(f"wrote {len(pcms)} sounds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
