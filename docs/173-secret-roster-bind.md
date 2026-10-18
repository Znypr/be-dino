# 173 Secret roster: which models are bound, and the playtest switch (BD-606, BD-228, 2026-10-18)

Label: **CURRENT BUILD BEHAVIOR of the *playtest* profile after this change; the *default* profile (Build 020 mirror) is unchanged and still pins `SecretSpeciesEnabled` off.** Offline work only: nothing ran in Studio, on a phone, on a published server or against a real DataStore, nothing was published. Spec of the rules: [149](149-secret-species.md). Decisions: [115](115-decisions-log.md) SS10 to SS12. Kanban: BD-606 (and the rows of the species: BD-228, BD-600, BD-602, BD-621, BD-622).

**Rule (OWNER DIRECTIVE 2026-10-18):** "always use our newest features in testbuilds". Reading under [157](157-playtest-profile-newest-features.md): a feature goes ON in the playtest profile when it is built, proven offline and has its final art. The secret creatures are built and proven; **one of seven has a model**, so the playtest turns the flag ON for that one and the rest wait for their models.

## 1. The table: every secret species and its model

"Asset id" is the id of the published `generate_mesh` **Model** (the id `InsertService:LoadAsset` takes, what `LowPolyDinoAssets` stores). Checked on 2026-10-18 with the public Roblox economy details call (read only, no file downloaded): every id below is a Model (`AssetTypeId` 10) of the owner's account `znyprs`, the same kind and owner as the 22 shipped species. A part mesh id (a `MeshPart.MeshId`) is NOT a Model id and cannot be bound.

| Species | Class | Asset id (Model) | Status in the game | Size known (studs, scale 1, W x H x L) | Owner decision / note |
| --- | --- | --- | --- | --- | --- |
| Foxosaurus | Ground | **112996440434481** (v2, BD-602 candidate C; created 2026-10-17). Part meshes, only a fallback if Place 1 is lost: body 140224882951722, head 121501467451319, hair 70401230262509, left ear 93176586443959, right ear 78485891946918, left leg 121540493748395, right leg 90686375947030, tail 124051111330462 | **BOUND** (slot, registry entry, measured ladder row, scale 0.79) | 3.8 x 8.4 x 8.0 (Place 1 bounding box, [evidence](evidence/2026-10-17-fox/README.md)) | A normal fox look: no glasses, no beanie, blue fur (owner 2026-10-17, then the owner's v2 picture). Rated 5 of 10. The v1 id 119604460832523 (glasses and beanie) is OUTDATED, never bind it. The head length is an estimate (22% of the length) until the head part is measured |
| Budgiesaurus | Fly | 107910518074360 (v2; created 2026-10-17). v1 111728956844490 is superseded | **MISSING: the box.** The id is real, but nobody wrote down the size, and a bound slot must have a MEASURED row (the verifier refuses an estimate in the game) | NOT recorded | Owner OW4 (2026-10-18): keep it as it is, no touch-up. Rated 6 of 10 |
| Chickosaurus | Ground | 108391746824463 (the v3 test mesh of the first chicken; created 2026-10-15) | **MISSING: the box**, and nobody has confirmed this is the mesh the owner wants as the final chicken | NOT recorded | Owner-named (BD-228). The old docs call it a "test mesh" |
| Pigeon | Ground | **MISSING: the id was never written down** | MISSING | NOT recorded | A Place 1 model exists in `Workspace > Silly secret dinos v3`; its Model id is in no document |
| Dodo | Ground | **MISSING: the id was never written down** | MISSING | NOT recorded | same |
| Duck | Ground | **MISSING: the id was never written down** | MISSING | NOT recorded | same |
| Penguin | Water | **MISSING: the id was never written down** | MISSING | NOT recorded | same |
| Cockatoosaurus (BD-621) | not set | placeholder candidate **K 77920946493998** (6.5 of 10; created 2026-10-18). Others: H 133259808005218, I 138642212523860, J 119185638622365 | **NOT in the roster**: no row in `SecretSpeciesConfig`, no class, no weight | K: 3.4 x 6.0 x 6.1 (scratch place) | LEAD placeholder = K ([115](115-decisions-log.md)). It stays out until the roster grows to nine (class and weight are a BD-606 decision, plus the hard-coded "7" in several verifiers) |
| Eaglesaurus (BD-622) | not set | candidate **F 116840996663024** (6.5 of 10, 8 parts, about 9.7k triangles; E 129626619779173 has the best face, H 116638992063695 the cutest; all in the scratch place only) | **NOT in the roster**: no row in `SecretSpeciesConfig`, no class, no weight | not recorded | A candidate, not accepted by the owner ([evidence](evidence/2026-10-18-eagle-generated/README.md)). Same step as the cockatoo before it can be a secret |

### What "MISSING" needs, and who makes it
- **The four ids (Pigeon, Dodo, Duck, Penguin):** the Model id of each model. The Place 1 instances do not store it. It is in the owner's **Creator Hub > Creations > Models** (they are all named "Roblox Generated Object", made by `znyprs`; the chicken above was created 2026-10-15 23:44 UTC, and the Pigeon, Dodo, Duck and Penguin most likely the same day or the day after, next to the other v3 low-poly dinos) or in the log of the `generate_mesh` call that made each one. Whoever finds them writes them into this table. Re-generating is the fallback.
- **The boxes (Chickosaurus, Budgiesaurus, and later the four):** one Studio measurement per model, in a Studio window that is free: the Model's bounding box at growth scale 1 (snippet in section 5). With the id and the box, binding is one command (section 4).

## 2. What the playtest does now (owner directive)
- `tools/release_profiles.py`: the `playtest` profile **sets** `SecretSpeciesEnabled = true`; the `default` profile **requires** it false (it moved out of the rules shared by every profile). `src/shared/Config.luau` still says `false`: the flag is rewritten into the generated place only.
- The roll only picks among species whose slot holds a real id (`Secret.readyIds`), so **today every secret hit is a Foxosaurus**. The other six hidden cards in the Index have no model and cannot be found yet.
- **What a tester can find:** the Foxosaurus, from **free** eggs only: eggs earned in a run, and eggs from a free bonus nest. A flat **0.5% chance per egg** (PROVISIONAL), the same for a 1-egg and a 400-egg run, and a hit on an egg that fails (a Cracked egg) is lost. In a 40-egg five-minute run that is about 1 run in 9 to 1 run in 5 (11% with 40% of the eggs failing, 18% if none fail); a 400-egg run nearly always has one (86% if none fail). The hatch shows the calm "Secret" line, a banner "Secret find! You hatched a Foxosaurus!" (others read "Sam found a secret dino!" without the name), the Index card turns from "???" into the fox, and the dino can be equipped and played as a Ground, Compy-sized fox. The Egg Odds panel says "A tiny chance of a secret dino in free eggs" for free eggs only.
- **Never from a shop egg or a paid egg** (docs/43): unchanged, proven again with the shipped roster in `verify_secret_species` part B (a crystal-shop egg carries no roll even at a forced 100% chance). The paid lines (`CrystalPacksEnabled`, `PaidRandomItemsEnabled`) stay off in every profile.
- The Index shows "0 / 7 secrets found" and seven cards: six of them are a plain "?" with no silhouette (no model). Honest, but a tester cannot complete it; the playtest notes should say so.

## 3. Why this is allowed by the rules
- [157](157-playtest-profile-newest-features.md) kept the flag off only because "all seven model slots are empty". That reason no longer holds for one slot.
- [149](149-secret-species.md) SS6: a secret cannot roll or hatch while its slot is empty (`modelReady`), so a partial roster is part of the design, not a hack. No code of the rules changed for this decision.
- Pace: nothing about normal eggs changes (with the flag on, a run egg gets one extra draw only when a model is ready; the golden hash of 16,000 flag-off rolls is unchanged).

## 4. How to bind the next one (offline, one command)
```
python tools/bind_secret_species.py --species budgiesaurus --asset-id <Model id> --box <W> <H> <L>            # dry run: prints scale, spawn box, snout, head
python tools/bind_secret_species.py --species budgiesaurus --asset-id <Model id> --box <W> <H> <L> --write --runner C:/Users/znypr/AppData/Local/Temp/bd057/luau/luau.exe
```
It edits the five places that must agree (slot, `LowPolyDinoAssets` entry, `ScaleLadder` row with `measured = true`, `SECRET_BOXES`, `BOUND_IDS` in `verify_secret_species.py`) and regenerates the docs/114 table. Then add the species to the table above and to [77](77-asset-registry.md), and run `verify_secret_species`, `verify_scale_ladder`, `verify_lowpoly_dinos`, `verify_hit_sizes`, `verify_mouth_reach`, `verify_camera_framing`, `run_rehearsal` for every profile. It refuses a made-up id (not 10 to 16 digits, already bound, not a secret), a non-positive box, a bound slot (unless `--replace`) and a box that cannot meet the size rule. `tests/test_bind_secret_species.py` checks that the tool reproduces the shipped Foxosaurus binding byte for byte.

## 5. Measuring a model in Studio (for whoever has a free window)
Insert the model at the origin (the same way the game loads it: `InsertService:LoadAsset(<Model id>)`), then read the box of its mesh parts at scale 1. The repo method is BD-471; the short form:
```lua
local container = game:GetService("InsertService"):LoadAsset(ASSET_ID)
local model = Instance.new("Model")
for _, part in container:GetDescendants() do if part:IsA("MeshPart") then part.Parent = model end end
model.Parent = workspace
local _, size = model:GetBoundingBox()
print(("%.2f x %.2f x %.2f"):format(size.X, size.Y, size.Z)) -- width x height x length, the model faces -Z
local head = model:FindFirstChild("head_geom", true) or model:FindFirstChild("head", true) -- optional: its length for --head-length
```
Width is the X size, height the Y size, length the Z size of the model as generated (the same convention as the 22 species rows). Delete the model afterwards.

## 6. Risks and what is not verified
- **Nothing was seen in Studio or on a phone.** The Foxosaurus has only been proven by pure rules, the real repository on a mocked store, the size verifiers and the registry checks. Not seen: the model standing in the game, its walk, the Index card, the hatch banner, the equip. The fox is rated 5 of 10 against the owner's picture (no shaggy hair, no crouch).
- The box is the Place 1 box of the generated model; **the head length is an estimate**. It only matters for the bite and the mouth reach of this one fox.
- `InsertService:LoadAsset` of the fox runs in the playtest at server start (one more asset next to the 22). If the load fails the species keeps the plain fallback look, like any other species.
- The drop rate (0.5%) and the chance a tester sees a fox in one session are PROVISIONAL; with one species in the roster the "secret" feels common in a long run.
- If a secret hatch ever misbehaves for a tester: delete the one `Rule("SecretSpeciesEnabled", "set", True, ...)` line in the playtest list of `tools/release_profiles.py` (the default is `_flag_off`), rebuild. A profile that already holds a hatched fox still loads (the Build 020 reader keeps the extra fields, [149](149-secret-species.md) RB1).
