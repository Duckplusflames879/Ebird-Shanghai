import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const ctx = { window: {}, Intl, Date, Math, Set, String, Number, Object, Array, JSON, console };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(new URL('../js/utils.js', import.meta.url), 'utf8'), ctx);
const U = ctx.window.AppUtils;
const birds = [
  {id:'cn_egret', name:'白鹭', family:'鹭科', genus:'白鹭属'},
  {id:'cn_bulbul', name:'白头鹎', family:'鹎科', genus:'鹎属'},
  {id:'cn_other', name:'黑水鸡', family:'秧鸡科', genus:'水鸡属'}
];
assert.equal(new Set(birds.map(b=>b.id)).size, birds.length);
assert.equal(new Set(birds.map(b=>b.name)).size, birds.length);
assert.ok(birds.some(b=>b.name==='白鹭'));
assert.ok(birds.some(b=>b.name==='白头鹎'));
const records = [
  {id:'2', date:'2026-09-02', updatedAt:'2026-09-02T10:00:00Z', speciesId:'cn_egret', speciesName:'白鹭', count:2, location:'东滩', note:''},
  {id:'1', date:'2026-08-20', updatedAt:'2026-08-20T10:00:00Z', speciesId:'cn_egret', speciesName:'白鹭', count:1, location:'南汇', note:''},
  {id:'3', date:'2026-09-01', updatedAt:'2026-09-01T10:00:00Z', speciesId:'cn_other', speciesName:'黑水鸡', count:3, location:'共青', note:''}
];
const sorted=U.sortRecords(records);
assert.equal(JSON.stringify(sorted.map(r=>r.id)), JSON.stringify(['2','3','1']));
assert.equal(U.calculateFirstSeen(records,'cn_egret'),'2026-08-20');
assert.equal(JSON.stringify([...U.calculateDiscoveredIds(records)].sort()), JSON.stringify(['cn_egret','cn_other']));
assert.ok(U.generateBirdingAdvice({weatherType:'rain'}).includes('降雨'));
assert.equal(U.safeJsonParse('{bad').ok,false);
assert.equal(JSON.stringify(U.safeJsonParse('{"x":1}').value), JSON.stringify({x:1}));
console.log('PHASE 1 LOGIC PASS');
