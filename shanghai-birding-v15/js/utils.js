(function () {
  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'"]/g, ch => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;' }[ch]));
  }
  function formatDate(date) {
    if (!date) return '—';
    const d = new Date(`${date}T00:00:00`);
    return new Intl.DateTimeFormat('zh-CN', { year:'numeric', month:'2-digit', day:'2-digit' }).format(d);
  }
  function debounce(fn, delay) {
    let timer = null;
    const debounced = (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => { timer = null; fn(...args); }, delay);
    };
    debounced.cancel = () => { clearTimeout(timer); timer = null; };
    return debounced;
  }
  function uid(prefix) {
    const now = Date.now().toString(36);
    const rand = Math.random().toString(36).slice(2, 9);
    return `${prefix}_${now}_${rand}`;
  }
  function todayISO() {
    const d = new Date();
    const pad = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
  }
  function normalizeSpeciesEntry(raw) {
    return {
      speciesId: String(raw?.speciesId ?? ''),
      speciesName: String(raw?.speciesName ?? '').trim(),
      count: Number(raw?.count)
    };
  }
  function normalizeRecord(raw) {
    const legacySpecies = raw?.speciesId ? [
      { speciesId: raw.speciesId, speciesName: raw.speciesName, count: raw.count }
    ] : [];
    const species = Array.isArray(raw?.species) && raw.species.length
      ? raw.species.map(normalizeSpeciesEntry)
      : legacySpecies.map(normalizeSpeciesEntry);
    if (species.length === 1 && raw?.count !== undefined && Number.isFinite(Number(raw.count)) && Number(raw.count) > 0) {
      // Backward compatibility for records written by the previous single-species schema.
      species[0].count = Number(raw.count);
    }
    const first = species[0] || { speciesId:'', speciesName:'', count:0 };
    return {
      id: String(raw?.id ?? uid('record')),
      date: String(raw?.date ?? ''),
      hotspotId: String(raw?.hotspotId ?? ''),
      location: String(raw?.location ?? '').trim(),
      species,
      // Legacy compatibility fields. The first species is the representative one.
      speciesId: first.speciesId,
      speciesName: first.speciesName,
      count: Number(first.count),
      note: String(raw?.note ?? ''),
      createdAt: raw?.createdAt ? String(raw.createdAt) : new Date().toISOString(),
      updatedAt: raw?.updatedAt ? String(raw.updatedAt) : new Date().toISOString()
    };
  }
  function recordSpecies(record) {
    const normalized = normalizeRecord(record);
    return normalized.species;
  }
  function sortRecords(records) {
    return [...records].sort((a,b) => {
      const byDate = String(b.date).localeCompare(String(a.date));
      if (byDate) return byDate;
      return String(b.updatedAt || '').localeCompare(String(a.updatedAt || ''));
    });
  }
  function calculateFirstSeen(records, speciesId) {
    const matchingDates = records.flatMap(r => {
      return recordSpecies(r).some(s => s.speciesId === speciesId) ? [r.date] : [];
    });
    return matchingDates.sort()[0] || null;
  }
  function calculateDiscoveredIds(records) {
    return new Set(records.flatMap(recordSpecies).map(s => s.speciesId).filter(Boolean));
  }
  function generateBirdingAdvice(day) {
    if (!day) return '暂无天气数据，请先运行本地数据更新脚本。';
    if (day.weatherType === 'rain') return '降雨明显，建议减少远距离出行，或选择有遮蔽的观鸟点。';
    if (Number(day.windLevel) >= 5) return '风力较大，建议选择林地或有遮蔽物的观鸟点。';
    if (Number(day.tempMax) >= 34) return '高温时段不利于舒适观鸟，建议优先安排清晨或傍晚。';
    return '天气条件适中，建议优先安排清晨时段，并结合潮汐或水位观察湿地鸟类。';
  }
  function safeJsonParse(text) {
    try { return { ok: true, value: JSON.parse(text) }; }
    catch (error) { return { ok: false, error }; }
  }
  window.AppUtils = { escapeHtml, formatDate, debounce, uid, todayISO, normalizeSpeciesEntry, normalizeRecord, recordSpecies, sortRecords, calculateFirstSeen, calculateDiscoveredIds, generateBirdingAdvice, safeJsonParse };
})();
