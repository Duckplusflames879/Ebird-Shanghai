import os
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]

def js(rel):
    return (ROOT / rel).read_text(encoding='utf8')

async def make_page(browser):
    page = await browser.new_page()
    await page.set_content('<div id="app"></div><div id="modal-root"></div><div id="toast-root"></div>')
    for rel in ['data/birds.js','js/constants.js','js/utils.js','js/modules/lexicon.js']:
        await page.add_script_tag(content=js(rel))
    await page.evaluate('(records) => { window.AppState={records}; }', [])
    await page.evaluate("(async () => { LexiconPage.filter='all'; LexiconPage.keyword=''; await LexiconPage.render(); })()")
    await page.wait_for_selector('#lexicon-search')
    return page

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-gpu'])

        page = await make_page(browser)
        assert await page.locator('.lexicon-item').count() == 544
        assert await page.locator('#lexicon-search').count() == 1
        await page.locator('#lexicon-search').fill('白鹭')
        await page.wait_for_timeout(180)
        assert await page.locator('[data-bird=cn_egret]').count() == 1
        await page.close()

        ime = await make_page(browser)
        search = ime.locator('#lexicon-search')
        await search.focus()
        await search.evaluate("""el => {
            window.__imeSearchOriginal = el;
            el.dispatchEvent(new CompositionEvent('compositionstart', {bubbles:true, data:''}));
            el.value = '白';
            el.dispatchEvent(new Event('input', {bubbles:true}));
        }""")
        await ime.wait_for_timeout(220)
        assert await ime.evaluate("window.__imeSearchOriginal === document.getElementById('lexicon-search')")
        assert await search.input_value() == '白'
        assert await ime.locator('.lexicon-item').count() == 544

        await search.evaluate("el => el.dispatchEvent(new CompositionEvent('compositionend', {bubbles:true, data:'白'}))")
        await ime.wait_for_timeout(120)
        assert await search.input_value() == '白'
        cards = await ime.locator('.lexicon-item').all_inner_texts()
        assert cards and all('白' in card for card in cards)
        assert await ime.locator('[data-bird=cn_egret]').count() == 1
        await ime.close()
        await browser.close()

    print('PHASE 12 PASS', flush=True)
    os._exit(0)

asyncio.run(main())
