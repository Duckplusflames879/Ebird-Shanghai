import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ebird=(ROOT/'js/modules/ebird.js').read_text(encoding='utf8')
assert "const SOURCE = 'eBird'" in ebird
assert "const REGION_CODE = 'CN-31'" in ebird
assert "back', '7'" in ebird
assert "hotspot', 'true'" in ebird
assert "sppLocale', 'zh_SIM'" in ebird

rows=[
 {'speciesCode':'sp1','comName':'白头鹎','locId':'L-BINJ','locName':'Binjiang Forest Park, Shanghai, China','subnational2Name':'浦东新区','lat':31.48,'lng':121.58,'obsDt':'2026-09-02 08:00','howMany':2,'subId':'S2'},
 {'speciesCode':'sp1','comName':'白头鹎','locId':'L-BINJ','locName':'滨江森林公园','subnational2Name':'浦东新区','lat':31.48,'lng':121.58,'obsDt':'2026-08-30 07:00','howMany':3,'subId':'S1'},
 {'speciesCode':'sp2','comName':'白鹭','locId':'L-BINJ','locName':'滨江森林公园','subnational2Name':'浦东新区','lat':31.48,'lng':121.58,'obsDt':'2026-09-01 06:30','howMany':1,'subId':'S3'},
]
js=f"""
globalThis.window=globalThis;
globalThis.AppState={{externalData:{{weather:null,hotspots:[],hotspotData:{{}},sourceStatus:'not_fetched'}}}};
globalThis.Storage={{getAppValue:async()=>'',setAppValue:async()=>{{}}}};
globalThis.AppUtils={{todayISO:()=> '2026-09-02'}};
const fs=require('fs');
eval(fs.readFileSync('{(ROOT/'js/modules/ebird.js').as_posix()}','utf8'));
const rows={json.dumps(rows,ensure_ascii=False)};
const out=window.EBirdData.aggregateObservations(rows, {{start:'2026-08-27',end:'2026-09-02'}});
if(out.hotspots.length!==1) throw new Error('expected one merged hotspot');
if(out.hotspots[0].name!=='滨江森林公园') throw new Error('expected Chinese hotspot name');
const records=out.hotspots[0].records;
const bul=records.find(r=>r.speciesName==='白头鹎');
if(!bul || bul.observedAt!=='2026-09-02 08:00') throw new Error('latest observation time rule failed');
if(bul.totalCount!==5 || bul.occurrenceCount!==2) throw new Error('aggregation count rule failed');
if(records.some(r=>!r.observedAt || !r.observedAt.includes(':'))) throw new Error('unknown time leaked');
console.log('PHASE 15 HOTSPOT EBIRD DATA PASS');
"""
run=subprocess.run(['node','-e',js],capture_output=True,text=True)
assert run.returncode==0, run.stderr
print(run.stdout.strip())
