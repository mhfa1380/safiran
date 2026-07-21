/**
 * صفحه کشور — جستجو، پیشنهاد، پرش به بخش‌ها، آکوردئون
 */
(function() {
  'use strict';

  var config = window.PAGE_CONFIG || {};
  var SEL = {
    wrapper: '#country-search-wrapper',
    searchInput: '#country-search-input',
    suggestPanel: '#country-suggest-panel',
    searchField: '.country-page__search-field',
    jump: 'button[data-country-jump], .country-page__tab[data-country-jump]',
    jumpAnchor: 'a[data-country-jump]',
    tab: '.country-page__tab',
    accordionItem: 'details.country-page__item'
  };

  function escapeHtml(str) {
    var el = document.createElement('div');
    el.textContent = str || '';
    return el.innerHTML;
  }

  function headerScrollOffset() {
    var header = document.getElementById('site-header');
    var extra = 12;
    if (header) {
      return header.getBoundingClientRect().height + extra;
    }
    return 88;
  }

  function scrollToSection(id) {
    if (!id) return;
    var el = document.getElementById(id);
    if (!el) return;
    if (el.tagName === 'DETAILS') {
      el.open = true;
    }
    setActiveTab(id);
    el.classList.add('is-highlight');
    var top = el.getBoundingClientRect().top + window.pageYOffset - headerScrollOffset();
    window.scrollTo({ behavior: 'smooth', top: Math.max(0, top) });
    window.setTimeout(function() {
      el.classList.remove('is-highlight');
    }, 1400);
  }

  function bindJumpButtons() {
    document.querySelectorAll(SEL.jump + ', ' + SEL.tab).forEach(function(btn) {
      btn.addEventListener('click', function() {
        var id = this.getAttribute('data-country-jump');
        setActiveTab(id);
        scrollToSection(id);
      });
    });
    document.querySelectorAll(SEL.jumpAnchor).forEach(function(link) {
      link.addEventListener('click', function(e) {
        var id = this.getAttribute('data-country-jump');
        if (!id || !document.getElementById(id)) return;
        e.preventDefault();
        scrollToSection(id);
        if (window.history && window.history.replaceState) {
          window.history.replaceState(null, '', '#' + id);
        }
      });
    });
  }

  function setActiveTab(sectionId) {
    if (!sectionId) return;
    document.querySelectorAll(SEL.tab).forEach(function(tab) {
      tab.classList.toggle('is-active', tab.getAttribute('data-country-jump') === sectionId);
    });
  }

  function initScrollSpy() {
    var tabs = document.querySelectorAll(SEL.tab);
    if (!tabs.length || !('IntersectionObserver' in window)) return;

    var sectionIds = [];
    tabs.forEach(function(tab) {
      var id = tab.getAttribute('data-country-jump');
      if (id && document.getElementById(id)) sectionIds.push(id);
    });
    if (!sectionIds.length) return;

    var observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          setActiveTab(entry.target.id);
        }
      });
    }, {
      rootMargin: '-' + headerScrollOffset() + 'px 0px -55% 0px',
      threshold: 0
    });

    sectionIds.forEach(function(id) {
      var el = document.getElementById(id);
      if (el) observer.observe(el);
    });
  }

  function bindAccordion() {
    document.querySelectorAll(SEL.accordionItem).forEach(function(detail) {
      detail.addEventListener('toggle', function() {
        if (!this.open) return;
        var accordion = this.closest('.country-page__accordion');
        if (!accordion) return;
        accordion.querySelectorAll(SEL.accordionItem).forEach(function(other) {
          if (other !== detail) other.open = false;
        });
      });
    });
  }

  function initCountrySearch() {
    var wrapper = document.querySelector(SEL.wrapper);
    var searchInput = document.querySelector(SEL.searchInput);
    var suggestPanel = document.querySelector(SEL.suggestPanel);
    if (!wrapper || !searchInput) return;

    var searchUrl = config.countrySearchUrl || '';
    var suggestUrl = config.countrySuggestUrl || '';
    var suggestTimer;
    var searchTimer;
    var highlightIndex = -1;

    function showResults() {
      wrapper.hidden = false;
    }

    function hideResults() {
      wrapper.hidden = true;
      wrapper.innerHTML = '';
    }

    function bindFaqToggles() {
      wrapper.querySelectorAll('[data-country-faq-toggle]').forEach(function(btn) {
        btn.onclick = function() {
          var answer = btn.closest('.country-hit').querySelector('.country-hit__answer');
          if (!answer) return;
          var open = answer.hidden;
          answer.hidden = !open;
          btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        };
      });
    }

    function doSearch() {
      var q = (searchInput.value || '').trim();
      if (q.length > 0 && q.length < 2) return;
      var url = searchUrl + (q ? '?q=' + encodeURIComponent(q) : '');
      fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function(r) { return r.json(); })
        .then(function(data) {
          if (!data.ok) return;
          if (!q) {
            hideResults();
            return;
          }
          wrapper.innerHTML = data.html || '';
          showResults();
          bindFaqToggles();
          var best = wrapper.querySelector('.country-hit--best');
          if (best) best.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        })
        .catch(function() {});
    }

    function hideSuggest() {
      if (suggestPanel) {
        suggestPanel.hidden = true;
        suggestPanel.innerHTML = '';
      }
      highlightIndex = -1;
    }

    function renderSuggest(items) {
      if (!suggestPanel) return;
      if (!items || !items.length) {
        hideSuggest();
        return;
      }
      suggestPanel.innerHTML = items.map(function(item, idx) {
        return '<button type="button" class="country-page__suggest-item" role="option" data-index="' + idx +
          '" data-url="' + escapeHtml(item.url) + '">' +
          '<span class="country-page__suggest-badge">' + escapeHtml(item.badge || '') + '</span>' +
          escapeHtml(item.title) +
          '</button>';
      }).join('');
      suggestPanel.hidden = false;
      suggestPanel.querySelectorAll('.country-page__suggest-item').forEach(function(el) {
        el.addEventListener('click', function() {
          var url = this.getAttribute('data-url');
          hideSuggest();
          if (url && url.indexOf('#') === -1) {
            window.location.href = url;
            return;
          }
          searchInput.value = this.textContent.trim();
          doSearch();
        });
      });
    }

    function doSuggest() {
      if (!suggestUrl) return;
      var q = (searchInput.value || '').trim();
      var url = suggestUrl + (q ? '?q=' + encodeURIComponent(q) : '');
      fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function(r) { return r.json(); })
        .then(function(data) {
          if (data.ok) renderSuggest(data.suggestions);
        })
        .catch(function() {});
    }

    searchInput.addEventListener('input', function() {
      clearTimeout(suggestTimer);
      clearTimeout(searchTimer);
      var q = (searchInput.value || '').trim();
      if (q.length === 0) {
        hideSuggest();
        hideResults();
        return;
      }
      if (q.length < 2) {
        hideSuggest();
        hideResults();
        return;
      }
      suggestTimer = setTimeout(doSuggest, 160);
      searchTimer = setTimeout(doSearch, 320);
    });

    searchInput.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        hideSuggest();
        var q = (searchInput.value || '').trim();
        if (q.length >= 2) doSearch();
        return;
      }
      if (!suggestPanel || suggestPanel.hidden) return;
      var items = suggestPanel.querySelectorAll('.country-page__suggest-item');
      if (!items.length) return;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        highlightIndex = Math.min(highlightIndex + 1, items.length - 1);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        highlightIndex = Math.max(highlightIndex - 1, 0);
      } else if (e.key === 'Escape') {
        hideSuggest();
        return;
      } else {
        return;
      }
      items.forEach(function(el, i) {
        el.classList.toggle('is-active', i === highlightIndex);
        el.classList.toggle('is-highlighted', i === highlightIndex);
      });
    });

    document.addEventListener('click', function(e) {
      if (!suggestPanel || suggestPanel.hidden) return;
      if (!e.target.closest(SEL.searchField)) hideSuggest();
    });
  }

  function initNavDegreeFocus() {
    var hash = (window.location.hash || '').replace('#', '');
    var targetId = hash;
    if (!targetId && config.focusScholarship) {
      targetId = 'guide-scholarship';
    }
    if (!targetId) return;
    window.setTimeout(function() {
      scrollToSection(targetId);
    }, 400);
  }

  function init() {
    bindJumpButtons();
    bindAccordion();
    initCountrySearch();
    initScrollSpy();
    initNavDegreeFocus();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
