import asyncio, json, os
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
FIXTURE={
  "format":"shanghai-birding-ebird-7d","version":1,"app":"shanghai-birding","source":"eBird","regionCode":"CN-31",
  "generatedAt":"2026-09-02T10:00:00+08:00","retrievedAt":"2026-09-02T10:00:00+08:00",
  "observationWindow":{"start":"2026-08-27","end":"2026-09-02"},
  "hotspotData":{"source":"eBird","sourceUrl":"https://ebird.org/region/CN-31","regionCode":"CN-31","observationWindow":{"start":"2026-08-27","end":"2026-09-02"},"retrievedAt":"2026-09-02T10:00:00+08:00","sourceObservationCount":2,"displayedRecordCount":1,"hotspotCount":1},
  "hotspots":[{"id":"ebird:L1","name":"滨江森林公园","district":"浦东新区","lat":31.48,"lon":121.58,"records":[{"observationId":"S1","speciesId":"cnbulb1","speciesName":"白头鹎","observedAt":"2026-09-02 06:42","latestCount":3,"totalCount":5,"occurrenceCount":2,"sourceUrl":"https://ebird.org/checklist/S1"}]}]
}

def js(rel): return (ROOT/rel).read_text(encoding='utf-8')

async def main():
  async with async_playwright() as p:
    browser=await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-gpu'])
    page=await browser.new_page()
    await page.set_content('<div id="app"></div><div id="modal-root"></div><div id="toast-root"></div>')
    await page.add_script_tag(content="""window.AppState={records:[],memos:[],memo:'',externalData:{weather:null,hotspots:[],hotspotData:{},sourceStatus:'not_fetched'}};window.AppStateActions={notify(){},load:async()=>AppState,refreshPersonal:async()=>{}};window.Storage={getAppValue:async()=>'',setAppValue:async()=>{}};window.AppToast={show:()=>{}};""")
    for rel in ['js/utils.js','js/modules/ebird.js','js/modules/settings.js']:
      await page.add_script_tag(content=js(rel))
    await page.evaluate('SettingsPage.render()')
    assert await page.locator('#ebird-api-key').count()==1
    assert await page.locator('#fetch-ebird').count()==1
    await page.locator('#import-ebird').set_input_files({"name":"ebird.json","mimeType":"application/json","buffer":json.dumps(FIXTURE,ensure_ascii=False).encode()})
    await page.wait_for_timeout(150)
    # Import handler updates AppState directly; verify actual file input path was executed.
    assert await page.evaluate("AppState.externalData.hotspots.length") == 1
    assert await page.evaluate("AppState.externalData.hotspots[0].name") == '滨江森林公园'
    assert await page.evaluate("AppState.externalData.hotspots[0].records[0].speciesName") == '白头鹎'
    assert await page.evaluate("AppState.externalData.hotspots[0].records[0].observedAt") == '2026-09-02 06:42'
    await browser.close()
  print('PHASE 29 EBIRD IMPORT BROWSER PASS', flush=True)
  os._exit(0)

asyncio.run(main())
