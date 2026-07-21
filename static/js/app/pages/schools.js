/**

 * صفحات دانشگاه‌ها — جستجو، پیشنهاد، فیلتر و بارگذاری تدریجی

 */

(function() {

  'use strict';



  var config = window.PAGE_CONFIG || {};

  var SEL = {

    wrapper: '#schools-content-wrapper',

    searchInput: '#schools-search-input',

    suggestPanel: '#schools-suggest-panel',

    countryFilter: '.schools-toolbar-filters [data-school-country]',

    tierFilter: '.schools-toolbar-filters [data-school-tier], .faq-page__nav-link[data-school-tier]',

    typeFilter: '.schools-toolbar-filters [data-school-type]',

    navCountry: '.faq-page__nav-link[data-school-country]',

    navTier: '.faq-page__nav-link[data-school-tier]',

    navType: '.faq-page__nav-link[data-school-type]',

    smartTag: '.schools-smart-tag',

    jump: '[data-uni-jump]',

    highlight: 'is-highlight',

    grid: '#schools-grid',

    sentinel: '#schools-load-sentinel',

    loadMore: '#schools-load-more',

    cta: '#schools-page-cta'

  };



  function escapeHtml(str) {

    var el = document.createElement('div');

    el.textContent = str || '';

    return el.innerHTML;

  }



  function initConsultModal() {

    var modal = document.getElementById('consultModal');

    var form = document.getElementById('quickConsultForm');

    if (!modal || !form) return;



    var formWrap = document.getElementById('consultForm');

    var successEl = document.getElementById('consultSuccess');

    var uniNameEl = document.getElementById('consultUniName');

    var uniIdInput = document.getElementById('consultUniId');

    var consultUrl = config.quickConsultUrl || '';



    function openModal(uniId, uniName) {

      if (uniIdInput) uniIdInput.value = uniId || '';

      if (uniNameEl) uniNameEl.textContent = uniName ? 'دانشگاه: ' + uniName : '';

      if (formWrap) formWrap.classList.remove('hide');

      if (successEl) {

        successEl.classList.remove('show');

        successEl.textContent = '';

      }

      form.reset();

      modal.classList.add('show');

    }



    function closeModal() {

      modal.classList.remove('show');

    }



    document.querySelectorAll('.js-consult-btn').forEach(function(btn) {

      if (btn._consultBound) return;

      btn._consultBound = true;

      btn.addEventListener('click', function(e) {

        e.preventDefault();

        openModal(btn.dataset.uniId, btn.dataset.uniName);

      });

    });



    var closeBtn = modal.querySelector('.consult-modal__close');

    if (closeBtn) closeBtn.addEventListener('click', closeModal);

    modal.addEventListener('click', function(e) {

      if (e.target === modal) closeModal();

    });



    form.addEventListener('submit', function(e) {

      e.preventDefault();

      if (!consultUrl) return;

      var btn = form.querySelector('button[type=submit]');

      btn.disabled = true;

      var fd = new FormData(form);

      var csrf = document.querySelector('[name=csrfmiddlewaretoken]');

      if (csrf) fd.append('csrfmiddlewaretoken', csrf.value);



      fetch(consultUrl, {

        method: 'POST',

        body: fd,

        headers: { 'X-Requested-With': 'XMLHttpRequest' }

      })

        .then(function(r) { return r.json(); })

        .then(function(data) {

          if (data.ok) {

            if (formWrap) formWrap.classList.add('hide');

            if (successEl) {

              successEl.textContent = data.message || 'درخواست شما ثبت شد.';

              successEl.classList.add('show');

            }

            setTimeout(closeModal, 2500);

          } else {

            alert(data.error || (data.errors ? JSON.stringify(data.errors) : 'خطا در ثبت درخواست'));

          }

        })

        .catch(function() { alert('خطا در ارتباط با سرور'); })

        .finally(function() { btn.disabled = false; });

    });

  }



  function initPopupGallery() {

    var gallery = document.querySelector('.popup-gallery');

    if (!gallery || typeof jQuery === 'undefined' || !jQuery.fn.magnificPopup) return;



    jQuery('.popup-gallery').magnificPopup({

      type: 'image',

      gallery: { enabled: true },

      mainClass: 'mfp-fade'

    });

  }



  function initSchoolsList() {

    var wrapper = document.querySelector(SEL.wrapper);

    var searchInput = document.querySelector(SEL.searchInput);

    if (!wrapper || !searchInput) return;



    var searchUrl = config.schoolsSearchUrl || '';

    var suggestUrl = config.schoolsSuggestUrl || '';

    var activeCountry = config.schoolsActiveCountry || '';

    var activeTier = config.schoolsActiveTier || '';

    var activeType = config.schoolsActiveType || '';

    var activeMajor = config.schoolsActiveMajor || '';

    var pageSize = parseInt(config.schoolsPageSize, 10) || 20;

    var nextOffset = parseInt(config.schoolsNextOffset, 10) || 0;

    var hasMore = !!config.schoolsHasMore;

    var totalCount = parseInt(config.schoolsTotal, 10) || 0;



    var pageParams = (function() {

      var out = {};

      try {

        var sp = new URLSearchParams(window.location.search);

        ['target_degree', 'intent'].forEach(function(key) {

          var val = sp.get(key);

          if (val) out[key] = val;

        });

        var major = sp.get('major');

        if (major) {

          activeMajor = major;

          config.schoolsActiveMajor = activeMajor;

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

    var worldCountries = Array.isArray(config.schoolsWorldCountries) ? config.schoolsWorldCountries : [];

    var worldCountryMap = {};

    worldCountries.forEach(function(item) {

      if (item && item.code) worldCountryMap[item.code] = item;

    });



    function isWorldCountry(code) {

      return !!(code && worldCountryMap[code]);

    }



    function updateWorldCountryTriggers(code) {

      var active = isWorldCountry(code) ? worldCountryMap[code] : null;

      document.querySelectorAll('[data-school-country-picker]').forEach(function(btn) {

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

        } else if (btn.classList.contains('schools-world-country-trigger')) {

          var textNode = btn.querySelector('span:last-child');

          if (textNode && !textNode.classList.contains('faq-page__nav-flag')) {

            textNode.textContent = active ? active.label : 'سایر کشورها';

          }

        }

        var flagImg = btn.querySelector('.faq-page__nav-flag');

        var iconEl = btn.querySelector('[class^="ti-"]');

        if (active && active.flag) {

          if (flagImg) {

            flagImg.src = active.flag;

            flagImg.hidden = false;

          } else if (iconEl) {

            var img = document.createElement('img');

            img.src = active.flag;

            img.alt = '';

            img.className = 'faq-page__nav-flag';

            img.width = 20;

            img.height = 14;

            img.loading = 'lazy';

            iconEl.replaceWith(img);

          }

        } else if (!active && flagImg && btn.classList.contains('faq-page__nav-link')) {

          var worldIcon = document.createElement('span');

          worldIcon.className = 'ti-world';

          worldIcon.setAttribute('aria-hidden', 'true');

          flagImg.replaceWith(worldIcon);

        }

      });

    }



    function setCountryActive(code) {

      activeCountry = code || '';

      config.schoolsActiveCountry = activeCountry;

      document.querySelectorAll(SEL.countryFilter).forEach(function(btn) {

        var c = btn.getAttribute('data-school-country') || '';

        btn.classList.toggle('is-active', c === activeCountry);

      });

      document.querySelectorAll(SEL.navCountry).forEach(function(link) {

        var c = link.getAttribute('data-school-country') || '';

        link.classList.toggle('is-active', c === activeCountry);

        if (c === activeCountry) {

          link.setAttribute('aria-current', 'page');

        } else {

          link.removeAttribute('aria-current');

        }

      });

      updateWorldCountryTriggers(activeCountry);

    }



    function setTierActive(code) {

      activeTier = code || '';

      config.schoolsActiveTier = activeTier;

      document.querySelectorAll(SEL.tierFilter).forEach(function(btn) {

        var t = btn.getAttribute('data-school-tier') || '';

        btn.classList.toggle('is-active', t === activeTier);

        if (btn.matches(SEL.navTier)) {

          if (t === activeTier) {

            btn.setAttribute('aria-current', 'page');

          } else {

            btn.removeAttribute('aria-current');

          }

        }

      });

    }



    function setTypeActive(code) {

      activeType = code || '';

      config.schoolsActiveType = activeType;

      document.querySelectorAll(SEL.typeFilter).forEach(function(btn) {

        var t = btn.getAttribute('data-school-type') || '';

        btn.classList.toggle('is-active', t === activeType);

      });

      document.querySelectorAll(SEL.navType).forEach(function(link) {

        var t = link.getAttribute('data-school-type') || '';

        link.classList.toggle('is-active', t === activeType);

      });

    }



    function buildQueryParams(q, extra) {

      var params = [];

      if (q) params.push('q=' + encodeURIComponent(q));

      if (activeCountry) params.push('country=' + encodeURIComponent(activeCountry));

      if (activeTier) params.push('tier=' + encodeURIComponent(activeTier));

      if (activeType) params.push('type=' + encodeURIComponent(activeType));

      if (activeMajor) params.push('major=' + encodeURIComponent(activeMajor));

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



    function findUniCard(slug) {

      if (!slug) return null;

      return document.getElementById('uni-' + slug)

        || wrapper.querySelector('[data-uni-slug="' + slug + '"]');

    }



    function openUniBySlug(slug, scroll) {

      if (scroll === undefined) scroll = true;

      var card = findUniCard(slug);

      if (!card) return;

      card.classList.add(SEL.highlight);

      if (scroll) {

        card.scrollIntoView({ behavior: 'smooth', block: 'start' });

      }

      setTimeout(function() { card.classList.remove(SEL.highlight); }, 1400);

    }



    function bindJumpButtons(root) {

      (root || document).querySelectorAll(SEL.jump).forEach(function(btn) {

        if (btn._schoolsJumpBound) return;

        btn._schoolsJumpBound = true;

        btn.addEventListener('click', function(e) {

          if (btn.tagName === 'A') return;

          e.preventDefault();

          openUniBySlug(btn.getAttribute('data-uni-jump'));

        });

      });

    }



    function bindConsultButtons(root) {

      (root || document).querySelectorAll('.js-consult-btn').forEach(function(btn) {

        if (btn._consultBound) return;

        btn._consultBound = true;

        btn.addEventListener('click', function(e) {

          e.preventDefault();

          var modal = document.getElementById('consultModal');

          if (!modal) return;

          var uniIdInput = document.getElementById('consultUniId');

          var uniNameEl = document.getElementById('consultUniName');

          var formWrap = document.getElementById('consultForm');

          var successEl = document.getElementById('consultSuccess');

          var form = document.getElementById('quickConsultForm');

          if (uniIdInput) uniIdInput.value = btn.dataset.uniId || '';

          if (uniNameEl) uniNameEl.textContent = btn.dataset.uniName ? 'دانشگاه: ' + btn.dataset.uniName : '';

          if (formWrap) formWrap.classList.remove('hide');

          if (successEl) {

            successEl.classList.remove('show');

            successEl.textContent = '';

          }

          if (form) form.reset();

          modal.classList.add('show');

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

              loadMoreSchools();

            }

          });

        },

        { root: null, rootMargin: '240px 0px', threshold: 0 }

      );

      scrollObserver.observe(sentinel);

    }



    function toPersianDigits(n) {

      return String(Math.max(0, parseInt(n, 10) || 0)).replace(/[0-9]/g, function(d) {

        return '۰۱۲۳۴۵۶۷۸۹'[+d];

      });

    }



    function updateResultsCount() {

      var el = document.getElementById('schools-results-count');

      if (!el) return;

      el.innerHTML = 'نتایج: <strong>' + toPersianDigits(totalCount) + '</strong> دانشگاه';

    }



    function syncPaginationState(data) {

      if (typeof data.has_more === 'boolean') hasMore = data.has_more;

      if (typeof data.next_offset === 'number') nextOffset = data.next_offset;

      if (typeof data.total === 'number') totalCount = data.total;

      config.schoolsHasMore = hasMore;

      config.schoolsNextOffset = nextOffset;

      config.schoolsTotal = totalCount;

      updateResultsCount();



      var sentinel = getSentinel();

      if (sentinel) {

        sentinel.hidden = !(hasMore && infiniteEnabled);

      }

      setCtaDeferred(hasMore && infiniteEnabled);

      if (!hasMore) teardownInfiniteScroll();

      else setupInfiniteScroll();

    }



    function loadMoreSchools() {

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

          bindConsultButtons(grid);



          nextOffset = data.next_offset != null ? data.next_offset : nextOffset + pageSize;

          hasMore = !!data.has_more;

          if (typeof data.total === 'number') totalCount = data.total;



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

      return (activeCountry || '') + '|' + (activeTier || '') + '|' + (activeType || '') + '|' + q;

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

      bindConsultButtons(wrapper);



      if (!q) {

        syncPaginationState({

          has_more: data.has_more,

          next_offset: data.next_offset,

          total: data.total

        });

      } else {

        infiniteEnabled = false;

        setCtaDeferred(false);

        if (typeof data.total === 'number') {

          totalCount = data.total;

          config.schoolsTotal = totalCount;

        } else if (typeof data.count === 'number') {

          totalCount = data.count;

          config.schoolsTotal = totalCount;

        }

        updateResultsCount();

      }



      if (scrollToBest && data.best_slug) {

        openUniBySlug(data.best_slug);

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

      var suggestPanel = document.querySelector(SEL.suggestPanel);

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

      var suggestPanel = document.querySelector(SEL.suggestPanel);

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

      var suggestPanel = document.querySelector(SEL.suggestPanel);

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

      var suggestPanel = document.querySelector(SEL.suggestPanel);

      if (!suggestPanel || suggestPanel.hidden) return;

      if (e.target.closest('.faq-page__search-field')) return;

      hideSuggest();

    });



    document.querySelectorAll(SEL.smartTag).forEach(function(tag) {

      tag.addEventListener('click', function() {

        var term = tag.getAttribute('data-school-smart') || '';

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



    function initCountryPickerModal() {

      var modal = document.getElementById('schoolsCountryModal');

      var searchEl = document.getElementById('schoolsCountrySearch');

      var listEl = document.getElementById('schoolsCountryList');

      var emptyEl = document.getElementById('schoolsCountryEmpty');

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

        return (str || '')

          .trim()

          .toLowerCase()

          .replace(/\u200c/g, '')

          .replace(/ي/g, 'ی')

          .replace(/ك/g, 'ک');

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

            var code = btn.getAttribute('data-country') || '';

            closeModal();

            changeCountry(code);

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



      document.querySelectorAll('[data-school-country-picker]').forEach(function(btn) {

        btn.addEventListener('click', function(e) {

          e.preventDefault();

          openModal();

        });

      });



      modal.querySelectorAll('[data-school-country-close]').forEach(function(el) {

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

        if (e.key === 'Escape' && modal.classList.contains('is-open')) {

          closeModal();

        }

      });

    }



    function changeTier(code) {

      var next = code || '';

      if (next && next === activeTier) {

        next = '';

      }

      if (next === activeTier) return;

      setTierActive(next);

      searchResultCache = {};

      hideSuggest();

      applyFilter(false);

      syncPageUrl((searchInput.value || '').trim());

    }



    function changeType(code) {

      var next = code || '';

      if (next === activeType) return;

      setTypeActive(next);

      searchResultCache = {};

      hideSuggest();

      applyFilter(false);

      syncPageUrl((searchInput.value || '').trim());

    }



    document.querySelectorAll(SEL.countryFilter).forEach(function(btn) {

      btn.addEventListener('click', function(e) {

        e.preventDefault();

        changeCountry(btn.getAttribute('data-school-country') || '');

      });

    });



    document.querySelectorAll(SEL.typeFilter).forEach(function(btn) {

      btn.addEventListener('click', function(e) {

        e.preventDefault();

        changeType(btn.getAttribute('data-school-type') || '');

      });

    });



    document.querySelectorAll(SEL.navCountry).forEach(function(link) {

      link.addEventListener('click', function(e) {

        e.preventDefault();

        changeCountry(link.getAttribute('data-school-country') || '');

      });

    });



    document.querySelectorAll(SEL.navType).forEach(function(link) {

      link.addEventListener('click', function(e) {

        e.preventDefault();

        changeType(link.getAttribute('data-school-type') || '');

      });

    });



    document.querySelectorAll(SEL.tierFilter).forEach(function(btn) {

      btn.addEventListener('click', function(e) {

        e.preventDefault();

        changeTier(btn.getAttribute('data-school-tier') || '');

      });

    });



    setTierActive(activeTier);

    updateWorldCountryTriggers(activeCountry);

    initCountryPickerModal();

    bindJumpButtons(wrapper);

    bindConsultButtons(wrapper);

    var initialQ = (searchInput.value || '').trim();

    if (initialQ) {

      infiniteEnabled = false;

      setCtaDeferred(false);

    } else {

      syncPaginationState({

        has_more: hasMore,

        next_offset: nextOffset,

        total: totalCount

      });

    }



    var hash = window.location.hash.replace(/^#/, '');

    if (hash.indexOf('uni-') === 0) {

      setTimeout(function() { openUniBySlug(hash.slice(4)); }, 300);

    }

  }



  function initSchoolDetail() {

    var page = document.querySelector('.school-detail-v2');

    if (!page) return;



    var jumpNav = document.getElementById('school-jump-nav');

    var jumpLinks = page.querySelectorAll('[data-sd-jump]');

    var sections = [];

    var headerOffset = 80;



    jumpLinks.forEach(function(btn) {

      var id = btn.getAttribute('data-sd-jump');

      var el = document.getElementById(id);

      if (el) sections.push({ id: id, el: el, btn: btn });

    });



    function setActiveJump(id) {

      jumpLinks.forEach(function(link) {

        link.classList.toggle('is-active', link.getAttribute('data-sd-jump') === id);

      });

    }



    function scrollToSection(el) {

      if (!el) return;

      el.scrollIntoView({ behavior: 'smooth', block: 'start' });

    }



    function navigateToSection(id) {

      if (!id) return;

      var target = document.getElementById(id);

      if (!target) return;



      if (id.indexOf('school-faq') === 0 && target.matches('.sd-faq__item')) {

        page.querySelectorAll('.sd-faq__item').forEach(function(d) {

          if (d !== target) d.removeAttribute('open');

        });

        target.setAttribute('open', '');

        target.classList.add('is-hash-focus');

        setActiveJump('school-faq');

        window.setTimeout(function() {

          target.classList.remove('is-hash-focus');

        }, 2400);

      } else if (id === 'school-cta') {

        setActiveJump('school-cta');

        target.classList.add('is-hash-focus');

        window.setTimeout(function() {

          target.classList.remove('is-hash-focus');

        }, 2400);

      } else if (sections.some(function(s) { return s.id === id; })) {

        setActiveJump(id);

      }



      window.setTimeout(function() {

        scrollToSection(target);

      }, id.indexOf('school-faq') === 0 ? 60 : 0);



      if (window.history && window.history.replaceState) {

        window.history.replaceState(null, '', '#' + id);

      } else {

        window.location.hash = id;

      }

    }



    jumpLinks.forEach(function(btn) {

      btn.addEventListener('click', function() {

        var id = btn.getAttribute('data-sd-jump');

        navigateToSection(id);

      });

    });



    page.querySelectorAll('.ai-qa-section__more[href^="#"]').forEach(function(link) {

      link.addEventListener('click', function(e) {

        var href = link.getAttribute('href') || '';

        if (href.charAt(0) !== '#') return;

        e.preventDefault();

        navigateToSection(href.slice(1));

      });

    });



    page.querySelectorAll('a[href^="#school-"]').forEach(function(link) {

      link.addEventListener('click', function(e) {

        var href = link.getAttribute('href') || '';

        if (href.charAt(0) !== '#') return;

        var id = href.slice(1);

        if (!document.getElementById(id)) return;

        e.preventDefault();

        navigateToSection(id);

      });

    });



    function openSectionFromHash() {

      var hash = (window.location.hash || '').replace(/^#/, '');

      if (!hash || hash.indexOf('school-') !== 0) return;

      navigateToSection(hash);

    }



    window.addEventListener('hashchange', openSectionFromHash);



    if (window.location.hash) {

      openSectionFromHash();

    } else {

      var firstFaq = page.querySelector('.sd-faq__item');

      if (firstFaq) firstFaq.setAttribute('open', '');

    }



    if (sections.length && 'IntersectionObserver' in window) {

      var observer = new IntersectionObserver(

        function(entries) {

          entries.forEach(function(entry) {

            if (entry.isIntersecting) {

              setActiveJump(entry.target.id);

            }

          });

        },

        { root: null, rootMargin: '-' + headerOffset + 'px 0px -55% 0px', threshold: 0 }

      );

      sections.forEach(function(s) { observer.observe(s.el); });

    }



    if (jumpNav) {

      var onScroll = function() {

        jumpNav.classList.toggle('is-scrolled', window.scrollY > 120);

      };

      window.addEventListener('scroll', onScroll, { passive: true });

      onScroll();

    }

  }



  function init() {

    initConsultModal();

    initPopupGallery();

    initSchoolsList();

    initSchoolDetail();

  }



  if (document.readyState === 'loading') {

    document.addEventListener('DOMContentLoaded', init);

  } else {

    init();

  }

})();


