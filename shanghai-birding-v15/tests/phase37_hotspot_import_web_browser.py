import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
def js(rel): return (ROOT/rel).read_text(encoding='utf8')
async def main():
    fixture={
      'format':'shanghai-birding-hotspots-7d','version':1,'app':'shanghai-birding','source':'中国观鸟记录中心',
      'sourceUrl':'https://www.birdreport.cn/home/search/page.html','generatedAt':'2026-09-02T09:00:00+08:00','retrievedAt':'2026-09-02T09:00:00+08:00',
      'observationWindow':{'start':'2026-08-27','end':'2026-09-02'},
      'hotspotData':{'source':'中国观鸟记录中心','observationWindow':{'start':'2026-08-27','end':'2026-09-02'},'retrievedAt':'2026-09-02T09:00:00+08:00','sourceObservationCount':2},
      'hotspots':[{'id':'binjiang','name':'滨江森林公园','district':'浦东新区','lat':31.48,'lon':121.58,'records':[{'observationId':'r1','speciesId':'','speciesName':'白鹭','observedAt':'2026-09-02 08:30:00','latestCount':3,'totalCount':3,'occurrenceCount':1}]}]
    }
    async with async_playwright() as p:
        b=await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-gpu'])
        page=await b.new_page()
        await page.set_content('<div id="app"></div>')
        for rel in ['data/birds.js','data/latest_data.js','js/constants.js','js/utils.js','js/storage.js','js/state.js','js/components/toast.js','js/components/modal.js','js/modules/ebird.js','js/modules/hotspots.js']:
            await page.add_script_tag(content=js(rel))
        result=await page.evaluate('data=>HotspotsPage.importGenericFile(new File([JSON.stringify(data)],"x.json",{type:"application/json"}))', fixture)
        assert result['success'] is True and result['hotspotCount']==1 and result['recordCount']==1
        assert await page.evaluate('AppState.externalData.hotspotData.source')=='中国观鸟记录中心'
        await b.close()
asyncio.run(main())
print('PHASE 37 HOTSPOT IMPORT WEB BROWSER PASS')
