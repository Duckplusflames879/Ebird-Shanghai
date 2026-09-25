import asyncio, json, os
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
RAW=[
  {"speciesCode":"cnbulb1","comName":"白头鹎","sciName":"Pycnonotus sinensis","locId":"L-BINJ","locName":"Binjiang Forest Park, Shanghai, China","subnational1Name":"上海市","subnational2Name":"浦东新区","lat":31.48,"lng":121.58,"obsDt":"2026-09-02 06:42","howMany":3,"subId":"S100"},
  {"speciesCode":"cnbulb1","comName":"白头鹎","sciName":"Pycnonotus sinensis","locId":"L-BINJ","locName":"滨江森林公园","subnational1Name":"上海市","subnational2Name":"浦东新区","lat":31.48,"lng":121.58,"obsDt":"2026-08-30 07:10","howMany":2,"subId":"S099"},
]

def js(rel): return (ROOT/rel).read_text(encoding='utf-8')

async def main():
  async with async_playwright() as p:
    browser=await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-gpu'])
    page=await browser.new_page()
    await page.set_content('<div id="app"></div>')
    await page.add_script_tag(content="""window.AppState={records:[],memos:[],memo:'',externalData:{weather:null,hotspots:[],hotspotData:{},sourceStatus:'not_fetched'}};window.AppStateActions={notify(){}};window.Storage={getAppValue:async()=> 'TEST-KEY',setAppValue:async()=>{}};""")
    await page.add_script_tag(content=js('js/utils.js'))
    await page.add_script_tag(content=js('js/modules/ebird.js'))
    result=await page.evaluate("""async (rows) => {
      window.fetch = async (url, options) => ({ok:true,status:200,json:async()=>rows});
      return await window.EBirdData.fetchRecent({force:true, apiKey:'TEST-KEY'});
    }""", RAW)
    assert result['success'] is True
    assert result['hotspotCount'] == 1
    assert result['recordCount'] == 1
    data=await page.evaluate("window.AppState.externalData.hotspots")
    assert data[0]['name']=='滨江森林公园'
    assert data[0]['lat']==31.48 and data[0]['lon']==121.58
    assert data[0]['records'][0]['speciesName']=='白头鹎'
    assert data[0]['records'][0]['observedAt']=='2026-09-02 06:42'
    assert data[0]['records'][0]['latestCount']==3
    await browser.close()
  print('PHASE 30 EBIRD FETCH BROWSER PASS', flush=True)
  os._exit(0)

asyncio.run(main())
