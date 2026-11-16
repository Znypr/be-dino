#!/usr/bin/env python3
"""Receive ONE file the browser page posts to http://127.0.0.1:<port>/save?name=<file> and write it to build/received/<file>, then exit
(or exit after --timeout seconds). Used to save an owner-approved ChatGPT picture into the ignored build folder, never Downloads.

    python tools/local_receiver.py [--port 8766] [--timeout 180]
"""
import argparse
import pathlib
import re
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "build/received"


class Handler(BaseHTTPRequestHandler):
    done = False

    def cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def do_OPTIONS(self):
        self.send_response(204)
        self.cors()
        self.end_headers()

    def do_POST(self):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        name = re.sub(r"[^A-Za-z0-9_.-]", "_", (query.get("name") or ["received.png"])[0])
        data = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / name).write_bytes(data)
        self.send_response(200)
        self.cors()
        self.end_headers()
        self.wfile.write(b"ok")
        print("saved", OUT / name, len(data), "bytes", flush=True)
        Handler.done = True

    def log_message(self, *args):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--timeout", type=int, default=180)
    a = ap.parse_args()
    server = HTTPServer(("127.0.0.1", a.port), Handler)
    server.timeout = 2
    import time
    end = time.time() + a.timeout
    while not Handler.done and time.time() < end:
        server.handle_request()
    sys.exit(0 if Handler.done else 1)


if __name__ == "__main__":
    main()
