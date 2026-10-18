"""BD-425: permanent guard for the Robux line (docs/114 section 11a, docs/86, docs/115).

Robux buys looks and convenience, never exclusive power. Pure text scan (no Luau runner); fails when:
  1. a Robux flag (Config keys naming Robux/Pack/Paid/GamePass/Product/Purchase) is true in the default profile;
  2. a developer product / game pass is not a plain crystal pack (positive whole crystals) or a config row grants a
     forbidden stat or a multiplier above CONVENIENCE_CAP;
  3. a server purchase handler (ProcessReceipt, ProfileRepository.purchase) touches combat stats, growth, species,
     rarity, luck, eggs or other power fields, or does more than credit crystals;
  4. Marketplace purchase code appears outside the allowed files, or the client crystal-pack UI is not gated by
     Config.CrystalPacksEnabled;
  5. paid random items lack the PolicyService gate (ProgressionService), the PaidRandomItemsEnabled/PaidRandomEligible
     server check (ProfileRepository) or the odds disclosure module (OddsCopy).
Usage: python tools/verify_robux_line.py [--selftest]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys as _sys  # noqa: E402
_sys.path.insert(0, str(Path(__file__).resolve().parent))
import profile_sources  # noqa: E402  (docs/150: ProfileRepository plus its parts)
SRC = ROOT / "src"
# Documented in docs/114 section 11a. Time-savers may stack up to this multiplier and never above the normal limit.
CONVENIENCE_CAP = 1.25
FORBIDDEN = re.compile(
    r"\b(damage|hp|health|speed|growth|scale|species|rarity|luck|mutation|shiny|big|egg|eggs|hatch|stat|stats|combat|"
    r"class|multiplier|boost|exclusive|weapon|armor|shield|fusion)\b", re.I)
FLAG_KEY = re.compile(r"(Robux|Pack|Paid|GamePass|Product|Purchase)", re.I)
PURCHASE_API = re.compile(r"PromptProductPurchase|PromptGamePassPurchase|PromptPurchase|UserOwnsGamePassAsync|ProcessReceipt")
ALLOWED_PURCHASE_FILES = {"src/client/Bootstrap.client.luau", "src/client/ShopScreens.luau", "src/server/Bootstrap.server.luau", "src/server/ProfileRepository.luau", "src/server/ProfileShop.luau"}


def strip(text: str) -> str:
    return "\n".join(re.sub(r"--.*$", "", line) for line in text.splitlines())


def block(text: str, start: str, end_pat: str) -> str:
    i = text.find(start)
    if i < 0:
        return ""
    m = re.search(end_pat, text[i + len(start):], re.M)
    return text[i:i + len(start) + (m.start() if m else len(text))]


def check(read) -> list[str]:
    errs: list[str] = []
    cfg = strip(read("src/shared/Config.luau"))
    for key, val in re.findall(r"^\s*([A-Za-z_]\w*)\s*=\s*(true|false)\b", cfg, re.M):
        if FLAG_KEY.search(key) and val == "true":
            errs.append(f"Config.{key} is true in the default profile (Robux flags stay off until policy is tested)")
    for flag in ("CrystalPacksEnabled", "PaidRandomItemsEnabled"):
        if not re.search(rf"^\s*{flag}\s*=\s*false\b", cfg, re.M):
            errs.append(f"Config.{flag} must exist and be false")
    m = re.search(r"DeveloperProducts\s*=\s*\{(.*?)\}", cfg, re.S)
    if not m:
        errs.append("Config.DeveloperProducts not found")
    else:
        for pid, amt in re.findall(r"\[\s*(\d+)\s*\]\s*=\s*([^,}\s]+)", m.group(1)):
            if not re.fullmatch(r"[1-9]\d*", amt):
                errs.append(f"developer product {pid} must grant a positive whole crystal count, got {amt}")
    for ln in cfg.splitlines():
        if re.search(r"GamePass|Gamepass|Bundle|RobuxProduct", ln) and "=" in ln and "Requires" not in ln:
            if FORBIDDEN.search(ln):
                errs.append(f"Robux-linked config row grants power: {ln.strip()[:100]}")
            for num in re.findall(r"=\s*(\d+\.?\d*)", ln):
                if float(num) > CONVENIENCE_CAP and re.search(r"Mult|Boost|Factor", ln, re.I):
                    errs.append(f"Robux-linked multiplier above cap {CONVENIENCE_CAP}: {ln.strip()[:100]}")
    repo = strip(chr(10).join(read(rel) for rel in profile_sources.files()))  # docs/150: ProfileRepository + its parts
    boot = strip(read("src/server/Bootstrap.server.luau"))
    purchase = block(repo, "function ProfileRepository.purchase", r"^end\b")
    receipt = block(boot, "ProcessReceipt=function", r"^end\b")
    if not purchase or not receipt:
        errs.append("purchase handler (ProfileRepository.purchase / ProcessReceipt) not found")
    else:
        body = re.sub(r"\"[^\"]*\"", '""', purchase + "\n" + receipt)
        for w in sorted(set(x.lower() for x in FORBIDDEN.findall(body))):
            errs.append(f"purchase handler touches power word '{w}' (Robux may only credit crystals)")
        if not re.search(r"progress\.crystals\s*\+=\s*crystals", purchase):
            errs.append("purchase handler no longer credits crystals")
        if len(re.findall(r"progress\.\w+\s*\+?=", purchase)) != 1:
            errs.append("purchase handler writes more than the crystal balance")
    for p in sorted(SRC.rglob("*.lua*")):
        rel = p.relative_to(ROOT).as_posix()
        if PURCHASE_API.search(strip(read(rel))) and rel not in ALLOWED_PURCHASE_FILES:
            errs.append(f"{rel} uses Marketplace purchase APIs outside the allowed files")
    client = strip(read("src/client/Bootstrap.client.luau") + read("src/client/ShopScreens.luau"))  # BD-1020: the crystal-pack cards moved with the shop screens
    if "PromptProductPurchase" in client and "CrystalPacksEnabled" not in client:
        errs.append("client crystal-pack UI is not gated by Config.CrystalPacksEnabled")
    prog = strip(read("src/server/ProgressionService.luau"))
    if "PolicyService" not in prog or "ArePaidRandomItemsRestricted" not in prog:
        errs.append("ProgressionService lost the PolicyService / ArePaidRandomItemsRestricted gate")
    if "PaidRandomItemsEnabled" not in repo or "PaidRandomEligible" not in repo:
        errs.append("ProfileRepository lost the PaidRandomItemsEnabled / PaidRandomEligible server gate")
    if not (SRC / "shared" / "OddsCopy.luau").exists():
        errs.append("odds disclosure module src/shared/OddsCopy.luau is missing")
    return errs


def main() -> int:
    def read(rel: str) -> str:
        return (ROOT / rel).read_text(encoding="utf-8")

    errs = check(read)
    if "--selftest" in sys.argv:
        bad = {
            "flag": ("Config.luau", "CrystalPacksEnabled = false", "CrystalPacksEnabled = true"),
            "power": ("ProfileShop.luau", "progress.crystals+=crystals", "progress.crystals+=crystals progress.speed+=1"),
            "policy": ("ProgressionService.luau", "ArePaidRandomItemsRestricted", "X"),
        }
        for name, (suffix, a, b) in bad.items():
            def mutated(rel, suffix=suffix, a=a, b=b):
                t = read(rel)
                return t.replace(a, b) if rel.endswith(suffix) else t
            if not check(mutated):
                print(f"selftest FAILED: mutation '{name}' was not caught")
                return 1
        print("selftest ok: 3 mutations caught")
    if errs:
        print("Robux line violations (docs/114 section 11a):")
        for e in errs:
            print(" -", e)
        return 1
    print("verify_robux_line ok: crystal-only products, flags off, PolicyService and odds gates present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
