import os
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
def js(rel): return (ROOT/rel).read_text(encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-gpu'])
        page = await browser.new_page()
        await page.set_content('<div id="app"></div>')
        await page.add_script_tag(content="window.__testLeafletCalls=[]; window.L={map:(el)=>{window.__testLeafletCalls.push(['map']); const root=typeof el==='string'?document.getElementById(el):el; root.classList.add('leaflet-container'); return {setView(c,z){window.__testLeafletCalls.push(['setView',c,z]); return this;},fitBounds(){window.__testLeafletCalls.push(['fitBounds']); return this;},invalidateSize(){return this;},remove(){return this;}}},tileLayer:(url,opts)=>{window.__testLeafletCalls.push(['tileLayer',url]); return {addTo(){return this;}}},marker:(latlng)=>{window.__testLeafletCalls.push(['marker',latlng]); return {addTo(){const node=document.createElement('div');node.className='leaflet-marker-icon';document.querySelector('.leaflet-container').appendChild(node);return this;},bindPopup(){return this;},openPopup(){return this;},on(){return this;}}},latLngBounds:(bounds)=>({pad(){return bounds;}})};")
        for rel in ['data/latest_data.js','js/constants.js','js/utils.js','js/modules/weather.js','js/modules/hotspots.js']:
            await page.add_script_tag(content=js(rel))
        fixture_text=(ROOT/'tests/external_fixture.json').read_text(encoding='utf8')
        await page.evaluate("window.EXTERNAL_DATA = JSON.parse(%s)" % json.dumps(fixture_text))
        await page.evaluate("AppState={externalData:window.EXTERNAL_DATA};")
        forecast = await page.evaluate('AppState.externalData.weather.forecast')
        assert len(forecast) == 7
        required = ['date','tempMin','tempMax','windDirection','windLevel','weather']
        assert all(all(k in d for k in required) for d in forecast)

        await page.evaluate("(async()=>{WeatherPage.selectedDate=null;await WeatherPage.render();})()")
        assert await page.locator('.weather-day').count() == 7
        assert await page.locator('.weather-day').first.inner_text()
        first_date = forecast[0]['date']
        assert first_date in await page.locator('.card').nth(1).inner_text()
        await page.locator('.weather-day').nth(2).click()
        assert forecast[2]['date'] in await page.locator('.card').nth(1).inner_text()
        assert '基础' not in await page.locator('.advice').inner_text() or len(await page.locator('.advice').inner_text()) > 4

        await page.evaluate("HotspotsPage.selectedId=null; AppState.externalData=window.EXTERNAL_DATA; (async()=>{await HotspotsPage.render();})()")
        assert await page.locator('.hotspot-item').count() == 4
        assert await page.locator('.leaflet-map').count() == 1
        assert await page.locator('.leaflet-marker-icon').count() == 4
        assert await page.locator('.hotspot-detail-card .obs-detail-row').count() == 2
        assert '白鹭' in await page.locator('.hotspot-detail-card').inner_text()
        assert '白鹭' in await page.locator('.hotspot-detail-card').inner_text()
        await page.locator('.hotspot-item').nth(1).click()
        assert await page.locator('.hotspot-item.active').count() == 1
        assert await page.locator('.hotspot-detail-card .obs-detail-row').count() == 2
        await browser.close()
    print('PHASE 5 PASS', flush=True)
    os._exit(0)

asyncio.run(main())
