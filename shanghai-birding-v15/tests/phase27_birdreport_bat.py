from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
# Legacy BirdReport launcher is no longer part of the active hotspot data path.
# The active browser path is eBird direct fetch + JSON import.
index=(ROOT/'index.html').read_text(encoding='utf8')
settings=(ROOT/'js/modules/settings.js').read_text(encoding='utf8')
assert 'js/modules/ebird.js' in index
assert 'ebird-api-key' in settings
assert 'import-ebird' in settings
print('PHASE 27 EBIRD ACTIVE PATH PASS')
