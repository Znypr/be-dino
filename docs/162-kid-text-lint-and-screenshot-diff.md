# 162 Kid-text lint and screenshot diff (BD-655, BD-656)

Written 2026-10-18. Owner request: two offline helper tools. Both run on any PC with Python. Neither needs Studio, Blender or Roblox. Neither changes the game.

Label: **CURRENT BUILD** (the tools exist and are tested). Whether every flagged text should be rewritten is an **OWNER TARGET** question and is not decided here.

## 1. Kid-text lint: `tools/lint_kid_text.py` (BD-655)

**What it does.** The owner rule is "children as audience: short, obvious text" ([72](72-ui-copy-and-asset-standards.md), [114](114-handbook.md)). The tool reads `src/client` and `src/shared` and finds the words a player can see: `Text = "..."`, `notify("...")`, label and button helpers, copy tables, `string.format` templates, error message tables. It does not look at ids, `warn`, `print`, `Name =` or `if x == "..."`. Then it checks each text.

| Rule | Catches | Say instead |
| --- | --- | --- |
| TIME_NOISE | "5m 0s", "2h 0m", "1:02:03" | "5 min", "2 h" |
| MULTIPLIER | "1.25x", "x2" | "Speed +25%" |
| DECIMAL | "2.5", `%.1f` | a whole number |
| RAW_ID | `rbxassetid`, "BD-12", `save_failed`, `CamelCaseName`, 7+ digit numbers | plain words |
| SHOUTING | ALL CAPS beyond a short word, "!!!" | normal capitals |
| LONG_TEXT | too many words, letters or sentences for the place it sits | shorter |
| JARGON | server, profile, revision, lease, DataStore, cooldown, RNG, probability, request... | plain words |
| TECH_PUNCT | `; | { } [ ] < > -> ::` | simple marks |

All limits live in ONE table at the top of the tool (`LIMITS`: letters, words and sentences for each place: title, button, label, toast, body). The jargon list (`JARGON`) and the caps rules (`CAPS_*`) are tables too. Print them with `python tools/lint_kid_text.py --rules`. Change a number there and the tool follows.

**Commands.**

```
python tools/lint_kid_text.py                      # every problem, exit 1 if any
python tools/lint_kid_text.py --baseline           # CI mode: exit 1 only for NEW problems
python tools/lint_kid_text.py --write-baseline     # record today's problems as the baseline
python tools/lint_kid_text.py --report --top 20    # worst files and worst texts (add --markdown)
python tools/lint_kid_text.py --rules              # show the limits and word lists
python tools/lint_kid_text.py --selftest           # built-in examples
python tools/lint_kid_text.py src/client/FusionMenu.luau   # one file
```

**Old problems and new problems.** The game already has some long and loud text, and this task does not edit game strings. `tools/lint_kid_text_baseline.json` records the problems that exist today (file + rule + text, no line numbers, so moving code does not matter). CI runs `--baseline`: a problem that is in the file is fine, a NEW one fails the check. When someone fixes old text, run `--write-baseline` so the list shrinks (the tool says how many were fixed). Never add new problems to the baseline by hand.

**Letting a text through.** Three ways, from best to worst:
1. Fix the text (short, plain words).
2. Add `-- kidtext-ok: reason` at the end of the line.
3. Add an entry to `tools/lint_kid_text_allow.json` (`file`, `rule`, optional exact `text`, and a `reason` a non-programmer can read). An entry without a reason stops the tool.

Files players never see (admin, QA, demo, sound lab) are skipped; the list and the reason for each is `EXCLUDED_FILES` in the tool.

**What it cannot do.** It finds text by reading code, not by running the game. Text built from many pieces (`"Ready in " .. time`) is checked piece by piece. Text loaded from elsewhere is missed. A single word in a data table that is shown to players may be missed. It is a safety net, not a judge: the lead still looks at every new screen ([72](72-ui-copy-and-asset-standards.md) Review).

**First run.** 387 files scanned, 94 old problems in 15 files. Worst files: `Bootstrap.client.luau` (30), `FusionSelection.luau` (21), `ShopOdds.luau` (12), `FusionMenu.luau` (8). The list is in [the evidence report](evidence/2026-10-18-kid-text/report.md). No "5m 0s" times were found.

## 2. Screenshot diff: `tools/compare_screenshots.py` (BD-656)

**What it does.** Takes two pictures (or two folders of same-named PNGs) and says what changed. It counts the changed pixels, gives the changed area as a percent, draws a box around each changed spot, and saves one picture: **before | after | changed** (changed pixels red). Then one plain sentence, for example "TOO MUCH CHANGE: 12.50% of the picture changed in 1 spot (allowed 0.5%). Biggest spot: 60x50 at (100,50)." Uses Pillow only (the tools folder already uses it); nothing new to install.

**Commands.**

```
python tools/compare_screenshots.py before.png after.png                    # writes after_diff.png
python tools/compare_screenshots.py before.png after.png --out diff.png
python tools/compare_screenshots.py before_dir after_dir --out diffs        # same file names are paired
python tools/compare_screenshots.py a.png b.png --ignore 1700,10,200,40     # skip a clock (X,Y,W,H)
python tools/compare_screenshots.py before_dir after_dir --ignore-file ignore.json
python tools/compare_screenshots.py a.png b.png --threshold 8 --max-changed-percent 2 --json
```

`ignore.json` looks like `{"*": [[1700, 10, 200, 40]], "menu.png": [[0, 0, 100, 30]]}` (`*` = every picture). Ignored parts are drawn with a blue outline in the changed panel and do not count toward the percent.

**Numbers you can change.** `--threshold` (default 16 of 255: how far one colour must move to count; hides tiny colour noise), `--max-changed-percent` (default 0.5: how much change is allowed), `--min-pixels` (hide tiny specks from the list of boxes).

**Exit code.** 0 = all the same or within the limit. 1 = changed too much, different sizes, or in folder mode a picture missing on one side (`--allow-missing`, `--allow-new` relax that). 2 = wrong use.

**Tried on a real picture.** One of the existing review pictures with a red box and a blue circle painted on: both spots were found with exact sizes, in 0.2 s for a 2280x1570 picture.

**What it cannot do.** It compares pixels, so a one-pixel shift of the whole picture looks like a big change. Take the two pictures from the same camera spot and size. It does not know what is a good or bad change: a person still looks at the red picture. Animated parts (flames, sparkles, clocks) need an ignore box. It is not Studio or phone acceptance by itself ([114](114-handbook.md) section 12).

## 3. Checks

- `python -m unittest tests.test_lint_kid_text tests.test_compare_screenshots` (made-up Luau snippets and generated images; the lint test also checks that the real tree has no NEW problems).
- CI: `python tools/lint_kid_text.py --baseline` in `.github/workflows/build-generated-place.yml`. The screenshot tool is on demand, not in CI.
