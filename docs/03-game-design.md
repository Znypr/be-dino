# Be Dino game design draft
Approved direction: private test, cute ground arena, small complete progression loop.
All precise quantities and rules below are proposed tuning, not copied Be Fish behavior.

## Player journey
Lobby -> select dinosaur -> spawn protected -> collect food / eat smaller dinosaurs -> end run or be eaten -> summary and rewards -> collection / egg queue -> next run.
Death resets run size, not owned dinosaurs. Avoid gore: a pop, dust puff and short result card communicate defeat.

## Three independent quantities
- Growth score: temporary run power, starts fresh each run; determines eligibility to eat.
- Run reward units: earned through validated active play; determines how many collection rolls a run grants.
- Collection counts: persistent copies by species and mutation; used for equip and upgrades.
Do not call all three 'score' in UI or code.

## Arena and movement
One compact mostly flat prehistoric clearing with rocks, low plants and a safe lobby.
Third-person ground movement using desktop and touch inputs. No flight, underwater movement, climbing or complex combat.
Prototype one fixed gameplay collider with a growing visual model; explicitly test visual/contact mismatch. Tune capped bite range alongside visual growth.
Proposed visual scale curve: clamp((1 + score / 100)^0.25, 1, 4). This is a trial curve, not final balancing.
Keep speed differences small and cap them; a rare dinosaur should not automatically catch every starter.

## Eating and growth
Server validates food proximity, claims each pickup once and applies score.
Proposed PvP rule: attacker score must exceed target score by 10%; equal/near-equal dinosaurs cannot eat one another. This differs from a strict 'any smaller score' rule and requires owner review.
Use server-validated proximity and state, not visual mesh touches alone. Resolve competing claims deterministically; only one run-end event per victim.
Proposed spawn protection: 5 seconds; protected players can neither eat nor be eaten. Show a visible countdown.
Manual exit proposal: 3-second channel, canceled by movement; still vulnerable until complete. Death wins if processed first. This prevents an instant escape button eliminating chase tension.
Disconnect proposal: finalize last validated checkpoint rewards without a voluntary-exit bonus. Reconnection does not restore arena position/size. Crash recovery is limited to durable checkpoints.

## Collection and rarity
Proposed species: starter Compsognathus, Triceratops and Tyrannosaurus. All use the same movement controller and simple shared animation approach.
Species identity is visual first. Trial growth multipliers 1.00 / 1.05 / 1.10; speed initially equal.
Use three base tiers for three species initially; defer a full common-to-legendary catalog. More tiers with only three species would imply variety we do not have.
One Gold mutation tier. Proposed conversion consumes 50 base copies and grants one Gold copy. Decide whether the last equipped base copy is protected before implementation.
Keep species rarity and mutation separate data fields. Gold can add a small configured growth bonus with a total cap.

## Reward proposal
A run grants immediate collection rolls plus a chance of an earned egg. This is a proposed interpretation, pending confirmation of the desired chest relationship.
Validated food and PvP activity increase reward progress; elapsed time alone grants nothing, avoiding an idle farming incentive.
Before coding, GD must define a bounded conversion curve and max rolls per run. Higher activity should increase total rolls first; defer score-dependent probability changes until balance can be measured.
Trial base roll table for three species: 80% / 18% / 2%, sum 100%. These are transparent test weights, not source-game probabilities.
Keep randomness server-side and persist reward outcomes once. Do not re-roll after a retry.
Use a guaranteed starter unlock and ensure short runs can earn visible progress; assess duplicate frustration with actual playtests.

## Egg queue
One sequential earned-egg queue; earned eggs can contain dinosaur copies.
Proposed test timer: 60 seconds per egg; release timer remains undecided. Environment configuration must visibly distinguish test and release values.
At enqueue: readyAt = max(serverNow, previousReadyAt) + duration. Claim all completed entries; retain unfinished entries. Offline elapsed time counts.
Trial contents: three rolls per egg, same test table initially. Cap queue/storage and specify a visible overflow outcome before implementation; never silently delete rewards.
No paid eggs or paid timer skips for first release.

## UI
Lobby: Play, Collection, Eggs, Settings.
Run: score, reward progress, nearby relative-threat indicator, End Run, optional small session ranking.
Summary: why run ended, food/PvP contribution, earned copies and eggs, Play Again.
Collection: owned/locked cards, rarity text plus color, stats, equip, duplicate count, mutation confirmation.
Eggs: queue position, completion time, ready count, claim, empty and saving/error states.
A new player sees a one-line instruction: 'Eat food. Grow bigger. Watch out for larger dinos.'

## Fairness and pacing review
Test whether giant players trap new spawns; adjust spawn selection, protection and map sightlines before adding content.
Test 50-copy mutation time from actual rolls/hour; lower alpha threshold only through clearly isolated test config if demonstration would otherwise be impractical.
Prevent repeated victim farming from becoming the best reward source. Candidate mitigation: reduced repeat-pair rewards in a time window.
No retention, monetization or engagement target is treated as validated until observed.
