# 246 Menus in the Steal an Egg frame (ChatGPT audit 2026-11-21)

Owner 2026-11-21: "fix the other menus as well and keep working on the queue items but make sure they are critiqued by chatgpt ensuring best quality and competitive with current famous roblox experiences."

**Input.** ChatGPT (strict art director) got three things:
- our menus as they are now (`docs/evidence/2026-11-17-menus-top-look/contact-sheet.jpg`, the MenusTopLook state after PR #630);
- our own phone research captures (local only, `be-dino-reference-shots/mobile-2026-11-17/phone/`): Steal an Egg shop featured, shop stars, index, eggs drawer, pets drawer and settings, plus the PS99, Grow a Garden and Steal a Brainrot shops.

We asked it to base every number on the research images. The owner's standard is Steal an Egg (docs/244: "clean, nice colours, easy to read, minimal").

**Verdict: menu system 5.7/10.** It approves the art direction (headers, outlines, colour families, icon style) but not the layouts as final phone UI. The colours are no longer the problem; the amount of interface competing for attention is.

## Measured gap

| | Steal an Egg | Be Dino! now |
| --- | --- | --- |
| Shop window | about 58 % W x 67 % H | 97-99 % W x 85-90 % H |
| Index window | about 49 % W | 97-99 % W |
| Settings window | about 34 % W | 97-99 % W |
| Section tabs | outside the window (icon rail) | inside the window |
| World around a menu | much visible, little or no dim | almost none |

Its main warning: **do not rebuild our menus at 60 % scale**. The text would fall under our 19 px phone floor. Steal an Egg's windows are small because they hold fewer, bigger things.

## Shared frame (targets at 720 p, % of the screen)

- **Three size presets, centred, top at about 21-22 % H:** shop 58 % W x 67 % H; index 50 % x 63 %; settings 36 % x 68 %. Workflow screens may be larger when it is justified (Fusion 62 x 68).
- **Header:** 9.5-10 % H, title 36-40 px heavy white with a 3 px black outline. Colours: shop green #59E947 (stripe highlight #A0FF85), index cyan #5CD6F5, settings silver-blue #C8D4E7, eggs / run complete / go home yellow #FFD963.
- **Body:** #2D3144 with a faint stud texture (studs 6-9 px, every 22-26 px, 4-6 % opacity). No dotted bottom strip. Padding 2.5-3 % H; outline 3 px; corners 5-7 px.
- **Close:** red #F44750 square, 52-58 px, white X, 3 px dark outline.
- **Tab rail outside the window:** starts 1-1.5 % W right of the window. Icons 7-8 % H, 1 % H apart. The active one gets a coloured tile; a label of 19-20 px only where it fits.
- **Cards:** at most three across a shop window, 12-15 px apart, art 95-115 px tall, a coloured or illustrated background (not a grey text box), corners 5-7 px, a 2-3 px border.
- **Buy button:** #66F52F with a darker lower edge, black outline, 46-52 px tall, crystal icon plus a whole-number price.
- **Rarity colours:** Common #858D9E, Uncommon #54D74A, Rare #39CBF5, Epic #A45BFF, Legendary #FFD13F, Secret #F457A9. Use only the tiers the game has.
- **Text:** item name 23-26 px, body 19-22 px (never under 19 on phones), price and button word 25-28 px.
- **Dim:** 0-8 % behind shops and collections, 12-18 % behind confirmations.

Our rules win over the audit: kid words only (it suggested "Grow faster!" / "Lasts 7 min" instead of "+40 %"), no Robux items, 19 px floor, and final icon art from the owner's pipeline.

## Per menu (score now, target size, ranked fixes)

1. **Dino Index, 4.5, 50 x 63.**
   - Four columns x two rows of cards 14-16 % H with a 9-11 % H render; found dinos in full colour.
   - One cyan title; Dinos / Patterns / Colours move to the outside rail.
   - A selected-dino panel of about 28 % of the window width; the progress bar 5 % H.
2. **Potion Shop, 5.3, 58 x 67.**
   - Three potions per page: cards 28-32 % H with the bottle 12-14 % H, on a strong rarity colour.
   - Kid words: "Grow faster!" and "Lasts 7 min". Buy button 6.5 % H.
   - "New in 3 min" as one 22 px line.
3. **Shop Landing, 5.8, 58 x 67.**
   - Auras, Trails, Eggs and Potions move to the outside rail.
   - The window shows one featured item or a row of three buyable items (art 14 % H, buy button 6.5 % H).
   - The crystal balance becomes a small pill by the header.
4. **Settings, 5.5, 36 x 68.**
   - A plain vertical list: rows 8-9 % H, sliders 7-9 px with a 20-24 px handle, on/off green #66F52F and red #F44750.
   - The big tabs become secondary. Silver header.
5. **Fusion, 5.2, 62 x 68.**
   - Six slots 3 x 2 (8-9 % H each); the result dino 14-17 % H on a gold card #FFD13F, shown as a preview.
   - One green button 7 % H ("Pick 4 more" / "FUSE!"). One line of text: "6 dinos make 1 gold dino!"
6. **Eggs, 5.7, 58 x 65.**
   - Three nests per row (11-13 % H), the selected egg 18-20 % H on its rarity colour.
   - One OPEN EGG button 7 % H right under it; auto-open as one separate setting.
7. **Auras, 6.6, 58 x 67.**
   - Keep three cards, art 14-16 % H on stronger rarity surfaces.
   - Benefits in words ("Small boost", "Big boost", "Huge boost"); tabs move to the rail.
8. **Run Complete, 5.9, 50 x 60.**
   - Three eggs at 12-14 % H together at the top, the crystal reward 9-11 % H.
   - A bright HATCH EGGS button 7 % H at the bottom; the toast never covers it.
9. **Home, 6.8, 52 x 62.**
   - The Compy 25-28 % H; Eggs / Nests / Level as three chips 6-7 % H.
   - EXPLORE 7 % H in #66F52F.
10. **Go home, 6.8, 42 x 46.**
    - Home art 18-20 % H; "Go home?" and "Your eggs are safe!".
    - CANCEL and GO HOME 7 % H, 24 px or more.

## How we build it (owner rule 2026-11-18: one small slice, owner OK before building more on it)

- **Slice 1 (BD-1287):**
  - The shared compact window and the outside rail, behind a new flag that is off by default and on in playtest.
  - The Shop landing rebuilt in it.
  - ChatGPT re-scores against the same research until 8+, then the owner sees Studio pictures.
- **Slice 2:** Potion Shop and Dino Index. **Slice 3:** Eggs, Settings, Fusion. **Slice 4:** Auras, Run Complete, Home, Go home.
- Every slice: `tools/ref_compare.py` plus a ChatGPT round with the matching research shot, our rules stated, 8+ before the owner sees it.
