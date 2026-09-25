import os
import asyncio
import json
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
        # Add duplicate same-species rows intentionally: UI sanitization must keep the latest time only.
        h=fixture['hotspots'][0]
        h['records'].append({**h['records'][0], 'observationId':'older-extra', 'observedAt':'2026-08-29 06:00:00'})
        await page.evaluate('(data)=>{AppState.externalData=data}', fixture)
        await page.evaluate('HotspotsPage.render()')
        await page.wait_for_selector('.hotspot-detail-card .obs-detail-row')
        names=await page.locator('.hotspot-item strong').all_inner_texts()
        assert all(not any(('A' <= ch <= 'Z') or ('a' <= ch <= 'z') for ch in n) for n in names)
        all_detail=await page.locator('.obs-detail-row').all_inner_texts()
        assert all('最近观测：' in row for row in all_detail)
        assert all('日期未知' not in row for row in all_detail)
        # Duplicate white egret entries must collapse to one row and keep the newest timestamp.
        assert await page.locator('.hotspot-detail-card .obs-detail-row').count()==2
        body=await page.locator('.hotspot-detail-card').inner_text()
        assert '2026-09-02 07:30:00' in body
        assert '2026-08-29 06:00:00' not in body
        assert 'eBird' in body
        await browser.close()
    print('PHASE 20 HOTSPOT UI CONTRACT PASS', flush=True)
    os._exit(0)

asyncio.run(main())
