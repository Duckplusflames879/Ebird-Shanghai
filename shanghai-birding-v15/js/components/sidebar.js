(function () {
  const items = [
    ['/home','⌂','首页'], ['/weather','☁','天气'], ['/hotspots','⌖','观鸟点'], ['/records','▤','我的记录'], ['/lexicon','▦','图鉴'], ['/settings','⚙','设置']
  ];
  function render(path) {
    document.getElementById('sidebar').innerHTML = `
      <div class="brand">
        <div class="brand-mark">鸟</div>
        <div class="brand-title">上海观鸟助手<br><span style="font-size:0.72em;opacity:.85">Ebirds-Shanghai</span></div>
      </div>
      <nav class="nav">${items.map(([href,icon,label])=>`<a class="nav-link ${href===path?'active':''}" href="#${href}" data-route="${href}"><span class="nav-icon">${icon}</span><span>${label}</span></a>`).join('')}</nav>
      <footer class="sidebar-foot">
        <div>开发者: 羽尘</div>
        <div>© 2026 Pheatherdust All Rights Reserved</div>
        <div>Part of the bird data comes from eBird API</div>
        <div>eBird © Cornell Lab of Ornithology</div>
      </footer>`;
  }
  window.Sidebar = { render };
})();
