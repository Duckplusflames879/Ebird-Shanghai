(function () {
  function confirmAction(title, message) {
    return new Promise(resolve => {
      const root = document.getElementById('modal-root');
      root.innerHTML = `<div class="modal-backdrop"><div class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><div class="modal-header"><strong id="modal-title">${AppUtils.escapeHtml(title)}</strong><button class="button small" data-close>关闭</button></div><div class="modal-body">${AppUtils.escapeHtml(message)}</div><div class="modal-footer"><button class="button" data-close>取消</button><button class="button danger" data-confirm>确认</button></div></div></div>`;
      const close = value => { root.innerHTML=''; resolve(value); };
      root.querySelectorAll('[data-close]').forEach(el => el.addEventListener('click', () => close(false)));
      root.querySelector('[data-confirm]').addEventListener('click', () => close(true));
    });
  }
  function showFormModal(title, html, onReady, onSubmit) {
    return new Promise(resolve => {
      const root = document.getElementById('modal-root');
      root.innerHTML = `<div class="modal-backdrop"><div class="modal" role="dialog" aria-modal="true"><div class="modal-header"><strong>${AppUtils.escapeHtml(title)}</strong><button class="button small" data-close>关闭</button></div><div class="modal-body">${html}</div><div class="modal-footer"><button class="button" data-cancel>取消</button><button class="button primary" data-submit>保存</button></div></div></div>`;
      const modal = root.querySelector('.modal');
      const submitButton = root.querySelector('[data-submit]');
      let submitting = false;
      const close = value => { root.innerHTML=''; resolve(value); };
      root.querySelectorAll('[data-close], [data-cancel]').forEach(el => el.addEventListener('click', () => close(null)));
      submitButton.addEventListener('click', async () => {
        if (submitting || !modal.isConnected) return;
        submitting = true;
        submitButton.disabled = true;
        const values = Object.fromEntries(new FormData(modal.querySelector('form')));
        try {
          const result = onSubmit ? await onSubmit(values, modal, close) : { values };
          if (!modal.isConnected) return;
          if (result === false) {
            submitting = false;
            submitButton.disabled = false;
            return;
          }
          close(result && Object.prototype.hasOwnProperty.call(result, 'values') ? result : { values });
        } catch (error) {
          console.error(error);
          if (modal.isConnected) {
            submitting = false;
            submitButton.disabled = false;
          }
        }
      });
      if (onReady) onReady(modal, close);
    });
  }
  window.AppModal = { confirmAction, showFormModal };
})();
