/**
 * صفحه دوره‌ها — جستجوی هوشمند، پیشنهاد و پرش به کارت
 */
(function() {
  'use strict';

  var config = window.PAGE_CONFIG || {};
  var SEL = {
    searchInput: '#courses-search-input',
    grid: '#courses-grid',
    wrapper: '#courses-content-wrapper',
    card: '.cr-card',
    emptyMsg: '#courses-search-empty',
    suggestPanel: '#courses-suggest-panel',
    didYouMean: '#courses-did-you-mean',
    jump: '[data-cr-jump]',
    highlight: 'is-highlight',
    hidden: 'is-hidden',
    loading: 'is-loading'
  };

  var SUGGEST_DEBOUNCE_MS = 140;
  var SEARCH_DEBOUNCE_MS = 220;
  var MIN_SEARCH_LEN = 2;
  var SEARCH_CACHE_MAX = 32;

  function escapeHtml(str) {
    var el = document.createElement('div');
    el.textContent = str || '';
    return el.innerHTML;
  }

  function initSearch() {
    var input = document.querySelector(SEL.searchInput);
    var grid = document.querySelector(SEL.grid);
    var wrapper = document.querySelector(SEL.wrapper);
    var emptyMsg = document.querySelector(SEL.emptyMsg);
    var suggestPanel = document.querySelector(SEL.suggestPanel);
    var didYouMeanEl = document.querySelector(SEL.didYouMean);
    if (!input || !grid || !wrapper) return;

    var searchUrl = config.coursesSearchUrl || '';
    var suggestUrl = config.coursesSuggestUrl || '';
    var activeCountry = config.coursesActiveCountry || '';

    var cards = Array.prototype.slice.call(grid.querySelectorAll(SEL.card));
    var slugSet = {};
    cards.forEach(function(card) {
      var slug = card.getAttribute('data-course-slug') || '';
      if (slug) slugSet[slug] = card;
    });

    var suggestTimer;
    var filterTimer;
    var highlightIndex = -1;
    var suggestEngaged = false;
    var isLoading = false;
    var suggestAbort = null;
    var searchAbort = null;
    var searchCache = {};

    function setLoading(on) {
      isLoading = on;
      wrapper.classList.toggle(SEL.loading, on);
    }

    function buildUrl(base, q) {
      var params = [];
      if (q) params.push('q=' + encodeURIComponent(q));
      if (activeCountry) params.push('country=' + encodeURIComponent(activeCountry));
      return base + (params.length ? '?' + params.join('&') : '');
    }

    function showDidYouMean(term) {
      if (!didYouMeanEl) return;
      if (!term) {
        didYouMeanEl.hidden = true;
        didYouMeanEl.innerHTML = '';
        return;
      }
      didYouMeanEl.innerHTML =
        'آیا منظورتان <button type="button" class="faq-page__did-you-mean-link">' +
        escapeHtml(term) + '</button> است؟';
      didYouMeanEl.hidden = false;
      var btn = didYouMeanEl.querySelector('.faq-page__did-you-mean-link');
      if (btn) {
        btn.addEventListener('click', function() {
          input.value = term;
          hideSuggest();
          applyFilter(true);
        });
      }
    }

    function applyVisibility(slugs, didYouMean) {
      var q = (input.value || '').trim();
      var allow = null;
      if (q.length >= MIN_SEARCH_LEN && slugs) {
        allow = {};
        slugs.forEach(function(slug) {
          allow[slug] = true;
        });
      }

      var visible = 0;
      cards.forEach(function(card) {
        var slug = card.getAttribute('data-course-slug') || '';
        var show = !allow || (slug && allow[slug]);
        card.classList.toggle(SEL.hidden, !show);
        if (show) visible += 1;
      });

      if (emptyMsg) {
        emptyMsg.hidden = !q || q.length < MIN_SEARCH_LEN || visible > 0;
      }
      showDidYouMean(didYouMean && q ? didYouMean : '');
    }

    function cacheKey(q) {
      return (activeCountry || '') + '|' + q;
    }

    function applyFilter(scrollToFirst) {
      var q = (input.value || '').trim();
      if (q.length === 1) return;

      if (!q || q.length < MIN_SEARCH_LEN) {
        showDidYouMean('');
        applyVisibility(null, '');
        return;
      }

      var key = cacheKey(q);
      if (searchCache[key]) {
        var cached = searchCache[key];
        applyVisibility(cached.slugs, cached.did_you_mean);
        if (scrollToFirst && cached.slugs && cached.slugs[0]) {
          scrollToCard(cached.slugs[0]);
        }
        return;
      }

      if (!searchUrl) {
        applyVisibility(null, '');
        return;
      }

      if (searchAbort) searchAbort.abort();
      searchAbort = typeof AbortController !== 'undefined' ? new AbortController() : null;
      var fetchOpts = { headers: { 'X-Requested-With': 'XMLHttpRequest' } };
      if (searchAbort) fetchOpts.signal = searchAbort.signal;

      setLoading(true);
      fetch(buildUrl(searchUrl, q), fetchOpts)
        .then(function(r) { return r.json(); })
        .then(function(data) {
          if (!data.ok) return;
          var entry = {
            slugs: data.slugs || [],
            did_you_mean: (data.did_you_mean || '').trim()
          };
          searchCache[key] = entry;
          var keys = Object.keys(searchCache);
          if (keys.length > SEARCH_CACHE_MAX) {
            delete searchCache[keys[0]];
          }
          applyVisibility(entry.slugs, entry.did_you_mean);
          if (scrollToFirst && entry.slugs[0]) {
            scrollToCard(entry.slugs[0]);
          }
        })
        .catch(function(err) {
          if (err && err.name === 'AbortError') return;
        })
        .finally(function() {
          setLoading(false);
        });
    }

    function renderSuggest(items, smart) {
      if (!suggestPanel) return;
      if (!items || !items.length) {
        suggestPanel.hidden = true;
        suggestPanel.innerHTML = '';
        return;
      }
      var html = '';
      if (smart) {
        html += '<div class="faq-page__suggest-head">پیشنهاد هوشمند</div>';
      }
      items.forEach(function(item, i) {
        var tag = item.smart_match
          ? '<span class="faq-page__suggest-tag">تطابق بالا</span>'
          : '';
        html +=
          '<button type="button" class="faq-page__suggest-item" role="option" data-index="' + i + '">' +
          '<span class="faq-page__suggest-q">' + escapeHtml(item.title) + tag + '</span>' +
          (item.country ? '<span class="faq-page__suggest-cat">' + escapeHtml(item.country) + '</span>' : '') +
          '</button>';
      });
      suggestPanel.innerHTML = html;
      suggestPanel.hidden = false;
      highlightIndex = -1;

      suggestPanel.querySelectorAll('.faq-page__suggest-item').forEach(function(btn) {
        btn.addEventListener('click', function() {
          var idx = parseInt(btn.getAttribute('data-index'), 10);
          if (items[idx]) {
            input.value = items[idx].title;
            suggestPanel.hidden = true;
            applyFilter(true);
          }
        });
      });
    }

    function hideSuggest() {
      if (!suggestPanel) return;
      suggestPanel.hidden = true;
      suggestPanel.innerHTML = '';
      highlightIndex = -1;
    }

    function fetchSuggest() {
      if (!suggestEngaged || !suggestUrl) return;

      var q = (input.value || '').trim();
      if (q.length < MIN_SEARCH_LEN) {
        hideSuggest();
        if (suggestAbort) {
          suggestAbort.abort();
          suggestAbort = null;
        }
        return;
      }

      if (suggestAbort) suggestAbort.abort();
      suggestAbort = typeof AbortController !== 'undefined' ? new AbortController() : null;
      var fetchOpts = { headers: { 'X-Requested-With': 'XMLHttpRequest' } };
      if (suggestAbort) fetchOpts.signal = suggestAbort.signal;

      fetch(buildUrl(suggestUrl, q), fetchOpts)
        .then(function(r) { return r.json(); })
        .then(function(data) {
          if (data.ok && data.suggestions) {
            renderSuggest(data.suggestions, data.smart);
          }
        })
        .catch(function(err) {
          if (err && err.name === 'AbortError') return;
        });
    }

    var searchField = input.closest('.faq-page__search-field');
    if (searchField) {
      searchField.addEventListener('pointerdown', function() {
        suggestEngaged = true;
        var q = (input.value || '').trim();
        if (q.length >= MIN_SEARCH_LEN) {
          clearTimeout(suggestTimer);
          suggestTimer = setTimeout(fetchSuggest, SUGGEST_DEBOUNCE_MS);
        }
      });
    }

    input.addEventListener('input', function() {
      clearTimeout(suggestTimer);
      clearTimeout(filterTimer);
      var q = (input.value || '').trim();
      if (!q) {
        hideSuggest();
        showDidYouMean('');
        applyVisibility(null, '');
        return;
      }
      if (q.length >= MIN_SEARCH_LEN) {
        if (suggestEngaged) {
          suggestTimer = setTimeout(fetchSuggest, SUGGEST_DEBOUNCE_MS);
        }
        filterTimer = setTimeout(function() { applyFilter(false); }, SEARCH_DEBOUNCE_MS);
      } else {
        hideSuggest();
        applyVisibility(null, '');
      }
    });

    input.addEventListener('search', function() {
      applyFilter(true);
    });

    input.addEventListener('keydown', function(e) {
      if (!suggestPanel || suggestPanel.hidden) {
        if (e.key === 'Enter') {
          e.preventDefault();
          applyFilter(true);
        }
        return;
      }
      var items = suggestPanel.querySelectorAll('.faq-page__suggest-item');
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        highlightIndex = Math.min(highlightIndex + 1, items.length - 1);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        highlightIndex = Math.max(highlightIndex - 1, 0);
      } else if (e.key === 'Enter' && highlightIndex >= 0) {
        e.preventDefault();
        items[highlightIndex].click();
        return;
      } else if (e.key === 'Escape') {
        suggestPanel.hidden = true;
        return;
      } else {
        return;
      }
      items.forEach(function(el, i) {
        el.classList.toggle('is-highlighted', i === highlightIndex);
      });
    });

    document.addEventListener('click', function(e) {
      if (!suggestPanel || suggestPanel.hidden) return;
      if (e.target.closest('.faq-page__search-field')) return;
      hideSuggest();
    });

  }

  function scrollToCard(slug) {
    if (!slug) return;
    var el = document.getElementById('course-' + slug);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    el.classList.remove(SEL.highlight);
    void el.offsetWidth;
    el.classList.add(SEL.highlight);
    window.setTimeout(function() {
      el.classList.remove(SEL.highlight);
    }, 1400);
  }

  function initJump() {
    document.querySelectorAll(SEL.jump).forEach(function(btn) {
      btn.addEventListener('click', function() {
        scrollToCard(btn.getAttribute('data-cr-jump'));
      });
    });
  }

  function init() {
    initSearch();
    initJump();
    var hash = window.location.hash;
    if (hash && hash.indexOf('course-') === 1) {
      scrollToCard(hash.slice(7));
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
