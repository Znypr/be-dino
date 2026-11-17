# Standard menu window, first slice: the Crystal Shop (BD-1266, BD-1267), 2026-11-18

Built behind `StandardMenuEnabled` (off by default, on in the playtest profile). Spec: docs/244 s2.12 to s2.14. The owner said on 2026-11-18
"don't do too much at once": this slice is the frame plus the Crystal Shop only, for the owner to approve the look first. The Featured tab
(BD-1270) is built but its flag `ShopFeaturedEnabled` stays off in every profile; the Potion Shop, the Aura Shop look (mock 07) and the egg
picker (mock 08) come next on the same frame.

| File | What |
| --- | --- |
| mock-crystal-shop.png | The approved mockup (owner 2026-11-17) |
| compare-crystal-shop.jpg | Mock next to the Studio capture (review copy 607) |
| studio-crystal-auras.jpg | Auras tab: 3 item cards, rarity colours, green number, crystal price |
| studio-crystal-trails.jpg | Trails tab: the trail icons, "Level N" while locked |
| studio-crystal-eggs.jpg | Eggs tab: offer cards (the random egg says Soon while PaidRandomGate blocks it, as on the old screen) |

## Measured in Studio (playtest build, my own test window on the virtual monitor)

Viewport 1274 x 423 px (Studio play, NOT the device emulator and NOT a phone: the Studio MCP cannot switch the emulator; the canvas is as short as a phone, wider).

| Piece | Spec | Measured |
| --- | --- | --- |
| Crystal Shop window | 58 % w x 67 % h | 58.0 % w x 66.9 % h |
| Title bar | 10 % h | 9.9 % h |
| Red X | 8 % h | 10.4 % h (raised to the 44 px touch floor on a 423 px canvas) |
| Side tab | icon 9.5 % h, 44 px target | tab 66 x 56 px, left edge 8 px right of the window |
| Blur | Size 12 while open | 12 open, 0 after close (also 0 when Bootstrap's window takes over) |

Flow checked in Studio: open the Crystal Shop, switch tabs, Chances closes the window and opens Bootstrap's chances page, opening the shop while
Bootstrap's window is open closes that first. (A real buy through the in-window confirm was checked on the earlier Potion Shop build: the server
answered "Done!".)

## Not checked / known gaps
- No phone or device-emulator capture yet (owner phone check open).
- The side tabs sit over today's weather card; the HUD rebuild (sibling session) moves the right column.
- The Luck tab (level 3) and an equipped aura were not captured.
