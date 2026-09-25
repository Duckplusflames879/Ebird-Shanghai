import asyncio, json, tempfile, os
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
def js(rel): return (ROOT/rel).read_text(encoding='utf8')
ALL = [
    'data/birds.js','data/latest_data.js','js/constants.js','js/utils.js','js/storage.js','js/state.js',
    'js/components/modal.js','js/components/toast.js','js/components/sidebar.js','js/components/autocomplete.js',
    'js/modules/home.js','js/modules/weather.js','js/modules/hotspots.js','js/modules/records.js','js/modules/lexicon.js','js/modules/settings.js','js/router.js','js/app.js'
]
SHELL='''<!doctype html><html lang="zh-CN"><body><div id="app-shell"><aside id="sidebar"></aside><main><header id="page-header"></header><section id="app"></section></main></div><div id="modal-root"></div><div id="toast-root"></div></body></html>'''

async def main():
    with tempfile.TemporaryDirectory() as td:
        restore = Path(td)/'restore.json'
        restore.write_text(json.dumps({
            'version':1,'app':'shanghai-birding','exportedAt':'2026-09-02T09:00:00+08:00',
            'records':[{'id':'restore1','date':'2026-09-02','location':'崇明东滩','hotspotId':'dongtan','species':[{'speciesId':'cn_egret','speciesName':'白鹭','count':2},{'speciesId':'cn_grey_heron','speciesName':'苍鹭','count':4}],'speciesId':'cn_egret','speciesName':'白鹭','count':2,'note':'恢复','createdAt':'x','updatedAt':'x'}],
            'memos':[{'id':'m1','text':'恢复备忘一','createdAt':'x','updatedAt':'x'},{'id':'m2','text':'恢复备忘二','createdAt':'x','updatedAt':'x'}],
            'quickMemo':'恢复备忘一'
        }, ensure_ascii=False),encoding='utf8')
        async with async_playwright() as p:
            browser=await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-gpu'])
            page=await browser.new_page(viewport={'width':1400,'height':900})
            await page.set_content(SHELL)
            # Use native IndexedDB for this end-to-end integration test; fallback storage is covered separately.
            await page.add_script_tag(content="window.__testLeafletCalls=[]; window.L={map:(el)=>{window.__testLeafletCalls.push(['map']); const root=typeof el==='string'?document.getElementById(el):el; root.classList.add('leaflet-container'); return {setView(c,z){window.__testLeafletCalls.push(['setView',c,z]); return this;},fitBounds(){window.__testLeafletCalls.push(['fitBounds']); return this;},invalidateSize(){return this;},remove(){return this;}}},tileLayer:(url,opts)=>{window.__testLeafletCalls.push(['tileLayer',url]); return {addTo(){return this;}}},marker:(latlng)=>{window.__testLeafletCalls.push(['marker',latlng]); return {addTo(){const node=document.createElement('div');node.className='leaflet-marker-icon';document.querySelector('.leaflet-container').appendChild(node);return this;},bindPopup(){return this;},openPopup(){return this;},on(){return this;}}},latLngBounds:(bounds)=>({pad(){return bounds;}})};")
            errors=[]
            page.on('pageerror', lambda e: errors.append(str(e)))
            for rel in ALL: await page.add_script_tag(content=js(rel))
            await page.wait_for_selector('#sidebar .nav-link')
            assert len(errors)==0, errors
            assert await page.locator('#sidebar .nav-link').count()==6
            assert await page.locator('.page-title').inner_text()=='首页'
            # The production snapshot is intentionally empty until a real live refresh; use a deterministic
            # fixture for this full UI integration test.
            fixture_data=json.loads((ROOT/'tests'/'external_fixture.json').read_text(encoding='utf8'))
            await page.evaluate("(data)=>{AppState.externalData=data}", fixture_data)

            # Core chain: Home -> Records -> list-based hotspot -> one record with two species -> Lexicon -> Home.
            await page.evaluate("Router.navigate('/records')")
            await page.wait_for_function("location.hash === '#/records'")
            await page.get_by_role('button', name='＋ 新增记录').click()
            await page.locator('#hotspot-select').select_option('dongtan')
            rows=page.locator('[data-species-row]')
            await rows.nth(0).locator('.species-input').fill('白')
            await page.wait_for_selector('.autocomplete-menu:not([hidden])')
            assert any('白鹭' in x for x in await page.locator('.autocomplete-item').all_inner_texts())
            await page.locator('.autocomplete-item', has_text='白鹭').first.click()
            await rows.nth(0).locator('.species-count').fill('1')
            await page.get_by_role('button', name='＋ 添加鸟种').click()
            rows=page.locator('[data-species-row]')
            await rows.nth(1).locator('.species-input').fill('苍')
            await page.wait_for_selector('.autocomplete-menu:not([hidden])')
            await page.locator('.autocomplete-item', has_text='苍鹭').first.click()
            await rows.nth(1).locator('.species-count').fill('2')
            await page.get_by_role('button', name='保存').click()
            await page.wait_for_function("AppState.records.length === 1")
            assert await page.get_by_text('白鹭 × 1、苍鹭 × 2').count()==1
            assert await page.evaluate("AppState.records[0].species.length") == 2

            await page.evaluate("Router.navigate('/lexicon')")
            await page.wait_for_function("location.hash === '#/lexicon'")
            await page.wait_for_selector('[data-bird=cn_egret]')
            assert '已点亮' in await page.locator('[data-bird=cn_egret]').inner_text()
            assert '已点亮' in await page.locator('[data-bird=cn_grey_heron]').inner_text()
            await page.evaluate("Router.navigate('/home')")
            await page.wait_for_function("location.hash === '#/home'")
            await page.get_by_text('2 / 544 种', exact=True).wait_for(timeout=3000)

            # Multiple memos: add two, both appear on Home, each autosaves, delete one.
            await page.get_by_role('button', name='＋ 添加备忘').click()
            await page.locator('#modal-root textarea[name=text]').fill('集成备忘一')
            await page.get_by_role('button', name='保存').click()
            await page.wait_for_selector('[data-memo-input]')
            await page.get_by_role('button', name='＋ 添加备忘').click()
            await page.locator('#modal-root textarea[name=text]').fill('集成备忘二')
            await page.get_by_role('button', name='保存').click()
            await page.wait_for_function("AppState.memos.length === 2")
            await page.wait_for_function("document.querySelectorAll('[data-memo-input]').length === 2")
            memo_values=await page.locator('[data-memo-input]').evaluate_all("els=>els.map(e=>e.value)")
            assert memo_values==['集成备忘一','集成备忘二']
            await page.locator('[data-memo-input]').nth(0).fill('集成备忘一已修改')
            await page.locator('[data-memo-input]').nth(0).blur()
            assert await page.evaluate("Storage.getMemos().then(xs=>xs[0].text)")=='集成备忘一已修改'
            await page.locator('[data-delete-memo]').nth(1).click()
            await page.get_by_role('button', name='确认').click()
            await page.wait_for_function("AppState.memos.length === 1")
            await page.wait_for_function("document.querySelectorAll('[data-memo-input]').length === 1")

            # Settings: export a valid backup with the new multi-species and multi-memo payload.
            await page.evaluate("Router.navigate('/settings')")
            await page.wait_for_function("location.hash === '#/settings'")
            async with page.expect_download() as info:
                await page.get_by_role('button', name='导出 JSON').click()
            download=await info.value
            exported=json.loads(Path(await download.path()).read_text(encoding='utf8'))
            assert exported['app']=='shanghai-birding'
            assert len(exported['records'])==1
            assert len(exported['records'][0]['species'])==2
            assert len(exported['memos'])==1
            assert exported['quickMemo']=='集成备忘一已修改'

            # Clear then restore. All record species, memos, and derived lexicon state must return.
            await page.get_by_role('button', name='清空全部数据').click()
            await page.get_by_role('button', name='确认').click()
            await page.wait_for_timeout(60)
            assert await page.evaluate('Storage.getRecords().then(x=>x.length)')==0
            assert await page.evaluate('Storage.getMemos().then(x=>x.length)')==0
            await page.locator('#import-json').set_input_files(str(restore))
            await page.wait_for_timeout(100)
            assert await page.evaluate('Storage.getRecords().then(x=>x.length)')==1
            restored=await page.evaluate('Storage.getRecords().then(x=>x[0])')
            assert [(x['speciesName'],x['count']) for x in restored['species']]==[('白鹭',2),('苍鹭',4)]
            assert await page.evaluate('Storage.getMemos().then(x=>x.length)')==2
            await page.evaluate("Router.navigate('/home')")
            await page.wait_for_function("location.hash === '#/home'")
            await page.get_by_text('2 / 544 种', exact=True).wait_for(timeout=3000)
            assert await page.get_by_text('白鹭 × 2、苍鹭 × 4').count()==1
            restored_memo_values=await page.locator('[data-memo-input]').evaluate_all("els=>els.map(e=>e.value)")
            assert restored_memo_values==['恢复备忘一','恢复备忘二']

            # Hotspot map remains in the final integrated app.
            await page.evaluate("Router.navigate('/hotspots')")
            await page.wait_for_function("location.hash === '#/hotspots'")
            await page.wait_for_selector('.leaflet-map', state='attached')
            assert await page.locator('.leaflet-map').count()==1
            assert await page.locator('.leaflet-container').count()==1
            assert await page.locator('.leaflet-marker-icon').count()==4
            assert await page.locator('#map-status').inner_text() != ''
            await browser.close()
    print('PHASE 8 PASS', flush=True)
    os._exit(0)

asyncio.run(main())
