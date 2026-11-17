"""Release profiles: the single place that lists release-critical Config values.

Used by `tools/build.py --profile NAME` (rewrites values in the *generated* place
only; `src/` is never modified) and by `tools/verify_release.py` (fails when a
forbidden value is present in source or a built `.rbxlx`).

Each rule names one top-level key of `src/shared/Config.luau`:

* ``require`` -- the value must already equal ``value``; the build fails otherwise.
  Safety flags use this mode on purpose: a test grant left on in source must stop
  the release, not be silently patched over.
* ``set`` -- the profile writes ``value`` (or the current value of ``from_key``)
  into the generated place, then verifies the result.
* ``check`` -- a custom predicate (``predicate(value) -> error string | None``).

``missing`` controls keys that do not exist in Config yet: ``"error"`` stops the
build, ``"warn"`` reports clearly and continues. Flags owned by work that has not
reached main (e.g. BD-064 ``IdentityPersistentEnabled``) start as ``"warn"``;
switch them to ``"error"`` once the owning PR merges. To add a future release
key, append one ``Rule`` to the relevant list below; nothing else needs editing.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable, Optional

STORE_NAME_PATTERN = re.compile(r"^BeDino_Playtest_[A-Za-z0-9]+_v[0-9]+$")
DEVELOPMENT_STORE_NAME = "BeDino_PrivateTest_v1"
MAX_DATASTORE_NAME = 50  # Roblox DataStore name limit (characters).

# BD-502 gate 4 (docs/147 s6): Workspace.StreamingEnabled / StreamingTargetRadius / StreamingMinRadius / StreamingIntegrityMode are
# NOT scriptable at runtime (Studio and the server cannot set them), so the build writes them into the .rbxlx. Every shipped profile
# keeps streaming OFF. A shipped profile may turn it on only with an explicit gate field naming the BD-502 evidence; a scratch
# profile (never published) may turn it on for measurement. Enum StreamingIntegrityMode: Default 0, Disabled 1, MinimumRadiusPause 2,
# PauseOutsideLoadedArea 3 (checked in Studio, docs/147-addendum in the BD-503 PR).
STREAMING_INTEGRITY_MODES = {"Default": 0, "Disabled": 1, "MinimumRadiusPause": 2, "PauseOutsideLoadedArea": 3}
STREAMING_GATE_PATTERN = re.compile(r"^BD-502:(docs/[A-Za-z0-9_./-]+)$")


@dataclass(frozen=True)
class Streaming:
    """Per-profile Workspace streaming setting. Default: OFF (nothing is written into the place)."""
    enabled: bool = False
    target_radius: int = 256   # PROPOSAL (docs/115 ST3)
    min_radius: int = 128      # PROPOSAL (docs/115 ST3)
    integrity_mode: str = "Default"
    gate: str = ""             # "BD-502:docs/<evidence file>"; required for a shipped profile that turns streaming on
    scratch: bool = False      # scratch profiles are never published (only for Studio measurement)


@dataclass(frozen=True)
class Rule:
    key: str
    mode: str  # "require" | "set" | "check"
    value: Any = None
    from_key: Optional[str] = None
    predicate: Optional[Callable[[Any], Optional[str]]] = None
    missing: str = "error"  # "error" | "warn"
    reason: str = ""


def _positive_id(value: Any) -> Optional[str]:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return "must be a positive integer Roblox ID (TODO(BD-004): owner records it in src/shared/Config.luau)"
    return None


def _id_or_zero(value: Any) -> Optional[str]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return "must be 0 (not yet recorded) or a positive integer Roblox ID"
    return None


def _store_name(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value or len(value) > MAX_DATASTORE_NAME:
        return f"must be a non-empty string of at most {MAX_DATASTORE_NAME} characters"
    return None


def _playtest_store_name(value: Any) -> Optional[str]:
    error = _store_name(value)
    if error:
        return error
    if value == DEVELOPMENT_STORE_NAME:
        return "must differ from the development/legacy store name"
    if not STORE_NAME_PATTERN.match(value):
        return "must match BeDino_Playtest_<Tag>_v<N> (rotate N to isolate a corrupted test store)"
    return None


def _flag_off(key: str, reason: str) -> Rule:
    return Rule(key, "require", False, reason=reason)


# Invariants of EVERY committed build, including the default one CI uploads:
# any build might be published, so paid/test/debug switches stay off in source.
COMMON_RULES = [
    _flag_off("PaidRandomItemsEnabled", "paid-random release gate (docs/43)"),
    _flag_off("CrystalPacksEnabled", "Robux developer-product sales gate"),
    _flag_off("CollectionTestGrantEnabled", "test-only species grant"),
    _flag_off("ChestTestGrantEnabled", "test-only egg grant"),
    _flag_off("MutationTestSetupEnabled", "test-only copy setup"),
    _flag_off("SecurityTestHarnessEnabled", "security test harness"),
    _flag_off("ArtTestHarnessEnabled", "art preview harness"),
    _flag_off("QaOverlayEnabled", "BD-085 owner phone QA overlay (docs/127); flipped locally for a measurement build, never committed"),
    _flag_off("DemoDirectorEnabled", "trailer clip director, Studio-only demo tool (docs/133)"),
    _flag_off("HatchV2", "BD-397 v2 hatch; off in every committed build (also the playtest, docs/157): the paint-bucket model is a PLACEHOLDER and the docs/118 owner evidence is missing"),
    _flag_off("HatchV2Preview", "docs/118 s9 Studio-only preview toggle; the owner flips it locally, never committed"),
    _flag_off("DuplicateSettlementProbe", "historical settlement probe"),
    _flag_off("GiftingEnabled", "BD-451/BD-453 Robux gifting (docs/134 s12); enabling needs the owner's explicit go-ahead and the go-live review; the Robux sender is not built (the playtest keeps it off, docs/157)"),
    _flag_off("AdminGiftsEnabled", "BD-451/BD-452 free admin gifts (docs/134); owner flips it for the first live test of the gift inbox; an admin switch, off in the playtest too (docs/157)"),
    _flag_off("GiftClaimEnabled", "BD-451 gift claim path (Gifts DataStore inbox -> profile); required by both gift senders, owner go-ahead only; with both senders off it would only poll the Gifts store, so the playtest keeps it off (docs/157)"),
    _flag_off("DinoSkinsEnabled", "BD-456 dino skins data model + equip (docs/137); no species has a skin model yet, so the playtest keeps it off too (docs/157); the owner decides when skins go on"),
    Rule("ProfileDataStoreName", "check", predicate=_store_name, reason="DataStore name limits"),
    Rule("PlaytestUniverseId", "check", predicate=_id_or_zero, reason="BD-004 record"),
    Rule("PlaytestPlaceId", "check", predicate=_id_or_zero, reason="BD-004 record"),
    Rule("PlaytestProfileDataStoreName", "check", predicate=_playtest_store_name, reason="isolated playtest store"),
]

# Studio-local conveniences that may stay true because the server only honours
# them in unpublished Studio (RunService:IsStudio() and game.GameId == 0).
# verify_release checks those guards still exist in source.
STUDIO_LOCAL_FLAGS = ["StudioLocalProfilesEnabled", "StudioTestWalletEnabled", "DemoDirectorEnabled"]

PROFILES: dict[str, list[Rule]] = {
    "default": COMMON_RULES + [
        Rule("ReleaseProfile", "require", "development", reason="default build is a development build"),
        _flag_off("ObjectivesEnabled", "BD-072..077 mini objectives (docs/66, docs/157): only the playtest profile enables it; PROVISIONAL rewards"),
        _flag_off("FastTravelPerk", "BD-391/405 fast travel crystal perk (docs/157): only the playtest profile enables it; needs CaveHub"),
        _flag_off("GeneBoostEnabled", "BD-1038 pattern + colour boost to growth and walking (docs/186 s6, docs/157): only the playtest profile enables it; PROVISIONAL numbers, free eggs only"),
        _flag_off("FoodLayerEnabled", "BD-1047 designed food map instead of the sector/jitter dice (docs/187 B, docs/157): only the playtest profile enables it; PROVISIONAL, no Studio look yet"),
        _flag_off("FoodRespawnTiersEnabled", "BD-1081 respawn time by food value (amber 120 s, drumstick 150 s; docs/115, docs/194): only the playtest profile enables it; PROVISIONAL numbers, tune with the test bot"),
        _flag_off("PatternColourIndexEnabled", "BD-1039 Pattern and Colour Index tabs, New pattern/colour ribbons, Index dot (docs/186 s7, docs/157): only the playtest profile enables it; no art yet, plain tinted tiles"),
        _flag_off("ShopPromptBubbleEnabled", "BD-1017 message bubble above each cave stall, key E (docs/180 option A, docs/157): only the playtest profile enables it; needs CaveHub; offline evidence only, no Studio or phone look yet"),
        _flag_off("RareFindBannerEnabled", "BD-1121 rare-find announcement as a huge outlined title and one sentence with the rarity word in its colour, no panel, no player name (docs/202 R6, docs/157): only the playtest profile enables it; same limits as BD-428, offline evidence only"),
        _flag_off("HudRailWordsEnabled", "BD-1116 HUD rail with a word on every button, bigger buttons, at most five, Settings as a gear (docs/202 R1, docs/212, docs/157): only the playtest profile enables it; offline evidence only, no Studio or phone look yet"),
        _flag_off("TimerChipsEnabled", "BD-1124 short timer words on the HUD, potion drain bars, big Found 1/22 bar in the Index (docs/202 R11 and R12, docs/220, docs/157): only the playtest profile enables it; offline evidence only, no Studio or phone look yet"),
        _flag_off("StarterRunEnabled", "BD-1163 starter run: the first run of a brand-new profile starts by itself, ends at a happy card and settles at least 3 never-Cracked eggs (owner decision 2026-11-10, docs/225, docs/157): only the playtest profile enables it; offline evidence only, no Studio, no child has played it"),
        _flag_off("DupProgressEnabled", "BD-1170 part A duplicate progress: '3 of 6 for Gold!' in the hatch reveal and a progress bar on the Index species page (docs/221, docs/227, docs/157): only the playtest profile enables it; client words only; offline evidence only, no Studio or phone look yet"),
        _flag_off("MotionPresetsEnabled", "BD-1182 UI motion presets: window open 0.3 s with a soft overshoot, close 0.15 s, button press sinks 5 px and pops on release (docs/228 board 6, docs/229, docs/157): only the playtest profile enables it; client presentation only; offline evidence only, no Studio, phone or eyes on it"),
        _flag_off("ToyboxUIEnabled", "BD-1177 Toybox UI skin: stud window body, glossy header per place, red gloss X, two-tone gloss buttons, 3 px outlined text (owner 2026-11-14), bright cream panels on the docs/232 layout rules (owner decision 2026-11-13, docs/228 board 1, docs/230, docs/157): only the playtest profile enables it; client presentation only; the 23 picture ids are bound (2026-11-14) and the owner and lead have seen it in Studio; no phone check yet"),
        _flag_off("HatchStageEnabled", "BD-1211 hatch as a full stage over the world in the one style (docs/240 R7, owner 2026-11-15 'continue until all proposed changes are in the actual game'): only the playtest profile enables it; client presentation only; no phone check yet"),
        _flag_off("WorldV3Enabled", "BD-1209 redesigned round island: beach, plaza, spoke paths, ring road, five zones (docs/241 W1-W3, owner 2026-11-15 'continue until all proposed changes are in the actual game'): only the playtest profile enables it; terrain and placement only; no phone check yet"),
        _flag_off("FoodV3Enabled", "BD-1208 V3 food pickups generated from the approved food icons (docs/241 W6, owner OK 2026-11-15): only the playtest profile enables it; visual only; Studio evidence docs/evidence/2026-11-15-food-v3, no phone check yet"),
        _flag_off("HudCohesionEnabled", "BD-1213 HUD and world labels on the style rules R1-R8 (docs/240 step 2, style tile v2 board 1, docs/157): only the playtest profile enables it; client presentation only; Studio evidence docs/evidence/2026-11-16-hud-cohesion, no phone check yet"),
        _flag_off("MenusCohesionEnabled", "BD-1237 Egg chances, Food guide, weather title card, toasts and the Fusion colour bar on the style rules R1-R8 (docs/240 step 4, docs/157): only the playtest profile enables it; client presentation only; Studio evidence docs/evidence/2026-11-16-menus-style, no phone check yet"),
        _flag_off("ScreensCohesionEnabled", "BD-1214 Run complete, Home, Welcome and Loading on the style rules R1-R8 (docs/240 step 3): only the playtest profile enables it; client presentation only; Studio evidence docs/evidence/2026-11-16-screens-cohesion, no phone check yet"),
        _flag_off("AudioPolishEnabled", "BD-1218 + BD-1219 calm music beds, sounds for the 14 silent cues and soft dino footsteps (docs/242 benchmark gaps 3 and 4): only the playtest profile enables it; client sound only; Roblox-licensed Creator Store audio (docs/77); unheard by agents, the owner judges by ear (docs/87)"),
        _flag_off("IndexMilestonesEnabled", "BD-1230 Dino Index milestone rewards: free crystals once at 25 / 50 / 75 / 100 % of the species (PROVISIONAL 50 / 100 / 200 / 500), granted inside the hatch transaction, additive profile field indexMilestones (docs/242 benchmark gap 15): only the playtest profile enables it; no Robux, no paid or random item; Studio evidence docs/evidence/2026-11-16-ui-feedback, no phone check yet"),
        _flag_off("PlayCuesEnabled", "BD-1226 + BD-1231 + BD-1234 play cues: point-at chips on the first food, the ready nest and a stall; a '+N' at the dino and a word banner at each SIZE quarter; an egg-ready toast and EGGS badge (docs/242 benchmark gaps 11, 15, 19): only the playtest profile enables it; client presentation only; Studio evidence docs/evidence/2026-11-16-ui-feedback, no phone check yet"),
        _flag_off("RealSeaEnabled", "BD-1220 real sea to the horizon, no square ocean plate, less haze from above (docs/242 benchmark gap 5): only the playtest profile enables it; terrain and lighting only; Studio evidence docs/evidence/2026-11-16-world-look, no phone check yet"),
        _flag_off("ToonWorldEnabled", "BD-1223 + BD-1224 one toy style on the island: flat toon ground colours, round bushes instead of the spiky ferns (docs/242 benchmark gaps 8 and 9): only the playtest profile enables it; look and placement only; Studio evidence docs/evidence/2026-11-16-world-look, no phone check yet"),
        _flag_off("FoodHostsEnabled", "BD-1238 food at matching hosts on the V3 island: berries on the round bushes, fruit under the trees, amber and eggs at rocks and landmarks (docs/241 W6 + W7): only the playtest profile enables it; placement only, no new parts; Studio evidence docs/evidence/2026-11-16-food-hosts, no phone check yet"),
        _flag_off("VegetationV2Enabled", "BD-1239 vegetation v2 on the V3 island: chunky toy trees, berry bushes, flower clusters, soft grass clumps, ferns and mossy rocks from the approved concept sheet (owner 2026-11-16): only the playtest profile enables it; look only, same placement and colliders, fewer ground cover parts; Studio evidence docs/evidence/2026-11-16-vegetation-v2, no phone check yet"),
        _flag_off("IslandLifeEnabled", "BD-1244 life on the V3 island: butterflies, dragonflies, gulls and small wild baby dinos grazing near the paths, client-only (owner 2026-11-16 'game still looks empty'): only the playtest profile enables it; look only, pooled, culled at 150 studs, no physics; Studio evidence docs/evidence/2026-11-16-world-fill-life, no phone check yet"),
        _flag_off("WarmLightEnabled", "BD-1247 warmer light on the V3 island: warm colour grade, gentle bloom, soft sun rays, slow pollen motes per zone (owner 2026-11-16 'game still looks empty'): only the playtest profile enables it; look only, clear weather on the island only; Studio evidence docs/evidence/2026-11-16-world-fill-life, no phone check yet"),
        _flag_off("GroundDetailEnabled", "BD-1245 path and ground detail on the V3 island: grass lip along the paths, soft grass and earth patches, generated edge stones, pebbles, logs and flower patches, thinner single ground cover (owner 2026-11-16 'game still looks empty'): only the playtest profile enables it; look only, fewer parts near spawn; Studio evidence docs/evidence/2026-11-16-world-fill-ground, no phone check yet"),
        _flag_off("ThingsToDoEnabled", "BD-1246 something to do in every view: food clusters along the first stretch of each spoke path (same foods and per-zone counts) and one generated set piece per spoke (owner 2026-11-16 'game still looks empty'): only the playtest profile enables it; placement and look only; Studio evidence docs/evidence/2026-11-16-world-fill-ground, no phone check yet"),
        _flag_off("PlazaHubEnabled", "BD-1221 spawn plaza hub: four stalls with big signs and walk-up prompts (docs/242 benchmark gap 4): only the playtest profile enables it; placement and client prompts only; Studio evidence docs/evidence/2026-11-16-world-look, no phone check yet"),
        _flag_off("BlobShadowEnabled", "BD-1261 soft blob shadow: one glow decal per dino instead of three stacked discs (owner 2026-11-17 phone test 'dino shadows are really low quality', docs/244 s2.14): only the playtest profile enables it; client presentation only; Studio evidence docs/evidence/2026-11-17-ui-world, no phone check yet"),
        _flag_off("PlazaShopsV2Enabled", "BD-1248 plaza shops v2: themed generated shop buildings (egg house, mushroom potion hut, crystal stall, fossil-skull hut), one wooden signboard with the word and an icon per shop, low-poly dino shopkeepers (owner 2026-11-16 'not what famous roblox experiences do'): only the playtest profile enables it; look only, same prompts and At home rule; Studio evidence docs/evidence/2026-11-16-plaza-shops-v2, no phone check yet"),
        _flag_off("RareHatchNewsEnabled", "BD-1227 rare hatch news with the hatcher's display name, Epic and up, one chat line (docs/242 gap 17): only the playtest profile enables it; free, no Robux; Studio evidence docs/evidence/2026-11-16-social"),
        _flag_off("FriendBonusEnabled", "BD-1228 friend bonus: +10% run crystals while a Roblox friend is in the server, HUD chip (docs/242 gap 17): only the playtest profile enables it; free, no Robux; Studio evidence docs/evidence/2026-11-16-social"),
        _flag_off("BadgesEnabled", "BD-1229 BadgeService awards from the badge-id table; ids empty until the owner creates the badges (docs/242 gap 18): only the playtest profile enables it; free, no Robux; Studio evidence docs/evidence/2026-11-16-social"),
        _flag_off("CodesEnabled", "BD-1233 code box and group gift chest, free crystals once per player, additive redeemedCodes field (docs/242 gap 18): only the playtest profile enables it; free, no Robux; Studio evidence docs/evidence/2026-11-16-social"),
        _flag_off("ZoneAmbienceEnabled", "BD-1225 soft ambient loop per World V3 zone, crossfaded, ambience volume group (docs/242 gap 14): only the playtest profile enables it; free, no Robux; Studio evidence docs/evidence/2026-11-16-social"),
        _flag_off("DinoRigClipsEnabled", "BD-1217 authored dino locomotion clips (idle, walk, run, hop), tail and head follow-through, default R15 Animate off under the hidden avatar (docs/242 benchmark gap 2): only the playtest profile enables it; client presentation only; Studio evidence docs/evidence/2026-11-16-dino-rig, no phone check yet"),
        _flag_off("LoadingSceneEnabled", "BD-1232 loading scene: the owner-approved Blender render egg_stage_jungle behind the logo, a rotating kid tip and a late Skip (docs/242 benchmark gap 17): only the playtest profile enables it; client presentation only; Studio evidence docs/evidence/2026-11-16-ui-feedback, no phone check yet"),
        _flag_off("HatchFastCommonsEnabled", "BD-1164 hatch pacing: Common and Uncommon eggs of a batch reveal in about 1 s each and move on by themselves, Rare and up keep the full show (owner decision 2026-11-10, docs/226, docs/157): only the playtest profile enables it; client presentation only; offline evidence only, no Studio, phone or eyes on it"),
        _flag_off("WelcomeBackEnabled", "BD-1168 welcome-back toast card at join when a nest finished while the player was away (docs/221, docs/223, docs/157): only the playtest profile enables it; offline evidence only, no Studio or phone look yet"),
        _flag_off("PlayAgainEnabled", "BD-1199 PLAY AGAIN button after the last egg + gentle run streak with a small crystal bonus (docs/235, docs/239, docs/157): only the playtest profile enables it; numbers PROVISIONAL, offline evidence only, no Studio or phone look yet"),
        _flag_off("ShopCardPriceButtonEnabled", "BD-1118/BD-1144 Aura and Trail shop card with the price on the one wide button, details behind Info (docs/202 R3, docs/213, docs/157): only the playtest profile enables it; offline evidence only, no Studio or phone look yet"),
        _flag_off("SecretSpeciesEnabled", "BD-604/BD-228 secret silly creatures (docs/149, docs/173): only the playtest profile enables it; PROVISIONAL 0.5% chance, free run and nest eggs only, never a shop or paid egg"),
        _flag_off("IdentityPersistentEnabled", "BD-064 persistent identities; only the playtest profile enables it"),
        _flag_off("IdentityFusionPreviewEnabled", "BD-057/BD-064 fusion; only the playtest profile enables it"),
        _flag_off("PerDinoCosmeticsEnabled", "BD-059 per-dino cosmetics (docs/121); phase 2 shop wiring stays off until owner Studio check"),
        _flag_off("RunTelemetryEnabled", "BD-426 session telemetry; only the playtest profile enables it"),
        _flag_off("PlaytestFeedbackEnabled", "docs/128 playtest feedback button; only the playtest profile enables it"),
        _flag_off("CombatEnabled", "BD-243 HP combat; unproven on a phone (BD-252), default build keeps instant predation"),
        _flag_off("ClassMovementEnabled", "BD-423 class movement; only the playtest profile enables it"),
        _flag_off("SpecialFoodsEnabled", "BD-207 rare special foods; PROVISIONAL points, behind an owner playtest"),
        _flag_off("CaveHub", "BD-280 cave Sanctuary; behind the BD-293 device test"),
        _flag_off("LowPolyDinos", "BD-225 low-poly dinos; behind BD-309/BD-097 published-server and phone checks"),
        Rule("WorldArtMode", "require", "Legacy", reason="BD-049 world kit; only the playtest profile enables it"),
        Rule("FoodArtMode", "require", "Legacy", reason="BD-050 food kit; only the playtest profile enables it"),
    ],
    "playtest": COMMON_RULES + [
        Rule("ReleaseProfile", "set", "playtest", reason="marks the generated place"),
        Rule("ProfileDataStoreName", "set", from_key="PlaytestProfileDataStoreName",
             reason="fresh, isolated playtest profile store"),
        Rule("ProfileDataStoreName", "check", predicate=_playtest_store_name, reason="isolated playtest store"),
        Rule("PlaytestUniverseId", "check", predicate=_positive_id, reason="BD-004: private experience ID"),
        Rule("PlaytestPlaceId", "check", predicate=_positive_id, reason="BD-004: private start place ID"),
        # Milestone 1 includes fusion with persistent identities (BD-064). The key
        # is not on main yet: warn until it lands, then set missing="error".
        Rule("IdentityPersistentEnabled", "set", True, reason="BD-064 persistent identities (Milestone 1)"),
        Rule("IdentityFusionPreviewEnabled", "set", True, reason="BD-064 fusion on persistent profiles (Milestone 1)"),
        # docs/68: owner wants the new world kit and food art in the playtest. With uploaded MeshParts one prop is
        # one part, so density 1.25 (~1,250 props) is ~4.3k parts incl. food (tools/verify_world_art.py enforces <= 8,000).
        Rule("RunTelemetryEnabled", "set", True, reason="BD-426 anonymous run/session telemetry for the playtest (docs/122)"),
        Rule("PlaytestFeedbackEnabled", "set", True, reason="docs/128 in-game feedback button for the friends playtest"),
        Rule("WorldArtMode", "set", "BiomeKit", reason="BD-049 new trees/rocks/landmarks (docs/68)"),
        Rule("FoodArtMode", "set", "Kit", reason="BD-050 food variants (docs/68)"),
        # docs/107: legacy dinos are 1,424-2,400 parts each (12 players = 24k-41k parts); low-poly dinos are ~119. The playtest
        # ships the cheap ones; the default profile keeps requiring false. Every species falls back to the legacy visual on a failed load.
        Rule("LowPolyDinos", "set", True, reason="BD-225 low-poly dinos for friends playtests (docs/107 part budget)"),
        Rule("ClassMovementEnabled", "set", True, reason="BD-423 class feel (glide, dash, speed) for friends playtests, no combat needed"),
        Rule("CaveHub", "set", True, reason="owner 2026-10-16: the cave hub is in the first friends playtest (docs/125)"),
        Rule("WorldArtDensity", "set", 1.25, reason="PROVISIONAL: world v2, 1 part per MeshPart prop, total under 8,000 (docs/68)"),
        # docs/157 (OWNER DIRECTIVE 2026-10-18: "always use our newest features in testbuilds including fusion, food models, dino models,
        # vegetation, map, etc"): the TEST/PLAYTEST profile turns the built player-facing features on. The default profile (which mirrors
        # Build 020) keeps requiring every one of them false. The paid line, the test/QA/demo switches and the flags whose final art is
        # still missing stay required-false below, each with its reason. One line per flag so a revert is a one-line change.
        Rule("ObjectivesEnabled", "set", True, reason="BD-072..077 mini objectives panel and hooks (docs/157); BD-625 batch rides the lease renew; PROVISIONAL rewards"),
        Rule("CombatEnabled", "set", True, reason="BD-243..252 HP combat with bite, health bars and NPC predators (docs/157); offline suites pass; phone/2-player test is exactly what the test build is for"),
        Rule("SpecialFoodsEnabled", "set", True, reason="BD-207 rare special foods (docs/157); PROVISIONAL points; works with FoodArtMode Kit"),
        Rule("PerDinoCosmeticsEnabled", "set", True, reason="BD-059 per-dino auras/trails with the fusion loss notice (docs/121, docs/157); fresh playtest store has no legacy purchases to migrate"),
        Rule("GeneBoostEnabled", "set", True, reason="BD-1038 pattern + colour boost: +1% growth a point (cap 15%), +0.5% walk a point (cap 7%), computed on the server (docs/186 s6, docs/157 standing rule: test builds carry the newest built features); PROVISIONAL; combat stays as it is"),
        Rule("FoodLayerEnabled", "set", True, reason="BD-1047 designed food map (spacing, fruit grove, egg meadow, lone ambers; same 3,600 foods, points and respawn; docs/187 B, docs/157 standing rule: test builds carry the newest built features); PROVISIONAL, offline evidence only, the default build keeps the old placement"),
        Rule("FoodRespawnTiersEnabled", "set", True, reason="BD-1081 respawn time by food value: berry 8 s, fruit 12 s, egg 40 s, amber 120 s, golden drumstick 150 s, so a loop on one rich food no longer pays (docs/194: the Studio test bot got 6 to 11 times the target pace; docs/157 standing rule: test builds carry the newest built features); PROVISIONAL, tune with the bot; the default build keeps the one 8 s"),
        Rule("PatternColourIndexEnabled", "set", True, reason="BD-1039 Pattern and Colour Index (docs/186 s7, docs/157 standing rule: test builds carry the newest built features); plain tinted tiles until the pattern icons exist; free eggs only, no Robux, no new saved field (the existing discovery log gains accent colours)"),
        Rule("ShopPromptBubbleEnabled", "set", True, reason="BD-1017 stall message bubble with the key E (docs/180 option A, docs/157 standing rule: test builds carry the newest built features); one press opens the existing window, no auto-open; free, no Robux; offline evidence only"),
        Rule("RareFindBannerEnabled", "set", True, reason="BD-1121 rare-find announcement with a huge outlined title and the rarity word in its colour, no panel, no player name (docs/202 R6, docs/157 standing rule: test builds carry the newest built features); free, same server limits as BD-428; offline evidence only"),
        Rule("HudRailWordsEnabled", "set", True, reason="BD-1116 HUD rail with a word on every button, bigger buttons, at most five, Settings as a gear (docs/202 R1, docs/212, docs/157 standing rule: test builds carry the newest built features); free, no Robux; offline evidence only"),
        Rule("TimerChipsEnabled", "set", True, reason="BD-1124 short timer words on the HUD, potion drain bars, big Found 1/22 bar in the Index (docs/202 R11 and R12, docs/220, docs/157 standing rule: test builds carry the newest built features); free, no Robux; offline evidence only"),
        Rule("StarterRunEnabled", "set", True, reason="BD-1163 starter run: the first run of a brand-new profile starts by itself, a card with one button ends it at 3 eggs, it settles at least 3 never-Cracked eggs exactly once, OPEN EGGS is the only button after it (owner decision 2026-11-10, docs/225, docs/157 standing rule: test builds carry the newest built features); who qualifies is read from the save, nothing new stored; free, no Robux; numbers PROVISIONAL; offline evidence only"),
        Rule("DupProgressEnabled", "set", True, reason="BD-1170 part A duplicate progress: the hatch reveal of a dino the player already has says '3 of 6 for Gold!' (count after the hatch, the Fusion Menu's own rule), the Index species page shows a progress bar whose tap opens the Fusion Menu on that dino (docs/221, docs/227, docs/157 standing rule: test builds carry the newest built features); client words only, nothing stored; free, no Robux; offline evidence only"),
        Rule("MotionPresetsEnabled", "set", True, reason="BD-1182 UI motion presets: a menu window opens in 0.3 s with a soft overshoot to 103% and closes in 0.15 s, a pressed button sinks 5 px in 80 ms and pops to 103% on release; Reduce Motion gives the end state at once (docs/228 board 6, docs/229, docs/157 standing rule: test builds carry the newest built features); client presentation only, no server, save or economy change; free, no Robux; timings PROVISIONAL; offline evidence only"),
        Rule("ToyboxUIEnabled", "set", True, reason="BD-1177 Toybox UI skin: the menu windows get a stud body, a glossy header in the colour of the place and a red gloss X, buttons become two-tone gloss buttons, outlined text is 3 px thick (owner 2026-11-14; owner decision 2026-11-13: on in the playtest profile, docs/228 board 1, docs/230, docs/157 standing rule: test builds carry the newest built features); Blender-render pictures (all 23 ids bound 2026-11-14), a group whose ids are missing keeps the old look; client presentation only, no server, save or economy change; free, no Robux; Studio evidence docs/evidence/2026-11-14-polish-loop*"),
        Rule("HatchStageEnabled", "set", True, reason="BD-1211 the hatch is a full stage over the world: no stud window, light veil with soft rays, cream chips with ink text, grey buttons, the green NEXT EGG kept (docs/240 R1-R3, R7, style tile v2 boards 2-4, owner 2026-11-15 'continue until all proposed changes are in the actual game', docs/157 standing rule); client presentation only, no server, odds or economy change; free, no Robux"),
        Rule("WorldV3Enabled", "set", True, reason="BD-1209 redesigned round island: beach and soft cliffs, paved spawn plaza, five spoke paths and a ring road, five readable zones (docs/241 W1-W3, owner 2026-11-15 'continue until all proposed changes are in the actual game', docs/157 standing rule: test builds carry the newest built features); terrain shape, ground colours and prop placement only, no save, economy or reward change; free, no Robux"),
        Rule("FoodV3Enabled", "set", True, reason="BD-1208 V3 food pickups: blueberry, raspberry, apple, orange, two spotted eggs in twig nests, two amber nuggets with fossils, generated with Roblox generate_mesh from the approved food icons (owner 2026-11-15: 'Yes, all food this way', 'Yes, wire it in'; docs/241 W6, docs/157 standing rule: test builds carry the newest built features); visual only, same kinds, points, sizes, placement and respawn; a mesh that fails to load keeps the kit mesh; free, no Robux"),
        Rule("HudCohesionEnabled", "set", True, reason="BD-1213 HUD and world labels on the approved style tile (docs/240 step 2, owner 2026-11-16: continue until all proposed changes are in the game; docs/157 standing rule: test builds carry the newest built features): cream plates with an ink outline, no debug lines, LEAP grey, key badges off the words, +3 Crystals above its amber; client presentation only, no server, save or economy change; free, no Robux"),
        Rule("MenusCohesionEnabled", "set", True, reason="BD-1237 Egg chances, the Food guide, the weather title card, the toast cards and the Fusion colour bar on the approved style rules R1-R8 (docs/240 step 4, owner 2026-11-16: continue until everything is done; docs/157 standing rule: test builds carry the newest built features): cream panels with ink words, kid chances with the exact numbers one tap away, grey buttons, the real V3 food meshes, a white weather word with its icon, cream toasts; client presentation only, no server, save, odds or economy change; free, no Robux"),
        Rule("ScreensCohesionEnabled", "set", True, reason="BD-1214 Run complete, Home (Sanctuary), the Welcome steps and the Loading screen on the approved style rules R1-R8 (owner 2026-11-15/16: one cohesive game, style tile docs/240 approved; docs/157 standing rule: test builds carry the newest built features): cream panels with an ink outline, one green main button, real pictures only, the 28/20/16/14 type scale, kid copy, a warm green loading screen; client presentation only, no server, save or economy change; free, no Robux"),
        Rule("AudioPolishEnabled", "set", True, reason="BD-1218 + BD-1219 (docs/242 benchmark, owner 2026-11-16: compare every aspect with famous Roblox games, sound included; docs/157 standing rule: test builds carry the newest built features): calm looping music on the island and at home and a softer bed under the hatch, crossfaded; sounds for the 14 silent Sfx slots, a soft window pop, soft defeat and nest-open cues, soft dino footsteps by surface; client sound only, no server, save or economy change; Roblox-licensed Creator Store audio (APMOfficial, ProSoundEffects, docs/77); unheard by agents; free, no Robux"),
        Rule("IndexMilestonesEnabled", "set", True, reason="BD-1230 (docs/242 benchmark gap 15, owner 2026-11-16: continue until all new proposed changes are in the actual game; docs/157 standing rule: test builds carry the newest built features): the Dino Index pays free crystals once at 25 / 50 / 75 / 100 % of the species found (PROVISIONAL 50 / 100 / 200 / 500, LEAD decision docs/115), inside the hatch transaction that reaches the step (exactly once), stored in the additive profile field indexMilestones; the Index bar says how many more dinos to the next reward and a toast celebrates it; free, no Robux, no paid or random item"),
        Rule("PlayCuesEnabled", "set", True, reason="BD-1226 + BD-1231 + BD-1234 (docs/242 benchmark, owner 2026-11-16: continue until all new proposed changes are in the actual game; docs/157 standing rule: test builds carry the newest built features): a bobbing chip on the first food, the ready nest and a stall for a new player; a calm '+N' at the dino when it eats and one word banner per SIZE quarter (Reduce Motion respected); a toast and a number badge on EGGS when a nest egg finishes during play, in game only; client presentation only, no server, save or economy change; free, no Robux"),
        Rule("RealSeaEnabled", "set", True, reason="BD-1220 real sea (docs/242 benchmark gap 5, rule W9 no haze, owner 2026-11-16: continue until all proposed changes are in the game; docs/157 standing rule: test builds carry the newest built features): terrain water to the horizon with a deeper floor, no square ocean plate, thinner clear-day Atmosphere, clear fog opens while the camera is high; terrain and lighting only, no save, economy or reward change; free, no Robux"),
        Rule("ToonWorldEnabled", "set", True, reason="BD-1223 + BD-1224 one toy style (docs/242 benchmark gaps 8 and 9, owner 2026-11-16: continue until all proposed changes are in the game; docs/157 standing rule: test builds carry the newest built features): flat toon ground colours instead of the photo textures, round glossy bushes instead of the spiky ferns and horsetail; look and placement only, no save, economy or reward change; free, no Robux"),
        Rule("FoodHostsEnabled", "set", True, reason="BD-1238 food at matching hosts (docs/241 W6 + W7, owner 2026-11-16: continue until everything is done; docs/157 standing rule: test builds carry the newest built features): berries at the rim of the round bushes, fruit under the tree crowns, amber against rocks and landmark edges, eggs in their twig nests against rocks and tree feet; the same 3,600 foods, kinds, points and per-zone counts, no new parts; free, no Robux"),
        Rule("VegetationV2Enabled", "set", True, reason="BD-1239 vegetation v2 (owner 2026-11-16: 'vegetation looks cheap', approved the concept sheet: 'Yes, build all'; docs/157 standing rule: test builds carry the newest built features): the island plants show the generated toy family (flower, fruit and twisty trees, pines, palms, red, blue and grape berry bushes as the berry hosts, flower clusters, soft grass clumps, ferns, mossy rocks), no flat spiky grass tufts, thinner ground cover; look only, no save, economy or reward change; free, no Robux"),
        Rule("IslandLifeEnabled", "set", True, reason="BD-1244 life on the island (owner 2026-11-16: 'game still looks empty', 'Yes, build all'; docs/157 standing rule: test builds carry the newest built features): butterfly flocks, dragonflies at the water, gulls circling high and small wild baby dinos grazing near the paths (V3 low-poly dinos, BD-1217 clips); client-only, never catchable; look only, no save, economy or reward change; free, no Robux"),
        Rule("WarmLightEnabled", "set", True, reason="BD-1247 warmer light and atmosphere (owner 2026-11-16: 'game still looks empty', 'Yes, build all'; docs/157 standing rule): warm colour grade, gentle bloom, soft sun rays and slow pollen motes per zone in clear weather on the island; look only, no save, economy or reward change; free, no Robux"),
        Rule("GroundDetailEnabled", "set", True, reason="BD-1245 path and ground detail (owner 2026-11-16: 'game still looks empty', 'Yes, build all'; docs/157 standing rule: test builds carry the newest built features): a darker grass lip along the paths and soft grass and earth patches (terrain only), generated edge stones, pebbles and a log along each spoke, flower patches in the open grass, fewer single ground cover clumps (fewer parts near spawn); look only, no save, economy or reward change; free, no Robux"),
        Rule("ThingsToDoEnabled", "set", True, reason="BD-1246 something to do in every view (owner 2026-11-16: 'game still looks empty', 'Yes, build all'; docs/157 standing rule: test builds carry the newest built features): food clusters along the first stretch of each spoke path moved inside the food map grid from the far side of the same zone (same foods, kinds, points and per-zone counts) with farther food glow, and one generated set piece per spoke (egg nest, signpost, campfire, log jetty, fossil dig); no save, economy or reward change; free, no Robux"),
        Rule("PlazaHubEnabled", "set", True, reason="BD-1221 spawn plaza hub (docs/242 benchmark gap 4, owner 2026-11-16: continue until all proposed changes are in the game; docs/157 standing rule: test builds carry the newest built features): four stalls with big signs on the plaza (the cave home's own generated meshes), walk-up prompts open the screens through the rail's own path; no save, economy or reward change; free, no Robux"),
        Rule("BlobShadowEnabled", "set", True, reason="BD-1261 soft blob shadow (owner 2026-11-17 phone test: 'dino shadows are really low quality'; new phone UI standard approved 'Yes, build it', first slice; docs/157 standing rule: test builds carry the newest built features): one soft blob decal (Roblox's built-in glow texture) under each dino instead of three stacked discs, 1 part instead of 3; client presentation only, no save, economy or reward change; free, no Robux"),
        Rule("PlazaShopsV2Enabled", "set", True, reason="BD-1248 plaza shops v2 (owner 2026-11-16: 'not what famous roblox experiences do with their 3d shops and texts', concept approved 'Yes, build them'; docs/157 standing rule: test builds carry the newest built features): the four plaza stalls become themed generated shop buildings with ONE big wooden signboard each (word and icon on the board face, no floating words) and a small low-poly dino shopkeeper; same spots, prompts and At home rule; no save, economy or reward change; free, no Robux"),
        Rule("RareHatchNewsEnabled", "set", True, reason="BD-1227 rare hatch news with the hatcher's display name, Epic and up, one chat line (docs/242 gap 17) (owner 2026-11-16: continue until all proposed changes are in the actual game; docs/157 standing rule: test builds carry the newest built features); free, no Robux, no paid line"),
        Rule("FriendBonusEnabled", "set", True, reason="BD-1228 friend bonus: +10% run crystals while a Roblox friend is in the server, HUD chip (docs/242 gap 17) (owner 2026-11-16: continue until all proposed changes are in the actual game; docs/157 standing rule: test builds carry the newest built features); free, no Robux, no paid line"),
        Rule("BadgesEnabled", "set", True, reason="BD-1229 BadgeService awards from the badge-id table; ids empty until the owner creates the badges (docs/242 gap 18) (owner 2026-11-16: continue until all proposed changes are in the actual game; docs/157 standing rule: test builds carry the newest built features); free, no Robux, no paid line"),
        Rule("CodesEnabled", "set", True, reason="BD-1233 code box and group gift chest, free crystals once per player, additive redeemedCodes field (docs/242 gap 18) (owner 2026-11-16: continue until all proposed changes are in the actual game; docs/157 standing rule: test builds carry the newest built features); free, no Robux, no paid line"),
        Rule("ZoneAmbienceEnabled", "set", True, reason="BD-1225 soft ambient loop per World V3 zone, crossfaded, ambience volume group (docs/242 gap 14) (owner 2026-11-16: continue until all proposed changes are in the actual game; docs/157 standing rule: test builds carry the newest built features); free, no Robux, no paid line"),
        Rule("DinoRigClipsEnabled", "set", True, reason="BD-1217 (docs/242 benchmark gap 2, owner 2026-11-16: continue until all new proposed changes are in the actual game; docs/157 standing rule: test builds carry the newest built features): the low-poly dinos move with authored idle / walk / run / hop clips plus tail and head follow-through, and the hidden avatar's default Animate script is off; client presentation only, no server, save or economy change; free, no Robux"),
        Rule("LoadingSceneEnabled", "set", True, reason="BD-1232 (docs/242 benchmark gap 17, owner 2026-11-16: continue until all new proposed changes are in the actual game; docs/157 standing rule: test builds carry the newest built features): the warm loading screen shows real scene art (the owner-approved Blender render egg_stage_jungle, uploaded and checked loaded in Studio), one short kid tip at a time and a grey Skip once the save has loaded; client presentation only, no server, save or economy change; free, no Robux"),
        Rule("HatchFastCommonsEnabled", "set", True, reason="BD-1164 hatch pacing: Common and Uncommon eggs of a batch reveal in about 1 s each and move on by themselves, Rare and up keep the full slow show, the first 3 eggs of a brand-new save too (owner decision 2026-11-10, docs/226, docs/157 standing rule: test builds carry the newest built features); client presentation only, no server, odds or economy change; free, no Robux; timings PROVISIONAL; offline evidence only"),
        Rule("WelcomeBackEnabled", "set", True, reason="BD-1168 welcome-back toast card at join when a nest finished while the player was away, tap opens the Nests screen (docs/221, docs/223, docs/157 standing rule: test builds carry the newest built features); the server counts, nothing stored; free, no Robux; offline evidence only"),
        Rule("PlayAgainEnabled", "set", True, reason="BD-1199 PLAY AGAIN (big green) and HOME after the last egg of a hatch, started through the normal run-start remote, plus a gentle run streak 1..5 (window 120 s, bonus 0/5/10/15/20 crystals paid in the existing settlement, session-only, nothing saved) (docs/235, docs/239, docs/157 standing rule: test builds carry the newest built features); no timer, no auto-start; free, no Robux; numbers PROVISIONAL; offline evidence only"),
        Rule("ShopCardPriceButtonEnabled", "set", True, reason="BD-1118/BD-1144 Aura and Trail shop card with the price on the one wide button, details behind Info (docs/202 R3, docs/213, docs/157 standing rule: test builds carry the newest built features); the same confirm page before any purchase; free, no Robux; offline evidence only"),
        Rule("FastTravelPerk", "set", True, reason="BD-391/405 fast travel as a crystal perk (owner decision D22, docs/115; price PROVISIONAL, no Robux); needs CaveHub, which the playtest sets"),
        Rule("SecretSpeciesEnabled", "set", True, reason="BD-604/BD-228/BD-606 secret silly creatures in the test build (owner directive 2026-10-18, docs/173): only species whose model slot holds a real published id can drop (all seven since the 2026-10-18 second binding round, docs/173); free run and nest eggs only, never a shop or paid egg (docs/43)"),
        _flag_off("FoodPickupAtMouth", "docs/115 MR6 + BD-527: eating at the mouth changes the egg pace (+18..37 percent); the owner said keep the pacing until a real LastRunFood log exists (docs/157)"),
        _flag_off("AutoOpenRequiresPass", "locks the auto-open setting behind a game pass: a Robux line, off in every build (docs/157)"),
        _flag_off("PredationAtMouth", "BD-515: shares the BD-527 pace decision and is inert while CombatEnabled is on (docs/152 finding 5)"),
        # Future fusion/menu release keys (BD-064/BD-065) go here, e.g.
        # Rule("<FusionFlagName>", "set", True, missing="warn", reason="BD-064 fusion server"),
    ],
}


# The playtest-streaming scratch profile is the playtest with Workspace streaming ON (radii 256 / 128: LEAD decision ST4, docs/115 and docs/147 s9). It is for Studio
# sessions of the BD-502 gates only: never published, never uploaded by CI. ReleaseProfile stays "playtest" so the game behaves as in
# the playtest build.
PROFILES["playtest-streaming"] = list(PROFILES["playtest"])

# The all-on-rehearsal scratch profile (docs/152) is the playtest with EVERY built-but-off gameplay flag ON at once, so the offline
# suites can be run against the combined Config (tools/run_rehearsal.py). It is never built into a published place and never
# uploaded; it is not a shipped profile (its Streaming entry is scratch, which is how release_playtest.shipped_profiles and the
# shipped-profile hard stops skip it). It keeps the paid/Robux line closed: CrystalPacksEnabled and PaidRandomItemsEnabled stay
# required-false, so no Robux product can sell and no paid random item can exist even in the rehearsal. Test/demo/QA/preview
# switches (grants, harnesses, QA overlay, DemoDirector, HatchV2Preview) are not gameplay and stay required-false too.
# A new built-but-off flag must be added here (or to EXCLUDED in tools/verify_switch_on.py, with a reason): that check fails until it is.
REHEARSAL_ON = [
    ("ObjectivesEnabled", "BD-072..077 mini objectives"),
    ("GiftClaimEnabled", "BD-451 gift claim path"),
    ("AdminGiftsEnabled", "BD-451/452 free admin gifts"),
    ("GiftingEnabled", "BD-451/453 gift sender flag (Robux sender not built; no product is sold while CrystalPacksEnabled is false)"),
    ("FoodPickupAtMouth", "BD-515 eating at the mouth"),
    ("PredationAtMouth", "BD-515 predation at the mouth"),
    ("CombatEnabled", "BD-243 HP combat"),
    ("SpecialFoodsEnabled", "BD-207 rare special foods"),
    ("PerDinoCosmeticsEnabled", "BD-059 per-dino cosmetics"),
    ("FastTravelPerk", "BD-391/405 fast travel perk"),
    ("GeneBoostEnabled", "BD-1038 pattern + colour boost"),
    ("FoodLayerEnabled", "BD-1047 designed food map"),
    ("FoodRespawnTiersEnabled", "BD-1081 respawn time by food value"),
    ("PatternColourIndexEnabled", "BD-1039 Pattern and Colour Index"),
    ("RareFindBannerEnabled", "BD-1121 rare-find announcement: huge title, coloured rarity word, no panel"),
    ("HudRailWordsEnabled", "BD-1116 HUD rail with a word on every button, at most five buttons"),
    ("ShopCardPriceButtonEnabled", "BD-1118/BD-1144 shop card with the price on the button, details behind Info"),
    ("TimerChipsEnabled", "BD-1124 short timer words, potion drain bars, big Index count bar"),
    ("StarterRunEnabled", "BD-1163 starter run: auto-start, card at 3 eggs, egg floor and safe eggs for the first run of a new save"),
    ("DupProgressEnabled", "BD-1170 part A duplicate progress: '3 of 6 for Gold!' on the hatch reveal and the Index species page"),
    ("MotionPresetsEnabled", "BD-1182 UI motion presets: window open and close, button press sink and pop"),
    ("ToyboxUIEnabled", "BD-1177 Toybox UI skin: stud window, glossy header per place, red gloss X, gloss buttons, 3..4 px text outline"),
    ("FoodV3Enabled", "BD-1208 V3 food pickups from the approved food icons"),
    ("WorldV3Enabled", "BD-1209 redesigned round island: beach, plaza, paths, ring road, five zones"),
    ("HatchStageEnabled", "BD-1211 hatch as a full stage over the world in the one style"),
    ("HudCohesionEnabled", "BD-1213 HUD and world labels on the style rules R1-R8"),
    ("MenusCohesionEnabled", "BD-1237 Egg chances, Food guide, weather card, toasts and Fusion bar on the style rules"),
    ("ScreensCohesionEnabled", "BD-1214 Run complete, Home, Welcome and Loading on the style rules"),
    ("AudioPolishEnabled", "BD-1218 + BD-1219 music beds, sounds for the silent cues, dino footsteps"),
    ("IndexMilestonesEnabled", "BD-1230 Dino Index milestone rewards (free crystals at 25 / 50 / 75 / 100 %)"),
    ("PlayCuesEnabled", "BD-1226 + BD-1231 + BD-1234 point-at chips, growth number pop, egg-ready toast and badge"),
    ("RealSeaEnabled", "BD-1220 real sea to the horizon, less haze from above"),
    ("ToonWorldEnabled", "BD-1223 + BD-1224 flat toon ground, round bushes instead of spiky ferns"),
    ("FoodHostsEnabled", "BD-1238 berries on bushes, fruit under trees, amber and eggs at rocks and landmarks"),
    ("VegetationV2Enabled", "BD-1239 vegetation v2: toy trees, berry bushes, flowers, grass clumps, ferns, mossy rocks"),
    ("IslandLifeEnabled", "BD-1244 life on the island: butterflies, dragonflies, gulls, wild baby dinos"),
    ("WarmLightEnabled", "BD-1247 warm light: colour grade, bloom, sun rays, pollen motes"),
    ("GroundDetailEnabled", "BD-1245 path and ground detail: grass lip, ground patches, edge stones, pebbles, logs, flower patches"),
    ("ThingsToDoEnabled", "BD-1246 food along the spoke paths and one set piece per spoke"),
    ("PlazaHubEnabled", "BD-1221 spawn plaza hub: stalls with big signs"),
    ("PlazaShopsV2Enabled", "BD-1248 plaza shops v2: themed shop buildings, one signboard each, dino shopkeepers"),
    ("BlobShadowEnabled", "BD-1261 soft blob shadow: one glow decal per dino instead of three discs"),
    ("RareHatchNewsEnabled", "BD-1227 rare hatch news with the hatcher's display name, Epic and up, one chat line (docs/242 gap 17)"),
    ("FriendBonusEnabled", "BD-1228 friend bonus: +10% run crystals while a Roblox friend is in the server, HUD chip (docs/242 gap 17)"),
    ("BadgesEnabled", "BD-1229 BadgeService awards from the badge-id table; ids empty until the owner creates the badges (docs/242 gap 18)"),
    ("CodesEnabled", "BD-1233 code box and group gift chest, free crystals once per player, additive redeemedCodes field (docs/242 gap 18)"),
    ("ZoneAmbienceEnabled", "BD-1225 soft ambient loop per World V3 zone, crossfaded, ambience volume group (docs/242 gap 14)"),
    ("LoadingSceneEnabled", "BD-1232 loading scene art, rotating kid tip, late Skip"),
    ("DinoRigClipsEnabled", "BD-1217 authored dino locomotion clips, follow-through, default Animate off"),
    ("HatchFastCommonsEnabled", "BD-1164 hatch pacing: fast Common and Uncommon eggs in a batch, full show for Rare and up"),
    ("WelcomeBackEnabled", "BD-1168 welcome-back card at join when a nest finished while away"),
    ("PlayAgainEnabled", "BD-1199 PLAY AGAIN button and gentle run streak"),
    ("ShopPromptBubbleEnabled", "BD-1017 stall message bubble with the key E"),
    ("HatchV2", "BD-397 v2 hatch (falls back to v1 per egg)"),
    ("SecretSpeciesEnabled", "BD-604/BD-228 secret silly creatures (a secret hatches only once its model slot is filled)"),
    ("DinoSkinsEnabled", "BD-456 dino skins data model and equip (shares profile.ownedSkins with gifting)"),
]
_REHEARSAL_ON_KEYS = {key for key, _ in REHEARSAL_ON}

# The second scratch variant (BD-626) turns on everything the first one does EXCEPT these, which it keeps OFF (the playtest profile sets CombatEnabled on since docs/157).
# CombatEnabled replaces the instant bigger-eats-smaller rule, and PredationService returns at once while combat is on, so the
# all-on build can never prove PredationAtMouth: the no-combat variant exists to run that rule (docs/152 s9).
NO_COMBAT_OFF = {"CombatEnabled": "BD-243 HP combat replaces instant predation; with it on PredationAtMouth is inert, so this variant keeps it off to exercise the mouth rule"}


def _rehearsal_rules(keep_off: dict[str, str] | None = None) -> list[Rule]:
    keep_off = keep_off or {}
    rules: list[Rule] = []
    for rule in PROFILES["playtest"]:
        if rule.key in _REHEARSAL_ON_KEYS and rule.mode in ("require", "set"):
            continue  # the playtest pins these off (or, since docs/157, already sets some on); the rehearsal states them once, below (unless the variant keeps the flag off)
        if rule.key in ("PlaytestUniverseId", "PlaytestPlaceId") and rule.mode == "check":
            rules.append(Rule(rule.key, "check", predicate=_id_or_zero, reason="rehearsal: BD-004 ids are not needed offline"))
            continue
        rules.append(rule)
    rules.extend(Rule(key, "set", True, reason=f"rehearsal: {why}") for key, why in REHEARSAL_ON if key not in keep_off)
    rules.extend(Rule(key, "require", False, reason=f"rehearsal variant: {why}") for key, why in keep_off.items())
    return rules


PROFILES["all-on-rehearsal"] = _rehearsal_rules()
PROFILES["all-on-no-combat"] = _rehearsal_rules(NO_COMBAT_OFF)

STREAMING: dict[str, Streaming] = {
    "default": Streaming(),
    "playtest": Streaming(),
    "playtest-streaming": Streaming(enabled=True, target_radius=256, min_radius=128, scratch=True),
    "all-on-rehearsal": Streaming(enabled=True, target_radius=256, min_radius=128, scratch=True),
    "all-on-no-combat": Streaming(enabled=True, target_radius=256, min_radius=128, scratch=True),
}


def streaming_for(profile: str) -> Streaming:
    return STREAMING.get(profile, Streaming())


def streaming_config_errors(profile: str, root: Any = None) -> list[str]:
    """Static rules for the profile's streaming setting (BD-502 gate 4)."""
    from pathlib import Path
    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    setting = streaming_for(profile)
    errors: list[str] = []
    if setting.integrity_mode not in STREAMING_INTEGRITY_MODES:
        errors.append(f"streaming integrity mode {setting.integrity_mode!r} is unknown (choose from {sorted(STREAMING_INTEGRITY_MODES)})")
    for label, value in (("target", setting.target_radius), ("min", setting.min_radius)):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            errors.append(f"streaming {label} radius must be a positive integer, got {value!r}")
    if not errors and setting.min_radius > setting.target_radius:
        errors.append(f"streaming min radius {setting.min_radius} is above the target radius {setting.target_radius}")
    if setting.enabled and not setting.scratch:
        match = STREAMING_GATE_PATTERN.match(setting.gate)
        if not match:
            errors.append(f"profile {profile!r} turns StreamingEnabled ON but is a shipped profile without a gate field "
                          "('BD-502:docs/<evidence file>'): shipped profiles keep streaming OFF until the BD-502 gates are met")
        elif not (root / match.group(1)).is_file():
            errors.append(f"profile {profile!r}: streaming gate evidence {match.group(1)} does not exist")
    if setting.scratch and profile in ("default", "playtest"):
        errors.append(f"profile {profile!r} is shipped and cannot be marked scratch")
    return errors


def workspace_properties(profile: str) -> list[tuple[str, str, str]]:
    """(xml tag, property name, text) triples the build writes onto the Workspace item. Empty = the place is unchanged (streaming off)."""
    setting = streaming_for(profile)
    if not setting.enabled:
        return []
    return [("bool", "StreamingEnabled", "true"),
            ("int", "StreamingTargetRadius", str(setting.target_radius)),
            ("int", "StreamingMinRadius", str(setting.min_radius)),
            ("token", "StreamingIntegrityMode", str(STREAMING_INTEGRITY_MODES[setting.integrity_mode]))]


def rules_for(profile: str) -> list[Rule]:
    if profile not in PROFILES:
        raise KeyError(f"Unknown release profile {profile!r}; choose from {sorted(PROFILES)}")
    return PROFILES[profile]


# ---------------------------------------------------------------- Config parsing
_TOP_LEVEL = re.compile(r"^    ([A-Za-z_][A-Za-z0-9_]*) = (.*?),?[ \t]*(--.*)?$")


def parse_literal(text: str) -> Any:
    text = text.strip().rstrip(",").strip()
    if text == "true":
        return True
    if text == "false":
        return False
    if re.fullmatch(r"-?[0-9]+", text):
        return int(text)
    if re.fullmatch(r"-?[0-9]*\.[0-9]+", text):
        return float(text)
    match = re.fullmatch(r'"((?:[^"\\]|\\.)*)"', text)
    if match:
        return match.group(1)
    if text.startswith("{") and text.endswith("}"):
        inner = text[1:-1].strip()
        return {} if not inner else RawLiteral(text)
    return RawLiteral(text)


class RawLiteral(str):
    """A value the release tooling does not interpret (expressions, tables)."""


def config_entries(source: str) -> dict[str, list[tuple[int, Any]]]:
    """Top-level `Key = value` lines (4-space indent) -> [(line index, value)]."""
    entries: dict[str, list[tuple[int, Any]]] = {}
    for index, line in enumerate(source.splitlines()):
        match = _TOP_LEVEL.match(line)
        if match:
            entries.setdefault(match.group(1), []).append((index, parse_literal(match.group(2))))
    return entries


def format_literal(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        if '"' in value or "\\" in value or "\n" in value:
            raise ValueError(f"Unsupported string literal: {value!r}")
        return f'"{value}"'
    raise ValueError(f"Unsupported literal: {value!r}")


@dataclass
class Report:
    errors: list[str]
    warnings: list[str]
    applied: dict[str, Any]

    @property
    def ok(self) -> bool:
        return not self.errors


def apply_profile(source: str, profile: str) -> tuple[str, Report]:
    """Return (rewritten Config source, report). Never raises for rule failures."""
    report = Report([], [], {})
    lines = source.splitlines(keepends=True)
    entries = config_entries(source)
    for key, found in entries.items():
        if len(found) > 1:
            report.errors.append(f"{key}: defined {len(found)} times in Config (later definitions silently win)")
    for rule in rules_for(profile):
        if rule.mode != "set":
            continue
        if rule.key not in entries:
            _missing(report, rule)
            continue
        value = rule.value
        if rule.from_key is not None:
            if rule.from_key not in entries:
                report.errors.append(f"{rule.key}: source key {rule.from_key} is missing from Config")
                continue
            value = entries[rule.from_key][-1][1]
        index = entries[rule.key][-1][0]
        line = lines[index]
        match = _TOP_LEVEL.match(line.rstrip("\r\n"))
        assert match is not None
        newline = line[len(line.rstrip("\r\n")):]
        comment = f" {match.group(3)}" if match.group(3) else ""
        lines[index] = f"    {rule.key} = {format_literal(value)},{comment}{newline}"
        report.applied[rule.key] = value
    rewritten = "".join(lines)
    verified = verify_source(rewritten, profile)
    report.errors.extend(e for e in verified.errors if e not in report.errors)
    report.warnings.extend(w for w in verified.warnings if w not in report.warnings)
    return rewritten, report


def _missing(report: Report, rule: Rule) -> None:
    message = (f"{rule.key}: missing from src/shared/Config.luau ({rule.reason}); "
               "add it as a top-level key or update tools/release_profiles.py")
    (report.warnings if rule.missing == "warn" else report.errors).append(message)


def verify_source(source: str, profile: str) -> Report:
    """Check a Config source against every rule of the profile."""
    report = Report([], [], {})
    entries = config_entries(source)
    for key, found in entries.items():
        if len(found) > 1:
            report.errors.append(f"{key}: defined {len(found)} times in Config (later definitions silently win)")
    seen_missing = set()
    for rule in rules_for(profile):
        if rule.key not in entries:
            if rule.key not in seen_missing:
                seen_missing.add(rule.key)
                _missing(report, rule)
            continue
        actual = entries[rule.key][-1][1]
        if rule.mode == "require" and actual != rule.value or rule.mode == "set" and rule.from_key is None and actual != rule.value:
            report.errors.append(f"{rule.key} = {actual!r}; profile {profile!r} requires {rule.value!r} ({rule.reason})")
        elif rule.mode == "set" and rule.from_key is not None:
            expected = entries.get(rule.from_key, [(0, None)])[-1][1]
            if actual != expected:
                report.errors.append(f"{rule.key} = {actual!r}; profile {profile!r} requires the value of {rule.from_key} ({expected!r})")
        elif rule.mode == "check" and rule.predicate is not None:
            problem = rule.predicate(actual)
            if problem:
                report.errors.append(f"{rule.key} = {actual!r}: {problem}")
    products = entries.get("DeveloperProducts", [(0, None)])[-1][1]
    if profile != "default" and products not in (None, {}):
        report.warnings.append(
            "DeveloperProducts still lists Robux product IDs: sales prompts stay hidden while "
            "CrystalPacksEnabled=false, random crystal items stay blocked while PaidRandomItemsEnabled=false, "
            "and the IDs are inert in any experience that does not own them. Do not create developer products "
            "in the playtest experience.")
    return report
