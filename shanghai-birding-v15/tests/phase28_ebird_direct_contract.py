from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'js/modules/ebird.js').read_text(encoding='utf-8')
assert "const REGION_CODE = 'CN-31'" in source
assert "back', '7'" in source
assert "hotspot', 'true'" in source
assert "maxResults', '10000'" in source
assert "sppLocale', 'zh_SIM'" in source
assert "X-eBirdApiToken" in source
assert 'localStorage.setItem(CACHE_KEY' in source
assert 'if (Array.isArray(data))' in source
assert "format:IMPORT_FORMAT" in source
print('PHASE 28 EBIRD DIRECT API CONTRACT PASS')
