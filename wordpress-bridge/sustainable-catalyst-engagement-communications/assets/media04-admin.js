/* MEDIA-04: deliberate user-initiated copy; no outbound network calls. */
(function () {
  'use strict';
  document.addEventListener('click', function (event) {
    var button = event.target.closest('button[data-scec-copy]');
    if (!button) return;
    var selector = button.getAttribute('data-scec-copy') || '';
    if (!/^#scec-copy-\d+-[a-z]+$/.test(selector)) return;
    var target = document.querySelector(selector);
    if (!target || target.tagName !== 'TEXTAREA') return;
    var original = button.textContent;
    function feedback(label) {
      button.textContent = label;
      window.setTimeout(function () { button.textContent = original; }, 1800);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(target.value).then(function () {
        feedback('Copied');
      }, function () { feedback('Select and copy manually'); target.focus(); target.select(); });
    } else {
      target.focus(); target.select();
      feedback('Selected — copy manually');
    }
  });
}());
