"""Sanity tests for the generated sound-effect pack."""
from pathlib import Path
import hashlib
import json
import sys
import unittest
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import generate_sfx  # noqa: E402

SFX = ROOT / "assets/audio/sfx"
REQUIRED = {
    "hatch_crack", "hatch_common", "hatch_rare", "hatch_legendary", "shiny_bang", "big_thud",
    "pickup", "run_start", "run_end", "shop_buy", "shop_refresh", "weather_start",
    "level_up", "fusion_reveal", "ui_click",
}


def load(name):
    with wave.open(str(SFX / f"{name}.wav")) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, 44100)
        return np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(float) / 32768


class SfxPackTests(unittest.TestCase):
    def test_manifest_lists_required_files(self):
        man = json.loads((SFX / "manifest.json").read_text())
        names = {s["name"] for s in man["sounds"]}
        self.assertTrue(REQUIRED <= names)
        for s in man["sounds"]:
            self.assertTrue((SFX / s["file"]).exists())
            for key in ("durationSeconds", "peakDbfs", "suggestedVolume", "suggestedRateJitter", "trigger"):
                self.assertIn(key, s)

    def test_durations_peaks_and_edges(self):
        for name in sorted(REQUIRED):
            with self.subTest(name=name):
                x = load(name)
                self.assertFalse(np.isnan(x).any())
                self.assertGreaterEqual(len(x) / 44100, 0.05)
                self.assertLessEqual(len(x) / 44100, 2.5)
                peak = 20 * np.log10(np.abs(x).max())
                self.assertTrue(-3.5 <= peak <= -2.5, peak)
                self.assertLess(abs(x[0]), 0.01)
                self.assertLess(abs(x[-1]), 0.01)

    def test_pack_is_small(self):
        self.assertLess(sum(p.stat().st_size for p in SFX.iterdir()), 2_000_000)

    def test_regeneration_is_deterministic_and_matches_disk(self):
        a = generate_sfx.render(generate_sfx.__dict__.get("SEED", 1014))
        b = generate_sfx.render(1014)
        digest = lambda d: hashlib.sha256(b"".join(d[k].tobytes() for k in sorted(d))).hexdigest()
        self.assertEqual(digest(a), digest(b))
        self.assertNotEqual(digest(a), digest(generate_sfx.render(7)))
        for name, pcm in b.items():
            diff = np.abs((load(name) * 32768).round().astype(int) - pcm.astype(int)).max()
            self.assertLessEqual(diff, generate_sfx.TOL_LSB, name)


if __name__ == "__main__":
    unittest.main()
