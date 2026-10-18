#!/usr/bin/env python3
"""Upload a 3D model (FBX / glTF), image or sound to Roblox through the Open Cloud Assets API (docs/169, BD-659).

  python tools/roblox_asset_upload.py model.fbx --name Cockatoo          # DRY RUN: checks the file, prints the request, sends nothing
  python tools/roblox_asset_upload.py model.fbx --name Cockatoo --upload # really uploads, waits, prints the asset id
  python tools/roblox_asset_upload.py model.fbx --name Cockatoo --upload --register   # also appends a line to the registry JSON

Safety rules (the owner's, 2026-10-18):
  * The API key is read ONLY from the environment variable ROBLOX_OPEN_CLOUD_KEY. There is no key argument, no key file,
    and the key is never printed, logged, written or echoed. Anything that comes back from the network is scrubbed first.
  * The creator (who owns the asset) comes from ROBLOX_CREATOR_USER_ID (or ROBLOX_CREATOR_GROUP_ID), or from a small JSON
    file OUTSIDE the repo: ~/.be-dino/roblox_upload.json  {"creator_user_id": 123}  (path can be changed with --config).
  * Dry run is the default. Only --upload sends anything.
  * Size limit 20 MB per file (docs: "up to 20 MB" per call); at most 5 files per run; a pause between files.
  * This tool never touches Studio and never publishes a place. It only creates assets in the creator's inventory.

Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_BASE = "https://apis.roblox.com/assets/v1"
KEY_ENV = "ROBLOX_OPEN_CLOUD_KEY"
USER_ENV = "ROBLOX_CREATOR_USER_ID"
GROUP_ENV = "ROBLOX_CREATOR_GROUP_ID"
DEFAULT_CONFIG = Path.home() / ".be-dino" / "roblox_upload.json"
DEFAULT_REGISTRY = ROOT / "docs" / "evidence" / "roblox-uploads.json"

MAX_BYTES = 20 * 1024 * 1024  # documented per-call limit (usage-assets guide, read 2026-10-18)
MAX_FILES = 5  # our own safety cap per run
PAUSE_BETWEEN_FILES = 3.0  # seconds
POLL_SECONDS = 2.0
POLL_TIMEOUT = 180.0
MAX_429_RETRIES = 3
NAME_MAX = 50  # our own cap (Roblox display names are short); UNVERIFIED exact limit
DESCRIPTION_MAX = 1000  # our own cap; UNVERIFIED exact limit

# extension -> (assetType, content type). Only formats the documented API accepts for each type.
FORMATS = {
    ".fbx": ("Model", "model/fbx"),
    ".gltf": ("Model", "model/gltf+json"),
    ".glb": ("Model", "model/gltf-binary"),
    ".png": ("Decal", "image/png"),
    ".jpg": ("Decal", "image/jpeg"),
    ".jpeg": ("Decal", "image/jpeg"),
    ".bmp": ("Decal", "image/bmp"),
    ".tga": ("Decal", "image/tga"),
    ".mp3": ("Audio", "audio/mpeg"),
    ".ogg": ("Audio", "audio/ogg"),
    ".wav": ("Audio", "audio/wav"),
    ".flac": ("Audio", "audio/flac"),
}
# .rbxm / .rbxmx are accepted by Roblox but only for files Studio itself saved; not supported here on purpose.


class UploadError(Exception):
    """A problem with the file, the setup or the answer from Roblox. The message is already scrubbed."""


# --------------------------------------------------------------------------- secrets

def scrub(text, key=None):
    """Remove the API key (and anything shaped like one) from text before it is shown or stored."""
    text = str(text)
    if key:
        text = text.replace(key, "[KEY-REMOVED]")
    return text


def get_key(environ=None):
    environ = os.environ if environ is None else environ
    key = (environ.get(KEY_ENV) or "").strip()
    return key or None


# --------------------------------------------------------------------------- setup

def load_creator(environ=None, config_path=None):
    """Return ('userId'|'groupId', int). Environment first, then the config file outside the repo."""
    environ = os.environ if environ is None else environ
    for env, kind in ((USER_ENV, "userId"), (GROUP_ENV, "groupId")):
        raw = (environ.get(env) or "").strip()
        if raw:
            if not raw.isdigit():
                raise UploadError("%s must be a number (digits only)." % env)
            return kind, int(raw)
    path = Path(config_path) if config_path else DEFAULT_CONFIG
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise UploadError("Could not read %s: %s" % (path, exc))
        for field, kind in (("creator_user_id", "userId"), ("creator_group_id", "groupId")):
            if isinstance(data.get(field), int) and data[field] > 0:
                return kind, data[field]
    raise UploadError(
        "No creator id. Set %s (your Roblox user id, digits only) or write {\"creator_user_id\": 123} to %s" % (USER_ENV, path)
    )


def check_file(path):
    """Return (assetType, contentType, size, sha256hex) or raise UploadError."""
    p = Path(path)
    if not p.is_file():
        raise UploadError("File not found: %s" % p)
    ext = p.suffix.lower()
    if ext not in FORMATS:
        raise UploadError("File type %s is not supported (allowed: %s)." % (ext or "none", ", ".join(sorted(FORMATS))))
    size = p.stat().st_size
    if size == 0:
        raise UploadError("%s is empty." % p.name)
    if size > MAX_BYTES:
        raise UploadError("%s is %.1f MB; the Assets API limit is 20 MB per file." % (p.name, size / 1048576))
    head = p.read_bytes()[:32]
    if ext == ".fbx" and not (head.startswith(b"Kaydara FBX Binary") or head.lstrip().startswith(b"; FBX")):
        raise UploadError("%s does not look like an FBX file (wrong header)." % p.name)
    if ext == ".glb" and not head.startswith(b"glTF"):
        raise UploadError("%s does not look like a .glb file (wrong header)." % p.name)
    asset_type, ctype = FORMATS[ext]
    return asset_type, ctype, size, sha256(p.read_bytes()).hexdigest()


def clean_name(name, fallback):
    name = re.sub(r"[^A-Za-z0-9 _.\-]", "", name or "").strip() or fallback
    return name[:NAME_MAX]


def build_request_json(asset_type, name, description, creator):
    kind, number = creator
    return {
        "assetType": asset_type,
        "displayName": name,
        "description": description[:DESCRIPTION_MAX],
        "creationContext": {"creator": {kind: str(number)}},
    }


def multipart(request_json, filename, content_type, data):
    """Build the multipart body by hand (stdlib only). Returns (body_bytes, content_type_header)."""
    boundary = "----bedino" + uuid.uuid4().hex
    safe = re.sub(r'[^A-Za-z0-9_.\-]', "_", filename)
    parts = [
        ("--%s\r\nContent-Disposition: form-data; name=\"request\"\r\nContent-Type: application/json\r\n\r\n" % boundary).encode(),
        json.dumps(request_json).encode(),
        ("\r\n--%s\r\nContent-Disposition: form-data; name=\"fileContent\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n" % (boundary, safe, content_type)).encode(),
        data,
        ("\r\n--%s--\r\n" % boundary).encode(),
    ]
    return b"".join(parts), "multipart/form-data; boundary=%s" % boundary


# --------------------------------------------------------------------------- HTTP (replaceable in tests)

def http_request(method, url, headers, body=None, timeout=60):
    """Real network call. Returns (status, response_headers_dict, body_bytes). Never raises for HTTP error codes."""
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise UploadError("Network problem: %s" % getattr(exc, "reason", exc))


def _json(body, key):
    try:
        return json.loads(body.decode("utf-8", "replace") or "{}")
    except ValueError:
        raise UploadError("Roblox answered with something that is not JSON: %s" % scrub(body[:200], key))


def _call(transport, method, url, key, body=None, content_type=None, sleep=time.sleep):
    """One API call with a small back-off on HTTP 429. The key only ever goes into the x-api-key header."""
    headers = {"x-api-key": key, "Accept": "application/json"}
    if content_type:
        headers["Content-Type"] = content_type
    for attempt in range(MAX_429_RETRIES + 1):
        status, resp_headers, data = transport(method, url, headers, body)
        if status != 429:
            return status, data
        if attempt == MAX_429_RETRIES:
            break
        wait = 5
        try:
            wait = min(60, max(1, int(float(resp_headers.get("Retry-After", wait)))))
        except (TypeError, ValueError):
            pass
        sleep(wait * (attempt + 1))
    raise UploadError("Roblox says slow down (HTTP 429) and kept saying it. Wait a few minutes and run again.")


def explain_http(status, data, key):
    text = scrub(data[:400].decode("utf-8", "replace"), key)
    hint = {
        400: "The request was rejected (bad file or fields).",
        401: "The key was not accepted. Check it is current and has the Assets Read+Write permission.",
        403: "The key is not allowed to do this (permission, creator id, or experience/IP restriction).",
        404: "Not found.",
    }.get(status, "")
    return "HTTP %d. %s %s" % (status, hint, text)


def upload_one(path, name, description, creator, key, transport=http_request, sleep=time.sleep,
               poll_seconds=POLL_SECONDS, poll_timeout=POLL_TIMEOUT, log=print):
    """Upload one file and wait for the operation. Returns a dict with assetId etc."""
    asset_type, ctype, size, digest = check_file(path)
    request_json = build_request_json(asset_type, name, description, creator)
    body, content_type = multipart(request_json, Path(path).name, ctype, Path(path).read_bytes())
    status, data = _call(transport, "POST", API_BASE + "/assets", key, body, content_type, sleep)
    if status not in (200, 201):
        raise UploadError(explain_http(status, data, key))
    op = _json(data, key)
    op_path = op.get("path")
    if not op_path or not re.fullmatch(r"operations/[A-Za-z0-9\-_]+", op_path):
        raise UploadError("Roblox did not return an operation path: %s" % scrub(json.dumps(op)[:200], key))
    log("  sent; waiting for %s" % op_path)
    waited = 0.0
    while True:
        status, data = _call(transport, "GET", API_BASE + "/" + op_path, key, sleep=sleep)
        if status != 200:
            raise UploadError(explain_http(status, data, key))
        result = _json(data, key)
        if result.get("done"):
            break
        if waited >= poll_timeout:
            raise UploadError("Still not done after %d s (operation %s). Check Creator Hub > Inventory later." % (poll_timeout, op_path))
        sleep(poll_seconds)
        waited += poll_seconds
    if result.get("error"):
        err = result["error"]
        raise UploadError("Roblox refused the asset: %s" % scrub(json.dumps(err)[:400], key))
    resp = result.get("response") or {}
    asset_id = str(resp.get("assetId") or "")
    if not asset_id.isdigit():
        raise UploadError("Operation finished but no asset id came back: %s" % scrub(json.dumps(result)[:300], key))
    moderation = ((resp.get("moderationResult") or {}).get("moderationState")) or "unknown"
    return {
        "assetId": asset_id,
        "assetType": asset_type,
        "displayName": name,
        "file": Path(path).name,
        "bytes": size,
        "sha256": digest,
        "moderation": moderation,
        "uploaded": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def register(entry, registry_path):
    """Append one entry to the registry JSON (a list). Contains no secrets and no creator id."""
    p = Path(registry_path)
    items = []
    if p.is_file():
        try:
            items = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            raise UploadError("%s is not valid JSON; fix it by hand first." % p)
    items.append(entry)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(items, indent=2) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- command line

def parse_args(argv):
    ap = argparse.ArgumentParser(description="Upload models/images/sounds to Roblox via Open Cloud. Dry run unless --upload.")
    ap.add_argument("files", nargs="+", help="file(s) to upload (.fbx .gltf .glb .png .jpg .mp3 .ogg ...), at most %d" % MAX_FILES)
    ap.add_argument("--name", help="display name (default: the file name). With several files the file name is used for each.")
    ap.add_argument("--description", default="Be Dino! asset (uploaded by tools/roblox_asset_upload.py)")
    ap.add_argument("--upload", action="store_true", help="really send the files (default is a dry run)")
    ap.add_argument("--register", action="store_true", help="after a successful upload append a line to the registry JSON")
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY), help="registry JSON path (default docs/evidence/roblox-uploads.json)")
    ap.add_argument("--config", help="creator config JSON (default ~/.be-dino/roblox_upload.json, outside the repo)")
    ap.add_argument("--timeout", type=float, default=POLL_TIMEOUT, help="seconds to wait for each operation")
    return ap.parse_args(argv)


def main(argv=None, environ=None, transport=http_request, sleep=time.sleep, out=print):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    environ = os.environ if environ is None else environ
    key = get_key(environ)
    try:
        if len(args.files) > MAX_FILES:
            raise UploadError("At most %d files per run (you gave %d)." % (MAX_FILES, len(args.files)))
        creator = load_creator(environ, args.config)
        checked = []
        for f in args.files:
            asset_type, ctype, size, digest = check_file(f)
            stem = Path(f).stem
            name = clean_name(args.name if (args.name and len(args.files) == 1) else stem, stem)
            checked.append((f, name, asset_type, ctype, size))
        if not args.upload:
            out("DRY RUN: nothing is sent. Add --upload to send.")
            out("Key present in %s: %s" % (KEY_ENV, "yes" if key else "NO (needed for --upload)"))
            for f, name, asset_type, ctype, size in checked:
                req = build_request_json(asset_type, name, args.description, creator)
                out("Would POST %s/assets  (header x-api-key: <hidden>)" % API_BASE)
                out("  request = %s" % json.dumps(req))
                out("  fileContent = %s  (%s, %.2f MB)" % (Path(f).name, ctype, size / 1048576))
                out("Then poll GET %s/operations/<id> every %ds up to %ds." % (API_BASE, POLL_SECONDS, args.timeout))
            return 0
        if not key:
            raise UploadError("%s is not set. Set it once as a user environment variable (docs/169 section 3), then open a NEW terminal." % KEY_ENV)
        results = []
        for i, (f, name, asset_type, ctype, size) in enumerate(checked):
            if i:
                sleep(PAUSE_BETWEEN_FILES)
            out("Uploading %s as %s %r ..." % (Path(f).name, asset_type, name))
            entry = upload_one(f, name, args.description, creator, key, transport, sleep, POLL_SECONDS, args.timeout, out)
            results.append(entry)
            out("ASSET_ID %s  rbxassetid://%s  (moderation: %s)" % (entry["assetId"], entry["assetId"], entry["moderation"]))
            if args.register:
                register(entry, args.registry)
                out("  registered in %s" % args.registry)
        return 0
    except UploadError as exc:
        print("ERROR: %s" % scrub(exc, key), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
