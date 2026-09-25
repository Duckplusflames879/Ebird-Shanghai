from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'js/modules/settings.js').read_text(encoding='utf8')
h=(ROOT/'js/modules/hotspots.js').read_text(encoding='utf8')
assert 'birdreport-web-exporter.user.js' in s
assert 'import-birdreport-web' in s
assert 'importGenericFile' in h
assert "中国观鸟记录中心" in s
print('PHASE 38 SETTINGS WEB IMPORT PASS')
