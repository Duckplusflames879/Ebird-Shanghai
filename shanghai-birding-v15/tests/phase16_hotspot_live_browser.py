import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
def js(rel): return (ROOT/rel).read_text(encoding='utf8')

async def main():
  async with async_playwright() as p:
    browser=await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-gpu'])
    page=await browser.new_page()
    await page.set_content('<div id="app"></div>')
    await page.add_script_tag(content=js('data/birds.js'))
    await page.add_script_tag(content=js('js/constants.js'))
    await page.add_script_tag(content=js('js/utils.js'))
    await page.add_script_tag(content='window.AppState={externalData:{weather:null,hotspots:[],hotspotData:{},sourceStatus:"not_fetched"}};')
    await page.add_script_tag(content=js('js/modules/ebird.js'))
    await page.add_script_tag(content=js('js/modules/hotspots.js'))
    ebird_js=js('js/modules/ebird.js')
    hotspots_js=js('js/modules/hotspots.js')
    app_js=js('js/app.js')
    assert "const SOURCE = 'eBird'" in ebird_js
    assert 'X-eBirdApiToken' in ebird_js
    assert 'iNaturalist' not in hotspots_js
    assert "const SOURCE = 'eBird';" in hotspots_js
    assert 'EBirdData.fetchRecent' in hotspots_js
    assert "route === '/hotspots'" not in app_js
    assert 'EBirdData.fetchRecent' in hotspots_js
    await browser.close()
  print('PHASE 16 HOTSPOT EBIRD BROWSER CONTRACT PASS', flush=True)
  os._exit(0)

asyncio.run(main())
