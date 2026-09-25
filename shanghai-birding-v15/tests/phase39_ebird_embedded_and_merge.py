import asyncio, json, os, re
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'js/modules/ebird.js').read_text(encoding='utf-8')
assert re.search(r"const EMBEDDED_API_KEY = '[0-9a-f-]{36}';", source)
assert 'return saved || EMBEDDED_API_KEY;' in source
assert 'haversineKm(record.lat, record.lon, candidate.lat, candidate.lon) <= 0.15' in source

RAW = [
  {"speciesCode":"cnbulb1","comName":"白头鹎","sciName":"Pycnonotus sinensis","locId":"A","locName":"Binjiang Forest Park, Shanghai, China","subnational2Name":"浦东新区","lat":31.48000,"lng":121.58000,"obsDt":"2026-09-02 06:42","howMany":3,"subId":"S1"},
  {"speciesCode":"cnbulb1","comName":"白头鹎","sciName":"Pycnonotus sinensis","locId":"B","locName":"滨江森林公园","subnational2Name":"浦东新区","lat":31.48002,"lng":121.58002,"obsDt":"2026-09-01 07:10","howMany":2,"subId":"S2"},
  {"speciesCode":"cnbulb1","comName":"白头鹎","sciName":"Pycnonotus sinensis","locId":"A","locName":"Binjiang Forest Park, Shanghai, China","subnational2Name":"浦东新区","lat":31.48000,"lng":121.58000,"obsDt":"2026-08-30 06:00","howMany":4,"subId":"S0"},
  {"speciesCode":"白眉姬鹟","comName":"白眉姬鹟","sciName":"Ficedula zanthopygia","locId":"B","locName":"滨江森林公园","subnational2Name":"浦东新区","lat":31.48002,"lng":121.58002,"obsDt":"2026-09-02 05:30","howMany":1,"subId":"S3"},
]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-gpu'])
        page = await browser.new_page()
        await page.set_content('<div id="app"></div>')
        await page.add_script_tag(content="""window.AppState={records:[],memos:[],memo:'',externalData:{weather:null,hotspots:[],hotspotData:{},sourceStatus:'not_fetched'}};window.AppStateActions={notify(){}};window.Storage={getAppValue:async()=>null,setAppValue:async()=>{}};""")
        await page.add_script_tag(content=(ROOT/'js/utils.js').read_text(encoding='utf-8'))
        await page.add_script_tag(content=source)
        fallback_key = await page.evaluate("async () => await EBirdData.getApiKey()")
        assert re.fullmatch(r'[0-9a-f-]{36}', fallback_key)
        await page.evaluate("rows => { window.__EBIRD_TEST_ROWS = rows; window.fetch = async () => ({ok:true,status:200,json:async()=>window.__EBIRD_TEST_ROWS}); }", RAW)
        result = await page.evaluate("async (rows) => await EBirdData.fetchRecent({force:true, apiKey:'TEST-KEY'})", RAW)
        assert result['success'] is True
        assert result['hotspotCount'] == 1, result
        assert result['recordCount'] == 2, result
        hotspot = await page.evaluate('window.AppState.externalData.hotspots[0]')
        assert hotspot['name'] == '滨江森林公园'
        assert len(hotspot['records']) == 2
        white = next(r for r in hotspot['records'] if r['speciesName'] == '白头鹎')
        assert white['observedAt'] == '2026-09-02 06:42'
        assert white['occurrenceCount'] == 3
        assert white['totalCount'] == 9
        assert white['latestCount'] == 3
        await browser.close()
    print('PHASE 39 EBIRD EMBEDDED KEY + SAME-LOCATION MERGE PASS', flush=True)
    os._exit(0)

asyncio.run(main())
