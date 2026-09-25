import asyncio, os
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
SCRIPT=(ROOT/'birdreport-web-exporter.user.js').read_text(encoding='utf8')
async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-gpu'])
        page=await browser.new_page()
        await page.set_content('<!doctype html><html><body></body></html>')
        await page.add_script_tag(content=SCRIPT)
        records=[
          {'reportId':'R1','place':'滨江森林公园','observedAt':'2026-09-02 08:30:00','speciesName':'白鹭','count':3,'sourceUrl':'https://www.birdreport.cn/home/search/page.html'},
          {'reportId':'R1','place':'滨江森林公园','observedAt':'2026-09-02 08:30:00','speciesName':'白头鹎','count':2,'sourceUrl':'https://www.birdreport.cn/home/search/page.html'},
        ]
        result=await page.evaluate("rows => BirdReportWebExporterCore.buildData(rows, {start:'2026-08-27',end:'2026-09-02'})", records)
        assert len(result)==1
        assert result[0]['name']=='滨江森林公园'
        assert len(result[0]['records'])==2
        assert all(r['observedAt']=='2026-09-02 08:30:00' for r in result[0]['records'])
        await browser.close()
    print('PHASE 36 BIRDREPORT WEB EXPORT BROWSER PASS', flush=True)
    os._exit(0)
asyncio.run(main())
