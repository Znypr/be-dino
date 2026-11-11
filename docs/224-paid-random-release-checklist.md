# 224 Paid and paid-random release checklist (BD-1167)

Label: **LEAD / COMPLIANCE checklist**, 2026-11-11. One list to tick before any build reaches players, and again before any Robux line opens. Rules come from [43](43-player-access-and-paid-random-policy.md), the [Roblox paid random items policy](https://create.roblox.com/docs/production/monetization/paid-random-items), AGENTS.md and the research ([221](221-po-plan-team-and-research-2026-11-10.md) C6). This page does not repeat them; it says what must be TRUE and how to check it. Paid flags stay closed (`CrystalPacksEnabled`, `PaidRandomItemsEnabled`); nothing here opens them.

## A. Before ANY publish to players (friends playtest included)

| # | Must be true | How to check | Who |
| --- | --- | --- | --- |
| A1 | **No Robux product can be bought.** The six crystal packs (ids in `Config.DeveloperProducts`) exist and were "Enabled" on newbuild on 2026-10-18 (BD-612). The server still pays them, because refusing a charged buyer is worse. | Creator Hub > the experience > Monetization > Developer Products: each of the six is **off sale** (or archived). Do not delete the `Config` table: `PaidRandomGate` reads it. | **Owner** (account page) |
| A2 | Paid lines are closed in the build that ships. | `python tools/verify_robux_line.py` and `python tools/verify_paid_random_gate.py` pass; `python tools/verify_release.py --profile playtest` passes. | Lead (CI) |
| A3 | The content questionnaire answer on Paid Random Items matches the shipped build (no paid random items while A1 and A2 hold). | Creator Hub questionnaire (BD-1136). | **Owner** |
| A4 | No game pass or product is shown in any menu. | Playtest build: open every shop tab. | QA (Studio) |

## B. Before a Robux line opens (any developer product, pass or premium currency)

| # | Must be true | How to check |
| --- | --- | --- |
| B1 | Which currencies are **Robux-linked** is written down. If crystals can be bought, crystals are Robux-linked, and everything crystals buy that is random (eggs, nests, luck or mutation potions, fusion outcomes) becomes a **paid random item**. | A table in the release doc, reviewed against `Config` shop items. |
| B2 | Every paid random item shows **all possible outcomes with numbers** before purchase, in kid-readable form (docs/72). | Studio look per item, screenshot in evidence. |
| B3 | `PolicyService` is checked on the **server**; restricted, failed and pending policy all count as "not allowed"; normal play and free earned eggs stay available. | `verify_paid_random_gate.py` truth table, plus a Studio run with a forced restricted policy. |
| B4 | Run eggs stay **play-only**: no Robux or Robux-linked currency changes how many run eggs you get or what they hatch. | Code review of settlement and egg rolls. |
| B5 | If trading ever exists, `IsPaidItemTradingAllowed` is enforced. | Review. |
| B6 | Receipts are granted exactly once, and survive a crash or a rejoin. | `verify_robux_line.py` plus a Studio test purchase on a private test universe. |

## C. Things we never sell (standing rule, kid-safe)

- Streak repair, or relief from a punishment or a loss.
- Protection from other players, or power over other players.
- Limited-**quantity** pressure ("only 3 left"), countdowns on paid offers, or offers timed at a loss (failed egg, death). Time-limited seasonal cosmetics are allowed.
- Anything the copy calls "free" that is not.

Allowed and preferred: non-random convenience that removes a real pain at the moment of need (a sixth nest spot when nests are full, a bigger egg bag) and cosmetics bound to one dino. Measure D1 and playtime before and after every shop change (BD-1166 telemetry).

## D. Status on 2026-11-11

A1 open (owner), A2 green on main, A3 open (owner, BD-1136), A4 not checked in Studio. Section B is not started: no Robux line is planned before the friends playtest.
