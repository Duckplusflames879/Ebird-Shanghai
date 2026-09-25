(function () {
  const ENDPOINT = '/__auto_update';
  let runPromise = null;
  let started = false;

  function isLocalAutoUpdateAvailable() {
    // Only the standalone Python launcher (start_app.py) serves /__auto_update.
    // When embedded under Birds Remain (/apps/ebirds-shanghai/), skip quietly.
    if (location.protocol !== 'http:' && location.protocol !== 'https:') return false;
    if (/\/apps\/ebirds-shanghai\//.test(location.pathname)) return false;
    return true;
  }

  async function reloadExternalData() {
    const response = await fetch('data/latest_data.js?auto_update=' + Date.now(), {
      cache: 'no-store',
      credentials: 'same-origin'
    });
    if (!response.ok) throw new Error(`latest_data.js HTTP ${response.status}`);
    const source = await response.text();
    if (!/window\.EXTERNAL_DATA\s*=/.test(source)) throw new Error('latest_data.js has invalid format');
    new Function(source)();
    return window.EXTERNAL_DATA;
  }

  async function run(options = {}) {
    if (!isLocalAutoUpdateAvailable()) {
      return { available: false, updated: false, skipped: true };
    }
    if (runPromise && !options.force) return runPromise;
    runPromise = (async () => {
      try {
        const url = ENDPOINT + (options.force ? '?force=1' : '');
        const response = await fetch(url, {
          method: 'POST',
          cache: 'no-store',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: '{}',
          signal: AbortSignal.timeout ? AbortSignal.timeout(180000) : undefined
        });
        if (response.status === 404) {
          return { available: false, updated: false, skipped: true };
        }
        if (!response.ok) throw new Error(`auto-update HTTP ${response.status}`);
        const result = await response.json();
        if (result.success) {
          if (result.updated || options.force) await reloadExternalData();
          started = true;
        }
        return { available: true, ...result };
      } catch (error) {
        console.warn('[auto-update]', error);
        return { available: true, updated: false, skipped: false, success: false, error: String(error.message || error) };
      } finally {
        runPromise = null;
      }
    })();
    return runPromise;
  }

  window.AutoUpdater = {
    run,
    isLocalAutoUpdateAvailable,
    reloadExternalData,
    get started() { return started; }
  };
})();
