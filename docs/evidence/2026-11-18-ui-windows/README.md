# Standard menu window: Crystal Shop and Potion Shop (BD-1266, BD-1267, BD-1270), 2026-11-18

Built behind `StandardMenuEnabled` and `ShopFeaturedEnabled` (both off by default, on in the playtest profile). Spec: docs/244 s2.12 to s2.14.

| File | What |
| --- | --- |
| mock-crystal-shop.png, mock-potion-shop.png | The approved mockups (owner 2026-11-17) |
| compare-crystal-shop.jpg, compare-potion-shop.jpg | Mock next to the Studio capture |
| studio-crystal-featured.jpg | Featured tab: this week's pick, "5 days left" |
| studio-crystal-featured-new.jpg | Featured scrolled: "-- NEW --" with two offer cards |
| studio-crystal-auras.jpg | Auras tab: 3 item cards, rarity colours, green number, crystal price |
| studio-crystal-eggs.jpg | Eggs tab: offer cards (the random egg says Soon while PaidRandomGate blocks it, as on the old screen) |
| studio-potion-shop.jpg | Potion Shop: item cards, "New in 1 min" on the title bar |
| studio-potion-confirm.jpg | The in-window "Buy Swift Sip?" confirm (earlier build: the veil covered the X; fixed, it now starts under the title bar) |
| studio-potion-yours.jpg | Yours tab after a real buy (the server answered "Done!") |

## Measured in Studio (playtest build, my own test window on the virtual monitor)

Viewport 1274 x 423 px (Studio play, NOT the device emulator and NOT a phone: the Studio MCP cannot switch the emulator; the canvas is as short as a phone, wider).

| Piece | Spec | Measured |
| --- | --- | --- |
| Crystal Shop window | 58 % w x 67 % h | 58.0 % w x 66.9 % h |
| Potion Shop window | 43 % w x 56 % h | 43.0 % w x 56.0 % h |
| Title bar | 10 % h | 9.9 % h |
| Red X | 8 % h | 10.4 % h (raised to the 44 px touch floor on a 423 px canvas) |
| Side tab | icon 9.5 % h, 44 px target | icon 10.4 % h while active (1.1 bounce), tab 66 x 56 px, left edge 8 px right of the window |
| Blur | Size 12 while open | 12 open, 0 after close (also 0 when Bootstrap's window takes over) |

Flow checked in Studio: open Crystal Shop and Potion Shop, switch tabs, Chances closes the standard window and opens Bootstrap's chances page, opening a shop while Bootstrap's window is open closes it first, buy a potion (Done!), see it on Yours.

## Not checked / known gaps
- No phone or device-emulator capture yet (owner phone check open).
- On this short canvas the item renders are small (the card is about 40 % h; name, rarity, strip and a 44 px button take most of it).
- The HUD in the pictures is today's HUD; the HUD rebuild (sibling session) moves the right column the side tabs sit next to.
- The Luck tab (level 3) and an equipped aura were not captured.
