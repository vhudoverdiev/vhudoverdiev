(() => {
  const sidebar = document.getElementById('sidebar');
  const menuButton = document.querySelector('.mobile-menu');
  const closeButton = document.querySelector('.sidebar-toggle');
  const backdrop = document.querySelector('.menu-backdrop');
  const mobile = window.matchMedia('(max-width: 760px)');
  const main = document.querySelector('.main-area');
  if (sidebar && menuButton && backdrop) {
    let open = false;
    menuButton.setAttribute('aria-controls', 'sidebar');
    menuButton.setAttribute('aria-expanded', 'false');
    const setOpen = (value, restoreFocus = true) => {
      open = value && mobile.matches;
      sidebar.classList.toggle('sidebar-open', open);
      document.body.classList.toggle('menu-is-open', open);
      backdrop.hidden = !open;
      sidebar.inert = mobile.matches && !open;
      if (main) main.inert = open;
      menuButton.setAttribute('aria-expanded', String(open));
      if (open) (closeButton || sidebar.querySelector('a'))?.focus();
      else if (restoreFocus && mobile.matches) menuButton.focus();
    };
    menuButton.addEventListener('click', () => setOpen(!open));
    closeButton?.addEventListener('click', () => setOpen(false));
    backdrop.addEventListener('click', () => setOpen(false));
    sidebar.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => setOpen(false)));
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && open) setOpen(false);
      if (event.key !== 'Tab' || !open) return;
      const items = Array.from(sidebar.querySelectorAll('a[href], button, input')).filter((el) => !el.disabled && el.getClientRects().length);
      const first = items[0], last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    });
    mobile.addEventListener('change', () => setOpen(false, false));
    setOpen(false, false);
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

// Reveal the server-graded feedback before advancing; the reader can pause it.
document.querySelectorAll('[data-auto-next]').forEach((form) => {
  const delay = Number(form.dataset.autoNext);
  const timer = window.setTimeout(() => form.requestSubmit(), delay);
  form.querySelector('[data-pause-next]')?.addEventListener('click', (event) => {
    window.clearTimeout(timer);
    event.currentTarget.hidden = true;
    const notice = form.querySelector('[data-advance-notice]');
    if (notice) notice.textContent = 'Автопереход остановлен. Нажмите кнопку, когда будете готовы.';
  });
  form.addEventListener('submit', () => window.clearTimeout(timer));
});

if (document.querySelector('[data-check-heading]')) {
  const resetQuestionPosition = () => {
    document.querySelector('[data-check-heading]')?.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  };
  window.addEventListener('pageshow', resetQuestionPosition);
}
