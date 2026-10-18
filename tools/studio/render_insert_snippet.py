#!/usr/bin/env python3
"""Print tools/studio/insert_uploaded_model.luau with the three placeholders filled in (docs/169, BD-659).

  python tools/studio/render_insert_snippet.py --asset-id 123456789 --name Cockatoosaurus --group "Silly secret dinos v3" [--live] [--create-group]

Paste the output into the Studio MCP execute_luau. Default is the DryRun version (prints the plan, changes nothing).
"""
import argparse
import re
import sys
from pathlib import Path

TEMPLATE = Path(__file__).with_name("insert_uploaded_model.luau")


def joints_table(joints):
    """'Head=Body,Crest=Head' (child=parent pairs) -> Luau table text for the snippet's Joints option."""
    pairs = []
    for item in joints.split(","):
        bits = item.strip().split("=")
        if len(bits) != 2 or not all(re.fullmatch(r"[A-Za-z0-9_]{1,40}", b) for b in bits):
            raise ValueError("joints must look like Head=Body,Crest=Head (child=parent), got %r" % item)
        pairs.append('["%s"] = "%s"' % (bits[0], bits[1]))
    return "{ " + ", ".join(pairs) + " }"


def render(asset_id, name, group, live=False, create_group=False, joints=None):
    if not str(asset_id).isdigit():
        raise ValueError("asset id must be digits only")
    for label, value in (("name", name), ("group", group)):
        if not re.fullmatch(r"[A-Za-z0-9 _.\-]{1,60}", value):
            raise ValueError("%s may only use letters, digits, space, _ . -" % label)
    text = TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("__ASSET_ID__", str(int(asset_id))).replace("__NAME__", name).replace("__GROUP__", group)
    if live:
        text = text.replace("DryRun = true,", "DryRun = false,", 1)
    if create_group:
        text = text.replace("CreateGroup = false,", "CreateGroup = true,", 1)
    if joints:
        text = text.replace("Joints = nil,", "Joints = %s," % joints_table(joints), 1)
    return text


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset-id", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--group", required=True)
    ap.add_argument("--live", action="store_true", help="DryRun = false (really insert)")
    ap.add_argument("--create-group", action="store_true", help="allow creating the group folder (for the acceptance test)")
    ap.add_argument("--joints", help="child=parent pairs for parts that came without Motor6D, e.g. Head=Body,Crest=Head")
    a = ap.parse_args()
    try:
        sys.stdout.write(render(a.asset_id, a.name, a.group, a.live, a.create_group, a.joints))
    except ValueError as exc:
        sys.exit("ERROR: %s" % exc)
