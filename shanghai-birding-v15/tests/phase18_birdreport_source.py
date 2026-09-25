import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
ebird=(ROOT/"js/modules/ebird.js").read_text(encoding="utf8")
hotspots=(ROOT/"js/modules/hotspots.js").read_text(encoding="utf8")
assert "const SOURCE = 'eBird'" in ebird
assert "const REGION_CODE = 'CN-31'" in ebird
assert "sppLocale" in ebird and "zh_SIM" in ebird
assert "X-eBirdApiToken" in ebird
assert "back', '7'" in ebird
assert "hotspot', 'true'" in ebird
assert "maxResults', '10000'" in ebird
assert 'inaturalist.org' not in ebird and 'iNaturalist' not in ebird
assert '中国观鸟记录中心' in hotspots  # retained only for backward-compatible import UI; not the online default source
assert "const SOURCE = 'eBird';" in hotspots
assert 'EBirdData.fetchRecent' in hotspots
print('PHASE 18 EBIRD SOURCE CONTRACT PASS')
