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

    var freeNext = document.getElementById('reg-free-next');
    if (freeNext) freeNext.hidden = tier !== 'conf_free_request';

    var ackText = document.getElementById('reg-ack-label-text');
    if (ackText) {
      if (tier === 'conf_free_request') {
        ackText.textContent = 'I understand that free tickets are only for CUNY students, that this is a request only, and that organizers will confirm eligibility by email. ';
      } else if (isWorkshopTier(tier)) {
        ackText.textContent = 'I understand that submitting this form does not guarantee a hands-on training seat, and that seats are limited. ';
      } else {
        ackText.textContent = 'I understand that organizers will confirm eligibility (including student rate where applicable) and send payment or access instructions separately. ';
      }
    }

    prevTier = tier;
  }

  var ERROR_TEXT = {
    verification: 'Human verification failed or expired. Complete the check above the submit button and try again.',
    phone: 'Enter a phone number with 8 to 15 digits, including the country code.',
    email: 'Enter a valid email address.',
    name: 'Enter your full name.',
    country: 'Select your country or territory.',
    ack: 'Check the acknowledgement box to continue.',
    early: 'Early registration has ended. Choose another registration option.',
    laptop: 'Say whether you will bring a laptop for the workshop.',
    tier: 'Select a registration option.'
  };

  function phoneOk(phone) {
    var digits = String(phone || '').replace(/\D/g, '');
    return digits.length >= 8 && digits.length <= 15 && String(phone || '').length <= 24;
  }

  var DIAL={AF:'93',AL:'355',DZ:'213',AS:'1',AD:'376',AO:'244',AI:'1',AG:'1',AR:'54',AM:'374',AW:'297',AU:'61',AT:'43',AZ:'994',BS:'1',BH:'973',BD:'880',BB:'1',BY:'375',BE:'32',BZ:'501',BJ:'229',BM:'1',BT:'975',BO:'591',BA:'387',BW:'267',BR:'55',IO:'246',VG:'1',BN:'673',BG:'359',BF:'226',BI:'257',KH:'855',CM:'237',CA:'1',CV:'238',BQ:'599',KY:'1',CF:'236',TD:'235',CL:'56',CN:'86',CX:'61',CC:'61',CO:'57',KM:'269',CK:'682',CR:'506',HR:'385',CU:'53',CW:'599',CY:'357',CZ:'420',DK:'45',DJ:'253',DM:'1',DO:'1',CD:'243',EC:'593',EG:'20',SV:'503',GQ:'240',ER:'291',EE:'372',SZ:'268',ET:'251',FK:'500',FO:'298',FJ:'679',FI:'358',FR:'33',GF:'594',PF:'689',TF:'262',GA:'241',GM:'220',GE:'995',DE:'49',GH:'233',GI:'350',GR:'30',GL:'299',GD:'1',GP:'590',GU:'1',GT:'502',GG:'44',GN:'224',GW:'245',GY:'592',HT:'509',HN:'504',HK:'852',HU:'36',IS:'354',IN:'91',ID:'62',IR:'98',IQ:'964',IE:'353',IM:'44',IL:'972',IT:'39',CI:'225',JM:'1',JP:'81',JE:'44',JO:'962',KZ:'7',KE:'254',KI:'686',XK:'383',KW:'965',KG:'996',LA:'856',LV:'371',LB:'961',LS:'266',LR:'231',LY:'218',LI:'423',LT:'370',LU:'352',MO:'853',MG:'261',MW:'265',MY:'60',MV:'960',ML:'223',MT:'356',MH:'692',MQ:'596',MR:'222',MU:'230',YT:'262',MX:'52',FM:'691',MD:'373',MC:'377',MN:'976',ME:'382',MS:'1',MA:'212',MZ:'258',MM:'95',NA:'264',NR:'674',NP:'977',NL:'31',NC:'687',NZ:'64',NI:'505',NE:'227',NG:'234',NU:'683',NF:'672',KP:'850',MK:'389',MP:'1',NO:'47',OM:'968',PK:'92',PW:'680',PS:'970',PA:'507',PG:'675',PY:'595',PE:'51',PH:'63',PN:'64',PL:'48',PT:'351',PR:'1',QA:'974',CG:'242',RO:'40',RU:'7',RW:'250',RE:'262',BL:'590',SH:'290',KN:'1',LC:'1',MF:'590',PM:'508',VC:'1',WS:'685',SM:'378',SA:'966',SN:'221',RS:'381',SC:'248',SL:'232',SG:'65',SX:'1',SK:'421',SI:'386',SB:'677',SO:'252',ZA:'27',KR:'82',SS:'211',ES:'34',LK:'94',SD:'249',SR:'597',SJ:'47',SE:'46',CH:'41',SY:'963',ST:'239',TW:'886',TJ:'992',TZ:'255',TH:'66',TL:'670',TG:'228',TK:'690',TO:'676',TT:'1',TN:'216',TR:'90',TM:'993',TC:'1',TV:'688',UG:'256',UA:'380',AE:'971',GB:'44',US:'1',UM:'1',VI:'1',UY:'598',UZ:'998',VU:'678',VA:'39',VE:'58',VN:'84',WF:'681',EH:'212',YE:'967',ZM:'260',ZW:'263',AX:'358'};
  var appliedDial = '';

  function syncPhoneDial() {
    var country = document.getElementById('country-code');
    var phone = document.getElementById('phone');
    if (!country || !phone) return;
    var next = DIAL[country.value] ? '+' + DIAL[country.value] : '';
    if (!next) return;
    var current = phone.value.trim();
    if (!current || current === appliedDial) {
      phone.value = next + ' ';
    } else if (appliedDial && current.indexOf(appliedDial) === 0) {
      var rest = current.slice(appliedDial.length).trim();
      phone.value = rest ? next + ' ' + rest : next + ' ';
    }
    appliedDial = next;
    phone.placeholder = next + ' 555 123 4567';
  }

  function showFormError(message, scroll) {
    var box = document.getElementById('reg-form-error');
    if (!box) return;
    box.textContent = message;
    box.hidden = false;
    if (scroll !== false && box.scrollIntoView) {
      box.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  function bindSubmitChecks() {
    var form = document.getElementById('ears-conn-register-form');
    var phone = document.getElementById('phone');
    if (!form) return;

    if (phone) {
      phone.addEventListener('input', function () {
        phone.setCustomValidity('');
      });
    }

    form.addEventListener('invalid', function () {
      showFormError('Complete the required fields, then submit again.', false);
    }, true);

    form.addEventListener('submit', function (e) {
      var token = form.querySelector('[name="cf-turnstile-response"]');
      var tsKey = typeof window.__TURNSTILE_SITE_KEY__ === 'string' ? window.__TURNSTILE_SITE_KEY__.trim() : '';
      if (!form.checkValidity()) {
        e.preventDefault();
        var first = form.querySelector(':invalid');
        showFormError('Complete the required fields, then submit again.');
        if (first && first.focus) first.focus();
        return;
      }
      if (phone && !phoneOk(phone.value)) {
        e.preventDefault();
        phone.setCustomValidity('Enter a phone number with 8 to 15 digits.');
        showFormError(ERROR_TEXT.phone);
        phone.focus();
        return;
      }
      if (tsKey && (!token || !token.value)) {
        e.preventDefault();
        showFormError(ERROR_TEXT.verification);
      }
    });
  }

  function handleQueryFlags() {
    var params = new URLSearchParams(window.location.search);
    var thanks = params.get('thanks') === '1';
    var duplicate = params.get('duplicate') === '1';
    var errorCode = params.get('error') || '';
    var formSection = document.getElementById('ws-form-section');
    var thanksBanner = document.getElementById('ws-thanks');
    var modal = document.getElementById('ws-duplicate-modal');
    var closeBtn = document.getElementById('ws-dup-close');

    if (errorCode && ERROR_TEXT[errorCode]) {
      showFormError(ERROR_TEXT[errorCode]);
      if (window.history && window.history.replaceState) {
        window.history.replaceState({}, '', window.location.pathname);
      }
    }

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
    bindSubmitChecks();

    var earlyInput = document.getElementById('reg-tier-conf-early');
    var stdInput = document.getElementById('reg-tier-conf-standard');
    if (earlyBirdOpen() && earlyInput && stdInput && stdInput.checked) {
      earlyInput.checked = true;
    }

    document.querySelectorAll('input[name="registration_tier"]').forEach(function (el) {
      el.addEventListener('change', syncTierUi);
    });
    syncTierUi();
    syncPhoneDial();
    var countrySelect = document.getElementById('country-code');
    if (countrySelect) countrySelect.addEventListener('change', syncPhoneDial);
    applyHashTier();
    window.addEventListener('hashchange', applyHashTier);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bind);
  } else {
    bind();
  }
})();
