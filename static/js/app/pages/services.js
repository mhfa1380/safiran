/**
 * صفحه خدمات — فیلتر نیاز (تک‌انتخابی)، جستجو و دسته (AJAX)
 */
(function() {
  'use strict';

  var config = window.PAGE_CONFIG || {};
  var SEL = {
    wrapper: '#services-content-wrapper',
    searchInput: '#services-search-input',
    suggestPanel: '#services-suggest-panel',
    needInput: '.svc-need__input',
    needBox: '.svc-need',
    categoryFilter: '.svc-category-filters .faq-page__filter',
    navCategory: '.faq-page__nav-link[data-svc-category]',
    card: '.svc-card',
    highlight: 'is-highlight',
    jump: '[data-svc-jump]',
    chip: '.faq-page__chip',
    searchBox: '.faq-page__search'
  };

  function escapeHtml(str) {
    var el = document.createElement('div');
    el.textContent = str || '';
    return el.innerHTML;
  }

  function getCookie(name) {
    var match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : '';
  }

  function initServices() {
    var wrapper = document.querySelector(SEL.wrapper);
    var searchInput = document.querySelector(SEL.searchInput);
    var suggestPanel = document.querySelector(SEL.suggestPanel);
    if (!wrapper || !searchInput) return;

    var searchUrl = config.servicesSearchUrl || '';
    var suggestUrl = config.servicesSuggestUrl || '';
    var trackUrl = config.servicesTrackUrl || '';
    var activeCategory = config.servicesActiveCategory || '';
    var suggestTimer;
    var filterTimer;
    var trackedIds = {};
    var highlightIndex = -1;
    var isLoading = false;

    function getSelectedNeeds() {
      var checked = document.querySelector(SEL.needInput + ':checked');
      return checked ? [checked.value] : [];
    }

    function syncNeedBoxes() {
      document.querySelectorAll(SEL.needBox).forEach(function(box) {
        var input = box.querySelector(SEL.needInput);
        if (input) box.classList.toggle('is-checked', input.checked);
      });
    }

    function setCategoryActive(slug) {
      document.querySelectorAll(SEL.categoryFilter).forEach(function(btn) {
        var cat = btn.getAttribute('data-svc-category') || '';
        btn.classList.toggle('is-active', cat === slug);
      });
      document.querySelectorAll(SEL.navCategory).forEach(function(link) {
        var cat = link.getAttribute('data-svc-category') || '';
        link.classList.toggle('is-active', cat === slug);
        if (cat === slug) {
          link.setAttribute('aria-current', 'page');
        } else {
          link.removeAttribute('aria-current');
        }
      });
    }

    function buildUrl(base, q, needs) {
      var params = [];
      if (q) params.push('q=' + encodeURIComponent(q));
      if (activeCategory) params.push('category=' + encodeURIComponent(activeCategory));
      if (needs && needs.length) params.push('needs=' + encodeURIComponent(needs.join(',')));
      return base + (params.length ? '?' + params.join('&') : '');
    }

    function setLoading(on) {
      isLoading = on;
      wrapper.classList.toggle('is-loading', on);
    }

    function findServiceCard(slug) {
      if (!slug) return null;
      return document.getElementById('service-' + slug)
        || wrapper.querySelector('[data-service-slug="' + slug + '"]');
    }

    function bindCards() {
      /* کارت‌ها همیشه باز هستند؛ فقط برای سازگاری با AJAX */
    }

    function bindJumpButtons() {
      document.querySelectorAll(SEL.jump + ', ' + SEL.chip).forEach(function(btn) {
        btn.onclick = function() {
          openServiceBySlug(this.getAttribute('data-svc-jump'));
          var id = this.getAttribute('data-service-id');
          if (id) trackView(id);
        };
      });
    }

    function trackView(serviceId) {
      if (!serviceId || !trackUrl || trackedIds[serviceId]) return;
      trackedIds[serviceId] = true;
      var body = new URLSearchParams();
      body.append('service_id', serviceId);
      fetch(trackUrl, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': getCookie('csrftoken'),
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: body.toString(),
        credentials: 'same-origin'
      }).catch(function() {});
    }

    function openServiceBySlug(slug, scroll) {
      if (scroll === undefined) scroll = true;
      var card = findServiceCard(slug);
      if (!card) return;
      card.classList.add(SEL.highlight);
      if (scroll) {
        card.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      setTimeout(function() { card.classList.remove(SEL.highlight); }, 1400);
      trackView(card.getAttribute('data-service-id'));
    }

    function applyFilter(scrollToBest) {
      if (isLoading) return;
      var q = (searchInput.value || '').trim();
      var needs = getSelectedNeeds();
      if (q.length === 1) return;

      setLoading(true);
      fetch(buildUrl(searchUrl, q, needs), { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function(r) { return r.json(); })
        .then(function(data) {
          if (!data.ok || !data.html) return;
          wrapper.innerHTML = data.html;
          bindCards();
          bindJumpButtons();
          if (scrollToBest) {
            var slug = data.best_slug;
            if (slug) {
              openServiceBySlug(slug, true);
            } else {
              var first = wrapper.querySelector('.svc-card--best, .svc-card');
              if (first) {
                first.classList.add(SEL.highlight);
                first.scrollIntoView({ behavior: 'smooth', block: 'start' });
                setTimeout(function() { first.classList.remove(SEL.highlight); }, 1400);
              }
            }
          }
          handleHashJump();
        })
        .finally(function() { setLoading(false); });
    }

    function scheduleFilter(scrollToBest) {
      clearTimeout(filterTimer);
      filterTimer = setTimeout(function() { applyFilter(scrollToBest); }, 280);
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
        return '<button type="button" class="faq-page__suggest-item" role="option" data-index="' + idx +
          '" data-slug="' + escapeHtml(item.slug) + '" data-id="' + item.id + '" data-title="' + escapeHtml(item.title) + '">' +
          '<span class="faq-page__suggest-q">' + escapeHtml(item.title) + '</span>' +
          (item.category ? '<span class="faq-page__suggest-cat">' + escapeHtml(item.category) + '</span>' : '') +
          (item.smart_match ? '<span class="faq-page__suggest-tag">پیشنهاد هوشمند</span>' : '') +
          '</button>';
      }).join('');
      suggestPanel.hidden = false;
      suggestPanel.querySelectorAll('.faq-page__suggest-item').forEach(function(el) {
        el.addEventListener('click', function() {
          searchInput.value = this.getAttribute('data-title') || '';
          hideSuggest();
          applyFilter(true);
        });
      });
    }

    function doSuggest() {
      if (!suggestUrl) return;
      var q = (searchInput.value || '').trim();
      var needs = getSelectedNeeds();
      fetch(buildUrl(suggestUrl, q, needs), { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function(r) { return r.json(); })
        .then(function(data) {
          if (data.ok) renderSuggest(data.suggestions);
        });
    }

    function handleHashJump() {
      var hash = window.location.hash;
      if (hash && hash.indexOf('#service-') === 0) {
        openServiceBySlug(hash.replace('#service-', ''), true);
      }
    }

    document.querySelectorAll(SEL.needInput).forEach(function(input) {
      input.addEventListener('change', function() {
        syncNeedBoxes();
        scheduleFilter(true);
      });
    });

    document.querySelectorAll(SEL.categoryFilter).forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        activeCategory = this.getAttribute('data-svc-category') || '';
        setCategoryActive(activeCategory);
        scheduleFilter(false);
      });
    });

    searchInput.addEventListener('input', function() {
      clearTimeout(suggestTimer);
      var q = (searchInput.value || '').trim();
      if (q.length === 0) {
        hideSuggest();
        scheduleFilter(false);
        return;
      }
      if (q.length < 2) {
        hideSuggest();
        return;
      }
      suggestTimer = setTimeout(doSuggest, 150);
      scheduleFilter(false);
    });

    searchInput.addEventListener('focus', function() {
      var q = (searchInput.value || '').trim();
      if (q.length >= 2) doSuggest();
    });

    searchInput.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        hideSuggest();
        applyFilter(true);
        return;
      }
      if (!suggestPanel || suggestPanel.hidden) return;
      var items = suggestPanel.querySelectorAll('.faq-page__suggest-item');
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
        el.classList.toggle('is-highlighted', i === highlightIndex);
      });
    });

    document.addEventListener('click', function(e) {
      if (!suggestPanel || suggestPanel.hidden) return;
      if (!e.target.closest(SEL.searchBox)) hideSuggest();
    });

    syncNeedBoxes();
    bindCards();
    bindJumpButtons();
    handleHashJump();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initServices);
  } else {
    initServices();
  }
})();
