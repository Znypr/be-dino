"""Sound Lab data check (BD-081 / BD-343, src/shared/SoundLabData.luau).

Static: every name in Sfx.Sounds and WeatherSounds.Sounds has a category in SoundLabData.CategoryOf, every category used
is declared in Lab.Categories and has a label, and the Settings Sound tab opens the lab. No Luau runtime needed.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def block(text: str, start: str) -> str:
    i = text.index(start)
    j = text.index("\n}", i)
    return text[i:j]


def main() -> int:
    sfx = (ROOT / "src/shared/Sfx.luau").read_text(encoding="utf-8")
    weather = (ROOT / "src/shared/WeatherSounds.luau").read_text(encoding="utf-8")
    lab = (ROOT / "src/shared/SoundLabData.luau").read_text(encoding="utf-8")
    menu = (ROOT / "src/client/SettingsMenu.luau").read_text(encoding="utf-8")
    names = set(re.findall(r"^\s+(\w+) = \{id =", block(sfx, "Sfx.Sounds = {"), re.M))
    names |= set(re.findall(r"^\s+(\w+)=\{id=", block(weather, "Sounds.Sounds={"), re.M))
    assert len(names) >= 28, f"expected at least 28 registered sounds, found {len(names)}"
    mapping = dict(re.findall(r"(\w+) = \"(\w+)\"", block(lab, "Lab.CategoryOf = table.freeze({")))
    missing = sorted(n for n in names if n not in mapping)
    assert not missing, f"sounds without a Sound Lab category: {missing}"
    cats_decl = set(re.findall(r'"(\w+)"', re.search(r"Lab\.Categories = table\.freeze\(\{(.*?)\}\)", lab, re.S).group(1)))
    labels = set(re.findall(r"(\w+) = \"[A-Z /]+\"", block(lab, "Lab.Labels = table.freeze({")))
    for cat in set(mapping.values()):
        assert cat in cats_decl, f"category {cat} not declared"
    for cat in cats_decl:
        assert cat in labels, f"category {cat} has no label"
    assert "Button_SoundLab" in menu and "SoundLab" in menu, "Settings Sound tab must open the Sound lab"
    print(f"Sound lab checks passed: {len(names)} registered sounds categorised, {len(cats_decl)} categories labelled")
    return 0


if __name__ == "__main__":
    sys.exit(main())
