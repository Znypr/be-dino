"""Tests for tools/studio/run_player_bot.py (BD-1048, docs/194): the snippets it prints are short, safe and well formed.
No Studio, no network. The Luau file itself is compiled by CI's Luau runner check (tools/studio is not under src/)."""
from pathlib import Path
import argparse
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "studio"))
import run_player_bot as rb  # noqa: E402


def args(*argv):
    return rb.parser().parse_args(list(argv))


class PlayerBotSnippets(unittest.TestCase):
    def test_install_is_the_bot_file(self):
        text = rb.render("install")
        self.assertIn("shared.PlayerBot = Bot", text)
        self.assertIn("function Bot.start", text)

    def test_every_loop_in_the_bot_waits(self):
        text = (ROOT / "tools" / "studio" / "player_bot.luau").read_text(encoding="utf-8")
        self.assertGreaterEqual(text.count("task.wait"), 8)
        self.assertNotIn("while true do", text)

    def test_start_options(self):
        a = args("start", "--seconds", "300", "--max-distance", "60", "--think", "0.4", "--no-end-run")
        self.assertEqual(rb.render("start", a).splitlines()[-1],
                         "return Bot.start({stopSeconds = 300, maxDistance = 60, thinkSeconds = 0.4, autoEndRun = false})")

    def test_start_without_options_is_empty_table(self):
        self.assertIn("Bot.start({})", rb.render("start", args("start")))

    def test_bad_number_is_refused(self):
        with self.assertRaises(ValueError):
            rb.render("start", args("start", "--seconds", "-5"))
        with self.assertRaises(ValueError):
            rb.render("start", args("start", "--seconds", "nan"))

    def test_small_snippets(self):
        for action, argv in (("status", ["status"]), ("report", ["report"]), ("log", ["log", "--from", "3", "--to", "9"]),
                             ("buttons", ["buttons"]), ("stop", ["stop"])):
            text = rb.render(action, args(*argv))
            self.assertLess(len(text), 300, action)
            self.assertIn("assert(Bot", text)
        self.assertIn("Bot.lines(3, 9)", rb.render("log", args("log", "--from", "3", "--to", "9")))


if __name__ == "__main__":
    unittest.main()
