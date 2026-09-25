(function () {
  let timer;
  function show(message) {
    const root = document.getElementById('toast-root');
    root.innerHTML = `<div class="toast">${AppUtils.escapeHtml(message)}</div>`;
    clearTimeout(timer); timer = setTimeout(() => { root.innerHTML=''; }, 1800);
  }
  window.AppToast = { show };
})();
