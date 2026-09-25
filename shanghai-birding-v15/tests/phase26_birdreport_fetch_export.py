import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
module=(ROOT/'js/modules/ebird.js').read_text(encoding='utf8')
assert "const IMPORT_FORMAT = 'shanghai-birding-ebird-7d'" in module
assert "const SOURCE = 'eBird'" in module
assert "regionCode: REGION_CODE" in module
assert 'exportCurrent' in module
print('PHASE 26 EBIRD FETCH EXPORT CONTRACT PASS')
