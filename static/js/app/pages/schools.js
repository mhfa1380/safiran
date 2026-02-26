/**
 * صفحات دانشگاه‌ها - مودال مشاوره سریع و گالری پاپ‌آپ
 */
(function() {
  'use strict';

  var config = window.PAGE_CONFIG || {};

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

  function initPopupGallery() {
    var gallery = document.querySelector('.popup-gallery');
    if (!gallery || typeof jQuery === 'undefined' || !jQuery.fn.magnificPopup) return;

    jQuery('.popup-gallery').magnificPopup({
      type: 'image',
      gallery: { enabled: true },
      mainClass: 'mfp-fade'
    });
  }

  function initFilterToggle() {
    var btn = document.getElementById('schoolsFilterToggle');
    var wrap = document.getElementById('schoolsFilterWrap');
    if (!btn || !wrap) return;

    var labelShow = 'فیلتر کردن';
    var labelHide = 'بستن فیلتر';

    btn.addEventListener('click', function() {
      var isOpen = wrap.classList.toggle('is_open');
      btn.setAttribute('aria-expanded', isOpen);
      var labelEl = btn.querySelector('.schools_filter_toggle_label');
      if (labelEl) labelEl.textContent = isOpen ? labelHide : labelShow;
    });
  }

  function init() {
    initConsultModal();
    initPopupGallery();
    initFilterToggle();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
