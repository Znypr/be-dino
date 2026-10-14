# 72 UI copy and UI asset standards (owner, 2026-10-14)

Short rules every contributor and agent follows. The audience is children: keep information minimal and obvious.

## In-game text
- Time: round and drop zeros. "5 min", "10 min", "2 h", "Ready in 3 h", "Back in 40 s" only under a minute. Never "5m 0s" or "2h 0m".
- Multipliers: plain words or percent. "Speed +20%" not "1.2x"; "Growth +25%". One number per line.
- One short line per fact. No jargon (no 'transform', 'window', 'idle', 'ledger'). Name the thing and the benefit: "Swift Sip: run faster for 5 min".
- Counts are plain: "1 left", "Sold out". No decimals except where a real number is the point.
- Errors say what to do next in a few words.
- No visible internal rules or hidden thresholds (for example, nest drop requirements stay invisible).

## UI art and icons
- Do not generate UI art or icons ad hoc in code (vector shapes, native shape stacks) as final art. Such code drawings are PLACEHOLDERS: mark them `PLACEHOLDER` in code and in the task, and they never count as done.
- Final UI art is its own task with this flow: brief (what, where, size, states) -> 2D drafts in 2-3 styles -> lead/owner picks -> final export at target sizes (plus phone size check) -> import/upload by the owner -> verified in Studio next to neighbouring UI.
- Quality bar before 'done': matches the v2 kit (chunky outline, saturated palette, rounded forms, same light direction), readable at 64 px and at phone size, distinct from every sibling icon, no leftover placeholder symbols.
- Do not invent Roblox asset IDs.

## Review
- The lead checks every new screen in Studio with a screenshot before merge (copy rules and art rules above included).
