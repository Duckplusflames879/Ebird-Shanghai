import asyncio, json, os
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
def js(rel): return (ROOT/rel).read_text(encoding='utf8')
SHELL='<!doctype html><html><body><div id="app"></div><div id="modal-root"></div><div id="toast-root"></div></body></html>'
async def main():
  async with async_playwright() as p:
    browser=await p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-gpu'])
    page=await browser.new_page(); await page.set_content(SHELL)
    fixture=json.loads((ROOT/'tests'/'ebird_import_fixture.json').read_text(encoding='utf8'))
    for rel in ['data/birds.js','data/latest_data.js','js/constants.js','js/utils.js','js/storage.js','js/state.js','js/components/modal.js','js/components/toast.js','js/modules/home.js','js/modules/ebird.js','js/modules/settings.js']:
      await page.add_script_tag(content=js(rel))
    await page.evaluate("AppState.externalData={weather:null,hotspots:[],hotspotData:{},sourceStatus:'not_fetched'}")
    await page.evaluate("data=>EBirdData.importFile(new File([JSON.stringify(data)],'ebird.json',{type:'application/json'}))", fixture)
    assert await page.evaluate("AppState.externalData.hotspotData.source")=='eBird'
    await page.evaluate('SettingsPage.render()')
    assert await page.locator('#import-ebird').count()==1
    await page.locator('#import-ebird').set_input_files(str(ROOT/'tests'/'ebird_import_fixture.json'))
    await page.wait_for_function("AppState.externalData.hotspots.length === 2")
    assert await page.evaluate("AppState.externalData.hotspotData.source")=='eBird'
    await browser.close()
  print('PHASE 25 EBIRD IMPORT BROWSER PASS',flush=True); os._exit(0)
asyncio.run(main())
