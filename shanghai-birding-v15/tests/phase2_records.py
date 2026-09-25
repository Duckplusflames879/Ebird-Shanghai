import os
import json
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]

def js(rel): return (ROOT / rel).read_text(encoding='utf8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-gpu'])
        page = await browser.new_page()
        await page.set_content('<div id="app"></div><div id="modal-root"></div><div id="toast-root"></div>')
        await page.evaluate("window.indexedDB = undefined")
        for rel in ['data/birds.js','data/latest_data.js','js/constants.js','js/utils.js','js/storage.js','js/state.js','js/components/modal.js','js/components/toast.js','js/components/autocomplete.js','js/modules/records.js']:
            await page.add_script_tag(content=js(rel))
        await page.evaluate("AppState.records=[]; AppState.memos=[]; AppState.memo=''; AppState.externalData=window.EXTERNAL_DATA")
        fixture_data=json.loads((ROOT/'tests'/'external_fixture.json').read_text(encoding='utf8'))
        await page.evaluate("(data)=>{AppState.externalData=data}", fixture_data)

        await page.evaluate("RecordsPage.render()")
        await page.get_by_role('button', name='＋ 新增记录').click()
        await page.locator('#hotspot-select').select_option('dongtan')

        rows=page.locator('[data-species-row]')
        await rows.nth(0).locator('.species-input').fill('白')
        await page.wait_for_selector('.autocomplete-menu:not([hidden])')
        suggestions = await page.locator('.autocomplete-item').all_inner_texts()
        assert any('白鹭' in x for x in suggestions)
        assert any('白头鹎' in x for x in suggestions)
        await page.locator('.autocomplete-item', has_text='白鹭').first.click()
        await rows.nth(0).locator('.species-count').fill('3')

        await page.get_by_role('button', name='＋ 添加鸟种').click()
        rows=page.locator('[data-species-row]')
        await rows.nth(1).locator('.species-input').fill('苍')
        await page.wait_for_selector('.autocomplete-menu:not([hidden])')
        await page.locator('.autocomplete-item', has_text='苍鹭').first.click()
        await rows.nth(1).locator('.species-count').fill('7')
        await page.locator('textarea[name=note]').fill('退潮后观察')
        await page.get_by_role('button', name='保存').click()
        await page.wait_for_function('AppState.records.length === 1')
        record=await page.evaluate('AppState.records[0]')
        assert record['hotspotId']=='dongtan'
        assert record['location']=='崇明东滩'
        assert [(x['speciesName'],x['count']) for x in record['species']]==[('白鹭',3),('苍鹭',7)]
        assert await page.get_by_text('白鹭 × 3、苍鹭 × 7').count()==1

        await page.get_by_role('button', name='编辑').click()
        assert await page.locator('[data-species-row]').count()==2
        await page.locator('[data-species-row]').nth(1).locator('.species-count').fill('8')
        await page.get_by_role('button', name='保存').click()
        await page.wait_for_function('AppState.records[0].species[1].count === 8')
        assert await page.get_by_text('白鹭 × 3、苍鹭 × 8').count()==1

        # Validation failure must keep the same form open with every entered value intact.
        await page.get_by_role('button', name='＋ 新增记录').click()
        await page.locator('#record-form input[name=date]').fill('2026-09-01')
        await page.locator('#hotspot-select').select_option('dongtan')
        rows=page.locator('[data-species-row]')
        await rows.nth(0).locator('.species-input').fill('白')
        await page.wait_for_selector('.autocomplete-menu:not([hidden])')
        await page.locator('.autocomplete-item', has_text='白鹭').first.click()
        await rows.nth(0).locator('.species-count').fill('5')
        await page.get_by_role('button', name='＋ 添加鸟种').click()
        rows=page.locator('[data-species-row]')
        await rows.nth(1).locator('.species-input').fill('苍')
        await page.wait_for_selector('.autocomplete-menu:not([hidden])')
        await page.locator('.autocomplete-item', has_text='苍鹭').first.click()
        await rows.nth(1).locator('.species-count').fill('8')
        await page.locator('textarea[name=note]').fill('信息完整，但故意测试缺失日期')
        await page.locator('#record-form input[name=date]').fill('')
        await page.get_by_role('button', name='保存').click()
        await page.wait_for_selector('#toast-root .toast')
        assert await page.locator('#modal-root .modal').count()==1
        assert await page.locator('#record-form input[name=date]').input_value()==''
        assert await page.locator('#hotspot-select').input_value()=='dongtan'
        rows=page.locator('[data-species-row]')
        assert await rows.count()==2
        assert await rows.nth(0).locator('.species-input').input_value()=='白鹭'
        assert await rows.nth(0).locator('.species-count').input_value()=='5'
        assert await rows.nth(1).locator('.species-input').input_value()=='苍鹭'
        assert await rows.nth(1).locator('.species-count').input_value()=='8'
        assert await page.locator('textarea[name=note]').input_value()=='信息完整，但故意测试缺失日期'
        await page.locator('#modal-root [data-cancel]').click()

        await page.get_by_role('button', name='＋ 新增记录').click()
        await page.locator('#hotspot-select').select_option('dongtan')
        await page.locator('[data-species-row]').nth(0).locator('.species-input').fill('非法鸟')
        await page.locator('[data-species-row]').nth(0).locator('.species-count').fill('1')
        await page.get_by_role('button', name='保存').click()
        await page.wait_for_timeout(100)
        assert await page.locator('#modal-root .modal').count()==1
        assert await page.locator('#toast-root .toast').count()==1
        assert await page.evaluate('AppState.records.length')==1
        await page.locator('#modal-root [data-cancel]').click()

        await page.get_by_role('button', name='删除').click()
        await page.get_by_role('button', name='确认').click()
        await page.wait_for_timeout(50)
        assert await page.evaluate('AppState.records.length')==0
        assert await page.get_by_text('还没有记录').count()==1
        await browser.close()
    print('PHASE 2 PASS', flush=True)
    os._exit(0)

asyncio.run(main())
