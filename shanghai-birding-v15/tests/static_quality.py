from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
html=(ROOT/'index.html').read_text(encoding='utf8')
script_paths=re.findall(r'<script src="([^"]+)"></script>', html)
css_paths=re.findall(r'<link rel="stylesheet" href="([^"]+)">', html)
assert len(script_paths)==22, f'expected 22 mounted scripts, got {len(script_paths)}'
assert all((ROOT/p).exists() for p in script_paths), 'all script assets must exist'
assert all((ROOT/p).exists() for p in css_paths), 'all css assets must exist'
assert script_paths[:2]==['data/birds.js','data/latest_data.js']
assert 'data/bird_details.js' in script_paths, 'generated bird detail dataset must be mounted'
assert 'js/modules/bird_profiles.js' in script_paths, 'bird detail profile module must be mounted'
assert 'js/auto_update.js' in script_paths, 'automatic update client must be mounted'
assert 'js/modules/ebird.js' in script_paths, 'eBird direct-data module must be mounted'
app_js=(ROOT/'js'/'app.js').read_text(encoding='utf8')
assert "route === '/hotspots'" not in app_js, 'hotspot route must not use legacy auto updater'
for path in ROOT.rglob('*'):
    if path.is_file(): assert '/' not in path.name and '\\' not in path.name, f'illegal slash in filename: {path.name}'
# JavaScript syntax check. node --check does not execute code.
js_files=sorted((ROOT/'js').rglob('*.js'))
for path in js_files:
    subprocess.run(['node','--check',str(path)],check=True,capture_output=True,text=True)
# Python syntax check.
for path in [ROOT/'run_tests.py', ROOT/'scripts'/'update_data.py', ROOT/'scripts'/'fetch_birdreport_7d.py', ROOT/'start_app.py']:
    subprocess.run([sys.executable,'-m','py_compile',str(path)],check=True)
# Required MVP exclusions must not be implemented as asset/module references.
birds_js=(ROOT/'data'/'birds.js').read_text(encoding='utf8')
assert 'speciesCount: 544' in birds_js, 'bird lexicon must contain the 544-species regional baseline'
assert 'window.BIRD_LEXICON = [' in birds_js
state_js=(ROOT/'js'/'state.js').read_text(encoding='utf8')
assert "sourceStatus: data.sourceStatus || 'ok'" in state_js, 'state layer must preserve not_fetched live-data status'
lexicon_js=(ROOT/'js'/'modules'/'lexicon.js').read_text(encoding='utf8')
assert 'compositionstart' in lexicon_js and 'compositionend' in lexicon_js, 'lexicon search must handle Chinese IME composition'
assert 'lexicon-results' in lexicon_js, 'lexicon search should not replace the input during IME composition'
hotspots_js=(ROOT/'js'/'modules'/'hotspots.js').read_text(encoding='utf8')
assert "LEAFLET_VERSION = '1.9.4'" in hotspots_js
assert 'vendor/leaflet/leaflet.js' in hotspots_js
assert 'webrd0{s}.is.autonavi.com' in hotspots_js
assert 'tile.openstreetmap.org/{z}/{x}/{y}.png' in hotspots_js
latest=(ROOT/'data'/'latest_data.js').read_text(encoding='utf8')
assert "sourceStatus: 'not_fetched'" in latest, 'production snapshot must not contain fabricated hotspot observations'
assert "source: 'eBird'" in latest and 'CN-31' in latest
assert 'inaturalist.org' not in latest and 'iNaturalist' not in latest
assert 'leaflet-map' in hotspots_js
assert 'offline-map' not in hotspots_js
assert 'inaturalist.org' not in hotspots_js and 'iNaturalist' not in hotspots_js
updater=(ROOT/'scripts'/'update_data.py').read_text(encoding='utf8')
assert 'inaturalist.org' not in updater and 'iNaturalist' not in updater
ebird=(ROOT/'js'/'modules'/'ebird.js').read_text(encoding='utf8')
assert "const SOURCE = 'eBird'" in ebird
assert "const REGION_CODE = 'CN-31'" in ebird
assert "back', '7'" in ebird
assert "sppLocale', 'zh_SIM'" in ebird
assert "X-eBirdApiToken" in ebird
assert 'localStorage.setItem(CACHE_KEY' in ebird

print(f'STATIC QUALITY PASS ({len(js_files)} JS files)')
