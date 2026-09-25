(function () {
  const SHANGHAI = { latitude: 31.2304, longitude: 121.4737, timezone: 'Asia/Shanghai' };
  const API_URL = 'https://api.open-meteo.com/v1/forecast';
  const WEATHER_TYPES = {
    0: ['晴', 'clear', '☀'], 1: ['大部晴朗', 'clear', '🌤'], 2: ['局部多云', 'cloudy', '⛅'], 3: ['多云', 'cloudy', '☁'],
    45: ['雾', 'cloudy', '🌫'], 48: ['雾凇', 'cloudy', '🌫'], 51: ['小毛毛雨', 'rain', '🌦'], 53: ['毛毛雨', 'rain', '🌦'], 55: ['较强毛毛雨', 'rain', '🌧'],
    56: ['冻毛毛雨', 'rain', '🌧'], 57: ['强冻毛毛雨', 'rain', '🌧'], 61: ['小雨', 'rain', '🌦'], 63: ['中雨', 'rain', '🌧'], 65: ['大雨', 'rain', '🌧'],
    66: ['冻雨', 'rain', '🌧'], 67: ['强冻雨', 'rain', '🌧'], 71: ['小雪', 'rain', '🌨'], 73: ['中雪', 'rain', '🌨'], 75: ['大雪', 'rain', '🌨'], 77: ['雪粒', 'rain', '🌨'],
    80: ['阵雨', 'rain', '🌦'], 81: ['较强阵雨', 'rain', '🌧'], 82: ['强阵雨', 'rain', '⛈'], 85: ['阵雪', 'rain', '🌨'], 86: ['强阵雪', 'rain', '🌨'],
    95: ['雷暴', 'rain', '⛈'], 96: ['雷暴伴冰雹', 'rain', '⛈'], 99: ['强雷暴伴冰雹', 'rain', '⛈']
  };
  const WIND_DIRS = ['北', '东北', '东', '东南', '南', '西南', '西', '西北'];

  function weatherType(code) {
    return WEATHER_TYPES[Number(code)] || ['未知', 'cloudy', '—'];
  }
  function windLevel(speedKmh) {
    const s = Number(speedKmh);
    if (!Number.isFinite(s)) return 0;
    if (s < 1) return 0;
    if (s < 5) return 1;
    if (s < 11) return 2;
    if (s < 19) return 3;
    if (s < 28) return 4;
    if (s < 38) return 5;
    if (s < 49) return 6;
    if (s < 61) return 7;
    return 8;
  }
  function windDirection(degrees) {
    const d = Number(degrees);
    if (!Number.isFinite(d)) return '—';
    return WIND_DIRS[Math.floor((d + 22.5) / 45) % 8];
  }
  function num(value, fallback = null) {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }
  function formatUpdatedAt(iso) {
    try {
      return new Intl.DateTimeFormat('zh-CN', {
        timeZone: SHANGHAI.timezone, year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
      }).format(new Date(iso));
    } catch (_) {
      return String(iso || '未知');
    }
  }
  function formatWind(speed) {
    const s = num(speed);
    return s == null ? '—' : `${Math.round(s)} km/h`;
  }
  function formatPercent(value) {
    const n = num(value);
    return n == null ? '—' : `${Math.round(n)}%`;
  }
  function parseLiveResponse(data) {
    const current = data.current || {};
    const daily = data.daily || {};
    const dates = Array.isArray(daily.time) ? daily.time : [];
    if (dates.length !== 7) throw new Error('Open-Meteo 未返回完整的 7 日数据。');

    const forecast = dates.map((date, i) => {
      const [label, kind, icon] = weatherType(daily.weather_code?.[i]);
      const min = num(daily.temperature_2m_min?.[i]);
      const max = num(daily.temperature_2m_max?.[i]);
      const wind = num(daily.wind_speed_10m_max?.[i]);
      return {
        date,
        weather: label,
        weatherType: kind,
        icon,
        tempMin: min == null ? '—' : Math.round(min),
        tempMax: max == null ? '—' : Math.round(max),
        windDirection: windDirection(daily.wind_direction_10m_dominant?.[i]),
        windLevel: windLevel(wind),
        windSpeed: wind == null ? null : Math.round(wind),
        precipitationProbability: num(daily.precipitation_probability_max?.[i]),
        precipitation: num(daily.precipitation_sum?.[i]),
        sunrise: daily.sunrise?.[i] || '',
        sunset: daily.sunset?.[i] || ''
      };
    });

    return {
      forecast,
      current: {
        time: current.time || '',
        temperature: num(current.temperature_2m),
        apparentTemperature: num(current.apparent_temperature),
        humidity: num(current.relative_humidity_2m),
        weatherCode: num(current.weather_code),
        weather: weatherType(current.weather_code)[0],
        icon: weatherType(current.weather_code)[2],
        windSpeed: num(current.wind_speed_10m),
        windDirection: windDirection(current.wind_direction_10m),
        isDay: num(current.is_day, 1) === 1
      },
      updatedAt: new Date().toISOString(),
      source: 'Open-Meteo',
      sourceUrl: API_URL
    };
  }

  async function fetchLive() {
    const params = new URLSearchParams({
      latitude: String(SHANGHAI.latitude),
      longitude: String(SHANGHAI.longitude),
      current: [
        'temperature_2m', 'relative_humidity_2m', 'apparent_temperature', 'is_day',
        'weather_code', 'wind_speed_10m', 'wind_direction_10m'
      ].join(','),
      daily: [
        'weather_code', 'temperature_2m_max', 'temperature_2m_min',
        'wind_direction_10m_dominant', 'wind_speed_10m_max',
        'precipitation_probability_max', 'precipitation_sum', 'sunrise', 'sunset'
      ].join(','),
      forecast_days: '7',
      timezone: SHANGHAI.timezone,
      temperature_unit: 'celsius',
      wind_speed_unit: 'kmh',
      precipitation_unit: 'mm'
    });
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 7000);
    let response;
    try {
      response = await fetch(`${API_URL}?${params.toString()}`, {
        method: 'GET',
        headers: { Accept: 'application/json' },
        cache: 'no-store',
        signal: controller.signal
      });
    } finally {
      clearTimeout(timeout);
    }
    if (!response.ok) throw new Error(`天气 API 请求失败（HTTP ${response.status}）。`);
    return parseLiveResponse(await response.json());
  }

  function fallbackWeather() {
    const saved = AppState.externalData.weather;
    if (!saved || !Array.isArray(saved.forecast)) return null;
    return {
      ...saved,
      forecast: saved.forecast,
      current: saved.current || null,
      source: saved.source || '本地快照',
      updatedAt: AppState.externalData.updatedAt || saved.updatedAt || ''
    };
  }

  function applyWeather(data) {
    AppState.externalData.weather = data;
    AppState.externalData.updatedAt = data.updatedAt || AppState.externalData.updatedAt;
    AppState.externalData.sourceStatus = 'ok';
  }

  window.WeatherData = { fetchLive, parseLiveResponse };

  window.WeatherPage = {
    selectedDate: null,
    liveLoaded: false,
    async render(forceRefresh = false) {
      let liveError = '';
      if (forceRefresh || !this.liveLoaded) {
        try {
          const live = await fetchLive();
          applyWeather(live);
          this.liveLoaded = true;
        } catch (error) {
          console.warn('[Weather] live API unavailable, using local fallback:', error);
          this.liveLoaded = true;
          liveError = error?.message || '实时天气获取失败';
        }
      }

      const weather = AppState.externalData.weather || fallbackWeather();
      const days = weather?.forecast || [];
      const selected = this.selectedDate && days.some(d => d.date === this.selectedDate) ? this.selectedDate : days[0]?.date;
      this.selectedDate = selected;
      const day = days.find(d => d.date === selected);
      const current = weather?.current || null;
      const badge = days.length ? `实时来源：${AppUtils.escapeHtml(weather?.source || 'Open-Meteo')}` : '暂无数据';
      const statusText = liveError
        ? `实时天气获取失败，当前显示本地快照${AppState.externalData.updatedAt ? `（${AppUtils.escapeHtml(formatUpdatedAt(AppState.externalData.updatedAt))}）` : ''}。`
        : '';

      document.getElementById('app').innerHTML = `
        <div class="card">
          <div class="card-header">
            <div><strong>未来 7 天</strong><div class="muted">自动获取实时天气 · 天气仅作为观鸟决策辅助</div></div>
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;justify-content:flex-end"><span class="badge ${days.length ? 'on':''}">${badge}</span><button class="button small" id="refresh-weather">刷新</button></div>
          </div>
          <div class="card-body">
            ${statusText ? `<div class="muted" style="margin-bottom:12px">${statusText}</div>` : ''}
            ${current ? `<div class="weather-live" style="margin:0 0 16px"><div class="card-body"><div class="weather-summary"><span class="weather-icon">${current.icon || '—'}</span><div><strong style="font-size:24px">${current.temperature == null ? '—' : `${Math.round(current.temperature)}°C`}</strong><div>${AppUtils.escapeHtml(current.weather)} · 体感 ${current.apparentTemperature == null ? '—' : `${Math.round(current.apparentTemperature)}°C`}</div><div class="muted" style="font-size:12px;margin-top:4px">湿度 ${formatPercent(current.humidity)} · ${AppUtils.escapeHtml(current.windDirection)}风 ${formatWind(current.windSpeed)}</div><div class="muted" style="font-size:12px;margin-top:3px">${current.time ? `实况时间 ${AppUtils.escapeHtml(formatUpdatedAt(current.time))}` : ''}</div></div></div></div></div>` : ''}
            <div class="grid" style="grid-template-columns:repeat(7,minmax(120px,1fr));overflow:auto;padding-bottom:6px">
              ${days.map(d => `<button class="button weather-day ${d.date===selected?'primary':''}" data-date="${AppUtils.escapeHtml(d.date)}"><div>${AppUtils.escapeHtml(d.date.slice(5))}</div><div style="font-size:25px;margin:8px 0">${d.icon || '—'}</div><strong>${d.tempMin}–${d.tempMax}°</strong><div class="muted" style="font-size:12px;margin-top:5px">${AppUtils.escapeHtml(d.weather)}</div><div class="muted" style="font-size:12px">${AppUtils.escapeHtml(d.windDirection)} ${d.windLevel}级</div>${d.precipitationProbability == null ? '' : `<div class="muted" style="font-size:12px">降水 ${Math.round(d.precipitationProbability)}%</div>`}</button>`).join('')}
            </div>
          </div>
        </div>
        <div class="card" style="margin-top:18px">
          <div class="card-header"><strong>${day ? AppUtils.escapeHtml(day.date) : '天气详情'}</strong></div>
          <div class="card-body">${day ? `<div class="grid grid-3"><div><div class="muted">温度</div><strong>${day.tempMin}–${day.tempMax}°C</strong></div><div><div class="muted">风向风力</div><strong>${AppUtils.escapeHtml(day.windDirection)} ${day.windLevel}级${day.windSpeed == null ? '' : `（${day.windSpeed} km/h）`}</strong></div><div><div class="muted">天气</div><strong>${AppUtils.escapeHtml(day.weather)}</strong></div></div><div class="grid grid-3" style="margin-top:16px"><div><div class="muted">最高降水概率</div><strong>${day.precipitationProbability == null ? '—' : `${Math.round(day.precipitationProbability)}%`}</strong></div><div><div class="muted">预计降水量</div><strong>${day.precipitation == null ? '—' : `${day.precipitation.toFixed(1)} mm`}</strong></div><div><div class="muted">日出 / 日落</div><strong>${day.sunrise ? AppUtils.escapeHtml(formatUpdatedAt(day.sunrise).slice(11,16)) : '—'} / ${day.sunset ? AppUtils.escapeHtml(formatUpdatedAt(day.sunset).slice(11,16)) : '—'}</strong></div></div><div class="advice" style="margin-top:18px">${AppUtils.escapeHtml(AppUtils.generateBirdingAdvice(day))}</div>` : '<div class="empty">暂无天气数据。</div>'}</div>
        </div>`;

      document.getElementById('refresh-weather')?.addEventListener('click', async () => {
        const btn = document.getElementById('refresh-weather');
        if (!btn) return;
        btn.disabled = true;
        btn.textContent = '获取中…';
        await this.render(true);
      });
      document.querySelectorAll('.weather-day').forEach(btn => btn.addEventListener('click', async () => {
        this.selectedDate = btn.dataset.date;
        await this.render(false);
      }));
    }
  };
})();
