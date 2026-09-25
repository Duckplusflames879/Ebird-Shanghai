import os
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]

def script(path):
    return (ROOT / path).read_text(encoding='utf-8')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-gpu'])
        page = await browser.new_page()
        await page.set_content('<div id="app"></div><div id="sidebar"></div><header id="page-header"></header><div id="modal-root"></div><div id="toast-root"></div>')
        await page.evaluate("window.indexedDB = undefined")
        for rel in ['data/birds.js','js/constants.js','js/utils.js','js/storage.js','js/state.js']:
            await page.add_script_tag(content=script(rel))
        await page.evaluate("""
          window.BIRD_LEXICON = [
            {id:'cn_egret',name:'白鹭',family:'鹭科',genus:'白鹭属'},
            {id:'cn_bulbul',name:'白头鹎',family:'鹎科',genus:'鹎属'}
          ];
        """)
        assert await page.evaluate("Storage.getRecords()") == []
        await page.evaluate("Storage.addRecord({id:'r1',date:'2026-09-02',location:'东滩',speciesId:'cn_egret',speciesName:'白鹭',count:2,note:'x',createdAt:'x',updatedAt:'x'})")
        assert await page.evaluate("Storage.getRecords().then(x => x.length)") == 1
        assert await page.evaluate("Storage.getRecords().then(x => x[0].speciesName)") == '白鹭'
        await page.evaluate("Storage.saveMemo('周末去东滩')")
        assert await page.evaluate("Storage.getMemo()") == '周末去东滩'
        await page.evaluate("(async () => Storage.updateRecord({...await Storage.getRecords().then(x=>x[0]), count:3}))()")
        assert await page.evaluate("Storage.getRecords().then(x=>x[0].count)") == 3
        await page.evaluate("Storage.deleteRecord('r1')")
        assert await page.evaluate("Storage.getRecords()") == []
        await page.evaluate("Storage.saveMemo('')")
        assert await page.evaluate("Storage.getMemo()") == ''
        await browser.close()
    print('PHASE 1 BROWSER STORAGE PASS', flush=True)
    os._exit(0)

asyncio.run(main())
