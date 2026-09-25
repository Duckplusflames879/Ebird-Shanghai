import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data' / 'latest_data.js'
BACKUP = OUTPUT.read_bytes()
proc = subprocess.Popen(
    [sys.executable, str(ROOT / 'start_app.py'), '--port', '0', '--no-open', '--fixture', 'tests/external_fixture.json'],
    cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True,
)
try:
    port = None
    lines = []
    deadline = time.time() + 30
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            continue
        lines.append(line.rstrip())
        if line.startswith('serving:'):
            port = int(line.rsplit(':', 1)[1].split('/', 1)[0])
            break
    assert port, '\n'.join(lines)
    base = f'http://127.0.0.1:{port}'
    health = json.loads(urllib.request.urlopen(base + '/__health', timeout=10).read().decode())
    assert health['running'] is True
    assert health['lastUpdate']['success'] is True
    assert health['lastUpdate']['updated'] is True
    response = json.loads(urllib.request.urlopen(base + '/__auto_update', timeout=10).read().decode())
    assert response['success'] is True
    assert response['skipped'] is True, response
    forced = json.loads(urllib.request.urlopen(base + '/__auto_update?force=1', timeout=10).read().decode())
    assert forced['success'] is True
    assert forced['updated'] is True
    health2 = json.loads(urllib.request.urlopen(base + '/__health', timeout=10).read().decode())
    assert health2['autoUpdateRequests'] >= 1
    latest = urllib.request.urlopen(base + '/data/latest_data.js', timeout=10).read().decode('utf-8')
    assert 'window.EXTERNAL_DATA' in latest
    assert 'hotspots' in latest and 'window.EXTERNAL_DATA' in latest
    print('PHASE 22 AUTO UPDATE SERVER PASS')
finally:
    try:
        os.killpg(proc.pid, 15)
    except Exception:
        proc.kill()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    OUTPUT.write_bytes(BACKUP)
