import os
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
def js(rel): return (ROOT/rel).read_text(encoding='utf8')

SHELL='''<!doctype html><html><body><div id="app"></div><div id="modal-root"></div><div id="toast-root"></div></body></html>'''

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-gpu'])
        page=await browser.new_page(viewport={'width':1400,'height':900})
        await page.set_content(SHELL)
        await page.add_script_tag(content=js('data/birds.js'))
        await page.add_script_tag(content=js('data/latest_data.js'))
        fixture_text=(ROOT/'tests/external_fixture.json').read_text(encoding='utf8')
        await page.evaluate("window.EXTERNAL_DATA = JSON.parse(%s)" % json.dumps(fixture_text))
        for rel in ['js/constants.js','js/utils.js','js/modules/hotspots.js']:
            await page.add_script_tag(content=js(rel))
        # Inject a deterministic Leaflet-compatible test double because the test sandbox has no external CDN access.
        await page.evaluate('''window.__leafletCalls=[]; window.L={map:(el,opts)=>{window.__leafletCalls.push(['map',el,opts]); const root=typeof el==='string'?document.getElementById(el):el; root.classList.add('leaflet-container'); return {setView(c,z){window.__leafletCalls.push(['setView',c,z]);return this;},invalidateSize(){window.__leafletCalls.push(['invalidateSize']);return this;},fitBounds(b,opts){window.__leafletCalls.push(['fitBounds',b,opts]);return this;},remove(){window.__leafletCalls.push(['remove']);},removeLayer(){return this;}}},tileLayer:(url,opts)=>{window.__leafletCalls.push(['tileLayer',url,opts]); return {addTo(map){window.__leafletCalls.push(['tileAdd']);return this;}}},marker:(latlng,opts)=>{window.__leafletCalls.push(['marker',latlng,opts]); let popup=''; let node=null; return {addTo(map){window.__leafletCalls.push(['markerAdd',latlng]); node=document.createElement('div');node.className='leaflet-marker-icon';document.querySelector('.leaflet-container').appendChild(node);return this;},bindPopup(html){popup=html;window.__leafletCalls.push(['bindPopup',html]);return this;},openPopup(){window.__leafletCalls.push(['openPopup',popup]);return this;},remove(){if(node&&node.parentNode)node.parentNode.removeChild(node);window.__leafletCalls.push(['markerRemove']);return this;},on(){return this;}}}};''')
        # Every hotspot needs geographic coordinates for mapping.
        await page.evaluate("AppState={externalData:window.EXTERNAL_DATA};")
        hotspots=await page.evaluate("AppState.externalData.hotspots")
        assert len(hotspots)==4
        assert all(isinstance(h['lat'],(int,float)) and isinstance(h['lon'],(int,float)) for h in hotspots)

        await page.evaluate("HotspotsPage.render()")
        assert await page.locator('.leaflet-map').count()==1
        assert await page.locator('.leaflet-container').count()==1
        assert await page.locator('.hotspot-item').count()==4
        calls=await page.evaluate('window.__leafletCalls')
        assert any(c[0]=='map' for c in calls)
        assert any(c[0]=='tileLayer' and ('autonavi.com' in c[1] or 'openstreetmap.org' in c[1]) for c in calls)
        assert sum(1 for c in calls if c[0]=='marker')==4
        assert all(c[0]=='marker' and len(c[1])==2 for c in calls if c[0]=='marker')

        # Clicking a hotspot list item selects the same hotspot and moves the Leaflet map.
        await page.locator('.hotspot-item[data-id="nanhui"]').click()
        await page.wait_for_selector('.hotspot-item[data-id="nanhui"].active')
        assert '南汇东滩' in await page.locator('.hotspot-detail-card').inner_text()
        calls=await page.evaluate('window.__leafletCalls')
        assert any(c[0]=='setView' and len(c[1])==2 for c in calls)

        # The production loader prefers the local Leaflet vendor; intercept the network so this test remains deterministic.
        await page.evaluate('''async () => {
            window.L=undefined;
            window.__originalHeadAppendChild = document.head.appendChild.bind(document.head);
            const append=window.__originalHeadAppendChild;
            document.head.appendChild=(node)=>{
                if(node.tagName==='SCRIPT' && String(node.src||'').includes('vendor/leaflet/leaflet.js')){
                    window.L={map:function(){}};
                    setTimeout(()=>node.onload && node.onload(),0);
                    return node;
                }
                if(node.tagName==='LINK' && String(node.href||'').includes('vendor/leaflet/leaflet.css')){
                    setTimeout(()=>node.onload && node.onload(),0);
                    return append(node);
                }
                return append(node);
            };
        }''')
        loaded=await page.evaluate('HotspotsPage.loadLeaflet().then(()=>typeof window.L.map === \"function\")')
        assert loaded is True
        assert await page.locator('link[data-leaflet-css="1.9.4"]').count()==1

        # The record form reads from the same hotspot list.
        for rel in ['js/storage.js','js/state.js','js/components/modal.js','js/components/toast.js','js/components/autocomplete.js','js/modules/records.js']:
            await page.add_script_tag(content=js(rel))
        await page.evaluate("AppState={externalData:window.EXTERNAL_DATA,records:[],memos:[],memo:''}; AppStateActions={refreshPersonal:async()=>{},notify:()=>{}};")
        form=await page.evaluate("RecordsPage.recordForm(null)")
        assert 'id="hotspot-select"' in form
        assert '崇明东滩' in form and '南汇东滩' in form and '滨江森林公园' in form and '共青森林公园' in form
        await browser.close()
    print('PHASE 11 HOTSPOT MAP PASS', flush=True)
    os._exit(0)

asyncio.run(main())
