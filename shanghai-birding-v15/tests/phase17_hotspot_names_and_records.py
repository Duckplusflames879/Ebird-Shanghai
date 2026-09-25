import os
import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
def js(rel): return (ROOT/rel).read_text(encoding='utf8')

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-gpu'])
        page=await browser.new_page(viewport={'width':1400,'height':900})
        await page.set_content('<div id="app"></div>')
        await page.add_script_tag(content="window.L={map:(el)=>{const root=typeof el==='string'?document.getElementById(el):el;root.classList.add('leaflet-container');return {setView(){return this},fitBounds(){return this},invalidateSize(){},remove(){}}},tileLayer:()=>({addTo(){return this}}),marker:()=>({addTo(){return this},bindPopup(){return this},openPopup(){return this},on(){return this}}),latLngBounds:(x)=>({pad(){return x}})};")
        for rel in ['data/birds.js','data/latest_data.js','js/constants.js','js/utils.js']:
            await page.add_script_tag(content=js(rel))
        await page.add_script_tag(content='window.AppState={externalData:{weather:null,hotspots:[],hotspotData:{},sourceStatus:"ok"}};')
        await page.add_script_tag(content=js('js/modules/hotspots.js'))
        for rel in ['css/variables.css','css/components.css','css/layout.css','css/modules.css']:
            await page.add_style_tag(content=js(rel))

        fixture=json.loads((ROOT/'tests/ebird_import_fixture.json').read_text(encoding='utf8'))
        await page.evaluate('(data)=>{AppState.externalData=data}', fixture)
        await page.evaluate('HotspotsPage.render()')
        await page.wait_for_selector('.hotspot-detail-card .obs-detail-row')

        names=await page.locator('.hotspot-item strong').all_inner_texts()
        assert all(any('\u3400' <= ch <= '\u9fff' for ch in name) for name in names)
        assert len(names)==2
        assert await page.locator('.hotspot-item[data-id="dongtan"]').count()==1
        assert await page.locator('.hotspot-item[data-id="nanhui"]').count()==1
        assert await page.locator('.hotspot-detail-card .obs-detail-row').count()==2
        await page.locator('.hotspot-item[data-id="dongtan"]').click()
        await page.wait_for_selector('.hotspot-detail-card .obs-detail-row')
        body=await page.locator('.hotspot-detail-card').inner_text()
        assert '2026-09-02 07:30:00' in body
        assert '日期未知' not in body
        assert 'eBird' in body
        assert '最近观测：' in body

        await page.locator('.hotspot-item').nth(1).click()
        assert await page.locator('.hotspot-item.active').count()==1
        body=await page.locator('.hotspot-detail-card').inner_text()
        assert '最近观测：' in body
        assert '2026-08-' in body or '2026-09-' in body

        await browser.close()
    print('PHASE 17 HOTSPOT NAMES / SOURCE RECORD TIME PASS', flush=True)
    os._exit(0)

asyncio.run(main())
