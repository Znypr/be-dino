"""Tier coat templates (docs/115 "fused tier look", approach C).

A SurfaceAppearance made by a script at runtime does not render in Roblox; one authored in the place (edit time) and cloned does.
So tools/build.py writes ReplicatedStorage.TierCoatTemplates at build time, from the plain-literal table `Tier.Maps` in
src/shared/LowPolyTier.luau, and LowPolyDinos only clones. This module is the single reader of that table (build + verifier).
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TIER_SOURCE = "src/shared/LowPolyTier.luau"
FOLDER = "TierCoatTemplates"
TIERS = ("gold", "emerald", "diamond")
ALPHA_MODE_TRANSPARENCY = 1  # Enum.AlphaMode: Overlay 0, Transparency 1, TintMask 2
ID_RE = re.compile(r"rbxassetid://[1-9][0-9]{5,18}")
_TOKEN = re.compile(r'\s*(?:(--[^\n]*)|("(?:[^"\\]|\\.)*")|([A-Za-z_][A-Za-z0-9_]*)|([{}=,]))')


def _tokens(text):
    pos = 0
    while pos < len(text):
        if not text[pos:].strip():
            return
        m = _TOKEN.match(text, pos)
        if not m:
            raise ValueError("Unsupported Luau in Tier.Maps near: " + text[pos:pos + 40].strip())
        pos = m.end()
        if m.group(1):
            continue
        yield ("str", m.group(2)[1:-1]) if m.group(2) is not None else ("name", m.group(3)) if m.group(3) else ("sym", m.group(4))


def _table(it):
    """Parse after '{' up to the matching '}'. Only `key = "string"`, `key = { ... }` and commas are supported."""
    out = {}
    while True:
        kind, val = next(it)
        if (kind, val) == ("sym", "}"):
            return out
        if (kind, val) == ("sym", ","):
            continue
        if kind != "name":
            raise ValueError(f"Tier.Maps: expected a key, got {val!r}")
        if next(it) != ("sym", "="):
            raise ValueError(f"Tier.Maps: expected '=' after {val}")
        kind2, val2 = next(it)
        if kind2 == "str":
            out[val] = val2
        elif (kind2, val2) == ("sym", "{"):
            out[val] = _table(it)
        else:
            raise ValueError(f"Tier.Maps.{val}: only string literals and tables are allowed")


def parse_maps(source):
    """Tier.Maps from the LowPolyTier.luau source: {"color": {species: {part: {tier: id}}}, "normal": id, "roughness": id, "metalness": id}."""
    m = re.search(r"^Tier\.Maps = \{", source, re.M)
    if not m:
        raise ValueError("Tier.Maps table not found")
    return _table(_tokens(source[m.end():]))


def template_name(species, part, tier):
    return f"{species}_{part}_{tier}"  # same as Tier.templateName in LowPolyTier.luau


def valid_id(value):
    return bool(ID_RE.fullmatch(value))


def templates(maps):
    """One dict per (species, part, tier) with a ColorMap id: name, ColorMap, NormalMap, RoughnessMap, MetalnessMap (None unless valid)."""
    shared = {k: maps.get(k, "") for k in ("normal", "roughness", "metalness")}
    out = []
    for species, parts in sorted(maps.get("color", {}).items()):
        for part, tiers in sorted(parts.items()):
            for tier in TIERS:
                color = tiers.get(tier, "")
                if not color:
                    continue
                if not valid_id(color):
                    raise ValueError(f"Tier.Maps.color.{species}.{part}.{tier}: malformed asset id {color!r}")
                for key, value in shared.items():
                    if value and not valid_id(value):
                        raise ValueError(f"Tier.Maps.{key}: malformed asset id {value!r}")
                out.append({
                    "name": template_name(species, part, tier), "species": species, "part": part, "tier": tier,
                    "ColorMap": color, "NormalMap": shared["normal"] or None,
                    "RoughnessMap": shared["roughness"] or None, "MetalnessMap": shared["metalness"] or None,
                })
    return out


def load_templates(root=ROOT):
    path = Path(root) / TIER_SOURCE
    return templates(parse_maps(path.read_text(encoding="utf-8"))) if path.exists() else []
