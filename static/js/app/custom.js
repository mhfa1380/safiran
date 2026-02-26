(function ($) {
  "use strict";

  var review = $('.player_info_item');
  if (review.length) {
    review.owlCarousel({
      items: 1,
      loop: true,
      dots: false,
      autoplay: true,
      margin: 40,
      autoplayHoverPause: true,
      autoplayTimeout: 5000,
      nav: true,
      navText: [
        '<img src="' + (window.STATIC_URL || '/static/') + 'img/icon/left.svg" alt="">',
        '<img src="' + (window.STATIC_URL || '/static/') + 'img/icon/right.svg" alt="">'
      ],
      responsive: {
        0: {
          margin: 15,
        },
        600: {
          margin: 10,
        },
        1000: {
          margin: 10,
        }
      }
    });
  }
  var popupYoutube = $('.popup-youtube, .popup-vimeo');
  if (popupYoutube.length) {
    popupYoutube.magnificPopup({
      type: 'iframe',
      mainClass: 'mfp-fade',
      removalDelay: 160,
      preloader: false,
      fixedContentPos: false
    });
  }

  var review = $('.textimonial_iner');
  if (review.length) {
    review.owlCarousel({
      items: 1,
      loop: true,
      dots: true,
      autoplay: true,
      autoplayHoverPause: true,
      autoplayTimeout: 5000,
      nav: false,
      responsive: {
        0: {
          margin: 15,
        },
        600: {
          margin: 10,
        },
        1000: {
          margin: 10,
        }
      }
    });
  }
  $(document).ready(function() {
    var niceSelectTarget = $('.form-select select, .default-select select');
    if (niceSelectTarget.length && typeof $.fn.niceSelect === 'function') {
      niceSelectTarget.niceSelect();
    }
  });
  /* menu fixed moved to base.js */

//   $(document).ready(function(){

//     var owl_1 = $('#owl-1');
//     var owl_2 = $('#owl-2');

//     owl_1.owlCarousel({
//       loop:true,
//       margin:10,
//       nav:false,
//       items: 1,
//       dots: false,
//       navText: false,
//       autoplay: true,
      
//     });
//  owl_2.find(".item").click(function(){
//     var slide_index = owl_2.find(".item").index(this);
//     owl_1.trigger('to.owl.carousel',[slide_index,300]);
//   });

//     owl_2.owlCarousel({
//       margin:50,
//       nav: true,
//       items: 3,
//       dots: false,
//       center: true,
//       loop:true,
//       navText: false,
//       autoplay: true,
//       center: true
//     });
    
//   });
 

  var persianDigits = '۰۱۲۳۴۵۶۷۸۹';
  function toPersianNum(n) {
    var num = parseInt(n, 10);
    if (isNaN(num) || num < 0) num = 0;
    return String(num).replace(/[0-9]/g, function(d) { return persianDigits[+d]; });
  }
  function initAnimatedCounters() {
    var nodes = document.querySelectorAll('.counter, .counter-persian');
    if (!nodes.length) return;

    function getTarget(el) {
      var raw = el.getAttribute('data-value') || el.getAttribute('data-value') || '0';
      var target = parseInt(String(raw).replace(/\D/g, ''), 10);
      if (isNaN(target) || target < 0) target = 0;
      return target;
    }

    function animateEl(el) {
      var target = getTarget(el);
      var isPersian = el.classList.contains('counter-persian');
      var duration = 2000;
      var startTime = null;

      function step(timestamp) {
        if (!startTime) startTime = timestamp;
        var progress = Math.min((timestamp - startTime) / duration, 1);
        var current = Math.round(target * progress);
        el.textContent = isPersian ? toPersianNum(current) : String(current);
        if (progress < 1) {
          window.requestAnimationFrame(step);
        }
      }

      window.requestAnimationFrame(step);
    }

    if ('IntersectionObserver' in window) {
      var observer = new IntersectionObserver(function(entries, obs) {
        entries.forEach(function(entry) {
          if (entry.isIntersecting) {
            animateEl(entry.target);
            obs.unobserve(entry.target);
          }
        });
      }, { threshold: 0.4 });

      nodes.forEach(function(el) { observer.observe(el); });
    } else {
      nodes.forEach(animateEl);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAnimatedCounters);
  } else {
    initAnimatedCounters();
  }

  var sliderEl = $('.slider');
  if (sliderEl.length && typeof $.fn.slick === 'function') {
  sliderEl.slick({
    slidesToShow: 1,
    slidesToScroll: 1,
    arrows: false,
    speed: 300,
    infinite: true,
    asNavFor: '.slider-nav-thumbnails',
    autoplay:true,
    pauseOnFocus: true,
    dots: true,
  });
 
  var sliderNav = $('.slider-nav-thumbnails');
  if (sliderNav.length && typeof $.fn.slick === 'function') {
  sliderNav.slick({
    slidesToShow: 3,
    slidesToScroll: 1,
    asNavFor: '.slider',
    focusOnSelect: true,
    infinite: true,
    prevArrow: false,
    nextArrow: false,
    centerMode: true,
    responsive: [
      {
        breakpoint: 480,
        settings: {
          centerMode: false,
        }
      }
    ]
  });
 
  //remove active class from all thumbnail slides
  sliderNav.find('.slick-slide').removeClass('slick-active');
 
  //set active class to first thumbnail slides
  sliderNav.find('.slick-slide').eq(0).addClass('slick-active');
 
  // On before slide change match active thumbnail to current slide
  sliderEl.on('beforeChange', function (event, slick, currentSlide, nextSlide) {
    var mySlideNumber = nextSlide;
    sliderNav.find('.slick-slide').removeClass('slick-active');
    sliderNav.find('.slick-slide').eq(mySlideNumber).addClass('slick-active');
  });
  }
  }
 
 //UPDATED 
  if (sliderEl.length && typeof $.fn.slick === 'function') {
 $('.slider').on('afterChange', function(event, slick, currentSlide){   
   $('.content').hide();
   $('.content[data-id=' + (currentSlide + 1) + ']').show();
 });
  }

  var galleryImg = $('.gallery_img');
  if (galleryImg.length && typeof $.fn.magnificPopup === 'function') {
  galleryImg.magnificPopup({
  type: 'image',
  gallery:{
    enabled:true
  }
});
  }


}(jQuery));