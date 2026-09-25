(function () {
  const LEAFLET_VERSION = '1.9.4';
  // Prefer local vendor copy (fast on GitHub Pages / China); CDN is fallback only.
  const LEAFLET_LOCAL_JS = 'vendor/leaflet/leaflet.js';
  const LEAFLET_LOCAL_CSS = 'vendor/leaflet/leaflet.css';
  const LEAFLET_CDN_JS = [
    `https://cdn.bootcdn.net/ajax/libs/leaflet/${LEAFLET_VERSION}/leaflet.js`,
    `https://unpkg.com/leaflet@${LEAFLET_VERSION}/dist/leaflet.js`
  ];
  const LEAFLET_CDN_CSS = [
    `https://cdn.bootcdn.net/ajax/libs/leaflet/${LEAFLET_VERSION}/leaflet.css`,
    `https://unpkg.com/leaflet@${LEAFLET_VERSION}/dist/leaflet.css`
  ];
  // Gaode tiles are GCJ-02; eBird coordinates are WGS-84 — convert markers when using Gaode.
  const GAODE_TILE_URL = 'https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}';
  const OSM_TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
  const SOURCE = 'eBird';
  const SOURCE_LABEL = 'eBird, Cornell Lab of Ornithology';
  const SOURCE_URL = window.EBirdData?.SOURCE_URL || 'https://ebird.org/region/CN-31';
  const IMPORT_FORMAT = window.EBirdData?.IMPORT_FORMAT || 'shanghai-birding-ebird-7d';
  const KNOWN_HOTSPOTS = [
    {id:'dongtan',name:'崇明东滩',district:'崇明区',lat:31.52,lon:121.99},
    {id:'nanhui',name:'南汇东滩',district:'浦东新区',lat:30.90,lon:121.95},
    {id:'binjiang',name:'滨江森林公园',district:'浦东新区',lat:31.48,lon:121.58},
    {id:'gongqing',name:'共青森林公园',district:'杨浦区',lat:31.35,lon:121.55},
    {id:'wusong',name:'吴淞炮台湾湿地森林公园',district:'宝山区',lat:31.38,lon:121.49},
    {id:'xisha',name:'西沙明珠湖景区',district:'崇明区',lat:31.62,lon:121.27},
    {id:'dongping',name:'东平国家森林公园',district:'崇明区',lat:31.66,lon:121.40},
    {id:'shanghai_bay',name:'上海海湾国家森林公园',district:'奉贤区',lat:30.86,lon:121.46},
    {id:'century_park',name:'世纪公园',district:'浦东新区',lat:31.22,lon:121.55},
    {id:'botanical_garden',name:'上海植物园',district:'徐汇区',lat:31.14,lon:121.45}
  ];
  const PLACE_ALIASES = new Map([
    ['滨江森林公园','binjiang'],['滨江森林公园,上海','binjiang'],['滨江森林公园,上海市','binjiang'],
    ['崇明东滩','dongtan'],['东滩','dongtan'],['南汇东滩','nanhui'],['共青森林公园','gongqing'],
    ['吴淞炮台湾湿地森林公园','wusong'],['西沙明珠湖景区','xisha'],['东平国家森林公园','dongping'],
    ['上海海湾国家森林公园','shanghai_bay'],['世纪公园','century_park'],['上海植物园','botanical_garden']
  ]);
  const PLACE_BY_ID = Object.fromEntries(KNOWN_HOTSPOTS.map(h => [h.id, h]));
  let leafletPromise = null;

  function hasChinese(value) {
    return /[\u3400-\u4dbf\u4e00-\u9fff]/.test(String(value || ''));
  }

  function normalizePlaceKey(value) {
    return String(value || '').trim().replace(/\s+/g, ' ').replace(/[，]/g, ',').replace(/(^,|,$)/g, '').toLowerCase();
  }

  function haversineKm(lat1, lon1, lat2, lon2) {
    const toRad = Math.PI / 180;
    const dLat = (lat2 - lat1) * toRad;
    const dLon = (lon2 - lon1) * toRad;
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * toRad) * Math.cos(lat2 * toRad) * Math.sin(dLon / 2) ** 2;
    return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  function knownFromPlaceName(value) {
    const key = normalizePlaceKey(value);
    const direct = PLACE_ALIASES.get(key);
    if (direct) return PLACE_BY_ID[direct];
    for (const [alias, id] of PLACE_ALIASES.entries()) {
      if (alias.length >= 4 && key.includes(alias)) return PLACE_BY_ID[id];
    }
    return null;
  }

  function isCityLevelPlace(name) {
    const normalized = normalizePlaceKey(name).replace(/[,，]\s*(china|cn)$/i, '').replace(/\s+china$/i, '');
    const key = normalized.replace(/[\s,]+/g, '');
    return ['shanghai','shanghaicity','上海','上海市'].includes(key);
  }

  function validObservedAt(value) {
    const text = String(value || '').trim();
    if (!text) return false;
    return /\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?$/.test(text);
  }

  function observationWindow() {
    return window.EBirdData?.observationWindow ? window.EBirdData.observationWindow(new Date()) : {start:'', end:''};
  }

  function formatSourceLabel(source) {
    const value = String(source || SOURCE).trim();
    if (!value || value === 'eBird') return SOURCE_LABEL;
    return value;
  }

  function loadLeafletAsset(tagName, attrs) {
    return new Promise((resolve, reject) => {
      const el = document.createElement(tagName);
      Object.entries(attrs).forEach(([key, value]) => {
        if (key === 'dataset') Object.assign(el.dataset, value);
        else if (value != null) el[key] = value;
      });
      el.onload = () => resolve(el);
      el.onerror = () => reject(new Error(`Failed to load ${attrs.href || attrs.src}`));
      document.head.appendChild(el);
    });
  }

  async function ensureLeafletCss() {
    if (document.querySelector(`link[data-leaflet-css="${LEAFLET_VERSION}"]`)) return;
    const candidates = [LEAFLET_LOCAL_CSS, ...LEAFLET_CDN_CSS];
    let lastError = null;
    for (const href of candidates) {
      try {
        await new Promise((resolve, reject) => {
          const css = document.createElement('link');
          css.rel = 'stylesheet';
          css.href = href;
          css.dataset.leafletCss = LEAFLET_VERSION;
          let settled = false;
          let failed = false;
          const done = (ok, err) => {
            if (settled) return;
            settled = true;
            if (ok) resolve();
            else reject(err || new Error(`Failed to load ${href}`));
          };
          css.onload = () => done(true);
          css.onerror = () => { failed = true; done(false); };
          // Some browsers never fire link.onload for cached/local CSS.
          setTimeout(() => { if (!failed) done(true); }, 400);
          document.head.appendChild(css);
        });
        return;
      } catch (error) {
        lastError = error;
        document.querySelector(`link[data-leaflet-css="${LEAFLET_VERSION}"]`)?.remove();
      }
    }
    throw lastError || new Error('Leaflet CSS failed to load.');
  }

  async function ensureLeafletJs() {
    if (window.L && typeof window.L.map === 'function') return window.L;
    if (document.querySelector(`script[data-leaflet-js="${LEAFLET_VERSION}"]`) && window.L) return window.L;
    const candidates = [LEAFLET_LOCAL_JS, ...LEAFLET_CDN_JS];
    let lastError = null;
    for (const src of candidates) {
      try {
        await loadLeafletAsset('script', {
          src,
          async: true,
          dataset: { leafletJs: LEAFLET_VERSION }
        });
        if (window.L && typeof window.L.map === 'function') return window.L;
        lastError = new Error('Leaflet loaded but global L is unavailable.');
      } catch (error) {
        lastError = error;
        document.querySelector(`script[src="${src}"]`)?.remove();
      }
    }
    throw lastError || new Error('Leaflet CDN failed to load.');
  }

  function configureLeafletIcons(L) {
    if (!L?.Icon?.Default?.mergeOptions) return;
    const base = LEAFLET_LOCAL_CSS.replace(/leaflet\.css$/, 'images/');
    L.Icon.Default.mergeOptions({
      iconUrl: `${base}marker-icon.png`,
      iconRetinaUrl: `${base}marker-icon-2x.png`,
      shadowUrl: `${base}marker-shadow.png`
    });
  }

  // Rough WGS-84 → GCJ-02 for China map tiles (Gaode). Outside China returns input.
  function wgs84ToGcj02(lat, lon) {
    const a = 6378245.0;
    const ee = 0.00669342162296594323;
    function outOfChina(la, lo) {
      return lo < 72.004 || lo > 137.8347 || la < 0.8293 || la > 55.8271;
    }
    function transformLat(x, y) {
      let ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x));
      ret += (20.0 * Math.sin(6.0 * x * Math.PI) + 20.0 * Math.sin(2.0 * x * Math.PI)) * 2.0 / 3.0;
      ret += (20.0 * Math.sin(y * Math.PI) + 40.0 * Math.sin(y / 3.0 * Math.PI)) * 2.0 / 3.0;
      ret += (160.0 * Math.sin(y / 12.0 * Math.PI) + 320 * Math.sin(y * Math.PI / 30.0)) * 2.0 / 3.0;
      return ret;
    }
    function transformLon(x, y) {
      let ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x));
      ret += (20.0 * Math.sin(6.0 * x * Math.PI) + 20.0 * Math.sin(2.0 * x * Math.PI)) * 2.0 / 3.0;
      ret += (20.0 * Math.sin(x * Math.PI) + 40.0 * Math.sin(x / 3.0 * Math.PI)) * 2.0 / 3.0;
      ret += (150.0 * Math.sin(x / 12.0 * Math.PI) + 300.0 * Math.sin(x / 30.0 * Math.PI)) * 2.0 / 3.0;
      return ret;
    }
    if (outOfChina(lat, lon)) return [lat, lon];
    let dLat = transformLat(lon - 105.0, lat - 35.0);
    let dLon = transformLon(lon - 105.0, lat - 35.0);
    const radLat = lat / 180.0 * Math.PI;
    let magic = Math.sin(radLat);
    magic = 1 - ee * magic * magic;
    const sqrtMagic = Math.sqrt(magic);
    dLat = (dLat * 180.0) / ((a * (1 - ee)) / (magic * sqrtMagic) * Math.PI);
    dLon = (dLon * 180.0) / (a / sqrtMagic * Math.cos(radLat) * Math.PI);
    return [lat + dLat, lon + dLon];
  }

  function toMapLatLng(lat, lon) {
    if (this._mapUsesGcj02) return wgs84ToGcj02(lat, lon);
    return [lat, lon];
  }

  function loadLeaflet() {
    if (window.L && typeof window.L.map === 'function') {
      configureLeafletIcons(window.L);
      return Promise.resolve(window.L);
    }
    if (leafletPromise) return leafletPromise;
    leafletPromise = (async () => {
      await ensureLeafletCss();
      const L = await ensureLeafletJs();
      configureLeafletIcons(L);
      return L;
    })();
    return leafletPromise.catch(error => { leafletPromise = null; throw error; });
  }

  function mergeHotspotRecords(target, incoming) {
    const bySpecies = new Map();
    for (const record of [...(target.records || []), ...(incoming.records || [])]) {
      const key = `${record.speciesId}|${record.speciesName}`;
      const existing = bySpecies.get(key);
      if (!existing) {
        bySpecies.set(key, {...record});
        continue;
      }
      existing.totalCount += Number(record.totalCount || 0);
      existing.occurrenceCount += Number(record.occurrenceCount || 1);
      if (String(record.observedAt) > String(existing.observedAt)) {
        existing.observedAt = record.observedAt;
        existing.latestCount = record.latestCount;
        existing.observationId = record.observationId;
        existing.sourceUrl = record.sourceUrl;
      }
    }
    target.records = [...bySpecies.values()].sort((a, b) => String(b.observedAt).localeCompare(String(a.observedAt), 'zh'));
    target.observations = target.records.map(r => ({speciesId:r.speciesId, speciesName:r.speciesName, frequency:r.occurrenceCount}));
    target.observationCount = target.records.length;
    target.sourceObservationCount = target.records.reduce((sum, r) => sum + Number(r.occurrenceCount || 1), 0);
    return target;
  }

  function hotspotMergeKey(hotspot) {
    if (hotspot.name === '其它观测记录' || hotspot.discovery === 'city_level') return 'other_shanghai';
    const placeKey = normalizePlaceKey(hotspot.name);
    if (placeKey) return `name:${placeKey}`;
    return '';
  }

  function shouldMergeHotspots(a, b) {
    const aKey = hotspotMergeKey(a), bKey = hotspotMergeKey(b);
    if (aKey && aKey === bKey) return true;
    if (a.name === '其它观测记录' || b.name === '其它观测记录') return false;
    if (![a.lat, a.lon, b.lat, b.lon].every(Number.isFinite)) return false;
    return haversineKm(a.lat, a.lon, b.lat, b.lon) <= 0.15;
  }

  function mergeSanitizedHotspots(hotspots) {
    const merged = [];
    for (const hotspot of hotspots) {
      const existing = merged.find(candidate => shouldMergeHotspots(candidate, hotspot));
      if (!existing) {
        merged.push({...hotspot, records:[...(hotspot.records || [])]});
        continue;
      }
      mergeHotspotRecords(existing, hotspot);
      if ((!existing.district || existing.district === '上海市') && hotspot.district) existing.district = hotspot.district;
      if (existing.lat == null && hotspot.lat != null) existing.lat = hotspot.lat;
      if (existing.lon == null && hotspot.lon != null) existing.lon = hotspot.lon;
      if (hotspot.observationWindow?.end && (!existing.observationWindow?.end || hotspot.observationWindow.end > existing.observationWindow.end)) {
        existing.observationWindow = hotspot.observationWindow;
      }
    }
    return merged;
  }

  function sanitizeHotspots(hotspots) {
    if (!Array.isArray(hotspots)) return [];
    const normalized = hotspots.map(h => {
      const fallbackName = hasChinese(h?.name) ? String(h.name).trim() : '其它观测记录';
      const records = Array.isArray(h?.records) ? h.records
        .filter(r => hasChinese(r?.speciesName) && validObservedAt(r?.observedAt))
        .map(r => ({
          observationId: String(r.observationId ?? ''),
          speciesId: String(r.speciesId ?? ''),
          speciesName: String(r.speciesName).trim(),
          observedAt: String(r.observedAt).trim(),
          latestCount: Number.isFinite(Number(r.latestCount)) ? Number(r.latestCount) : 0,
          totalCount: Number.isFinite(Number(r.totalCount)) ? Number(r.totalCount) : 0,
          occurrenceCount: Math.max(1, Number(r.occurrenceCount || 1)),
          sourceUrl: String(r.sourceUrl || SOURCE_URL)
        }))
        .sort((a, b) => String(b.observedAt).localeCompare(String(a.observedAt), 'zh') || a.speciesName.localeCompare(b.speciesName, 'zh'))
      : [];
      const unique = new Map();
      for (const r of records) {
        const key = `${r.speciesId}|${r.speciesName}`;
        const existing = unique.get(key);
        if (!existing || r.observedAt > existing.observedAt) unique.set(key, r);
      }
      const normalizedRecords = [...unique.values()].sort((a,b) => String(b.observedAt).localeCompare(String(a.observedAt), 'zh'));
      const isOther = h?.id === 'other_shanghai' || fallbackName === '其它观测记录' || h?.discovery === 'city_level';
      const known = knownFromPlaceName(fallbackName);
      return {
        ...h,
        id: String(h?.id || `hotspot_${Math.random().toString(36).slice(2,10)}`),
        name: isOther ? '其它观测记录' : (known?.name || fallbackName),
        district: String(h?.district || known?.district || '上海市'),
        lat: isOther ? null : (Number.isFinite(Number(h?.lat)) ? Number(h.lat) : known?.lat ?? null),
        lon: isOther ? null : (Number.isFinite(Number(h?.lon)) ? Number(h.lon) : known?.lon ?? null),
        records: normalizedRecords,
        observations: normalizedRecords.map(r => ({speciesId:r.speciesId, speciesName:r.speciesName, frequency:r.occurrenceCount})),
        observationCount: normalizedRecords.length,
        sourceObservationCount: normalizedRecords.reduce((sum, r) => sum + Number(r.occurrenceCount || 1), 0),
        source: SOURCE,
        sourceUrl: SOURCE_URL,
        observationWindow: h?.observationWindow || observationWindow()
      };
    }).filter(h => h.name === '其它观测记录' || h.records.length > 0);
    return mergeSanitizedHotspots(normalized);
  }

  function loadCachedLiveData() {
    return Boolean(window.EBirdData?.loadCache?.());
  }

  function cacheCurrentData() { /* eBirdData owns the cache */ }

  async function refreshLiveData(options = {}) {
    if (!window.EBirdData?.fetchRecent) return {success:false,error:'eBird 数据模块未加载。'};
    return window.EBirdData.fetchRecent({force:Boolean(options.force), apiKey:options.apiKey});
  }

  function popupHtml(hotspot) {
    const recent = [...(hotspot.records || [])].slice(0, 5);
    const rows = recent.map(r => `${AppUtils.escapeHtml(r.speciesName)} · ${AppUtils.escapeHtml(r.observedAt)}`).join('<br>');
    return `<strong>${AppUtils.escapeHtml(hotspot.name)}</strong><br><span class="muted">${AppUtils.escapeHtml(hotspot.district)}</span>${rows ? `<div style="margin-top:8px">${rows}</div>` : ''}`;
  }

  function renderEmptyState(message, actionLabel='重新加载') {
    document.getElementById('app').innerHTML = `<section class="card"><div class="empty"><strong>${AppUtils.escapeHtml(message)}</strong><br><span class="muted">请在“设置”中保存 eBird API Key 后直接获取最近 7 日上海热点观测，也可以导入 eBird 最近 7 日 JSON 文件。</span><div style="margin-top:14px;display:flex;flex-direction:column;align-items:center;gap:8px"><input id="import-ebird-empty" type="file" accept="application/json,.json" class="input" aria-label="导入最近7日 eBird 数据"><button class="button" id="retry-hotspots" type="button">${AppUtils.escapeHtml(actionLabel)}</button></div></div></section>`;
    document.getElementById('retry-hotspots')?.addEventListener('click', async () => {
      const result = await refreshLiveData.call(this, {force:true});
      if (result.success) await render.call(this); else AppToast.show(result.error || '无法获取 eBird 数据，请检查设置。');
    });
    document.getElementById('import-ebird-empty')?.addEventListener('change', async (event) => {
      const file = event.target.files?.[0];
      if (!file) return;
      const result = await importEBirdFile(file);
      if (result.success) {
        AppToast.show(`已导入 ${result.hotspotCount} 个观测点、${result.recordCount} 条鸟种记录`);
        await render.call(this);
      } else {
        AppToast.show(result.error);
      }
      event.target.value = '';
    });
  }

  function validateImportPayload(data) {
    return window.EBirdData?.validatePayload ? window.EBirdData.validatePayload(data) : {ok:false,error:'eBird 数据模块未加载。'};
  }

  async function importEBirdFile(file) {
    return window.EBirdData?.importFile ? window.EBirdData.importFile(file) : {success:false,error:'eBird 数据模块未加载。'};
  }


  function normalizeGenericImportedHotspots(data) {
    if (!data || data.format !== 'shanghai-birding-hotspots-7d' || data.version !== 1 || data.app !== 'shanghai-birding') {
      return {ok:false,error:'文件不是可识别的观鸟点最近 7 日数据文件。'};
    }
    const w=data.observationWindow;
    if (!w?.start || !w?.end) return {ok:false,error:'导入文件缺少观测时间范围。'};
    const start=Date.parse(`${w.start}T00:00:00`), end=Date.parse(`${w.end}T00:00:00`);
    if(!Number.isFinite(start)||!Number.isFinite(end)||Math.round((end-start)/86400000)!==6) return {ok:false,error:'导入文件必须覆盖连续 7 个自然日。'};
    if(data.source!=='中国观鸟记录中心') return {ok:false,error:'导入文件来源必须为中国观鸟记录中心。'};
    const normalized=[];
    const byKey=new Map();
    for(const h of Array.isArray(data.hotspots)?data.hotspots:[]) {
      const isOther=h.name==='其它观测记录'||h.id==='other_shanghai'||h.discovery==='city_level';
      const name=isOther?'其它观测记录':String(h.name||'').trim();
      if(!name) continue;
      const key=isOther?'other_shanghai':name;
      const bucket=byKey.get(key)||{id:key,name,district:String(h.district||'上海市'),lat:Number.isFinite(Number(h.lat))?Number(h.lat):null,lon:Number.isFinite(Number(h.lon))?Number(h.lon):null,discovery:isOther?'city_level':'web_import',source:'中国观鸟记录中心',sourceUrl:String(h.sourceUrl||'https://www.birdreport.cn/home/search/page.html'),observationWindow:w,records:[]};
      for(const r of Array.isArray(h.records)?h.records:[]) {
        const observedAt=String(r.observedAt||'').trim();
        if(!/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})?$/.test(observedAt)) continue;
        const speciesName=String(r.speciesName||'').trim();
        if(!/[\u3400-\u4dbf\u4e00-\u9fff]/.test(speciesName)) continue;
        const species=BIRD_LEXICON.find(b=>b.name===speciesName);
        bucket.records.push({observationId:String(r.observationId||''),speciesId:String(r.speciesId||species?.id||speciesName),speciesName,observedAt,latestCount:Number(r.latestCount||0),totalCount:Number(r.totalCount||r.latestCount||0),occurrenceCount:Math.max(1,Number(r.occurrenceCount||1)),sourceUrl:String(r.sourceUrl||'https://www.birdreport.cn/home/search/page.html')});
      }
      byKey.set(key,bucket);
    }
    for(const h of byKey.values()) {
      const latest=new Map();
      for(const r of h.records) {
        const k=r.speciesId||r.speciesName; const old=latest.get(k);
        if(!old || r.observedAt>old.observedAt) latest.set(k,{...r,totalCount:(old?.totalCount||0)+r.totalCount,occurrenceCount:(old?.occurrenceCount||0)+r.occurrenceCount});
        else { old.totalCount += r.totalCount; old.occurrenceCount += r.occurrenceCount; }
      }
      h.records=[...latest.values()].sort((a,b)=>b.observedAt.localeCompare(a.observedAt,'zh'));
      h.observations=h.records.map(r=>({speciesId:r.speciesId,speciesName:r.speciesName,frequency:r.occurrenceCount}));
      h.observationCount=h.records.length;
      h.sourceObservationCount=h.records.reduce((n,r)=>n+r.occurrenceCount,0);
      normalized.push(h);
    }
    const usable=normalized.filter(h=>h.records.length);
    if(!usable.length) return {ok:false,error:'导入文件没有包含具体观测时间和中文鸟种的有效记录。'};
    return {ok:true,value:{...data,hotspots:usable}};
  }

  async function importGenericFile(file) {
    try {
      const parsed=JSON.parse(await file.text());
      const checked=normalizeGenericImportedHotspots(parsed);
      if(!checked.ok) return {success:false,error:checked.error};
      const data=checked.value;
      AppState.externalData={...AppState.externalData,hotspots:data.hotspots,hotspotData:data.hotspotData||{source:'中国观鸟记录中心',sourceUrl:data.sourceUrl,observationWindow:data.observationWindow,retrievedAt:data.retrievedAt,sourceObservationCount:data.hotspotData?.sourceObservationCount||0,displayedRecordCount:data.hotspotData?.displayedRecordCount||data.hotspots.reduce((n,h)=>n+h.records.length,0)},sourceStatus:'ok',updatedAt:data.retrievedAt||data.generatedAt};
      window.EXTERNAL_DATA={...window.EXTERNAL_DATA,...AppState.externalData};
      try{localStorage.setItem('shanghai-birding-generic-hotspots-v1',JSON.stringify(data));}catch(_){}
      AppStateActions.notify();
      return {success:true,hotspotCount:data.hotspots.length,recordCount:data.hotspots.reduce((n,h)=>n+h.records.length,0)};
    } catch(error) { return {success:false,error:'无法解析观鸟点 JSON：'+(error?.message||'文件无效')}; }
  }

  function renderShell(hotspots, selectedId) {
    const range = AppState.externalData.hotspotData?.observationWindow || observationWindow();
    const sourceRecords = Number(AppState.externalData.hotspotData?.sourceObservationCount || 0);
    return `<div class="grid hotspot-layout">
      <section class="card hotspot-list-card">
        <div class="card-header">
          <div><strong>上海观鸟点</strong><div class="muted">${AppUtils.escapeHtml(formatSourceLabel(AppState.externalData.hotspotData?.source))} · 最近 7 日（${AppUtils.escapeHtml(range.start)} 至 ${AppUtils.escapeHtml(range.end)}） · ${hotspots.length} 个观测点 · ${sourceRecords} 条来源记录</div></div>
          <button class="button" id="refresh-hotspots" type="button">刷新数据</button>
        </div>
        <div class="card-body hotspot-list-body"><div class="hotspot-list">${hotspots.map(h => `<button class="hotspot-item ${h.id === selectedId ? 'active' : ''}" data-id="${AppUtils.escapeHtml(h.id)}" type="button"><strong>${AppUtils.escapeHtml(h.name)}</strong><div class="muted" style="margin-top:4px">${AppUtils.escapeHtml(h.district)} · ${h.records.length} 种 · ${Number(h.sourceObservationCount || h.records.reduce((s,r)=>s+r.occurrenceCount,0))} 条来源记录</div></button>`).join('')}</div></div>
      </section>
      <div class="hotspot-main">
        <section class="card hotspot-map-section"><div class="card-body hotspot-map-card"><div id="leaflet-map" class="leaflet-map" role="application" aria-label="上海观鸟点地图"></div><div id="map-status" class="map-status">正在加载地图……</div></div></section>
        <section class="card hotspot-detail-card"><div id="hotspot-detail"></div></section>
      </div>
    </div>`;
  }

  function renderDetail(selected) {
    const detail = document.getElementById('hotspot-detail');
    if (!detail) return;
    const records = selected ? sanitizeHotspots([selected])[0]?.records || [] : [];
    const label = selected?.id === 'other_shanghai' || selected?.discovery === 'city_level' ? '上海市级记录' : '该观鸟点最近 7 日记录';
    const coordinate = selected && selected.lat != null && selected.lon != null
      ? `<span class="badge">${Number(selected.lat).toFixed(5)}, ${Number(selected.lon).toFixed(5)}</span>` : '';
    const rows = records.length ? records.map((r, i) => `<div class="obs-detail-row">
      <div><strong>${AppUtils.escapeHtml(r.speciesName)}</strong><div class="muted obs-detail-meta">最近观测：${AppUtils.escapeHtml(r.observedAt)} · ${Number(r.occurrenceCount)} 次来源记录${Number(r.latestCount) > 0 ? ` · 最近一次 ${Number(r.latestCount)} 只` : ''}${Number(r.totalCount) > 0 ? ` · 合计记录数量 ${Number(r.totalCount)}` : ''}</div></div>
    </div>`).join('') : '<div class="empty">最近 7 日暂无带具体观测时间的公开记录。</div>';
    const sumOccurrences = records.reduce((s, r) => s + Number(r.occurrenceCount || 1), 0);
    detail.innerHTML = `<div class="card-header"><div><strong>${selected ? AppUtils.escapeHtml(selected.name) : '暂无观测点'}</strong><div class="muted">${label}</div></div>${coordinate}</div>
      <div class="card-body"><div class="hotspot-detail-summary"><strong>${records.length}</strong><span>种鸟</span><strong style="margin-left:12px">${sumOccurrences}</strong><span>条来源记录</span><span class="muted">数据源：${AppUtils.escapeHtml(formatSourceLabel(AppState.externalData.hotspotData?.source))}</span></div><div class="hotspot-observation-list">${rows}</div></div>`;
  }

  async function select(id) {
    const hotspots = sanitizeHotspots(AppState.externalData.hotspots || []);
    const selected = hotspots.find(h => h.id === id);
    if (!selected) return;
    this.selectedId = id;
    document.querySelectorAll('.hotspot-item').forEach(btn => btn.classList.toggle('active', btn.dataset.id === id));
    renderDetail(selected);
    if (this.map && selected.lat != null && selected.lon != null && typeof this.map.setView === 'function') {
      const [lat, lon] = toMapLatLng.call(this, Number(selected.lat), Number(selected.lon));
      this.map.setView([lat, lon], 11);
      this.markers?.get(id)?.openPopup?.();
    }
  }

  function shellMounted() {
    return Boolean(document.getElementById('leaflet-map') && document.querySelector('.hotspot-layout'));
  }

  function clearMarkers() {
    if (this.markers instanceof Map) {
      for (const marker of this.markers.values()) {
        if (marker?.remove) marker.remove();
        else if (this.map?.removeLayer && marker) this.map.removeLayer(marker);
      }
    }
    this.markers = new Map();
  }

  function placeMarkers(L, hotspots, selectedId) {
    clearMarkers.call(this);
    const bounds = [];
    hotspots.forEach(h => {
      const lat = Number(h.lat), lon = Number(h.lon);
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
      const [mapLat, mapLon] = toMapLatLng.call(this, lat, lon);
      bounds.push([mapLat, mapLon]);
      const marker = L.marker([mapLat, mapLon], {keyboard:false, riseOnHover:true}).addTo(this.map).bindPopup(popupHtml(h));
      if (marker.on) marker.on('click', () => select.call(this, h.id));
      this.markers.set(h.id, marker);
    });
    if (bounds.length > 1 && L.latLngBounds && this.map.fitBounds) {
      this.map.fitBounds(L.latLngBounds(bounds).pad(0.12), {animate:false});
    }
    const active = hotspots.find(h => h.id === selectedId);
    if (active && this.markers.get(active.id)) this.markers.get(active.id).openPopup();
    return bounds.length;
  }

  function addBaseTiles(L, map) {
    const gaode = L.tileLayer(GAODE_TILE_URL, {
      subdomains: '1234',
      maxZoom: 18,
      updateWhenIdle: true,
      keepBuffer: 2,
      attribution: '&copy; 高德地图'
    });
    const osm = L.tileLayer(OSM_TILE_URL, {
      maxZoom: 18,
      updateWhenIdle: true,
      keepBuffer: 2,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    });
    let gaodeErrors = 0;
    gaode.on?.('tileerror', () => {
      gaodeErrors += 1;
      if (gaodeErrors < 4 || this._mapTileFallbackDone) return;
      this._mapTileFallbackDone = true;
      this._mapUsesGcj02 = false;
      try { map.removeLayer(gaode); } catch (_) {}
      osm.addTo(map);
      if (this._lastHotspots) placeMarkers.call(this, L, this._lastHotspots, this.selectedId);
    });
    this._mapUsesGcj02 = true;
    this._mapTileFallbackDone = false;
    gaode.addTo(map);
    return gaode;
  }

  function bindHotspotChrome(hotspots) {
    document.querySelectorAll('.hotspot-item').forEach(btn => {
      btn.addEventListener('click', () => select.call(this, btn.dataset.id));
    });
    document.getElementById('refresh-hotspots')?.addEventListener('click', async () => {
      const button = document.getElementById('refresh-hotspots');
      if (button) { button.disabled = true; button.textContent = '更新中…'; }
      try {
        const result = await refreshLiveData.call(this, {force:true});
        if (result.success) {
          const next = sanitizeHotspots(AppState.externalData.hotspots || []);
          AppState.externalData.hotspots = next;
          await paintUI.call(this, next);
          AppToast?.show?.(`已更新 ${result.hotspotCount} 个观测点`);
        } else {
          AppToast?.show?.(result.error || '刷新失败');
        }
      } finally {
        if (button) { button.disabled = false; button.textContent = '刷新数据'; }
      }
    });
  }

  function updateListAndMeta(hotspots, selectedId) {
    const range = AppState.externalData.hotspotData?.observationWindow || observationWindow();
    const sourceRecords = Number(AppState.externalData.hotspotData?.sourceObservationCount || 0);
    const meta = document.querySelector('.hotspot-list-card .card-header .muted');
    if (meta) {
      meta.textContent = `${formatSourceLabel(AppState.externalData.hotspotData?.source)} · 最近 7 日（${range.start} 至 ${range.end}） · ${hotspots.length} 个观测点 · ${sourceRecords} 条来源记录`;
    }
    const list = document.querySelector('.hotspot-list');
    if (list) {
      list.innerHTML = hotspots.map(h => `<button class="hotspot-item ${h.id === selectedId ? 'active' : ''}" data-id="${AppUtils.escapeHtml(h.id)}" type="button"><strong>${AppUtils.escapeHtml(h.name)}</strong><div class="muted" style="margin-top:4px">${AppUtils.escapeHtml(h.district)} · ${h.records.length} 种 · ${Number(h.sourceObservationCount || h.records.reduce((s,r)=>s+r.occurrenceCount,0))} 条来源记录</div></button>`).join('');
      list.querySelectorAll('.hotspot-item').forEach(btn => btn.addEventListener('click', () => select.call(this, btn.dataset.id)));
    }
  }

  async function initializeMap(hotspots, selectedId) {
    const status = document.getElementById('map-status');
    const mapElement = document.getElementById('leaflet-map');
    if (!mapElement) return;
    this._lastHotspots = hotspots;
    try {
      const L = await loadLeaflet();
      const canReuse = this.map && this._mapEl === mapElement && document.body.contains(mapElement);
      if (canReuse) {
        placeMarkers.call(this, L, hotspots, selectedId);
        if (this.map.invalidateSize) requestAnimationFrame(() => this.map.invalidateSize());
        if (status) status.textContent = `最近 7 日公开观测数据来自 ${formatSourceLabel(AppState.externalData.hotspotData?.source)}。`;
        return;
      }
      if (this.map?.remove) this.map.remove();
      this._mapUsesGcj02 = true;
      const [centerLat, centerLon] = toMapLatLng.call(this, 31.2304, 121.4737);
      this.map = L.map(mapElement, {
        scrollWheelZoom: true,
        preferCanvas: true,
        fadeAnimation: false,
        markerZoomAnimation: false,
        zoomAnimation: true
      }).setView([centerLat, centerLon], 9);
      this._mapEl = mapElement;
      addBaseTiles.call(this, L, this.map);
      placeMarkers.call(this, L, hotspots, selectedId);
      if (this.map.invalidateSize) requestAnimationFrame(() => this.map.invalidateSize());
      if (status) status.textContent = `最近 7 日公开观测数据来自 ${formatSourceLabel(AppState.externalData.hotspotData?.source)}。`;
    } catch (error) {
      if (status) status.innerHTML = '<strong>地图底图加载失败。</strong> 需要网络连接以加载地图库或瓦片；真实观测点列表及下方记录仍可正常使用。';
      mapElement.classList.add('leaflet-map-unavailable');
      console.error(error);
    }
  }

  async function paintUI(hotspots) {
    const selectedId = hotspots.some(h => h.id === this.selectedId)
      ? this.selectedId
      : (hotspots.find(h => h.id !== 'other_shanghai')?.id || hotspots[0]?.id);
    this.selectedId = selectedId;
    if (shellMounted() && this.map && this._mapEl === document.getElementById('leaflet-map')) {
      updateListAndMeta.call(this, hotspots, selectedId);
      renderDetail(hotspots.find(h => h.id === selectedId));
      await initializeMap.call(this, hotspots, selectedId);
      return;
    }
    if (this.map?.remove) this.map.remove();
    this.map = null;
    this._mapEl = null;
    this.markers = new Map();
    document.getElementById('app').innerHTML = renderShell(hotspots, selectedId);
    renderDetail(hotspots.find(h => h.id === selectedId));
    bindHotspotChrome.call(this, hotspots);
    await initializeMap.call(this, hotspots, selectedId);
  }

  async function shouldAutoRefresh() {
    const key = await window.EBirdData?.getApiKey?.();
    if (!key) return false;
    const updated = AppState.externalData?.hotspotData?.retrievedAt || AppState.externalData?.updatedAt;
    if (!updated) return true;
    const age = Date.now() - Date.parse(updated);
    return !Number.isFinite(age) || age > 10 * 60 * 1000;
  }

  async function render() {
    if (!AppState.externalData.hotspots?.length) loadCachedLiveData();
    let hotspots = sanitizeHotspots(AppState.externalData.hotspots || []);

    // Paint cached data first so the map appears immediately; refresh in the background.
    if (hotspots.length) {
      AppState.externalData.hotspots = hotspots;
      cacheCurrentData();
      await paintUI.call(this, hotspots);
    }

    try {
      if (await shouldAutoRefresh()) {
        const result = await refreshLiveData.call(this, {force:true});
        if (result.success) {
          hotspots = sanitizeHotspots(AppState.externalData.hotspots || []);
          if (hotspots.length) {
            AppState.externalData.hotspots = hotspots;
            cacheCurrentData();
            await paintUI.call(this, hotspots);
          }
        }
      }
    } catch (_) {}

    if (!hotspots.length) {
      const hasKey = Boolean(await window.EBirdData?.getApiKey?.());
      renderEmptyState(hasKey ? 'eBird 最近 7 日数据获取失败，请检查 API Key 或网络连接，或使用浏览器采集助手导入中国观鸟记录中心数据。' : '尚未获取最近 7 日热点观测数据，请使用浏览器采集助手导入中国观鸟记录中心数据，或配置 eBird API Key。', '重新获取');
    }
  }

  window.HotspotsPage = {
    render,
    loadLeaflet,
    refreshLiveData,
    loadCachedLiveData,
    observationWindow,
    KNOWN_HOTSPOTS,
    SOURCE,
    SOURCE_URL,
    sanitizeHotspots,
    isCityLevelPlace,
    validObservedAt,
    validateImportPayload,
    importEBirdFile,
    normalizeGenericImportedHotspots,
    importGenericFile,
    IMPORT_FORMAT
  };
})();
