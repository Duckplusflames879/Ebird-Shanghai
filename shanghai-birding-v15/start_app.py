#!/usr/bin/env python3
"""Launch the Shanghai birding app with automatic external-data refresh.

The browser sandbox cannot execute Python when index.html is opened directly.
This tiny local server bridges that gap: it updates data on startup, serves the
same static app, and exposes /__auto_update so the page can refresh again while
it remains open.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent
UPDATE_SCRIPT = ROOT / "scripts" / "update_data.py"
MIN_AUTO_UPDATE_INTERVAL = 10 * 60
UPDATE_TIMEOUT = 30 * 60

class AppServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

class Handler(SimpleHTTPRequestHandler):
    server_version = "ShanghaiBirdingLauncher/1.0"

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        if self.path.startswith('/__'):
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def _json(self, payload, status=200):
        raw = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/__health':
            self._json(self.server.launcher_state())
            return
        if path == '/__auto_update':
            force = parse_qs(urlparse(self.path).query).get('force', ['0'])[0] == '1'
            self._json(self.server.auto_update(force=force))
            return
        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == '/__auto_update':
            length = int(self.headers.get('Content-Length', '0') or 0)
            if length:
                self.rfile.read(length)
            force = parse_qs(urlparse(self.path).query).get('force', ['0'])[0] == '1'
            self._json(self.server.auto_update(force=force))
            return
        self.send_error(404)

    def log_message(self, fmt, *args):
        if not self.path.startswith('/__'):
            super().log_message(fmt, *args)

class Launcher:
    def __init__(self, fixture: str | None = None):
        self.fixture = fixture
        self.lock = threading.Lock()
        self.last_attempt = 0.0
        self.auto_update_requests = 0
        self.last_result: dict = {
            'success': False, 'updated': False, 'skipped': False,
            'message': '尚未执行自动更新'
        }
        self.started_at = time.time()

    def run_update(self, force=False):
        now = time.time()
        if not force and now - self.last_attempt < MIN_AUTO_UPDATE_INTERVAL:
            return {**self.last_result, 'success': True, 'updated': False, 'skipped': True}
        if not self.lock.acquire(blocking=False):
            return {**self.last_result, 'success': True, 'updated': False, 'skipped': True, 'message': '更新正在进行中'}
        self.last_attempt = now
        try:
            command = [sys.executable, str(UPDATE_SCRIPT)]
            if self.fixture:
                command += ['--fixture', self.fixture]
            completed = subprocess.run(
                command, cwd=ROOT, capture_output=True, text=True, timeout=UPDATE_TIMEOUT
            )
            output = ((completed.stdout or '') + '\n' + (completed.stderr or '')).strip()
            if completed.returncode == 0:
                self.last_result = {
                    'success': True, 'updated': True, 'skipped': False,
                    'message': '自动更新成功', 'output': output,
                    'finishedAt': time.time()
                }
            else:
                self.last_result = {
                    'success': False, 'updated': False, 'skipped': False,
                    'message': '自动更新失败', 'output': output,
                    'finishedAt': time.time()
                }
            return self.last_result
        except Exception as exc:
            self.last_result = {
                'success': False, 'updated': False, 'skipped': False,
                'message': '自动更新异常', 'output': str(exc),
                'finishedAt': time.time()
            }
            return self.last_result
        finally:
            self.lock.release()

    def launcher_state(self):
        return {
            'running': True,
            'startedAt': self.started_at,
            'lastUpdate': self.last_result,
            'autoUpdateRequests': self.auto_update_requests,
        }


def serve(port: int, no_open: bool, fixture: str | None):
    launcher = Launcher(fixture)
    # Do the first update before the browser is opened, so the very first view
    # already contains a fresh snapshot.
    first = launcher.run_update(force=True)
    server = AppServer(('127.0.0.1', port), lambda *a, **kw: Handler(*a, directory=ROOT, **kw))
    server.launcher_state = launcher.launcher_state
    def auto_update(force=False):
        launcher.auto_update_requests += 1
        return launcher.run_update(force=force)
    server.auto_update = auto_update
    actual_port = server.server_address[1]
    url = f'http://127.0.0.1:{actual_port}/index.html'
    print(f'auto_update: {"success" if first.get("success") else "failed"}', flush=True)
    if first.get('output'):
        print(first['output'], flush=True)
    print(f'serving: {url}', flush=True)
    print('按 Ctrl+C 关闭本地服务。', flush=True)
    if not no_open:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-open', action='store_true')
    parser.add_argument('--fixture', help='Testing only: use a deterministic fixture instead of live APIs.')
    args = parser.parse_args()
    if args.fixture:
        fixture_path = Path(args.fixture)
        if not fixture_path.is_absolute():
            fixture_path = ROOT / fixture_path
        if not fixture_path.exists():
            raise SystemExit(f'fixture not found: {fixture_path}')
        args.fixture = str(fixture_path)
    serve(args.port, args.no_open, args.fixture)

if __name__ == '__main__':
    main()
