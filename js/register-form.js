/**
 * EARS-CONN unified registration: tier selection, participation_mode,
 * workshop-only fields, early-bird cutoff (local calendar through December 18, 2026),
 * thank-you / duplicate query handling.
 */
(function () {
  /* End of December 18, 2026 local time → first moment of December 19. */
  var EARLY_LAST_MOMENT = new Date(2026, 11, 19, 0, 0, 0);
  var prevTier = '';

  function earlyBirdOpen() {
    return new Date() < EARLY_LAST_MOMENT;
  }

  function isWorkshopTier(tier) {
    return tier === 'workshop_full' || tier === 'workshop_online';
  }

  function getSelectedTier() {
    var el = document.querySelector('input[name="registration_tier"]:checked');
    return el ? el.value : '';
  }

  function syncTierUi() {
    var tier = getSelectedTier();
    var prevWasConference = prevTier !== '' && !isWorkshopTier(prevTier);
    var pm = document.getElementById('reg-participation-mode');
    var wblock = document.getElementById('reg-workshop-only');
    var laptop = document.getElementById('laptop');
    var earlyInput = document.getElementById('reg-tier-conf-early');
    var earlyRow = earlyInput ? earlyInput.closest('.ws-radio-row') : null;

    if (earlyInput && earlyRow) {
      var open = earlyBirdOpen();
      earlyInput.disabled = !open;
      earlyRow.style.opacity = open ? '' : '0.55';
      earlyRow.title = open ? '' : 'Early registration ended on December 18, 2026.';
      if (!open && tier === 'conf_early') {
        var std = document.getElementById('reg-tier-conf-standard');
        if (std) std.checked = true;
        tier = getSelectedTier();
      }
    }

    if (pm) {
      pm.value = tier === 'workshop_online' ? 'remote' : 'in_person';
    }

    if (wblock) {
      var show = isWorkshopTier(tier);
      wblock.hidden = !show;
      wblock.setAttribute('aria-hidden', show ? 'false' : 'true');
    }

    if (laptop) {
      laptop.required = isWorkshopTier(tier);
      if (!isWorkshopTier(tier)) {
        laptop.value = 'no';
        laptop.removeAttribute('aria-required');
      } else {
        laptop.setAttribute('aria-required', 'true');
        if (prevWasConference && isWorkshopTier(tier) && laptop.value === 'no') {
          laptop.value = '';
        }
      }
    }

    var ackText = document.getElementById('reg-ack-label-text');
    if (ackText) {
      if (tier === 'conf_free_request') {
        ackText.textContent = 'I understand that free tickets are limited, that this is a request only, and that organizers will confirm eligibility by email. ';
      } else if (isWorkshopTier(tier)) {
        ackText.textContent = 'I understand that submitting this form does not guarantee a hands-on training seat, and that seats are limited. ';
      } else {
        ackText.textContent = 'I understand that organizers will confirm eligibility (including student rate where applicable) and send payment or access instructions separately. ';
      }
    }

    prevTier = tier;
  }

  function handleQueryFlags() {
    var params = new URLSearchParams(window.location.search);
    var thanks = params.get('thanks') === '1';
    var duplicate = params.get('duplicate') === '1';
    var formSection = document.getElementById('ws-form-section');
    var thanksBanner = document.getElementById('ws-thanks');
    var modal = document.getElementById('ws-duplicate-modal');
    var closeBtn = document.getElementById('ws-dup-close');

    if (thanks && thanksBanner) {
      thanksBanner.hidden = false;
      if (formSection) formSection.hidden = true;
      if (window.history && window.history.replaceState) {
        window.history.replaceState({}, '', window.location.pathname);
      }
    }

    function closeDuplicate() {
      if (!modal) return;
      modal.hidden = true;
      document.body.style.overflow = '';
      if (window.history && window.history.replaceState) {
        window.history.replaceState({}, '', window.location.pathname);
      }
    }

    if (duplicate && modal) {
      modal.hidden = false;
      document.body.style.overflow = 'hidden';
      if (closeBtn) closeBtn.focus();
      if (closeBtn) closeBtn.addEventListener('click', closeDuplicate);
      modal.addEventListener('click', function (e) {
        if (e.target === modal) closeDuplicate();
      });
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && !modal.hidden) closeDuplicate();
      });
    }
  }

  function applyHashTier() {
    var hash = (window.location.hash || '').replace(/^#/, '');
    var map = {
      'reg-early': 'conf_early',
      'reg-free': 'conf_free_request',
      'reg-student': 'conf_student',
      'reg-standard': 'conf_standard',
      'reg-workshop': 'workshop_full'
    };
    var tier = map[hash];
    if (!tier) return;
    if (tier === 'conf_early' && !earlyBirdOpen()) return;
    var input = document.querySelector('input[name="registration_tier"][value="' + tier + '"]');
    if (input && !input.disabled) {
      input.checked = true;
      syncTierUi();
      input.focus({ preventScroll: true });
      var legend = document.getElementById('tier-legend');
      if (legend && legend.scrollIntoView) {
        legend.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }

  function bind() {
    handleQueryFlags();

    var earlyInput = document.getElementById('reg-tier-conf-early');
    var stdInput = document.getElementById('reg-tier-conf-standard');
    if (earlyBirdOpen() && earlyInput && stdInput && stdInput.checked) {
      earlyInput.checked = true;
    }

    document.querySelectorAll('input[name="registration_tier"]').forEach(function (el) {
      el.addEventListener('change', syncTierUi);
    });
    syncTierUi();
    applyHashTier();
    window.addEventListener('hashchange', applyHashTier);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bind);
  } else {
    bind();
  }
})();
