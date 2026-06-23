/**
 * Side-drawer site navigation (burger tab on left edge).
 */
(function () {
  var hamburger = document.querySelector('.nav-hamburger');
  var navTab = document.querySelector('.nav-tab');
  if (!hamburger || !navTab) return;

  hamburger.addEventListener('click', function (e) {
    e.stopPropagation();
    var expanded = navTab.classList.toggle('expanded');
    hamburger.classList.toggle('active', expanded);
    hamburger.setAttribute('aria-expanded', expanded);
  });

  document.addEventListener('click', function (e) {
    if (!navTab.classList.contains('expanded')) return;
    if (e.target.closest('.nav-hamburger') || e.target.closest('.nav-links')) return;
    navTab.classList.remove('expanded');
    hamburger.classList.remove('active');
    hamburger.setAttribute('aria-expanded', 'false');
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && navTab.classList.contains('expanded')) {
      navTab.classList.remove('expanded');
      hamburger.classList.remove('active');
      hamburger.setAttribute('aria-expanded', 'false');
    }
  });
})();
