(function () {
  const C = window.AppConstants;
  let dbPromise = null;
  let fallbackMode = false;
  const memory = { records: [], app: {} };

  function canUseLocalStorage() {
    try { const k='__birding_test__'; localStorage.setItem(k,'1'); localStorage.removeItem(k); return true; } catch { return false; }
  }
  const localStore = canUseLocalStorage();
  function fallbackRead() {
    if (!localStore) return null;
    try { return JSON.parse(localStorage.getItem('shanghai-birding-fallback') || 'null'); } catch { return null; }
  }
  function fallbackWrite() {
    if (!localStore) return;
    try { localStorage.setItem('shanghai-birding-fallback', JSON.stringify(memory)); } catch { /* memory remains source of truth */ }
  }
  if (localStore) Object.assign(memory, fallbackRead() || {});

  function openDb() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise((resolve, reject) => {
      if (!('indexedDB' in window)) return reject(new Error('IndexedDB unavailable'));
      let req;
      try { req = indexedDB.open(C.DB_NAME, C.DB_VERSION); } catch (error) { reject(error); return; }
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(C.STORES.RECORDS)) db.createObjectStore(C.STORES.RECORDS, { keyPath: 'id' });
        if (!db.objectStoreNames.contains(C.STORES.APP)) db.createObjectStore(C.STORES.APP, { keyPath: 'key' });
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error || new Error('IndexedDB open failed'));
    });
    dbPromise.catch(() => { fallbackMode = true; });
    return dbPromise;
  }
  function request(storeName, mode, operation) {
    if (fallbackMode) return Promise.resolve().then(() => {
      const isRecords = storeName === C.STORES.RECORDS;
      const fakeStore = {
        getAll: () => ({ result: isRecords ? [...memory.records] : Object.entries(memory.app).map(([key,value]) => ({key,value})) }),
        get: key => ({ result: isRecords ? memory.records.find(x => x.id === key) : (key in memory.app ? {key, value:memory.app[key]} : undefined) }),
        add: value => { if (isRecords) memory.records.push(value); else memory.app[value.key]=value.value; fallbackWrite(); return {result:value}; },
        put: value => { if (isRecords) { const i=memory.records.findIndex(x=>x.id===value.id); if(i>=0) memory.records[i]=value; else memory.records.push(value); } else memory.app[value.key]=value.value; fallbackWrite(); return {result:value}; },
        delete: id => { if (isRecords) memory.records=memory.records.filter(x=>x.id!==id); else delete memory.app[id]; fallbackWrite(); return {result:undefined}; },
        clear: () => { if (isRecords) memory.records=[]; else memory.app={}; fallbackWrite(); return {result:undefined}; }
      };
      return operation(fakeStore).result;
    });
    return openDb().then(db => new Promise((resolve, reject) => {
      const tx = db.transaction(storeName, mode);
      const store = tx.objectStore(storeName);
      let requestObj;
      try { requestObj = operation(store); } catch (e) { reject(e); return; }
      requestObj.onsuccess = () => resolve(requestObj.result);
      requestObj.onerror = () => reject(requestObj.error || new Error('IndexedDB request failed'));
    })).catch(error => {
      fallbackMode = true;
      return request(storeName, mode, operation);
    });
  }
  async function migrateMemosIfNeeded() {
    const existing = await request(C.STORES.APP, 'readonly', store => store.get('memos'));
    if (existing?.value && Array.isArray(existing.value)) return existing.value;
    const legacy = await request(C.STORES.APP, 'readonly', store => store.get('quickMemo'));
    const value = String(legacy?.value || '');
    const memos = value ? [{ id:AppUtils.uid('memo'), text:value, createdAt:new Date().toISOString(), updatedAt:new Date().toISOString() }] : [];
    if (memos.length) await request(C.STORES.APP, 'readwrite', store => store.put({key:'memos', value:memos}));
    return memos;
  }
  const Storage = {
    async getRecords() {
      const rows = await request(C.STORES.RECORDS, 'readonly', store => store.getAll());
      return rows.map(AppUtils.normalizeRecord);
    },
    async addRecord(record) {
      const normalized = AppUtils.normalizeRecord(record);
      if (fallbackMode) { memory.records.push(normalized); fallbackWrite(); return normalized; }
      return request(C.STORES.RECORDS, 'readwrite', store => store.add(normalized));
    },
    async updateRecord(record) {
      const normalized = AppUtils.normalizeRecord(record);
      if (fallbackMode) { const i=memory.records.findIndex(x=>x.id===normalized.id); if(i<0) throw new Error('Record not found'); memory.records[i]=normalized; fallbackWrite(); return normalized; }
      return request(C.STORES.RECORDS, 'readwrite', store => store.put(normalized));
    },
    async deleteRecord(id) {
      if (fallbackMode) { memory.records=memory.records.filter(x=>x.id!==id); fallbackWrite(); return; }
      return request(C.STORES.RECORDS, 'readwrite', store => store.delete(id));
    },
    async getMemos() {
      const memos = await migrateMemosIfNeeded();
      return Array.isArray(memos) ? memos.map(m => ({...m, id:String(m.id), text:String(m.text ?? ''), createdAt:String(m.createdAt ?? ''), updatedAt:String(m.updatedAt ?? '')})) : [];
    },
    async addMemo(text) {
      const now = new Date().toISOString();
      const memo = { id:AppUtils.uid('memo'), text:String(text ?? ''), createdAt:now, updatedAt:now };
      const memos = await this.getMemos(); memos.push(memo);
      await request(C.STORES.APP, 'readwrite', store => store.put({key:'memos', value:memos}));
      return memo;
    },
    async updateMemo(memo) {
      const memos = await this.getMemos();
      const index = memos.findIndex(x => x.id === memo.id);
      if (index < 0) throw new Error('Memo not found');
      memos[index] = {...memos[index], text:String(memo.text ?? ''), updatedAt:new Date().toISOString()};
      await request(C.STORES.APP, 'readwrite', store => store.put({key:'memos', value:memos}));
      return memos[index];
    },
    async deleteMemo(id) {
      const memos = await this.getMemos();
      await request(C.STORES.APP, 'readwrite', store => store.put({key:'memos', value:memos.filter(x => x.id !== id)}));
    },
    async getMemo() {
      const memos = await this.getMemos();
      return memos[0]?.text || '';
    },
    async saveMemo(value) {
      const memos = await this.getMemos();
      if (!String(value ?? '')) {
        if (memos.length) await this.deleteMemo(memos[0].id);
        return;
      }
      if (memos.length) { memos[0] = {...memos[0], text:String(value), updatedAt:new Date().toISOString()}; }
      else { const now=new Date().toISOString(); memos.push({id:AppUtils.uid('memo'),text:String(value),createdAt:now,updatedAt:now}); }
      await request(C.STORES.APP, 'readwrite', store => store.put({key:'memos', value:memos}));
    },
    async getAppValue(key) {
      if (fallbackMode) return memory.app[key] ?? null;
      const row = await request(C.STORES.APP, 'readonly', store => store.get(key)); return row ? row.value : null;
    },
    async setAppValue(key, value) {
      if (fallbackMode) { memory.app[key]=value; fallbackWrite(); return; }
      return request(C.STORES.APP, 'readwrite', store => store.put({ key, value }));
    },
    async clearAll() {
      if (fallbackMode) { memory.records=[]; memory.app={}; fallbackWrite(); return; }
      return openDb().then(db => new Promise((resolve, reject) => {
        const tx = db.transaction([C.STORES.RECORDS, C.STORES.APP], 'readwrite');
        tx.objectStore(C.STORES.RECORDS).clear(); tx.objectStore(C.STORES.APP).clear();
        tx.oncomplete = resolve; tx.onerror=()=>reject(tx.error || new Error('Clear failed')); tx.onabort=()=>reject(tx.error || new Error('Clear aborted'));
      })).catch(() => { fallbackMode=true; memory.records=[]; memory.app={}; fallbackWrite(); });
    }
  };
  window.Storage = Storage;
  window.openBirdingDb = openDb;
})();
