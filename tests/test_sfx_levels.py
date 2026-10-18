"""SFX level checks (BD-166, BD-637, docs/161): cue volumes stay in the quiet range and no cue is much louder than the rest.

Reads src/shared/Sfx.luau and the WAV files committed in assets/audio/sfx (plain 16-bit WAV: no ffmpeg needed). Only the
re-render test needs ffmpeg and is skipped when it is missing. Numbers only: nobody listened (the owner judges by ear).
"""
from pathlib import Path
import re
import sys
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import audio_report as ar  # noqa: E402
import render_soft_sfx as rs  # noqa: E402

SFX = ROOT / "src/shared/Sfx.luau"
PACK = ROOT / "assets/audio/sfx"
FIX = ROOT / "docs/evidence/2026-10-18-audio-fix"

OUTLIER_LU = 4.0  # no cue louder than the pack median by more than this (docs/161: 3 LU is the usual tolerance)
# Rare payoff cues (the rarity reveal stings and the two rare hatch files) sit well above the median ON PURPOSE: the rarer the egg, the
# bigger the moment (docs/87, BD-437 ladder, tested in tools/verify_audio.py). Holding them to 4 LU would flatten that ladder, so they get
# their own cap, a little above today's level (hatch_reveal_legendary +7.8, epic +7.0, the rest about +5.5), so they cannot creep louder.
PAYOFF_CAP_LU = {"hatch_rare": 6.0, "hatch_reveal_rare": 6.0, "hatch_legendary": 6.0, "hatch_reveal_epic": 7.5, "hatch_reveal_legendary": 8.5}
EVERYDAY = ("pickup", "pickup_hi", "pickup_lo", "ui_click", "run_start", "run_end", "shop_buy", "shop_refresh", "weather_start",
            "level_up", "hatch_crack", "hatch_crack_stage")
# Files the report still calls harsh: the soft re-renders exist but are not uploaded yet (kanban BD-997). When the asset id of one of
# these cues changes, the cue is measured with its new file and must pass like every other cue.
PENDING_UPLOAD = {"shop_buy": "rbxassetid://102585210519734", "shiny_bang": "rbxassetid://124365194004947"}


def cues():
    return ar.parse_sfx_luau(SFX.read_text(encoding="utf-8"))


def player_levels():
    results = [ar.analyze(p) for p in sorted(PACK.glob("*.wav"))]
    rows = {r["cue"]: r for r in ar.apply_game(results, cues())}
    median = float(np.median([r["game_lufs_m"] for r in rows.values()]))
    return rows, median


class QuietConstants(unittest.TestCase):
    def test_every_volume_is_in_range(self):
        text = SFX.read_text(encoding="utf-8")
        top = float(re.search(r"Sfx\.MaxCueVolume\s*=\s*([\d.]+)", text).group(1))
        self.assertLessEqual(top, 0.9)
        self.assertGreater(len(cues()), 20)
        for name, c in cues().items():
            self.assertGreater(c["volume"], 0, name)
            self.assertLessEqual(c["volume"], top, name)
            self.assertTrue(0.5 <= c["rate"] <= 1.2, "%s rate %s" % (name, c["rate"]))

    def test_everyday_cues_are_quiet(self):
        c = cues()
        for name in EVERYDAY:
            self.assertLessEqual(c[name]["volume"], 0.6, name)
        self.assertLessEqual(c["level_up"]["volume"], 0.3)          # BD-166: was .4, the loudest automatic run-end cue
        self.assertLessEqual(c["run_end"]["volume"], 0.25)           # BD-166: soft chime stays soft
        self.assertLessEqual(c["hatch_legendary"]["volume"], 0.75)  # was .85, +5.7 LU over the median

    def test_pending_cues_are_softened_until_the_new_file_is_uploaded(self):
        c = cues()
        if c["shop_buy"]["id"] == PENDING_UPLOAD["shop_buy"]:
            self.assertLessEqual(c["shop_buy"]["rate"], 0.8)        # the old file plays lower and slower; the new file is rendered at .75
        else:
            self.assertGreaterEqual(c["shop_buy"]["rate"], 0.95, "new shop_buy_soft file is already slowed: play it at rate 1")
        if c["shiny_bang"]["id"] == PENDING_UPLOAD["shiny_bang"]:
            self.assertLessEqual(c["shiny_bang"]["volume"], 0.6)


class PackLevels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.median = player_levels()

    def test_no_cue_is_louder_than_the_pack_median_by_more_than_4_lu(self):
        for name, r in self.rows.items():
            gap = r["game_lufs_m"] - self.median
            self.assertLess(gap, PAYOFF_CAP_LU.get(name, OUTLIER_LU), "%s is %+.1f LU over the median %.1f" % (name, gap, self.median))

    def test_level_up_is_back_at_the_median(self):
        self.assertLess(self.rows["level_up"]["game_lufs_m"] - self.median, 2.0)

    def test_only_the_files_waiting_for_upload_are_harsh(self):
        c = cues()
        for name, r in self.rows.items():
            if r["verdict"] == "harsh":
                self.assertEqual(c[name]["id"], PENDING_UPLOAD.get(name), "%s is harsh: %s" % (name, r["why"]))

    def test_nothing_clips(self):
        for p in PACK.glob("*.wav"):
            self.assertEqual(ar.analyze(p)["clip_events"], 0, p.name)


class SoftCandidates(unittest.TestCase):
    """The re-rendered files kept as evidence (not uploaded, no asset id): they must measure ok or calm and stay small."""

    def test_committed_candidates_are_ok_or_calm(self):
        total = 0
        for name, old in (("shop_buy_soft", "shop_buy"), ("shiny_bang_soft", "shiny_bang")):
            path = FIX / (name + ".wav")
            self.assertTrue(path.exists(), path)
            total += path.stat().st_size
            new, before = ar.analyze(path), ar.analyze(PACK / (old + ".wav"))
            self.assertIn(new["verdict"], ("ok", "calm"), "%s: %s" % (name, new["reasons"]))
            self.assertLess(new["harsh_score"], 40, name)
            self.assertLess(new["harsh_score"], before["harsh_score"] - 20, name)
            self.assertLess(new["bands"]["air"], 0.05, name)          # nothing above 8 kHz (docs/110 style rule 2)
            self.assertEqual(new["clip_events"], 0, name)
        self.assertLess(total, 5 * 1024 * 1024)

    @unittest.skipIf(rs.find_ffmpeg() is None, "ffmpeg not installed")
    def test_render_recipe_reproduces_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            made = rs.render(rs.find_ffmpeg(), Path(tmp))
            self.assertEqual(len(made), 2)
            for p in made:
                r = ar.analyze(p)
                self.assertIn(r["verdict"], ("ok", "calm"), p.name)


if __name__ == "__main__":
    unittest.main()
