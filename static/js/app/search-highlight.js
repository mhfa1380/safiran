/**
 * هایلایت عبارت جستجو در صفحه مقصد (?highlight=...)
 * پس از کلیک روی نتیجه جستجوی سراسری، کاربر به بخش مرتبط هدایت می‌شود.
 */
(function() {
  'use strict';

  var MAX_MARKS = 60;
  var SKIP_TAGS = /^(SCRIPT|STYLE|NOSCRIPT|MARK|INPUT|TEXTAREA|SELECT|BUTTON|OPTION|SVG|PATH)$/i;
  var SKIP_SELECTOR =
    'header, footer, nav, .site-header, .site-search-highlight-banner, ' +
    '.site-search-page, .site-header__search-panel, [hidden], [aria-hidden="true"]';

  function getHighlightQuery() {
    var params = new URLSearchParams(window.location.search);
    return (params.get('highlight') || '').trim();
  }

  function isSearchResultsPage() {
    return /\/search\/?$/i.test(window.location.pathname);
  }

  function normalizePersian(text) {
    if (!text) return '';
    return String(text)
      .replace(/[\u064A\u0649]/g, '\u06CC')
      .replace(/[\u0643\u06A9]/g, '\u06A9')
      .replace(/\u200c/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase();
  }

  function tokenize(query) {
    var norm = normalizePersian(query);
    if (!norm) return [];
    return norm.split(/\s+/).filter(function(t) {
      return t.length >= 2;
    });
  }

  function escapeRegExp(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  function charPattern(ch) {
    var c = normalizePersian(ch);
    if (c === '\u06cc') return '[\u064A\u0649\u06CC\u0649]';
    if (c === '\u06a9') return '[\u0643\u06A9]';
    return escapeRegExp(ch);
  }

  function tokenPattern(token) {
    return token.split('').map(charPattern).join('');
  }

  function buildTokenRegex(tokens) {
    var parts = tokens.map(tokenPattern);
    if (!parts.length) return null;
    return new RegExp('(' + parts.join('|') + ')', 'gi');
  }

  function shouldSkipNode(node) {
    var parent = node.parentElement;
    if (!parent) return true;
    if (SKIP_TAGS.test(parent.tagName)) return true;
    if (parent.closest(SKIP_SELECTOR)) return true;
    if (parent.isContentEditable) return true;
    return false;
  }

  function highlightTextNode(textNode, regex) {
    var text = textNode.nodeValue;
    if (!text || !regex.test(text)) return 0;
    regex.lastIndex = 0;
    var frag = document.createDocumentFragment();
    var last = 0;
    var count = 0;
    var match;
    while ((match = regex.exec(text)) !== null) {
      if (match.index > last) {
        frag.appendChild(document.createTextNode(text.slice(last, match.index)));
      }
      var mark = document.createElement('mark');
      mark.className = 'site-search-highlight';
      mark.setAttribute('data-search-highlight', '1');
      mark.textContent = match[0];
      frag.appendChild(mark);
      count += 1;
      last = regex.lastIndex;
      if (count >= MAX_MARKS) break;
    }
    if (count === 0) return 0;
    if (last < text.length) {
      frag.appendChild(document.createTextNode(text.slice(last)));
    }
    textNode.parentNode.replaceChild(frag, textNode);
    return count;
  }

  function walkAndHighlight(root, regex) {
    var total = 0;
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function(node) {
        if (shouldSkipNode(node)) return NodeFilter.FILTER_REJECT;
        if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var nodes = [];
    while (walker.nextNode()) {
      nodes.push(walker.currentNode);
    }
    nodes.forEach(function(node) {
      if (total >= MAX_MARKS) return;
      regex.lastIndex = 0;
      total += highlightTextNode(node, regex);
    });
    return total;
  }

  function pulseBlock(mark) {
    var block =
      mark.closest('section, article, details, .card, .faq-page__item, .country-page__item, .svc-card, h2, h3') ||
      mark.parentElement;
    if (!block) return;
    block.classList.add('site-search-highlight-block');
    window.setTimeout(function() {
      block.classList.remove('site-search-highlight-block');
    }, 2200);
  }

  function getHeaderOffset() {
    var header = document.querySelector('.site-header, .main_menu');
    return header ? header.getBoundingClientRect().height + 12 : 80;
  }

  function scrollToMark(mark, behavior) {
    if (!mark) return;
    var top = mark.getBoundingClientRect().top + window.pageYOffset - getHeaderOffset();
    window.scrollTo({ top: Math.max(0, top), behavior: behavior || 'smooth' });
    pulseBlock(mark);
  }

  function getMarks() {
    return Array.prototype.slice.call(
      document.querySelectorAll('mark.site-search-highlight[data-search-highlight]')
    );
  }

  function removeHighlights() {
    document.querySelectorAll('mark.site-search-highlight').forEach(function(mark) {
      var parent = mark.parentNode;
      if (!parent) return;
      parent.replaceChild(document.createTextNode(mark.textContent), mark);
      parent.normalize();
    });
    document.querySelectorAll('.site-search-highlight-block').forEach(function(el) {
      el.classList.remove('site-search-highlight-block');
    });
  }

  function stripHighlightFromUrl() {
    var url = new URL(window.location.href);
    url.searchParams.delete('highlight');
    var next = url.pathname + url.search + url.hash;
    window.history.replaceState({}, '', next);
  }

  function createBanner(query, total) {
    var existing = document.querySelector('.site-search-highlight-banner');
    if (existing) existing.remove();

    var banner = document.createElement('div');
    banner.className = 'site-search-highlight-banner';
    banner.setAttribute('role', 'status');
    banner.setAttribute('dir', 'rtl');

    var text = document.createElement('p');
    text.className = 'site-search-highlight-banner__text';
    if (total > 0) {
      text.textContent =
        total + ' مورد برای «' + query + '» در این صفحه یافت شد — با دکمه‌های زیر بین آن‌ها جابه‌جا شوید.';
    } else {
      text.textContent =
        'عبارت «' + query + '» در متن این صفحه پیدا نشد؛ ممکن است در بخش دیگری از سایت باشد.';
    }

    var actions = document.createElement('div');
    actions.className = 'site-search-highlight-banner__actions';

    var prevBtn = document.createElement('button');
    prevBtn.type = 'button';
    prevBtn.className = 'site-search-highlight-banner__nav';
    prevBtn.textContent = 'قبلی';
    prevBtn.setAttribute('aria-label', 'مورد قبلی');

    var nextBtn = document.createElement('button');
    nextBtn.type = 'button';
    nextBtn.className = 'site-search-highlight-banner__nav';
    nextBtn.textContent = 'بعدی';
    nextBtn.setAttribute('aria-label', 'مورد بعدی');

    var closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'site-search-highlight-banner__close';
    closeBtn.textContent = 'بستن';
    closeBtn.setAttribute('aria-label', 'بستن هایلایت جستجو');

    actions.appendChild(prevBtn);
    actions.appendChild(nextBtn);
    actions.appendChild(closeBtn);

    banner.appendChild(text);
    banner.appendChild(actions);
    document.body.appendChild(banner);

    return { banner: banner, prevBtn: prevBtn, nextBtn: nextBtn, closeBtn: closeBtn };
  }

  function init() {
    var query = getHighlightQuery();
    if (!query || isSearchResultsPage()) return;

    var tokens = tokenize(query);
    if (!tokens.length) return;

    var regex = buildTokenRegex(tokens);
    if (!regex) return;

    var root = document.getElementById('main-content');
    if (!root) return;

    var total = walkAndHighlight(root, regex);
    var marks = getMarks();
    var activeIndex = 0;

    function setActive(index) {
      if (!marks.length) return;
      activeIndex = (index + marks.length) % marks.length;
      marks.forEach(function(m, i) {
        m.classList.toggle('is-active', i === activeIndex);
      });
      scrollToMark(marks[activeIndex], 'smooth');
    }

    var ui = createBanner(query, marks.length);
    if (marks.length) {
      marks[0].classList.add('is-active');
      window.requestAnimationFrame(function() {
        scrollToMark(marks[0], 'auto');
      });
    }

    ui.prevBtn.disabled = !marks.length;
    ui.nextBtn.disabled = !marks.length;

    ui.prevBtn.addEventListener('click', function() {
      setActive(activeIndex - 1);
    });
    ui.nextBtn.addEventListener('click', function() {
      setActive(activeIndex + 1);
    });
    ui.closeBtn.addEventListener('click', function() {
      removeHighlights();
      ui.banner.remove();
      stripHighlightFromUrl();
    });

    document.addEventListener('keydown', function(e) {
      if (!document.querySelector('.site-search-highlight-banner')) return;
      if (e.key === 'Escape') {
        ui.closeBtn.click();
      } else if (e.key === 'F3' || (e.key === 'g' && (e.ctrlKey || e.metaKey))) {
        e.preventDefault();
        setActive(activeIndex + (e.shiftKey ? -1 : 1));
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
