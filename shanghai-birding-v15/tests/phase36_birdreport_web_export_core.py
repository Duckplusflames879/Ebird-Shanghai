import json, subprocess, textwrap
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
script=(ROOT/'birdreport-web-exporter.user.js').read_text(encoding='utf8')
node=textwrap.dedent('''
const fs=require('fs'),vm=require('vm');
const code=fs.readFileSync(process.argv[1],'utf8');
const sandbox={window:{},document:{readyState:'complete',addEventListener(){},getElementById(){return null;},createElement(){return {style:{},appendChild(){},remove(){}};},body:{appendChild(){}}},location:{href:'https://www.birdreport.cn/home/search/page.html'},URL,Blob,Date,Map,Set,console};
sandbox.window.BirdReportWebExporterCore={};
vm.createContext(sandbox);vm.runInContext(code,sandbox);
const c=sandbox.window.BirdReportWebExporterCore;
if(c.parseDateTime('2026-09-02 08:30').length!==19) throw new Error('datetime parser');
const rows=[
 {reportId:'r1',place:'滨江森林公园',observedAt:'2026-09-01 08:00:00',speciesName:'白鹭',count:2,sourceUrl:'x'},
 {reportId:'r2',place:'滨江森林公园',observedAt:'2026-09-02 09:00:00',speciesName:'白鹭',count:3,sourceUrl:'y'},
 {reportId:'r3',place:'上海市',observedAt:'2026-09-02 07:00:00',speciesName:'白头鹎',count:1,sourceUrl:'z'}
];
const out=c.buildData(rows,{start:'2026-08-27',end:'2026-09-02'});
if(out.length!==2) throw new Error('hotspot grouping');
const b=out.find(x=>x.name==='滨江森林公园'); if(!b || b.records.length!==1 || b.records[0].observedAt!=='2026-09-02 09:00:00' || b.records[0].occurrenceCount!==2) throw new Error('latest aggregation');
const o=out.find(x=>x.name==='其它观测记录'); if(!o || o.lat!==null || o.lon!==null) throw new Error('city-level grouping');
''')
res=subprocess.run(['node','-e',node,str(ROOT/'birdreport-web-exporter.user.js')],capture_output=True,text=True)
if res.returncode!=0: raise SystemExit(res.stderr or res.stdout)
print('PHASE 36 BIRDREPORT WEB EXPORT CORE PASS')
