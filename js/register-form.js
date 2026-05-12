/**
 * EARS-CONN unified registration: tier selection, participation_mode,
 * workshop-only fields, early-bird cutoff (local calendar through July 4, 2026).
 */
(function () {
  var EARLY_LAST_MOMENT = new Date(2026, 6, 5, 0, 0, 0);
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
      earlyRow.title = open ? '' : 'Early registration ended on July 4, 2026.';
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
      ackText.textContent = isWorkshopTier(tier)
        ? 'I understand that submitting this form does not guarantee a hands-on training seat, and that seats are limited. '
        : 'I understand that organizers will confirm eligibility (including student rate where applicable) and send payment or access instructions separately. ';
    }

    prevTier = tier;
  }

  function bind() {
    document.querySelectorAll('input[name="registration_tier"]').forEach(function (el) {
      el.addEventListener('change', syncTierUi);
    });
    syncTierUi();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bind);
  } else {
    bind();
  }
})();
