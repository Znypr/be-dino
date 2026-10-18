#!/usr/bin/env python3
"""BD-1052 (docs/188): write the team catalogue as generated Markdown under docs/catalog/.

    python tools/build_catalog.py                 # writes docs/catalog/*.md (the team catalogue, committed)
    python tools/build_catalog.py --public        # player-safe copy in build/catalog-public (no secrets, nothing behind an off flag,
                                                  # provisional odds hidden); never written to docs/catalog
    python tools/build_catalog.py --check         # same as tools/verify_catalog.py: fail when docs/catalog is stale

Every number comes from the real Luau data modules (pinned runner, tools/catalog_dump.luau), flag states from
tools/release_profiles.py and pictures from the tracked files of the repository. Nothing is typed in by hand, so the pages cannot
drift from the game. Six pages (hard cap 8, docs/188): every item is a SECTION with an anchor, never a page of its own.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog_core as core  # noqa: E402
from catalog_core import Files, Gaps, kebab, num, one_in, pct, plus, table, title_from_id  # noqa: E402

ROOT = core.ROOT
MAX_PAGES = 8
PAGE_ORDER = ["Home", "Dinosaurs", "Eggs-and-looks", "Mutations-and-fusion", "Shop-items", "World-and-food"]
PAGE_TITLES = {
    "Home": "Be Dino! team catalogue",
    "Dinosaurs": "Dinosaurs",
    "Eggs-and-looks": "Eggs and looks",
    "Mutations-and-fusion": "Mutations and fusion",
    "Shop-items": "Shop items",
    "World-and-food": "World and food",
}
DEFAULT_OUT = "docs/catalog"
PUBLIC_OUT = "build/catalog-public"
HIDDEN = "not published yet"

# Odds and numbers whose source file says PROVISIONAL. {key: (file, text that stands next to the word PROVISIONAL)}.
# tests/test_catalog.py checks that every marker is still in the file, so a removed comment is noticed.
PROVISIONAL = {
    "species": ("src/shared/Config.luau", "PROVISIONAL base species weights"),
    "run boost": ("src/shared/Config.luau", "PROVISIONAL run-size species boost"),
    "conditions": ("src/shared/ProgressionConfig.luau", "PROVISIONAL monotonic"),
    "nests": ("src/shared/Config.luau", "Egg Nests v2"),
    "secret": ("src/shared/SecretSpeciesConfig.luau", "Every number is PROVISIONAL"),
    "potions": ("src/shared/ProgressionConfig.luau", "PROVISIONAL rotating Potion Shop"),
    "fusion odds": ("src/server/FusionOdds.luau", "PROVISIONAL"),
    "event mutations": ("src/shared/ProgressionConfig.luau", "Provisional event mutation perks"),
    "food": ("src/shared/Config.luau", "FoodCatchRate = 12 / 500, -- PROVISIONAL"),
    "special food": ("src/shared/Config.luau", "BD-207: rare special foods. All PROVISIONAL"),
}
TIER_NAMES_FALLBACK = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"]
FLAG_OF_SECTION = {"secret": "SecretSpeciesEnabled", "special food": "SpecialFoodsEnabled", "fusion": "IdentityFusionPreviewEnabled",
                   "cave hub": "CaveHub"}


class Ctx:
    def __init__(self, root: Path, runner: str, public: bool, out_dir: Path):
        self.root = root
        self.public = public
        self.out_dir = out_dir
        dump = core.dump_data(root, runner)
        self.d: dict[str, Any] = dump["data"]
        self.calls: dict[str, Any] = dump["calls"]
        self.files = Files(root)
        self.flags = core.flag_states(root)
        self.gaps = Gaps()
        self.docs77 = (root / "docs/77-asset-registry.md").read_text(encoding="utf-8")
        self.config: dict[str, Any] = self.d["Config"]
        self.prog: dict[str, Any] = self.d["ProgressionConfig"]
        names = (self.d.get("RarityCurve") or {}).get("Names") or TIER_NAMES_FALLBACK
        self.tier_names: list[str] = list(names)

    # -- paths and links
    def up(self, repo_path: str) -> str:
        """Path of a repository file as seen from the folder the pages are written to."""
        return Path(os.path.relpath(self.root / repo_path, self.out_dir)).as_posix()

    def image(self, repo_path: str, alt: str, width: int = 160) -> str:
        return f'<img src="{self.up(repo_path)}" alt="{alt}" width="{width}">'

    def link(self, repo_path: str, label: Optional[str] = None) -> str:
        return f"[{label or repo_path}]({self.up(repo_path)})"

    # -- flags and provisional
    def flag_on_default(self, flag: str) -> bool:
        return self.flags.get(flag, {}).get("default") is True

    def shown(self, flag: Optional[str]) -> bool:
        """Public pages drop everything behind a flag that is off in the default build."""
        return not self.public or flag is None or self.flag_on_default(flag)

    def flag_note(self, flag: str) -> str:
        state = self.flags.get(flag)
        if not state:
            return ""
        def word(v: Any) -> str:
            return "on" if v is True else "off" if v is False else "not set"
        return f"Switch: {word(state['default'])} in the default build, {word(state['playtest'])} in the playtest build."

    def hide(self, text: str, provisional_key: Optional[str]) -> str:
        return HIDDEN if self.public and provisional_key in PROVISIONAL else text

    def prov_mark(self, key: str) -> str:
        return " (PROVISIONAL)" if key in PROVISIONAL and not self.public else ""

    # -- pictures
    def registered(self, repo_path: str) -> bool:
        return repo_path in self.docs77 or repo_path.rsplit("/", 1)[-1] in self.docs77

    def find_picture(self, category: str, item: str, anchor: str, candidates: list[str], deliver: str, kind: str = "picture",
                     standin_basenames: tuple[str, ...] = (), what: str = "") -> Optional[str]:
        """First existing candidate (a 'stem' without extension picks its newest -vN file). Adds a gap when none exists."""
        for candidate in candidates:
            found = self.files.has(candidate) and candidate or self.files.newest_version(re.sub(r"\.(png|jpg|jpeg|webp)$", "", candidate))
            if found:
                if not self.registered(found):
                    self.gaps.add("registry line", category, item, anchor, "picture exists but has no line in docs/77", "docs/77-asset-registry.md", found,
                                  "add one line (name, file, asset id, used by, status)")
                return found
        folder, _, name = deliver.rpartition("/")
        stand = next((p for b in standin_basenames for p in [self.files.by_basename(b)] if p), None)
        self.gaps.add(kind, category, item, anchor, what or ("no final " + kind), folder, name,
                      ("a stand-in is shown: " + stand) if stand else "")
        return stand

    def asset_id_status(self, category: str, item: str, anchor: str, value: Any, slot: str, folder_hint: str = "") -> str:
        """'bound' or a gap. value is whatever the slot module holds (string id, number or empty)."""
        text = str(value) if value not in (None, "", 0) else ""
        if text and re.search(r"\d{5,}", text):
            return "bound"
        self.gaps.add("asset id", category, item, anchor, "uploaded id not written into the slot yet", folder_hint, slot,
                      "after the upload, tools/bind_assets.py writes the id; add the docs/77 line")
        return "not bound"


# ---------------------------------------------------------------- page assembly
class Page:
    def __init__(self, name: str, intro: str):
        self.name = name
        self.title = PAGE_TITLES[name]
        self.intro = intro
        self.sections: list[tuple[str, str, str, list[tuple[str, str]]]] = []  # anchor, heading, body, items [(anchor, label)]

    def add(self, anchor: str, heading: str, body: str, items: Optional[list[tuple[str, str]]] = None) -> None:
        self.sections.append((anchor, heading, body.strip("\n"), items or []))

    def render(self, ctx: Ctx) -> str:
        out = [f"# {self.title}", "", self.intro.strip(), ""]
        out.append("Generated by `tools/build_catalog.py` from the game code. Do not edit by hand: change the code, then run "
                   "`python tools/build_catalog.py`." + (" Player-safe copy." if ctx.public else ""))
        out += ["", "## Contents", ""]
        nav = " | ".join(f"[{PAGE_TITLES[p]}]({p}.md)" if p != self.name else f"**{PAGE_TITLES[p]}**" for p in PAGE_ORDER)
        out += [f"Pages: {nav}", ""]
        for anchor, heading, _body, items in self.sections:
            out.append(f"- [{heading}](#{anchor})")
            if items:
                out.append("  " + " | ".join(f"[{label}](#{a})" for a, label in items))
        out.append("")
        for anchor, heading, body, _items in self.sections:
            out += [f'<a id="{anchor}"></a>', f"## {heading}", "", body, ""]
        return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).rstrip() + "\n"


def item_heading(anchor: str, label: str, level: int = 3) -> str:
    return f'<a id="{anchor}"></a>\n### {label}\n\n'


def tier_name(ctx: Ctx, index_zero_based: int) -> str:
    return ctx.tier_names[index_zero_based] if 0 <= index_zero_based < len(ctx.tier_names) else f"Tier {index_zero_based + 1}"


def page_ref(page: str, anchor: str = "") -> str:
    return f"{page}.md" + (f"#{anchor}" if anchor else "")


# ---------------------------------------------------------------- Dinosaurs
def build_dinosaurs(ctx: Ctx) -> Page:
    cfg, d = ctx.config, ctx.d
    order = list(cfg["SpeciesOrder"])
    names = cfg["SpeciesDisplayNames"]
    rarities = cfg["SpeciesRarities"]
    tiers = list(cfg["SpeciesRarityNames"])
    weights = {row["speciesId"]: row["weight"] for row in cfg["ChestSpeciesWeights"]}
    total = sum(weights.values())
    full = {row["speciesId"]: row["weight"] for row in ctx.calls["speciesWeightsMax"]}
    full_total = sum(full.values())
    classes = ctx.calls["classInfo"]
    sizes = d["ScaleLadder"]["Dino"]["species"]
    secret_sizes = d["ScaleLadder"]["Dino"]["secret"]["species"]
    models = d["LowPolyDinoAssets"]
    secret = d["SecretSpeciesConfig"]
    secret_ready = [i for i in secret["Order"] if isinstance(secret["Species"][i].get("assetId"), int) and secret["Species"][i]["assetId"] > 0]
    secret_weight_total = sum(secret["Species"][i]["weight"] for i in secret_ready) or 1
    show_secret = ctx.shown("SecretSpeciesEnabled")
    boost_eggs = cfg["EggRarityBoostMaxEggs"]
    page = Page("Dinosaurs", "Every dinosaur in the game with its picture, class, rarity and the chance to get it from an egg.")

    def row_of(species: str, is_secret: bool) -> dict[str, Any]:
        info = classes.get(species, {})
        if is_secret:
            row = secret["Species"][species]
            tier_text = "SECRET, internal only" if not ctx.public else "Secret"
            per_egg = secret["Chance"] * 100 * (secret["Species"][species]["weight"] / secret_weight_total) if species in secret_ready else 0.0
            return {"id": species, "name": row["name"], "class": info.get("label", row["class"]), "hint": info.get("hint", ""), "tier": tier_text,
                    "egg": per_egg, "full": per_egg, "size": secret_sizes.get(species)}
        tier = rarities[species]
        return {"id": species, "name": names[species], "class": info.get("label", "Ground"), "hint": info.get("hint", ""),
                "tier": f"{tiers[tier - 1]} (tier {tier} of {len(tiers)})", "egg": 100 * weights[species] / total,
                "full": 100 * full[species] / full_total, "size": sizes.get(species)}

    rows = [row_of(s, False) for s in order]
    secret_rows = [row_of(s, True) for s in secret["Order"]] if show_secret else []
    prov = ctx.prov_mark("species")

    # -- picture lookups (also fills the gaps list)
    def picture(row: dict[str, Any], is_secret: bool) -> Optional[str]:
        anchor = f"dino-{row['id']}"
        return ctx.find_picture("Dinosaur", row["name"], f"Dinosaurs#{anchor}", [f"resources/ui/v2/dinos/{row['id']}-v1.png"],
                                f"resources/ui/v2/dinos/{row['id']}-v1.png", standin_basenames=(f"desktop-species-{row['id']}.png",),
                                what="no dinosaur picture (final art: one clear picture of the dino, square)")

    pics = {r["id"]: picture(r, False) for r in rows}
    pics.update({r["id"]: picture(r, True) for r in secret_rows})

    # -- tier table
    tier_rows = []
    for index, name in enumerate(tiers, start=1):
        members = [r["name"] for r in rows if rarities[r["id"]] == index]
        egg_sum = sum(r["egg"] for r in rows if rarities[r["id"]] == index)
        full_sum = sum(r["full"] for r in rows if rarities[r["id"]] == index)
        tier_rows.append([name, len(members), ctx.hide(pct(egg_sum), "species"), ctx.hide(pct(full_sum), "species"), ", ".join(members)])
    body = ["Chances are per egg. \"Shop egg\" is one egg bought with crystals. \"Big run\" is the best run-size boost "
            f"(a batch of {boost_eggs} eggs or more)." + (" All species odds are PROVISIONAL (see the Config comment)." if not ctx.public else ""),
           "", table(["Rarity", "Dinos", "Shop egg", "Big run", "Which"], tier_rows)]
    page.add("rarity-tiers", "Rarity tiers", "\n".join(body))

    # -- overview table
    def overview_row(r: dict[str, Any], key: str) -> list[Any]:
        sz = r["size"]
        return [f"[{r['name']}](#dino-{r['id']})", r["class"], r["tier"], ctx.hide(pct(r["egg"]), key), ctx.hide(pct(r["full"]), key),
                f"{num(sz['height'], 3)} studs tall" if sz else "no size yet"]
    over = [overview_row(r, "species") for r in rows]
    text = f"{len(rows)} dinosaurs.\n\n" + table(["Dino", "Class", "Rarity", "Shop egg" + prov, "Big run", "Size"], over)
    if secret_rows:
        lead = "**SECRET, internal only.** " if not ctx.public else ""
        text += f"\n\n{lead}{len(secret_rows)} secret dinosaurs. The chance is per run or nest egg, never a shop egg.\n\n" + table(
            ["Dino", "Class", "Rarity", "Run or nest egg", "Same in a big run", "Size"], [overview_row(r, "secret") for r in secret_rows])
    page.add("all-dinosaurs", "All dinosaurs", text)

    # -- classes
    class_rows = []
    slots = d["AssetSlots"]["Images"]
    for cls, slot in sorted(d["ClassInfo"]["IconSlots"].items()):
        label = d["ClassInfo"]["Labels"][cls]
        img = ctx.find_picture("Class", label, "Dinosaurs#classes", [f"resources/ui/v2/icons/class-{cls.lower()}-v1.png"],
                               f"resources/ui/v2/icons/class-{cls.lower()}-v1.png", kind="icon", what="no class icon")
        asset = ctx.asset_id_status("Class", label, "Dinosaurs#classes", slots.get(slot), f"AssetSlots.Images.{slot}", "resources/ui/v2/icons")
        members = [r["name"] for r in rows + secret_rows if r["class"] == label]
        class_rows.append([label, d["ClassInfo"]["Hints"][cls], len(members), ctx.image(img, label, 48) if img else "none", asset])
    page.add("classes", "Classes", table(["Class", "What it does", "Dinos", "Icon", "Icon id"], class_rows))

    # -- status table
    status = []
    for r in rows + secret_rows:
        model = models.get(r["id"], {})
        mid = model.get("assetId")
        model_state = "bound" if isinstance(mid, int) and mid > 0 else "not bound"
        if model_state != "bound":
            ctx.gaps.add("model id", "Dinosaur", r["name"], f"Dinosaurs#dino-{r['id']}", "no model id in LowPolyDinoAssets",
                         "src/shared", "LowPolyDinoAssets.luau", "needs the generated model and a docs/77 line")
        sz = r["size"]
        if sz is None:
            ctx.gaps.add("not in code", "Dinosaur", r["name"], f"Dinosaurs#dino-{r['id']}", "no size row in ScaleLadder", "src/shared", "ScaleLadder.luau")
        status.append([f"[{r['name']}](#dino-{r['id']})", f"yes: `{pics[r['id']]}`" if pics[r["id"]] else "MISSING",
                       "model " + model_state, "n/a (procedural patterns)", "`src/shared/Config.luau` ChestSpeciesWeights" if r in rows else "`src/shared/SecretSpeciesConfig.luau`"])
    page.add("status", "Status", "**STATUS** Picture = a dino picture file in the repository. Model = the generated 3D model id is written into the code. "
             "Pictures go to `resources/ui/v2/dinos/<id>-v1.png` (square).\n\n" + table(["Dino", "Picture", "Model id", "Mask", "Odds from"], status))

    # -- one section per dino
    def dino_section(r: dict[str, Any], is_secret: bool) -> str:
        anchor = f"dino-{r['id']}"
        lines = [item_heading(anchor, r["name"])]
        lines.append(f"id: `{r['id']}`")
        lines.append("")
        pic = pics[r["id"]]
        lines.append(ctx.image(pic, r["name"], 200) if pic else "_No picture yet (see Missing on the Home page)._")
        lines.append("")
        lines.append(f"- **Class:** {r['class']}" + (f" ({r['hint']})" if r["hint"] else ""))
        lines.append(f"- **Rarity:** {r['tier']}")
        key = "secret" if is_secret else "species"
        if is_secret:
            lines.append(f"- **Chance:** {ctx.hide(pct(r['egg']), key)} of a run or nest egg ({ctx.hide(one_in(r['egg']), key)}); never from a shop egg"
                         + ("" if r["id"] in secret_ready else " (cannot drop yet: no model)"))
        else:
            lines.append(f"- **Chance per egg:** {ctx.hide(pct(r['egg']), key)} from a shop egg ({ctx.hide(one_in(r['egg']), key)}); "
                         f"{ctx.hide(pct(r['full']), key)} in a big run{ctx.prov_mark(key)}")
        sz = r["size"]
        if sz:
            lines.append(f"- **Size:** {num(sz['height'], 3)} studs tall, {num(sz['length'], 3)} long, {num(sz['width'], 3)} wide"
                         + ("" if sz.get("measured") else " (estimated, not measured in Studio)"))
        if is_secret:
            lines.append("- **Notes:** " + ("SECRET, internal only. " if not ctx.public else "") + ctx.flag_note("SecretSpeciesEnabled"))
        return "\n".join(lines)

    items = [(f"dino-{r['id']}", r["name"]) for r in rows]
    page.add("dinosaurs", "The dinosaurs", "\n\n".join(dino_section(r, False) for r in rows), items)
    if secret_rows:
        note = ("**SECRET, internal only.** " if not ctx.public else "") + "Secret species are not in the 22-species Index count. A flat chance per run or nest egg, then a pick by weight. " + ctx.flag_note("SecretSpeciesEnabled")
        page.add("secret-dinosaurs", "Secret dinosaurs", note + "\n\n" + "\n\n".join(dino_section(r, True) for r in secret_rows),
                 [(f"dino-{r['id']}", r["name"]) for r in secret_rows])
    return page


# ---------------------------------------------------------------- Eggs and looks
def build_eggs(ctx: Ctx) -> Page:
    cfg, prog, d = ctx.config, ctx.prog, ctx.d
    page = Page("Eggs-and-looks", "Egg colours, patterns and egg conditions, with how nests and hatching work. Pattern and colour tiers are "
                "being reworked (docs/186), so this page always shows the code as it is today.")
    # -- colours
    scale = prog["EggColorWeightScale"]
    colours = prog["EggColors"]
    def tier_index(c: dict[str, Any]) -> int:
        return ctx.tier_names.index(c.get("rarity", ctx.tier_names[0])) if c.get("rarity", ctx.tier_names[0]) in ctx.tier_names else 0
    ordered = sorted(colours, key=lambda c: (tier_index(c), -c["weight"]))
    tier_rows = []
    for ti, name in enumerate(ctx.tier_names):
        members = [c for c in ordered if tier_index(c) == ti]
        if members:
            tier_rows.append([name, len(members), pct(100 * sum(c["weight"] for c in members) / scale), ", ".join(c["name"] for c in members)])
    body = ["Each egg rolls two colours (main and accent), each one on its own with these chances.", "", table(["Rarity", "Colours", "Chance for one slot", "Which"], tier_rows), ""]
    status = []
    blocks = []
    for c in ordered:
        a = f"colour-{c['id']}"
        status.append([f"[{c['name']}](#{a})", "swatch drawn from the colour value", "n/a", "n/a", "`src/shared/ProgressionConfig.luau` EggColors"])
        blocks.append(item_heading(a, c["name"], 4) + f"id: `{c['id']}`\n\n- **Colour:** `{core.hex_rgb(c['rgb'])}`\n- **Rarity:** {c.get('rarity', tier_name(ctx, 0))}\n"
                      f"- **Chance for one slot:** {pct(100 * c['weight'] / scale)} ({one_in(100 * c['weight'] / scale)})")
    body += ["**STATUS** colours need no picture file; the swatch comes from the colour value in the code.", "", table(["Colour", "Picture", "Asset id", "Mask", "Odds from"], status), ""]
    body += blocks
    page.add("colours", "Colours", "\n\n".join(body), [(f"colour-{c['id']}", c["name"]) for c in ordered])

    # -- patterns
    raw = ctx.calls["patterns"]
    patterns = [{"id": p} if isinstance(p, str) else dict(p) for p in raw]
    mask_ids = set((d.get("LowPolyPattern") or {}).get("Ids") or [])
    has_weights = all("weight" in p for p in patterns)
    wsum = sum(p["weight"] for p in patterns) if has_weights else len(patterns)
    status, blocks, rows = [], [], []
    for p in patterns:
        pid = p["id"]
        a = f"pattern-{kebab(pid)}"
        name = p.get("name") or title_from_id(pid)
        chance = 100 * (p["weight"] if has_weights else 1) / wsum
        icon = ctx.find_picture("Pattern", name, f"Eggs-and-looks#{a}", [f"resources/ui/v2/patterns/{pid}-v1.png"], f"resources/ui/v2/patterns/{pid}-v1.png",
                                kind="icon", what="no pattern icon for the Index (square, black pattern on white)")
        mask = "yes (procedural mask in code)" if pid in mask_ids else "no mask in code"
        if pid not in mask_ids:
            ctx.gaps.add("mask", "Pattern", name, f"Eggs-and-looks#{a}", "no pattern mask in LowPolyPattern.Ids", "src/shared", "LowPolyPattern.luau")
        rows.append([f"[{name}](#{a})", p.get("rarity", "all the same"), pct(chance)])
        status.append([f"[{name}](#{a})", f"yes: `{icon}`" if icon else "MISSING", "no slot in code yet", mask, "`src/shared/EggGenetics.luau` Patterns"])
        blocks.append(item_heading(a, name, 4) + f"id: `{pid}`\n\n" + (ctx.image(icon, name, 120) + "\n\n" if icon else "_No icon yet (see Missing)._\n\n")
                      + f"- **Chance:** {pct(chance)} ({one_in(chance)}) per egg" + (f"\n- **Rarity:** {p['rarity']}" if "rarity" in p else "\n- **Rarity:** every pattern is equally likely today"))
    mode = ctx.calls.get("blendMode", "")
    body = [f"{len(patterns)} patterns. The two colours mix by a share from 1 to 99 ({mode} mode); matching colours are 100 to 1.", "",
            table(["Pattern", "Rarity", "Chance per egg"], rows), "", "**STATUS**", "", table(["Pattern", "Icon", "Asset id", "Mask", "Odds from"], status), ""] + blocks
    page.add("patterns", "Patterns", "\n\n".join(body), [(f"pattern-{kebab(p['id'])}", p.get("name") or title_from_id(p["id"])) for p in patterns])

    # -- conditions
    conds = prog["Conditions"]
    weights = prog["ConditionWeights"]
    percents = ctx.calls["conditionPercents"]
    failure = ctx.calls["failure"]
    head = ["Egg upgrade tier"] + [c["name"] for c in conds] + ["Egg fails"]
    cond_rows = []
    for level in range(len(weights)):
        cond_rows.append([level] + [ctx.hide(pct(v), "conditions") for v in percents[level]] + [ctx.hide(pct(100 * failure[level]), "conditions")])
    safe = prog["SafeEggs"]
    body = [f"Chances by condition upgrade tier (version `{prog['ConditionOddsVersion']}`; the owner target is tier 0)." + (" Tiers 1 to 6 are PROVISIONAL." if not ctx.public else ""),
            f"A new player's first {safe} eggs are never Cracked.", "", table(head, cond_rows), ""]
    status, blocks = [], []
    stage_ids = prog.get("ConditionStageAssetIds") or {}
    for c in conds:
        a = f"condition-{c['id']}"
        pic = ctx.find_picture("Egg condition", c["name"], f"Eggs-and-looks#{a}", [f"resources/eggs/conditions/BeDino_Cond_{c['name']}.png"] + (["resources/ui/v2/icons/premium-egg-normal.png"] if c["id"] == "normal" else []),
                               f"resources/eggs/conditions/BeDino_Cond_{c['name']}.png", what="no egg picture for this condition")
        aid = ctx.asset_id_status("Egg condition", c["name"], f"Eggs-and-looks#{a}", stage_ids.get(c["id"]), f"ProgressionConfig.ConditionStageAssetIds.{c['id']}", "resources/eggs/conditions")
        status.append([f"[{c['name']}](#{a})", f"yes: `{pic}`" if pic else "MISSING", aid, "n/a", "`src/shared/ProgressionConfig.luau` ConditionWeights"])
        hatch = c["hatchChance"]
        blocks.append(item_heading(a, c["name"], 4) + f"id: `{c['id']}`\n\n" + (ctx.image(pic, c["name"], 140) + "\n\n" if pic else "")
                      + f"- **Strength:** {num(c['stats'] * 100)}% of normal\n- **Hatch chance:** {pct(100 * hatch)}" + (" (can fail)" if hatch < 1 else "")
                      + f"\n- **Chance at tier 0:** {ctx.hide(pct(percents[0][conds.index(c)]), 'conditions')}")
    upg = [[u["level"], num(u["price"]) + " crystals", f"level {u['requiredLevel']}"] for u in prog["ConditionUpgrades"]]
    body += ["**STATUS**", "", table(["Condition", "Picture", "Asset id", "Mask", "Odds from"], status), "", "Upgrade tiers (shop):", "", table(["Tier", "Price", "Needs"], upg), ""] + blocks
    page.add("conditions", "Egg conditions", "\n\n".join(body), [(f"condition-{c['id']}", c["name"]) for c in conds])

    # -- nests and hatching
    nest_luck = cfg["NestLuckTiers"]
    facts = [
        f"- Eggs from food: {num(500 * cfg['FoodCatchRate'], 3)} eggs per 500 food points{ctx.prov_mark('food')}. One catch is one egg; one egg is one dino.",
        f"- Waiting eggs: {cfg['ChestQueueCapacity']} in the queue, {cfg['ChestOverflowCapacity']} more in overflow, up to {num(cfg['RunEggBankCapacity'])} banked; a run stops counting at {cfg['RunEggMaxPerRun']} eggs.",
        f"- Each egg shows for {num(cfg['HatchRevealSeconds'])} second(s) when it hatches.",
        f"- Nests: {cfg['NestStorageCapacity']} spots, {num(cfg['NestIncubationSeconds'] / 3600, 3)} hours each, {cfg['NestMinSize']} to {cfg['NestMaxSize']} eggs{ctx.prov_mark('nests')}. "
        f"A run needs {cfg['NestMinRunSeconds']} seconds and {cfg['NestMinCatches']} catch to drop one; one more nest per {cfg['NestEggsPerExtraNest']} extra eggs. "
        f"A nest with no free spot turns into {cfg['NestOverflowCrystals']} crystals.",
        "- Nest luck: " + "; ".join(f"BIG {pct(100 * t['bigChance'])}, Shiny {pct(100 * t['shinyChance'])}, +{t['conditionLevels']} condition tiers" for t in nest_luck) + ".",
        f"- Shop egg: {num(prog['RandomEggPrice'])} crystals.",
    ]
    page.add("nests", "Nests and hatching", "\n".join(facts))
    return page


# ---------------------------------------------------------------- Mutations and fusion
def build_mutations(ctx: Ctx) -> Page:
    cfg, prog, d = ctx.config, ctx.prog, ctx.d
    page = Page("Mutations-and-fusion", "BIG, Shiny, weather mutations, and the fusion ladder (Gold, Emerald, Diamond).")
    slots = d["AssetSlots"]["Images"]
    look = d["MutationLook"]["Entries"]
    weather = {w["mutation"]: w for w in prog["Weather"]}

    # -- BIG and Shiny
    body = [
        f"- **BIG:** {pct(100 * cfg['BigChance'])} of eggs ({one_in(100 * cfg['BigChance'])}). The dino is {num((cfg['BigScaleMultiplier'] - 1) * 100)}% bigger. Size only.",
        f"- **Shiny:** {pct(100 * cfg['ShinyChance'])} of earned eggs ({one_in(100 * cfg['ShinyChance'])}), only in irregular weather: "
        + ", ".join(w["name"] for w in prog["Weather"] if cfg["IrregularWeather"].get(w["id"])) + ". Bought eggs are never Shiny.",
    ]
    page.add("big-and-shiny", "BIG and Shiny", "\n".join(body))

    # -- event mutations
    status, blocks = [], []
    for m in prog["EventMutations"]:
        a = f"mutation-{m['id']}"
        e = look.get(m["id"], {})
        w = weather.get(m["id"])
        pic = ctx.find_picture("Mutation", m["name"], f"Mutations-and-fusion#{a}", [f"resources/ui/v2/icons/mutation-{m['id']}-v1.png"],
                               f"resources/ui/v2/icons/mutation-{m['id']}-v1.png", kind="icon", what="no mutation icon")
        aid = ctx.asset_id_status("Mutation", m["name"], f"Mutations-and-fusion#{a}", slots.get(f"mutation_{m['id']}"), f"AssetSlots.Images.mutation_{m['id']}", "resources/ui/v2/icons")
        status.append([f"[{m['name']}](#{a})", f"yes: `{pic}`" if pic else "MISSING", aid, "n/a", "`src/shared/ProgressionConfig.luau` Weather"])
        lines = [item_heading(a, m["name"], 4) + f"id: `{m['id']}`\n", (ctx.image(pic, m["name"], 96) + "\n") if pic else "",
                 f"- **Growth:** {plus(m['growth'])}, **speed:** {plus(m['speed'])}{ctx.prov_mark('event mutations')}",
                 f"- **Colour:** `{core.hex_rgb(m['color'])}`" + (f"; mood: {e['mood']}" if e.get("mood") else "")]
        if w:
            lines.append(f"- **Comes from:** {w['name']} weather, {ctx.hide(pct(100 * w['chance']), 'event mutations')} per egg ({ctx.hide(one_in(100 * w['chance']), 'event mutations')})")
        blocks.append("\n".join(lines))
    body = ["A mutation rides on an egg caught in that weather. It gives a small perk and a tint.", "", "**STATUS**", "",
            table(["Mutation", "Icon", "Asset id", "Mask", "Odds from"], status), ""] + blocks
    page.add("event-mutations", "Weather mutations", "\n\n".join(body), [(f"mutation-{m['id']}", m["name"]) for m in prog["EventMutations"]])

    # -- fusion
    if ctx.shown("IdentityFusionPreviewEnabled"):
        fusion = d["IdentityFusion"]
        odds = d["FusionOdds"]
        recipes = fusion["Recipes"]
        rows, status, blocks = [], [], []
        art = d["ArtworkAssets"]
        for stage in fusion["Ladder"][1:]:
            r = recipes[stage]
            a = f"fusion-{stage}"
            label = stage.capitalize()
            rule = "any pattern of the same species" if r.get("anyPattern") else "same species and same pattern"
            rows.append([f"[{label}](#{a})", f"{r['donorCount']} x {r['sourceStage'].capitalize()}", rule])
            pic = ctx.find_picture("Fusion tier", label, f"Mutations-and-fusion#{a}", [f"resources/ui/v2/icons/tier-{stage}-v1.png", f"resources/ui/v2/layers/mutation-{stage}-v1.png"],
                                   f"resources/ui/v2/icons/tier-{stage}-v1.png", kind="icon", what="no tier icon")
            aid = ctx.asset_id_status("Fusion tier", label, f"Mutations-and-fusion#{a}", slots.get(f"tier_{stage}"), f"AssetSlots.Images.tier_{stage}", "resources/ui/v2/icons")
            status.append([f"[{label}](#{a})", f"yes: `{pic}`" if pic else "MISSING", aid, "n/a", "`src/server/IdentityFusion.luau` Recipes"])
            blocks.append(item_heading(a, label, 4) + f"id: `{stage}`\n\n" + (ctx.image(pic, label, 96) + "\n\n" if pic else "")
                          + f"- **Needs:** {r['donorCount']} {r['sourceStage'].capitalize()} dinos ({rule}). All are used up.\n- **Result:** one new {label} dino; the next stage is guaranteed.")
        coeff = f"each chance is {num(odds['ShinyCoefficient'] * 100)}% (Shiny), {num(odds['BigCoefficient'] * 100)}% (BIG) and {num(odds['MutationCoefficient'] * 100)}% (mutation) of the share of such dinos among the inputs"
        body = [f"Ladder version `{fusion['Version']}`. {ctx.flag_note('IdentityFusionPreviewEnabled')}", "", table(["Result", "Inputs", "Rule"], rows), "",
                f"New traits are rolled from the inputs ({'PROVISIONAL, ' if not ctx.public else ''}version `{odds['Version']}`): {ctx.hide(coeff, 'fusion odds')}.", "",
                "**STATUS**", "", table(["Tier", "Icon", "Asset id", "Mask", "Odds from"], status), ""] + blocks
        page.add("fusion", "Fusion", "\n\n".join(body), [(f"fusion-{s}", s.capitalize()) for s in fusion["Ladder"][1:]])
    return page


# ---------------------------------------------------------------- Shop items
def build_shop(ctx: Ctx) -> Page:
    cfg, prog, d = ctx.config, ctx.prog, ctx.d
    slots = d["AssetSlots"]["Images"]
    page = Page("Shop-items", "Potions, auras and trails, with prices and pictures.")
    # -- potions
    shop = prog["PotionShop"]
    wsum = sum(shop["RarityWeights"].values())
    offer_rows = [[r, ctx.hide(pct(100 * shop["RarityWeights"][r] / wsum), "potions")] for r in shop["Rarities"]]
    status, blocks = [], []
    for p in prog["Potions"]:
        a = f"potion-{kebab(p['id'])}"
        pic = ctx.find_picture("Potion", p["name"], f"Shop-items#{a}", [f"resources/ui/v2/items/potion-{kebab(p['name'])}.png"],
                               f"resources/ui/v2/items/potion-{kebab(p['name'])}.png", what="no potion picture")
        aid = ctx.asset_id_status("Potion", p["name"], f"Shop-items#{a}", slots.get(f"potion_icon_{p['id']}"), f"AssetSlots.Images.potion_icon_{p['id']}", "resources/ui/v2/items")
        status.append([f"[{p['name']}](#{a})", f"yes: `{pic}`" if pic else "MISSING", aid, "n/a", "`src/shared/ProgressionConfig.luau` PotionShop"])
        kind = {"speed": "Speed", "growth": "Growth", "loot": "Luck"}.get(p["kind"], p["kind"])
        blocks.append(item_heading(a, p["name"], 4) + f"id: `{p['id']}`\n\n" + (ctx.image(pic, p["name"], 96) + "\n\n" if pic else "")
                      + f"- **Kind:** {kind}, {p['rarity']}\n- **Power:** {plus(p['multiplier'])} for {num(p['duration'] / 60, 3)} min\n- **Price:** {num(p['price'])} crystals")
    body = [f"The potion shop offers {shop['OfferCount']} potions and restocks every {num(shop['PeriodSeconds'] / 60, 3)} minutes. Chance that a slot is each rarity"
            f"{ctx.prov_mark('potions')}:", "", table(["Rarity", "Chance"], offer_rows), "", "**STATUS**", "",
            table(["Potion", "Picture", "Asset id", "Mask", "Odds from"], status), ""] + blocks
    page.add("potions", "Potions", "\n\n".join(body), [(f"potion-{kebab(p['id'])}", p["name"]) for p in prog["Potions"]])
    # -- auras
    status, blocks = [], []
    for au in prog["Auras"]:
        a = f"aura-{au['id']}"
        pic = ctx.find_picture("Aura", au["name"], f"Shop-items#{a}", [f"resources/ui/v2/items/aura-{au['id']}-v1.png"], f"resources/ui/v2/items/aura-{au['id']}-v1.png", what="no aura picture")
        aid = ctx.asset_id_status("Aura", au["name"], f"Shop-items#{a}", slots.get(f"aura_{au['id']}"), f"AssetSlots.Images.aura_{au['id']}", "resources/ui/v2/items")
        status.append([f"[{au['name']}](#{a})", f"yes: `{pic}`" if pic else "MISSING", aid, "n/a", "`src/shared/ProgressionConfig.luau` Auras"])
        blocks.append(item_heading(a, au["name"], 4) + f"id: `{au['id']}`\n\n" + (ctx.image(pic, au["name"], 96) + "\n\n" if pic else "")
                      + f"- **Rarity:** {au['rarity']}\n- **Growth:** {plus(au['growth'])}\n- **Price:** {num(au['price'])} crystals\n- **Colour:** `{core.hex_rgb(au['color'])}`")
    page.add("auras", "Auras", "**STATUS**\n\n" + table(["Aura", "Picture", "Asset id", "Mask", "Odds from"], status) + "\n\n" + "\n\n".join(blocks),
             [(f"aura-{x['id']}", x["name"]) for x in prog["Auras"]])
    # -- trails
    status, blocks = [], []
    trail_ids = prog.get("TrailIconAssetIds") or {}
    for t in prog["Trails"]:
        a = f"trail-{t['id']}"
        pic = ctx.find_picture("Trail", t["name"], f"Shop-items#{a}", [f"resources/ui/v2/icons/trail-{t['id']}-v1.png"], f"resources/ui/v2/icons/trail-{t['id']}-v1.png", kind="icon", what="no trail icon")
        aid = ctx.asset_id_status("Trail", t["name"], f"Shop-items#{a}", trail_ids.get(t["id"]), f"ProgressionConfig.TrailIconAssetIds.{t['id']}", "resources/ui/v2/icons")
        status.append([f"[{t['name']}](#{a})", f"yes: `{pic}`" if pic else "MISSING", aid, "n/a", "`src/shared/ProgressionConfig.luau` Trails"])
        price = "free" if t["price"] == 0 else num(t["price"]) + " crystals"
        blocks.append(item_heading(a, t["name"], 4) + f"id: `{t['id']}`\n\n" + (ctx.image(pic, t["name"], 96) + "\n\n" if pic else "")
                      + f"- **Rarity:** {t['rarity']}\n- **Speed:** {plus(t['speed'])}\n- **Price:** {price}, needs level {t['level']}\n- **Colour:** `{core.hex_rgb(t['color'])}`")
    page.add("trails", "Trails", "**STATUS**\n\n" + table(["Trail", "Icon", "Asset id", "Mask", "Odds from"], status) + "\n\n" + "\n\n".join(blocks),
             [(f"trail-{x['id']}", x["name"]) for x in prog["Trails"]])
    # -- other
    other = [f"- **Shop egg:** {num(prog['RandomEggPrice'])} crystals (chances on the Dinosaurs and Eggs and looks pages).",
             f"- **Condition upgrades:** {len(prog['ConditionUpgrades'])} tiers, {num(prog['ConditionUpgrades'][0]['price'])} to {num(prog['ConditionUpgrades'][-1]['price'])} crystals (see Egg conditions).",
             f"- **Fast travel perk:** {num(prog['FastTravelPrice'])} crystals. {ctx.flag_note('FastTravelPerk')}"]
    page.add("other-shop", "Other shop items", "\n".join(other))
    return page


# ---------------------------------------------------------------- World and food
def parse_food_kinds(root: Path) -> list[dict[str, Any]]:
    """FoodService keeps its food kinds in a local table (not a data module), so the four lines are read carefully as text."""
    text = (root / "src/server/FoodService.luau").read_text(encoding="utf-8")
    block = re.search(r"local TYPES = \{(.*?)\n\}", text, re.S)
    rows = []
    if block:
        for m in re.finditer(r'\{id = "(\w+)", weight = (\d+), points = (\d+)', block.group(1)):
            rows.append({"id": m.group(1), "weight": int(m.group(2)), "points": int(m.group(3))})
    if not rows:
        raise SystemExit("tools/build_catalog.py: could not read the food kinds from src/server/FoodService.luau (local TYPES table). Update parse_food_kinds().")
    return rows


def material_words(name: str) -> str:
    """'LeafyGrass' -> 'leafy grass'."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name).lower()


def statue_label(key: str) -> str:
    short = key.replace("hub_statue_", "")
    return {"trex": "T-Rex"}.get(short, title_from_id(short)) + " statue"


def build_world(ctx: Ctx) -> Page:
    cfg, prog, d = ctx.config, ctx.prog, ctx.d
    page = Page("World-and-food", "Food, weather, biomes, wind and landmarks of the island.")
    ladder = d["ScaleLadder"]
    # -- food
    kinds = parse_food_kinds(ctx.root)
    total = sum(k["weight"] for k in kinds)
    names = {"berry": "Berry", "fruit": "Fruit", "egg": "Egg", "amber": "Amber"}
    status, blocks, rows = [], [], []
    for k in kinds:
        a = f"food-{k['id']}"
        label = names.get(k["id"], title_from_id(k["id"]))
        pic = ctx.find_picture("Food", label, f"World-and-food#{a}", [f"resources/ui/v2/items/food-{k['id']}-v1.png"], f"resources/ui/v2/items/food-{k['id']}-v1.png", what="no food picture")
        kit = [n for n in d["WorldKitData"] if n.startswith(f"food_{k['id']}_")]
        status.append([f"[{label}](#{a})", f"yes: `{pic}`" if pic else "MISSING", f"{len(kit)} world-kit model(s) in code" if kit else "no model in code", "n/a", "`src/server/FoodService.luau` TYPES"])
        share = 100 * k["weight"] / total
        size = ladder["Food"].get(k["id"], {}).get("size")
        rows.append([f"[{label}](#{a})", k["points"], pct(share)])
        blocks.append(item_heading(a, label, 4) + f"id: `{k['id']}`\n\n" + (ctx.image(pic, label, 96) + "\n\n" if pic else "")
                      + f"- **Food points:** {k['points']}\n- **Share of food on the island:** {pct(share)}" + (f"\n- **Size:** {num(size)} stud" + ("" if size == 1 else "s") if size else ""))
    body = [f"Every pickup gives food points (growth and eggs come from them). The island has {num(cfg['FoodSectorCount'] ** 2)} clusters of {num(cfg['FoodClusterItems'])} pickups.", "",
            table(["Food", "Food points", "Share"], rows), "", "**STATUS**", "", table(["Food", "Picture", "Model", "Mask", "Points from"], status), ""] + blocks
    page.add("food", "Food", "\n\n".join(body), [(f"food-{k['id']}", names.get(k["id"], title_from_id(k["id"]))) for k in kinds])
    # -- special food
    if ctx.shown("SpecialFoodsEnabled"):
        sf = d["SpecialFoods"]["GOLDEN_DRUMSTICK"]
        a = "food-golden-drumstick"
        pic = ctx.find_picture("Special food", sf["name"], f"World-and-food#{a}", ["resources/ui/v2/items/food-golden-drumstick-v1.png"], "resources/ui/v2/items/food-golden-drumstick-v1.png", what="no picture")
        icon = ctx.asset_id_status("Special food", sf["name"], f"World-and-food#{a}", d["AssetSlots"]["Images"].get("golden_drumstick_icon"), "AssetSlots.Images.golden_drumstick_icon", "resources/ui/v2/items")
        mesh = ctx.asset_id_status("Special food", sf["name"] + " (mesh)", f"World-and-food#{a}", d["AssetSlots"]["Meshes"].get("golden_drumstick_mesh"), "AssetSlots.Meshes.golden_drumstick_mesh", "resources/models")
        body = [item_heading(a, sf["name"], 4) + f"id: `{sf['id']}`\n", (ctx.image(pic, sf["name"], 96) + "\n") if pic else "", f"- {sf['benefit']}",
                f"- **Food points:** {ctx.calls['specialPoints']}{ctx.prov_mark('special food')}",
                f"- **Chance:** {ctx.hide(pct(100 * cfg['SpecialFoodChance']), 'special food')} of food slots ({ctx.hide(one_in(100 * cfg['SpecialFoodChance']), 'special food')})",
                f"- Picture: {'yes' if pic else 'MISSING'}; icon id: {icon}; mesh id: {mesh}. {ctx.flag_note('SpecialFoodsEnabled')}"]
        page.add("special-food", "Special food", "\n".join(body))
    # -- weather
    weather = prog["Weather"]
    wsum = sum(w["weight"] for w in weather)
    uiicons = d["UIIconAssets"]
    cycle = prog["WeatherInterval"] + prog["WeatherDuration"]
    mutation_names = {m['id']: m['name'] for m in prog['EventMutations']}
    status, blocks, rows = [], [], []
    for w in weather:
        a = f"weather-{w['id']}"
        pic = ctx.find_picture("Weather", w["name"], f"World-and-food#{a}", [f"resources/ui/v2/icons/weather-{w['id']}"], f"resources/ui/v2/icons/weather-{w['id']}-v1.png", kind="icon", what="no weather icon")
        aid = ctx.asset_id_status("Weather", w["name"], f"World-and-food#{a}", uiicons.get(w["icon"]), f"UIIconAssets.{w['icon']}", "resources/ui/v2/icons")
        status.append([f"[{w['name']}](#{a})", f"yes: `{pic}`" if pic else "MISSING", aid, "n/a", "`src/shared/ProgressionConfig.luau` Weather"])
        share = 100 * w["weight"] / wsum
        rows.append([f"[{w['name']}](#{a})", w["rarity"], pct(share)])
        blocks.append(item_heading(a, w["name"], 4) + f"id: `{w['id']}`\n\n" + (ctx.image(pic, w["name"], 96) + "\n\n" if pic else "")
                      + f"- **Rarity:** {w['rarity']}\n- **Chance when weather starts:** {pct(share)}\n- **Growth** {plus(w['growth'])}, **speed** {plus(w['speed'])}, **loot** {plus(w['loot'])}\n"
                      + f"- **Egg mutation:** {mutation_names.get(w['mutation'], w['mutation'])} at {pct(100 * w['chance'])} per egg" + (" (also Shiny)" if cfg["IrregularWeather"].get(w["id"]) else ""))
    body = [f"Weather starts every {num(cycle / 60, 3)} minutes and lasts {num(prog['WeatherDuration'] / 60, 3)} minutes. Between storms the sky is clear.", "",
            table(["Weather", "Rarity", "Chance"], rows), "", "**STATUS**", "", table(["Weather", "Icon", "Asset id", "Mask", "Odds from"], status), ""] + blocks
    page.add("weather", "Weather", "\n\n".join(body), [(f"weather-{w['id']}", w["name"]) for w in weather])
    # -- biomes
    biome = d["BiomeMap"]
    status, blocks = [], []
    for b in biome["Order"]:
        a = f"biome-{b}"
        label = biome["Names"][b]
        pic = ctx.find_picture("Biome", label, f"World-and-food#{a}", [f"resources/ui/v2/world/biome-{b}-v1.png"], f"resources/ui/v2/world/biome-{b}-v1.png", what="no biome picture")
        status.append([f"[{label}](#{a})", f"yes: `{pic}`" if pic else "MISSING", "n/a", "n/a", "`src/shared/BiomeMap.luau`"])
        ground = ", ".join(material_words(band[0]) for band in biome["Ground"][b])
        blocks.append(item_heading(a, label, 4) + f"id: `{b}`\n\n" + (ctx.image(pic, label, 160) + "\n\n" if pic else "") + f"- **Ground:** {ground}\n- **Rock:** {material_words(biome['Rock'][b])}")
    page.add("biomes", "Biomes", f"{len(biome['Order'])} biomes blend smoothly into each other.\n\n**STATUS**\n\n" + table(["Biome", "Picture", "Asset id", "Mask", "Data from"], status) + "\n\n" + "\n\n".join(blocks),
             [(f"biome-{b}", biome["Names"][b]) for b in biome["Order"]])
    # -- wind
    ctx.gaps.add("not in code", "Wind", "Wind (breeze)", "World-and-food#wind", "no wind or breeze data exists in the game code (nothing sways)", "src/shared", "(new module, for example WindConfig.luau)",
                 "the owner listed wind; it is not data-driven yet")
    page.add("wind", "Wind", "**Not data-driven yet.** The game has no wind or breeze setting today (trees and grass do not sway). This is listed under Missing on the Home page.")
    # -- landmarks and statues
    kit, meshes = d["WorldKitData"], d["WorldKitMeshAssets"]
    marks = [(m["id"], m) for m in d["BiomePlacement"]["Landmarks"]]
    status, blocks = [], []
    for kid, m in marks:
        short = kid.replace("world_landmark_", "")
        a = f"landmark-{kebab(short)}"
        label = title_from_id(short)
        pic = ctx.find_picture("Landmark", label, f"World-and-food#{a}", [f"resources/ui/v2/world/landmark-{kebab(short)}-v1.png"], f"resources/ui/v2/world/landmark-{kebab(short)}-v1.png", what="no landmark picture")
        mesh = meshes.get(kid, {}).get("meshId")
        mesh_state = ctx.asset_id_status("Landmark", label, f"World-and-food#{a}", mesh, f"WorldKitMeshAssets.{kid}", "resources/worldkit-meshes")
        ext = kit.get(kid, {}).get("extent", [0, 0, 0])
        status.append([f"[{label}](#{a})", f"yes: `{pic}`" if pic else "MISSING", "mesh " + mesh_state, "n/a", "`src/shared/BiomePlacement.luau` Landmarks"])
        blocks.append(item_heading(a, label, 4) + f"id: `{kid}`\n\n" + (ctx.image(pic, label, 160) + "\n\n" if pic else "")
                      + f"- **Where:** x {num(m['x'])}, z {num(m['z'])}\n- **Size:** about {num(ext[1] * d['BiomePlacement']['LandmarkScale'], 3)} studs tall")
    page.add("landmarks", "Landmarks", "Big things on the island you can walk up to.\n\n**STATUS**\n\n" + table(["Landmark", "Picture", "Mesh", "Mask", "Data from"], status) + "\n\n" + "\n\n".join(blocks),
             [(f"landmark-{kebab(k.replace('world_landmark_', ''))}", title_from_id(k.replace("world_landmark_", ""))) for k, _ in marks])
    if ctx.shown("CaveHub"):
        props = d["CaveHubProps"]["Assets"]
        statues = sorted(k for k in props if k.startswith("hub_statue_"))
        status, blocks = [], []
        for k in statues:
            short = k.replace("hub_statue_", "")
            a = f"statue-{kebab(short)}"
            label = statue_label(k)
            pic = ctx.find_picture("Statue", label, f"World-and-food#{a}", [f"resources/ui/v2/world/statue-{kebab(short)}-v1.png"], f"resources/ui/v2/world/statue-{kebab(short)}-v1.png", what="no statue picture")
            mid = ctx.asset_id_status("Statue", label, f"World-and-food#{a}", props[k].get("id"), f"CaveHubProps.Assets.{k}", "src/shared")
            status.append([f"[{label}](#{a})", f"yes: `{pic}`" if pic else "MISSING", "model " + mid, "n/a", "`src/shared/CaveHubProps.luau`"])
            blocks.append(item_heading(a, label, 4) + f"id: `{k}`\n\n" + (ctx.image(pic, label, 160) + "\n\n" if pic else "") + f"- {props[k].get('note', '')}")
        page.add("statues", "Statues in the cave hub", ctx.flag_note("CaveHub") + "\n\n**STATUS**\n\n" + table(["Statue", "Picture", "Model id", "Mask", "Data from"], status) + "\n\n" + "\n\n".join(blocks),
                 [(f"statue-{kebab(k.replace('hub_statue_', ''))}", statue_label(k)) for k in statues])
    return page


# ---------------------------------------------------------------- Home (needs every gap, so it is built last)
def build_home(ctx: Ctx, pages: dict[str, Page]) -> Page:
    cfg, prog = ctx.config, ctx.prog
    page = Page("Home", "This is the one place where everyone (owner, helpers, Codex) reads what the game contains today: which dinosaurs, looks, items and "
                "foods exist, their pictures, what is missing and the chances. It is only for the team. Agents: read this page first when you make art or content.")
    listing = [f"- [{PAGE_TITLES[n]}]({n}.md): {desc}" for n, desc in [
        ("Dinosaurs", "every dinosaur: picture, class, rarity, chance, size"), ("Eggs-and-looks", "colours, patterns, egg conditions, nests"),
        ("Mutations-and-fusion", "BIG, Shiny, weather mutations, fusion"), ("Shop-items", "potions, auras, trails"),
        ("World-and-food", "food, weather, biomes, wind, landmarks")]]
    page.add("what-is-here", "What is here", "\n".join(listing) + "\n\nEvery item is a section with an anchor on its page (never a page of its own). Each page starts with a contents list. "
             "A STATUS table per category shows: picture or icon present, asset id bound, mask present, and where the odds come from.")
    add_art = ("1. Find your item under **Missing** below. It names the exact folder and file name.\n2. Put the file there (and add one line to "
               "[docs/77](../77-asset-registry.md)).\n3. Run `python tools/build_catalog.py` and commit `docs/catalog/` together with your change. "
               "CI fails when the catalogue is out of date (`python tools/verify_catalog.py`).\n4. Binding the uploaded id into the code is a separate step "
               "(`tools/bind_assets.py`).")
    if not ctx.public:
        page.add("how-to-add", "How to add art or content", add_art)
    # switches
    rows = []
    for key, label in core.FLAGS:
        s = ctx.flags.get(key, {})
        def w(v: Any) -> str:
            return "on" if v is True else "off" if v is False else "not set"
        rows.append([label, w(s.get("default")), w(s.get("playtest"))])
    if not ctx.public:
        page.add("switches", "What is switched on", "Read from `tools/release_profiles.py` and `src/shared/Config.luau`.\n\n" + table(["Feature", "Default build", "Playtest build"], rows))
    # missing
    gaps = ctx.gaps.rows
    counts = ctx.gaps.by_kind()
    summary = table(["Kind", "How many"], [[k, v] for k, v in counts.items()]) if gaps else "Nothing is missing."
    cats: dict[str, list] = {}
    for g in gaps:
        cats.setdefault(g.category, []).append(g)
    parts = [f"{len(gaps)} gaps. Deliver the file at the exact folder and name shown.", "", summary, ""]
    for cat in sorted(cats):
        parts.append(f"### {cat}\n")
        parts.append(table(["Item", "Missing", "Put it in folder", "File name", "Note"],
                           [[f"[{g.item}]({g.anchor.split('#')[0]}.md#{g.anchor.split('#')[1]})", g.kind, f"`{g.folder}`" if g.folder else "", f"`{g.file}`" if g.file else "",
                             "; ".join(x for x in (g.what, g.note) if x)] for g in cats[cat]]))
        parts.append("")
    if not ctx.public:
        page.add("missing", "Missing", "\n".join(parts))
    page.add("odds", "Odds", build_odds(ctx))
    return page


def build_odds(ctx: Ctx) -> str:
    cfg, prog, d = ctx.config, ctx.prog, ctx.d
    rows: list[list[Any]] = []
    def P(key: str) -> str:
        return "PROVISIONAL" if key in PROVISIONAL else ""
    weights = {r["speciesId"]: r["weight"] for r in cfg["ChestSpeciesWeights"]}
    total = sum(weights.values())
    for ti, name in enumerate(cfg["SpeciesRarityNames"], start=1):
        share = 100 * sum(w for s, w in weights.items() if cfg["SpeciesRarities"][s] == ti) / total
        rows.append([f"Dinosaur: {name}", ctx.hide(pct(share), "species"), "per shop egg", "Dinosaurs.md#rarity-tiers", "src/shared/Config.luau ChestSpeciesWeights", P("species")])
    if ctx.shown("SecretSpeciesEnabled"):
        sec = d["SecretSpeciesConfig"]
        rows.append(["Secret dinosaur", ctx.hide(pct(100 * sec["Chance"]), "secret"), "per run or nest egg", "Dinosaurs.md#secret-dinosaurs", "src/shared/SecretSpeciesConfig.luau", (P("secret") + " (SECRET, internal only)") if not ctx.public else P("secret")])
    pc = ctx.calls["conditionPercents"][0]
    for c, v in zip(prog["Conditions"], pc):
        rows.append([f"Egg condition: {c['name']}", ctx.hide(pct(v), "conditions"), "per egg, tier 0", "Eggs-and-looks.md#conditions", "src/shared/ProgressionConfig.luau ConditionWeights", "owner target"])
    fail = ctx.calls["failure"][0]
    rows.append(["Egg fails (no dino)", ctx.hide(pct(100 * fail), "conditions"), "per egg, tier 0", "Eggs-and-looks.md#conditions", "src/shared/EggOutcomeOdds.luau", "owner target"])
    scale = prog["EggColorWeightScale"]
    for ti, name in enumerate(ctx.tier_names):
        members = [c for c in prog["EggColors"] if c.get("rarity", ctx.tier_names[0]) == name]
        if members:
            rows.append([f"Colour: {name}", pct(100 * sum(c["weight"] for c in members) / scale), "per colour slot", "Eggs-and-looks.md#colours", "src/shared/ProgressionConfig.luau EggColors", ""])
    n = len(ctx.calls["patterns"])
    rows.append(["Pattern: each one", pct(100 / n), f"per egg ({n} patterns)", "Eggs-and-looks.md#patterns", "src/shared/EggGenetics.luau Patterns", ""])
    rows.append(["BIG", pct(100 * cfg["BigChance"]), "per egg", "Mutations-and-fusion.md#big-and-shiny", "src/shared/Config.luau BigChance", ""])
    rows.append(["Shiny", pct(100 * cfg["ShinyChance"]), "per earned egg in irregular weather", "Mutations-and-fusion.md#big-and-shiny", "src/shared/Config.luau ShinyChance", ""])
    for w in prog["Weather"]:
        rows.append([f"Weather mutation: {w['mutation']}", ctx.hide(pct(100 * w["chance"]), "event mutations"), f"per egg in {w['name']}", "Mutations-and-fusion.md#event-mutations", "src/shared/ProgressionConfig.luau Weather", P("event mutations")])
    wsum = sum(w["weight"] for w in prog["Weather"])
    for w in prog["Weather"]:
        rows.append([f"Weather: {w['name']}", pct(100 * w["weight"] / wsum), "when weather starts", "World-and-food.md#weather", "src/shared/ProgressionConfig.luau Weather", ""])
    shop = prog["PotionShop"]
    ws = sum(shop["RarityWeights"].values())
    for r in shop["Rarities"]:
        rows.append([f"Potion offer: {r}", ctx.hide(pct(100 * shop["RarityWeights"][r] / ws), "potions"), "per shop slot", "Shop-items.md#potions", "src/shared/ProgressionConfig.luau PotionShop", P("potions")])
    if ctx.shown("SpecialFoodsEnabled"):
        rows.append(["Golden Drumstick", ctx.hide(pct(100 * cfg["SpecialFoodChance"]), "special food"), "per food slot", "World-and-food.md#special-food", "src/shared/Config.luau SpecialFoodChance", P("special food")])
    out = ["Every chance in the game in one table. Details are on the linked pages.", ""]
    link_rows = [[r[0], r[1], r[2], f"[open]({r[3]})", f"`{r[4]}`", r[5] if not ctx.public else ""] for r in rows]
    head = ["Chance", "Value", "For", "Page", "Source file", "Status"] if not ctx.public else ["Chance", "Value", "For", "Page", "Source file", ""]
    out.append(table(head, link_rows))
    return "\n".join(out)


# ---------------------------------------------------------------- build and write
def build(root: Path = ROOT, runner: Optional[str] = None, public: bool = False, out_dir: Optional[Path] = None) -> dict[str, str]:
    """Return {file name: Markdown} without writing anything."""
    out_dir = out_dir or (root / (PUBLIC_OUT if public else DEFAULT_OUT))
    ctx = Ctx(root, core.find_runner(runner), public, out_dir)
    pages = {
        "Dinosaurs": build_dinosaurs(ctx), "Eggs-and-looks": build_eggs(ctx), "Mutations-and-fusion": build_mutations(ctx),
        "Shop-items": build_shop(ctx), "World-and-food": build_world(ctx),
    }
    pages["Home"] = build_home(ctx, pages)
    names = [n for n in PAGE_ORDER if n in pages]
    if len(names) > MAX_PAGES:
        raise SystemExit("more than %d pages" % MAX_PAGES)
    result = {f"{n}.md": pages[n].render(ctx) for n in names}
    build.last_gaps = ctx.gaps  # type: ignore[attr-defined]
    return result


def write(files: dict[str, str], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("*.md"):
        if stale.name not in files:
            stale.unlink()
    for name, text in files.items():
        (out_dir / name).write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runner", help="pinned Luau runner (default: LUAU_RUNNER, PATH, or the known install)")
    parser.add_argument("--public", action="store_true", help="player-safe copy: no secrets, nothing behind an off flag, no provisional odds")
    parser.add_argument("--out", help="output folder (default docs/catalog; with --public build/catalog-public)")
    parser.add_argument("--check", action="store_true", help="do not write; fail when docs/catalog is stale")
    args = parser.parse_args()
    if args.check:
        import verify_catalog
        return verify_catalog.main(["--runner", args.runner] if args.runner else [])
    out_dir = ROOT / (args.out or (PUBLIC_OUT if args.public else DEFAULT_OUT))
    files = build(ROOT, args.runner, args.public, out_dir)
    write(files, out_dir)
    gaps: Gaps = build.last_gaps  # type: ignore[attr-defined]
    print("wrote %d pages to %s" % (len(files), out_dir.relative_to(ROOT).as_posix()))
    for name, text in files.items():
        print("  %-26s %6d lines  %7d bytes" % (name, text.count("\n"), len(text.encode("utf-8"))))
    print("missing: %d gaps (%s)" % (len(gaps.rows), ", ".join(f"{k} {v}" for k, v in gaps.by_kind().items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
