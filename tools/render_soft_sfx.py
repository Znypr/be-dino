"""Re-render softer candidates of the two harshest SFX files with ffmpeg (BD-166 / BD-637, docs/161).

    python tools/render_soft_sfx.py                                  # writes docs/evidence/2026-10-18-audio-fix/*.wav
    python tools/render_soft_sfx.py --out build/soft --check          # also fail if a candidate is not ok / calm

Reads assets/audio/sfx/*.wav (never changes them) and writes NEW files. Nothing is uploaded to Roblox and no asset id
changes: the owner listens first (docs/161 section "Upload steps"). Needs ffmpeg (default C:/ffmpeg/bin, or FFMPEG=); exits
0 with a note when ffmpeg is missing so CI can run it.
"""
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets/audio/sfx"
DEFAULT_OUT = ROOT / "docs/evidence/2026-10-18-audio-fix"

# name -> (source file, ffmpeg filter chain). asetrate N then aresample 44100 = play N/44100 times as fast (pitch AND length).
# Every chain ends with a 10-15 ms fade-in so the first sample is not a click (the tool flags attacks under 5 ms).
RECIPES = {
    # rate .75 (about 5 semitones lower), low-pass 4 kHz (5 kHz alone left harshness at 38, still "bit bright"), 10 ms fade-in.
    "shop_buy_soft": ("shop_buy", "asetrate=33075,aresample=44100,lowpass=f=4000,afade=t=in:d=0.01"),
    # rate .70, two low-pass stages at 3.5 kHz (one stage left harshness at 80+: it is a spike, not just bright), 10 ms fade-in.
    "shiny_bang_soft": ("shiny_bang", "asetrate=30870,aresample=44100,lowpass=f=3500,lowpass=f=3500,afade=t=in:d=0.01"),
}


def find_ffmpeg():
    env = os.environ.get("FFMPEG")
    for cand in (env, shutil.which("ffmpeg"), "C:/ffmpeg/bin/ffmpeg.exe"):
        if cand and (Path(cand).exists() or shutil.which(cand)):
            return cand
    return None


def render(ffmpeg, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    made = []
    for name, (src, chain) in RECIPES.items():
        dst = out_dir / (name + ".wav")
        cmd = [ffmpeg, "-v", "error", "-y", "-i", str(SRC / (src + ".wav")), "-af", chain, "-ar", "44100", "-ac", "1",
               "-c:a", "pcm_s16le", str(dst)]
        subprocess.run(cmd, check=True)
        made.append(dst)
    return made


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="folder for the new WAV files")
    ap.add_argument("--check", action="store_true", help="fail unless every candidate measures ok or calm")
    args = ap.parse_args(argv)
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("ffmpeg not found: nothing rendered (set FFMPEG=)")
        return 0
    made = render(ffmpeg, Path(args.out))
    total = sum(p.stat().st_size for p in made)
    for p in made:
        print("wrote %s (%d KB)" % (p, p.stat().st_size // 1024))
    if total > 5 * 1024 * 1024:
        print("FAIL: candidates are %d MB, over the 5 MB limit" % (total // 1048576))
        return 1
    if args.check:
        sys.path.insert(0, str(ROOT / "tools"))
        import audio_report as ar
        bad = []
        for p in made:
            r = ar.analyze(p)
            print("%s: verdict %s, harsh %.0f, LUFS-M %.1f" % (p.name, r["verdict"], r["harsh_score"], r["lufs_m"]))
            if r["verdict"] not in ("ok", "calm"):
                bad.append(p.name)
        if bad:
            print("FAIL: not ok/calm:", ", ".join(bad))
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
