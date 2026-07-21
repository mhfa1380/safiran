/**
 * صفحه سوالات متداول — جستجو، پیشنهاد، آکاردئون
 */
(function() {
  'use strict';

  var config = window.PAGE_CONFIG || {};
  var SEL = {
    wrapper: '#faq-content-wrapper',
    searchInput: '#faq-search-input',
    suggestPanel: '#faq-suggest-panel',
    item: 'details.faq-page__item',
    highlight: 'is-highlight',
    jump: '[data-faq-jump]',
    chip: '.faq-page__chip',
    searchBox: '.faq-page__search'
  };

  function getCookie(name) {
    var match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : '';
  }

  function escapeHtml(str) {
    var el = document.createElement('div');
    el.textContent = str || '';
    return el.innerHTML;
  }

  function initFaq() {
    var wrapper = document.querySelector(SEL.wrapper);
    var searchInput = document.querySelector(SEL.searchInput);
    var suggestPanel = document.querySelector(SEL.suggestPanel);
    if (!wrapper || !searchInput) return;

    var faqSearchUrl = config.faqSearchUrl || '';
    var faqSuggestUrl = config.faqSuggestUrl || '';
    var faqTrackUrl = config.faqTrackUrl || '';
    var activeCategory = config.faqActiveCategory || '';
    var suggestTimer;
    var trackedIds = {};
    var highlightIndex = -1;

    function findFaqItem(slug) {
      if (!slug) return null;
      return document.getElementById('faq-' + slug)
        || document.getElementById('faq-related-' + slug)
        || wrapper.querySelector('[data-faq-slug="' + slug + '"]');
    }

    function bindAccordion() {
      wrapper.querySelectorAll(SEL.item).forEach(function(detail) {
        detail.addEventListener('toggle', function() {
          if (!this.open) return;
          var section = this.closest('.faq-page__accordion--primary');
          if (section) {
            section.querySelectorAll(SEL.item).forEach(function(other) {
              if (other !== detail) other.open = false;
            });
          }
          trackView(this.getAttribute('data-faq-id'));
        });
      });
    }

    function bindJumpButtons() {
      document.querySelectorAll(SEL.jump + ', ' + SEL.chip).forEach(function(btn) {
        btn.onclick = function() {
          openFaqBySlug(this.getAttribute('data-faq-jump'));
          var id = this.getAttribute('data-faq-id');
          if (id) trackView(id);
        };
      });
    }

    function trackView(faqId) {
      if (!faqId || !faqTrackUrl || trackedIds[faqId]) return;
      trackedIds[faqId] = true;
      var body = new URLSearchParams();
      body.append('faq_id', faqId);
      fetch(faqTrackUrl, {
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

    function openFaqBySlug(slug, scroll) {
      if (scroll === undefined) scroll = true;
      var item = findFaqItem(slug);
      if (!item || item.tagName !== 'DETAILS') return;
      item.open = true;
      item.classList.add(SEL.highlight);
      if (scroll) {
        item.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      setTimeout(function() { item.classList.remove(SEL.highlight); }, 1400);
      trackView(item.getAttribute('data-faq-id'));
    }

    function buildSearchUrl(q) {
      var params = [];
      if (q) params.push('q=' + encodeURIComponent(q));
      if (activeCategory) params.push('category=' + encodeURIComponent(activeCategory));
      return faqSearchUrl + (params.length ? '?' + params.join('&') : '');
    }

    function buildSuggestUrl(q) {
      var params = [];
      if (q) params.push('q=' + encodeURIComponent(q));
      if (activeCategory) params.push('category=' + encodeURIComponent(activeCategory));
      return faqSuggestUrl + (params.length ? '?' + params.join('&') : '');
    }

    function doSearch(scrollToBest) {
      var q = (searchInput.value || '').trim();
      if (q.length > 0 && q.length < 2) return;
      fetch(buildSearchUrl(q), { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function(r) { return r.json(); })
        .then(function(data) {
          if (!data.ok || !data.html) return;
          wrapper.innerHTML = data.html;
          bindAccordion();
          bindJumpButtons();
          if (scrollToBest) {
            var slug = data.best_slug;
            if (slug) {
              openFaqBySlug(slug, true);
            } else {
              var best = wrapper.querySelector('.is-best-match');
              if (best) {
                best.open = true;
                best.scrollIntoView({ behavior: 'smooth', block: 'center' });
              }
            }
          }
          handleHashJump();
        });
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
          '" data-slug="' + item.slug + '" data-id="' + item.id + '" data-question="' + escapeHtml(item.question) + '">' +
          '<span class="faq-page__suggest-q">' + escapeHtml(item.question) + '</span>' +
          (item.category ? '<span class="faq-page__suggest-cat">' + escapeHtml(item.category) + '</span>' : '') +
          '</button>';
      }).join('');
      suggestPanel.hidden = false;
      suggestPanel.querySelectorAll('.faq-page__suggest-item').forEach(function(el) {
        el.addEventListener('click', function() {
          var slug = this.getAttribute('data-slug');
          searchInput.value = this.getAttribute('data-question') || '';
          hideSuggest();
          fetch(buildSearchUrl(searchInput.value.trim()), {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
          })
            .then(function(r) { return r.json(); })
            .then(function(data) {
              if (data.ok && data.html) {
                wrapper.innerHTML = data.html;
                bindAccordion();
                bindJumpButtons();
                openFaqBySlug(slug, true);
              }
            });
        });
      });
    }

    function doSuggest() {
      if (!faqSuggestUrl) return;
      var q = (searchInput.value || '').trim();
      fetch(buildSuggestUrl(q), { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function(r) { return r.json(); })
        .then(function(data) {
          if (data.ok) renderSuggest(data.suggestions);
        });
    }

    function handleHashJump() {
      var hash = window.location.hash;
      if (hash && hash.indexOf('#faq-') === 0) {
        openFaqBySlug(hash.replace('#faq-', ''), true);
      }
    }

    searchInput.addEventListener('input', function() {
      clearTimeout(suggestTimer);
      var q = (searchInput.value || '').trim();
      if (q.length === 0) {
        hideSuggest();
        doSearch(false);
        return;
      }
      if (q.length < 2) {
        hideSuggest();
        return;
      }
      suggestTimer = setTimeout(doSuggest, 150);
    });

    searchInput.addEventListener('focus', function() {
      var q = (searchInput.value || '').trim();
      if (q.length >= 2) doSuggest();
    });

    searchInput.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        hideSuggest();
        var q = (searchInput.value || '').trim();
        if (q.length === 0) {
          doSearch(false);
        } else if (q.length >= 2) {
          doSearch(true);
        }
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
      } else if (e.key === 'Enter' && highlightIndex >= 0) {
        e.preventDefault();
        items[highlightIndex].click();
        return;
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

    bindAccordion();
    bindJumpButtons();
    handleHashJump();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFaq);
  } else {
    initFaq();
  }
})();
