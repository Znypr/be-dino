"""Generate deterministic worst-case BD-060 profile serialization measurements.

The Studio acceptance record remains authoritative for Roblox HttpService byte
counts. This dependency-free mirror keeps the growth curve and safety assumptions
visible in CI without accessing any DataStore.
"""
from __future__ import annotations

import argparse
import json

DATASTORE_VALUE_LIMIT = 4_194_304
COUNTS = (500, 1_000, 5_000, 10_000)


def profile(count: int) -> dict:
    owner = "u:7285577648"
    instances = {}
    eggs = {}
    for sequence in range(1, count + 1):
        instance_id = f"{owner}/d:{sequence}"
        egg_id = f"storage-measurement-egg-{sequence}"
        genes = {
            "patternId": "06_wavy_stripes",
            "conditionId": "rainbow",
            "primaryColorId": "green",
            "secondaryColorId": "blue",
            "blend": 20,
            "hatchSuccess": True,
        }
        eggs[egg_id] = {
            "eggId": egg_id,
            "kind": "run_egg",
            "source": {"kind": "run", "operationId": f"run-{sequence}"},
            "eventId": "aurora",
            "mutationId": "ember",
            "big": sequence % 2 == 0,
            "shiny": sequence % 5 == 0,
            "genes": genes,
            "traitRollVersion": "build020-v1",
            "readyAt": 1_799_999_999,
            "reward": {"speciesId": "velociraptor", "count": 1},
        }
        instances[instance_id] = {
            "instanceId": instance_id,
            "bucketKey": "velociraptor/variant/06_wavy_stripes",
            "speciesId": "velociraptor",
            "stage": "base",
            "genes": genes.copy(),
            "traitRollVersion": "build020-v1",
            "big": sequence % 2 == 0,
            "shiny": sequence % 5 == 0,
            "mutationId": "ember",
            "traitsKnown": True,
            "origin": {"kind": "hatch", "eggId": egg_id},
            "cosmetics": {
                "ownedAuraIds": {},
                "ownedTrailIds": {},
                "equippedAuraId": "",
                "equippedTrailId": "",
            },
        }
    return {
        "schemaVersion": 9,
        "revision": 42,
        "collection": {},
        "progress": {},
        "eggs": {"nextId": 1, "items": {}, "order": []},
        "dinosaurIdentity": {
            "version": 1,
            "ownerKey": owner,
            "nextId": count + 1,
            "instances": instances,
            "eggs": eggs,
        },
    }


def encoded_size(count: int) -> int:
    return len(json.dumps(profile(count), separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    results = {count: encoded_size(count) for count in COUNTS}
    for count, size in results.items():
        print(f"{count:>5} dinosaurs: {size:>9} bytes ({size / DATASTORE_VALUE_LIMIT:>6.1%} of 4 MiB)")
    if args.check:
        assert results[1_000] < DATASTORE_VALUE_LIMIT
        assert results[5_000] > DATASTORE_VALUE_LIMIT
        assert results[10_000] > results[5_000] * 1.9


if __name__ == "__main__":
    main()
