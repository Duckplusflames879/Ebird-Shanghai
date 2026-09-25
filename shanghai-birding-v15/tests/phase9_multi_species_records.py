import os
import json
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]

def js(rel):
    return (ROOT / rel).read_text(encoding='utf8')

SHELL='''<!doctype html><html lang="zh-CN"><body><div id="app"></div><div id="modal-root"></div><div id="toast-root"></div></body></html>'''

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-gpu'])
        page=await browser.new_page()
        await page.set_content(SHELL)
        await page.evaluate('window.indexedDB=undefined')
        for rel in ['data/birds.js','data/latest_data.js','js/constants.js','js/utils.js','js/storage.js','js/state.js','js/components/modal.js','js/components/toast.js','js/components/autocomplete.js','js/modules/records.js']:
            await page.add_script_tag(content=js(rel))
        await page.evaluate("AppState={records:[],memos:[],memo:'',externalData:window.EXTERNAL_DATA}; AppStateActions={refreshPersonal:async()=>{},notify:()=>{}};")
        fixture_data=json.loads((ROOT/'tests'/'external_fixture.json').read_text(encoding='utf8'))
        await page.evaluate("(data)=>{AppState.externalData=data}", fixture_data)


        # Legacy single-species record remains readable and is normalized into species[].
        legacy=await page.evaluate("AppUtils.normalizeRecord({id:'legacy',date:'2026-09-01',location:'东滩',speciesId:'cn_egret',speciesName:'白鹭',count:2})")
        assert len(legacy['species'])==1
        assert legacy['species'][0]['speciesName']=='白鹭'
        assert legacy['species'][0]['count']==2

        # The form must expose a hotspot select, not a free-text location input.
        form=await page.evaluate("RecordsPage.recordForm(null)")
        assert 'id="hotspot-select"' in form
        assert '请选择观鸟点' in form
        assert 'name="location"' not in form

        # Saving one record with two species keeps independent counts.
        result=await page.evaluate("""RecordsPage.saveRecord({
            date:'2026-09-02', hotspotId:'dongtan',
            speciesPayload:JSON.stringify([
              {speciesId:'cn_egret',speciesName:'白鹭',count:3},
              {speciesId:'cn_grey_heron',speciesName:'苍鹭',count:7}
            ]), note:'多鸟种测试'
        }, null).then(x=>x)""")
        assert result['ok'] is True
        saved=await page.evaluate("Storage.getRecords()")
        assert len(saved)==1
        assert saved[0]['hotspotId']=='dongtan'
        assert saved[0]['location']=='崇明东滩'
        assert [(x['speciesName'],x['count']) for x in saved[0]['species']]==[('白鹭',3),('苍鹭',7)]

        # Duplicate bird in one observation record must be rejected.
        duplicate=await page.evaluate("""RecordsPage.saveRecord({
            date:'2026-09-02', hotspotId:'dongtan',
            speciesPayload:JSON.stringify([
              {speciesId:'cn_egret',speciesName:'白鹭',count:1},
              {speciesId:'cn_egret',speciesName:'白鹭',count:2}
            ])
        }, null).then(x=>x)""")
        assert duplicate['ok'] is False
        assert '不能重复添加' in duplicate['error']

        # Unknown hotspot must be rejected even with otherwise valid species data.
        unknown=await page.evaluate("""RecordsPage.saveRecord({
            date:'2026-09-02', hotspotId:'not-a-hotspot',
            speciesPayload:JSON.stringify([{speciesId:'cn_egret',speciesName:'白鹭',count:1}])
        }, null).then(x=>x)""")
        assert unknown['ok'] is False
        assert '请选择列表中的观鸟点' in unknown['error']

        # Actual modal form exposes one species row by default and can add a second row.
        await page.evaluate("RecordsPage.render()")
        await page.get_by_role('button', name='＋ 新增记录').click()
        assert await page.locator('#hotspot-select').count()==1
        assert await page.locator('[data-species-row]').count()==1
        await page.get_by_role('button', name='＋ 添加鸟种').click()
        assert await page.locator('[data-species-row]').count()==2
        assert await page.locator('#hotspot-select option').count() >= 5
        await browser.close()
    print('PHASE 9 MULTI-SPECIES RECORDS PASS', flush=True)
    os._exit(0)

asyncio.run(main())
