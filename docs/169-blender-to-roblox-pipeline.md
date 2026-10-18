# 169 Blender to Roblox: the model pipeline that needs no owner clicks

Written 2026-10-18 (BD-659). Owner goal: "when I give you a task, or you identify a task yourself, you should be able to create a Blender model and upload it to Roblox Studio yourself without my input." Today one step blocks that: getting the file INTO Roblox. This page says which way to do it, builds the tools, and lists the one thing only the owner can do. Label: **CURRENT BUILD** = the tools in this PR (tested offline, never run against the real Roblox servers). **OWNER TARGET** = the goal above.

## 0. Short answer

- **Best path: Roblox Open Cloud Assets API.** One HTTPS call uploads an FBX, Roblox makes a Model with MeshParts from it, and the answer is an asset id. No window, no mouse, no Studio needed. Roblox documents it as supported for FBX, glTF and glb.
- **Then the lead inserts it in Studio** with a short Luau snippet through the Studio MCP `execute_luau` (it loads the asset by id, puts it in the right row, builds the joints).
- **The owner does one thing, once:** make an API key in Creator Hub and store it as a Windows environment variable himself (section 3). Nobody else ever sees the key.
- Driving the Studio 3D Importer with fake mouse clicks is the backup, not the plan (section 1.3).

## 1. Research (read 2026-10-18)

### 1.1 Open Cloud Assets API (recommended)

Sources read: [Usage guide for assets](https://create.roblox.com/docs/cloud/guides/usage-assets) (and its [.md copy](https://create.roblox.com/docs/en-us/cloud/guides/usage-assets.md)), [API keys](https://create.roblox.com/docs/cloud/auth/api-keys), [Assets reference list](https://create.roblox.com/docs/cloud/reference/features/assets), [Operation resource](https://create.roblox.com/docs/cloud/reference/Operation), all read 2026-10-18.

| Fact | What the docs say | Status |
|---|---|---|
| Upload call | `POST https://apis.roblox.com/assets/v1/assets`, multipart form: field `request` (JSON: `assetType`, `displayName`, `description`, `creationContext.creator.userId` or `groupId`) and field `fileContent` (the file, `type=model/fbx`) | verified in docs |
| Model formats | `.fbx` (`model/fbx`), `.gltf` (`model/gltf+json`), `.glb` (`model/gltf-binary`), `.rbxm`, `.rbxmx` | verified in docs |
| Size | "up to 20 MB" per file, one asset per call | verified in docs (a forum post says 30 MB: UNVERIFIED, the tool uses 20) |
| Result | "Custom 3D models import as a Model container holding one or more MeshPart objects"; "Models upload as packages" (Toolbox > Inventory > My Packages) | verified in docs |
| Answer | Returns `{"path": "operations/<id>"}`. Poll `GET /assets/v1/operations/<id>` with the same key until `done: true`; then `response.assetId` and `response.moderationResult.moderationState` (`MODERATION_STATE_APPROVED`) | verified in docs (the Operation page lists `path, done, response, metadata`; an `error` field is NOT documented there, the tool handles it anyway) |
| Key | Header `x-api-key`. In Creator Hub > Credentials > API Keys add API system **Assets**, operations **Read** and **Write**. Keys work as the user who made them. Unused keys expire after 60 days; optional expiry date; optional IP allow-list | verified in docs |
| Status | The endpoints are **Beta** and "may change" | verified in docs |
| Rate limits | Not stated for Models (only audio/video quotas) | UNVERIFIED; the tool does at most 5 files per run, 3 s apart, and backs off on HTTP 429 |
| Other files | Textures inside an FBX: not mentioned. Rig and animation: **not mentioned** in the API guide | UNVERIFIED, see 1.4 |

Related forum facts (community and staff posts, not the official reference): an FBX upload "returns a Model ID", not a mesh id ([devforum 3226166](https://devforum.roblox.com/t/how-to-get-meshid-from-model-upload-cloud-assets-api/3226166), a staff member says the asset is a package and the mesh/texture ids can be read by inserting it; read 2026-10-18). Open Cloud later added `.rbxm` and mesh uploads ([announcement 2025-10-23](https://devforum.roblox.com/t/open-cloud-upload-support-for-more-asset-types/4022082)) but it tells people to use FBX or glTF through the API or the Studio Importer for ordinary 3D files, and says externally edited `.rbxm` files may not work: we do not use `.rbxm`.

### 1.2 Getting the uploaded model into Studio

- `InsertService:LoadAsset(assetId)` returns the model for an asset **you own** (devforum thread above, Apr 2025: "as the model owner ... still works"; [API page](https://create.roblox.com/docs/reference/engine/classes/InsertService) lists capability `LoadOwnedAsset`; the shared-asset extension is [announced 2025-08-20](https://devforum.roblox.com/t/extending-insertserviceloadasset-to-shared-model-meshpart-assets/3891135)). Our model is uploaded by the owner's own account, so this is the right call. `AssetService:LoadAssetAsync` is the newer one for assets of other people and needs the extra capability `LoadUnownedAsset` ([AssetService page](https://create.roblox.com/docs/reference/engine/classes/AssetService)); not needed.
- `tools/studio/insert_uploaded_model.luau` does this, and also places the model in the showcase row and builds Motor6D joints (section 2).
- The Studio MCP also has an `insert_asset` tool. We did NOT test it; the snippet does not depend on it. UNVERIFIED.
- For game code the asset ids can later be turned into mesh ids by inserting the package and reading `MeshId` / `TextureID` (staff suggestion: the Open Cloud "Execute Luau" API, [same thread](https://devforum.roblox.com/t/how-to-get-meshid-from-model-upload-cloud-assets-api/3226166)). Not needed for showcase models. UNVERIFIED.

### 1.3 The other two ways (not recommended)

| Way | Verdict |
|---|---|
| **Creator Hub web uploader** | Cannot do it: it offers Decals, Audio, Video only, and shows an `.fbx` as "Invalid file type" (found in the cockatoo test, [evidence](evidence/2026-10-18-cockatoo-blender/README.md)). |
| **Studio 3D Importer driven by the mouse** (`user_mouse_input` / `user_keyboard_input`) | Possible in principle, but it needs a visible Studio window the whole time ([docs/158](158-virtual-display-and-phone-emulator.md) plan), every dialog is a pixel guess, the owner's Place1 window must never be touched, and the docs describe the Importer as UI only: "no Studio scripting API for the Importer" found in the [Importer page](https://create.roblox.com/docs/art/modeling/3d-importer). Keep as the **backup** if the API turns out not to build joints. |
| **A Studio plugin that imports an FBX** | No such plugin API was found in the docs or by search (2026-10-18). UNVERIFIED that none exists. |

### 1.4 What the API upload may NOT keep (the biggest unknown)

The Studio Importer has settings for rig type (R15 / Custom / None), animation, "use imported pivot", and "ignore vertex colours" ([Importer page](https://create.roblox.com/docs/art/modeling/3d-importer)). The API guide does not say which settings an API upload uses. So these were **UNVERIFIED until the acceptance test and the cockatoo run, now answered in section 6**: part names, part pivots (the cockatoo parts keep their joint at the Blender origin; confirmed for parts-only, see section 6), vertex colours, a Motor6D rig, and baked animations. The pipeline is built so that it works even in the worst case: the snippet builds the Motor6D joints itself from the part pivots, and the animation module (`assets/blender/creatures/CockatooAnimations.luau`, BD-621) animates parts without needing an imported animation.

## 2. The pipeline: who does which step

```
 1 lead/agent   Blender model          .blend (an agent, headless Blender; no owner)
 2 tool         tools/blender_export_roblox.py   .blend -> .fbx + report.json (+ model check if present)
 3 tool         tools/roblox_asset_upload.py     .fbx -> Open Cloud -> asset id (+ docs/evidence/roblox-uploads.json with --register)
 4 lead         Studio MCP execute_luau          snippet loads the id, files it in the showcase row, builds joints
 5 lead         screenshot + docs/77 line        evidence, asset id in the registry, kanban row
 6 OWNER        Ctrl+S in the Place1 window      work in Place1 is UNSAVED until he does this (owner rule)
```

| Step | Command (from the repo root) |
|---|---|
| 2 export | `python tools/blender_export_roblox.py assets/blender/creatures/Cockatoo_HQ.blend --out build/pipeline-test/Cockatoo.fbx --anim` (`--rig` for armature without animations, nothing for parts only, `--dry-run` to see the Blender command) |
| 3 upload, look first | `python tools/roblox_asset_upload.py build/pipeline-test/Cockatoo.fbx --name Cockatoosaurus` (dry run: checks the file, prints what it WOULD send, sends nothing) |
| 3 upload, for real | add `--upload`; add `--register` to append the id to `docs/evidence/roblox-uploads.json` |
| 4 insert, look first | `python tools/studio/render_insert_snippet.py --asset-id 123456 --name Cockatoosaurus --group "Silly secret dinos v3"` then paste the output into `execute_luau` (DryRun: prints the plan, changes nothing) |
| 4 insert, for real | same with `--live` |

What the pieces do:

- **Export** uses plain `blender --background` (Blender 5.1.2 at `C:\Program Files\Blender Foundation\Blender 5.1\`, or `BLENDER_EXE`). It never touches the Blender MCP or an open Blender window. Settings come from the cockatoo evidence: 1 Blender unit = 1 stud, up Y, FBX forward from `--faces` (default +Y gives FBX forward Z so a creature facing +Y in Blender faces -Z in Roblox; the first run with forward -Z turned it 180 degrees, see section 6), part origins kept (they become joint pivots), scale 1 / rotation 0 (checked), vertex colours as sRGB, normals only, no extra leaf bones, bone axis Y/X, all actions baked with `--anim`. It refuses a mesh over 21,844 triangles and warns about odd scale, missing UVs/colours, wrong size. It writes `<name>.report.json` (parts, triangles, size in studs). If `tools/check_model_for_roblox.py` exists (the docs/163 model checker, not on main when this was written) it runs it; if not it prints a notice and goes on. The checker's command line is assumed to be `check_model_for_roblox.py <fbx>`: UNVERIFIED.
- **Upload** accepts only `.fbx .gltf .glb` (models), images and sounds, max 20 MB, max 5 files per run, checks the file header, and does nothing but print unless `--upload` is given. It reads the key only from `ROBLOX_OPEN_CLOUD_KEY` and the owner's user id from `ROBLOX_CREATOR_USER_ID` (or `ROBLOX_CREATOR_GROUP_ID`, or a small file `%USERPROFILE%\.be-dino\roblox_upload.json` with `{"creator_user_id": 123}`, which lives outside the repo). The registry line holds asset id, name, file, size, sha256, moderation state and time: no key, no user id.
- **Studio snippet** (`tools/studio/`, never `src/`): looks at the group folder first (existing models, row z, next free x), refuses to duplicate a model that is already there, loads the asset, aborts if it contains a script, lays the model on y = 0 at the next free x with a 6-stud gap, anchors the parts, and if you pass a `Joints` table it makes Motor6D joints from each part's pivot (`C0`/`C1` computed from the pivot so the rest pose does not move). It does not make signs: a brand-new group needs the cream sign at x = -14 added by hand.

**Images are Decals (BD-1068, 2026-10-18).** The Assets API makes a `.png` a **Decal** asset. A Decal id is not an image id: an ImageLabel given it logs "Asset type does not match requested type" and shows nothing. The real image id is the Decal's `Texture` property: run `tools/studio/decal_to_image.luau` in Studio (`InsertService:LoadAsset(decalId)` works for assets the signed-in account owns), bind the id it prints, and write it as `imageId` beside the `assetId` in `docs/evidence/roblox-uploads.json`. The upload tool now prints this reminder after every Decal. The four class icons were fixed this way.

## 3. What the OWNER does once (about 5 minutes)

1. Open Creator Hub, **Credentials > API Keys > Create API Key**. Name: `bedino-asset-upload`.
2. Access Permissions: add API system **Assets**, operations **Read** and **Write**. Nothing else (no data stores, no places, no messaging). If the page asks which experience, pick the Be Dino one; if it lets you, keep the restriction on. (The docs say "if applicable": UNVERIFIED whether the Assets system asks.)
3. Expiration: set about 90 days. Leave the IP list off (the PC's address changes).
4. **Save & Generate Key**, copy the key.
5. Store it yourself, in a way that does not leave it in a command history. Easiest: Windows search "Edit environment variables for your account" > **New...** > name `ROBLOX_OPEN_CLOUD_KEY`, value = the key > OK. Add a second one: name `ROBLOX_CREATOR_USER_ID`, value = the number in your Roblox profile address (`roblox.com/users/NUMBER/profile`).
   Terminal version (the key is then in the shell history; delete that line afterwards): `setx ROBLOX_OPEN_CLOUD_KEY "PASTE_KEY_HERE"` and `setx ROBLOX_CREATOR_USER_ID "PASTE_YOUR_NUMBER_HERE"`.
6. Close and reopen the Claude app (environment variables are only read when a program starts).
7. Check, without showing the key: in a new terminal `python tools/roblox_asset_upload.py anyfile.fbx` must say `Key present in ROBLOX_OPEN_CLOUD_KEY: yes`.

**Never paste the key into the chat, a file, a commit, an issue or a message to the lead or an agent.** If it ever appears anywhere, delete the key in Creator Hub (Credentials, the key's menu) and make a new one.

## 4. Security notes

- **Scope.** The key can only create and update assets in the owner's inventory. It cannot publish the game, change settings, read player data, or spend Robux. Worst case if it leaks: someone uploads junk (or rule-breaking content, which could earn the owner's account a moderation strike). That is why it is Assets-only, expires, and is easy to delete.
- **Honest limit.** The tool never prints, logs or writes the key, has no key argument, and scrubs it out of every error message (tests check this). But any program running as the owner can read an environment variable, including an agent that decides to run `echo`. The protection is the small scope, the expiry date, and the rule below, not secrecy from the PC. Agents must never print, copy or look for the key, and must say so if they ever see it.
- **Rotation.** Make a new key every 90 days (or when it expires or after 60 unused days), replace the two variables, delete the old key.
- **Never commit** the key, the creator config file, or anything from `%USERPROFILE%\.be-dino\`. The registry file is safe to commit.
- Uploads go through moderation. The tool prints the moderation state; a model that is not approved will not load for other people. Upload only models we made (rule: final art is Blender or the owner's).
- Dry run is the default. Only `--upload` sends. At most 5 files per run.

## 5. 10-minute acceptance test (after the key exists)

Uses a 4-stud cube. It proves each step once; delete the result afterwards.

1. `blender --background --factory-startup --python tools/blender/make_acceptance_cube.py -- build/pipeline-test/cube.blend` (full path to `blender.exe` if it is not on PATH).
2. `python tools/blender_export_roblox.py build/pipeline-test/cube.blend --out build/pipeline-test/cube.fbx` : expect `FBX written` and a report with 12 triangles, size 4 x 4 x 4.
3. `python tools/roblox_asset_upload.py build/pipeline-test/cube.fbx --name AcceptanceCube` : dry run, expect the request and `Key present ... yes`.
4. Same with `--upload` : expect `ASSET_ID <number>` and moderation `APPROVED` within about a minute. Pass: the number exists. Note it down; in Creator Hub > Inventory > My Packages the cube should be listed.
5. `python tools/studio/render_insert_snippet.py --asset-id <number> --name AcceptanceCube --group "Pipeline test" --create-group`, paste into `execute_luau`: expect a plan (1 part, size about 4 x 4 x 4). Run again with `--live`.
6. Pass if: the cube is in `Workspace > Pipeline test`, 4 studs wide, lowest point on y = 0, the six face colours show (vertex colours), no script inside. Take a Studio capture (path into the evidence folder).
7. Delete the folder `Pipeline test` in Studio. (Place1 is unsaved until the owner presses Ctrl+S, so nothing is lost or kept without him.)
8. Then the real test: export `Cockatoo_HQ.blend` with `--anim`, upload, insert with the `Joints` table from the snippet's comment, and write down in the BD-659 row what survived: part names, pivots, vertex colours, joints, animation. That answers section 1.4.

If step 4 fails: HTTP 401 = key wrong or expired; 403 = key lacks Assets Write, or wrong creator id, or an experience/IP restriction; 400 = Roblox rejected the file (try the Studio Importer once by hand to see its error text); "still not done" = wait and check My Packages.

### Acceptance run, 2026-10-18 (lead, owner-created key, scratch copy of Place1, nothing in the owner's Place1)

- Export -> upload -> approval -> `InsertService:LoadAsset` in Studio through the Studio MCP all WORKED with the real key (key present in the lead process, never printed).
- First cube upload (asset 98358657150463) came into Studio as **400 x 400 x 400 studs**: Blender writes metres as centimetres and Roblox reads FBX units as studs (x100). Fix in `tools/blender_export_roblox.py`: `global_scale=0.01`. Second upload (asset 118790017458239): **4 x 4 x 4 studs**, one MeshPart, no script inside. Pass.
- The upload returned approved within seconds; Open Cloud made a Model with one MeshPart (name kept).
- Still UNVERIFIED: vertex colours (needs a rendered Studio frame; the scratch Studio is minimised), multi-part names, pivots, Motor6D/rig and animations (the cockatoo run answers this), cost per upload (none seen), whether `LoadAsset` also works from a Studio signed in as a different account.
- Both test assets are the owner's account models named AcceptanceCube / AcceptanceCube2 (delete in Creator Hub > Inventory when no longer needed; deleting is the owner's choice).

## 6. What survived, and what is still not verified (cockatoo run, 2026-10-18)

Full numbers and the Studio output summary: [evidence/2026-10-18-cockatoo-pipeline](evidence/2026-10-18-cockatoo-pipeline/README.md). Real key, headless Blender 5.1.2, scratch Studio `cockatoo-scratch.rbxl` (Edit mode, `InsertService:LoadAsset`). Three uploads of `Cockatoo_HQ.blend` (all Approved): parts only **116310176815729**, rig **89600501756470**, rig plus animations **102247452194822**.

| Question (1.4) | Result | Status |
|---|---|---|
| Upload, approval, `LoadAsset` for a 10-part 17,668-triangle model | works, Model > Model > 10 MeshParts, no script inside | **verified** |
| Size | 1 Blender unit = 1 stud with `global_scale 0.01`; cockatoo 7.43 studs tall (7.34 after the rest-pose fix) | **verified** |
| Part names | all 10 kept (Body, Head, Crest, Tail, ArmL, ArmR, LegL, LegR, FootL, FootR) in all variants | **verified** |
| Pivots (joint at the part origin) | **parts only: kept** (`PivotOffset`, `GetPivot()` = Blender origin; 8 of 10 within 0.001 stud of the animation module's `Joints`) | **verified** |
| Facing | **FAILED with `axis_forward -Z`**: the creature arrived turned 180 degrees (faces +Z, left and right swapped). Exporter fixed (`--faces +Y` gives forward `Z`); the fixed file was checked in Blender and in Studio by turning the model, NOT re-uploaded | defect found, fix unconfirmed in Roblox |
| Vertex colours | **kept inside the mesh** (read with `CreateEditableMeshAsync`: Body 24 distinct colours, Head 11, Crest 6, Foot 3; cream, yellow, brown, grey). `MeshPart.Color` stays default grey, `TextureID` empty | **verified in the data**; how they LOOK on the grey part is not seen (no frame) |
| Rig (`--rig`) | Roblox makes 10 Motor6D plus RootPart, InitialPoses folder, AnimationController (no Animator, no Bone), but the placement is wrong: Foot 0.93 above Leg, Crest turned, Body pivot Y and Z swapped, a Body-to-Body joint | **FAILED** |
| Baked animation (`--anim`) | **does not arrive**: no KeyframeSequence, no Animation. Identical to the rig variant | **FAILED** (not carried by the API upload) |
| Part rotations | all 0 in all variants | verified |
| Snippet joints from pivots | 9 Motor6D, rest error 0.00002 stud; the snippet found "Pipeline test" already there (AcceptanceCube) and added the model after it | **verified** |
| Animation module in Studio | `CockatooAnimations.luau` ran as a ModuleScript on the parts model; 10 samples per animation: Idle max joint rotation 9.3 degrees, Walk 28.3, Jump 75.8 (arms), Body height change 0.04 / 0.12 / 1.58 studs | **verified (numbers only)** |
| Leftover pose in the .blend | saved with LegR moved 0.2 and Idle assigned: arrived as a 0.2 pivot error on LegR and FootR; exporter now resets to the rest pose | defect found and fixed |

**Use this path:** export with no `--rig`, upload the parts model, insert with the snippet (`render_insert_snippet.py ... --joints Head=Body,Crest=Head,Tail=Body,ArmL=Body,ArmR=Body,LegL=Body,LegR=Body,FootL=LegL,FootR=LegR`), animate with the Luau module. Do not rely on `--rig` / `--anim` through the API upload.

Still NOT verified:

- The fixed export (forward `Z`, rest pose) in Roblox. Needs one more upload of the parts model.
- How the vertex colours look in a rendered frame (the scratch Studio is minimised, `screen_capture` is dark); whether a grey `MeshPart.Color` darkens them.
- Why the rig variant places second-level bones wrongly (bone axes Y/X, bone roll, hierarchy depth). A bone-less export with empties, or a different `primary_bone_axis`, would be the next experiments, each one costs an upload.
- Animation as a Roblox asset (KeyframeSequence): only the Studio importer by hand is known to make it.
- Cost per upload (none seen), rate limits (3 uploads in 20 s were fine), `LoadAsset` from a Studio signed in as another account.
- Whether `creator.userId` as a string is required (it worked as a string).
- `tools/check_model_for_roblox.py` hook (the checker is still not in this tree).
- Beta API: Roblox may change it.

## 7. Files (this PR)

`tools/roblox_asset_upload.py`, `tools/blender_export_roblox.py` (+ `--faces`, rest pose), `tools/blender/make_acceptance_cube.py`, `tools/studio/insert_uploaded_model.luau`, `tools/studio/render_insert_snippet.py`, `tests/test_roblox_asset_upload.py`, this page, the BD-659 kanban row, a pointer in [160](160-agent-brief.md), and two ignored folders in `.gitignore` (`build/pipeline-test/`, `build/blender-export/`).
