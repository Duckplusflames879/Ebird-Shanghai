(function () {
  const items = [
    ['/home','⌂','首页'], ['/weather','☁','天气'], ['/hotspots','⌖','观鸟点'], ['/records','▤','我的记录'], ['/lexicon','▦','图鉴'], ['/settings','⚙','设置']
  ];
  function render(path) {
    document.getElementById('sidebar').innerHTML = `<div class="brand"><div class="brand-mark">鸟</div><div class="brand-title">上海本地<br>观鸟辅助系统</div></div><nav class="nav">${items.map(([href,icon,label])=>`<a class="nav-link ${href===path?'active':''}" href="#${href}" data-route="${href}"><span class="nav-icon">${icon}</span><span>${label}</span></a>`).join('')}</nav>`;
  }
  window.Sidebar = { render };
})();
