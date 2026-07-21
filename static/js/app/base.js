/**
 * base.js - اسکریپت‌های مشترک در تمام صفحات
 * شامل: منوی ثابت هنگام اسکرول
 */
(function($) {
  'use strict';

  // صفحه اول: menu_fixed با اسکرول — صفحات داخلی: CSS با :has(.page-hero)
  if (!document.querySelector('.page-hero')) {
    var $menu = $('.main_menu');
    function syncScrollMenuFixed() {
      var window_top = $(window).scrollTop() + 1;
      var menuOpen = document.body.classList.contains('site-header-menu-open');
      if (window_top > 50 || menuOpen) {
        $menu.addClass('menu_fixed animated fadeInDown');
      } else {
        $menu.removeClass('menu_fixed animated fadeInDown');
      }
    }

    $(window).on('scroll', syncScrollMenuFixed);
    syncScrollMenuFixed();
  }
})(jQuery);
