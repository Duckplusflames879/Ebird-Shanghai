import asyncio, os
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]

def js(rel):
    return (ROOT / rel).read_text(encoding='utf8')

DUPLICATES = [
    {
        'id':'ebird:A','name':'滨江森林公园','district':'浦东新区','lat':31.4800,'lon':121.5800,
        'records':[{'observationId':'a1','speciesId':'sp1','speciesName':'白头鹎','observedAt':'2026-09-02 07:00','latestCount':3,'totalCount':3,'occurrenceCount':1}],
        'source':'eBird','discovery':'ebird_recent'
    },
    {
        'id':'ebird:B','name':'滨江森林公园','district':'浦东新区','lat':31.4804,'lon':121.5804,
        'records':[{'observationId':'b1','speciesId':'sp1','speciesName':'白头鹎','observedAt':'2026-09-01 06:00','latestCount':2,'totalCount':2,'occurrenceCount':1},
                   {'observationId':'b2','speciesId':'sp2','speciesName':'白鹭','observedAt':'2026-09-01 08:00','latestCount':1,'totalCount':1,'occurrenceCount':1}],
        'source':'eBird','discovery':'ebird_recent'
    }
]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-gpu'])
        page = await browser.new_page()
        await page.set_content('<div id="app"></div>')
        await page.add_script_tag(content="window.AppState={externalData:{hotspots:[],hotspotData:{},sourceStatus:'ok'}};")
        await page.add_script_tag(content=js('js/modules/hotspots.js'))
        merged = await page.evaluate('data => HotspotsPage.sanitizeHotspots(data)', DUPLICATES)
        assert len(merged) == 1, merged
        h = merged[0]
        assert h['name'] == '滨江森林公园'
        assert len(h['records']) == 2
        bul = next(r for r in h['records'] if r['speciesName'] == '白头鹎')
        assert bul['observedAt'] == '2026-09-02 07:00'
        assert bul['occurrenceCount'] == 2
        assert bul['totalCount'] == 5
        assert h['sourceObservationCount'] == 3
        await browser.close()
    print('PHASE 40 HOTSPOT DUPLICATE LOCATION MERGE PASS', flush=True)
    os._exit(0)

asyncio.run(main())
