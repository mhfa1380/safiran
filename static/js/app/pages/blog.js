/**
 * صفحه وبلاگ — جستجوی زنده، فیلتر برچسب و بارگذاری تدریجی
 */
(function () {
  'use strict';

  var config = window.PAGE_CONFIG || {};
  var SEL = {
    wrapper: '#blog-content-wrapper',
    searchInput: '#blog-search-input',
    suggestPanel: '#blog-suggest-panel',
    tagSelect: '#blog-tag-select',
    clearFilters: '#blog-clear-filters',
    grid: '#blog-grid',
    sentinel: '#blog-load-sentinel',
    loadMore: '#blog-load-more',
    highlight: 'is-highlight'
  };

  function escapeHtml(str) {
    var el = document.createElement('div');
    el.textContent = str || '';
    return el.innerHTML;
  }

  function initBlog() {
    var wrapper = document.querySelector(SEL.wrapper);
    var searchInput = document.querySelector(SEL.searchInput);
    var suggestPanel = document.querySelector(SEL.suggestPanel);
    var tagSelect = document.querySelector(SEL.tagSelect);
    var clearBtn = document.querySelector(SEL.clearFilters);
    if (!wrapper || !searchInput) return;

    var searchUrl = config.blogSearchUrl || '';
    var suggestUrl = config.blogSuggestUrl || '';
    var activeTag = config.blogActiveTag || '';
    var pageSize = parseInt(config.blogPageSize, 10) || 6;
    var nextOffset = parseInt(config.blogNextOffset, 10) || 0;
    var hasMore = !!config.blogHasMore;
    var totalCount = parseInt(config.blogTotal, 10) || 0;

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
    var SUGGEST_DEBOUNCE_MS = 120;
    var SEARCH_DEBOUNCE_MS = 220;
    var MIN_SEARCH_LEN = 2;
    var searchResultCache = {};
    var SEARCH_CACHE_MAX = 24;

    function setActiveTag(tag) {
      activeTag = tag || '';
      config.blogActiveTag = activeTag;
      if (tagSelect) tagSelect.value = activeTag;
      if (clearBtn) {
        clearBtn.classList.toggle(
          'is-hidden',
          !(searchInput.value || '').trim() && !activeTag
        );
      }
      wrapper.classList.toggle('is-filtered', !!(searchInput.value || '').trim() || !!activeTag);
    }

    function buildQueryParams(q, extra) {
      var params = [];
      if (q) params.push('q=' + encodeURIComponent(q));
      if (activeTag) params.push('tag=' + encodeURIComponent(activeTag));
      if (extra) {
        Object.keys(extra).forEach(function (key) {
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

    function setLoadingMore(on) {
      isLoadingMore = on;
      var loadMore = getLoadMoreEl();
      if (loadMore) loadMore.hidden = !on;
    }

    function setLoading(on) {
      isLoading = on;
      wrapper.classList.toggle('is-loading', on);
    }

    function findBlogCard(slug) {
      if (!slug) return null;
      return wrapper.querySelector('[data-blog-slug="' + slug + '"]');
    }

    function openBlogBySlug(slug, scroll) {
      if (scroll === undefined) scroll = true;
      var card = findBlogCard(slug);
      if (!card) return;
      card.classList.add(SEL.highlight);
      if (scroll) {
        card.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      setTimeout(function () {
        card.classList.remove(SEL.highlight);
      }, 1400);
    }

    function bindTagButtons(root) {
      (root || wrapper).querySelectorAll('[data-blog-filter-tag]').forEach(function (btn) {
        if (btn._blogTagBound) return;
        btn._blogTagBound = true;
        btn.addEventListener('click', function (e) {
          e.preventDefault();
          var tag = btn.getAttribute('data-blog-filter-tag') || '';
          setActiveTag(tag);
          searchResultCache = {};
          hideSuggest();
          applyFilter(false);
          syncPageUrl((searchInput.value || '').trim());
        });
      });
    }

    function bindDidYouMean(root) {
      (root || wrapper).querySelectorAll('[data-blog-correct]').forEach(function (btn) {
        if (btn._blogCorrectBound) return;
        btn._blogCorrectBound = true;
        btn.addEventListener('click', function () {
          searchInput.value = btn.getAttribute('data-blog-correct') || '';
          applyFilter(true);
        });
      });
    }

    function bindClearButtons(root) {
      (root || wrapper).querySelectorAll('[data-blog-clear]').forEach(function (btn) {
        if (btn._blogClearBound) return;
        btn._blogClearBound = true;
        btn.addEventListener('click', function () {
          clearAllFilters();
        });
      });
    }

    function bindInteractions(root) {
      bindTagButtons(root);
      bindDidYouMean(root);
      bindClearButtons(root);
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
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              loadMorePosts();
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
      config.blogHasMore = hasMore;
      config.blogNextOffset = nextOffset;
      config.blogTotal = totalCount;

      var sentinel = getSentinel();
      if (sentinel) {
        sentinel.hidden = !(hasMore && infiniteEnabled);
      }
      if (!hasMore) teardownInfiniteScroll();
      else setupInfiniteScroll();
    }

    function loadMorePosts() {
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
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (!data.ok || !data.cards_html) return;

          grid.insertAdjacentHTML('beforeend', data.cards_html);
          bindInteractions(grid);

          nextOffset = data.next_offset != null ? data.next_offset : nextOffset + pageSize;
          hasMore = !!data.has_more;
          if (typeof data.total === 'number') totalCount = data.total;

          syncPaginationState({
            has_more: hasMore,
            next_offset: nextOffset,
            total: totalCount
          });
        })
        .catch(function () {})
        .finally(function () {
          setLoadingMore(false);
        });
    }

    function searchCacheKey(q) {
      return (activeTag || '') + '|' + q;
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
      bindInteractions(wrapper);

      if (!q) {
        syncPaginationState({
          has_more: data.has_more,
          next_offset: data.next_offset,
          total: data.total
        });
      } else {
        infiniteEnabled = false;
        teardownInfiniteScroll();
      }

      if (scrollToBest && data.best_slug) {
        openBlogBySlug(data.best_slug);
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
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (!data.ok || !data.html) return;
          if (q) rememberSearchCache(q, data);
          applySearchResult(data, q, scrollToBest);
        })
        .catch(function (err) {
          if (err && err.name === 'AbortError') return;
        })
        .finally(function () {
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
      items.forEach(function (item, i) {
        var tag = item.smart_match
          ? '<span class="faq-page__suggest-tag">تطابق بالا</span>'
          : '';
        html +=
          '<button type="button" class="faq-page__suggest-item" role="option" data-index="' +
          i +
          '" data-slug="' +
          escapeHtml(item.slug) +
          '">' +
          '<span class="faq-page__suggest-q">' +
          escapeHtml(item.title) +
          tag +
          '</span>' +
          (item.tag
            ? '<span class="faq-page__suggest-cat">' + escapeHtml(item.tag) + '</span>'
            : '') +
          '</button>';
      });
      suggestPanel.innerHTML = html;
      suggestPanel.hidden = false;
      highlightIndex = -1;

      suggestPanel.querySelectorAll('.faq-page__suggest-item').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var idx = parseInt(btn.getAttribute('data-index'), 10);
          var item = items[idx];
          if (!item) return;
          searchInput.value = item.title;
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
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (data.ok && data.suggestions) {
            renderSuggest(data.suggestions, data.smart);
          }
        })
        .catch(function (err) {
          if (err && err.name === 'AbortError') return;
        });
    }

    function clearAllFilters() {
      searchInput.value = '';
      setActiveTag('');
      searchResultCache = {};
      hideSuggest();
      if (suggestAbort) {
        suggestAbort.abort();
        suggestAbort = null;
      }
      applyFilter(false);
      syncPageUrl('');
    }

    var searchField = searchInput.closest('.faq-page__search-field');
    if (searchField) {
      searchField.addEventListener('pointerdown', function () {
        suggestEngaged = true;
        var q = (searchInput.value || '').trim();
        if (q.length >= MIN_SEARCH_LEN) {
          clearTimeout(suggestTimer);
          suggestTimer = setTimeout(fetchSuggest, SUGGEST_DEBOUNCE_MS);
        }
      });
    }

    searchInput.addEventListener('input', function () {
      clearTimeout(suggestTimer);
      clearTimeout(filterTimer);
      setActiveTag(activeTag);
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
        filterTimer = setTimeout(function () {
          applyFilter(false);
        }, SEARCH_DEBOUNCE_MS);
      } else {
        hideSuggest();
      }
    });

    searchInput.addEventListener('keydown', function (e) {
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
      items.forEach(function (el, i) {
        el.classList.toggle('is-highlighted', i === highlightIndex);
      });
    });

    document.addEventListener('click', function (e) {
      if (!suggestPanel || suggestPanel.hidden) return;
      if (e.target.closest('.faq-page__search-field')) return;
      hideSuggest();
    });

    if (tagSelect) {
      tagSelect.addEventListener('change', function () {
        setActiveTag(tagSelect.value || '');
        searchResultCache = {};
        hideSuggest();
        applyFilter(false);
        syncPageUrl((searchInput.value || '').trim());
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener('click', clearAllFilters);
    }

    bindInteractions(wrapper);
    setActiveTag(activeTag);
    syncPaginationState({
      has_more: hasMore,
      next_offset: nextOffset,
      total: totalCount
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initBlog);
  } else {
    initBlog();
  }
})();
