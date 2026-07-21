/**
 * ثبت بازدید محتوا بدون وابستگی به کش HTML — الگوی سایت‌های بزرگ.
 */
(function() {
  'use strict';

  var el = document.getElementById('content-track-config');
  if (!el) return;

  var url = el.getAttribute('data-track-url');
  var id = el.getAttribute('data-track-id');
  var field = el.getAttribute('data-track-field') || 'faq_id';
  if (!url || !id) return;

  var body = new URLSearchParams();
  body.set(field, id);

  if (typeof window.fetch === 'function') {
    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: body.toString(),
      credentials: 'same-origin',
      keepalive: true
    }).catch(function() {});
  }
})();
