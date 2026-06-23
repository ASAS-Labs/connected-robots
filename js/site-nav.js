/**
 * Site navigation: top-right menu toggle, right-hand drawer panel.
 */
(function () {
  var nav = document.querySelector('.site-nav.nav-tab') || document.querySelector('.nav-tab');
  var toggle = document.getElementById('site-nav-toggle') || document.querySelector('.nav-hamburger');
  var panel = document.getElementById('site-nav-panel') || document.querySelector('.nav-links');
  if (!nav || !toggle || !panel) return;

  var focusableSelector = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';

  function getFocusable() {
    return Array.prototype.slice.call(panel.querySelectorAll(focusableSelector))
      .filter(function (el) { return el.offsetParent !== null || el === document.activeElement; });
  }

  function setOpen(open) {
    nav.classList.toggle('expanded', open);
    toggle.classList.toggle('active', open);
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    document.body.style.overflow = open ? 'hidden' : '';

    if ('inert' in panel) {
      panel.inert = !open;
    }

    if (open) {
      var focusables = getFocusable();
      if (focusables.length) focusables[0].focus();
    } else {
      toggle.focus();
    }
  }

  toggle.addEventListener('click', function (e) {
    e.stopPropagation();
    setOpen(!nav.classList.contains('expanded'));
  });

  document.addEventListener('click', function (e) {
    if (!nav.classList.contains('expanded')) return;
    if (e.target.closest('.nav-hamburger') || e.target.closest('.nav-links')) return;
    setOpen(false);
  });

  document.addEventListener('keydown', function (e) {
    if (!nav.classList.contains('expanded')) return;

    if (e.key === 'Escape') {
      setOpen(false);
      return;
    }

    if (e.key !== 'Tab') return;

    var focusables = getFocusable();
    if (!focusables.length) return;

    var first = focusables[0];
    var last = focusables[focusables.length - 1];

    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  });
})();
