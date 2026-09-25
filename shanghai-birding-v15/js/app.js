(function () {
  async function renderRoute() {
    const route = Router.current();
    // Hotspots now fetch directly from eBird in the browser; the legacy local
    // auto-update bridge must never block or replace that data path.
    await Router.navigate(route);
  }
  async function init() {
    try {
      if (window.AutoUpdater) await window.AutoUpdater.run();
      await AppStateActions.load();
      await renderRoute();
    }
    catch (error) { console.error(error); document.getElementById('app').innerHTML='<div class="card empty">应用初始化失败。请检查浏览器本地存储权限。</div>'; }
  }
  window.addEventListener('hashchange', renderRoute);
  document.addEventListener('appstatechange', async () => { const route=Router.current(); if (route==='/home' || route==='/lexicon') await renderRoute(); });
  init();
})();
