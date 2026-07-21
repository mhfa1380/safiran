/**
 * صفحه اصلی — متن چرخشی هیرو
 */
(function () {
  'use strict';

  var ROTATOR_LINES = [
    'با همراهی مشاوران مجرب، مسیر تحصیل در برترین دانشگاه‌های جهان را هموار کنید.',
    'از دریافت پذیرش تا اخذ ویزا، در کنار شما هستیم تا با کمترین هزینه و زمان به رویاهای تحصیلی‌تان برسید.',
    'بورسیه و فاند تحصیلی برای کارشناسی، ارشد و دکتری — با ارزیابی هوشمند مسیر مناسب را پیدا کنید.',
    'کانادا، آلمان، چین، اسپانیا و ده‌ها مقصد دیگر؛ کشور و دانشگاه را متناسب با هدف شما انتخاب می‌کنیم.',
    'مشاوره تخصصی، مکاتبه با دانشگاه‌ها و تکمیل پرونده — همه در یک مسیر شفاف و قابل پیگیری.',
    'آینده روشن شما با تیمی که سال‌ها در مهاجرت تحصیلی همراه دانشجویان بوده است.',
    'ارزیابی رایگان شرایط شما؛ پیشنهاد واقع‌بینانه برای پذیرش، بورسیه و برنامه‌ریزی مالی.',
    'ویزای تحصیلی، استقرار در مقصد و پشتیبانی پس از ورود — تا آرامش خاطر در مسیر مهاجرت.'
  ];

  var INTERVAL_MS = 4800;
  var FADE_MS = 550;

  function shuffle(arr) {
    var copy = arr.slice();
    for (var i = copy.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = copy[i];
      copy[i] = copy[j];
      copy[j] = tmp;
    }
    return copy;
  }

  function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  function initHeroRotator() {
    var rotator = document.getElementById('indexHeroRotator');
    if (!rotator) return;

    var lineEl = rotator.querySelector('[data-index-hero-line]');
    if (!lineEl) return;

    var queue = shuffle(ROTATOR_LINES);
    var index = 0;
    var timer = null;
    var transitioning = false;

    function currentText() {
      return lineEl.textContent.trim();
    }

    function nextLine() {
      var next = queue[index];
      index = (index + 1) % queue.length;
      if (index === 0) {
        queue = shuffle(ROTATOR_LINES);
      }
      if (next === currentText()) {
        return queue[index++] || ROTATOR_LINES[0];
      }
      return next;
    }

    function setLine(text) {
      lineEl.textContent = text;
      lineEl.classList.add('index-hero__line--active');
      lineEl.classList.remove('index-hero__line--exit');
    }

    function rotate() {
      if (transitioning) return;
      transitioning = true;

      lineEl.classList.remove('index-hero__line--active');
      lineEl.classList.add('index-hero__line--exit');

      window.setTimeout(function () {
        setLine(nextLine());
        transitioning = false;
      }, FADE_MS);
    }

    if (prefersReducedMotion()) {
      return;
    }

    timer = window.setInterval(rotate, INTERVAL_MS);

    document.addEventListener('visibilitychange', function () {
      if (document.hidden) {
        if (timer) window.clearInterval(timer);
        timer = null;
      } else if (!timer) {
        timer = window.setInterval(rotate, INTERVAL_MS);
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initHeroRotator);
  } else {
    initHeroRotator();
  }
})();
