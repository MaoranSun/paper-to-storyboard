#!/usr/bin/env python3
"""
Start a local HTTP server in out_dir and (on macOS) open it.

Usage:
    python3 preview.py <out_dir> [port]
"""

import argparse
import http.server
import os
import socketserver
import subprocess
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("port", type=int, nargs="?", default=8765)
    args = ap.parse_args()

    if not args.out_dir.exists():
        print(f"ERROR: out_dir not found: {args.out_dir}", file=sys.stderr)
        sys.exit(2)

    os.chdir(str(args.out_dir))
    handler = http.server.SimpleHTTPRequestHandler
    url = f"http://localhost:{args.port}/"
    print(url)

    if sys.platform == "darwin":
        try:
            subprocess.Popen(["open", url])
        except Exception:
            pass

    with socketserver.TCPServer(("", args.port), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
