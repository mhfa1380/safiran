/**
 * صفحه رشته‌ها — جستجو، پیشنهاد هوشمند، فیلتر کشور و بارگذاری تدریجی
 */
(function() {
  'use strict';

  var config = window.PAGE_CONFIG || {};
  var SEL = {
    wrapper: '#majors-content-wrapper',
    searchInput: '#majors-search-input',
    suggestPanel: '#majors-suggest-panel',
    countryFilter: '.majors-country-filters .faq-page__filter[data-major-country]',
    navCountry: '.faq-page__nav-link[data-major-country]',
    smartTag: '.majors-smart-tag',
    jump: '[data-major-jump]',
    highlight: 'is-highlight',
    grid: '#majors-grid',
    sentinel: '#majors-load-sentinel',
    loadMore: '#majors-load-more',
    shownCount: '#majors-shown-count',
    cta: '#majors-page-cta'
  };

  function escapeHtml(str) {
    var el = document.createElement('div');
    el.textContent = str || '';
    return el.innerHTML;
  }

  function initMajors() {
    var wrapper = document.querySelector(SEL.wrapper);
    var searchInput = document.querySelector(SEL.searchInput);
    var suggestPanel = document.querySelector(SEL.suggestPanel);
    if (!wrapper || !searchInput) return;

    var searchUrl = config.majorsSearchUrl || '';
    var suggestUrl = config.majorsSuggestUrl || '';
    var activeCountry = config.majorsActiveCountry || '';
    var activeUniversity = config.majorsActiveUniversity || '';
    var pageSize = parseInt(config.majorsPageSize, 10) || 20;
    var nextOffset = parseInt(config.majorsNextOffset, 10) || 0;
    var hasMore = !!config.majorsHasMore;
    var totalCount = parseInt(config.majorsTotal, 10) || 0;

    var pageParams = (function() {
      var out = {};
      try {
        var sp = new URLSearchParams(window.location.search);
        ['target_degree', 'intent'].forEach(function(key) {
          var val = sp.get(key);
          if (val) out[key] = val;
        });
        var uni = sp.get('university');
        if (uni) {
          activeUniversity = uni;
          config.majorsActiveUniversity = activeUniversity;
        }
      } catch (e) {}
      return out;
    })();

    var suggestTimer;
    var filterTimer;
    var highlightIndex = -1;
    var suggestEngaged = false;
    var isLoading = false;
    var isLoadingMore = false;
    var infiniteEnabled = true;
    var scrollObserver = null;
    var suggestAbort = null;
    var searchAbort = null;
    var SUGGEST_DEBOUNCE_MS = 140;
    var SEARCH_DEBOUNCE_MS = 260;
    var MIN_SEARCH_LEN = 2;
    var searchResultCache = {};
    var SEARCH_CACHE_MAX = 24;

    var SEARCH_CACHE_MAX = 24;

    var worldCountries = Array.isArray(config.majorsWorldCountries) ? config.majorsWorldCountries : [];
    var worldCountryMap = {};
    worldCountries.forEach(function(item) {
      if (item && item.code) worldCountryMap[item.code] = item;
    });

    function isWorldCountry(code) {
      return !!(code && worldCountryMap[code]);
    }

    function updateWorldCountryTriggers(code) {
      var active = code === 'other' ? { code: 'other', label: 'سایر کشورها', flag: '' } : (isWorldCountry(code) ? worldCountryMap[code] : null);
      document.querySelectorAll('[data-major-country-picker]').forEach(function(btn) {
        btn.classList.toggle('is-active', !!active);
        if (active) {
          btn.setAttribute('aria-current', 'page');
        } else {
          btn.removeAttribute('aria-current');
        }
        var labelEl = btn.querySelector('.schools-world-country-trigger__label');
        if (labelEl) {
          labelEl.textContent = active ? active.label : 'سایر کشورها';
        } else if (!btn.querySelector('.faq-page__nav-flag') && !btn.querySelector('[class^="ti-"]')) {
          btn.textContent = active ? active.label : 'سایر کشورها';
        }
      });
    }

    function setCountryActive(code) {
      activeCountry = code || '';
      config.majorsActiveCountry = activeCountry;
      document.querySelectorAll(SEL.countryFilter).forEach(function(btn) {
        var c = btn.getAttribute('data-major-country') || '';
        btn.classList.toggle('is-active', c === activeCountry);
      });
      document.querySelectorAll(SEL.navCountry).forEach(function(link) {
        var c = link.getAttribute('data-major-country') || '';
        link.classList.toggle('is-active', c === activeCountry);
        if (c === activeCountry) {
          link.setAttribute('aria-current', 'page');
        } else {
          link.removeAttribute('aria-current');
        }
      });
      updateWorldCountryTriggers(activeCountry);
    }

    function buildQueryParams(q, extra) {
      var params = [];
      if (q) params.push('q=' + encodeURIComponent(q));
      if (activeCountry) params.push('country=' + encodeURIComponent(activeCountry));
      if (activeUniversity) params.push('university=' + encodeURIComponent(activeUniversity));
      Object.keys(pageParams).forEach(function(key) {
        params.push(key + '=' + encodeURIComponent(pageParams[key]));
      });
      if (extra) {
        Object.keys(extra).forEach(function(key) {
          if (extra[key] !== undefined && extra[key] !== null && extra[key] !== '') {
            params.push(key + '=' + encodeURIComponent(extra[key]));
          }
        });
      }
      return params;
    }

    function buildUrl(base, q, extra) {
      var params = buildQueryParams(q, extra);
      return base + (params.length ? '?' + params.join('&') : '');
    }

    function syncPageUrl(q) {
      if (!window.history || !window.history.replaceState) return;
      var params = buildQueryParams(q || '');
      var next = window.location.pathname + (params.length ? '?' + params.join('&') : '');
      if (next !== window.location.pathname + window.location.search) {
        window.history.replaceState(null, '', next);
      }
    }

    function getGrid() {
      return wrapper.querySelector(SEL.grid);
    }

    function getSentinel() {
      return wrapper.querySelector(SEL.sentinel);
    }

    function getLoadMoreEl() {
      return wrapper.querySelector(SEL.loadMore);
    }

    function getCta() {
      return wrapper.querySelector(SEL.cta);
    }

    function updateShownCount(shown) {
      var el = wrapper.querySelector(SEL.shownCount);
      if (el) el.textContent = String(shown);
    }

    function setCtaDeferred(deferred) {
      var cta = getCta();
      if (cta) cta.classList.toggle('faq-page__cta--deferred', !!deferred);
    }

    function setLoadingMore(on) {
      isLoadingMore = on;
      var loadMore = getLoadMoreEl();
      if (loadMore) loadMore.hidden = !on;
    }

    function setLoading(on) {
      isLoading = on;
      wrapper.classList.toggle('is-loading', on);
    }

    function findMajorCard(slug) {
      if (!slug) return null;
      return document.getElementById('major-' + slug)
        || wrapper.querySelector('[data-major-slug="' + slug + '"]');
    }

    function openMajorBySlug(slug, scroll) {
      if (scroll === undefined) scroll = true;
      var card = findMajorCard(slug);
      if (!card) return;
      card.classList.add(SEL.highlight);
      if (scroll) {
        card.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      setTimeout(function() { card.classList.remove(SEL.highlight); }, 1400);
    }

    function bindJumpButtons(root) {
      (root || document).querySelectorAll(SEL.jump).forEach(function(btn) {
        if (btn._majorsJumpBound) return;
        btn._majorsJumpBound = true;
        btn.addEventListener('click', function(e) {
          if (btn.tagName === 'A') return;
          e.preventDefault();
          openMajorBySlug(btn.getAttribute('data-major-jump'));
        });
      });
    }

    function teardownInfiniteScroll() {
      if (scrollObserver) {
        scrollObserver.disconnect();
        scrollObserver = null;
      }
    }

    function setupInfiniteScroll() {
      teardownInfiniteScroll();
      if (!infiniteEnabled || !hasMore) return;

      var sentinel = getSentinel();
      if (!sentinel) return;

      sentinel.hidden = false;

      if (!('IntersectionObserver' in window)) return;

      scrollObserver = new IntersectionObserver(
        function(entries) {
          entries.forEach(function(entry) {
            if (entry.isIntersecting) {
              loadMoreMajors();
            }
          });
        },
        { root: null, rootMargin: '240px 0px', threshold: 0 }
      );
      scrollObserver.observe(sentinel);
    }

    function syncPaginationState(data) {
      if (typeof data.has_more === 'boolean') hasMore = data.has_more;
      if (typeof data.next_offset === 'number') nextOffset = data.next_offset;
      if (typeof data.total === 'number') totalCount = data.total;
      config.majorsHasMore = hasMore;
      config.majorsNextOffset = nextOffset;
      config.majorsTotal = totalCount;

      var sentinel = getSentinel();
      if (sentinel) {
        if (hasMore && infiniteEnabled) {
          sentinel.hidden = false;
        } else {
          sentinel.hidden = true;
        }
      }
      setCtaDeferred(hasMore && infiniteEnabled);
      if (!hasMore) teardownInfiniteScroll();
      else setupInfiniteScroll();
    }

    function loadMoreMajors() {
      var q = (searchInput.value || '').trim();
      if (!infiniteEnabled || !hasMore || isLoadingMore || isLoading || q) return;

      var grid = getGrid();
      if (!grid) return;

      setLoadingMore(true);

      fetch(
        buildUrl(searchUrl, '', {
          partial: '1',
          offset: nextOffset,
          limit: pageSize
        }),
        { headers: { 'X-Requested-With': 'XMLHttpRequest' } }
      )
        .then(function(r) { return r.json(); })
        .then(function(data) {
          if (!data.ok || !data.cards_html) return;

          grid.insertAdjacentHTML('beforeend', data.cards_html);
          bindJumpButtons(grid);

          nextOffset = data.next_offset != null ? data.next_offset : nextOffset + pageSize;
          hasMore = !!data.has_more;
          if (typeof data.total === 'number') totalCount = data.total;

          updateShownCount(nextOffset);
          syncPaginationState({
            has_more: hasMore,
            next_offset: nextOffset,
            total: totalCount
          });
        })
        .catch(function() {})
        .finally(function() { setLoadingMore(false); });
    }

    function searchCacheKey(q) {
      return (activeCountry || '') + '|' + q;
    }

    function rememberSearchCache(q, data) {
      if (!q || !data || !data.html) return;
      var key = searchCacheKey(q);
      searchResultCache[key] = data;
      var keys = Object.keys(searchResultCache);
      if (keys.length > SEARCH_CACHE_MAX) {
        delete searchResultCache[keys[0]];
      }
    }

    function applySearchResult(data, q, scrollToBest) {
      if (!data || !data.html) return;
      wrapper.innerHTML = data.html;
      bindJumpButtons(wrapper);

      if (!q) {
        syncPaginationState({
          has_more: data.has_more,
          next_offset: data.next_offset,
          total: data.total
        });
        updateShownCount(data.next_offset || 0);
      } else {
        infiniteEnabled = false;
        setCtaDeferred(false);
      }

      if (scrollToBest && data.best_slug) {
        openMajorBySlug(data.best_slug);
      }
    }

    function applyFilter(scrollToBest) {
      var q = (searchInput.value || '').trim();
      if (q.length > 0 && q.length < MIN_SEARCH_LEN) return;

      if (searchAbort) {
        searchAbort.abort();
      }
      searchAbort = typeof AbortController !== 'undefined' ? new AbortController() : null;

      teardownInfiniteScroll();
      infiniteEnabled = !q;
      nextOffset = 0;
      hasMore = false;

      if (q) {
        var cached = searchResultCache[searchCacheKey(q)];
        if (cached) {
          applySearchResult(cached, q, scrollToBest);
        }
      }

      setLoading(true);
      var fetchOpts = { headers: { 'X-Requested-With': 'XMLHttpRequest' } };
      if (searchAbort) fetchOpts.signal = searchAbort.signal;

      fetch(buildUrl(searchUrl, q), fetchOpts)
        .then(function(r) { return r.json(); })
        .then(function(data) {
          if (!data.ok || !data.html) return;
          if (q) rememberSearchCache(q, data);
          applySearchResult(data, q, scrollToBest);
        })
        .catch(function(err) {
          if (err && err.name === 'AbortError') return;
        })
        .finally(function() {
          setLoading(false);
          syncPageUrl((searchInput.value || '').trim());
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
          '<button type="button" class="faq-page__suggest-item" role="option" data-index="' + i + '" data-slug="' + escapeHtml(item.slug) + '">' +
          '<span class="faq-page__suggest-q">' + escapeHtml(item.title) + tag + '</span>' +
          (item.country ? '<span class="faq-page__suggest-cat">' + escapeHtml(item.country) + '</span>' : '') +
          '</button>';
      });
      suggestPanel.innerHTML = html;
      suggestPanel.hidden = false;
      highlightIndex = -1;

      suggestPanel.querySelectorAll('.faq-page__suggest-item').forEach(function(btn) {
        btn.addEventListener('click', function() {
          searchInput.value = items[parseInt(btn.getAttribute('data-index'), 10)].title;
          suggestPanel.hidden = true;
          applyFilter(true);
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
      if (!suggestEngaged) return;

      var q = (searchInput.value || '').trim();
      if (q.length < MIN_SEARCH_LEN) {
        hideSuggest();
        if (suggestAbort) {
          suggestAbort.abort();
          suggestAbort = null;
        }
        return;
      }

      if (suggestAbort) {
        suggestAbort.abort();
      }
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

    var searchField = searchInput.closest('.faq-page__search-field');
    if (searchField) {
      searchField.addEventListener('pointerdown', function() {
        suggestEngaged = true;
        var q = (searchInput.value || '').trim();
        if (q.length >= MIN_SEARCH_LEN) {
          clearTimeout(suggestTimer);
          suggestTimer = setTimeout(fetchSuggest, SUGGEST_DEBOUNCE_MS);
        }
      });
    }

    searchInput.addEventListener('input', function() {
      clearTimeout(suggestTimer);
      clearTimeout(filterTimer);
      document.querySelectorAll(SEL.smartTag).forEach(function(t) {
        t.classList.remove('is-active');
      });
      var q = (searchInput.value || '').trim();
      if (!q) {
        hideSuggest();
        applyFilter(false);
        return;
      }
      if (q.length >= MIN_SEARCH_LEN) {
        if (suggestEngaged) {
          suggestTimer = setTimeout(fetchSuggest, SUGGEST_DEBOUNCE_MS);
        }
        filterTimer = setTimeout(function() { applyFilter(false); }, SEARCH_DEBOUNCE_MS);
      } else {
        hideSuggest();
      }
    });

    searchInput.addEventListener('keydown', function(e) {
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

    document.querySelectorAll(SEL.smartTag).forEach(function(tag) {
      tag.addEventListener('click', function() {
        var term = tag.getAttribute('data-major-smart') || '';
        suggestEngaged = false;
        hideSuggest();
        if (suggestAbort) {
          suggestAbort.abort();
          suggestAbort = null;
        }
        searchInput.value = term;
        document.querySelectorAll(SEL.smartTag).forEach(function(t) {
          t.classList.toggle('is-active', t === tag);
        });
        applyFilter(true);
      });
    });

    function changeCountry(code) {
      var next = code || '';
      if (next === activeCountry) return;
      setCountryActive(next);
      searchResultCache = {};
      hideSuggest();
      applyFilter(false);
      syncPageUrl((searchInput.value || '').trim());
    }

    document.querySelectorAll(SEL.countryFilter).forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        changeCountry(btn.getAttribute('data-major-country') || '');
      });
    });

    document.querySelectorAll(SEL.navCountry).forEach(function(link) {
      link.addEventListener('click', function(e) {
        e.preventDefault();
        changeCountry(link.getAttribute('data-major-country') || '');
      });
    });

    function initCountryPickerModal() {
      var modal = document.getElementById('majorsCountryModal');
      var searchEl = document.getElementById('majorsCountrySearch');
      var listEl = document.getElementById('majorsCountryList');
      var emptyEl = document.getElementById('majorsCountryEmpty');
      if (!modal || !searchEl || !listEl || !worldCountries.length) return;

      var highlightIndex = -1;
      var filteredItems = worldCountries.slice();

      function closeModal() {
        modal.classList.remove('is-open');
        modal.hidden = true;
        modal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
        highlightIndex = -1;
      }

      function openModal() {
        modal.hidden = false;
        modal.setAttribute('aria-hidden', 'false');
        modal.classList.add('is-open');
        document.body.style.overflow = 'hidden';
        searchEl.value = '';
        renderList('');
        window.setTimeout(function() { searchEl.focus(); }, 60);
      }

      function normalizeSearch(str) {
        return (str || '').trim().toLowerCase().replace(/\u200c/g, '').replace(/ي/g, 'ی').replace(/ك/g, 'ک');
      }

      function renderList(query) {
        var q = normalizeSearch(query);
        filteredItems = worldCountries.filter(function(item) {
          return !q || normalizeSearch(item.label).indexOf(q) >= 0;
        });
        highlightIndex = filteredItems.length ? 0 : -1;

        if (!filteredItems.length) {
          listEl.innerHTML = '';
          if (emptyEl) emptyEl.hidden = !q;
          return;
        }
        if (emptyEl) emptyEl.hidden = true;

        listEl.innerHTML = filteredItems.map(function(item, index) {
          var isActive = item.code === activeCountry;
          var isHighlighted = index === highlightIndex;
          var flagHtml = item.flag
            ? '<img src="' + escapeHtml(item.flag) + '" alt="" width="18" height="12" loading="lazy">'
            : '<span class="ti-location-pin" aria-hidden="true"></span>';
          return (
            '<button type="button"' +
            ' class="schools-country-modal__item' +
            (isActive ? ' is-active' : '') +
            (isHighlighted ? ' is-highlighted' : '') +
            '"' +
            ' role="option"' +
            ' data-index="' + index + '"' +
            ' data-country="' + escapeHtml(item.code) + '">' +
            flagHtml +
            '<span>' + escapeHtml(item.label) + '</span>' +
            '</button>'
          );
        }).join('');

        listEl.querySelectorAll('.schools-country-modal__item').forEach(function(btn) {
          btn.addEventListener('click', function() {
            closeModal();
            changeCountry(btn.getAttribute('data-country') || '');
          });
        });
      }

      function moveHighlight(delta) {
        if (!filteredItems.length) return;
        highlightIndex = Math.max(0, Math.min(filteredItems.length - 1, highlightIndex + delta));
        listEl.querySelectorAll('.schools-country-modal__item').forEach(function(el, i) {
          el.classList.toggle('is-highlighted', i === highlightIndex);
          if (i === highlightIndex) el.scrollIntoView({ block: 'nearest' });
        });
      }

      document.querySelectorAll('[data-major-country-picker]').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
          e.preventDefault();
          openModal();
        });
      });

      modal.querySelectorAll('[data-major-country-close]').forEach(function(el) {
        el.addEventListener('click', closeModal);
      });

      searchEl.addEventListener('input', function() {
        renderList(searchEl.value);
      });

      searchEl.addEventListener('keydown', function(e) {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          moveHighlight(1);
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          moveHighlight(-1);
        } else if (e.key === 'Enter') {
          if (highlightIndex >= 0 && filteredItems[highlightIndex]) {
            e.preventDefault();
            closeModal();
            changeCountry(filteredItems[highlightIndex].code);
          }
        } else if (e.key === 'Escape') {
          e.preventDefault();
          closeModal();
        }
      });

      document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && !modal.hidden) closeModal();
      });
    }

    initCountryPickerModal();
    updateWorldCountryTriggers(activeCountry);

    bindJumpButtons(wrapper);
    syncPaginationState({
      has_more: hasMore,
      next_offset: nextOffset,
      total: totalCount
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMajors);
  } else {
    initMajors();
  }
})();
