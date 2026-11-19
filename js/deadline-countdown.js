/**
 * Shows days remaining until the next EARS-CONN deadline in America/New_York.
 * Updates at most once per minute. Hides when every deadline has passed.
 */
(function () {
  var el = document.getElementById('deadline-countdown');
  if (!el) return;

  var deadlines = [
    { y: 2026, m: 12, d: 12, label: 'Papers and Innovation Challenge deadline' },
    { y: 2026, m: 12, d: 18, label: 'Conference early bird' },
    { y: 2026, m: 12, d: 25, label: 'Workshop early bird' },
    { y: 2027, m: 1, d: 19, label: 'Event starts' }
  ];

  function nyDayNumber(date) {
    var parts = new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/New_York',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    }).formatToParts(date);
    function get(type) {
      for (var i = 0; i < parts.length; i++) {
        if (parts[i].type === type) return parts[i].value;
      }
      return '0';
    }
    return Date.UTC(Number(get('year')), Number(get('month')) - 1, Number(get('day')));
  }

  function render() {
    var today = nyDayNumber(new Date());
    var next = null;
    var days = 0;
    for (var i = 0; i < deadlines.length; i++) {
      var item = deadlines[i];
      var target = Date.UTC(item.y, item.m - 1, item.d);
      var delta = Math.round((target - today) / 86400000);
      if (delta >= 0) {
        next = item;
        days = delta;
        break;
      }
    }
    if (!next) {
      el.hidden = true;
      el.textContent = '';
      return;
    }
    var text = days === 0
      ? (next.label === 'Event starts' ? 'Event starts today' : next.label + ' is today')
      : days + (days === 1 ? ' day' : ' days') + ' until ' + next.label;
    if (el.textContent !== text) el.textContent = text;
    el.hidden = false;
  }

  render();
  setInterval(render, 60000);
})();
