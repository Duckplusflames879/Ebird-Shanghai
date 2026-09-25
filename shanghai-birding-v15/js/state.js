(function () {
  const S = {
    records: [], memos: [], memo: '', externalData: { weather:null, hotspots:[], updatedAt:null, sourceStatus:'unknown' }, ready:false
  };
  async function load() {
    S.records = await Storage.getRecords();
    S.memos = await Storage.getMemos();
    S.memo = S.memos[0]?.text || '';
    const data = window.EXTERNAL_DATA || null;
    S.externalData = data ? { ...data, sourceStatus: data.sourceStatus || 'ok' } : { weather:null, hotspots:[], updatedAt:null, sourceStatus:'missing' };
    S.ready = true;
    return S;
  }
  async function refreshPersonal() {
    S.records = await Storage.getRecords();
    S.memos = await Storage.getMemos();
    S.memo = S.memos[0]?.text || '';
  }
  function discoveredCount() { return window.AppUtils.calculateDiscoveredIds(S.records).size; }
  function progressTotal() { return Array.isArray(window.BIRD_LEXICON) ? window.BIRD_LEXICON.length : 0; }
  function notify() { document.dispatchEvent(new CustomEvent('appstatechange')); }
  window.AppState = S;
  window.AppStateActions = { load, refreshPersonal, discoveredCount, progressTotal, notify };
})();
