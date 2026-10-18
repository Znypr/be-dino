"""Where the ProfileRepository code lives (docs/150), for the verifiers that read or embed it.

src/server/ProfileRepository.luau keeps the shared infrastructure (store wrappers, lease, retry, admit, load / migration, renew /
release) and installs the transaction groups from sibling modules (ProfileFusion, ProfileEggs, ...) with
`require(script.Parent.<Part>)(ProfileRepository, shared)`. The parts keep their `function ProfileRepository.<name>` bodies verbatim, so:

  * `repository_text()` is the main file followed by every part: use it wherever a verifier used to read ProfileRepository.luau
    and look for a function, a call or a string (the text of each function is exactly what it was before the split);
  * `module(path)` is the Luau expression the textual harnesses embed for a module; for ProfileRepository it wraps the main file so
    that `require(script.Parent.<Part>)` yields the part's installer function embedded next to it, with no extra stubs.

The part list is read from the main file, so adding a part needs no change here.
"""
from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MAIN = "src/server/ProfileRepository.luau"
_PART = re.compile(r"^require\(script\.Parent\.(\w+)\)\(ProfileRepository, shared\)\s*$", re.M)


def read(path: str | Path, root: Path = ROOT) -> str:
    return (root / path).read_text(encoding="utf-8")


def parts(root: Path = ROOT) -> list[str]:
    """Module names (files under src/server) the repository installs, in install order."""
    return _PART.findall(read(MAIN, root))


def repository_text(root: Path = ROOT) -> str:
    """ProfileRepository.luau followed by every part, one string (line endings normalised to LF)."""
    chunks = [read(MAIN, root)] + [read(f"src/server/{name}.luau", root) for name in parts(root)]
    return "\n".join(chunks)


def module(path: str | Path, root: Path = ROOT) -> str:
    """A Luau expression evaluating to the module at `path` (relative to the repository root)."""
    path = str(path).replace("\\", "/")
    text = read(path, root)
    if path != MAIN:
        return "(function()\n" + text + "\nend)()"
    installers = ", ".join(f"{name} = (function()\n{read(f'src/server/{name}.luau', root)}\nend)()" for name in parts(root))
    return (
        "(function()\n"
        "local __harnessScript, __harnessRequire = script, require\n"
        "local script = {Parent = setmetatable({" + installers + "}, {__index = __harnessScript.Parent})}\n"
        "local require = function(id) if type(id) == 'function' then return id end return __harnessRequire(id) end\n"
        + text + "\nend)()"
    )


_SECRET_SLOT = re.compile(r'(\{ id = "\w+", name = "[^"]+", secret = true, class = "\w+", weight = \d+, assetId = )\d+( \})')


def neutral_secret_module(root: Path = ROOT) -> str:
    """The real src/shared/SecretSpeciesConfig.luau with EVERY model slot set to 0 (docs/173): a Luau expression like `module()`.

    The playtest binds real model ids (the Foxosaurus), so a harness that serves the shipped module to RewardMath would see one extra random draw per
    earned egg (the secret roll) the moment SecretSpeciesEnabled is on, which shifts every seeded sequence of the rewards-family verifiers (rewards,
    rollback, skins, gifts ...). Those verifiers are about eggs, saves and Build 020, not about secrets: they get this neutral copy, and
    tools/verify_secret_species.py proves the secret rules and the shipped roster on their own.
    """
    text = _SECRET_SLOT.sub(lambda m: m.group(1) + "0" + m.group(2), read("src/shared/SecretSpeciesConfig.luau", root))
    return "(function()\n" + text + "\nend)()"


def files(root: Path = ROOT) -> list[str]:
    """Repo-relative paths of the main file and every part."""
    return [MAIN] + [f"src/server/{name}.luau" for name in parts(root)]
