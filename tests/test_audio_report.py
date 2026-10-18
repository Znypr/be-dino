"""Tests for tools/audio_report.py (docs/161): synthetic sounds with known answers (sine, clipped sine, silence, click)."""
from pathlib import Path
import contextlib
import io
import shutil
import sys
import tempfile
import unittest
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import audio_report as ar  # noqa: E402

SR = 44100
HAS_FFMPEG = ar.find_tool("ffmpeg") is not None and ar.find_tool("ffprobe") is not None


def tone(freq, seconds, db=-12.0, fade=0.01):
    t = np.arange(int(SR * seconds)) / SR
    x = np.sin(2 * np.pi * freq * t) * 10 ** (db / 20)
    n = int(SR * fade)
    if n:
        x[:n] *= np.linspace(0, 1, n)
        x[-n:] *= np.linspace(1, 0, n)
    return x


def write_wav(path, x, channels=1):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    if channels > 1:
        pcm = np.repeat(pcm[:, None], channels, axis=1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


class AudioReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="audio_report_test_"))
        write_wav(cls.tmp / "sine.wav", tone(440, 1.0, -12.0))
        write_wav(cls.tmp / "clipped.wav", np.clip(tone(440, 1.0, -12.0, fade=0) * 8, -1, 1))
        write_wav(cls.tmp / "silence.wav", np.zeros(SR))
        click = np.zeros(SR)
        click[SR // 2] = 0.9
        write_wav(cls.tmp / "click.wav", click)
        write_wav(cls.tmp / "padded.wav", np.concatenate([np.zeros(int(0.2 * SR)), tone(440, 0.5, -20.0), np.zeros(int(0.3 * SR))]))
        write_wav(cls.tmp / "shrill.wav", tone(4000, 1.0, -12.0))
        write_wav(cls.tmp / "loud.wav", tone(1000, 1.0, -2.0))
        write_wav(cls.tmp / "whisper.wav", tone(440, 1.0, -45.0))
        write_wav(cls.tmp / "stereo.wav", tone(440, 0.5, -12.0), channels=2)
        cls.r = {p.stem: ar.analyze(p) for p in sorted(cls.tmp.glob("*.wav"))}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_basic_facts(self):
        s = self.r["sine"]
        self.assertAlmostEqual(s["duration_s"], 1.0, places=3)
        self.assertEqual((s["sample_rate"], s["channels"]), (SR, 1))
        self.assertEqual(self.r["stereo"]["channels"], 2)

    def test_sine_levels(self):
        s = self.r["sine"]
        self.assertAlmostEqual(s["peak_db"], -12.0, delta=0.2)
        # a sine's RMS is 3.01 dB under its peak, so its crest factor is about 3 dB
        self.assertAlmostEqual(s["crest_db"], 3.0, delta=0.6)
        self.assertEqual(s["clip_events"], 0)
        self.assertEqual(s["clipped_samples"], 0)

    def test_sine_loudness_matches_bs1770_reference(self):
        # EBU Tech 3341/ITU-R BS.1770: a full-scale 1 kHz sine reads -3.01 LUFS; ours is 1 kHz at -2 dBFS peak -> about -5.0.
        # (K-weighting is about +0.7 dB at 1 kHz relative to the -0.691 offset, so the constant cancels.)
        self.assertAlmostEqual(self.r["loud"]["lufs_m"], -5.0 - 0.0, delta=0.6)

    def test_dominant_frequency_and_centroid(self):
        s = self.r["sine"]
        self.assertAlmostEqual(s["dominant_hz"], 440.0, delta=12.0)
        self.assertAlmostEqual(s["centroid_hz"], 440.0, delta=60.0)
        self.assertAlmostEqual(self.r["shrill"]["dominant_hz"], 4000.0, delta=25.0)

    def test_band_shares_sum_to_one_and_land_in_the_right_band(self):
        for name, r in self.r.items():
            if name == "silence":
                continue
            self.assertAlmostEqual(sum(r["bands"].values()), 1.0, places=6, msg=name)
        self.assertGreater(self.r["sine"]["bands"]["mid"], 0.95)
        self.assertGreater(self.r["shrill"]["bands"]["presence"], 0.95)

    def test_clipped_sine_is_detected_and_called_clipped(self):
        c = self.r["clipped"]
        self.assertGreater(c["clip_events"], 100)
        self.assertGreater(c["clipped_samples"], 1000)
        self.assertEqual(c["verdict"], "clipped")
        self.assertNotEqual(self.r["sine"]["verdict"], "clipped")

    def test_silence(self):
        s = self.r["silence"]
        self.assertEqual(s["verdict"], "silent")
        self.assertLess(s["peak_db"], -100)

    def test_click_has_instant_attack_big_crest_and_leading_silence(self):
        c = self.r["click"]
        self.assertAlmostEqual(c["lead_silence_s"], 0.5, delta=0.01)
        self.assertAlmostEqual(c["tail_silence_s"], 0.5, delta=0.01)
        self.assertLess(c["attack_ms"], 1.0)
        self.assertGreater(c["crest_db"], 20.0)
        self.assertGreater(c["sharp_score"], 90.0)

    def test_leading_and_trailing_silence(self):
        p = self.r["padded"]
        self.assertAlmostEqual(p["lead_silence_s"], 0.2, delta=0.02)
        self.assertAlmostEqual(p["tail_silence_s"], 0.3, delta=0.02)
        self.assertFalse(any("silent tail" in n for n in p["notes"]))  # 0.3 s is under the 0.5 s limit

    def test_attack_and_decay_of_a_shaped_sound(self):
        t = np.arange(int(SR * 1.0)) / SR
        x = np.sin(2 * np.pi * 440 * t) * np.minimum(t / 0.1, 1.0) * np.exp(-3.0 * np.maximum(t - 0.1, 0))
        path = self.tmp / "shaped.wav"
        write_wav(path, x * 0.5)
        r = ar.analyze(path)
        self.assertAlmostEqual(r["attack_ms"], 90.0, delta=12.0)  # 90% of a 100 ms linear ramp
        self.assertGreater(r["decay_ms"], 400.0)  # envelope falls 20 dB after ln(10)/3 = 0.77 s
        self.assertLess(r["decay_ms"], 1000.0)

    def test_verdict_words(self):
        self.assertEqual(self.r["shrill"]["verdict"], "harsh")
        self.assertEqual(self.r["loud"]["verdict"], "loud")
        self.assertEqual(self.r["whisper"]["verdict"], "too quiet")
        self.assertIn(self.r["sine"]["verdict"], ("ok", "calm"))

    def test_harshness_orders_sounds(self):
        self.assertGreater(self.r["shrill"]["harsh_score"], self.r["sine"]["harsh_score"] + 30)

    def test_all_thresholds_live_in_the_one_table(self):
        needed = {"clip_sample_level", "calm_lufs_max", "loud_lufs_max", "quiet_lufs_max", "harsh_score", "outlier_lu",
                  "silence_db", "sharp_attack_ms", "game_loud_lufs"}
        self.assertTrue(needed <= set(ar.THRESHOLDS))

    def test_outlier_detection(self):
        vals = {"a": -20.0, "b": -21.0, "c": -19.5, "d": -20.5, "loud_one": -12.0}
        out, med = ar.outliers(vals, ar.THRESHOLDS["outlier_lu"])
        self.assertEqual(list(out), ["loud_one"])
        self.assertAlmostEqual(med, -20.0)
        self.assertEqual(ar.outliers({"a": -20.0, "b": -10.0}, 4.0)[0], {})  # too few files to call anything an outlier

    def test_game_rows_use_the_file_that_owns_the_asset_id(self):
        cues = ar.parse_sfx_luau(
            'x = {\n    run_start = {id = "rbxassetid://1", volume = .25, rate = 1, gap = .5},\n'
            '    run_end = {id = "rbxassetid://1", volume = .2, rate = .9, gap = .5, len = .6},\n'
            '    empty = {id = "", volume = .6, rate = 1, gap = .3},\n}\n')
        self.assertEqual(cues["run_end"]["volume"], 0.2)
        rows = ar.apply_game([self.r["sine"] | {"file": "run_start.wav"}, self.r["loud"] | {"file": "run_end.wav"}], cues)
        by = {r["cue"]: r for r in rows}
        self.assertEqual(by["run_end"]["plays_file"], "run_start")  # the first named cue with that id owns the file
        self.assertNotIn("empty", by)
        self.assertAlmostEqual(by["run_end"]["game_lufs_m"], self.r["sine"]["lufs_m"] + 20 * np.log10(0.2), places=6)

    def test_command_line_table_and_compare(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = ar.main([str(self.tmp / "sine.wav"), str(self.tmp / "loud.wav"), str(self.tmp / "whisper.wav"),
                            str(self.tmp / "padded.wav"), "--compare"])
        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("sine.wav", text)
        self.assertIn("OUTLIER", text)

    @unittest.skipUnless(HAS_FFMPEG, "ffmpeg/ffprobe not installed")
    def test_picture_and_ogg_and_ffmpeg_cross_check(self):
        out = self.tmp / "pics"
        png = ar.write_picture(self.tmp / "sine.wav", out)
        self.assertIsNotNone(png)
        self.assertEqual(png.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        ogg = self.tmp / "sine.ogg"
        rc = ar.run([ar.find_tool("ffmpeg"), "-v", "error", "-y", "-i", str(self.tmp / "sine.wav"), str(ogg)]).returncode
        if rc == 0 and ogg.exists():  # needs an ogg encoder in the local ffmpeg build
            r = ar.analyze(ogg)
            self.assertAlmostEqual(r["dominant_hz"], 440.0, delta=15.0)
        # our K-weighted integrated loudness agrees with ffmpeg ebur128 (both implement BS.1770-4)
        cross = ar.ffmpeg_loudness(self.tmp / "sine.wav")
        self.assertIsNotNone(cross)
        self.assertAlmostEqual(self.r["sine"]["lufs_i"], cross, delta=0.3)

    def test_real_sfx_pack_is_readable(self):
        pack = ROOT / "assets/audio/sfx"
        for name in ("run_end", "shop_buy", "level_up"):
            r = ar.analyze(pack / (name + ".wav"))
            self.assertEqual(r["clip_events"], 0, name)
            self.assertLess(r["peak_db"], -1.0, name)


if __name__ == "__main__":
    unittest.main()
