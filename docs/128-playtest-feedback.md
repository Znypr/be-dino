# Playtest feedback tool (docs/128)

Status: **Review / test. CURRENT BUILD BEHAVIOR: off by default; on only in the playtest profile.** Added for the first friends playtest (docs/125). Not Studio- or phone-verified yet: the lead must screenshot the button and panel (docs/72 review rule) and confirm it does not overlap the HUD.

## What players see
- A small **Tell us!** button, bottom-left, 120 x 48 px (touch target above 44 px).
- It opens a panel with three rows of three emoji faces: **Fun?**, **Hard?** (too easy / just right / too hard), **Looks?**, an optional text box (140 characters), SEND and CLOSE.
- Short replies: "Thank you!", "Try again in a little while", "Thanks! That is all for today". All text is plain, short and kid-friendly (docs/72). Emoji are text, not art; final icons are a separate art task.

## Server rules (src/server/FeedbackService.luau)
- One RemoteEvent `BeDinoRemotes/PlaytestFeedback`, created only when `Config.PlaytestFeedbackEnabled` is true.
- Rate limit per player: 1 per 2 minutes, at most 10 per session (memory only, `src/shared/PlaytestFeedback.luau`).
- Ratings are clamped to 1-3; the text goes through `TextService:FilterStringAsync` (`GetNonChatStringForBroadcastAsync`) in a pcall. **Raw text is never stored or printed**; if filtering fails the text is dropped and only the ratings are logged.
- Prints one line: `[BD-FEEDBACK] {"event":"feedback","fun":3,"level":2,"looks":3,"runs":2,"location":"Run","species":"compy","text":"..."}`. Fields: three ratings (0 = not answered), run count this session (counted from `Location` becoming `Island`), `location` Hub or Run, equipped species id, filtered text. No UserId, name or session id.
- No gameplay, FoodService, nest, cosmetic, movement, hatch or FX code is touched. Nothing is written to a profile.

## Flag
`Config.PlaytestFeedbackEnabled = false` in source; `tools/release_profiles.py` requires false in the default profile and sets true in the playtest profile.

## Report
`python tools/feedback_report.py server.log [--json]` prints entries, average per rating (fun and looks 1 sad, 3 happy; level 1 too easy, 3 too hard), split by hub and run, and the filtered comments. `python tools/verify_feedback.py --runner <luau>` is the CI check (also wired into `.github/workflows/build-generated-place.yml`).
