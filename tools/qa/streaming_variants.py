"""docs/147 (BD-498 experiment): make StreamingEnabled / forced-phone COPIES of a built place, for a Studio session. Never touches src/, the default or the playtest
profile, or the repo's build output; the shipped places keep StreamingEnabled OFF.

  python tools/build.py --profile playtest --output C:/tmp/stream-off.rbxlx
  python tools/qa/streaming_variants.py C:/tmp/stream-off.rbxlx C:/tmp/stream-on.rbxlx --target 256 --min 128
  python tools/qa/streaming_variants.py C:/tmp/stream-off.rbxlx C:/tmp/stream-on-phone.rbxlx --target 256 --min 128 --phone

--off writes the unchanged place plus the probe only (the control). --phone patches the device classifiers of WorldCulling, ContactShadow, CavePhoneGuard and
WeatherVisuals to "Phone" in the COPY (Studio on a PC cannot emulate a touch phone for them). The probe is tools/qa/streaming_probe.client.luau.
Workspace.StreamingTargetRadius / StreamingMinRadius are not scriptable in Studio, so they are written into the .rbxlx as properties (verified by behaviour: the
streamed part counts follow the radius, docs/147 s3).
"""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


PHONE_PATCHES = [
    ('    if not UserInputService.TouchEnabled then return "Desktop" end\n    local size = camera.ViewportSize\n'
     '    return if math.min(size.X, size.Y) >= 600 then "Tablet" else "Phone"', '    return "Phone" -- SCRATCH forced phone', 2),
    ("device = Recipes.deviceClass(UserInputService.TouchEnabled, UserInputService.MouseEnabled, math.min(camera.ViewportSize.X, camera.ViewportSize.Y))",
     'device = "phone" -- SCRATCH forced phone', 1),
    ("local phone=UserInputService.TouchEnabled and not UserInputService.MouseEnabled", "local phone=true -- SCRATCH forced phone", 1),
    ('return if not UserInputService.TouchEnabled then "Desktop" elseif math.min(size.X,size.Y)>=600 then "Tablet" else "Phone"', 'return "Phone" -- SCRATCH', 1),
]


def make(source: str, streaming: bool, target: int, minimum: int, phone: bool) -> str:
    place = source
    old = '<string name="Name">Workspace</string>\n'
    if place.count(old) != 1:
        raise SystemExit("expected exactly one Workspace item")
    if streaming:
        place = place.replace(old, old + f'      <bool name="StreamingEnabled">true</bool>\n      <int name="StreamingTargetRadius">{target}</int>\n'
                                        f'      <int name="StreamingMinRadius">{minimum}</int>\n')
    probe = esc((ROOT / "tools/qa/streaming_probe.client.luau").read_text(encoding="utf-8"))
    marker = '<string name="Name">ReplicatedFirst</string>\n    </Properties>\n'
    if place.count(marker) != 1:
        raise SystemExit("expected exactly one ReplicatedFirst item")
    item = ('    <Item class="LocalScript" referent="RBXPROBE1">\n      <Properties>\n        <string name="Name">ZProbe</string>\n'
            f'        <ProtectedString name="Source">{probe}</ProtectedString>\n      </Properties>\n    </Item>\n')
    place = place.replace(marker, marker + item)
    if phone:
        for before, after, count in PHONE_PATCHES:
            if place.count(esc(before)) != count:
                raise SystemExit(f"phone patch no longer matches the source (expected {count}): {before[:60]}")
            place = place.replace(esc(before), esc(after))
    return place


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument("--target", type=int, default=256, help="StreamingTargetRadius")
    parser.add_argument("--min", type=int, default=128, help="StreamingMinRadius")
    parser.add_argument("--off", action="store_true", help="control: probe only, StreamingEnabled stays false")
    parser.add_argument("--phone", action="store_true", help="force the Phone device class in the copy")
    args = parser.parse_args()
    text = Path(args.source).read_text(encoding="utf-8", newline="")
    result = make(text, not args.off, args.target, args.min, args.phone)
    Path(args.output).write_text(result, encoding="utf-8", newline="")
    print(f"wrote {args.output} (streaming={'off' if args.off else f'{args.target}/{args.min}'}, phone={args.phone})")
