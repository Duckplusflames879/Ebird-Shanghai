from pathlib import Path
s=(Path(__file__).resolve().parents[1]/'js/modules/hotspots.js').read_text(encoding='utf8')
assert "shanghai-birding-hotspots-7d" in s
assert "中国观鸟记录中心" in s
assert "importGenericFile" in s
assert "import-birdreport-web" in (Path(__file__).resolve().parents[1]/'js/modules/settings.js').read_text(encoding='utf8')
print('PHASE 33 GENERIC HOTSPOT IMPORT PASS')
