(function () {
  function hotspotOptions(existing) {
    const hotspots = AppState.externalData.hotspots || [];
    const options = hotspots.map(h => `<option value="${AppUtils.escapeHtml(h.id)}" data-location="${AppUtils.escapeHtml(h.name)}" ${existing?.hotspotId===h.id?'selected':''}>${AppUtils.escapeHtml(h.name)} · ${AppUtils.escapeHtml(h.district)}</option>`).join('');
    const legacy = existing && existing.location && !hotspots.some(h => h.id === existing.hotspotId)
      ? `<option value="legacy:${AppUtils.escapeHtml(existing.location)}" selected>历史地点：${AppUtils.escapeHtml(existing.location)}</option>` : '';
    return `<select class="select" name="hotspotId" id="hotspot-select" required><option value="">请选择观鸟点</option>${options}${legacy}</select>`;
  }
  function speciesRow(entry={}, removable=true) {
    const bird = BIRD_LEXICON.find(b => b.id === entry.speciesId);
    return `<div class="species-row" data-species-row>
      <div class="autocomplete"><input class="input species-input" value="${AppUtils.escapeHtml(bird?.name || entry.speciesName || '')}" placeholder="输入鸟名" autocomplete="off"><input type="hidden" class="species-id" value="${AppUtils.escapeHtml(entry.speciesId || '')}"></div>
      <input class="input species-count" type="number" min="1" step="1" value="${Number(entry.count) > 0 ? Number(entry.count) : 1}" aria-label="观察次数">
      ${removable ? '<button class="button small" type="button" data-remove-species>删除</button>' : '<span class="species-remove-spacer"></span>'}
    </div>`;
  }
  function recordForm(existing) {
    const species = AppUtils.recordSpecies(existing);
    const initial = species.length ? species : [{speciesId:'', speciesName:'', count:1}];
    return `<form id="record-form"><div class="form-grid">
      <div class="form-field"><label class="label">日期</label><input class="input" name="date" type="date" value="${AppUtils.escapeHtml(existing?.date || AppUtils.todayISO())}" required></div>
      <div class="form-field"><label class="label">观鸟点</label>${hotspotOptions(existing)}</div>
      <div class="form-field full"><label class="label">鸟种与观察次数</label><div id="species-list">${initial.map((s,i)=>speciesRow(s,i>0)).join('')}</div><input type="hidden" name="speciesPayload" id="species-payload"><button class="button small" type="button" id="add-species">＋ 添加鸟种</button><div class="muted" style="margin-top:7px">可分别填写观察到的次数，同一次观鸟记录可以添加多个鸟种。</div></div>
      <div class="form-field full"><label class="label">备注</label><textarea class="textarea" style="min-height:90px" name="note" placeholder="可选">${AppUtils.escapeHtml(existing?.note || '')}</textarea></div>
    </div></form>`;
  }
  function collectSpecies(modal) {
    return [...modal.querySelectorAll('[data-species-row]')].map(row => ({
      speciesId: row.querySelector('.species-id').value,
      speciesName: row.querySelector('.species-input').value.trim(),
      count: Number(row.querySelector('.species-count').value)
    }));
  }
  function syncPayload(modal) {
    const input = modal.querySelector('#species-payload');
    if (input) input.value = JSON.stringify(collectSpecies(modal));
  }
  function attachSpeciesRow(row, modal) {
    const input=row.querySelector('.species-input');
    const id=row.querySelector('.species-id');
    Autocomplete.attach(input, keyword => keyword.trim() ? BIRD_LEXICON.filter(b => b.name.includes(keyword.trim())) : [], bird => {
      input.value=bird.name; id.value=bird.id; input.dataset.selected='true'; syncPayload(modal);
    });
    input.addEventListener('input', () => { if (!BIRD_LEXICON.some(b=>b.id===id.value && b.name===input.value)) id.value=''; syncPayload(modal); });
    row.querySelector('.species-count').addEventListener('input', () => syncPayload(modal));
    const remove=row.querySelector('[data-remove-species]');
    if (remove) remove.addEventListener('click', () => { row.remove(); syncPayload(modal); });
  }
  async function editRecord(existing) {
    return AppModal.showFormModal(existing ? '编辑观鸟记录' : '新增观鸟记录', recordForm(existing), modal => {
      modal.querySelectorAll('[data-species-row]').forEach(row => attachSpeciesRow(row, modal));
      modal.querySelector('#add-species').addEventListener('click', () => {
        const list=modal.querySelector('#species-list'); const wrapper=document.createElement('div'); wrapper.innerHTML=speciesRow({}, true); const row=wrapper.firstElementChild; list.appendChild(row); attachSpeciesRow(row, modal); syncPayload(modal);
      });
      modal.querySelector('#hotspot-select').addEventListener('change', e => {
        const option=e.target.selectedOptions[0]; e.target.dataset.location=option?.dataset.location || '';
      });
      syncPayload(modal);
    }, async values => {
      const save = await saveRecord(values, existing);
      if (!save.ok) {
        AppToast.show(save.error);
        return false;
      }
      return { values, saved: true };
    });
  }
  async function saveRecord(values, existing) {
    const hotspot = (AppState.externalData.hotspots || []).find(h => h.id === values.hotspotId);
    const species = (() => { try { return JSON.parse(values.speciesPayload || '[]'); } catch { return []; } })();
    const seenIds=new Set();
    const normalizedSpecies = species.map(s => {
      const bird=BIRD_LEXICON.find(b => b.id===s.speciesId && b.name===s.speciesName);
      const count=Number(s.count);
      return bird && Number.isInteger(count) && count > 0 ? {speciesId:bird.id,speciesName:bird.name,count} : null;
    });
    if (!values.date) return {ok:false,error:'日期不能为空。'};
    if (!hotspot) return {ok:false,error:'请选择列表中的观鸟点。'};
    if (!species.length || normalizedSpecies.some(s=>!s) || normalizedSpecies.length !== species.length) return {ok:false,error:'请为每个鸟种选择输入联想中的有效鸟种，并填写正整数观察次数。'};
    for (const s of normalizedSpecies) { if (seenIds.has(s.speciesId)) return {ok:false,error:'同一条记录中不能重复添加同一种鸟。'}; seenIds.add(s.speciesId); }
    const now = new Date().toISOString();
    const location = hotspot.name;
    const first = normalizedSpecies[0];
    const record = AppUtils.normalizeRecord({
      id: existing?.id || AppUtils.uid('record'), date:values.date, hotspotId:hotspot.id, location,
      species:normalizedSpecies, speciesId:first.speciesId, speciesName:first.speciesName, count:first.count,
      note:values.note || '', createdAt:existing?.createdAt || now, updatedAt:now
    });
    if (existing) await Storage.updateRecord(record); else await Storage.addRecord(record);
    await AppStateActions.refreshPersonal(); AppStateActions.notify();
    return { ok:true };
  }
  function renderSpecies(record) {
    return AppUtils.recordSpecies(record).map(s=>`${AppUtils.escapeHtml(s.speciesName)} × ${s.count}`).join('、');
  }
  async function render() {
    const records = AppUtils.sortRecords(AppState.records);
    document.getElementById('app').innerHTML = `<section class="card"><div class="card-header"><div><strong>我的观鸟记录</strong><div class="muted">共 ${records.length} 条</div></div><button class="button primary" id="add-record">＋ 新增记录</button></div><div>${records.length ? records.map(r=>`<article class="record-item"><div class="record-main"><div><div class="record-title">${renderSpecies(r)}</div><div class="record-sub">${AppUtils.escapeHtml(r.date)} · ${AppUtils.escapeHtml(r.location)}</div>${r.note ? `<div style="margin-top:8px">${AppUtils.escapeHtml(r.note)}</div>` : ''}</div><div class="record-actions"><button class="button small" data-edit="${r.id}">编辑</button><button class="button small" data-delete="${r.id}">删除</button></div></div></article>`).join('') : '<div class="empty">还没有记录，先添加一条观鸟记录。</div>'}</div></section>`;
    document.getElementById('add-record').addEventListener('click', async () => {
      const result = await editRecord(null);
      if (result?.saved) { AppToast.show('记录已保存'); await render(); }
    });
    document.querySelectorAll('[data-edit]').forEach(btn => btn.addEventListener('click', async () => {
      const existing = AppState.records.find(r=>r.id===btn.dataset.edit); if (!existing) return;
      const result = await editRecord(existing);
      if (result?.saved) { AppToast.show('记录已更新'); await render(); }
    }));
    document.querySelectorAll('[data-delete]').forEach(btn => btn.addEventListener('click', async () => {
      const existing=AppState.records.find(r=>r.id===btn.dataset.delete); if (!existing) return;
      const ok=await AppModal.confirmAction('删除记录',`确定删除 ${renderSpecies(existing)}（${existing.date}）吗？`); if(!ok)return;
      await Storage.deleteRecord(existing.id); await AppStateActions.refreshPersonal(); AppStateActions.notify(); AppToast.show('记录已删除'); await render();
    }));
  }
  window.RecordsPage = { render, saveRecord, recordForm };
})();
