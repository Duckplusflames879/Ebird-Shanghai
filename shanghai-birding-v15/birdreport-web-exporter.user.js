// ==UserScript==
// @name         上海观鸟系统：中国观鸟记录中心浏览器采集助手
// @namespace    shanghai-birding
// @version      1.1.0
// @description  在中国观鸟记录中心“记录查询”页面中，把当前查询结果及报告详情整理成上海观鸟系统可直接导入的最近7日 JSON。使用当前浏览器会话，不需要 Python 或额外 API Token。
// @match        https://www.birdreport.cn/home/search/page.html*
// @grant        none
// ==/UserScript==
(function () {
  'use strict';
  const FORMAT='shanghai-birding-hotspots-7d';
  const SOURCE='中国观鸟记录中心';
  const SOURCE_URL='https://www.birdreport.cn/home/search/page.html';
  const text=v=>String(v??'').replace(/\s+/g,' ').trim();
  const zh=v=>/[\u3400-\u4dbf\u4e00-\u9fff]/.test(text(v));
  function parseDateTime(v){const t=text(v).replace(/[./]/g,'-').replace(/年|月/g,'-').replace(/日/g,'');const m=t.match(/(20\d{2})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?/);return m?`${m[1]}-${String(m[2]).padStart(2,'0')}-${String(m[3]).padStart(2,'0')} ${String(m[4]).padStart(2,'0')}:${m[5]}:${m[6]||'00'}`:'';}
  function window7(){const e=new Date();const end=new Date(e.getFullYear(),e.getMonth(),e.getDate());const st=new Date(end);st.setDate(st.getDate()-6);const iso=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;return {start:iso(st),end:iso(end)};}
  function rows(table){const rs=[...table.querySelectorAll('tr')];if(rs.length<2)return[];const hs=[...rs[0].querySelectorAll('th,td')].map(x=>text(x.innerText));return rs.slice(1).map(row=>{const vs=[...row.querySelectorAll('td,th')].map(x=>text(x.innerText));const r={};hs.forEach((h,i)=>r[h]=vs[i]||'');return {r,row};}).filter(x=>Object.keys(x.r).length);}
  function findReportTable(){return [...document.querySelectorAll('table')].map(table=>({table,rows:rows(table)})).find(x=>x.rows.some(x=>/观测时间/.test(Object.keys(x.r).join('|'))&&/观测地点/.test(Object.keys(x.r).join('|'))));}
  function findSpeciesTable(doc){return [...doc.querySelectorAll('table')].map(table=>({table,rows:rows(table)})).find(x=>x.rows.some(x=>/(中文名|鸟种)/.test(Object.keys(x.r).join('|'))&&/数量/.test(Object.keys(x.r).join('|'))));}
  const val=(r,ps)=>{const k=Object.keys(r).find(k=>ps.some(p=>p.test(k)));return k?r[k]:'';};
  async function detailDoc(url){return new Promise(resolve=>{const f=document.createElement('iframe');f.style.cssText='position:fixed;left:-10000px;top:-10000px;width:1px;height:1px;opacity:0;';let finished=false;const done=v=>{if(finished)return;finished=true;f.remove();resolve(v)};f.onload=()=>setTimeout(()=>{try{done(f.contentDocument)}catch(_){done(null)}},1200);setTimeout(()=>done(null),12000);f.src=url;document.body.appendChild(f);});}
  function buildData(records,w){const grouped=new Map();for(const r of records){const place=zh(r.place)?r.place:'其它观测记录';const pk=place==='上海'||place==='上海市'?'其它观测记录':place;const k=`${pk}::${r.speciesName}`;const old=grouped.get(k);if(!old||r.observedAt>old.observedAt)grouped.set(k,{...r,place:pk,latestCount:r.count,totalCount:r.count,occurrenceCount:(old?.occurrenceCount||0)+1});else{old.totalCount+=r.count;old.occurrenceCount+=1;}}const hs=new Map();for(const r of grouped.values()){const key=r.place==='其它观测记录'?'other_shanghai':r.place;const h=hs.get(key)||{id:key,name:r.place,district:r.place==='其它观测记录'?'上海市':'',lat:null,lon:null,discovery:r.place==='其它观测记录'?'city_level':'web_import',source:SOURCE,sourceUrl:SOURCE_URL,observationWindow:w,records:[]};h.records.push({observationId:r.reportId,speciesId:'',speciesName:r.speciesName,observedAt:r.observedAt,latestCount:r.latestCount,totalCount:r.totalCount,occurrenceCount:r.occurrenceCount,sourceUrl:r.sourceUrl||SOURCE_URL});hs.set(key,h);}for(const h of hs.values()){h.records.sort((a,b)=>b.observedAt.localeCompare(a.observedAt));h.observations=h.records.map(r=>({speciesId:r.speciesId,speciesName:r.speciesName,frequency:r.occurrenceCount}));h.observationCount=h.records.length;}return [...hs.values()].filter(h=>h.records.length);}
  async function collect(){const w=window7();const found=findReportTable();if(!found)throw Error('未找到观测报告表。请先打开中国观鸟记录中心“记录查询”页面并执行查询。');const reports=[];for(const x of found.rows){const reportId=val(x.r,[/报告编号/,/记录编号/]);const observedAt=parseDateTime(val(x.r,[/观测时间/]));const place=text(val(x.r,[/观测地点/]));const a=x.row.querySelector('a[href]');if(reportId&&observedAt&&place&&(observedAt>=`${w.start} 00:00:00`&&observedAt<=`${w.end} 23:59:59`))reports.push({reportId,observedAt,place,url:a?new URL(a.href,location.href).href:''});}
    if(!reports.length)throw Error('当前结果中没有最近7日且包含具体时分的公开报告。');
    const records=[];
    for(let i=0;i<reports.length;i++){const rp=reports[i];if(!rp.url)continue;const doc=await detailDoc(rp.url);if(!doc)continue;const st=findSpeciesTable(doc);if(!st)continue;for(const x of st.rows){const speciesName=text(val(x.r,[/中文名/,/^鸟种$/]));const count=Number.parseInt(String(val(x.r,[/数量/])).replace(/[^0-9]/g,''),10)||0;if(zh(speciesName)&&count>0)records.push({reportId:rp.reportId,place:rp.place,observedAt:rp.observedAt,speciesName,count,sourceUrl:rp.url});}}
    if(!records.length)throw Error('没有从报告详情中采集到带具体时间的中文鸟种记录。');
    const hotspots=buildData(records,w);return {format:FORMAT,version:1,app:'shanghai-birding',source:SOURCE,sourceUrl:SOURCE_URL,generatedAt:new Date().toISOString(),retrievedAt:new Date().toISOString(),observationWindow:w,hotspotData:{source:SOURCE,sourceUrl:SOURCE_URL,retrievedAt:new Date().toISOString(),observationWindow:w,sourceObservationCount:records.length,displayedRecordCount:hotspots.reduce((n,h)=>n+h.records.length,0)},hotspots};}
  function download(data){const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`birdreport-7d-import-${data.observationWindow.end}.json`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  function install(){if(document.getElementById('__shbird_web_exporter'))return;const b=document.createElement('button');b.id='__shbird_web_exporter';b.textContent='导出最近7日到上海观鸟系统';b.style.cssText='position:fixed;right:20px;bottom:20px;z-index:2147483647;padding:12px 16px;background:#1769aa;color:#fff;border:0;border-radius:8px;box-shadow:0 3px 12px rgba(0,0,0,.25);font-size:14px;cursor:pointer';b.onclick=async()=>{b.disabled=true;b.textContent='采集中…';try{const data=await collect();download(data);b.textContent=`已生成 ${data.hotspots.length} 个点位`;}catch(e){alert(`采集失败：${e.message||e}`);b.textContent='导出最近7日到上海观鸟系统';}finally{b.disabled=false;}};document.body.appendChild(b);}
  window.BirdReportWebExporterCore={parseDateTime,window7,rows,buildData,collect};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install);else install();
})();
