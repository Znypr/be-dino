"""Trailer clip editor (docs/133): trim, concatenate with crossfades, placeholder title cards, 16:9 / 9:16 export, music, GIF.

    python tools/demo/edit.py trim IN OUT --start 2 --end 8
    python tools/demo/edit.py build CLIP [CLIP...] --out out/demo --intro "NEW: Cave" --outro "Be Dino!" \
        --aspects 16:9 9:16 [--music song.mp3] [--crossfade 0.5] [--focus 0.5] [--pad] [--gif]
    python tools/demo/edit.py gif IN OUT.gif
    python tools/demo/edit.py selftest

Title cards are PLACEHOLDERS rendered from text with Pillow in the brand colours (docs/114 section 5.1) and say so in a small
corner tag. Real branding art is an owner task; pass --intro-image / --outro-image to use finished art instead.
No music is bundled: pass --music PATH to a track you have the rights to.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_FFMPEG = "C:/ffmpeg/bin/ffmpeg"
SIZES = {"16:9": (1920, 1080), "9:16": (1080, 1920)}
PANEL = (42, 40, 53)    # docs/114 5.1 panel #2A2835
GOLD = (255, 210, 43)   # #FFD22B
GREEN = (93, 237, 31)   # #5DED1F


def find_tool(name: str) -> str:
    env = os.environ.get(name.upper())
    if env:
        return env
    base = DEFAULT_FFMPEG.replace("ffmpeg", name)
    if Path(base + ".exe").exists():
        return base
    return shutil.which(name) or name


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError("command failed: " + " ".join(cmd) + "\n" + proc.stderr[-2000:])


def probe(path: str) -> dict:
    out = subprocess.run(
        [find_tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
         "-of", "json", path], capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    return {"width": data["streams"][0]["width"], "height": data["streams"][0]["height"], "duration": float(data["format"]["duration"])}


def fit_filter(size: tuple[int, int], pad: bool = False, focus: float = 0.5, fps: int = 60) -> str:
    """Scale to cover and crop (focus 0..1 picks which part of an overflowing axis is kept), or letterbox with --pad."""
    w, h = size
    if pad:
        core = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x2A2835"
    else:
        f = min(1.0, max(0.0, focus))
        core = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                f"crop={w}:{h}:(iw-{w})*{f:g}:(ih-{h})*{f:g}")
    return f"{core},setsar=1,fps={fps},format=yuv420p"


def trim(src: str, dst: str, start: float, end: float | None) -> None:
    cmd = [find_tool("ffmpeg"), "-y", "-ss", f"{start:g}", "-i", src]
    if end is not None:
        cmd += ["-t", f"{end - start:g}"]
    run(cmd + ["-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", dst])


def make_card_png(text: str, dst: str, size: tuple[int, int], subtitle: str = "", placeholder: bool = True) -> None:
    from PIL import Image, ImageDraw, ImageFont

    w, h = size
    img = Image.new("RGB", size, PANEL)
    draw = ImageDraw.Draw(img)

    def font(px: int):
        for candidate in ("C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf", "DejaVuSans-Bold.ttf"):
            try:
                return ImageFont.truetype(candidate, px)
            except OSError:
                continue
        return ImageFont.load_default(px)

    big = font(int(min(w, h) * 0.11))
    small = font(int(min(w, h) * 0.04))
    safe_x = int(w * (0.06 if h > w else 0.05))
    # Wrap the title to the safe width.
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=big) <= w - 2 * safe_x or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    line_h = int(big.size * 1.2)
    y = (h - line_h * len(lines)) // 2 - (int(small.size * 1.5) if subtitle else 0)
    for line in lines:
        tw = draw.textlength(line, font=big)
        draw.text(((w - tw) / 2 + 4, y + 4), line, font=big, fill=(13, 15, 20))  # outline colour shadow
        draw.text(((w - tw) / 2, y), line, font=big, fill=GOLD)
        y += line_h
    if subtitle:
        tw = draw.textlength(subtitle, font=small)
        draw.text(((w - tw) / 2, y + small.size * 0.5), subtitle, font=small, fill=GREEN)
    if placeholder:
        draw.text((safe_x, h - int(h * 0.05) - small.size), "PLACEHOLDER CARD - real art is an owner task", font=small, fill=(128, 142, 158))
    img.save(dst)


def card_clip(text: str, dst: str, size: tuple[int, int], seconds: float, fps: int, subtitle: str = "", image: str | None = None) -> None:
    png = image
    tmp = None
    if png is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        png = tmp.name
        make_card_png(text, png, size, subtitle)
    try:
        vf = fit_filter(size, pad=False, fps=fps) if image else f"fps={fps},format=yuv420p"
        run([find_tool("ffmpeg"), "-y", "-loop", "1", "-framerate", str(fps), "-i", png, "-t", f"{seconds:g}", "-vf", vf,
             "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", dst])
    finally:
        if tmp:
            os.unlink(tmp.name)


def concat_filter(durations: list[float], size: tuple[int, int], pad: bool, focus: float, fps: int, xfade: float) -> tuple[str, float]:
    """Filter graph that normalises every input and chains xfade crossfades. Returns (graph, total duration)."""
    n = len(durations)
    parts = [f"[{i}:v]{fit_filter(size, pad, focus, fps)}[v{i}]" for i in range(n)]
    if n == 1:
        return ";".join(parts) + ";[v0]null[outv]", durations[0]
    total = durations[0]
    prev = "v0"
    for i in range(1, n):
        if xfade >= min(durations[i], total):
            raise ValueError("crossfade longer than a clip")
        offset = total - xfade
        label = "outv" if i == n - 1 else f"x{i}"
        parts.append(f"[{prev}][v{i}]xfade=transition=fade:duration={xfade:g}:offset={offset:g}[{label}]")
        total = offset + durations[i]
        prev = label
    return ";".join(parts), total


def assemble(inputs: list[str], out: str, size: tuple[int, int], *, pad: bool = False, focus: float = 0.5, fps: int = 60,
             xfade: float = 0.5, music: str | None = None) -> float:
    durations = [probe(p)["duration"] for p in inputs]
    graph, total = concat_filter(durations, size, pad, focus, fps, xfade)
    cmd = [find_tool("ffmpeg"), "-y"]
    for p in inputs:
        cmd += ["-i", p]
    if music:
        cmd += ["-i", music]
        graph += f";[{len(inputs)}:a]atrim=0:{total:g},afade=t=in:d=0.5,afade=t=out:st={max(total - 1.5, 0):g}:d=1.5[outa]"
    cmd += ["-filter_complex", graph, "-map", "[outv]"]
    if music:
        cmd += ["-map", "[outa]", "-c:a", "aac", "-b:a", "192k"]
    else:
        cmd += ["-an"]
    run(cmd + ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out])
    return total


def make_gif(src: str, dst: str, width: int = 480, fps: int = 12) -> None:
    vf = f"fps={fps},scale={width}:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse"
    run([find_tool("ffmpeg"), "-y", "-i", src, "-vf", vf, "-loop", "0", dst])


def build(args) -> list[str]:
    outputs = []
    for aspect in args.aspects:
        size = SIZES[aspect]
        tag = aspect.replace(":", "x")
        with tempfile.TemporaryDirectory() as tmp:
            segments = []
            if args.intro or args.intro_image:
                seg = os.path.join(tmp, "intro.mp4")
                card_clip(args.intro or "", seg, size, args.card_seconds, args.fps, args.subtitle or "", args.intro_image)
                segments.append(seg)
            segments += args.clips
            if args.outro or args.outro_image:
                seg = os.path.join(tmp, "outro.mp4")
                card_clip(args.outro or "", seg, size, args.card_seconds, args.fps, "", args.outro_image)
                segments.append(seg)
            out = f"{args.out}_{tag}.mp4"
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            assemble(segments, out, size, pad=args.pad, focus=args.focus, fps=args.fps, xfade=args.crossfade, music=args.music)
            outputs.append(out)
            if args.gif and aspect == args.aspects[0]:
                make_gif(out, f"{args.out}.gif")
                outputs.append(f"{args.out}.gif")
    return outputs


def selftest() -> int:
    ffmpeg = find_tool("ffmpeg")
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        clips = []
        for i, pattern in enumerate(("testsrc", "smptebars")):
            p = str(t / f"c{i}.mp4")
            run([ffmpeg, "-y", "-f", "lavfi", "-i", f"{pattern}=size=1280x720:rate=30:duration=3", "-c:v", "libx264", "-pix_fmt", "yuv420p", p])
            clips.append(p)
        # trim
        trimmed = str(t / "trim.mp4")
        trim(clips[0], trimmed, 1, 2.5)
        assert abs(probe(trimmed)["duration"] - 1.5) < 0.2, probe(trimmed)
        # graph maths: two 3 s clips, 0.5 s fade => 5.5 s
        _, total = concat_filter([3, 3], (1920, 1080), False, 0.5, 60, 0.5)
        assert abs(total - 5.5) < 1e-9
        try:
            concat_filter([1, 1], (1920, 1080), False, 0.5, 60, 2)
        except ValueError:
            pass
        else:
            raise AssertionError("oversized crossfade accepted")
        assert "crop=1080:1920" in fit_filter((1080, 1920)) and "pad=1080:1920" in fit_filter((1080, 1920), pad=True)
        # placeholder card carries the marker and is the right size
        from PIL import Image
        png = str(t / "card.png")
        make_card_png("Selftest card with a long title to wrap", png, SIZES["9:16"])
        assert Image.open(png).size == (1080, 1920)
        # full build in both aspects with intro/outro + gif
        ns = argparse.Namespace(clips=clips, out=str(t / "out" / "demo"), intro="Selftest", outro="Be Dino!", intro_image=None, outro_image=None,
                                subtitle="sub", aspects=["16:9", "9:16"], music=None, crossfade=0.5, focus=0.5, pad=False, gif=True,
                                fps=30, card_seconds=2)
        outs = build(ns)
        wide, tall = probe(outs[0]), probe(outs[2] if outs[1].endswith(".gif") else outs[1])
        assert (wide["width"], wide["height"]) == (1920, 1080), wide
        assert (tall["width"], tall["height"]) == (1080, 1920), tall
        # 2 + 3 + 3 + 2 minus 3 crossfades of 0.5
        assert abs(wide["duration"] - 8.5) < 0.3, wide
        assert Path(outs[1]).stat().st_size > 1000 and outs[1].endswith(".gif")
        # music path: synthetic tone
        tone = str(t / "tone.wav")
        run([ffmpeg, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=20", tone])
        scored = str(t / "scored.mp4")
        assemble(clips, scored, SIZES["16:9"], fps=30, music=tone)
        audio = subprocess.run([find_tool("ffprobe"), "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_name", "-of", "csv=p=0", scored],
                               capture_output=True, text=True).stdout.strip()
        assert audio == "aac", audio
    print("edit.py selftest OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("trim")
    p.add_argument("src"), p.add_argument("dst")
    p.add_argument("--start", type=float, default=0)
    p.add_argument("--end", type=float)
    p = sub.add_parser("gif")
    p.add_argument("src"), p.add_argument("dst")
    p.add_argument("--width", type=int, default=480)
    p = sub.add_parser("build")
    p.add_argument("clips", nargs="+")
    p.add_argument("--out", required=True, help="output prefix; writes PREFIX_16x9.mp4 / PREFIX_9x16.mp4 (+ PREFIX.gif)")
    p.add_argument("--aspects", nargs="+", choices=sorted(SIZES), default=["16:9"])
    p.add_argument("--intro"), p.add_argument("--outro"), p.add_argument("--subtitle")
    p.add_argument("--intro-image"), p.add_argument("--outro-image")
    p.add_argument("--music", help="path to a track you have the rights to (none is bundled)")
    p.add_argument("--crossfade", type=float, default=0.5)
    p.add_argument("--focus", type=float, default=0.5, help="0 left .. 1 right: which part of a wide clip a 9:16 crop keeps")
    p.add_argument("--pad", action="store_true", help="letterbox instead of cropping")
    p.add_argument("--fps", type=int, default=60)
    p.add_argument("--card-seconds", type=float, default=2.5)
    p.add_argument("--gif", action="store_true")
    sub.add_parser("selftest")
    args = ap.parse_args()
    if args.cmd == "selftest":
        return selftest()
    if args.cmd == "trim":
        trim(args.src, args.dst, args.start, args.end)
    elif args.cmd == "gif":
        make_gif(args.src, args.dst, args.width)
    else:
        for o in build(args):
            print(o)
    return 0


if __name__ == "__main__":
    sys.exit(main())
