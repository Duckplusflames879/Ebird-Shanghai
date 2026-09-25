import os
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [
    'data/birds.js','data/latest_data.js','data/bird_details.js','js/constants.js','js/utils.js','js/storage.js','js/state.js',
    'js/components/modal.js','js/components/toast.js','js/components/sidebar.js','js/components/autocomplete.js',
    'js/auto_update.js','js/modules/home.js','js/modules/weather.js','js/modules/hotspots.js','js/modules/records.js','js/modules/lexicon.js','js/modules/settings.js','js/router.js','js/app.js'
]
SHELL = '''<!doctype html><html lang="zh-CN"><body>
<div id="app-shell"><aside id="sidebar"></aside><main><header id="page-header"></header><section id="app"></section></main></div>
<div id="modal-root"></div><div id="toast-root"></div>
</body></html>'''

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-gpu'])
        page = await browser.new_page(viewport={'width': 1440, 'height': 900})
        await page.set_content(SHELL)
        page.on('console', lambda msg: print('BROWSER:', msg.type, msg.text) if msg.type == 'error' else None)
        for rel in SCRIPTS:
            await page.add_script_tag(content=(ROOT / rel).read_text(encoding='utf-8'))
        await page.evaluate("window.location.hash = '#/home'")
        await page.wait_for_selector('#sidebar .nav-link')
        assert await page.locator('.nav-link').count() == 6
        assert await page.locator('.page-title').inner_text() == '首页'
        for route, title in [('/weather','天气'),('/hotspots','观鸟点'),('/records','我的记录'),('/lexicon','图鉴'),('/settings','设置'),('/home','首页')]:
            await page.evaluate(f"window.location.hash = '#{route}'")
            await page.wait_for_selector('.page-title')
            assert await page.locator('.page-title').inner_text() == title, route
        assert await page.locator('.nav-link.active').get_attribute('data-route') == '/home'
        await browser.close()
    print('PHASE 0 PASS', flush=True)
    os._exit(0)

asyncio.run(main())
