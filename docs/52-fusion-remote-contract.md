# FusionAction remote contract (BD-064 server / BD-065 client)

Written 2026-10-13 on `claude/bd-064-fusion-server`. Server implementation:
[`src/server/FusionService.luau`](../src/server/FusionService.luau), backed by
`ProfileRepository` and [`IdentityFusion`](../src/server/IdentityFusion.luau).
Implementation notes and evidence: [53](53-bd064-fusion-server.md). Task status lives
only in [Kanban](07-kanban.md).

**Status: implemented and offline-tested; no Studio or live-client verification yet.**
The client (BD-065 Fusion Menu) is built by a separate agent against this document.

## Transport

- `ReplicatedStorage.BeDinoRemotes.FusionAction` is a **RemoteFunction**, created at
  server start by `Bootstrap.server.luau` (always present, even when fusion is off).
- Call: `FusionAction:InvokeServer(request)` with exactly **one** table argument.
  Extra arguments are `bad_request`.
- Every response is a table with `ok: boolean`. The server never throws to the client.
- Any failure is `{ok = false, reason = string}`.

## Request validation (server side)

- `request` must be a table whose keys are all strings from the action's allowed set
  (below). Unknown keys (for example `traits`, `odds`, `resultId`) are `bad_request`:
  **the client never supplies traits, odds, result IDs or stages beyond `targetStage`.**
- Strings: 1..120 chars for IDs, 1..80 for `token`, 1..64 for digests, 1..16 for
  `targetStage`. Numbers must be finite integers in range.
- `donorIds`: a proper array (keys `1..n`, no holes) of 1..16 strings. The exact recipe
  count (10 for Gold) and ownership are enforced afterwards (`wrong_donor_count`,
  `wrong_owner`, ...). IDs are only ever looked up inside the caller's own profile.
- **Rate limit (PROVISIONAL):** `Config.FusionRequestsPerWindow = 20` requests per player
  per `Config.FusionRateWindowSeconds = 10` s fixed window, counted before validation
  (malformed requests also count). Over the limit → `rate_limited`.

## Actions

### `list`

Request: `{action = "list", cursor = number?, limit = number?}`

- `cursor`: the last instance sequence already received (exclusive), integer >= 0;
  omitted = from the start. `limit`: integer 1..200, default 100.

Response:

```lua
{ok = true, dinosaurs = {
    {instanceId, speciesId, stage, genes, big, shiny, mutationId, originKind,
     locked, favorited, auraCount, trailCount, equippedAuraId, equippedTrailId},
    ...
}, nextCursor = number | nil}
```

- Sorted by the numeric instance sequence (`u:<userId>/d:<n>` → `n`), ascending.
- `nextCursor` is present only if more entries remain; pass it back as `cursor`.
- `stage`: `"base" | "gold" | "diamond"` (Emerald is not enabled).
- `genes`: `{patternId?, conditionId, primaryColorId, secondaryColorId, blend, hatchSuccess}`,
  or **nil** for legacy copies whose DNA was never saved (they cannot be donors:
  `missing_pattern`).
- `originKind`: `"hatch" | "fusion" | "legacy_unknown"`.
- `locked` / `favorited`: booleans (no UI sets them yet; locked/favorited donors are
  refused with `donor_locked`).
- `mutationId`: `""` when none. `auraCount` / `trailCount`: owned per-instance cosmetics.

### `details`

Request: `{action = "details", instanceId = string}`

Response: `{ok = true, dinosaur = <copy of the identity record>}` with all record
fields (`instanceId, bucketKey, speciesId, stage, genes, big, shiny, mutationId,
traitsKnown, traitRollVersion, origin, cosmetics`) plus:

- `originalEgg` (hatched records): the saved egg snapshot (`eggId, eventId,
  mutationId, genes, shiny, big, source, ...`).
- `lineage` (fused records): `{operationId, resultId, parentIds, parentOperationIds,
  recipeVersion, oddsVersion, parentEggs = {[eggId] = egg}}`.
- Unknown or foreign ID → `donor_missing`.

### `quote`

Request: `{action = "quote", targetStage = string, donorIds = {string}}`

Response:

```lua
{ok = true, quote = {
    speciesId, patternId, targetStage,
    donorIds,          -- sorted copy of the selection
    lossManifest,      -- {{instanceId, auraIds, trailIds, equippedAuraId, equippedTrailId, shiny, big, mutationId}}
    consentRequired,   -- true when lossManifest is non-empty
    consentDigest,     -- echo in `fuse` when consentRequired
    quoteDigest,       -- echo in `fuse`; any donor change makes it stale
    recipeVersion,     -- "gold-same-species-pattern-10-v1"
    oddsVersion,       -- "fusion-odds-provisional-v1"
    odds = {
        shiny = p, big = p,
        mutation = {[mutationId] = p},   -- only mutations present on donors
        noMutation = p,
        condition = {[conditionId] = p},
        primaryColor = {[colorId] = p},
        secondaryColor = {[colorId] = p},
    },
}}
```

- Every `p` is the **exact** probability (0..1) the server rolls with. `mutation`
  values plus `noMutation` sum to 1; `condition`, `primaryColor`, `secondaryColor`
  each sum to 1. Outcomes with 0% are omitted from the maps.
- Not in `odds` but fixed by the PROVISIONAL formula: blend is a uniform integer
  1..99, or 100 when the rolled primary and secondary colors are equal; the pattern is
  locked to `patternId`; the result never fails (`hatchSuccess = true`); the stage is
  guaranteed (`targetStage`).
- A quote consumes nothing and reserves nothing.

### `fuse`

Request:

```lua
{action = "fuse", token = string, targetStage = string, donorIds = {string},
 quoteDigest = string, consentDigest = string?}
```

- `token`: client-generated idempotency key (for example a GUID), 1..80 chars. Reuse the
  same token when retrying the same confirmation.
- `consentDigest` is required when the quote had `consentRequired = true`.

Response:

```lua
{ok = true, status = "fused" | "duplicate", result = {
    resultId, targetStage, speciesId, patternId,
    traits = {genes, big, shiny, mutationId},
    oddsVersion,
}}
```

- `"fused"`: committed now. `"duplicate"`: the same token and donor set were already
  committed; the original result is returned without a reroll or second consumption.
- All selected donors are consumed and one NEW dinosaur `resultId` is created in one
  atomic profile write; traits are rolled once on the server before the write. A
  reveal wheel must only display `result.traits`.

## Reason codes (`ok = false`)

| Reason | Meaning |
| --- | --- |
| `bad_request` | Malformed request (type, length, keys, extra arguments) |
| `rate_limited` | Over the per-player request window |
| `fusion_disabled` | Fusion flag off (or identity not enabled for this server) |
| `profile_not_loaded` | Profile still loading, lease lost or save failed earlier |
| `identity_unavailable` | No identity sidecar, or it is suspended (legacy/over capacity) |
| `random_items_unavailable` | Profile is Robux-linked and the paid-random gate is closed |
| `unknown_stage`, `recipe_not_approved`, `projection_unsupported` | Target stage not fusable (only Gold is) |
| `wrong_donor_count`, `duplicate_donor`, `invalid_donor_id`, `wrong_owner` | Bad selection |
| `donor_missing`, `invalid_instance`, `wrong_stage`, `donor_locked`, `missing_pattern`, `species_mismatch`, `pattern_mismatch` | Donor not eligible |
| `stale_quote` | A donor changed since the quote: re-quote and re-confirm |
| `consent_required` | Missing or wrong `consentDigest` |
| `invalid_token`, `token_conflict` | Bad token, or the token was used for a different request |
| `odds_not_approved`, `invalid_outcome` | No valid roller / rolled traits failed validation |
| `storage_limit` | Profile byte budget would be exceeded; nothing consumed |
| `identity_capacity`, `grouped_mismatch`, `invalid_fusion_ledger`, `identity_collision`, `invalid_profile` | Consistency guard; nothing consumed |
| `lease_lost`, `save_failed` | Write not committed; nothing consumed. Retry with the same token after reload |

## Client guidance

- Re-quote after any inventory change; show `odds` exactly; show every `lossManifest`
  entry before asking for confirmation.
- On a timeout, retry `fuse` with the **same token**: the answer is either the
  committed result (`duplicate`) or a clean failure. After `save_failed` or
  `lease_lost` the session's profile state leaves `Loaded` (existing repository
  behavior), so further calls return `profile_not_loaded` until the player rejoins;
  retrying the same token after reload is safe.
- Never compute or display odds client-side from donor traits; always use the quote.
