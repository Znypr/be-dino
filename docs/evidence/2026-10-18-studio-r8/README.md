# Studio round 8 (2026-10-19): stall bubble, rail in a run, toasts, small windows, food vs colliders

Playtest build of `origin/main` `1f78c38b` (on screen: **BUILD redesign-020 1f78c38b**; `playtest_freshness.py`: up to date). Report: [docs/205](../../205-studio-round8-bubbles-rail-toasts.md). Copies of every picture are in `docs/evidence/review-2026-10-17/` with the same number and the prefix `-studio-r8-`.

Viewports measured with `workspace.CurrentCamera.ViewportSize`: **516 x 481** at the start (Studio maximised on the virtual monitor), **1156 x 841** for a stretch in the middle (the window was on a 1080p screen by itself), 296 x 472 once (not maximised on the virtual monitor, not used for pictures), then back to **516 x 481** after `monitor4.py place --maximize`.

Important: `screen_capture` does not draw BillboardGuis (same as docs/141, BD-289). The stall bubble pictures (421, 423 to 425, 430, 432) therefore show an **exact copy** of the live bubble (cloned from the real `HubPromptBubble`, same size, same text) placed in a temporary ScreenGui at the bubble's projected screen point and drawn UNDER the HUD (as a billboard would be). The real bubble's text, key and state were read from the game as numbers.

| # | Picture | Size | Verdict |
| --- | --- | --- | --- |
| 421 | nests-bubble-516-behind-rail-and-weather-plate | 516 | DEFECT: the bubble's name and line are under the rail, the key button is cut by the weather plate (BD-1128) |
| 422 | home-hud-516-six-buttons | 516 | PASS: all six rail buttons at home |
| 423 | potions-bubble-1156x841-build-stamp-visible | 1156 | PASS: "Potions / Fresh potions here! / E Open" fits; build stamp 1f78c38b visible |
| 424 | fuse-bubble-1156x841 | 1156 | PASS: "Fuse / Make a stronger dino!" |
| 425 | shop-bubble-1156x841 | 1156 | PASS: "Shop / Auras and trails!" |
| 426 | shop-opened-by-E-landing-1156x841-trails-1-yours | 1156 | PASS: one E opened the Crystal Shops; copy slip "1 yours" on the Trails tile (BD-1129) |
| 427 to 429 | shop auras, trails, eggs tabs | 1156 | PASS: every tab stays in the shop |
| 430 | dinos-bubble-1156x841 | 1156 | PASS: "Dinos / Meet all your dinos!" |
| 431 | dinos-index-opened-by-E-class-badge-small | 1156 | PASS: E opens the Dino Index; class badge is a small icon |
| 432 | heart-show-off-bubble-says-Open | 1156 | PASS for the look; copy slip: the button says "Open" for Show off (BD-1129) |
| 433 | run-active-rail-only-potions-settings-1156x841 | 1156 | PASS: in a run only Potions and Settings, no gap, no MENU chip |
| 434 | home-516-tell-us-and-admin-cover-explore-button | 516 | DEFECT: Tell us! and Admin cover Explore (BD-1130) |
| 435 | run-516-rail-two-buttons-in-a-row-home-button-covered-by-admin | 516 | PASS for the rail (two buttons in a row); DEFECT: HOME covered (BD-1130) |
| 436 | potion-shop-516-clean | 516 | PASS: hint lines under the second row |
| 437 | potion-bought-slim-done-toast-bottom-516-calm-on-sold-out-text-cut | 516 | PASS: one slim toast along the bottom, not over X, tabs or first row; small touch on the USE row, "Sold out. Back" cut (BD-1129) |
| 438 | settings-look-516-rows-crowded | 516 | DEFECT: tab row touches Effects, Calm motion touches Fast mode (BD-1132) |
| 439 | toast-follow-the-glow-no-menu-516-below-rail-clear | 516 | PASS: toast below the rail, clear |
| 440 | fusion-516-tabs-EMERAL-DIAMON-cut-admin-and-tell-us-over-menu | 516 | DEFECT: tab names still cut; Admin and Tell us! over the menu (BD-1131, BD-1130) |
| 441 | index-dinos-516-class-badge-tiny-tab-cut-left-empty-space | 516 | class badge present; layout leaves half the panel empty (BD-1132) |
| 442 | index-patterns-516-boost-n-of-5-list-clipped | 516 | PASS for "Boost N of 5" |
| 443 | goals-sheet-open-516-covers-settings-and-part-of-rail | 516 | DEFECT confirmed (BD-1108) |
| 444 | home-516-goals-plate-done-card-near-rail | 516 | info: Goals plate and a Done card sit under the Crystals plate |
| 445 | eggs-screen-516-egg-1-of-17-common-dirty | 516 | PASS: header clear of nests, OPEN EGG whole |
| 446 | run-complete-516-17-eggs-open-eggs-button | 516 | PASS: run card, +38 Crystals, +1 nest |
| 447 | home-516-weather-title-volcanic-bloom-over-rail-potions | 516 | DEFECT: weather title text drawn over the Potions button (BD-1132) |
| 448 | settings-help-auto-open-rarity-toggles-516 | 516 | PASS for the toggles; DEFECT: AUTO opens the last used tab, not Help (BD-1132) |
| 449 | reveal-516-dewdrop-mutation | 516 | DEFECT: "Skip stops here" chip over the ribbon, class chip over the name (BD-1107, BD-1097) |
| 450 | reveal-516-big-raptor | 516 | same stack on a BIG reveal |
| 451 | reveal-516-rainbow-egg-ribbon-cut-left-chips-overlap | 516 | DEFECT confirmed (BD-1107): ribbon cut at the left edge, chips overlap |
| 452 | hatching-516-rainbow-egg-16-of-17 | 516 | info: the egg before the reveal |
| 453 | auto-opened-summary-516 | 516 | PASS: "Auto-opened 14, 7 Common, 7 eggs did not hatch" |
| 454 | index-patterns-516-found-on-one-line-whole | 516 | PASS: "Found on Raptor", "Found on 2 dinos" on one line |
| 455 | index-dinos-516-class-badge-icon-only-dewdrop-chip-cut | 516 | DEFECT: DEWDROP chip cut, badge has no word (BD-1132) |
| 456 | my-dinos-details-516-class-icon-ok-boost-line-hidden-under-buttons | 516 | PASS: class icon with the word "Ground"; DEFECT: second Species line hidden under EQUIP and BACK (BD-1132) |
