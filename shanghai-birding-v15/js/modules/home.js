window.HomePage = {
  async render() {
    const records = AppUtils.sortRecords(AppState.records);
    const memos = AppState.memos || [];
    const total = AppStateActions.progressTotal();
    const discovered = AppStateActions.discoveredCount();
    const latest = records[0];
    const today = (AppState.externalData.weather?.forecast || [])[0];
    document.getElementById('app').innerHTML = `
      <div class="grid" style="gap:18px">
        <section class="card hero">
          <div class="page-kicker">天气与观鸟简报</div>
          <div class="weather-summary" style="margin:10px 0 14px">
            <span class="weather-icon">${today?.icon || '—'}</span>
            <div><strong style="font-size:20px">${today ? AppUtils.escapeHtml(today.weather) : '暂无天气数据'}</strong><div class="muted">${today ? `${today.tempMin}–${today.tempMax}°C · ${today.windDirection}风 ${today.windLevel}级` : '请运行数据更新脚本'}</div></div>
          </div>
          <div class="advice">${AppUtils.escapeHtml(AppUtils.generateBirdingAdvice(today))}</div>
        </section>
        <section class="card">
          <div class="card-header"><div><strong>备忘录</strong><div class="muted" style="font-size:12px;margin-top:3px">每条备忘失去焦点即自动保存</div></div><button class="button primary" id="add-memo">＋ 添加备忘</button></div>
          <div class="card-body"><div id="memo-list" class="memo-list">${memos.length ? memos.map((memo,i)=>`<article class="memo-item" data-memo="${AppUtils.escapeHtml(memo.id)}"><div class="memo-item-header"><span class="muted">备忘 ${i+1} · ${AppUtils.escapeHtml(AppUtils.formatDate(memo.createdAt.slice(0,10)))}</span><button class="button small" type="button" data-delete-memo="${AppUtils.escapeHtml(memo.id)}">删除</button></div><textarea class="textarea memo" data-memo-input="${AppUtils.escapeHtml(memo.id)}" placeholder="记录一个想法、待去的地点或看到的鸟……">${AppUtils.escapeHtml(memo.text)}</textarea></article>`).join('') : '<div class="empty" id="memo-empty">还没有备忘，先添加一条。</div>'}</div></div>
        </section>
        <section class="grid grid-2">
          <div class="card"><div class="card-header"><strong>图鉴进度</strong><span>${discovered} / ${total} 种</span></div><div class="card-body"><div class="progress-meta"><span class="muted">已点亮</span><strong>${total ? Math.round(discovered/total*100) : 0}%</strong></div><div class="progress-track"><div class="progress-bar" style="width:${total ? Math.min(100, discovered/total*100) : 0}%"></div></div></div></div>
          <div class="card"><div class="card-header"><strong>最近一条记录</strong><a class="button small" href="#/records">查看全部</a></div><div class="card-body">${latest ? `<div class="record-title">${AppUtils.recordSpecies(latest).map(s=>`${AppUtils.escapeHtml(s.speciesName)} × ${s.count}`).join('、')}</div><div class="record-sub">${AppUtils.escapeHtml(latest.date)} · ${AppUtils.escapeHtml(latest.location)}</div><div style="margin-top:10px">${AppUtils.escapeHtml(latest.note || '暂无备注')}</div>` : '<div class="empty">还没有观鸟记录。</div>'}</div></div>
        </section>
      </div>`;

    const saveTimers = new Map();
    document.querySelectorAll('[data-memo-input]').forEach(textarea => {
      const id = textarea.dataset.memoInput;
      const save = AppUtils.debounce(async () => {
        const memo = (AppState.memos || []).find(x => x.id === id);
        if (!memo) return;
        memo.text = textarea.value;
        await Storage.updateMemo(memo);
      }, 350);
      saveTimers.set(id, save);
      textarea.addEventListener('input', save);
      textarea.addEventListener('blur', async () => { save.cancel(); const memo=(AppState.memos||[]).find(x=>x.id===id); if(!memo)return; memo.text=textarea.value; await Storage.updateMemo(memo); });
    });

    document.querySelectorAll('[data-delete-memo]').forEach(button => button.addEventListener('click', async () => {
      const id=button.dataset.deleteMemo;
      const memo=(AppState.memos||[]).find(x=>x.id===id); if(!memo)return;
      const ok=await AppModal.confirmAction('删除备忘', '确定删除这条备忘吗？');
      if(!ok)return;
      saveTimers.get(id)?.cancel();
      await Storage.deleteMemo(id);
      await AppStateActions.refreshPersonal();
      await window.HomePage.render();
    }));

    document.getElementById('add-memo').addEventListener('click', async () => {
      const result=await AppModal.showFormModal('添加备忘', '<form id="memo-form"><label class="label">内容</label><textarea class="textarea" name="text" placeholder="记录一个想法、待去的地点或看到的鸟……" required></textarea></form>', modal => {
        modal.querySelector('textarea').focus();
      });
      if(!result?.values) return;
      const text=String(result.values.text||'').trim();
      if(!text){AppToast.show('备忘内容不能为空。');return;}
      await Storage.addMemo(text);
      await AppStateActions.refreshPersonal();
      await window.HomePage.render();
    });
  }
};
