import os
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
def js(rel): return (ROOT/rel).read_text(encoding='utf8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-gpu'])
        page = await browser.new_page()
        await page.set_content('<div id="app"></div><div id="modal-root"></div><div id="toast-root"></div>')
        await page.evaluate("window.indexedDB = undefined")
        for rel in ['data/birds.js','data/latest_data.js','js/constants.js','js/utils.js','js/storage.js','js/state.js','js/components/modal.js','js/components/toast.js','js/modules/home.js']:
            await page.add_script_tag(content=js(rel))
        await page.evaluate("AppState.records=[{id:'r1',date:'2026-09-01',location:'南汇',speciesId:'cn_bulbul',speciesName:'白头鹎',count:1,note:'旧记录',updatedAt:'2026-09-01T10:00:00Z'},{id:'r2',date:'2026-09-02',location:'东滩',speciesId:'cn_egret',speciesName:'白鹭',count:3,note:'今天看到',updatedAt:'2026-09-02T10:00:00Z'}]; AppState.memos=[]; AppState.memo=''; AppState.externalData=window.EXTERNAL_DATA;")
        await page.evaluate("HomePage.render()")
        assert '2 / 544 种' in await page.locator('#app').inner_text()
        assert await page.get_by_text('白鹭 × 3').count() == 1
        assert '东滩' in await page.locator('#app').inner_text()
        assert '天气与观鸟简报' in await page.locator('#app').inner_text()

        # The old single memo behavior remains available through the first memo editor.
        await page.get_by_role('button', name='＋ 添加备忘').click()
        await page.locator('#modal-root textarea[name=text]').fill('周日去东滩，带望远镜')
        await page.get_by_role('button', name='保存').click()
        await page.wait_for_selector('[data-memo-input]')
        memo=page.locator('[data-memo-input]').first
        await memo.fill('周日去东滩，带望远镜')
        await memo.blur()
        await page.wait_for_timeout(80)
        assert await page.evaluate("Storage.getMemo()") == '周日去东滩，带望远镜'
        await page.wait_for_timeout(450)
        assert await page.evaluate("Storage.getMemo()") == '周日去东滩，带望远镜'
        await page.evaluate("AppStateActions.refreshPersonal().then(()=>HomePage.render())")
        await page.wait_for_selector('[data-memo-input]')
        assert await page.locator('[data-memo-input]').first.input_value() == '周日去东滩，带望远镜'
        assert await page.locator('a[href="#/records"]').count() == 1
        await browser.close()
    print('PHASE 4 PASS', flush=True)
    os._exit(0)

asyncio.run(main())
