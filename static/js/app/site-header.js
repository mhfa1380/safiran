/**
 * نوبار — جستجوی زنده (پیشنهاد هوشمند، بدون آیکون)
 */
(function() {
  'use strict';

  var cfg = window.SITE_HEADER_CONFIG || {};
  var suggestUrl = cfg.suggestUrl || '';
  var searchPageUrl = cfg.searchPageUrl || '/search/';
  var MAX_SUGGESTIONS = 8;
  var DEBOUNCE_MS = 110;
  var CACHE_MAX = 24;
  var suggestCache = Object.create(null);
  var cacheKeys = [];

  function escapeHtml(str) {
    var el = document.createElement('div');
    el.textContent = str || '';
    return el.innerHTML;
  }

  function cacheGet(key) {
    return suggestCache[key];
  }

  function cacheSet(key, data) {
    if (cacheKeys.indexOf(key) >= 0) {
      suggestCache[key] = data;
      return;
    }
    cacheKeys.push(key);
    suggestCache[key] = data;
    if (cacheKeys.length > CACHE_MAX) {
      var old = cacheKeys.shift();
      delete suggestCache[old];
    }
  }

  function highlightQuery(text, q) {
    var safe = escapeHtml(text);
    if (!q || q.length < 2) return safe;
    var words = q.trim().split(/\s+/).filter(function(w) { return w.length >= 2; });
    if (!words.length) return safe;
    words.forEach(function(word) {
      var re = new RegExp('(' + word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
      safe = safe.replace(re, '<mark>$1</mark>');
    });
    return safe;
  }

  function isDesktopNav() {
    return window.innerWidth > 1199;
  }

  function initSiteSearch() {
    var root = document.getElementById('site-header-search');
    var header = document.getElementById('site-header');
    var input = document.getElementById('site-search-input');
    var dropdown = document.getElementById('site-search-dropdown');
    var results = document.getElementById('site-search-results');
    var clearBtn = document.getElementById('site-search-clear');
    var openBtn = document.getElementById('site-header-search-open');
    var form = root && root.querySelector('.site-header__search-form');
    if (!root || !input || !dropdown || !results || !form) return;

    var suggestTimer;
    var activeIndex = -1;
    var abortCtrl = null;
    var blurTimer;
    var lastQuery = '';

    function setDesktopSearchExpanded(expanded) {
      if (!isDesktopNav()) return;
      root.classList.toggle('is-expanded', expanded);
      if (openBtn) {
        openBtn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
      }
    }

    function expandDesktopSearch(focusInput) {
      if (!isDesktopNav()) return;
      setDesktopSearchExpanded(true);
      if (focusInput !== false) {
        window.requestAnimationFrame(function() {
          input.focus();
          if (typeof input.select === 'function') input.select();
        });
      }
    }

    function collapseDesktopSearchIfEmpty() {
      if (!isDesktopNav()) return;
      if (!input.value.trim() && !root.classList.contains('is-search-open')) {
        setDesktopSearchExpanded(false);
      }
    }

    function positionMobileDropdown() {
      if (window.innerWidth > 1199) {
        dropdown.style.position = '';
        dropdown.style.top = '';
        dropdown.style.left = '';
        dropdown.style.right = '';
        return;
      }
      var rect = input.getBoundingClientRect();
      dropdown.style.position = 'fixed';
      dropdown.style.top = Math.round(rect.bottom + 8) + 'px';
      dropdown.style.left = '12px';
      dropdown.style.right = '12px';
    }

    function setDropdownOpen(open) {
      dropdown.hidden = !open;
      input.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (header) header.classList.toggle('is-search-open', open);
      root.classList.toggle('is-search-open', open);
      if (open) positionMobileDropdown();
    }

    function updateClearButton() {
      if (!clearBtn) return;
      var hasValue = !!input.value.trim();
      clearBtn.hidden = !hasValue;
      root.classList.toggle('has-search-value', hasValue);
    }

    function normalizeItems(data, limit) {
      if (data.suggestions && data.suggestions.length) {
        return data.suggestions.slice(0, limit).map(function(item) {
          return {
            title: item.title,
            subtitle: item.subtitle,
            url: item.url,
            type_label: item.type_label || ''
          };
        });
      }
      return flattenGroups(data.groups, limit);
    }

    function flattenGroups(groups, limit) {
      var items = [];
      (groups || []).forEach(function(group) {
        (group.items || []).forEach(function(item) {
          if (items.length < limit) {
            items.push({
              title: item.title,
              subtitle: item.subtitle,
              url: item.url,
              type_label: item.type_label || group.type_label || ''
            });
          }
        });
      });
      return items;
    }

    function setLoading(loading) {
      results.setAttribute('aria-busy', loading ? 'true' : 'false');
      if (loading) {
        results.innerHTML =
          '<div class="site-header__search-loading" aria-hidden="true">' +
          '<div class="site-header__search-skeleton">' +
          '<span></span><span></span><span></span>' +
          '</div></div>';
      }
    }

    function renderDidYouMean(didYouMean, q) {
      if (!didYouMean || !q || didYouMean.toLowerCase() === q.toLowerCase()) {
        return '';
      }
      return (
        '<p class="site-header__search-did-you-mean" role="note">' +
        'آیا منظورتان ' +
        '<a href="' + escapeHtml(searchPageUrl) + '?q=' + encodeURIComponent(didYouMean) + '">' +
        '«' + escapeHtml(didYouMean) + '»' +
        '</a> است؟' +
        '</p>'
      );
    }

    function renderItems(items, q, didYouMean) {
      if (!items.length) {
        var emptyHtml = renderDidYouMean(didYouMean, q);
        emptyHtml += '<p class="site-header__search-empty">نتیجه‌ای پیدا نشد</p>';
        results.innerHTML = emptyHtml;
        setDropdownOpen(!!q);
        activeIndex = -1;
        return;
      }

      var html = renderDidYouMean(didYouMean, q);
      html += '<ul class="site-header__suggest-list" role="presentation">';
      items.forEach(function(item, i) {
        html += '<li class="site-header__suggest-item" role="option" id="site-suggest-' + i + '">';
        html += '<a class="site-header__suggest-link" href="' + escapeHtml(item.url) + '" tabindex="-1">';
        html += '<span class="site-header__suggest-body">';
        html += '<span class="site-header__suggest-title">' + highlightQuery(item.title, q) + '</span>';
        if (item.subtitle) {
          html += '<span class="site-header__suggest-meta">' + escapeHtml(item.subtitle) + '</span>';
        }
        html += '</span>';
        if (item.type_label) {
          html += '<span class="site-header__suggest-type">' + escapeHtml(item.type_label) + '</span>';
        }
        html += '</a></li>';
      });
      html += '</ul>';

      if (q) {
        html += '<div class="site-header__suggest-footer">';
        html += '<a href="' + escapeHtml(searchPageUrl) + '?q=' + encodeURIComponent(q) + '">مشاهده همه نتایج</a>';
        html += '</div>';
      }

      results.innerHTML = html;
      setDropdownOpen(true);
      activeIndex = -1;
    }

    function renderHint() {
      results.innerHTML =
        '<p class="site-header__search-hint">کشور، دانشگاه، خدمت، وبلاگ یا سوال متداول را جستجو کنید</p>';
      setDropdownOpen(false);
    }

    function applySuggestData(data, q) {
      if (!data || !data.ok) {
        renderHint();
        return;
      }
      var items = normalizeItems(data, MAX_SUGGESTIONS);
      if (!items.length && !q) {
        renderHint();
        return;
      }
      renderItems(items, q, data.did_you_mean || '');
    }

    function fetchSuggest(q) {
      if (!suggestUrl) {
        renderHint();
        return;
      }

      if (abortCtrl) abortCtrl.abort();
      abortCtrl = new AbortController();
      lastQuery = q;

      if (!q) {
        var cachedEmpty = cacheGet('');
        if (cachedEmpty) {
          applySuggestData(cachedEmpty, '');
          return;
        }
      } else {
        var cached = cacheGet(q);
        if (cached) {
          applySuggestData(cached, q);
          return;
        }
      }

      setLoading(true);
      setDropdownOpen(true);

      var url = suggestUrl + (suggestUrl.indexOf('?') >= 0 ? '&' : '?') + 'q=' + encodeURIComponent(q);
      fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin',
        signal: abortCtrl.signal
      })
        .then(function(res) { return res.json(); })
        .then(function(data) {
          if (q !== lastQuery) return;
          if (!q) cacheSet('', data);
          else cacheSet(q, data);
          applySuggestData(data, q);
        })
        .catch(function(err) {
          if (err && err.name === 'AbortError') return;
          results.innerHTML = '<p class="site-header__search-empty">خطا در جستجو</p>';
          setDropdownOpen(true);
        });
    }

    function scheduleSuggest() {
      clearTimeout(suggestTimer);
      var q = input.value.trim();
      updateClearButton();
      if (q && isDesktopNav()) {
        expandDesktopSearch(false);
      }
      suggestTimer = setTimeout(function() {
        fetchSuggest(q);
      }, q ? DEBOUNCE_MS : 0);
    }

    function getLinks() {
      return Array.prototype.slice.call(results.querySelectorAll('.site-header__suggest-link'));
    }

    function setActiveLink(index) {
      var links = getLinks();
      links.forEach(function(link, i) {
        link.classList.toggle('is-active', i === index);
      });
      if (index >= 0 && links[index]) {
        links[index].scrollIntoView({ block: 'nearest' });
      }
    }

    function closeDropdown() {
      setDropdownOpen(false);
      activeIndex = -1;
    }

    if (openBtn) {
      openBtn.addEventListener('click', function() {
        expandDesktopSearch(true);
      });
    }

    input.addEventListener('focus', function() {
      clearTimeout(blurTimer);
      if (isDesktopNav()) {
        expandDesktopSearch(false);
      }
      if (window.innerWidth <= 1199 && header) {
        header.classList.add('is-mobile-search-open');
        var mobToggle = document.getElementById('site-header-search-toggle');
        if (mobToggle) {
          mobToggle.setAttribute('aria-expanded', 'true');
          mobToggle.classList.add('is-active');
        }
      }
      positionMobileDropdown();
      var q = input.value.trim();
      fetchSuggest(q);
    });

    input.addEventListener('blur', function() {
      blurTimer = setTimeout(function() {
        if (dropdown.contains(document.activeElement)) return;
        closeDropdown();
        collapseDesktopSearchIfEmpty();
      }, 220);
    });

    dropdown.addEventListener('mousedown', function(e) {
      e.preventDefault();
    });

    input.addEventListener('input', scheduleSuggest);

    if (clearBtn) {
      clearBtn.addEventListener('click', function() {
        input.value = '';
        updateClearButton();
        input.focus();
        fetchSuggest('');
      });
    }

    form.addEventListener('submit', function(e) {
      var links = getLinks();
      if (activeIndex >= 0 && links[activeIndex]) {
        e.preventDefault();
        window.location.href = links[activeIndex].href;
      }
    });

    input.addEventListener('keydown', function(e) {
      var links = getLinks();
      if (e.key === 'Escape') {
        closeDropdown();
        input.blur();
        return;
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (!dropdown.hidden && links.length) {
          activeIndex = Math.min(activeIndex + 1, links.length - 1);
          setActiveLink(activeIndex);
        } else if (dropdown.hidden && input.value.trim()) {
          fetchSuggest(input.value.trim());
        }
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (!dropdown.hidden && links.length) {
          activeIndex = Math.max(activeIndex - 1, 0);
          setActiveLink(activeIndex);
        }
        return;
      }
      if (e.key === 'Enter' && activeIndex >= 0 && links[activeIndex]) {
        e.preventDefault();
        window.location.href = links[activeIndex].href;
      }
    });

    document.addEventListener('keydown', function(e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        if (isDesktopNav()) {
          expandDesktopSearch(true);
        } else if (header) {
          header.classList.add('is-mobile-search-open');
          var mobToggle = document.getElementById('site-header-search-toggle');
          if (mobToggle) {
            mobToggle.setAttribute('aria-expanded', 'true');
            mobToggle.classList.add('is-active');
          }
          input.focus();
          input.select();
        }
      }
    });

    document.addEventListener('click', function(e) {
      if (!root.contains(e.target)) {
        closeDropdown();
        collapseDesktopSearchIfEmpty();
      }
    });

    window.addEventListener(
      'scroll',
      function() {
        if (!dropdown.hidden) positionMobileDropdown();
      },
      { passive: true }
    );

    window.addEventListener('resize', function() {
      if (!dropdown.hidden) positionMobileDropdown();
      if (!isDesktopNav()) {
        setDesktopSearchExpanded(false);
      }
    });

    updateClearButton();
  }

  function initMobileMenuDropdowns() {
    var dropdowns = document.querySelectorAll('.site-header__dropdown');
    if (!dropdowns.length) return;

    function isMobile() {
      return window.innerWidth <= 1199;
    }

    function closeAll(except) {
      dropdowns.forEach(function(item) {
        if (except && item === except) return;
        item.classList.remove('show');
        var menu = item.querySelector('.dropdown-menu');
        var toggle = item.querySelector('.dropdown-toggle');
        if (menu) menu.classList.remove('show');
        if (toggle) toggle.setAttribute('aria-expanded', 'false');
      });
    }

    dropdowns.forEach(function(item) {
      var toggle = item.querySelector('.dropdown-toggle');
      var menu = item.querySelector('.dropdown-menu');
      if (!toggle || !menu) return;

      toggle.addEventListener('click', function(e) {
        if (!isMobile()) return;
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        var willOpen = !item.classList.contains('show');
        closeAll(willOpen ? item : null);
        item.classList.toggle('show', willOpen);
        menu.classList.toggle('show', willOpen);
        toggle.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
      });

      item.querySelectorAll('.dropdown-item[href]').forEach(function(link) {
        link.addEventListener('click', function() {
          if (!isMobile()) return;
          closeAll();
        });
      });
    });

    document.addEventListener('click', function(e) {
      if (!isMobile()) return;
      var header = document.getElementById('site-header');
      if (!header || header.contains(e.target)) return;
      closeAll();
    });

    window.addEventListener('resize', function() {
      if (!isMobile()) closeAll();
    });
  }

  function initMobileNav() {
    var header = document.getElementById('site-header');
    var searchToggle = document.getElementById('site-header-search-toggle');
    var searchRoot = document.getElementById('site-header-search');
    var searchInput = document.getElementById('site-search-input');
    var collapse = document.getElementById('navbarSupportedContent');
    var menuToggler = document.querySelector(
      '.site-header__toggler[data-target="#navbarSupportedContent"]'
    );
    if (!header || !searchToggle) return;

    function closeMobileSearch() {
      header.classList.remove('is-mobile-search-open');
      searchToggle.setAttribute('aria-expanded', 'false');
      searchToggle.classList.remove('is-active');
    }

    function isMobileMenuOpen() {
      return collapse && collapse.classList.contains('show');
    }

    function closeMobileMenu() {
      if (!collapse || !isMobileMenuOpen()) return;
      if (window.jQuery) {
        window.jQuery(collapse).collapse('hide');
      } else {
        collapse.classList.remove('show');
        if (menuToggler) {
          menuToggler.setAttribute('aria-expanded', 'false');
          menuToggler.classList.add('collapsed');
        }
      }
    }

    searchToggle.addEventListener('click', function() {
      var willOpen = !header.classList.contains('is-mobile-search-open');
      header.classList.toggle('is-mobile-search-open', willOpen);
      searchToggle.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
      searchToggle.classList.toggle('is-active', willOpen);
      if (willOpen) {
        if (collapse && collapse.classList.contains('show') && window.jQuery) {
          window.jQuery(collapse).collapse('hide');
        }
        if (searchInput) {
          searchInput.focus({ preventScroll: true });
        }
      } else if (searchInput) {
        searchInput.blur();
      }
    });

    function syncMobileMenuToggler() {
      if (!menuToggler || window.innerWidth > 1199) return;
      var open = isMobileMenuOpen();
      menuToggler.setAttribute('aria-label', open ? 'بستن منو' : 'باز کردن منو');
      menuToggler.setAttribute('aria-expanded', open ? 'true' : 'false');
      menuToggler.classList.toggle('collapsed', !open);
    }

    function openMobileMenuState() {
      header.classList.add('site-header--menu-open', 'menu_fixed');
      document.body.classList.add('site-header-menu-open');
    }

    function closeMobileMenuState() {
      header.classList.remove('site-header--menu-open');
      document.body.classList.remove('site-header-menu-open');
      if (document.querySelector('.page-hero')) return;
      if ((window.pageYOffset || 0) <= 50) {
        header.classList.remove('menu_fixed');
      }
    }

    if (menuToggler) {
      menuToggler.addEventListener('click', function() {
        if (window.innerWidth > 1199) return;
        if (menuToggler.classList.contains('collapsed')) {
          openMobileMenuState();
        }
      });
    }

    if (collapse) {
      collapse.addEventListener('show.bs.collapse', function() {
        closeMobileSearch();
        openMobileMenuState();
        syncMobileMenuToggler();
      });
      collapse.addEventListener('shown.bs.collapse', syncMobileMenuToggler);
      collapse.addEventListener('hidden.bs.collapse', function() {
        closeMobileMenuState();
        collapse.style.height = '';
        collapse.style.maxHeight = '';
        collapse.style.overflow = '';
        syncMobileMenuToggler();
        document.querySelectorAll('.site-header__dropdown.show').forEach(function(item) {
          item.classList.remove('show');
          var menu = item.querySelector('.dropdown-menu');
          var toggle = item.querySelector('.dropdown-toggle');
          if (menu) menu.classList.remove('show');
          if (toggle) toggle.setAttribute('aria-expanded', 'false');
        });
      });

      collapse.querySelectorAll('a.nav-link[href], a.dropdown-item[href]').forEach(function(link) {
        link.addEventListener('click', function() {
          if (window.innerWidth > 1199) return;
          if (link.classList.contains('dropdown-toggle')) return;
          closeMobileMenu();
        });
      });
    }

    document.addEventListener('click', function(e) {
      if (window.innerWidth > 1199) return;
      if (!header.classList.contains('is-mobile-search-open')) return;
      if (searchRoot && searchRoot.contains(e.target)) return;
      if (searchToggle.contains(e.target)) return;
      closeMobileSearch();
    });

    document.addEventListener('click', function(e) {
      if (window.innerWidth > 1199) return;
      if (!isMobileMenuOpen()) return;
      if (collapse.contains(e.target)) return;
      if (menuToggler && menuToggler.contains(e.target)) return;
      closeMobileMenu();
    });

    document.addEventListener('keydown', function(e) {
      if (e.key !== 'Escape' || window.innerWidth > 1199) return;
      if (isMobileMenuOpen()) {
        closeMobileMenu();
      }
    });

    window.addEventListener('resize', function() {
      if (window.innerWidth > 1199) {
        closeMobileSearch();
        closeMobileMenu();
        document.body.classList.remove('site-header-menu-open');
      }
    });
  }

  function boot() {
    initSiteSearch();
    initMobileMenuDropdowns();
    initMobileNav();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
