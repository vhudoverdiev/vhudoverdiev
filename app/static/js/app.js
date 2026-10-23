(() => {
  const sidebar = document.getElementById('sidebar');
  const menuButton = document.querySelector('.mobile-menu');
  const closeButton = document.querySelector('.sidebar-toggle');
  if (sidebar && menuButton) {
    menuButton.addEventListener('click', () => sidebar.classList.add('sidebar-open'));
    closeButton?.addEventListener('click', () => sidebar.classList.remove('sidebar-open'));
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') sidebar.classList.remove('sidebar-open');
    });
  }
  document.querySelectorAll('.flash-close').forEach((button) => {
    button.addEventListener('click', () => button.closest('.flash')?.remove());
  });
  document.querySelectorAll('[data-copy-target]').forEach((button) => {
    button.addEventListener('click', async () => {
      const value = document.getElementById(button.dataset.copyTarget)?.textContent?.trim();
      if (!value) return;
      try {
        await navigator.clipboard.writeText(value);
        button.textContent = 'Скопировано';
      } catch {
        button.textContent = 'Выделите пароль';
        const range = document.createRange();
        range.selectNodeContents(document.getElementById(button.dataset.copyTarget));
        window.getSelection()?.removeAllRanges();
        window.getSelection()?.addRange(range);
      }
    });
  });
  document.querySelectorAll('.password-toggle').forEach((button) => {
    button.addEventListener('click', () => {
      const input = button.closest('.password-wrap')?.querySelector('input');
      if (!input) return;
      const visible = input.type === 'password';
      input.type = visible ? 'text' : 'password';
      button.textContent = visible ? 'Скрыть' : 'Показать';
      button.setAttribute('aria-label', visible ? 'Скрыть пароль' : 'Показать пароль');
    });
  });
})();
