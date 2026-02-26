/**
 * صفحه دوره‌ها - دکمه فیلتر کردن
 */
(function() {
  'use strict';

  function initFilterToggle() {
    var btn = document.getElementById('coursesFilterToggle');
    var wrap = document.getElementById('coursesFilterWrap');
    if (!btn || !wrap) return;

    var labelShow = 'فیلتر کردن';
    var labelHide = 'بستن فیلتر';

    btn.addEventListener('click', function() {
      var isOpen = wrap.classList.toggle('is_open');
      btn.setAttribute('aria-expanded', isOpen);
      var labelEl = btn.querySelector('.courses_filter_toggle_label');
      if (labelEl) labelEl.textContent = isOpen ? labelHide : labelShow;
    });
  }

  function init() {
    initFilterToggle();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
