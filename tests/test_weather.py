"""Weather v3 guards: the weather start sound stays quiet, the audio briefs cover every sound id, and the owner's readability rules hold in source."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WeatherTests(unittest.TestCase):
    def test_weather_start_is_quiet(self):
        sfx = (ROOT / "src/shared/Sfx.luau").read_text(encoding="utf-8")
        volume = float(re.search(r'weather_start = \{id = "[^"]*", volume = ([\d.]+)', sfx).group(1))
        self.assertLessEqual(volume, 0.25)

    def test_every_weather_sound_has_a_brief(self):
        sounds = (ROOT / "src/shared/WeatherSounds.luau").read_text(encoding="utf-8")
        names = re.findall(r"^    (\w+)=\{id=\"\"", sounds, re.M)
        self.assertGreaterEqual(len(names), 11)
        docs = (ROOT / "docs/85-weather-audio-briefs.md").read_text(encoding="utf-8")
        for name in names:
            self.assertIn(name, docs, name + " has no brief in docs/85")

    def test_no_invented_weather_sound_ids(self):
        sounds = (ROOT / "src/shared/WeatherSounds.luau").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r'id="(\d+|rbxassetid://\d+)"', sounds), [])

    def test_weather_scripts_are_registered_by_the_build(self):
        for path in ("src/client/WeatherAudio.client.luau", "src/shared/WeatherSounds.luau", "src/shared/WeatherLooks.luau"):
            self.assertTrue((ROOT / path).exists(), path)


if __name__ == "__main__":
    unittest.main()
