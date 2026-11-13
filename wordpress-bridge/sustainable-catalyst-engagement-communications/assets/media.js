/* Media v8.8.4: visitor-initiated embeds only; no analytics or external requests on load. */
(function () {
  'use strict';
  function permitted(url, kind) {
    try {
      var parsed = new URL(url);
      if (parsed.protocol !== 'https:' || parsed.username || parsed.password || parsed.port) return false;
      if (kind === 'youtube') {
        return parsed.hostname === 'www.youtube-nocookie.com' &&
          (/^\/embed\/[A-Za-z0-9_-]{11}$/.test(parsed.pathname) || parsed.pathname === '/embed/videoseries');
      }
      if (kind === 'substack') {
        return parsed.hostname.indexOf('.') !== -1 &&
          !/\.(?:local|test|invalid|internal)$/.test(parsed.hostname) &&
          parsed.hostname !== 'localhost' && parsed.pathname === '/embed' && !parsed.search;
      }
      return false;
    } catch (error) { return false; }
  }
  document.addEventListener('click', function (event) {
    var button = event.target.closest('.scec-media button[data-scec-embed]');
    if (!button || button.disabled) return;
    var kind = button.getAttribute('data-scec-kind');
    var url = button.getAttribute('data-scec-embed') || '';
    if (!permitted(url, kind)) return;
    var holder = button.closest('.scec-media-load-wrap');
    if (!holder) return;
    var frame = document.createElement('iframe');
    frame.setAttribute('title', button.getAttribute('data-scec-embed-title') || 'External media');
    frame.setAttribute('loading', 'lazy');
    frame.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
    frame.setAttribute('allowfullscreen', '');
    frame.setAttribute('allow', 'encrypted-media; picture-in-picture; fullscreen');
    frame.src = url;
    frame.className = 'scec-media-frame';
    holder.replaceChildren(frame);
  });
}());
