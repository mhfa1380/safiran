/**
 * صفحه رزرو مشاوره - بارگذاری اسلات‌ها با AJAX
 */
(function() {
  'use strict';

  var config = window.PAGE_CONFIG || {};

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

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAppointmentSlots);
  } else {
    initAppointmentSlots();
  }
})();
