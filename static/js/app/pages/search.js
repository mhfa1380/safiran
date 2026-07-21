/**
 * صفحه جستجوی سراسری — فیلتر نوع محتوا + پیشنهاد زنده
 */
(function() {
  'use strict';

  var cfg = window.PAGE_CONFIG || {};
  var suggestUrl = cfg.siteSuggestUrl || '';
  var DEBOUNCE_MS = 280;
  var MIN_CHARS = 2;

  function escapeHtml(str) {
    var el = document.createElement('div');
    el.textContent = str || '';
    return el.innerHTML;
  }

  function initFilters() {
    var groups = document.querySelectorAll('[data-search-group]');
    var buttons = document.querySelectorAll('[data-search-filter]');
    var emptyMsg = document.getElementById('search-page-filter-empty');
    if (!buttons.length || !groups.length) return;

    function applyFilter(type) {
      var visible = 0;
      groups.forEach(function(group) {
        var show = type === 'all' || group.getAttribute('data-search-group') === type;
        group.classList.toggle('is-filtered-out', !show);
        if (show) visible += 1;
      });
      buttons.forEach(function(btn) {
        btn.classList.toggle('is-active', btn.getAttribute('data-search-filter') === type);
      });
      if (emptyMsg) {
        emptyMsg.hidden = visible > 0;
      }
    }

    buttons.forEach(function(btn) {
      btn.addEventListener('click', function() {
        applyFilter(btn.getAttribute('data-search-filter') || 'all');
      });
    });
  }

  function initSuggest() {
    var input = document.getElementById('site-search-page-input');
    var panel = document.getElementById('search-page-suggest');
    var clearBtn = document.getElementById('search-page-clear');
    if (!input || !panel || !suggestUrl) return;

    var timer;
    var abortCtrl;
    var activeIndex = -1;

    function setPanelOpen(open) {
      panel.hidden = !open;
      input.setAttribute('aria-expanded', open ? 'true' : 'false');
    }

    function getItems() {
      return Array.prototype.slice.call(panel.querySelectorAll('.search-page__suggest-item'));
    }

    function renderDidYouMean(didYouMean, q) {
      if (!didYouMean || !q || didYouMean.toLowerCase() === q.toLowerCase()) {
        return '';
      }
      var searchUrl = (cfg.siteSearchUrl || '/search/') + '?q=' + encodeURIComponent(didYouMean);
      return (
        '<p class="search-page__suggest-did-you-mean" role="note">' +
        'آیا منظورتان <a href="' + escapeHtml(searchUrl) + '">«' + escapeHtml(didYouMean) + '»</a> است؟' +
        '</p>'
      );
    }

    function renderSuggest(data, q) {
      var items = [];
      var didYouMean = (data && data.did_you_mean) ? data.did_you_mean : '';
      if (data && data.ok) {
        if (data.suggestions && data.suggestions.length) {
          items = data.suggestions.slice(0, 8);
        } else if (data.groups) {
          data.groups.forEach(function(group) {
            (group.items || []).forEach(function(item) {
              if (items.length < 8) items.push(item);
            });
          });
        }
      }

      if (!items.length) {
        panel.innerHTML = (q ? renderDidYouMean(didYouMean, q) : '') +
          (q ? '<p class="search-page__suggest-empty">پیشنهادی یافت نشد</p>' : '');
        setPanelOpen(!!q);
        activeIndex = -1;
        return;
      }

      var html = renderDidYouMean(didYouMean, q);
      items.forEach(function(item, i) {
        html += '<a class="search-page__suggest-item" role="option" id="search-suggest-' + i + '" href="' + escapeHtml(item.url) + '">';
        html += '<span class="search-page__suggest-title">' + escapeHtml(item.title) + '</span>';
        if (item.subtitle) {
          html += '<span class="search-page__suggest-meta">' + escapeHtml(item.subtitle) + '</span>';
        }
        html += '</a>';
      });
      panel.innerHTML = html;
      setPanelOpen(true);
      activeIndex = -1;
    }

    function fetchSuggest(q) {
      if (abortCtrl) abortCtrl.abort();
      if (!q || q.length < MIN_CHARS) {
        panel.innerHTML = '';
        setPanelOpen(false);
        return;
      }
      abortCtrl = new AbortController();
      var url = suggestUrl + (suggestUrl.indexOf('?') >= 0 ? '&' : '?') + 'q=' + encodeURIComponent(q);
      fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin',
        signal: abortCtrl.signal
      })
        .then(function(res) { return res.json(); })
        .then(function(data) { renderSuggest(data, q); })
        .catch(function(err) {
          if (err && err.name === 'AbortError') return;
          panel.innerHTML = '<p class="search-page__suggest-empty">خطا در بارگذاری پیشنهاد</p>';
          setPanelOpen(true);
        });
    }

    function scheduleFetch() {
      clearTimeout(timer);
      var q = input.value.trim();
      if (clearBtn) clearBtn.hidden = !q;
      timer = setTimeout(function() { fetchSuggest(q); }, DEBOUNCE_MS);
    }

    input.addEventListener('input', scheduleFetch);
    input.addEventListener('focus', function() {
      var q = input.value.trim();
      if (q.length >= MIN_CHARS) fetchSuggest(q);
    });

    panel.addEventListener('mousedown', function(e) {
      e.preventDefault();
    });

    if (clearBtn) {
      clearBtn.addEventListener('click', function() {
        input.value = '';
        clearBtn.hidden = true;
        panel.innerHTML = '';
        setPanelOpen(false);
        input.focus();
      });
    }

    input.addEventListener('keydown', function(e) {
      var items = getItems();
      if (e.key === 'ArrowDown' && items.length) {
        e.preventDefault();
        activeIndex = Math.min(activeIndex + 1, items.length - 1);
        items.forEach(function(el, i) { el.classList.toggle('is-active', i === activeIndex); });
      } else if (e.key === 'ArrowUp' && items.length) {
        e.preventDefault();
        activeIndex = Math.max(activeIndex - 1, 0);
        items.forEach(function(el, i) { el.classList.toggle('is-active', i === activeIndex); });
      } else if (e.key === 'Enter' && activeIndex >= 0 && items[activeIndex]) {
        e.preventDefault();
        window.location.href = items[activeIndex].href;
      } else if (e.key === 'Escape') {
        setPanelOpen(false);
      }
    });

    document.addEventListener('click', function(e) {
      if (!panel.contains(e.target) && e.target !== input) {
        setPanelOpen(false);
      }
    });
  }

  function boot() {
    initFilters();
    initSuggest();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
