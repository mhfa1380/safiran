/**
 * Page-specific scripts extracted from Django templates.
 * Uses window.PAGE_CONFIG for Django URLs (set by templates).
 */
(function() {
  'use strict';

  var config = window.PAGE_CONFIG || {};

  /**
   * Blog carousel on index page (Owl Carousel)
   */
  function initBlogCarousel() {
    var carousel = document.querySelector('.blog-carousel');
    if (!carousel || !carousel.querySelector('.item')) return;

    if (typeof jQuery !== 'undefined' && jQuery.fn.owlCarousel) {
      jQuery('.blog-carousel').owlCarousel({
        rtl: true,
        items: 3,
        loop: true,
        margin: 24,
        nav: false,
        dots: true,
        autoplay: true,
        autoplayTimeout: 5000,
        autoplayHoverPause: true,
        responsive: {
          0: { items: 1, margin: 16 },
          576: { items: 2, margin: 20 },
          992: { items: 3, margin: 24 }
        }
      });
    }
  }

  /**
   * FAQ search and accordion
   */
  function initFaq() {
    var wrapper = document.getElementById('faq-content-wrapper');
    var searchInput = document.getElementById('faq-search-input');
    if (!wrapper || !searchInput) return;

    var faqSearchUrl = config.faqSearchUrl || '';
    var debounceTimer;

    function bindAccordion() {
      var triggers = wrapper.querySelectorAll('[data-faq-toggle]');
      triggers.forEach(function(btn) {
        btn.onclick = function() {
          var item = this.closest('.faq_item');
          var wasActive = item.classList.contains('active');
          wrapper.querySelectorAll('.faq_item').forEach(function(i) { i.classList.remove('active'); });
          wrapper.querySelectorAll('[data-faq-toggle]').forEach(function(b) { b.setAttribute('aria-expanded', 'false'); });
          if (!wasActive) {
            item.classList.add('active');
            this.setAttribute('aria-expanded', 'true');
          }
        };
      });
    }

    function doSearch() {
      var q = (searchInput.value || '').trim();
      var url = faqSearchUrl + (q ? '?q=' + encodeURIComponent(q) : '');
      if (!url) return;
      fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function(r) { return r.json(); })
        .then(function(data) {
          if (data.ok && data.html) {
            wrapper.innerHTML = data.html;
            bindAccordion();
          }
        });
    }

    searchInput.addEventListener('input', function() {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(doSearch, 280);
    });

    bindAccordion();
  }

  /**
   * Schools list - quick consultation modal
   */
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

  /**
   * School detail - gallery popup (Magnific Popup)
   */
  function initPopupGallery() {
    var gallery = document.querySelector('.popup-gallery');
    if (!gallery || typeof jQuery === 'undefined' || !jQuery.fn.magnificPopup) return;

    jQuery('.popup-gallery').magnificPopup({
      type: 'image',
      gallery: { enabled: true },
      mainClass: 'mfp-fade'
    });
  }

  /**
   * Appointment - day select loads slots via AJAX
   */
  function initAppointmentSlots() {
    var daySelect = document.getElementById('appt-day-select');
    var slotsWrapper = document.getElementById('appt-slots-wrapper');
    if (!daySelect || !slotsWrapper) return;

    var slotsUrl = config.appointmentSlotsUrl || '';

    daySelect.addEventListener('change', function() {
      var day = this.value;
      if (!day || !slotsUrl) return;

      var url = slotsUrl + '?day=' + encodeURIComponent(day);
      fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function(res) { return res.json(); })
        .then(function(data) {
          if (data.ok && data.html) {
            slotsWrapper.innerHTML = data.html;
          }
        })
        .catch(function() {});
    });
  }

  /**
   * Initialize all page modules on DOM ready
   */
  function init() {
    initBlogCarousel();
    initFaq();
    initConsultModal();
    initPopupGallery();
    initAppointmentSlots();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
