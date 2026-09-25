import os
import asyncio
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
        await page.add_script_tag(content='window.AppState={externalData:{weather:null,hotspots:[],hotspotData:{},sourceStatus:"ok"}};')
        await page.add_script_tag(content=js('js/modules/hotspots.js'))
        for rel in ['css/variables.css','css/components.css','css/layout.css','css/modules.css']:
            await page.add_style_tag(content=js(rel))
        fixture=[{'id':'ebird-binjiang','name':'滨江森林公园','district':'浦东新区','lat':31.48,'lon':121.58,
            'observations':[{'speciesId':'cn_bulbul','speciesName':'白头鹎','frequency':2}],
            'records':[{'observationId':'r2','speciesId':'cn_bulbul','speciesName':'白头鹎','observedAt':'2026-09-02 08:30:00','latestCount':3,'totalCount':5,'occurrenceCount':2}],
            'observationCount':1,'sourceObservationCount':2,'observationWindow':{'start':'2026-08-27','end':'2026-09-02'},'source':'eBird','sourceUrl':'https://ebird.org/region/CN-31','discovery':'ebird_recent'}]
        await page.evaluate('(h)=>{AppState.externalData.hotspots=h;AppState.externalData.hotspotData={source:"eBird",sourceObservationCount:2,observationWindow:{start:"2026-08-27",end:"2026-09-02"}}}', fixture)
        await page.evaluate('HotspotsPage.render()')
        await page.wait_for_selector('.hotspot-detail-card .obs-detail-row')
        body=await page.locator('.hotspot-detail-card').inner_text()
        assert '滨江森林公园' in body and '白头鹎' in body and '2026-09-02 08:30:00' in body
        assert 'eBird' in body
        assert '日期未知' not in body
        hotspots_js=js('js/modules/hotspots.js')
        assert 'inaturalist.org' not in hotspots_js
        assert "const SOURCE = 'eBird';" in hotspots_js
        assert 'EBirdData.fetchRecent' in hotspots_js
        await browser.close()
    print('PHASE 19 EBIRD BROWSER CONTRACT PASS', flush=True)
    os._exit(0)

asyncio.run(main())
