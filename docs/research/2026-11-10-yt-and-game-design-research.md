# YouTube study tools + game design research for Be Dino!

Date: 2026-11-10. Author: researcher sub-agent (read-only research, no code or balance changes).
Status: **RESEARCH / PROPOSALS ONLY.** Nothing here is an owner decision, a shipped feature or a balance value. Every "apply to Be Dino" line is an idea for the backlog ([docs/07-kanban.md](../07-kanban.md)), to be checked against the owner target in [docs/09](../09-reward-economy.md) and [docs/03](../03-game-design.md) before anyone builds it.

How to read it: Part A = tools, Part B = what each video actually says, Part C = synthesis and the ranked "Top 15 actions". If you only read one thing, read the Top 15 at the end.

---

## 0. Method and what was not verified

- **Transcripts were NOT blocked.** `youtube-transcript-api` 1.2.5 fetched 23 of 23 transcripts from this PC (Python 3.14, no login, no cookies). `yt-dlp` 2026.10.26 was used for search and metadata only (no video was downloaded).
- 21 videos were read from the transcript. Two long ones were read in part (marked). One candidate (Onett's "Fireside Chat" cut) turned out to be a re-cut of the RDC 2025 retention panel and was dropped as a duplicate.
- Repo stars, last push and licence come from the GitHub API (`gh api repos/...`) on 2026-11-10.
- Written sources were read through a page summariser (WebFetch), not line by line.

Not verified (details repeated where they matter):

1. GameAnalytics benchmark numbers come from a secondary write-up of the 2025 Roblox report, not from the report's own tables.
2. Creator revenue claims in YouTube videos (e.g. "$12.5k a month", "3% click rate") are the creators' own claims.
3. `faster-whisper` / `whisperX` were not installed or run here. PyPI shows Windows wheels for Python 3.14 for `ctranslate2` 4.9.0 and `torch` 2.15.0, but the full dependency chain (especially whisperX's diarisation packages) on 3.14 is untested.
4. Whether Be Dino already has a given feature: I only did a keyword scan of the Kanban (no hits for "daily reward", "analytics", "pity", "private server"; hits for quest, leaderboard, offline, event, icon). Treat "new for Be Dino" as "probably new".
5. The Roblox discovery signal list changed between the October 2025 webinar (six 7-day signals) and the current docs (eight signals, 28-day view since June 2026). I report both; the docs are the current ones. Signal weights are only visible inside Creator Analytics, which I cannot see.
6. Effort (S/M/L) and impact rankings are my estimates. No Be Dino player data exists yet.

---

## Part A: Top 10 GitHub repos for studying YouTube videos

Ranked for OUR setup: Windows 11, Python 3.14, NVIDIA GPU, Claude Code as the agent that reads the text.

| # | Repo | Stars | Last push | Licence | What it does | Verdict |
|---|---|---:|---|---|---|---|
| 1 | [jdepoix/youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) | 8.6k | 2026-11-09 | MIT | Fetches existing captions (manual or auto) with timestamps. No API key, no browser. | **USE. Already proven today: 23/23 videos, about 1.5 s each.** First choice for any video that has captions. |
| 2 | [yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp) | 207k | 2026-11-04 | Unlicense | Search, metadata, chapters, playlists and channels, subtitle files, audio-only download. | **USE.** Search and bulk listing (`ytsearchN:`, flat playlist), plus audio-only when a video has no captions. Pure Python wheel, runs on 3.14. |
| 3 | [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) | 26.7k | 2026-11-10 | MIT | Whisper speech-to-text on CTranslate2, fast on NVIDIA GPUs. | **USE as fallback** for videos without captions. Wheels exist for 3.14; not test-run here. Heavy GPU job: ask before running (house rule). |
| 4 | [m-bain/whisperX](https://github.com/m-bain/whisperX) | 25.2k | 2026-10-22 | BSD-2-Clause | faster-whisper plus word-level timestamps and speaker labels. | **Only for panels/podcasts** where "who said it" matters. Speaker models need a Hugging Face login and their own terms; 3.14 support untested. |
| 5 | [Breakthrough/PySceneDetect](https://github.com/Breakthrough/PySceneDetect) | 5.4k | 2026-11-10 | BSD-3-Clause | Finds scene cuts and saves one image per scene. | **USE when slides matter** (talks with charts, UI teardowns). Needs the video file, so it breaks our "text only" default; use on request. |
| 6 | [steipete/summarize](https://github.com/steipete/summarize) | 6.8k | 2026-11-05 | MIT | CLI: point at a URL/YouTube/podcast, get a summary; falls back to Whisper. | **Skip for now.** Claude already does the summarising; this adds a second LLM and API keys. Good if the owner wants a one-command tool outside Claude. |
| 7 | [danielmiessler/Fabric](https://github.com/danielmiessler/Fabric) | 44.6k | 2026-11-10 | MIT | Prompt "patterns" (extract_wisdom etc.) plus a YouTube transcript helper. | **Borrow the patterns, skip the tool.** The extract-insights prompt is a good template for our own note format. |
| 8 | [jkawamoto/mcp-youtube-transcript](https://github.com/jkawamoto/mcp-youtube-transcript) | 496 | 2026-11-09 | MIT | MCP server that gives Claude a "get transcript" tool. | **Optional.** Convenient, but a 30-line script with #1 does the same and caches to disk. Alternative: [kimtaeyoon83/mcp-server-youtube-transcript](https://github.com/kimtaeyoon83/mcp-server-youtube-transcript) (603 stars, MIT, last push 2026-07). |
| 9 | [NotJoeMartinez/yt-fts](https://github.com/NotJoeMartinez/yt-fts) | 1.8k | 2026-01-22 | Unlicense | Pulls all subtitles of a channel into SQLite and full-text searches them. | **USE later** if we want "search everything the Roblox Creators channel ever said about retention". Slower maintenance. |
| 10 | [rmusser01/tldw_server](https://github.com/rmusser01/tldw_server) | 1.5k | 2026-11-10 | **Unclear (GitHub reports no standard licence; check before any use)** | Full "too long, didn't watch" research server: ingest, transcribe, search, chat. | **Skip.** Too big for our need, licence unclear. |

Also checked, not in the top 10: `openai/whisper` (112k, MIT; slower than #3), `ggml-org/whisper.cpp` (55k, MIT; good without Python), `Purfview/whisper-standalone-win` (3.2k, **no licence file**, last push 2025-11; handy .exe but licence unclear), `byjlw/video-analyzer` (1.6k, Apache-2.0; frames + LLM, quiet since 2026-04), `tubearchivist` (GPL-3.0, a media server, wrong tool), `pytube` (stale since 2024). No repo in the top 10 has a non-commercial clause; the two licence warnings are #10 and the Purfview build.

### Recommended 3-tool pipeline

1. **Find and list: `yt-dlp`** (metadata only). `ytsearch10:<topic>`, a channel or a playlist URL in flat mode gives id, title, channel, views, length; a full metadata call adds upload date and chapters.
2. **Get text: `youtube-transcript-api`**, cached as one text file per video id with a timestamp every few minutes. **Fallback only when there are no captions:** `yt-dlp` audio-only into the scratchpad, then `faster-whisper` on the GPU (ask first, low priority, delete the audio after).
3. **Read and extract: Claude Code** reads the cached text and writes notes in a fixed format (source, year, how studied, techniques, "apply to Be Dino"). Add `PySceneDetect` only when a talk's slides carry the content.

Working scripts from this session (search, metadata, fetch, compact) are in the session scratchpad, not in the repo. If the owner wants this as a reusable tool, it is a small backlog item (one script in `tools/`, output into an ignored folder).

---

## Part B: Videos studied

Format: title, channel, year, how studied, then techniques with one Be Dino idea each. "T" = full transcript read.

### Roblox: official talks

**B1. The Retention Playbook: Turning Players into Fans (RDC 2025)** — Roblox, 2025, T. <https://www.youtube.com/watch?v=YgyfcMfxQcI>
Panel: developers of Jailbreak, Bee Swarm Simulator, Evade, Gunfight Arena.
- Prove the core loop is fun before any retention system; doubling the retention of a game that is not fun still gives nothing. *Be Dino: put 5 to 10 real children in front of "eat, grow, hatch" before building more of the 480 tasks.*
- Pace content: ship two items a week for ten weeks, not ten at once; players do not feel the difference. *Be Dino: hold back finished species/patterns and release them as weekly drops.*
- Release slightly unfinished and keep things for updates; hang quiet weeks on real-world holidays. *Be Dino: plan the first six updates before launch, holiday eggs included.*
- Keep the first minutes the same for years and add depth behind gates; when a new feature must reach beginners, make its first item as strong as the starter one but more fun. *Be Dino: fusion, genetics, potions and nests stay hidden or locked until the first hatch is done.*
- Watch new players (YouTube videos, young relatives), not the loudest Discord voices; own testers go blind to the first-time experience. *Be Dino: record first sessions; the lead agent cannot be the tester.*
- "First 48 hours" after each update: someone watches for abuse and bugs. *Be Dino: release on days the owner can watch.*

**B2. Creating an Intriguing First Time User Experience (RDC 2022)** — Onett (Bee Swarm Simulator), 2022, T. <https://www.youtube.com/watch?v=TZ14iO23Bpk> (older than 2023, kept because it is the most cited Roblox onboarding talk, 400k views)
- Three jobs of the first session: make them stay, let them teach themselves, give a reason to return.
- Familiar theme plus one clear twist; the icon should be crowded with cute characters. *Be Dino: "be a dinosaur" is the familiar part, "hatch what you caught" is the twist; the icon shows many colourful dinos and an egg.*
- Spawn players where veterans return, so beginners see what they can become within seconds. *Be Dino: spawn next to the hatch/nest area where big Gold/Diamond dinos stand around.*
- Sightlines: gates, machines and characters visible from spawn, with a requirement shown but not explained. *Be Dino: a locked fusion machine and a locked second zone visible from spawn ("needs 15 of the same").*
- No lecture tutorial: one arrow, a safe starting area where no permanent mistake is possible, a first enemy that is not scary, and small rewards hidden to pull players around. *Be Dino: arrow to first food, first predator slow and weak, crystals placed to lead the child across the map.*
- Run the core loop many times in the first session with a steep early curve. *Be Dino: first run short; first egg in about a minute (PROPOSAL, needs owner balance decision).*
- Return hooks: timed random rewards (a boss every 30 minutes, a mini-game every 2 hours), quest lines longer than one session, and repeatable score challenges that scale forever. *Be Dino: nests on a timer already fit; add a "best run" record per species.*
- Show late-game items early at absurd prices to widen the "space of possibility". *Be Dino: Index shows silhouettes of Legendary and Diamond dinos from minute one.*
- The loop must change in kind over time, not only in numbers. *Be Dino: small dino hides and eats; big dino hunts; later runs are about targeting rare eggs.*

**B3. How Home Recommendations & Ads Actually Work** — Roblox Creators, Oct 2025, T. <https://www.youtube.com/watch?v=tUz_OekIIiU>
- Two stages: retrieval (any play source counts, threshold is very low) and ranking (only players who came from "Recommended for You" count).
- Signals named in the talk: qualified play-through rate, 7-day playtime, play days, Robux spent, spend days, intentional co-play days. *Be Dino: design for all of them, especially play days and co-play, which a run-based game can miss.*
- Ad traffic and social-media traffic do not count for ranking and do not hurt it; ads only add players on top. *Be Dino: a small ad test at launch is safe for the algorithm; judge it by retention of those players.*
- Read retention by acquisition source; a drop is often a traffic-mix change. *Be Dino: never judge an update on blended D1.*
- Impressions can fall with flat numbers because of season (school) and competitors. Games are never "quarantined".
- When the algorithm widens the audience, numbers dip; niche games are served to their niche. Product managers said some of 2025's biggest games spent under 100 dollars on ads.
- Ads now have four goals (plays, new users, retention 0 to 30 days, re-activation) and up to ten custom thumbnails per campaign. *Be Dino: later, a "come back, new eggs" thumbnail set for lapsed players.*

**B4. LiveOps Essentials** — Roblox Creators, 2023, T. <https://www.youtube.com/watch?v=kNE757v3Bwg>
- Five kinds of post-launch work: regular content drops, big expansions (every 4 to 6 months), live events, quality-of-life, bug fixes.
- Content drops must reuse existing systems; never build a new system for a weekly drop. *Be Dino: species, patterns, auras, trails, egg types and nest contents are our "pipes"; make adding one a data change.*
- Put updates inside the world, not in a side window. *Be Dino: a new egg type appears as a physical nest on the map.*
- Time limits create urgency; seasonal themes should work worldwide (spring eggs, not a national holiday).
- Themed drops ("polar pets"), not random mixes. *Be Dino: "Ice Age week", "Volcano week".*
- Release just before the weekend peak (Friday), update the icon/thumbnail with an "update" marker, tell the community, then measure.
- Expansion types that last: social systems (trading, groups), competition (leaderboards), collections and goals for tomorrow / next week / six months, live events.

**B5. What are retention metrics on Roblox?** — Roblox Creators, 2023, T. <https://www.youtube.com/watch?v=LpAU6TheAZ4>
- Diagnostic rule: low D1 = onboarding and core-loop introduction; low D7 = progression; low D30 = no end-game or repeatable loop. *Be Dino: map each backlog item to D1, D7 or D30 so we know which number it is meant to move.*
- Show a glimpse of later progression during the first session. *Be Dino: one big dino NPC walks past in the first minute.*
- For D7 to D30, look for what players did just before leaving. *Be Dino: log last action before quit (died? egg queue full? hatch screen?).*

### Roblox: creators and analysts

**B6. Here's Why Roblox Games Blow Up** — AlvinBlox, 2025, T. <https://www.youtube.com/watch?v=Y93DRfB-Deo>
- The idea must be explainable in one sentence and playable with no tutorial; test: would it work with the text in a language you cannot read? *Be Dino: "Eat, grow, hatch the eggs you caught." Play one session with all text hidden.*
- Fun must be immediate: every interaction gives feedback within the first seconds. *Be Dino: first bite has a crunch, a pop and a number.*
- Broad appeal (kids, parents, short sessions on a bus). *Be Dino: a run a parent and child can do together.*
- He recommends fear-of-missing-out and calls these "dark patterns" himself. *Be Dino: do NOT copy as stated; see the kid-safe version in C6.*
- Early data: small ad spend over 2 to 4 weeks, or friends and dev communities.

**B7. How to ACTUALLY get Players in your Roblox Game in 2026** — DitchyDevelopments, 2026, T. <https://www.youtube.com/watch?v=cfLbW2j2VLs>
- Ads on a weak game: he peaked near 20 players and fell to zero within the hour. *Be Dino: no ad money before retention is measured.*
- Daily devlog shorts with a personal challenge story, viewers name things and suggest features; by launch there is a tester community (his claim: 40k visits with no ads). *Be Dino: owner already makes videos; a "building a dino game" shorts series fits. Owner decision.*
- Small reviewers and dev Discords beat cold-messaging big YouTubers.

**B8. How to ACTUALLY Make High CTR Roblox Thumbnails** — CallMeDogey, 2026, T. <https://www.youtube.com/watch?v=SjjPGduApZU>
- Click rate decays within a week (his lost 0.8 points); thumbnails need regular replacement. About 3% was his best (claim).
- Start from a reference thumbnail of a well-performing game in the genre; split panels showing tiers of the same thing (small to huge) are a common winning layout. *Be Dino: a three-panel "tiny Compy, big raptor, glowing Diamond dino" layout. Art rule applies: Blender render or owner/ChatGPT asset, never code-drawn; register in docs/77.*
- Note: half the video is a sponsor segment for an AI thumbnail tool; ignored.

**B9. Roblox Game Monetization Explained Like You're 5** — Tizzy RBLX, 2026, T. <https://www.youtube.com/watch?v=zoz3PSMqets>
- Look at the best-selling product and add bigger sizes of the same thing.
- Best sellers remove a pain players already complain about; read the feedback tab and watch real play first.
- Consumable developer products (bought again) raise "spend days", a ranking signal; one-off passes do not.
- "Purchase pathways": the same product reachable from the shop button, a plus sign next to the currency, a pad in the world on the main walking route, and an offer at the moment of need (e.g. "double it?" when collecting). He opens the shop only on the third failed purchase and caps it per session.
- After each monetization change check D1, D7, playtime and first-session numbers, not only revenue; do not sell things that break the economy (he refused auto-collect).
- *Be Dino: later, non-random conveniences at the moment of need (a sixth nest slot when the sixth nest is blocked, faster nest, crystal pack via a plus sign next to the crystal count). Must stay behind closed release flags until tested; anything random needs odds (see W1).*

**B10. My Roblox Game Makes $12,535/mo (3K CCU)** — MoseyTube77, 2026, T. <https://www.youtube.com/watch?v=a170E9klbP4> (revenue is his claim; the video also sells his course)
- One simple loop with about five light systems on top: a collection, a daily rotating shop, limited skins, four separate return rewards (daily, playtime, group, VIP daily), a streak.
- One "clippable" mechanic that creates funny player-to-player moments for YouTubers. *Be Dino: big dino chasing small ones, a giant hatch reveal; build a moment worth clipping.*
- Paying to restore a broken streak. *Be Dino: do not sell this to children; give a free "streak freeze" instead.*
- Hire help only for the one bottleneck (he bought UI polish).

**B11. Before You Make Your Roblox Game, Study THIS First** — SmartyRBX, 2025, T. <https://www.youtube.com/watch?v=N2FND74tgGE>
- Five drives: progression (every action moves something), status (things to show off), urgency, mastery (something to figure out), community (single-player designs usually fail on Roblox).
- Study method: stand in top games and watch what players do; read comments for their words; write down trigger, action, reward for each loop. *Be Dino: do this for two or three animal/collection games before launch and file it under docs/research.*

**B12. The Rise And Fall Of Grow A Garden** — Coael, 2025, T. <https://www.youtube.com/watch?v=1BX1tLoM-oI> (commentary, one creator's analysis; player numbers are his)
- Growth engine: a shop that restocks every few minutes with rare stock, plus a big update and a live "admin" event every Saturday at a fixed time.
- Why it faded (his view): weekly updates became item-only with no new play; rare items required constant checking so casual players capped out; the event hour moved and children woke early for nothing; other players could pay a little Robux to steal your rare plant; school started.
- *Be Dino: a fixed weekend event hour that never moves; every third or fourth update adds a new verb, not only new species; never let one player pay to take another child's dino; rare things must also be reachable by slow steady play.*

**B13. Inside RDC 2025: How Roblox Is Courting Pro Developers** — Deconstructor of Fun, 2025, **partial (first 12 of 56 min)**. <https://www.youtube.com/watch?v=8pruyZlxMI4>
- RDC 2025 raised the developer exchange rate by 8.5%; creator payouts passed 1 billion dollars a year (their figures).
- Guests believe the 2025 mega-hits are played by many parents together with their children. *Be Dino: supports a parent-and-child friendly run and a visible "play with a friend" bonus.*
- Low value for design; not read further.

### Game design and "what makes it fun"

**B14. Juice it or lose it** — Martin Jonasson and Petri Purho, 2012, T. <https://www.youtube.com/watch?v=Fy0aCDmgnxg> (old, still the reference; 618k views)
- Maximum output for minimum input. Order of cheapest wins: sound first, then easing on appear/scale, squash and stretch on impact, a white flash on hit, particles, a small screen shake, and eyes that look at the action.
- Add a small random delay when many things appear so they cascade.
- *Be Dino: one pass on exactly three moments (bite, grow-up, egg crack) with sound + scale pop + particles + tiny shake; eggs get eyes that follow the camera. Effect textures must be Blender renders (art rule).*

**B15. How to Keep Players Engaged (Without Being Evil)** — Game Maker's Toolkit, 2018, T. <https://www.youtube.com/watch?v=hbzGO_Qonu0>
- Alternate calm and intense moments; long max-intensity stretches tire players. *Be Dino: a run (tense) is followed by the hatch (calm, joyful), then the Index (calm).*
- Tease content before giving it; anticipation stretches each new thing. *Be Dino: locked areas, silhouettes, "next egg is glowing".*
- Long-term dream plus short milestones plus planning plus growing power plus automation later. *Be Dino: "complete the Index" as the dream, zone pages as milestones.*
- Short failed runs are fine if the next run is different and the player feels better. *Be Dino: dying still pays out the eggs caught so far (check against owner target before promising).*

**B16. This Psychological Trick Makes Rewards Backfire** — Game Maker's Toolkit, 2020, T. <https://www.youtube.com/watch?v=1ypOUn6rThM>
- Step-by-step quest lists make players do only the list, avoid risk, and stop when the list ends (Don't Starve prototype). A UI hint did the teaching better than quests.
- Expected rewards for an activity that is already fun reduce interest (the children's drawing study); unexpected, small, performance-linked rewards do not.
- Prefer big open goals, personal bests and comparisons over fixed thresholds; make goals optional.
- *Be Dino: keep the tutorial to highlights and arrows, not a ten-step checklist; hide small surprise rewards in the world; show "your best run" and "your friend's best" instead of only "collect 10".*

**B17. Progression Systems: How Good Games Avoid Skinner Boxes** — Extra Credits, 2015, T. <https://www.youtube.com/watch?v=S5camMoNw-o>
- A progression system should add long-term planning, unlock complexity step by step at the player's own speed, and reward the most interesting play.
- If the fastest way to progress is the dullest, players will do the dull thing. *Be Dino: check that standing still next to a food spawner is never the best egg rate; risky hunting should pay more.*
- Let players undo strategic choices cheaply. *Be Dino: fusion is irreversible, so the itemised warning in docs/46 matters; auras/trails stay switchable.*

**B18. The Loot Box Question: Designing Ethical Lootboxes I** — Extra Credits, 2018, T. <https://www.youtube.com/watch?v=-Uha5c7hJdA>
- Random boxes resemble blind boxes more than casino play because there is no cash-out, but the research was thin (2018 view).
- The overspending found in research came from social pressure and fear of losing status, more than from the random draw itself.
- Never target children; greedy designs lose money in the end (Battlefront II).
- *Be Dino: run eggs are earned by play, which is the safe shape. Never tie paid randomness to status against other children, never to a group obligation.*

**B19. What Makes A Good Luck Mechanic?** — Design Doc, 2024, T. <https://www.youtube.com/watch?v=4cmGSMDOrfc>
- People read 90% as "certain"; Fire Emblem quietly averages two rolls so displayed odds feel fair. *Be Dino: do not show children raw percentages on the hatch screen; if Cracked eggs fail often (owner target implies about 40% failed eggs at tier 0), expect it to feel far worse than the number. Flag to owner as a feel risk, with data once we have testers. Any shown odds must still be the true odds (W1).*
- Too many lucky bonuses make luck boring (Crisis Core). *Be Dino: Shiny/BIG stay rare; do not make every fifth egg "special".*
- Let players nudge luck with a choice (Mario Party items, Balatro deck). *Be Dino: the potion shop already does this; a "choose which zone to hunt for which egg type" choice would too.*
- Make failure give something (Disco Elysium). *Be Dino: a failed Cracked egg gives a small consolation (shell bits toward a guaranteed egg). PROPOSAL; it changes the economy, owner decision.*
- Duplicates that level something up turn bad luck into progress. *Be Dino: fusion already does this; show "7 of 15 for Gold" on every duplicate reveal.*

**B20. Idle Games: The Mechanics and Monetization of Self-Playing Games (GDC 2015)** — Anthony Pecorella (Kongregate), uploaded 2017, **partial (about 36 of 55 min)**. <https://www.youtube.com/watch?v=Lu-RjxeDpU8>
- Offline progress turns every return into a celebration ("welcome back, you earned..."), and these games out-retained Kongregate's other top earners without daily rewards or forced appointments.
- The longer away, the bigger the gift, so absence is not punished; steep growth keeps linear offline gains from breaking balance.
- Make the cost curve bumpy on purpose; a smooth curve is boring.
- Prestige (reset for a permanent boost) converts huge numbers back into a slow second currency and gives the best rush.
- Many small unlocks and achievements as "moments of joy"; rapid small updates matched every hit.
- Sells well without anger: time skips, permanent multipliers, opt-in boosts. Sells badly long-term: paying to avoid a punishment.
- *Be Dino: nests on a timer are our offline progress; open the session with a "your nest is ready" celebration. Never add a "pay or lose your dino" mechanic. Fusion tiers are our prestige; show the rush (big reveal, permanent stat up).*

### UI / UX

**B21. Bridging the Gap Between UX Principles and Game Design (GDC)** — Jim Brown (Epic), uploaded 2020, T. <https://www.youtube.com/watch?v=73Pqsk74Jc0>
- Players see groups, not single things; the one thing that matters must differ in colour and shape and stand apart. *Be Dino: predators share one silhouette family and colour; food another.*
- A consistent shape language: round = safe, blocky = solid, spiky = danger; and never let it lie (all cover in Gears is the same height). *Be Dino: every edible thing is round and bright, every danger is spiky and red, with no exceptions.*
- Negative space and contrast pull the eye to the goal.
- "Think in 4D": design a system by how it feels over time, not by its spreadsheet.
- Hidden help for beginners: the last sliver of health is tougher, the last bullets hit harder, so new players get close escapes. *Be Dino: a brand-new small dino gets a hidden grace (predators slightly slower for the first run or two). PROPOSAL.*
- Break long goals into visible short steps with the next reward shown.

**B22. Designing Text UX for Effortless Reading (GDC)** — Joseph Humfrey (inkle), uploaded 2020, T. <https://www.youtube.com/watch?v=x4G8UNiE560>
- A wall of text is skipped even if it is pretty. Show the title first, then one short chunk at a time.
- Readability comes from familiar fonts; decorative fonts are for props, not for reading.
- Phone and TV need the same chunky text size; design the phone layout first.
- 5 to 15 words per line; put text next to the thing it is about; brighten the current line and dim the old.
- Let the player choose to open text (a button) so reading feels like a reward.
- Delay buttons by under a second so the message is read first; overlap lines so nothing waits.
- Test by watching for tiny moments of boredom.
- *Be Dino: matches docs/72. One idea per screen, short words, text beside the object, "Hatch!" button appears a beat after the egg name.*

### Written sources that add something

- **W1. Roblox Creator Hub: paid random items policy.** <https://create.roblox.com/docs/production/monetization/randomized-virtual-items-policy> Anything random bought with Robux, or with a currency that can be bought with Robux, counts, including hatching, combining/fusing and luck boosts. Every outcome with true numeric odds totalling 100% must be shown before the purchase (a bare "i" icon is not enough), odds must update when a boost is active, and `PolicyService` must be checked per player with a fallback for restricted players. Rewards earned by play with no Robux link need no disclosure. *Be Dino: this is the line between run eggs (earned) and anything involving purchasable crystals, potions that change odds, or fusion with Robux-linked inputs. Already noted in AGENTS.md; keep paid flags closed.*
- **W2. Roblox Creator Hub: Discovery.** <https://create.roblox.com/docs/discovery> Current Home signals in priority order: play-through rate; first-play bounce (under 60 s and 61 to 180 s); play days (day 1, days 2 to 7, days 8 to 28); playtime per user (capped at 60 minutes a day); intentional co-play days; qualified sessions; spend days; Robux spent. A game with only the default thumbnail gets no Home impressions; titles that lead with money rewards and look-alike names/images get less exposure.
- **W3. Roblox newsroom, June 2026: discovery now uses a 28-day view.** <https://about.roblox.com/newsroom/2026/06/optimizing-discovery-great-games-reach-millions-players-roblox> Roblox says over-weighting short-term signals let eye-catching thumbnails crowd out games that keep players, so ranking now measures day 1, days 2 to 7 and days 8 to 28 directly.
- **W4. GameAnalytics 2025 Roblox benchmark report** (via a secondary write-up, **not verified at source**): <https://www.gameanalytics.com/reports/2025-roblox-report> Median D1 about 10%, D7 about 1.6%, D30 about 0.5%; top 1% about 22% / 9% / 4.7%; casual players leave in under 2 minutes, core players average about 37 minutes a session. Other blogs quote far higher "top 100" numbers with no method; ignore them.
- **W5. Roblox Creator Hub: Retention analytics.** <https://create.roblox.com/docs/production/analytics/retention> D1/D7/D30 definitions and retention split by acquisition source.

---

## Part C: Synthesis

Each row: technique, evidence, Be Dino application, effort (S = days, M = 1 to 2 weeks, L = more), risk. Ranked by expected impact inside each group. All applications are PROPOSALS.

### C1. Core loop and fun

| # | Technique | Evidence | Be Dino application | Effort | Risk |
|---|---|---|---|---|---|
| 1 | Prove the loop is fun with real new players before adding systems | B1, B7 | Playtest "eat, grow, die or finish, hatch" with 5 to 10 children, screen recorded, before more backlog | S | Low; main risk is not doing it |
| 2 | Juice the three key moments | B14, B6 | Bite, grow-up, egg crack: sound, pop, particles, tiny shake, eyes on eggs | M | Art rule: Blender effects only; too much shake hurts on phones |
| 3 | Calm/intense rhythm and a loop that changes in kind | B15, B2 | Tense run, joyful hatch, calm Index; small dino hides, big dino hunts | M | Hatch of 40 to 400 eggs at 5 s each can turn calm into waiting (see C4) |
| 4 | Make the interesting play the efficient play | B17 | Check egg rate per minute for "camp a food spot" vs "hunt"; hunting must win | S | Balance values are provisional; needs owner sign-off |
| 5 | Failure still gives something; duplicates feel like progress | B19, B15 | "7 of 15 for Gold" on every duplicate; consolation for failed Cracked egg | S / M | Consolation changes the economy: owner decision |

### C2. First-time experience (first 60 s / 5 min)

| # | Technique | Evidence | Be Dino application | Effort | Risk |
|---|---|---|---|---|---|
| 1 | Playing within seconds, no lecture; one arrow, visual language | B2, B6, B16 | Spawn, arrow to food, first bite inside 10 s. Test with all text hidden | M | Low |
| 2 | First payoff inside the bounce window (under 60 s and under 180 s are ranking signals) | W2, B3 | First run ends with a first egg hatched within about 2 to 3 minutes | M | Needs a special short first run; economy exception must be owner-approved |
| 3 | Show what you can become at spawn; visible locked things | B2, B5, B15 | Spawn beside nests and veterans; locked fusion machine and zone gate in view; Index silhouettes | M | Clutter; keep to two or three teasers |
| 4 | Safe start and hidden beginner help | B2, B21 | No permanent mistakes in run 1; first predator slow; hidden grace period | S | Must not be visible or exploitable |
| 5 | Hide depth behind gates | B1, B17 | Genetics, conditions, potions, fusion, nests appear one at a time after first hatch | M | Players may miss features: add a soft hint, not a checklist |

### C3. Retention (D1 / D7 / D30)

| # | Technique | Evidence | Be Dino application | Effort | Risk |
|---|---|---|---|---|---|
| 1 | Return = celebration, not punishment | B20, B2 | Nest timer finishes while away; session opens with "Your nest hatched!" | S | Low; fits existing nests |
| 2 | Goals for tomorrow, next week, six months | B4, B5, B15 | Tomorrow: nest + daily egg. Week: finish a zone page of the Index. Months: Diamond of a favourite species | M | Index must show "what is next" in child-readable form |
| 3 | Co-play (a ranking signal and the stickiest hook) | B3, W2, B4, B11, B13 | Friend-in-server bonus egg, "hatch together" viewing, later trading | M / L | Trading needs `IsPaidItemTradingAllowed` checks and scam protection; start with co-play bonus only |
| 4 | Play days via gentle daily reasons | W2, B10, B16 | Daily free egg plus a soft streak with free "freeze"; never sell streak repair | S | Expected rewards can dull intrinsic fun; keep them small and add surprises |
| 5 | Repeatable personal-best challenge | B2, B16 | "Biggest dino", "most eggs in one run" per species, compared with friends | M | Leaderboard cheaters: server-authoritative only |

### C4. Session design

| # | Technique | Evidence | Be Dino application | Effort | Risk |
|---|---|---|---|---|---|
| 1 | Short loop repeated many times in session one, steep early curve | B2, B20 | First three runs short and generous, then normal pacing | M | Economy exception; owner decision |
| 2 | Respect the 60-minute daily playtime cap in ranking; aim for more days, not marathons | W2 | Natural stopping point after hatch + nest set: "Come back when your nest is ready" | S | None |
| 3 | Hatch reveal pacing | B22, B14, B19 | **Question for owner:** 400 eggs at 5 s is about 33 minutes of reveals. Proposal: commons cascade fast with overlap, the reveal slows only for rare tiers; still one egg at a time and in rising rarity | M | Touches an owner-approved rule (one at a time, about five seconds); needs an explicit decision, not a silent change |
| 4 | Bumpy cost curve | B20 | Alternate cheap and expensive steps in aura/trail/potion prices | S | Provisional balance |
| 5 | Unexpected small rewards | B16, B2 | Hidden crystals and one random event per run (meteor shower of food) | M | Keep rare (B19) |

### C5. UI / UX for children on phones

| # | Technique | Evidence | Be Dino application | Effort | Risk |
|---|---|---|---|---|---|
| 1 | One idea per screen, title first, text beside the thing | B22, docs/72 | Audit hatch, Index, shop, fusion screens for walls of text | S | Low |
| 2 | Consistent shape/colour language that never lies | B21 | Round bright = eat; spiky red = danger; gold glow = rare. One sheet in the UI standards | S | Existing art may need repainting |
| 3 | Phone first, chunky text, 5 to 15 words a line | B22 | Design at phone size, check on a real phone before PC | S | Studio/phone evidence required before claiming done |
| 4 | "No reading" test | B6 | Play a full session with labels hidden or in another language | S | None |
| 5 | Delay buttons a beat; brighten current, dim old | B22 | "Hatch!" / "Next" appears after the name is shown | S | Too long a delay annoys; keep under a second |

### C6. Monetization: kid-safe and policy compliant

| # | Technique | Evidence | Be Dino application | Effort | Risk |
|---|---|---|---|---|---|
| 1 | Keep earned randomness and paid randomness strictly apart | W1, B18 | Run eggs stay play-only. Anything where Robux or purchasable crystals touch hatching, luck or fusion needs full odds disclosure and `PolicyService` fallback before any flag opens | M | Policy breach if crystals become purchasable and also buy luck potions without disclosure |
| 2 | Sell non-random convenience that removes a real pain, at the moment of need | B9, B20 | Sixth nest slot when a nest is blocked; faster nest; bigger egg bag | M | Paid release flags stay closed until tested (AGENTS.md); never frame as avoiding a loss |
| 3 | Do not sell punishment relief, streak repair or protection from other players | B20, B12, B10 | Standing rule for the shop spec | S | None |
| 4 | Instance-bound cosmetics for status | B11, B9 | Auras/trails as planned; a few limited seasonal ones | M | Limited stock pressure on children: prefer time-limited over quantity-limited |
| 5 | Measure D1/D7/playtime after every shop change | B9 | Shop changes ship alone, with a before/after read | S | Needs analytics events first |

### C7. Discovery and growth on Roblox

| # | Technique | Evidence | Be Dino application | Effort | Risk |
|---|---|---|---|---|---|
| 1 | Design for the eight Home signals | W2, W3, B3 | Add a one-page "signal map": which feature feeds bounce, play days, co-play, qualified sessions | S | Signals change; re-check docs each quarter |
| 2 | Icon and thumbnail as a living asset | B8, B4, W2, B2 | Custom thumbnail before launch (required for Home), reference-based layout, refresh on each update | M | Art rule and asset registry; must show real gameplay, no look-alikes |
| 3 | Seed with a small trusted group; ads only after retention is known | B3, B6, B7 | Friends/family/dev-server playtest, then a small ad test read by acquisition source | S | Publishing and spend need owner OK |
| 4 | One-sentence pitch and name | B6, W2 | "Eat, grow, hatch the eggs you caught" on the page; title without reward bait | S | None |
| 5 | Devlog shorts and a clippable moment | B7, B10 | Owner's channel: build-in-public shorts; giant hatch reveal as the clip | M | Owner's time; owner decision |

### C8. LiveOps

| # | Technique | Evidence | Be Dino application | Effort | Risk |
|---|---|---|---|---|---|
| 1 | Content pipes: weekly drops through existing systems only | B4, B1 | Species, patterns, egg types, auras as data; a checklist for "add one species" | M | Art throughput (Blender) is the bottleneck |
| 2 | Bank content before launch and drip it | B1 | Hold 6 to 8 weeks of finished drops | S | Temptation to ship everything at once |
| 3 | Fixed weekend rhythm that never moves; update marker on the icon | B4, B12 | Friday release, one fixed event hour | S | A solo owner cannot be live every week: automate the event |
| 4 | Every few updates add a new verb, not just items | B12, B4, B1 | Planned expansions: fusion UI, trading, new zone, each 2 to 4 months apart | L | Scope |
| 5 | First-48-hours watch and measure every release | B1, B4 | Release only when someone can watch; rollback plan | S | None |

---

## Top 15 actions (ranked)

All are proposals for the backlog; none is approved. "Owner" marks where a decision is needed first.

1. **Run a real first-session playtest with 5 to 10 children before building more** (record screens; watch the first 3 minutes and the last action before quitting). S. Evidence: B1, B5.
2. **Rebuild the first 3 minutes: playing in 10 seconds, first egg hatched inside the bounce window**, no checklist tutorial. M. Owner: short first run is an economy exception. Evidence: B2, B6, W2.
3. **Decide the hatch reveal pacing for big batches** (400 eggs at five seconds is about 33 minutes). Owner decision; proposal is fast cascade for commons, slow reveal for rare tiers, still one at a time. Evidence: B22, B14.
4. **Juice pass on bite, grow-up and egg crack** (sound first). M. Evidence: B14.
5. **Add analytics events and a signal map** (bounce at 60/180 s, play days, co-play, last action before quit, retention by source). S to M. Evidence: B3, W2, W5.
6. **"Welcome back" celebration on nest completion** as the session opener. S. Evidence: B20.
7. **Co-play bonus** (extra egg or shared hatch viewing when playing with a friend). M. Evidence: W2, B3, B4.
8. **Three-horizon goals in the Index** (tomorrow / this week / long dream) with "7 of 15 for Gold" shown on duplicates. M. Evidence: B4, B15, B19.
9. **Spawn-area staging**: veterans, nests and two or three visible locked teasers at spawn. M. Evidence: B2.
10. **Paid-random compliance gate written down as a release checklist** (odds display, `PolicyService` fallback, which currencies are Robux-linked) and kept closed. S. Evidence: W1.
11. **Content pipeline + 6 to 8 weeks of banked drops, Friday rhythm.** M. Evidence: B4, B1, B12.
12. **Icon/thumbnail set made from references, with an update variant**, registered in docs/77. M. Evidence: B8, W2.
13. **Shape and colour language sheet + "no reading" test + phone-first check** added to docs/72 practice. S. Evidence: B21, B22, B6.
14. **Gentle daily egg and free streak freeze; written rule: never sell streak repair, punishment relief or protection from other players.** S. Evidence: B10, B16, B20, B12.
15. **Check that hunting beats camping for eggs per minute, and that Cracked-egg failure does not feel unfair** (consider a consolation). S to M. Owner: balance. Evidence: B17, B19.

---

## Sources

Videos: B1 to B22 URLs above. Written: W1 to W5 URLs above. Also consulted for context only: Roblox RDC 2025 newsroom post (<https://about.roblox.com/newsroom/2025/09/roblox-rdc-2025>), DevForum retention-by-source announcement (<https://devforum.roblox.com/t/analytics-view-retention-by-acquisition-source-and-select-your-benchmark-set/4010157>). Third-party blogs with unsourced retention numbers were not used.
