import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
fixture=ROOT/'tests'/'ebird_import_fixture.json'
if not fixture.exists():
    fixture=ROOT/'tests'/'birdreport_import_fixture.json'
data=json.loads(fixture.read_text(encoding='utf8'))
assert data['format']=='shanghai-birding-ebird-7d'
assert data['source']=='eBird'
assert data['regionCode']=='CN-31'
assert (data['observationWindow']['end'], data['observationWindow']['start']) == ('2026-09-02','2026-08-27')
assert all(h['source']=='eBird' for h in data['hotspots'])
assert all(all('㐀'<=c<='鿿' for c in r['speciesName'] if c.strip()) for h in data['hotspots'] for r in h['records'])
assert all(r['observedAt'] and ':' in r['observedAt'] for h in data['hotspots'] for r in h['records'])
print('PHASE 24 EBIRD IMPORT CONTRACT PASS')
