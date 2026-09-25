(function () {
  function attach(input, getOptions, onSelect) {
    const wrapper = input.closest('.autocomplete');
    const menu = document.createElement('div'); menu.className='autocomplete-menu'; menu.hidden=true; wrapper.appendChild(menu);
    let options=[];
    function render() {
      options = getOptions(input.value);
      menu.innerHTML = options.slice(0, 8).map(b => `<div class="autocomplete-item" data-id="${AppUtils.escapeHtml(b.id)}"><strong>${AppUtils.escapeHtml(b.name)}</strong><div class="muted">${AppUtils.escapeHtml(b.family)} · ${AppUtils.escapeHtml(b.genus)}</div></div>`).join('');
      menu.hidden = options.length === 0;
      menu.querySelectorAll('.autocomplete-item').forEach(el => el.addEventListener('mousedown', e => { e.preventDefault(); const item=options.find(x=>x.id===el.dataset.id); if(item) onSelect(item); menu.hidden=true; }));
    }
    input.addEventListener('input', render);
    input.addEventListener('focus', render);
    input.addEventListener('blur', () => setTimeout(() => { menu.hidden=true; }, 100));
    return { refresh: render, close: () => { menu.hidden=true; } };
  }
  window.Autocomplete = { attach };
})();
