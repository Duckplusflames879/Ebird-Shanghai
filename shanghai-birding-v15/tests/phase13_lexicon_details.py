import os
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]

def js(rel):
    return (ROOT / rel).read_text(encoding='utf8')

async def make_page(browser, records=None):
    page = await browser.new_page()
    await page.set_content('<div id="app"></div><div id="modal-root"></div><div id="toast-root"></div>')
    for rel in ['data/birds.js','data/bird_details.js','js/constants.js','js/utils.js','js/modules/bird_profiles.js','js/modules/lexicon.js']:
        await page.add_script_tag(content=js(rel))
    await page.evaluate('(records) => { window.AppState={records:records||[]}; }', records or [])
    await page.evaluate("(async () => { LexiconPage.filter='all'; LexiconPage.keyword=''; await LexiconPage.render(); })()")
    await page.wait_for_selector('#lexicon-results [data-bird]')
    return page

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-gpu'])

        # Both discovered and undiscovered entries open the same local detail structure.
        page = await make_page(browser, [{'id':'r1','date':'2026-09-01','location':'东滩','species':[{'speciesId':'cn_egret','speciesName':'白鹭','count':3}], 'speciesId':'cn_egret','speciesName':'白鹭','count':3}])
        for selector in ['.lexicon-item.undiscovered', '.lexicon-item.discovered[data-bird="cn_egret"]']:
            await page.locator(selector).first.click()
            await page.wait_for_selector('#bird-detail-title')
            sections = await page.locator('.bird-detail-section h3').all_inner_texts()
            assert sections == ['外观与识别','习性','栖息地','食性','迁徙与上海出现']
            body = await page.locator('.bird-detail-body').inner_text()
            assert '分类' in body and '属' in body
            assert '资料范围说明' not in sections
            assert '鸣声' not in sections
            assert '繁殖' not in sections
            assert '观察建议' not in sections
            assert '近似种比较提示' not in sections
            assert 'BirdNET' not in body
            assert '在线观察数' not in body
            assert '联网' not in body
            await page.locator('[data-close]').click()
        await page.close()

        # The detail module is fully local: it exposes no online-fetch API and never calls fetch.
        page = await make_page(browser)
        result = await page.evaluate("""() => ({
          keys: Object.keys(BirdProfiles),
          fetchSource: String(BirdProfiles.getLocal),
          fetchCount: typeof window.fetch === 'function' ? 0 : -1,
          detailKeys: Object.keys(BIRD_DETAILS.cn_egret)
        })""")
        assert result['keys'] == ['getLocal']
        assert 'fetch(' not in result['fetchSource']
        assert 'fetchOnline' not in result['fetchSource']
        assert result['detailKeys'] == ['id','name','family','genus','appearance','behavior','habitat','diet','migration']
        await page.close()
        await browser.close()
    print('PHASE 13 PASS', flush=True)
    os._exit(0)

asyncio.run(main())
