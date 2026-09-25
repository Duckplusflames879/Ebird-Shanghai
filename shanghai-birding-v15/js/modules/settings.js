(function () {
  function exportPayload() {
    const currentMemos = Array.isArray(AppState.memos) ? AppState.memos : [];
    const memos = currentMemos.length ? currentMemos.map(m => ({id:String(m.id), text:String(m.text ?? ''), createdAt:String(m.createdAt || ''), updatedAt:String(m.updatedAt || '')})) : (AppState.memo ? [{id:AppUtils.uid('memo'), text:String(AppState.memo), createdAt:new Date().toISOString(), updatedAt:new Date().toISOString()}] : []);
    return { version:1, app:'shanghai-birding', exportedAt:new Date().toISOString(), records:AppUtils.sortRecords(AppState.records || []), memos, quickMemo:memos[0]?.text || '' };
  }
  function normalizeBackupMemos(data) {
    if (Array.isArray(data.memos)) return data.memos.map(m => ({id:String(m.id || AppUtils.uid('memo')), text:String(m.text ?? ''), createdAt:String(m.createdAt || new Date().toISOString()), updatedAt:String(m.updatedAt || new Date().toISOString())}));
    return data.quickMemo ? [{id:AppUtils.uid('memo'), text:String(data.quickMemo), createdAt:new Date().toISOString(), updatedAt:new Date().toISOString()}] : [];
  }
  function validateBackup(data) {
    if (!data || data.app !== 'shanghai-birding' || data.version !== 1 || !Array.isArray(data.records)) return {ok:false,error:'JSON 不是可识别的上海观鸟备份文件。'};
    if (data.memos !== undefined && !Array.isArray(data.memos)) return {ok:false,error:'备份文件的 memos 字段无效，未导入任何数据。'};
    if (data.memos === undefined && typeof data.quickMemo !== 'string') return {ok:false,error:'备份文件缺少可识别的备忘数据，未导入任何数据。'};
    const ids = new Set();
    for (const raw of data.records) {
      if (!raw || typeof raw.id !== 'string' || ids.has(raw.id)) return {ok:false,error:'备份文件包含重复或无效记录编号，未导入任何数据。'};
      ids.add(raw.id);
      const r=AppUtils.normalizeRecord(raw);
      if (!/^\d{4}-\d{2}-\d{2}$/.test(r.date) || !r.location || !Array.isArray(r.species) || !r.species.length) return {ok:false,error:'备份文件包含无效记录，未导入任何数据。'};
      const speciesIds=new Set();
      for(const s of r.species){
        const species=BIRD_LEXICON.find(b=>b.id===s.speciesId && b.name===s.speciesName);
        if(!species || !Number.isInteger(s.count) || s.count<1 || speciesIds.has(s.speciesId)) return {ok:false,error:'备份文件包含无效鸟种数据，未导入任何数据。'};
        speciesIds.add(s.speciesId);
      }
    }
    const memoIds=new Set();
    for(const memo of normalizeBackupMemos(data)){
      if(!memo.id || memoIds.has(memo.id) || !memo.text.trim()) return {ok:false,error:'备份文件包含无效备忘数据，未导入任何数据。'};
      memoIds.add(memo.id);
    }
    return {ok:true};
  }
  async function importBackup(file) {
    const text=await file.text(); const parsed=AppUtils.safeJsonParse(text); if(!parsed.ok) return {ok:false,error:'无法解析 JSON 文件。'};
    const checked=validateBackup(parsed.value); if(!checked.ok) return checked;
    const memos=normalizeBackupMemos(parsed.value);
    await Storage.clearAll();
    for (const raw of parsed.value.records) await Storage.addRecord(AppUtils.normalizeRecord(raw));
    for (const memo of memos) await Storage.addMemo(memo.text);
    await AppStateActions.refreshPersonal(); AppStateActions.notify();
    return {ok:true};
  }
  async function render() {
    const memoCount=(AppState.memos||[]).length;
    document.getElementById('app').innerHTML=`<div class="grid" style="gap:18px"><section class="card settings-section"><strong>数据备份</strong><div class="muted" style="margin:5px 0 14px">导出完整个人记录和全部备忘。</div><button class="button primary" id="export-json">导出 JSON</button></section><section class="card settings-section"><strong>数据恢复</strong><div class="muted" style="margin:5px 0 14px">导入同版本 JSON 备份，会替换当前个人数据。</div><input id="import-json" type="file" accept="application/json,.json" class="input"></section><section class="card settings-section"><strong>观鸟点数据</strong><input id="ebird-api-key" type="hidden" value="" autocomplete="off" aria-hidden="true"><div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:12px"><button class="button primary" id="fetch-ebird">获取最近7日数据</button><button class="button" id="export-ebird">导出当前 eBird JSON</button></div><input id="import-ebird" type="file" accept="application/json,.json" class="input" style="margin-top:12px"><div class="muted" style="margin-top:8px">同一地点会自动合并，同一地点同一鸟种仅保留最晚观测时间。数据源：eBird, Cornell Lab of Ornithology（上海区域 CN-31）。</div></section><section class="card settings-section"><strong>危险操作</strong><div class="muted" style="margin:5px 0 14px">清空所有观鸟记录和全部备忘；图鉴状态会随记录重新计算。</div><button class="button danger" id="clear-data">清空全部数据</button></section><section class="card settings-section"><strong>个人数据</strong><div class="status-row"><span>观鸟记录</span><span>${AppState.records.length}</span></div><div class="status-row"><span>备忘</span><span>${memoCount}</span></div></section></div>`;
    document.getElementById('export-json').addEventListener('click',()=>{const blob=new Blob([JSON.stringify(exportPayload(),null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`shanghai-birding-backup-${AppUtils.todayISO()}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);AppToast.show('备份文件已生成');});
    document.getElementById('import-json').addEventListener('change',async e=>{const file=e.target.files?.[0];if(!file)return;const result=await importBackup(file);AppToast.show(result.ok?'数据恢复完成':result.error);if(result.ok)await render();e.target.value='';});
    document.getElementById('fetch-ebird')?.addEventListener('click',async()=>{const key=await window.EBirdData.getApiKey();const button=document.getElementById('fetch-ebird');if(button){button.disabled=true;button.textContent='获取中…';}try{const result=await window.EBirdData.fetchRecent({force:true,apiKey:key});AppToast.show(result.success?`eBird 数据获取完成：${result.hotspotCount} 个观测点、${result.recordCount} 条鸟种记录`:result.error);if(result.success){await AppStateActions.load();await render();}}finally{if(button){button.disabled=false;button.textContent='获取最近7日数据';}}});
    document.getElementById('export-ebird')?.addEventListener('click',()=>window.EBirdData?.exportCurrent?.());
    document.getElementById('import-ebird')?.addEventListener('change',async e=>{const file=e.target.files?.[0];if(!file)return;const result=await window.EBirdData.importFile(file);AppToast.show(result.success?`eBird 数据导入完成：${result.hotspotCount} 个观测点、${result.recordCount} 条鸟种记录`:result.error);if(result.success){await AppStateActions.load();await render();}e.target.value='';});
    document.getElementById('clear-data').addEventListener('click',async()=>{const ok=await AppModal.confirmAction('清空全部数据','此操作将删除全部观鸟记录和全部备忘，且无法自动恢复。请先确认已经备份。');if(!ok)return;await Storage.clearAll();await AppStateActions.refreshPersonal();AppStateActions.notify();AppToast.show('个人数据已清空');await render();});
  }
  window.SettingsPage={render,validateBackup,exportPayload,importBackup};
})();
