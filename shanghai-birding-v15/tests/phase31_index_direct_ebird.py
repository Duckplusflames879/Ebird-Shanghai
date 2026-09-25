from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
index=(ROOT/'index.html').read_text(encoding='utf8')
app=(ROOT/'js/app.js').read_text(encoding='utf8')
hotspots=(ROOT/'js/modules/hotspots.js').read_text(encoding='utf8')

scripts=re.findall(r'<script src="([^"]+)"></script>', index)
assert 'js/modules/ebird.js' in scripts
assert 'js/modules/hotspots.js' in scripts
assert scripts.index('js/modules/ebird.js') < scripts.index('js/modules/hotspots.js')
assert "await window.EBirdData.fetchRecent" in hotspots or 'EBirdData.fetchRecent' in hotspots
assert 'shouldAutoRefresh' in hotspots
assert "route === '/hotspots'" not in app
assert "await window.AutoUpdater.run()" in app  # weather/general legacy bridge remains intact
assert '中国观鸟记录中心' in hotspots and 'importGenericFile' in hotspots
assert 'iNaturalist' not in hotspots and 'inaturalist.org' not in hotspots
print('PHASE 31 INDEX EBIRD ENTRY CONTRACT PASS')
