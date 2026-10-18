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
