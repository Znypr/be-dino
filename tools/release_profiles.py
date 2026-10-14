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
    _flag_off("DuplicateSettlementProbe", "historical settlement probe"),
    Rule("ProfileDataStoreName", "check", predicate=_store_name, reason="DataStore name limits"),
    Rule("PlaytestUniverseId", "check", predicate=_id_or_zero, reason="BD-004 record"),
    Rule("PlaytestPlaceId", "check", predicate=_id_or_zero, reason="BD-004 record"),
    Rule("PlaytestProfileDataStoreName", "check", predicate=_playtest_store_name, reason="isolated playtest store"),
]

# Studio-local conveniences that may stay true because the server only honours
# them in unpublished Studio (RunService:IsStudio() and game.GameId == 0).
# verify_release checks those guards still exist in source.
STUDIO_LOCAL_FLAGS = ["StudioLocalProfilesEnabled", "StudioTestWalletEnabled"]

PROFILES: dict[str, list[Rule]] = {
    "default": COMMON_RULES + [
        Rule("ReleaseProfile", "require", "development", reason="default build is a development build"),
        _flag_off("IdentityPersistentEnabled", "BD-064 persistent identities; only the playtest profile enables it"),
        _flag_off("IdentityFusionPreviewEnabled", "BD-057/BD-064 fusion; only the playtest profile enables it"),
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
        # docs/68: owner wants the new world kit and food art in the playtest. Density is a PROVISIONAL phone
        # budget: at 0.35 the kit world is ~6.3k native parts (tools/verify_world_art.py enforces <= 8,000 with food).
        Rule("WorldArtMode", "set", "BiomeKit", reason="BD-049 new trees/rocks/landmarks (docs/68)"),
        Rule("FoodArtMode", "set", "Kit", reason="BD-050 food variants (docs/68)"),
        Rule("WorldArtDensity", "set", 0.35, reason="PROVISIONAL phone part budget (docs/68)"),
        # Future fusion/menu release keys (BD-064/BD-065) go here, e.g.
        # Rule("<FusionFlagName>", "set", True, missing="warn", reason="BD-064 fusion server"),
    ],
}


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
