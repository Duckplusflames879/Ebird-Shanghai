import os
import asyncio, json, tempfile
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
def js(rel): return (ROOT/rel).read_text(encoding='utf-8')

async def main():
    with tempfile.TemporaryDirectory() as td:
        backup=Path(td)/'backup.json'
        backup.write_text(json.dumps({
            'version':1,'app':'shanghai-birding','exportedAt':'2026-09-02T09:00:00+08:00',
            'records':[{'id':'r1','date':'2026-09-02','location':'东滩','speciesId':'cn_egret','speciesName':'白鹭','count':3,'note':'测试','createdAt':'x','updatedAt':'x'},
                       {'id':'r2','date':'2026-09-01','location':'南汇','speciesId':'cn_bulbul','speciesName':'白头鹎','count':2,'note':'备份','createdAt':'x','updatedAt':'x'}],
            'quickMemo':'恢复后的备忘'
        }, ensure_ascii=False), encoding='utf8')
        bad=Path(td)/'bad.json'; bad.write_text('{not-json',encoding='utf8')
        async with async_playwright() as p:
            browser=await p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-gpu'])
            page=await browser.new_page()
            await page.set_content('<div id="app"></div><div id="modal-root"></div><div id="toast-root"></div>')
            await page.evaluate('window.indexedDB=undefined')
            for rel in ['data/birds.js','data/latest_data.js','js/constants.js','js/utils.js','js/storage.js','js/state.js','js/components/modal.js','js/components/toast.js','js/modules/settings.js']:
                await page.add_script_tag(content=js(rel))
            await page.evaluate("AppState={records:[{id:'old',date:'2026-08-01',location:'共青',speciesId:'cn_great_tit',speciesName:'大山雀',count:1,note:'old',createdAt:'x',updatedAt:'x'}],memo:'旧备忘',externalData:window.EXTERNAL_DATA}")
            await page.evaluate("Storage.addRecord(AppState.records[0]); Storage.saveMemo('旧备忘')")
            await page.evaluate("SettingsPage.render()")
            assert await page.get_by_text('导出 JSON').count()==1
            assert await page.get_by_text('清空全部数据').count()==1

            # Validate export payload without relying on browser's download path.
            payload=await page.evaluate('SettingsPage.exportPayload()')
            assert payload['app']=='shanghai-birding'
            assert payload['version']==1
            assert len(payload['records'])==1
            assert payload['quickMemo']=='旧备忘'

            # Invalid import must not mutate data.
            await page.locator('#import-json').set_input_files(str(bad))
            await page.wait_for_timeout(100)
            assert await page.evaluate('Storage.getRecords().then(x=>x.length)')==1
            assert await page.evaluate('Storage.getMemo()')=='旧备忘'
            assert '无法解析 JSON 文件' in await page.locator('#toast-root').inner_text()

            # Valid import replaces all personal data and restores the derived input state.
            await page.locator('#import-json').set_input_files(str(backup))
            await page.wait_for_timeout(100)
            assert await page.evaluate('Storage.getRecords().then(x=>x.length)')==2
            assert await page.evaluate('Storage.getMemo()')=='恢复后的备忘'
            records=await page.evaluate('Storage.getRecords()')
            assert sorted([r['speciesName'] for r in records])==['白头鹎','白鹭']

            # Clear requires explicit confirmation and leaves personal data empty.
            await page.get_by_role('button', name='清空全部数据').click()
            assert await page.locator('#modal-root .modal').count()==1
            await page.get_by_role('button', name='取消').click()
            assert await page.evaluate('Storage.getRecords().then(x=>x.length)')==2
            await page.get_by_role('button', name='清空全部数据').click()
            await page.get_by_role('button', name='确认').click()
            await page.wait_for_timeout(80)
            assert await page.evaluate('Storage.getRecords().then(x=>x.length)')==0
            assert await page.evaluate('Storage.getMemo()')==''
            await browser.close()
    print('PHASE 7 PASS', flush=True)
    os._exit(0)

asyncio.run(main())
