/**
 * صفحه رزرو مشاوره — انتخاب روز، مودال ساعت، کارت‌ها
 */
(function () {
  'use strict';

  var config = window.PAGE_CONFIG || {};
  var lastFocus = null;

  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function qsa(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  function setSelectedCards(container, selector) {
    if (!container) return;
    qsa(selector, container).forEach(function (card) {
      var input = card.querySelector('input[type="radio"]');
      if (!input) return;
      card.classList.toggle('is-selected', input.checked);
      input.addEventListener('change', function () {
        qsa(selector, container).forEach(function (c) {
          var inp = c.querySelector('input[type="radio"]');
          c.classList.toggle('is-selected', inp && inp.checked);
        });
        highlightStepForField(input.name);
      });
    });
  }

  function headerScrollOffset() {
    var header = document.getElementById('site-header');
    return (header ? header.getBoundingClientRect().height : 68) + 20;
  }

  function setActiveStep(step) {
    var active = Math.max(1, Math.min(4, step || 1));
    qsa('.appt-page__step, .appt-page__progress-item').forEach(function (el) {
      var n = parseInt(el.getAttribute('data-appt-step'), 10);
      el.classList.toggle('is-active', n === active);
      el.classList.toggle('is-done', n < active);
    });
  }

  function highlightStepForField(name) {
    var stepMap = {
      full_name: 1, phone: 1, email: 1,
      consultation_type: 2, country: 2,
      slot: 3, day: 3,
      description: 4,
      referral_source: 4,
      referral_social_platform: 4,
      referral_detail: 4,
      captcha_answer: 4
    };
    setActiveStep(stepMap[name] || 1);
  }

  function clearFormErrorState(form) {
    qsa('.appt-page__field.has-error, .form-captcha.has-error', form).forEach(function (el) {
      el.classList.remove('has-error');
    });
    qsa('.is-invalid', form).forEach(function (el) {
      el.classList.remove('is-invalid');
      el.removeAttribute('aria-invalid');
    });
  }

  function markFieldError(field) {
    if (!field) return;
    field.classList.add('has-error');
    qsa('input.form-control, textarea.form-control', field).forEach(function (input) {
      input.classList.add('is-invalid');
      input.setAttribute('aria-invalid', 'true');
    });
    var timeTrigger = field.querySelector('#appt-time-trigger');
    if (timeTrigger) {
      timeTrigger.classList.add('is-invalid');
      timeTrigger.setAttribute('aria-invalid', 'true');
    }
  }

  function scrollToFirstFormError() {
    var form = qs('#appt-form');
    if (!form) return false;

    var errorEl = qs('.appt-page__error, .form-captcha__error', form);
    if (!errorEl) return false;

    clearFormErrorState(form);

    var field = errorEl.closest('.appt-page__field');
    var captchaBlock = errorEl.closest('.form-captcha');
    var scrollTarget = field || captchaBlock || errorEl.closest('[data-appt-section]') || errorEl;

    if (field) markFieldError(field);
    if (captchaBlock) {
      captchaBlock.classList.add('has-error');
      var captchaInput = captchaBlock.querySelector('.form-control');
      if (captchaInput) {
        captchaInput.classList.add('is-invalid');
        captchaInput.setAttribute('aria-invalid', 'true');
      }
    }

    var section = scrollTarget.closest('[data-appt-section]');
    if (section) {
      setActiveStep(parseInt(section.getAttribute('data-appt-section'), 10));
    } else {
      setActiveStep(4);
    }

    var focusName = null;
    if (field) {
      var named = field.querySelector('[name]');
      if (named) focusName = named.name;
    } else if (captchaBlock) {
      focusName = 'captcha_answer';
    }
    if (focusName) highlightStepForField(focusName);

    var top = scrollTarget.getBoundingClientRect().top + window.pageYOffset - headerScrollOffset();
    window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });

    window.setTimeout(function () {
      var focusEl = null;
      if (field) {
        focusEl =
          field.querySelector('input.form-control, textarea.form-control') ||
          field.querySelector('#appt-time-trigger') ||
          field.querySelector('input:not(.appt-page__sr-only):not([type=hidden])');
      }
      if (!focusEl && captchaBlock) {
        focusEl = captchaBlock.querySelector('.form-control');
      }
      if (focusEl && typeof focusEl.focus === 'function') {
        try {
          focusEl.focus({ preventScroll: true });
        } catch (err) {
          focusEl.focus();
        }
      }
    }, 420);

    return true;
  }

  function initScrollSpy() {
    var sections = qsa('[data-appt-section]').sort(function (a, b) {
      return parseInt(a.getAttribute('data-appt-section'), 10) -
        parseInt(b.getAttribute('data-appt-section'), 10);
    });
    if (!sections.length) return;

    var ticking = false;

    function updateActiveFromScroll() {
      var offset = headerScrollOffset();
      var active = 1;
      sections.forEach(function (section) {
        var rect = section.getBoundingClientRect();
        if (rect.top - offset <= 72) {
          active = parseInt(section.getAttribute('data-appt-section'), 10) || active;
        }
      });
      setActiveStep(active);
      ticking = false;
    }

    window.addEventListener('scroll', function () {
      if (!ticking) {
        ticking = true;
        window.requestAnimationFrame(updateActiveFromScroll);
      }
    }, { passive: true });

    window.addEventListener('resize', updateActiveFromScroll, { passive: true });
    updateActiveFromScroll();
  }

  function initStepHighlight() {
    var form = qs('#appt-form');
    if (!form) return;
    qsa('input, select, textarea', form).forEach(function (el) {
      el.addEventListener('focus', function () {
        highlightStepForField(el.name);
      });
    });
  }

  /* ─── مودال ساعت ─── */
  function getModal() {
    return qs('#appt-time-modal');
  }

  function openTimeModal() {
    var modal = getModal();
    if (!modal) return;
    lastFocus = document.activeElement;
    modal.hidden = false;
    modal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('appt-modal-open');
    var closeBtn = qs('.appt-time-modal__close', modal);
    if (closeBtn) closeBtn.focus();
  }

  function closeTimeModal() {
    var modal = getModal();
    if (!modal) return;
    modal.hidden = true;
    modal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('appt-modal-open');
    if (lastFocus && typeof lastFocus.focus === 'function') {
      lastFocus.focus();
    }
  }

  function initTimeModal() {
    var modal = getModal();
    if (!modal) return;

    qsa('[data-appt-modal-close]', modal).forEach(function (el) {
      el.addEventListener('click', closeTimeModal);
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !modal.hidden) {
        closeTimeModal();
      }
    });
  }

  function setModalDateLabel(label) {
    var el = qs('#appt-time-modal-date');
    if (el) el.textContent = label || '';
  }

  function updateTimeTrigger(hasSelection, dayLabel, slotLabel) {
    var trigger = qs('#appt-time-trigger');
    var labelEl = qs('#appt-time-trigger-label');
    var subEl = qs('#appt-time-trigger-sub');
    if (!trigger || !labelEl || !subEl) return;

    if (hasSelection && slotLabel) {
      trigger.classList.add('is-filled');
      labelEl.textContent = slotLabel;
      subEl.textContent = dayLabel ? 'تاریخ: ' + dayLabel + ' — برای تغییر کلیک کنید' : 'برای تغییر ساعت کلیک کنید';
    } else if (dayLabel) {
      trigger.classList.remove('is-filled');
      labelEl.textContent = 'انتخاب ساعت مشاوره';
      subEl.textContent = 'برای ' + dayLabel + ' — کلیک کنید';
    } else {
      trigger.classList.remove('is-filled');
      labelEl.textContent = 'انتخاب ساعت مشاوره';
      subEl.textContent = 'پس از انتخاب تاریخ فعال می‌شود';
    }
  }

  function clearSlotSelection() {
    qsa('input[name="slot"]').forEach(function (input) {
      input.checked = false;
    });
    qsa('.appt-modal__slot').forEach(function (el) {
      el.classList.remove('is-selected');
    });
    var slotsWrapper = qs('#appt-slots-wrapper');
    if (slotsWrapper) {
      slotsWrapper.removeAttribute('data-loaded-day');
    }
    updateTimeTrigger(false, getActiveDayLabel(), null);
  }

  function getActiveDayLabel() {
    var active = qs('.appt-page__day-btn.is-active');
    return active ? active.getAttribute('data-day-label') || '' : '';
  }

  function syncModalSlots() {
    qsa('.appt-modal__slot').forEach(function (slot) {
      var input = slot.querySelector('input[type="radio"]');
      slot.classList.toggle('is-selected', input && input.checked);
    });
    var checked = qs('input[name="slot"]:checked');
    if (checked) {
      var dayLabel = getActiveDayLabel();
      var slotLabel = checked.getAttribute('data-slot-label') || checked.closest('label').textContent.trim();
      updateTimeTrigger(true, dayLabel, slotLabel);
    }
  }

  function slotsReadyForDay(slotsWrapper, day) {
    if (!slotsWrapper || !day) return false;
    if (slotsWrapper.getAttribute('data-loaded-day') !== day) return false;
    return !!slotsWrapper.querySelector('.appt-modal__slots-grid, .appt-modal__slots-empty');
  }

  function fetchSlotsAndOpenModal(day, dayLabel, openModal) {
    var slotsWrapper = qs('#appt-slots-wrapper');
    var slotsUrl = config.appointmentSlotsUrl || '';
    if (!slotsWrapper || !day || !slotsUrl) return;

    setModalDateLabel(dayLabel);

    if (slotsReadyForDay(slotsWrapper, day)) {
      bindSlotSelection();
      if (openModal) openTimeModal();
      return;
    }

    slotsWrapper.classList.add('is-loading');

    fetch(slotsUrl + '?day=' + encodeURIComponent(day), {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.ok && data.html) {
          slotsWrapper.innerHTML = data.html;
          slotsWrapper.setAttribute('data-loaded-day', day);
          bindSlotSelection();
          if (openModal) openTimeModal();
        }
      })
      .catch(function () {})
      .finally(function () {
        slotsWrapper.classList.remove('is-loading');
      });
  }

  function bindSlotSelection() {
    qsa('.appt-modal__slot input[type="radio"]').forEach(function (input) {
      input.addEventListener('change', function () {
        syncModalSlots();
        highlightStepForField('slot');
        if (input.checked) {
          window.setTimeout(closeTimeModal, 220);
        }
      });
    });
    syncModalSlots();
  }

  function initDayChips() {
    var daySelect = qs('#appt-day-select');
    var dayBtns = qsa('.appt-page__day-btn');
    var trigger = qs('#appt-time-trigger');
    if (!daySelect || !dayBtns.length) return;

    function selectDay(btn, openModal) {
      var day = btn.getAttribute('data-day');
      var dayLabel = btn.getAttribute('data-day-label') || '';
      if (!day) return;

      daySelect.value = day;
      dayBtns.forEach(function (b) {
        var active = b === btn;
        b.classList.toggle('is-active', active);
        b.setAttribute('aria-pressed', active ? 'true' : 'false');
      });

      if (trigger) {
        trigger.disabled = false;
      }

      clearSlotSelection();
      updateTimeTrigger(false, dayLabel, null);
      highlightStepForField('day');
      fetchSlotsAndOpenModal(day, dayLabel, openModal !== false);
    }

    dayBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        selectDay(btn, true);
      });
    });

    var activeBtn = qs('.appt-page__day-btn.is-active');
    var slotsWrapper = qs('#appt-slots-wrapper');
    if (activeBtn && trigger) {
      trigger.disabled = false;
      var label = activeBtn.getAttribute('data-day-label') || '';
      var day = activeBtn.getAttribute('data-day');
      if (slotsWrapper && day) {
        slotsWrapper.setAttribute('data-loaded-day', day);
        setModalDateLabel(label);
      }
      var preselected = qs('input[name="slot"]:checked');
      if (preselected) {
        syncModalSlots();
      } else {
        updateTimeTrigger(false, label, null);
      }
    }
  }

  function initTimeTrigger() {
    var trigger = qs('#appt-time-trigger');
    if (!trigger) return;
    trigger.addEventListener('click', function () {
      if (trigger.disabled) return;
      var activeBtn = qs('.appt-page__day-btn.is-active');
      if (!activeBtn) return;
      var day = activeBtn.getAttribute('data-day');
      var dayLabel = activeBtn.getAttribute('data-day-label') || '';
      fetchSlotsAndOpenModal(day, dayLabel, true);
    });
  }

  function validateReferralOnSubmit(form) {
    var picker = qs('[data-referral-picker]', form);
    if (!picker || !window.SafiranReferralSource) return true;
    return window.SafiranReferralSource.validate(picker);
  }

  function initFormSubmit() {
    var form = qs('#appt-form');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      if (!validateReferralOnSubmit(form)) {
        e.preventDefault();
        setActiveStep(4);
        var picker = qs('[data-referral-picker]', form);
        if (picker) {
          var top = picker.getBoundingClientRect().top + window.pageYOffset - headerScrollOffset();
          window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
        }
      }
    });
  }

  function init() {
    setSelectedCards(document, '.appt-page__type-card');
    setSelectedCards(document, '.appt-page__country-chip');
    initTimeModal();
    initDayChips();
    initTimeTrigger();
    initStepHighlight();
    initScrollSpy();
    bindSlotSelection();
    initFormSubmit();

    var preselected = qs('input[name="slot"]:checked');
    if (preselected) {
      syncModalSlots();
    }

    window.requestAnimationFrame(function () {
      scrollToFirstFormError();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
