#!/usr/bin/env python3
"""Print the Luau snippet to paste into the Studio MCP `execute_luau` (datamodel_type Client, Play session running) for the Studio test bot
tools/studio/player_bot.luau (BD-1048, docs/194). Like render_insert_snippet.py it only prints text; it never talks to Studio.

  python tools/studio/run_player_bot.py install                      # the whole bot (paste once per Play session)
  python tools/studio/run_player_bot.py start --seconds 300          # starts the walk (starts the run itself)
  python tools/studio/run_player_bot.py start --stop-food 500        # or stop at about 500 food points
  python tools/studio/run_player_bot.py start --max-distance 60 --think 0.4   # a player who sees only what is on screen and looks around
  python tools/studio/run_player_bot.py start --no-start-run         # you start the run by hand; --no-end-run: you end it by hand
  python tools/studio/run_player_bot.py start --casual --max-distance 90   # the slow, casual walker (about 60 percent of full speed, no value seeking)
  python tools/studio/run_player_bot.py summary                      # points by kind, amber + drumstick share, points from repeat eats
  python tools/studio/run_player_bot.py status                       # one line: phase, seconds, food, eggs, last event
  python tools/studio/run_player_bot.py report [--lines 400]         # totals, a table per 30 s, every event except single eats
  python tools/studio/run_player_bot.py log --from 1 --to 80         # raw log lines (one line per event, eats included)
  python tools/studio/run_player_bot.py buttons                      # the open buttons and where to click (for the Run Complete card)
  python tools/studio/run_player_bot.py stop

The snippets for everything but `install` are one line long. Every loop in the bot waits, so Studio never freezes.
"""
import argparse
import re
import sys
from pathlib import Path

BOT = Path(__file__).with_name("player_bot.luau")

OPTION_KEYS = {  # CLI name -> (Luau name, kind)
    "seconds": ("stopSeconds", "number"),
    "stop_food": ("stopFood", "number"),
    "avoid": ("predatorAvoid", "number"),
    "max_distance": ("maxDistance", "number"),
    "think": ("thinkSeconds", "number"),
}


def lua_number(value):
    if value is None:
        raise ValueError("number expected")
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")) or number < 0 or number > 1e6:
        raise ValueError("number out of range: %r" % value)
    return repr(int(number)) if number == int(number) else repr(number)


def options_table(args):
    parts = []
    for cli, (lua, _kind) in OPTION_KEYS.items():
        value = getattr(args, cli, None)
        if value is not None:
            parts.append("%s = %s" % (lua, lua_number(value)))
    if getattr(args, "casual", False):
        parts.append("casual = true")
    if getattr(args, "no_start_run", False):
        parts.append("autoStartRun = false")
    if getattr(args, "no_end_run", False):
        parts.append("autoEndRun = false")
    return "{" + ", ".join(parts) + "}"


def render(action, args=None):
    if action == "install":
        return BOT.read_text(encoding="utf-8")
    guard = 'local Bot = shared.PlayerBot assert(Bot, "bot not installed: run the install snippet first")\n'
    if action == "start":
        return guard + "return Bot.start(%s)\n" % options_table(args)
    if action == "status":
        return guard + "return Bot.status()\n"
    if action == "summary":
        return guard + "return Bot.summary()\n"
    if action == "report":
        return guard + "return Bot.report(%d)\n" % int(args.lines)
    if action == "log":
        return guard + "return Bot.lines(%d, %d)\n" % (int(args.from_), int(args.to))
    if action == "buttons":
        return guard + "return Bot.buttons()\n"
    if action == "stop":
        return guard + "return Bot.stop()\n"
    raise ValueError("unknown action %r" % action)


def parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="action", required=True)
    sub.add_parser("install")
    st = sub.add_parser("start")
    st.add_argument("--seconds", type=float, help="stop this many seconds after the run began (default 300)")
    st.add_argument("--stop-food", dest="stop_food", type=float, help="or stop at this many food points")
    st.add_argument("--avoid", type=float, help="skip food and flee within this many studs of a predator (default 34)")
    st.add_argument("--max-distance", dest="max_distance", type=float, help="only look at food this close (default 170)")
    st.add_argument("--think", type=float, help="stand still this many seconds before choosing each next food (default 0)")
    st.add_argument("--casual", action="store_true", help="the casual walker of the round-3b pace run (nearest-six, short walks, pauses); use with --max-distance 90")
    st.add_argument("--no-start-run", action="store_true")
    st.add_argument("--no-end-run", action="store_true")
    sub.add_parser("status")
    sub.add_parser("summary")
    rp = sub.add_parser("report")
    rp.add_argument("--lines", type=int, default=400)
    lg = sub.add_parser("log")
    lg.add_argument("--from", dest="from_", type=int, default=1)
    lg.add_argument("--to", type=int, default=100000)
    sub.add_parser("buttons")
    sub.add_parser("stop")
    return ap


if __name__ == "__main__":
    a = parser().parse_args()
    try:
        sys.stdout.write(render(a.action, a))
    except ValueError as exc:
        sys.exit("ERROR: %s" % exc)
