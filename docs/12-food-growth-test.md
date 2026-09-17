# Build 004: food and growth

## Implemented prototype contracts
- Server creates at most 64 anchored orange berries on a fixed grid; occupied ground is excluded by an arena raycast.
- Every 0.1 seconds, a bounded loop checks living, initialized characters. No pickup requests or score values come from client remotes.
- Within 4 horizontal studs and less than 6 vertical studs, nearest eligible player wins; equal distances break by UserId. Arena geometry occludes pickup rays.
- A berry grants exactly 10 growth score once, disappears for everyone and becomes available again after 8 seconds. Claim and award contain no yield.
- Basic sampled displacement rejection is included; it is not complete anti-cheat and does not prevent all gradual speed exploits.
- Scale is min(4, sqrt(1 + score/50)); this is fast test tuning, not final balance. At 50 score size is about 1.41x; at 150, 2x; at 750, 4x. Score continues past the visual cap.
- Score belongs to the current character, resets on respawn, and is not saved. It is not catch score or collection loot.
- Test size pads are removed. Cosmetic collision still uses the previously tested fixed Humanoid collider.
- Six source scripts are packaged; five packaging tests pass. Roblox food behavior is not yet runtime-tested here.
- Bounded all-pairs search is sufficient for this 64-food prototype; spatial indexing is required before a larger load target if profiling calls for it.

## Tester checklist
Open the new .rbxlx, press F5. Then repeat the multiplayer cases with F7 and 2 clients.

| Test | Expected |
|---|---|
| Eat one berry | It disappears; only your score rises by 10; dinosaur grows slightly |
| Collect five | Score 50, size about 1.41x; camera usable |
| Return to a cleared spot | Berry returns about 8 seconds after pickup; collecting gives another 10 |
| Both clients approach one berry | One winner only: combined score increase is 10; berry disappears in both views |
| Watch other client collect | Other dinosaur grows; your own score and size stay unchanged |
| Reset after growing | Score 0, size 1x, dinosaur and controls still work |

When testing respawn timing, stand away from the spot so the returned berry is not immediately collected again. At large size, pickup is based on the center of the dinosaur's fixed collider, not the snout or tail.
Report test number, observed result and any red Output errors. Multiplayer score comparison requires both HUDs before and after the same pickup.

## Known scope limits
No combat, catch accrual, inventory, chest, save/load, final tuning or movement-security acceptance. BD-005 full durable-state design remains open. This isolated increment defines only temporary score and server pickup authority.

## Reference
[Roblox raycasting documentation](https://create.roblox.com/docs/workspace/raycasting) reviewed for ground and occlusion queries.
