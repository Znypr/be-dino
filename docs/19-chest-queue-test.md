# Build 009: earned chest queue test

Build 009 validates BD-013. It uses a 10-second accelerated timer only for this mechanics test; the planned private-alpha balance remains 60 seconds per chest.

## Implemented

- Active chest queue capacity: 5.
- Bounded overflow capacity: 10.
- Absolute server `readyAt` timestamps, so time continues while offline.
- Overflow moves into the active queue as chests are claimed.
- Server-generated chest rewards use a separate loot table from run rewards.
- Claim outcomes are generated once before `UpdateAsync` and persisted by `chest:<id>`.
- Retrying the same claim returns the stored result and cannot grant twice.
- One-time test grant adds 7 chests, intentionally producing 5 active + 2 overflow.

## Test objectives

A new private test experience is fine if overwrite publishing hangs again. Enable Studio Access to API Services.

1. Start F5. Profile says Loaded. Chest queue should start empty on a fresh experience.
2. Click TEST ADD 7 CHESTS once. It must show Active 5 / 5 and Overflow 2.
3. Wait until Next says READY (about 10 seconds), then click CLAIM NEXT CHEST. A reward such as `1x compy` appears. Active stays 5 and Overflow becomes 1.
4. Note all dinosaur copy counts, then click RETRY LAST CLAIM. Claim status must become duplicate and no copy count may increase again.
5. As soon as the next chest is counting down, stop Play completely. Wait at least 11 seconds in real time, then start F5 again. The next chest should be READY immediately or within about one second. This proves offline elapsed time uses the saved server timestamp.
6. Claim that chest. Active stays 5 and Overflow becomes 0.
7. Stop and start F5 again. Queue counts, next ready time and all claimed dinosaur copies must persist.
8. Click TEST ADD 7 CHESTS again. Status must say duplicate and the queue must not gain another seven chests.

If all eight pass, BD-013 is Done.
