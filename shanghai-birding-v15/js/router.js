(function () {
  const pageMap = {
    '/home': () => HomePage.render(), '/weather': () => WeatherPage.render(), '/hotspots': () => HotspotsPage.render(), '/records': () => RecordsPage.render(), '/lexicon': () => LexiconPage.render(), '/settings': () => SettingsPage.render()
  };
  function current() { return window.location.hash.replace(/^#/, '') || '/home'; }
  async function navigate(path) {
    const normalized = pageMap[path] ? path : '/home';
    if (window.location.hash !== `#${normalized}`) { window.location.hash = normalized; return; }
    const meta = AppConstants.ROUTES[normalized];
    Sidebar.render(normalized);
    document.getElementById('page-header').innerHTML = `<div class="page-kicker">${AppUtils.escapeHtml(meta.kicker)}</div><h1 class="page-title">${AppUtils.escapeHtml(meta.title)}</h1>`;
    document.getElementById('app').innerHTML = '<div class="empty">正在加载…</div>';
    await pageMap[normalized]();
  }
  window.Router = { current, navigate };
})();
