"""docs/152, BD-626: how a verifier knows it runs inside the switch-on rehearsal scratch tree.

tools/run_rehearsal.py sets the environment variable BD_REHEARSAL (to the profile name) for every verifier it starts in the scratch
tree, and ONLY there: plain CI and every manual run leave it unset, so the verifiers behave exactly as they always did.

Many verifiers open with a pin such as `assert(GameConfig.ObjectivesEnabled==false,"the committed Config has the flag off")` and then
run an off-state section before they flip the flag themselves. Under the rehearsal the Config carries the all-on values, so that pin
stopped the file before its flag-on tests ran. `pin()` swaps the pin for a line that puts THAT ONE flag into the off state in the
verifier's own mutable copy of the Config (the off-state section then runs for real, and every other flag stays on), or removes the
pin when the line is only a pin. The replaced text must still exist exactly once in CI, so the rewrite cannot drift silently.
"""
from __future__ import annotations

import os

PROFILE = os.environ.get("BD_REHEARSAL", "")
ACTIVE = bool(PROFILE)


def pin(text: str, old: str, rehearsal: str, *, label: str = "") -> str:
    """Return `text`; under the rehearsal with `old` replaced by `rehearsal`. `old` must occur exactly once either way."""
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"rehearsal pin {label or old[:60]!r} occurs {count} times (expected 1): the verifier changed, update its pin() call")
    return text.replace(old, rehearsal, 1) if ACTIVE else text


OVERLAY_MARKER = "\n\n-- rehearsal overlay (tools/run_rehearsal.py)"
OVERLAY_HEAD = "local BaseConfig = table.freeze({"


def committed_config(text: str) -> str:
    """The COMMITTED Config source, given the source the verifier read.

    Plain CI: `text` already is the committed source and comes back unchanged. In the rehearsal scratch tree, src/shared/Config.luau is
    the committed table renamed `BaseConfig` plus a tail that returns the all-on copy (tools/run_rehearsal.py overlay_config); this
    undoes exactly that, so a verifier that needs its own DEFAULT variant (the Legacy look, no cave hub) can still build it.
    """
    if OVERLAY_MARKER not in text:
        return text
    body = text.split(OVERLAY_MARKER, 1)[0].rstrip() + "\n"
    if body.count(OVERLAY_HEAD) != 1:
        raise SystemExit("rehearsal Config overlay has an unexpected shape; update rehearsal_env.committed_config")
    return body.replace(OVERLAY_HEAD, "return table.freeze({", 1)
