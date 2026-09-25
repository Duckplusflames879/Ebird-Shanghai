window.LexiconPage = {
  filter: 'all',
  keyword: '',

  getList(discovered) {
    let list = BIRD_LEXICON.filter(b => {
      if (this.filter === 'discovered') return discovered.has(b.id);
      if (this.filter === 'undiscovered') return !discovered.has(b.id);
      return true;
    });
    const keyword = this.keyword.trim();
    if (keyword) list = list.filter(b => `${b.name} ${b.family} ${b.genus}`.includes(keyword));
    return [...list].sort((a, b) => a.name.localeCompare(b.name, 'zh'));
  },

  showDetail(birdId, discovered) {
    const bird = BIRD_LEXICON.find(b => b.id === birdId);
    if (!bird) return;
    const first = AppUtils.calculateFirstSeen(AppState.records, bird.id);
    const data = BirdProfiles.getLocal(bird);
    const root = document.getElementById('modal-root');
    const discoveredState = discovered.has(bird.id);
    root.innerHTML = `<div class="modal-backdrop"><div class="modal bird-detail-modal" role="dialog" aria-modal="true" aria-labelledby="bird-detail-title">
      <div class="modal-header"><div><strong id="bird-detail-title">${AppUtils.escapeHtml(bird.name)}</strong></div><button class="button small" data-close>关闭</button></div>
      <div class="modal-body bird-detail-body">
        <div class="detail-status ${discoveredState ? 'detail-status-on' : 'detail-status-off'}">${discoveredState ? `✓ 已点亮${first ? ` · 首次发现 ${AppUtils.escapeHtml(first)}` : ''}` : '○ 尚未点亮 · 个人记录中尚未发现'}</div>
        <div class="detail-grid">
          <div class="detail-stat"><span>分类</span><strong>${AppUtils.escapeHtml(bird.family)}</strong></div>
          <div class="detail-stat"><span>属</span><strong>${AppUtils.escapeHtml(data.genus)}</strong></div>
        </div>
        <section class="bird-detail-section"><h3>外观与识别</h3><p>${AppUtils.escapeHtml(data.appearance)}</p></section>
        <section class="bird-detail-section"><h3>习性</h3><p>${AppUtils.escapeHtml(data.behavior)}</p></section>
        <section class="bird-detail-section"><h3>栖息地</h3><p>${AppUtils.escapeHtml(data.habitat)}</p></section>
        <section class="bird-detail-section"><h3>食性</h3><p>${AppUtils.escapeHtml(data.diet)}</p></section>
        <section class="bird-detail-section"><h3>迁徙与上海出现</h3><p>${AppUtils.escapeHtml(data.migration)}</p></section>
        ${discoveredState && first ? `<div style="margin-top:14px"><a class="button small" data-first-seen href="#/records">查看首次发现记录</a></div>` : ''}
      </div></div></div>`;
    root.querySelector('[data-close]').addEventListener('click', () => { root.innerHTML=''; });
    const firstSeenLink = root.querySelector('[data-first-seen]');
    if (firstSeenLink) firstSeenLink.addEventListener('click', () => { root.innerHTML=''; });
  },

  renderResults(discovered) {
    const container = document.getElementById('lexicon-results');
    if (!container) return;
    const list = this.getList(discovered);
    container.innerHTML = list.length ? list.map(b => {
      const on = discovered.has(b.id);
      const first = AppUtils.calculateFirstSeen(AppState.records, b.id);
      const taxonomy = b.genus && b.genus !== '—' ? `${AppUtils.escapeHtml(b.family)} · ${AppUtils.escapeHtml(b.genus)}` : AppUtils.escapeHtml(b.family);
      return `<article class="lexicon-item ${on ? 'discovered' : 'undiscovered'}" data-bird="${AppUtils.escapeHtml(b.id)}" tabindex="0" role="button" aria-label="查看${AppUtils.escapeHtml(b.name)}详情">
        <div class="lexicon-title"><strong>${on ? '✓ ' : '○ '}${AppUtils.escapeHtml(b.name)}</strong><span class="badge ${on ? 'on' : ''}">${on ? '已点亮' : '未点亮'}</span></div>
        <div class="muted" style="margin-top:8px">${taxonomy}</div>
        <div style="margin-top:10px;font-size:13px">${on ? `首次发现：<strong>${AppUtils.escapeHtml(first)}</strong>` : '尚未在个人记录中发现'}</div>
      </article>`;
    }).join('') : '<div class="empty" style="grid-column:1/-1">没有匹配的鸟种。</div>';

    document.querySelectorAll('#lexicon-results [data-bird]').forEach(card => {
      const open = () => this.showDetail(card.dataset.bird, discovered);
      card.addEventListener('click', open);
      card.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); } });
    });
  },

  async render() {
    const discovered = AppUtils.calculateDiscoveredIds(AppState.records);
    const total = BIRD_LEXICON.length;
    document.getElementById('app').innerHTML = `
      <section class="card">
        <div class="card-header"><div><strong>上海鸟类图鉴</strong><div class="muted">${discovered.size} / ${total} 已点亮</div></div></div>
        <div class="card-body"><div class="grid" style="grid-template-columns:1fr auto;align-items:start">
          <input id="lexicon-search" class="input" placeholder="搜索鸟种、科、属" value="${AppUtils.escapeHtml(this.keyword)}" autocomplete="off" lang="zh-CN" aria-label="图鉴搜索">
          <div class="tabs">${[['all','全部'],['discovered','已点亮'],['undiscovered','未点亮']].map(([k,v]) => `<button class="tab ${this.filter === k ? 'active' : ''}" data-filter="${k}">${v}</button>`).join('')}</div>
        </div><div id="lexicon-results" class="grid grid-3" style="margin-top:18px"></div></div>
      </section>`;
    this.renderResults(discovered);
    const search = document.getElementById('lexicon-search');
    let composing = false; let timer = null;
    const updateResults = () => { this.keyword = search.value; this.renderResults(AppUtils.calculateDiscoveredIds(AppState.records)); };
    const schedule = () => { if (composing) return; clearTimeout(timer); timer = window.setTimeout(updateResults, 100); };
    search.addEventListener('compositionstart', () => { composing = true; });
    search.addEventListener('compositionend', () => { composing = false; clearTimeout(timer); updateResults(); });
    search.addEventListener('input', schedule);
    document.querySelectorAll('[data-filter]').forEach(btn => btn.addEventListener('click', async () => { this.filter = btn.dataset.filter; await this.render(); }));
  }
};
