import os
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]

def js(rel): return (ROOT/rel).read_text(encoding='utf-8')

RECORDS = [
    {'id':'r1','date':'2026-09-02','location':'东滩','speciesId':'cn_egret','speciesName':'白鹭','count':2,'updatedAt':'x'},
    {'id':'r2','date':'2026-08-20','location':'南汇','speciesId':'cn_egret','speciesName':'白鹭','count':1,'updatedAt':'x'},
    {'id':'r3','date':'2026-09-01','location':'共青','speciesId':'cn_bulbul','speciesName':'白头鹎','count':1,'updatedAt':'x'}
]

async def make_page(browser):
    page = await browser.new_page()
    await page.set_content('<div id="app"></div><div id="modal-root"></div><div id="toast-root"></div>')
    for rel in ['data/birds.js','data/bird_details.js','js/constants.js','js/utils.js','js/modules/bird_profiles.js','js/modules/lexicon.js']:
        await page.add_script_tag(content=js(rel))
    await page.evaluate('(records) => { window.AppState={records}; }', RECORDS)
    await page.evaluate("(async () => { LexiconPage.filter='all'; LexiconPage.keyword=''; await LexiconPage.render(); })()")
    return page

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-gpu'])
        page = await make_page(browser)
        assert await page.locator('.lexicon-item').count() == 544
        assert '已点亮' in await page.locator('.lexicon-item[data-bird=cn_egret]').inner_text()
        assert '2026-08-20' in await page.locator('.lexicon-item[data-bird=cn_egret]').inner_text()
        assert '未点亮' in await page.locator('.lexicon-item[data-bird=cn_tree_sparrow]').inner_text()

        await page.locator('[data-filter=discovered]').click()
        assert await page.locator('.lexicon-item').count() == 2
        assert await page.locator('[data-bird=cn_egret]').count() == 1
        assert await page.locator('[data-bird=cn_bulbul]').count() == 1
        await page.locator('[data-filter=undiscovered]').click()
        assert await page.locator('[data-bird=cn_egret]').count() == 0
        assert await page.locator('[data-bird=cn_tree_sparrow]').count() == 1
        await page.locator('[data-filter=all]').click()
        assert await page.locator('.lexicon-item').count() == 544
        await page.close()

        search_page = await make_page(browser)
        await search_page.locator('#lexicon-search').fill('白鹭')
        await search_page.wait_for_timeout(400)
        assert await search_page.locator('.lexicon-item').count() >= 1
        cards = await search_page.locator('.lexicon-item').all_inner_texts()
        assert all('白鹭' in card for card in cards)
        assert await search_page.locator('[data-bird=cn_egret]').count() == 1
        await search_page.close()

        click_page = await make_page(browser)
        await click_page.evaluate("window.fetch = async () => ({ok:false, status:503, json:async()=>({})});")
        await click_page.locator('[data-bird=cn_bulbul]').click()
        await click_page.wait_for_selector('#bird-detail-title')
        assert await click_page.locator('[data-first-seen]').count() == 1
        await click_page.locator('[data-first-seen]').click()
        assert await click_page.evaluate('location.hash') == '#/records'
        await click_page.close()
        await browser.close()
    print('PHASE 3 PASS', flush=True)
    os._exit(0)

asyncio.run(main())
