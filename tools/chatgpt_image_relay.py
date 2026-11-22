#!/usr/bin/env python3
"""BD-1289: save ChatGPT-generated pictures at full size into build/received/ (ignored), never Downloads.

ChatGPT's page blocks posting to 127.0.0.1 (its security policy), so tools/local_receiver.py can't be reached from it.
This relay serves a tiny page on 127.0.0.1; the ChatGPT tab hands each picture to that page with window.postMessage,
and the page posts it to its own origin, which is allowed.

    python tools/chatgpt_image_relay.py                 # listen on 8767 for 1 picture, quit after 240 s
    python tools/chatgpt_image_relay.py --count 3       # wait for 3 pictures
    python tools/chatgpt_image_relay.py --snippet NAME  # print the browser snippet that sends the newest generated image as NAME

Order that works (Claude in Chrome):
  1. start this tool (background);
  2. in the ChatGPT tab run the --snippet JavaScript (javascript_tool). It opens the relay page itself
     (a relay tab opened by the extension is in another browsing group, so window.open('', name) can't find it:
     it made an empty about:blank tab and timed out, 2026-11-22). It reports {"saved": NAME, "status": 200};
  3. close the relay tab it opened.
Files land in build/received/NAME. Exit code 0 when all pictures arrived, 1 on timeout.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "received"
NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,80}\.(png|jpg|jpeg|webp)$")

PAGE = b"""<!doctype html><meta charset=utf-8><title>relay</title><body>Be Dino relay ready
<script>
window.name = 'beDinoRelay';
window.addEventListener('message', async (e) => {
  const d = e.data || {};
  if (!d.name || !d.blob) return;
  const r = await fetch('/save?name=' + encodeURIComponent(d.name), {method: 'POST', body: d.blob});
  document.body.append(' saved ' + d.name + ' ' + r.status);
  if (e.source) e.source.postMessage({saved: d.name, status: r.status}, '*');
});
</script>"""

SNIPPET = """const imgs = [...document.querySelectorAll('img[alt^="Generated image"]')];
const blob = await (await fetch(imgs[imgs.length - 1].src)).blob();
const w = window.open('http://127.0.0.1:%d/', 'beDinoRelay');
await new Promise(r => setTimeout(r, 3000));
w.postMessage({name: %s, blob}, '*');
const saved = await new Promise(r => { const h = e => { if (e.data && e.data.saved) { window.removeEventListener('message', h); r(e.data) } };
  window.addEventListener('message', h); setTimeout(() => r('timeout'), 15000) });
JSON.stringify(saved) + ' bytes=' + blob.size"""


def safe_name(name: str) -> str | None:
    return name if NAME_RE.match(name or "") else None


def make_handler(state: dict, out: pathlib.Path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(PAGE)

        def do_POST(self):
            m = re.search(r"[?&]name=([^&]+)", self.path)
            name = safe_name(m.group(1)) if m else None
            length = int(self.headers.get("Content-Length", "0") or 0)
            data = self.rfile.read(length) if 0 < length <= 30_000_000 else b""
            if not name or not data:
                self.send_response(400)
                self.end_headers()
                return
            out.mkdir(parents=True, exist_ok=True)
            (out / name).write_bytes(data)
            print(f"saved {name} {len(data)} bytes -> {out / name}", flush=True)
            self.send_response(200)
            self.end_headers()
            state["left"] -= 1
            if state["left"] <= 0:
                state["ok"] = True
                threading.Thread(target=self.server.shutdown, daemon=True).start()
    return Handler


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=8767)
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--snippet", metavar="NAME", help="print the browser snippet for NAME and exit")
    a = ap.parse_args(argv)
    if a.snippet:
        if not safe_name(a.snippet):
            print("NAME must look like picture-name.png")
            return 2
        print(SNIPPET % (a.port, json.dumps(a.snippet)))
        return 0
    state = {"left": max(1, a.count), "ok": False}
    srv = HTTPServer(("127.0.0.1", a.port), make_handler(state, OUT))
    timer = threading.Timer(a.timeout, srv.shutdown)
    timer.daemon = True
    timer.start()
    print(f"listening on http://127.0.0.1:{a.port}/ for {state['left']} picture(s)", flush=True)
    srv.serve_forever()
    return 0 if state["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
