(function () {
  const SOURCE = 'eBird';
  const API_BASE = 'https://api.ebird.org/v2';
  const REGION_CODE = 'CN-31';
  const SOURCE_URL = 'https://ebird.org/region/CN-31';
  const API_DOC_URL = 'https://documenter.getpostman.com/view/664302/S1ENwy59?version=latest';
  const CACHE_KEY = 'shanghai-birding-ebird-hotspots-v1';
  const IMPORT_FORMAT = 'shanghai-birding-ebird-7d';
  const API_KEY_STORAGE_KEY = 'ebirdApiKey';
  // Default key supplied by the project owner. A user-saved key can still override it.
  // Keep this out of the UI text; the input remains available only for replacing the default.
  const EMBEDDED_API_KEY = '62fd8ff3-7489-40ee-9f63-37eecb63da37';

  function normalizeKey(value) {
    return String(value || '').trim();
  }
  function hasChinese(value) { return /[\u3400-\u4dbf\u4e00-\u9fff]/.test(String(value || '')); }
  function isoDate(d) {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }
  function observationWindow(reference = new Date()) {
    const end = isoDate(reference);
    const d = new Date(reference.getFullYear(), reference.getMonth(), reference.getDate());
    d.setDate(d.getDate() - 6);
    return { start: isoDate(d), end };
  }
  function parseObservedAt(value) {
    const raw = String(value || '').trim();
    if (!raw) return null;
    const normalized = raw.replace('T', ' ').replace(/([+-]\d{2}:?\d{2}|Z)$/, '').trim();
    const m = normalized.match(/^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})(?::(\d{2}))?/);
    if (!m) return null;
    return `${m[1]} ${m[2]}${m[3] ? ':' + m[3] : ''}`;
  }
  function recordTimestamp(value) {
    const parsed = parseObservedAt(value);
    if (!parsed) return NaN;
    const n = Date.parse(parsed.replace(' ', 'T'));
    return Number.isFinite(n) ? n : NaN;
  }
  function normalizePlaceName(raw, district) {
    let name = String(raw || '').trim();
    name = name.replace(/\s*,\s*Shanghai(?:\s*,\s*China)?$/i, '').replace(/\s*,\s*China$/i, '').trim();
    const aliases = new Map([
      ['Binjiang Forest Park', '滨江森林公园'],
      ['Binjiang Forest Park, Shanghai', '滨江森林公园'],
      ['Century Park', '世纪公园'],
      ['Shanghai Century Park', '世纪公园'],
      ['Shanghai Botanical Garden', '上海植物园'],
      ['Shanghai Gongqing Forest Park', '共青森林公园'],
      ['Gongqing Forest Park', '共青森林公园'],
      ['Wusong Paotaiwan Wetland Forest Park', '吴淞炮台湾湿地森林公园'],
      ['Shanghai Bay National Forest Park', '上海海湾国家森林公园'],
      ['Dongtan National Nature Reserve', '崇明东滩'],
      ['Chongming Dongtan', '崇明东滩'],
      ['Nanhui Dongtan', '南汇东滩']
    ]);
    const mapped = aliases.get(name) || aliases.get(name.replace(/\s+/g, ' '));
    if (mapped) return mapped;
    if (hasChinese(name)) return name;
    if (isShanghaiLevel(name)) return '其它观测记录';
    // Keep a Chinese-only deterministic fallback name. The original eBird name
    // remains in sourcePlaceName for traceability, while UI uses Chinese only.
    const suffix = district && hasChinese(district) ? district.replace(/区$/, '') : '上海';
    return `${suffix}其它观测点`;
  }
  function isShanghaiLevel(name) {
    const raw = String(name || '').trim().toLowerCase();
    const s = raw.replace(/[\s,，]+/g, '');
    return ['shanghai', 'shanghaicity', 'shanghaichina', '上海', '上海市', '上海市中国'].includes(s);
  }
  function normalizeSpeciesName(raw) {
    const name = String(raw || '').trim();
    return hasChinese(name) ? name : '';
  }
  function normalizePlaceForMerge(raw) {
    return normalizePlaceName(raw, '').replace(/[\s,，。·•-]+/g, '').toLowerCase();
  }
  function haversineKm(lat1, lon1, lat2, lon2) {
    const toRad = Math.PI / 180;
    const dLat = (lat2 - lat1) * toRad;
    const dLon = (lon2 - lon1) * toRad;
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * toRad) * Math.cos(lat2 * toRad) * Math.sin(dLon / 2) ** 2;
    return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }
  function observationKey(row) {
    const locKey = row.locId ? `loc:${row.locId}` : `name:${normalizePlaceForMerge(row.locName)}|${Number(row.lat || 0).toFixed(4)}|${Number(row.lng || 0).toFixed(4)}`;
    return `${locKey}::species:${row.speciesCode || row.comName || row.sciName || ''}`;
  }
  function mergeHotspotRecord(hotspot, record) {
    const key = record.speciesId || record.speciesName;
    const existing = hotspot.recordsBySpecies.get(key);
    if (!existing) {
      hotspot.recordsBySpecies.set(key, {...record});
      return;
    }
    existing.totalCount += Number(record.totalCount || 0);
    existing.occurrenceCount += Number(record.occurrenceCount || 1);
    if (recordTimestamp(record.observedAt) > recordTimestamp(existing.observedAt)) {
      existing.observedAt = record.observedAt;
      existing.latestCount = record.latestCount;
      existing.observationId = record.observationId;
      existing.sourceUrl = record.sourceUrl;
    }
  }
  function aggregateObservations(rows, window) {
    const groups = new Map();
    let sourceCount = 0;
    for (const row of Array.isArray(rows) ? rows : []) {
      const observedAt = parseObservedAt(row.obsDt || row.observedAt);
      const speciesName = normalizeSpeciesName(row.comName || row.speciesName);
      if (!observedAt || !speciesName) continue;
      const lat = Number(row.lat), lon = Number(row.lng ?? row.lon);
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
      const key = observationKey(row);
      sourceCount += 1;
      const current = groups.get(key);
      const timestamp = recordTimestamp(observedAt);
      const count = Number.isFinite(Number(row.howMany)) && Number(row.howMany) >= 0 ? Number(row.howMany) : 0;
      if (!current) {
        groups.set(key, {
          locId: String(row.locId || ''),
          locName: String(row.locName || ''),
          sourcePlaceName: String(row.locName || ''),
          district: String(row.subnational2Name || row.subnational1Name || '上海市'),
          lat, lon,
          speciesCode: String(row.speciesCode || ''),
          speciesName,
          observedAt,
          latestCount: count,
          totalCount: count,
          occurrenceCount: 1,
          subId: String(row.subId || '')
        });
        continue;
      }
      current.totalCount += count;
      current.occurrenceCount += 1;
      if (timestamp > recordTimestamp(current.observedAt)) {
        current.observedAt = observedAt;
        current.latestCount = count;
        current.subId = String(row.subId || current.subId || '');
      }
    }

    const hotspots = [];
    const exactByLocId = new Map();
    const byName = new Map();

      function findHotspot(record, displayName, isCity) {
      if (isCity) return exactByLocId.get('__CITY__') || null;
      if (record.locId && exactByLocId.has(record.locId)) return exactByLocId.get(record.locId);
      const nameKey = normalizePlaceForMerge(displayName);
      const candidates = byName.get(nameKey) || [];
      // A stable normalized place name is the primary key: eBird may assign
      // different locIds and slightly different coordinates to the same site.
      if (candidates.length) return candidates[0];
      // Keep a coordinate fallback for the case where eBird uses different
      // names for the same physical hotspot.
      for (const candidate of hotspots) {
        if (candidate.name === '其它观测记录' || !Number.isFinite(candidate.lat) || !Number.isFinite(candidate.lon)) continue;
        if (haversineKm(record.lat, record.lon, candidate.lat, candidate.lon) <= 0.15) return candidate;
      }
      return null;
    }

    function addHotspot(record) {
      const isCity = isShanghaiLevel(record.locName);
      const name = isCity ? '其它观测记录' : normalizePlaceName(record.locName, record.district);
      let hotspot = findHotspot(record, name, isCity);
      const cleanedDistrict = hasChinese(record.district) ? record.district : '上海市';
      if (!hotspot) {
        hotspot = {
          id: isCity ? 'other_shanghai' : `ebird:${record.locId || normalizePlaceForMerge(name)}`,
          name,
          district: isCity ? '上海市' : cleanedDistrict,
          lat: isCity ? null : record.lat,
          lon: isCity ? null : record.lon,
          discovery: isCity ? 'city_level' : 'ebird_recent',
          source: SOURCE,
          sourceUrl: record.subId ? `https://ebird.org/checklist/${record.subId}` : SOURCE_URL,
          observationWindow: window,
          recordsBySpecies: new Map()
        };
        hotspots.push(hotspot);
        const nameKey = normalizePlaceForMerge(name);
        if (!isCity) {
          if (!byName.has(nameKey)) byName.set(nameKey, []);
          byName.get(nameKey).push(hotspot);
          if (record.locId) exactByLocId.set(record.locId, hotspot);
        } else {
          exactByLocId.set('__CITY__', hotspot);
        }
      } else if (record.locId) {
        exactByLocId.set(record.locId, hotspot);
      }
      mergeHotspotRecord(hotspot, {
        observationId: record.subId || `${record.speciesCode}|${record.observedAt}`,
        speciesId: record.speciesCode || record.speciesName,
        speciesName: record.speciesName,
        observedAt: record.observedAt,
        latestCount: record.latestCount,
        totalCount: record.totalCount,
        occurrenceCount: record.occurrenceCount,
        sourceUrl: record.subId ? `https://ebird.org/checklist/${record.subId}` : SOURCE_URL
      });
    }

    for (const record of groups.values()) addHotspot(record);

    const out = hotspots.map(h => ({
      ...h,
      records: [...h.recordsBySpecies.values()].sort((a, b) => recordTimestamp(b.observedAt) - recordTimestamp(a.observedAt) || a.speciesName.localeCompare(b.speciesName, 'zh')),
      observations: [...h.recordsBySpecies.values()].sort((a, b) => recordTimestamp(b.observedAt) - recordTimestamp(a.observedAt)).map(r => ({speciesId:r.speciesId, speciesName:r.speciesName, frequency:r.occurrenceCount})),
      observationCount: h.recordsBySpecies.size,
      sourceObservationCount: [...h.recordsBySpecies.values()].reduce((s,r)=>s+Number(r.occurrenceCount || 1),0)
    }));

    return {
      hotspots: out,
      meta: {
        source: SOURCE,
        sourceUrl: SOURCE_URL,
        apiUrl: `${API_BASE}/data/obs/${REGION_CODE}/recent`,
        regionCode: REGION_CODE,
        observationWindow: window,
        retrievedAt: new Date().toISOString(),
        sourceObservationCount: sourceCount,
        displayedRecordCount: out.reduce((s,h)=>s+h.records.length,0),
        hotspotCount: out.length,
        note: '来自 eBird 最近 7 日热点观测；同一热点同一鸟种仅保留最晚观测时间。'
      }
    };
  }
  function validatePayload(data) {
    if (!data || data.format !== IMPORT_FORMAT || data.version !== 1 || data.app !== 'shanghai-birding') return {ok:false,error:'文件不是可识别的 eBird 最近 7 日数据文件。'};
    if (data.source !== SOURCE || data.regionCode !== REGION_CODE) return {ok:false,error:'导入文件必须来自上海 eBird（CN-31）。'};
    const w = data.observationWindow;
    if (!w?.start || !w?.end) return {ok:false,error:'导入文件缺少观测时间范围。'};
    const start = new Date(`${w.start}T00:00:00`), end = new Date(`${w.end}T00:00:00`);
    if (!Number.isFinite(start.getTime()) || !Number.isFinite(end.getTime()) || Math.round((end-start)/86400000) !== 6) return {ok:false,error:'导入文件必须覆盖连续 7 个自然日。'};
    if (!Array.isArray(data.hotspots) || !data.hotspots.length) return {ok:false,error:'导入文件没有可用观鸟点。'};
    const checked = data.hotspots.map(h => ({
      ...h,
      name: isShanghaiLevel(h.name) ? '其它观测记录' : normalizePlaceName(h.name, h.district),
      records: Array.isArray(h.records) ? h.records.filter(r => normalizeSpeciesName(r.speciesName) && parseObservedAt(r.observedAt)).map(r => ({...r, observedAt:parseObservedAt(r.observedAt)})) : []
    })).filter(h => h.records.length || h.name === '其它观测记录');
    if (!checked.length) return {ok:false,error:'导入文件中的记录没有有效的中文鸟种和具体观测时间。'};
    return {ok:true,value:{...data,hotspots:checked}};
  }
  function maskApiKey(value) {
    const key = normalizeKey(value);
    if (!key) return '';
    if (key.length <= 4) return '••••';
    return `••••${key.slice(-4)}`;
  }
  async function getSavedApiKey() {
    try {
      return normalizeKey(await Storage.getAppValue(API_KEY_STORAGE_KEY));
    } catch (_) { return ''; }
  }
  async function getApiKey() {
    const saved = await getSavedApiKey();
    return saved || EMBEDDED_API_KEY;
  }
  async function getApiKeyInfo() {
    const saved = await getSavedApiKey();
    if (saved) {
      return {source:'custom', masked:maskApiKey(saved), usingEmbedded:false, hasOverride:true};
    }
    return {source:'embedded', masked:maskApiKey(EMBEDDED_API_KEY), usingEmbedded:true, hasOverride:false};
  }
  async function saveApiKey(value) {
    const key = normalizeKey(value);
    if (!key) { await Storage.setAppValue(API_KEY_STORAGE_KEY, ''); return ''; }
    await Storage.setAppValue(API_KEY_STORAGE_KEY, key);
    return key;
  }
  async function fetchRecent(options={}) {
    const apiKey = normalizeKey(options.apiKey || await getApiKey());
    if (!apiKey) return {success:false,error:'请先在“设置”中保存 eBird API Key。'};
    const window = observationWindow(new Date());
    const url = new URL(`${API_BASE}/data/obs/${REGION_CODE}/recent`);
    url.searchParams.set('back', '7');
    url.searchParams.set('detail', 'full');
    url.searchParams.set('hotspot', 'true');
    url.searchParams.set('maxResults', '10000');
    url.searchParams.set('sppLocale', 'zh_SIM');
    let response;
    try {
      response = await fetch(url.toString(), {headers:{'X-eBirdApiToken':apiKey}, cache:'no-store'});
    } catch (error) {
      // A file:// page may fail the custom-header CORS preflight. eBird also documents
      // API-key query-string access for hotspot endpoints, so retry the same GET with key=.
      try {
        const fallbackUrl = new URL(url.toString());
        fallbackUrl.searchParams.set('key', apiKey);
        response = await fetch(fallbackUrl.toString(), {cache:'no-store'});
      } catch (fallbackError) {
        return {success:false,error:`无法连接 eBird API：${fallbackError?.message || error?.message || '网络错误'}`};
      }
    }
    if (!response.ok) {
      let detail = '';
      try { detail = await response.text(); } catch (_) {}
      if (response.status === 403 || response.status === 401) return {success:false,error:'eBird API Key 无效或无权限。请在设置中更新个人 API Key。'};
      return {success:false,error:`eBird API 返回 HTTP ${response.status}${detail ? `：${detail.slice(0,160)}` : ''}`};
    }
    let rows;
    try { rows = await response.json(); } catch (_) { return {success:false,error:'eBird 返回的数据不是有效 JSON。'}; }
    const aggregated = aggregateObservations(rows, window);
    if (!aggregated.hotspots.length) return {success:false,error:'eBird 最近 7 日未返回上海热点观测，未覆盖已有数据。'};
    const payload = {format:IMPORT_FORMAT,version:1,app:'shanghai-birding',source:SOURCE,sourceUrl:SOURCE_URL,apiUrl:url.toString().replace(/([?&])/, '$1'),regionCode:REGION_CODE,generatedAt:new Date().toISOString(),retrievedAt:aggregated.meta.retrievedAt,observationWindow:window,hotspotData:aggregated.meta,hotspots:aggregated.hotspots};
    try { localStorage.setItem(CACHE_KEY, JSON.stringify(payload)); } catch (_) {}
    AppState.externalData = {...AppState.externalData, hotspots:aggregated.hotspots, hotspotData:aggregated.meta, sourceStatus:'ok', updatedAt:aggregated.meta.retrievedAt};
    window.EXTERNAL_DATA = {...window.EXTERNAL_DATA, ...AppState.externalData};
    AppStateActions.notify();
    return {success:true,payload,hotspotCount:aggregated.hotspots.length,recordCount:aggregated.hotspots.reduce((s,h)=>s+h.records.length,0)};
  }
  function loadCache() {
    try {
      const raw = localStorage.getItem(CACHE_KEY); if (!raw) return false;
      const parsed = JSON.parse(raw); const checked = validatePayload(parsed); if (!checked.ok) return false;
      const data = checked.value; const w = observationWindow(new Date());
      if (data.observationWindow.end !== w.end) return false;
      AppState.externalData = {...AppState.externalData, hotspots:data.hotspots, hotspotData:{...data.hotspotData,source:SOURCE,sourceUrl:SOURCE_URL},sourceStatus:'ok',updatedAt:data.retrievedAt || data.generatedAt};
      return true;
    } catch (_) { return false; }
  }
  async function importFile(file) {
    try {
      const text = await file.text(); const data = JSON.parse(text);
      let normalized = data;
      if (Array.isArray(data)) {
        const window = observationWindow(new Date());
        const aggregated = aggregateObservations(data, window);
        if (!aggregated.hotspots.length) return {success:false,error:'原始 eBird JSON 中没有可用的上海热点观测（需要具体时间、坐标和中文鸟种名）。'};
        normalized = {format:IMPORT_FORMAT,version:1,app:'shanghai-birding',source:SOURCE,sourceUrl:SOURCE_URL,regionCode:REGION_CODE,generatedAt:new Date().toISOString(),retrievedAt:aggregated.meta.retrievedAt,observationWindow:window,hotspotData:aggregated.meta,hotspots:aggregated.hotspots};
      }
      const checked = validatePayload(normalized); if (!checked.ok) return {success:false,error:checked.error};
      const value = checked.value;
      AppState.externalData = {...AppState.externalData, hotspots:value.hotspots, hotspotData:{...value.hotspotData,source:SOURCE,sourceUrl:SOURCE_URL},sourceStatus:'ok',updatedAt:value.retrievedAt || value.generatedAt || new Date().toISOString()};
      try { localStorage.setItem(CACHE_KEY, JSON.stringify(value)); } catch (_) {}
      window.EXTERNAL_DATA = {...window.EXTERNAL_DATA, ...AppState.externalData}; AppStateActions.notify();
      return {success:true,hotspotCount:value.hotspots.length,recordCount:value.hotspots.reduce((s,h)=>s+h.records.length,0)};
    } catch (error) { return {success:false,error:`导入失败：${error?.message || '无效文件'}`}; }
  }
  function exportCurrent() {
    const payload = {format:IMPORT_FORMAT,version:1,app:'shanghai-birding',source:SOURCE,sourceUrl:SOURCE_URL,regionCode:REGION_CODE,generatedAt:new Date().toISOString(),retrievedAt:AppState.externalData.updatedAt || '',observationWindow:AppState.externalData.hotspotData?.observationWindow || observationWindow(),hotspotData:AppState.externalData.hotspotData || {},hotspots:AppState.externalData.hotspots || []};
    const blob = new Blob([JSON.stringify(payload,null,2)], {type:'application/json'});
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `shanghai-ebird-7d-${AppUtils.todayISO()}.json`; a.click(); setTimeout(()=>URL.revokeObjectURL(a.href),1000);
  }
  window.EBirdData = {SOURCE,API_BASE,REGION_CODE,SOURCE_URL,API_DOC_URL,IMPORT_FORMAT,observationWindow,parseObservedAt,aggregateObservations,validatePayload,getApiKey,getApiKeyInfo,maskApiKey,saveApiKey,fetchRecent,loadCache,importFile,exportCurrent};
})();
