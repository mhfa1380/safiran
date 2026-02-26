/**
 * صفحه سوالات متداول - جستجو و آکاردئون
 */
(function() {
  'use strict';

  var config = window.PAGE_CONFIG || {};

  function initFaq() {
    var wrapper = document.getElementById('faq-content-wrapper');
    var searchInput = document.getElementById('faq-search-input');
    if (!wrapper || !searchInput) return;

    var faqSearchUrl = config.faqSearchUrl || '';
    var debounceTimer;

    function bindAccordion() {
      var triggers = wrapper.querySelectorAll('[data-faq-toggle]');
      triggers.forEach(function(btn) {
        btn.onclick = function() {
          var item = this.closest('.faq_item');
          var wasActive = item.classList.contains('active');
          wrapper.querySelectorAll('.faq_item').forEach(function(i) { i.classList.remove('active'); });
          wrapper.querySelectorAll('[data-faq-toggle]').forEach(function(b) { b.setAttribute('aria-expanded', 'false'); });
          if (!wasActive) {
            item.classList.add('active');
            this.setAttribute('aria-expanded', 'true');
          }
        };
      });
    }

    function doSearch() {
      var q = (searchInput.value || '').trim();
      var url = faqSearchUrl + (q ? '?q=' + encodeURIComponent(q) : '');
      if (!url) return;
      fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function(r) { return r.json(); })
        .then(function(data) {
          if (data.ok && data.html) {
            wrapper.innerHTML = data.html;
            bindAccordion();
          }
        });
    }

    searchInput.addEventListener('input', function() {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(doSearch, 280);
    });

    bindAccordion();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFaq);
  } else {
    initFaq();
  }
})();
