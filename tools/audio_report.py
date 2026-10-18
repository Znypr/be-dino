#!/usr/bin/env python3
"""Judge sound from the numbers: an objective audio report for WAV / OGG / MP3 files (docs/161, BD-637).

Agents cannot listen. This tool measures what CAN be measured (level, loudness, clipping, silence, attack, decay,
spectrum, harshness) and draws a waveform + spectrogram picture so a person can LOOK at the sound. It cannot judge
taste: it flags loud, harsh, clipped, inconsistent and silent sounds. A human ear still decides "nice".

  python tools/audio_report.py assets/audio/sfx                       # table for a folder
  python tools/audio_report.py a.wav b.ogg --out build/audio-images   # also write PNG pictures
  python tools/audio_report.py assets/audio/sfx --compare             # side by side + loudness outliers
  python tools/audio_report.py assets/audio/sfx --game src/shared/Sfx.luau --compare --md report.md
  python tools/audio_report.py a.wav --json                           # machine readable

Needs Python 3 + numpy. ffmpeg/ffprobe are used for OGG/MP3/odd WAVs, the cross-check loudness (ebur128) and the
pictures; plain 16-bit PCM WAV needs neither. Set FFMPEG=path if ffmpeg is not on PATH (default C:/ffmpeg/bin).

Loudness method: K-weighting + gating computed IN THIS TOOL following ITU-R BS.1770-4 (the same maths as ffmpeg's
ebur128); ffmpeg's integrated value is printed next to it as a cross-check when ffmpeg is available. Sounds shorter
than 400 ms are zero-padded to one 400 ms block (that is also how a short tick is heard: shorter means quieter).
The number used to compare sounds is LUFS-M max, the loudest 400 ms block.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------------------------------------------------
# THRESHOLDS: every number that turns a measurement into a verdict lives in this ONE table. Change them here only.
# They are engineering starting points for a calm children's game, not laws: tune them when the owner's ears disagree
# (record the change in docs/161). Sources / reasoning next to each line. LU = loudness unit (1 LU = 1 dB).
# ---------------------------------------------------------------------------------------------------------------------
THRESHOLDS = {
    # --- level -----------------------------------------------------------------------------------------------------
    # A sample at or above this is "full scale". 16-bit full scale is 32767/32768 = 0.99997; the margin catches
    # samples that were rounded or dithered onto the rail. Reasoning: a flat run at the rail is the clipping signature.
    "clip_sample_level": 0.9995,
    # A run of this many consecutive full-scale samples counts as one clipping EVENT (a single touch is not a flat top).
    "clip_run_samples": 2,
    # True peak (4x oversampled, ITU-R BS.1770 / EBU R128 s1) above this dBTP can clip after MP3/OGG encode or Roblox's
    # decoder. EBU R128 s1 asks for max -1 dBTP; we only call it "clipped" at the 0 dBTP ceiling and warn above -1.
    "clip_true_peak_db": -0.1,
    "warn_true_peak_db": -1.0,
    # --- loudness (LUFS-M max: loudest 400 ms block, K-weighted) ---------------------------------------------------
    # Commonly quoted game-audio targets: about -23 LUFS console (EBU R128 programme), -18 LUFS handheld/mobile
    # (Wwise/Audiokinetic loudness guidance), -16 LUFS for phone speakers/streaming (Apple, Spotify). Roblox kids play on
    # phones with Master 0.8 x SFX 0.7 sliders, and the owner wants "soft, calm, bubbly" (docs/87). So:
    # (a) the FILE as authored (every file in this pack is peak-normalised to about -3 dBFS, so file loudness mostly shows
    # how dense/sustained the sound is): above -14 LUFS-M is a hot master (hotter than the -16 phone reference + margin).
    "calm_lufs_max": -26.0,    # at or below this = calm (about 3 LU under the console reference)
    "loud_lufs_max": -14.0,    # above this = loud
    "quiet_lufs_max": -40.0,   # below this = too quiet to hear on a phone speaker over game noise (about -17 LU under console)
    # (b) the level the PLAYER gets = file LUFS-M + 20*log10(cue volume), before the Master (0.5 in Sfx.luau) and the
    # Settings sliders (0.8 x 0.7 default), which take roughly another 5 dB off. Frequent cues should sit near or under the
    # -23 LUFS console reference; the rare payoff cues (legendary reveal, fusion) may be a few LU hotter.
    "game_calm_lufs": -26.0,   # at or below this = calm
    "game_loud_lufs": -18.0,   # above this = loud (reference -23 plus 5 LU of headroom for rare payoffs, minus the ~5 dB sliders)
    "game_quiet_lufs": -40.0,  # below this = too quiet even for a tick
    "quiet_peak_db": -30.0,    # a peak under this is inaudible whatever the loudness maths says
    "silent_peak_db": -80.0,   # below this the file is effectively digital silence
    # --- silence / timing --------------------------------------------------------------------------------------------
    # The first/last sample above this level ends the leading / starts the trailing silence. -60 dBFS is the usual
    # "silence" gate for editing (about 1/1000 of full scale); 16-bit dither noise sits near -90.
    "silence_db": -60.0,
    "long_lead_silence_s": 0.15,   # more than this before the sound starts feels like lag after a button press
    "long_tail_silence_s": 0.50,   # more than this of dead tail is wasted bytes and can delay a queued cue
    # Time from first sound to 90% of peak. Under 5 ms the ear hears a "click/snap" (the precedence-effect and click
    # literature put onset smoothing at 5-10 ms); sharp attacks are what the owner called "sharp" in BD-166.
    "sharp_attack_ms": 5.0,
    # --- spectrum / harshness ----------------------------------------------------------------------------------------
    # Human hearing is most sensitive 2-5 kHz (ISO 226 equal-loudness curves; the A-weighting peak is ~2.5 kHz). Energy
    # there reads as bright/sharp, and shrill when it dominates. Share = energy above 2 kHz / total energy.
    "presence_band_hz": (2000.0, 5000.0),
    "air_band_hz": (8000.0, 24000.0),
    "air_note_share": 0.05,  # more than this share above 8 kHz breaks docs/110 style rule 2 ("no energy above roughly 8 kHz")
    "bright_share": 0.10,    # at or below this share above 2 kHz counts as no brightness penalty (warm/soft sounds)
    "bright_full": 0.60,     # at or above this share above 2 kHz the brightness part of the score is full
    "sharp_crest_db": 6.0,   # crest factor (peak vs active RMS) under this is sustained (a sine is 3 dB), no transient penalty
    "sharp_crest_full": 18.0,  # at or above this the sound is mostly one spike (a click is 25+ dB)
    "harsh_score": 55.0,     # harshness score (0-100) at or above this = harsh
    "bright_score": 35.0,    # at or above this = a bit bright (still "ok", but listen first)
    # --- consistency (compare mode) ----------------------------------------------------------------------------------
    # ITU-R BS.1770 / EBU R128 consistency practice: programme items within about +/-1-2 LU, SFX families within +/-3 LU.
    # Anything 4 LU or more from the pack median is an outlier (2 LU is clearly audible, 3 LU is the usual tolerance).
    "outlier_lu": 4.0,
    "outlier_harsh_gap": 20.0,  # harshness score this far above the pack median is flagged as a harshness outlier
}

BANDS = [  # name, low Hz, high Hz (energy shares sum to 100% of the spectrum between 20 Hz and Nyquist)
    ("sub", 20.0, 100.0),
    ("low", 100.0, 400.0),
    ("mid", 400.0, 2000.0),
    ("presence", 2000.0, 5000.0),
    ("high", 5000.0, 8000.0),
    ("air", 8000.0, 1e9),
]

AUDIO_EXT = {".wav", ".ogg", ".mp3", ".flac", ".m4a", ".aiff", ".aif"}
MAX_SECONDS = 120.0  # longer files are analysed over their first two minutes (the python filter loop is slow)


# --------------------------------------------------------------------------------------------------------------- ffmpeg
def find_tool(name: str):
    env = os.environ.get(name.upper())
    if env and Path(env).exists():
        return env
    found = shutil.which(name)
    if found:
        return found
    for base in (r"C:\ffmpeg\bin", "/c/ffmpeg/bin", "/usr/bin", "/usr/local/bin"):
        for ext in (".exe", ""):
            p = Path(base) / (name + ext)
            if p.exists():
                return str(p)
    return None


def run(cmd, binary=False):
    return subprocess.run(cmd, capture_output=True, text=not binary, check=False)


def decode(path: Path):
    """Return (samples float32 shape (n, channels) in -1..1, sample_rate, container note)."""
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path)) as w:
                if w.getsampwidth() == 2:
                    sr, ch = w.getframerate(), w.getnchannels()
                    raw = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
                    return raw[: len(raw) // ch * ch].reshape(-1, ch), sr, "wav pcm16"
        except (wave.Error, EOFError):
            pass
    ffmpeg, ffprobe = find_tool("ffmpeg"), find_tool("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("ffmpeg/ffprobe needed to read %s (set FFMPEG / FFPROBE or put them on PATH)" % path.name)
    pr = run([ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=sample_rate,channels,codec_name",
              "-of", "json", str(path)])
    info = json.loads(pr.stdout or "{}").get("streams") or []
    if not info:
        raise RuntimeError("no audio stream in %s" % path.name)
    sr, ch = int(info[0]["sample_rate"]), int(info[0]["channels"])
    dr = run([ffmpeg, "-v", "error", "-i", str(path), "-t", str(MAX_SECONDS), "-f", "f32le", "-acodec", "pcm_f32le", "-"],
             binary=True)
    data = np.frombuffer(dr.stdout, dtype="<f4")
    return data[: len(data) // ch * ch].reshape(-1, ch).astype(np.float32), sr, info[0].get("codec_name", "?")


def ffmpeg_loudness(path: Path):
    """Cross-check: ffmpeg's ebur128 integrated loudness (None when ffmpeg is missing or the file is under 400 ms)."""
    ffmpeg = find_tool("ffmpeg")
    if not ffmpeg:
        return None
    r = run([ffmpeg, "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"])
    tail = (r.stderr or "").rsplit("Summary:", 1)
    if len(tail) < 2:
        return None
    m = re.search(r"\bI:\s+(-?[\d.]+)\s+LUFS", tail[1])
    if not m:
        return None
    v = float(m.group(1))
    return v if v > -69.9 else None


# ------------------------------------------------------------------------------------------------------------ loudness
def db(x: float, floor: float = -200.0) -> float:
    return 20.0 * math.log10(x) if x > 0 else floor


def k_weight(x: np.ndarray, sr: int) -> np.ndarray:
    """ITU-R BS.1770-4 K-weighting (high-shelf then 38 Hz high-pass) for any sample rate, as two biquads."""
    def biquad(sig, b, a):
        y = np.zeros_like(sig)
        x1 = x2 = y1 = y2 = 0.0
        b0, b1, b2 = b
        _, a1, a2 = a
        for i, v in enumerate(sig.tolist()):
            o = b0 * v + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
            x2, x1, y2, y1 = x1, v, y1, o
            y[i] = o
        return y

    f0, g, q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    k = math.tan(math.pi * f0 / sr)
    vh = 10 ** (g / 20)
    vb = vh ** 0.4996667741545416
    a0 = 1 + k / q + k * k
    b = ((vh + vb * k / q + k * k) / a0, 2 * (k * k - vh) / a0, (vh - vb * k / q + k * k) / a0)
    a = (1.0, 2 * (k * k - 1) / a0, (1 - k / q + k * k) / a0)
    y = biquad(x.astype(np.float64), b, a)
    f0, q = 38.13547087602444, 0.5003270373238773
    k = math.tan(math.pi * f0 / sr)
    a0 = 1 + k / q + k * k
    return biquad(y, (1.0, -2.0, 1.0), (1.0, 2 * (k * k - 1) / a0, (1 - k / q + k * k) / a0))


def loudness(samples: np.ndarray, sr: int):
    """Return (lufs_integrated, lufs_momentary_max). Channels are K-weighted and their powers summed (BS.1770)."""
    power = None
    for c in range(samples.shape[1]):
        w = k_weight(samples[:, c], sr)
        power = w * w if power is None else power + w * w
    block = int(round(0.4 * sr))
    n = len(power)
    if n < block:
        power = np.concatenate([power, np.zeros(block - n)])
        n = block
    cs = np.concatenate([[0.0], np.cumsum(power)])
    hop = max(1, int(round(0.1 * sr)))  # 75% overlap, as the standard
    starts = np.arange(0, n - block + 1, hop)
    ms = (cs[starts + block] - cs[starts]) / block
    lk = -0.691 + 10 * np.log10(np.maximum(ms, 1e-12))
    lufs_m = float(lk.max())
    keep = ms[lk > -70.0]
    if len(keep) == 0:
        return -70.0, lufs_m
    rel = -0.691 + 10 * math.log10(float(keep.mean())) - 10.0
    keep = ms[lk > max(-70.0, rel)]
    return -0.691 + 10 * math.log10(float(keep.mean())), lufs_m


# ------------------------------------------------------------------------------------------------------------- metrics
def true_peak_db(mono_ch: np.ndarray) -> float:
    """4x oversampled peak (zero-padded FFT upsampling), dBTP."""
    n = len(mono_ch)
    if n < 4:
        return db(float(np.max(np.abs(mono_ch))) if n else 0.0)
    spec = np.fft.rfft(mono_ch.astype(np.float64))
    up = np.fft.irfft(spec, n * 4) * 4
    return db(float(np.max(np.abs(up))))


def spectrum(mono: np.ndarray, sr: int):
    """Welch-style average power spectrum. Returns (freqs, power) with DC and below 20 Hz removed."""
    frame = 4096
    if len(mono) < frame:
        pad = np.zeros(frame)
        pad[: len(mono)] = mono
        frames = [pad]
    else:
        frames = [mono[i:i + frame] for i in range(0, len(mono) - frame + 1, frame // 2)]
        tail = len(mono) - ((len(mono) - frame) // (frame // 2) * (frame // 2) + frame)
        if tail > 0:
            frames.append(mono[-frame:])
    win = np.hanning(frame)
    acc = np.zeros(frame // 2 + 1)
    for fr in frames:
        acc += np.abs(np.fft.rfft(fr * win)) ** 2
    freqs = np.fft.rfftfreq(frame, 1.0 / sr)
    acc[freqs < 20.0] = 0.0
    return freqs, acc


def analyze(path: Path):
    samples, sr, codec = decode(path)
    n, ch = samples.shape
    r = {"file": path.name, "path": str(path), "codec": codec, "sample_rate": sr, "channels": ch,
         "duration_s": n / sr if sr else 0.0}
    if n == 0:
        r.update(peak_db=-200.0, verdict="silent", reasons=["no samples"], notes=[])
        return r
    mono = samples.mean(axis=1).astype(np.float64)
    absmax = np.abs(samples).max(axis=1)
    peak = float(absmax.max())
    r["peak_db"] = db(peak)
    r["true_peak_db"] = max(true_peak_db(samples[:, c]) for c in range(ch))
    # clipping: full-scale samples and runs of them (events)
    hot = absmax >= THRESHOLDS["clip_sample_level"]
    r["clipped_samples"] = int(hot.sum())
    events, run_len = 0, 0
    for h in np.append(hot, False):
        if h:
            run_len += 1
        else:
            if run_len >= THRESHOLDS["clip_run_samples"]:
                events += 1
            run_len = 0
    r["clip_events"] = events
    # silence, activity
    thr = 10 ** (THRESHOLDS["silence_db"] / 20)
    above = np.nonzero(absmax > thr)[0]
    if len(above) == 0 or peak <= thr:
        r.update(lead_silence_s=r["duration_s"], tail_silence_s=0.0, rms_db=-200.0, active_rms_db=-200.0, crest_db=0.0,
                 attack_ms=0.0, decay_ms=0.0, lufs_i=-70.0, lufs_m=-70.0, lufs_ffmpeg=None, dominant_hz=0.0,
                 centroid_hz=0.0, bands={b[0]: 0.0 for b in BANDS}, hf_share=0.0, harsh_score=0.0, sharp_score=0.0)
        r["verdict"], r["reasons"], r["notes"] = "silent", ["nothing above %d dBFS" % THRESHOLDS["silence_db"]], []
        return r
    first, last = int(above[0]), int(above[-1])
    r["lead_silence_s"] = first / sr
    r["tail_silence_s"] = (n - 1 - last) / sr
    r["rms_db"] = db(float(np.sqrt(np.mean(mono ** 2))))
    # active region = first to last sample above the silence gate, but never under 50 ms (a lone click would otherwise
    # have crest 0 dB: one sample is its own RMS); 50 ms is also about the shortest sound the ear can rate for loudness
    active = mono[first:max(last + 1, first + int(0.05 * sr))]
    arms = float(np.sqrt(np.mean(active ** 2)))
    r["active_rms_db"] = db(arms)
    r["crest_db"] = r["peak_db"] - r["active_rms_db"]
    # envelope in 0.5 ms blocks (max of |x|) -> attack and decay
    blk = max(1, int(round(sr * 0.0005)))
    nb = (n + blk - 1) // blk
    env = np.zeros(nb)
    padded = np.zeros(nb * blk)
    padded[:n] = absmax
    env = padded.reshape(nb, blk).max(axis=1)
    ipk = int(np.argmax(env))
    t90 = int(np.argmax(env >= 0.9 * env[ipk]))
    r["attack_ms"] = max(0.0, (t90 * blk - first) / sr * 1000.0)
    # decay: from the peak block until the 10 ms-smoothed envelope falls 20 dB under the peak for good
    sm = max(1, int(round(0.010 / (blk / sr))))
    senv = np.sqrt(np.convolve(env ** 2, np.ones(sm) / sm, mode="same"))
    pk_s = senv[ipk]
    loud = np.nonzero(senv[ipk:] >= pk_s * 0.1)[0]
    r["decay_ms"] = float(loud[-1] * blk / sr * 1000.0) if len(loud) else 0.0
    # loudness
    r["lufs_i"], r["lufs_m"] = loudness(samples[: int(MAX_SECONDS * sr)], sr)
    r["lufs_ffmpeg"] = ffmpeg_loudness(path) if find_tool("ffmpeg") else None
    # spectrum
    freqs, p = spectrum(mono, sr)  # whole file: silence adds no energy, and a Hann window would zero a click at the edge of a cut
    tot = float(p.sum()) or 1.0
    k = int(np.argmax(p))
    dom = float(freqs[k])
    if 0 < k < len(p) - 1 and p[k - 1] > 0 and p[k + 1] > 0:
        a, b, c = math.log(p[k - 1]), math.log(p[k]), math.log(p[k + 1])
        d = a - 2 * b + c
        if d != 0:
            dom = float(freqs[k] + 0.5 * (a - c) / d * (freqs[1] - freqs[0]))
    r["dominant_hz"] = dom
    r["centroid_hz"] = float((freqs * p).sum() / tot)
    r["bands"] = {name: float(p[(freqs >= lo) & (freqs < hi)].sum() / tot) for name, lo, hi in BANDS}
    r["hf_share"] = float(p[freqs >= THRESHOLDS["presence_band_hz"][0]].sum() / tot)  # presence + high + air
    # harshness: brightness (energy above 2 kHz) 60% + sharp transient (fast attack AND spiky) 40%
    T = THRESHOLDS
    bright = min(1.0, max(0.0, (r["hf_share"] - T["bright_share"]) / (T["bright_full"] - T["bright_share"])))
    fast = min(1.0, max(0.0, (20.0 - r["attack_ms"]) / (20.0 - T["sharp_attack_ms"] / 2)))
    spiky = min(1.0, max(0.0, (r["crest_db"] - T["sharp_crest_db"]) / (T["sharp_crest_full"] - T["sharp_crest_db"])))
    r["sharp_score"] = 100.0 * fast * spiky
    r["harsh_score"] = 100.0 * (0.6 * bright + 0.4 * fast * spiky)
    r["verdict"], r["reasons"], r["notes"] = verdict(r)
    return r


VERDICT_ORDER = ["clipped", "silent", "harsh", "loud", "too quiet", "ok", "calm"]  # worst first; the first match is the verdict


def verdict(r, level=None, level_label="loudest 400 ms", loud=None, calm=None, quiet=None):
    """Plain-words verdict for a children's game. Returns (word, reasons, notes). Worst problem first; every problem is
    listed in the reasons. `level` defaults to the file's LUFS-M max with the file-level thresholds; the game table passes
    the player level and the game thresholds."""
    T = THRESHOLDS
    level = r["lufs_m"] if level is None else level
    loud = T["loud_lufs_max"] if loud is None else loud
    calm = T["calm_lufs_max"] if calm is None else calm
    quiet = T["quiet_lufs_max"] if quiet is None else quiet
    found, notes = {}, []
    if r["lead_silence_s"] > T["long_lead_silence_s"]:
        notes.append("%.2f s of silence before the sound starts (feels laggy)" % r["lead_silence_s"])
    if r["tail_silence_s"] > T["long_tail_silence_s"]:
        notes.append("%.2f s of silent tail (trim it)" % r["tail_silence_s"])
    if r["true_peak_db"] > T["warn_true_peak_db"] and r["clip_events"] == 0 and r["true_peak_db"] <= T["clip_true_peak_db"]:
        notes.append("true peak %.1f dBTP is above the %.0f dBTP safety line" % (r["true_peak_db"], T["warn_true_peak_db"]))
    if r["attack_ms"] < T["sharp_attack_ms"] and r["crest_db"] > T["sharp_crest_db"]:
        notes.append("very fast attack (%.1f ms): a snap or click" % r["attack_ms"])
    if r["bands"]["air"] > T["air_note_share"]:
        notes.append("%.0f%% of the energy is above 8 kHz (docs/110 style rule 2 says none)" % (100 * r["bands"]["air"]))
    if r["clip_events"] > 0 or r["true_peak_db"] > T["clip_true_peak_db"]:
        found["clipped"] = "%d clipped runs, true peak %.1f dBTP" % (r["clip_events"], r["true_peak_db"])
    if r["peak_db"] < T["silent_peak_db"]:
        found["silent"] = "peak %.0f dBFS" % r["peak_db"]
    if r["harsh_score"] >= T["harsh_score"]:
        found["harsh"] = ("harshness %.0f (%.0f%% of the energy is above 2 kHz, attack %.1f ms)"
                          % (r["harsh_score"], 100 * r["hf_share"], r["attack_ms"]))
    if level > loud:
        found["loud"] = "%s is %.1f LUFS (limit %.0f)" % (level_label, level, loud)
    if "silent" not in found and (level < quiet or r["peak_db"] < T["quiet_peak_db"]):
        found["too quiet"] = "%s is %.1f LUFS, file peak %.1f dBFS" % (level_label, level, r["peak_db"])
    if found:
        word = next(w for w in VERDICT_ORDER if w in found)
        return word, [found[w] for w in VERDICT_ORDER if w in found], notes
    if r["harsh_score"] >= T["bright_score"]:
        notes.append("bit bright (harshness %.0f): listen first" % r["harsh_score"])
        return "ok", ["bright but within limits"], notes
    if level <= calm:
        return "calm", ["%.1f LUFS, soft top end" % level], notes
    return "ok", ["%.1f LUFS" % level], notes


# --------------------------------------------------------------------------------------------------------------- images
PIC_W, PIC_WAVE_H, PIC_SPEC_H = 800, 140, 360
PIC_F_LO, PIC_F_HI = 20.0, 20000.0
# Frequency guide lines drawn over the spectrogram (no fonts needed): Hz, colour. Red = 2 kHz, where harshness starts.
PIC_GUIDES = [(100.0, "white@0.30"), (1000.0, "white@0.30"), (2000.0, "red@0.85"), (8000.0, "orange@0.60"), (10000.0, "white@0.30")]


def write_picture(path: Path, out_dir: Path):
    """One PNG per file: waveform on top, log-frequency spectrogram below (20 Hz bottom, 20 kHz top) with guide lines
    at 100 Hz, 1 kHz, 2 kHz (red: harshness starts), 8 kHz (orange: 'air') and 10 kHz. Returns the PNG path or None."""
    ffmpeg = find_tool("ffmpeg")
    if not ffmpeg:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / (path.stem + ".png")
    span = math.log(PIC_F_HI / PIC_F_LO)
    boxes = "".join(",drawbox=x=0:y=%d:w=iw:h=1:color=%s:t=fill" % (round(PIC_SPEC_H * (1 - math.log(f / PIC_F_LO) / span)), col)
                    for f, col in PIC_GUIDES)
    graph = ("[0:a]aformat=channel_layouts=mono,asplit[a][b];"
             "[a]showwavespic=s=%dx%d:colors=0x2a7fff:scale=lin,format=rgb24[w];"
             "[b]showspectrumpic=s=%dx%d:legend=0:fscale=log:start=%d:stop=%d:color=viridis,format=rgb24%s[s];"
             "[w][s]vstack,format=rgb24[v]" % (PIC_W, PIC_WAVE_H, PIC_W, PIC_SPEC_H, PIC_F_LO, PIC_F_HI, boxes))
    r = run([ffmpeg, "-v", "error", "-y", "-i", str(path), "-filter_complex", graph, "-map", "[v]", "-frames:v", "1", str(png)])
    if r.returncode == 0 and png.exists():
        return png
    print("picture failed for %s: %s" % (path.name, (r.stderr or "").strip()[-300:]), file=sys.stderr)
    return None


# ------------------------------------------------------------------------------------------------------ game cue levels
def parse_sfx_luau(text: str):
    """Cues from src/shared/Sfx.luau: name -> {id, volume, rate}. Only simple `name = {id = "...", volume = .x}` lines."""
    cues = {}
    for m in re.finditer(r'^\s*(\w+)\s*=\s*\{\s*id\s*=\s*"([^"]*)"\s*,\s*volume\s*=\s*([\d.]+)\s*,\s*rate\s*=\s*([\d.]+)',
                         text, re.M):
        cues[m.group(1)] = {"id": m.group(2), "volume": float(m.group(3)), "rate": float(m.group(4))}
    return cues


def apply_game(results, cues):
    """Add the level the PLAYER gets: file loudness + 20*log10(cue volume). A cue that carries another file's asset id
    (BD-166: run_end plays the run_start chime) is measured with the file that owns that id (first file-named cue)."""
    by_name = {r["file"].rsplit(".", 1)[0]: r for r in results if "lufs_m" in r}
    owner = {}
    for name, c in cues.items():
        if c["id"] and name in by_name and c["id"] not in owner:
            owner[c["id"]] = name
    rows = []
    for name, c in cues.items():
        if not c["id"]:
            continue
        src = owner.get(c["id"])
        if src is None or src not in by_name:
            continue
        r = by_name[src]
        lvl = r["lufs_m"] + db(c["volume"])
        word, why, _ = verdict(r, level=lvl, level_label="player level", loud=THRESHOLDS["game_loud_lufs"],
                               calm=THRESHOLDS["game_calm_lufs"], quiet=THRESHOLDS["game_quiet_lufs"])
        rows.append({"cue": name, "plays_file": src, "volume": c["volume"], "rate": c["rate"],
                     "game_lufs_m": r["lufs_m"] + db(c["volume"]), "file_lufs_m": r["lufs_m"],
                     "game_peak_db": r["peak_db"] + db(c["volume"]), "verdict": word, "why": why,
                     "harsh_score": r["harsh_score"], "duration_s": r["duration_s"] / c["rate"]})
    return rows


# --------------------------------------------------------------------------------------------------------------- compare
def outliers(values: dict, limit: float):
    """name -> signed LU distance from the median, for names beyond `limit`."""
    if len(values) < 3:
        return {}, (sum(values.values()) / len(values) if values else 0.0)
    med = float(np.median(list(values.values())))
    return {k: v - med for k, v in values.items() if abs(v - med) >= limit}, med


# --------------------------------------------------------------------------------------------------------------- output
COLS = [("file", "file", "{}"), ("dur s", "duration_s", "{:.2f}"), ("Hz", "sample_rate", "{}"), ("ch", "channels", "{}"),
        ("peak dBFS", "peak_db", "{:.1f}"), ("true pk", "true_peak_db", "{:.1f}"), ("RMS dB", "active_rms_db", "{:.1f}"),
        ("LUFS-M max", "lufs_m", "{:.1f}"), ("LUFS-I", "lufs_i", "{:.1f}"), ("clip runs", "clip_events", "{}"),
        ("lead s", "lead_silence_s", "{:.2f}"), ("tail s", "tail_silence_s", "{:.2f}"), ("attack ms", "attack_ms", "{:.1f}"),
        ("decay ms", "decay_ms", "{:.0f}"), ("crest dB", "crest_db", "{:.1f}"), ("main Hz", "dominant_hz", "{:.0f}"),
        ("centroid Hz", "centroid_hz", "{:.0f}"), ("harsh", "harsh_score", "{:.0f}"), ("verdict", "verdict", "{}")]


def cell(r, key, fmt):
    v = r.get(key)
    return "-" if v is None else fmt.format(v)


def markdown_table(results):
    head = [c[0] for c in COLS]
    lines = ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] * len(head)) + "|"]
    for r in results:
        lines.append("| " + " | ".join(cell(r, k, f) for _, k, f in COLS) + " |")
    return "\n".join(lines)


def band_table(results):
    names = [b[0] for b in BANDS]
    lines = ["| file | " + " | ".join("%s %%" % n for n in names) + " | above 2 kHz % |", "|" + "|".join(["---"] * (len(names) + 2)) + "|"]
    for r in results:
        if "bands" in r:
            lines.append("| %s | %s | %.0f |" % (r["file"], " | ".join("%.0f" % (100 * r["bands"][n]) for n in names), 100 * r["hf_share"]))
    return "\n".join(lines)


def text_table(results):
    rows = [[c[0] for c in COLS]] + [[cell(r, k, f) for _, k, f in COLS] for r in results]
    widths = [max(len(row[i]) for row in rows) for i in range(len(COLS))]
    return "\n".join("  ".join(c.ljust(w) if i in (0, len(COLS) - 1) else c.rjust(w) for i, (c, w) in enumerate(zip(row, widths)))
                     for row in rows)


def compare_text(results, game_rows, md=False):
    T = THRESHOLDS
    ok = [r for r in results if "lufs_m" in r and r["verdict"] != "silent"]
    out = []
    file_out, file_med = outliers({r["file"]: r["lufs_m"] for r in ok}, T["outlier_lu"])
    out.append("Loudness of the files themselves (LUFS-M max); pack median %.1f LUFS; outlier = %.0f LU or more from the median."
               % (file_med, T["outlier_lu"]))
    for r in sorted(ok, key=lambda x: -x["lufs_m"]):
        d = r["lufs_m"] - file_med
        flag = "  <-- OUTLIER %+.1f LU" % d if r["file"] in file_out else ""
        out.append("  %-24s %6.1f LUFS  (%+.1f LU)%s" % (r["file"], r["lufs_m"], d, flag))
    harsh_med = float(np.median([r["harsh_score"] for r in ok])) if ok else 0.0
    hs = [r for r in ok if r["harsh_score"] - harsh_med >= T["outlier_harsh_gap"]]
    out.append("Harshness outliers (score %.0f or more above the pack median %.0f): %s"
               % (T["outlier_harsh_gap"], harsh_med, ", ".join("%s %.0f" % (r["file"], r["harsh_score"]) for r in hs) or "none"))
    if game_rows:
        g_out, g_med = outliers({g["cue"]: g["game_lufs_m"] for g in game_rows}, T["outlier_lu"])
        out.append("")
        out.append("Level the PLAYER gets (file LUFS-M max + 20*log10(cue volume), before the Master/SFX sliders); median %.1f LUFS."
                   % g_med)
        for g in sorted(game_rows, key=lambda x: -x["game_lufs_m"]):
            d = g["game_lufs_m"] - g_med
            flag = "  <-- OUTLIER %+.1f LU" % d if g["cue"] in g_out else ""
            out.append("  %-24s %6.1f LUFS  vol %.2f  plays %-16s %4.1f s  harsh %3.0f  %s%s"
                       % (g["cue"], g["game_lufs_m"], g["volume"], g["plays_file"], g["duration_s"], g["harsh_score"],
                          g["verdict"], flag))
    return "\n".join(out)


def collect(paths):
    files = []
    for p in paths:
        p = Path(p)
        if p.is_dir():
            files += sorted(f for f in p.rglob("*") if f.suffix.lower() in AUDIO_EXT)
        elif p.exists():
            files.append(p)
        else:
            print("not found: %s" % p, file=sys.stderr)
    return files


def main(argv=None):
    ap = argparse.ArgumentParser(description="Objective audio report: level, loudness, clipping, spectrum, harshness, pictures.")
    ap.add_argument("paths", nargs="+", help="audio files or folders")
    ap.add_argument("--out", help="folder for the waveform + spectrogram PNG of each file")
    ap.add_argument("--compare", action="store_true", help="side by side + loudness outliers versus the rest of the pack")
    ap.add_argument("--game", help="path to src/shared/Sfx.luau: also report the level the player gets (file x cue volume)")
    ap.add_argument("--md", help="write the report as Markdown to this file")
    ap.add_argument("--json", action="store_true", help="print JSON instead of the text table")
    ap.add_argument("--bands", action="store_true", help="also print the energy-per-band table")
    args = ap.parse_args(argv)

    files = collect(args.paths)
    if not files:
        print("no audio files found", file=sys.stderr)
        return 2
    results = []
    for f in files:
        try:
            r = analyze(f)
        except Exception as e:  # keep going: one bad file must not hide the rest
            print("FAILED %s: %s" % (f, e), file=sys.stderr)
            continue
        if args.out:
            png = write_picture(f, Path(args.out))
            r["picture"] = png.name if png else None
        results.append(r)
    game_rows = []
    if args.game:
        game_rows = apply_game(results, parse_sfx_luau(Path(args.game).read_text(encoding="utf-8")))
    if args.json:
        print(json.dumps({"files": results, "game": game_rows}, indent=1, default=float))
    else:
        print(text_table(results))
        if args.bands:
            print()
            print(band_table(results))
        for r in results:
            if r.get("notes"):
                print("  note %s: %s" % (r["file"], "; ".join(r["notes"])))
        if args.compare:
            print()
            print(compare_text(results, game_rows))
    if args.md:
        parts = ["## Per-file numbers", markdown_table(results), "", "## Energy per band", band_table(results), "",
                 "## Verdicts and notes"]
        for r in results:
            line = "- **%s**: %s (%s)" % (r["file"], r["verdict"], "; ".join(r["reasons"]))
            if r.get("notes"):
                line += ". Notes: " + "; ".join(r["notes"])
            parts.append(line)
        if args.compare or game_rows:
            parts += ["", "## Compare", "```", compare_text(results, game_rows), "```"]
        if args.out:
            rel = os.path.relpath(args.out, Path(args.md).parent).replace("\\", "/")
            parts += ["", "## Pictures (top: waveform; bottom: spectrogram, low pitch at the bottom; red line = 2 kHz, orange = 8 kHz, "
                      "white = 100 Hz / 1 kHz / 10 kHz)"]
            for r in results:
                if r.get("picture"):
                    parts += ["", "**%s**" % r["file"], "", "![%s](%s/%s)" % (r["file"], rel, r["picture"])]
        Path(args.md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.md).write_text("\n".join(parts) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
