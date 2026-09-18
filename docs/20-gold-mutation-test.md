# Build 010: Gold mutation test

Build 010 validates BD-014. Use a fresh private test experience because the three test setup buttons intentionally overwrite Compy base/Gold counts.

## Implemented

- Gold mutation costs exactly 50 base copies.
- Conversion is atomic in the same profile UpdateAsync: -50 base, +1 Gold.
- 49 base is rejected without changing inventory.
- 50 base becomes 0 base + 1 Gold.
- 51 base becomes 1 base + 1 Gold.
- Mutation operation ID is derived from the request token, so replaying the same request returns the stored result and does not deduct twice.
- Species ownership counts base + Gold, so an equipped dinosaur stays equipped even when base reaches zero.
- If the equipped species has no base copies but does have Gold, its placeholder visual switches to metallic Gold.
- Private-test SET 49 / SET 50 / SET 51 buttons reset Compy to exact test states.

## Test objectives

Create a fresh private test experience if possible and enable Studio Access to API Services.

1. Start F5. Profile says Loaded and Compy is equipped.
2. Click SET 49, then MUTATE GOLD. Status must say insufficient_copies. Compy remains exactly 49 base / 0 Gold.
3. Click SET 50, then MUTATE GOLD. Status says mutated. Compy becomes exactly 0 base / 1 Gold, stays EQUIPPED, and the dinosaur turns metallic Gold.
4. Click RETRY SAME. Status says duplicate. Compy remains exactly 0 base / 1 Gold.
5. Click SET 51. Compy becomes exactly 51 base / 0 Gold and stays equipped.
6. Click MUTATE GOLD. Compy becomes exactly 1 base / 1 Gold. It must never go negative.
7. Stop Play completely and start F5 again. Compy must still be 1 base / 1 Gold and still equipped.
8. Click Compy in the collection panel. It remains equippable with a Gold copy present. Then click SET 50 and mutate once more: at 0 base / 1 Gold it must still remain owned/equipped.

If all eight pass, BD-014 is Done.
