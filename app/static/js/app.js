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

  document.querySelectorAll('video[data-progress-url]').forEach((video) => {
    let lastSent = -1;
    const saveProgress = () => {
      if (!Number.isFinite(video.duration) || video.duration <= 0) return;
      const percent = Math.min(100, Math.floor((video.currentTime / video.duration) * 100));
      if (percent < 1 || (percent < 90 && percent - lastSent < 5) || percent <= lastSent) return;
      lastSent = percent;
      const data = new URLSearchParams({
        watched_percent: String(percent),
        csrf_token: document.querySelector('meta[name="csrf-token"]')?.content || '',
      });
      fetch(video.dataset.progressUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' },
        body: data,
      }).catch(() => { lastSent = Math.min(lastSent, percent - 5); });
    };
    video.addEventListener('timeupdate', saveProgress);
    video.addEventListener('ended', saveProgress);
  });
})();

// Keep long checks readable and prevent accidental duplicate submissions.
document.querySelectorAll('.quiz-form').forEach((form) => {
  const counter = form.querySelector('[data-answer-count]');
  const update = () => {
    if (counter) counter.textContent = String(new Set(Array.from(form.querySelectorAll('input[type="radio"]:checked'), (input) => input.name)).size);
  };
  form.addEventListener('change', update);
  update();
  form.addEventListener('submit', () => {
    const button = form.querySelector('button[type="submit"]');
    if (button) { button.disabled = true; button.textContent = 'Проверяем ответы…'; }
  });
});
