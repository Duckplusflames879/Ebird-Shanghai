from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
index = (ROOT / 'index.html').read_text(encoding='utf-8')
app = (ROOT / 'js' / 'app.js').read_text(encoding='utf-8')
auto = (ROOT / 'js' / 'auto_update.js').read_text(encoding='utf-8')
hotspots = (ROOT / 'js' / 'modules' / 'hotspots.js').read_text(encoding='utf-8')
server = (ROOT / 'start_app.py').read_text(encoding='utf-8')
launcher = (ROOT / '启动观鸟系统.bat').read_text(encoding='utf-8')

assert 'js/auto_update.js' in index
assert 'await window.AutoUpdater.run()' in app
assert "route === '/hotspots'" not in app
assert "ENDPOINT = '/__auto_update'" in auto
assert "method: 'POST'" in auto
assert 'EBirdData.fetchRecent' in hotspots
assert "path == '/__auto_update'" in server
assert "path == '/__health'" in server
assert 'launcher.run_update(force=True)' in server
assert 'start_app.py' in launcher
print('PHASE 21 AUTO UPDATE CONTRACT PASS')
