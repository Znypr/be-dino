# Menu screenshots, 2026-10-16 (main at a36b0f7)

Captured in Roblox Studio (Play, Client) from the playtest profile build (`python tools/build.py --profile playtest`), desktop-size viewport 1009x645, real buttons clicked through the Studio mouse tool. Studio preview: progress not saved, 1,000,000 test crystals. Phone sizes were NOT captured; this is desktop only.

| Image | What it shows |
| --- | --- |
| 01-settings-sound.jpg | Settings, Sound tab |
| 02-settings-look.jpg | Settings, Look tab |
| 03-settings-controls.jpg | Settings, Controls tab |
| 04-settings-help.jpg | Settings, Help tab (How to play, Food guide, Auto-open) |
| 05-shop-auras-cards.jpg | Crystal Shops, Auras cards (extra, shared card style) |
| 06-shop-eggs-odds-details-button.jpg | Eggs tab with the ODDS / DETAILS button |
| 07-egg-odds-panel.jpg | Egg Odds panel for the Random Egg (top) |
| 08-egg-odds-panel-scrolled.jpg | Egg Odds panel scrolled (species list) |
| 09-buy-egg-confirm.jpg | Buy Random Egg? confirm (reached by BACK from the odds panel) |
| 10-shop-conditions.jpg | Conditions tab (five condition eggs and percents) |
| 11-upgrade-conditions-confirm.jpg | Upgrade Conditions? confirm |
| 12-upgrade-odds-panel.jpg | Upgrade Odds panel (from the confirm's ODDS / DETAILS) |
| 13-shop-crystals-cards.jpg | Crystals tab cards |
| 14-dino-index-collected-bar.jpg | Dino Index with "Collected 1 of 22 (4%)" bar and milestone ticks |
| 15-potion-shop-normal.jpg | Potion Shop, six offers |
| 16-potion-shop-sold-out.jpg | Potion Shop after buying Growth Sip: grey SOLD OUT card, "Done!" toast |

## Ratings (honest, 1 to 5)

- Settings Sound 4, Look 4, Controls 3, Help 3.
- Egg shop tab 3, Egg Odds panel 4, Buy egg confirm 3, Conditions tab 4, Upgrade confirm 3, Upgrade odds 4.
- Crystals tab 2, Dino Index 3, Potion Shop 4, Sold out card 4, Auras 4.

## Things that look wrong or off-vision

1. Dino Index bar: a milestone tick crosses the "1" in "Collected 1 of 22 (4%)" (14). Text must sit on a clear background (docs/72).
2. Odds disagree: Egg Odds says "Hatches a dino 60% / Cracked 40%" (07), the Buy Random Egg confirm says "Cracked: 20% hatch success" (09). Same egg, two numbers. Also "Cracked: 20% hatch success" is hard wording for children.
3. Crystals tab buttons show only "..." and a "Coming soon!" line (13): reads as broken, no price on any card, and the cards are cut off at the bottom of the scroll area.
4. Upgrade Conditions copy: "Unlocks at level 3. New eggs only." (11) and "Unlocks at level 3" under the upgrade button (10) are unclear (what unlocks? the player is level 1 and the button is active). The confirm shows a plain egg, not the condition being improved.
5. Toast "Done!" (16) sits on top of the modal title ("Potion Shop" is covered) and its icon box is an empty dark square.
6. Admin button (top left) overlaps the top-left corner of every modal (all images). Owner-only, but it hides the title edge area and collides in Studio test passes.
7. Help tab (04): large empty band between the two buttons and the Auto-open row; the Auto-open buttons use about 12 px two-line text ("Common SHOW") which is tiny for children (docs/72). Auto-open is also odd to find under Help.
8. Egg shop and confirm screens (06, 09, 11) show the same plain beige egg and a lot of empty space under the buttons.
9. Egg Odds scroll bar is a thin 6 px strip (07, 08): hard target on touch. Not tested on phone.
10. Sold-out card text is grey on grey (16): readable but low contrast; the "Sold out. Back later!" line is small.

Not checked: phone/touch layout, odds panels for non-Random eggs (only one egg exists), the shared Details panel on Aura or Trail cards.

Mouse note for testers: Studio's mouse tool clicks reliably by `instance_path`; button instances here have empty names and duplicate "Frame" parents, so rename them from an `execute_luau` call first. Raw x/y clicks did not register.
