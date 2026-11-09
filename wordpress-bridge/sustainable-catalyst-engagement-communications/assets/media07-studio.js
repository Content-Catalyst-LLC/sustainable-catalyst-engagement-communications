/* MEDIA-07 visual editor — WordPress admin only; no API sends or subscriptions. */
(function () {
  'use strict';

  var boot = window.SCEC07_BOOT || {};
  var $ = function (id) { return document.getElementById(id); };
  var editor, selectedId = 0, revision = 0, dirty = false, inFlight = false;
  var autosaveTimer = null, opening = false;

  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (ch) {
      return { '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[ch];
    });
  }
  function safeURL(value) {
    try {
      var url = new URL(String(value), window.location.origin);
      return /^https?:$/.test(url.protocol) ? url.href : '';
    } catch (_err) { return ''; }
  }
  function message(value, error) {
    var box = $('scec07-feedback');
    if (box) { box.textContent = value; box.classList.toggle('is-error', !!error); }
  }
  function modified() {
    dirty = true;
    $('scec07-revision').textContent = 'Unsaved changes · revision ' + revision;
    if (selectedId && !opening) {
      window.clearTimeout(autosaveTimer);
      autosaveTimer = window.setTimeout(function () {
        if (!inFlight && dirty) { save(true); }
      }, 12000);
    }
  }
  function template(kind) {
    var heading = kind === 'policy' ? 'Policy &amp; the long view'
      : kind === 'institutional' ? 'Institutional update'
      : 'Research, policy &amp; insight';
    var eyebrow = kind === 'policy' ? 'POLICY BRIEFING'
      : kind === 'institutional' ? 'INSTITUTIONAL NEWS'
      : 'RESEARCH BULLETIN';
    var introduction = kind === 'policy'
      ? 'A concise briefing on evidence, policy developments, and the decisions ahead.'
      : kind === 'institutional'
      ? 'A considered update on the work and priorities of Sustainable Catalyst.'
      : 'Evidence, analysis, and practical insight for sustainable systems.';
    return [
      '<mjml><mj-head>',
      '<mj-attributes><mj-all font-family="Arial, Helvetica, sans-serif" />',
      '<mj-text font-size="16px" line-height="1.6" color="#181818" />',
      '<mj-button font-size="14px" font-weight="700" background-color="#ef0000" color="#ffffff" border-radius="0px" />',
      '</mj-attributes>',
      '<mj-preview>New from Sustainable Catalyst</mj-preview>',
      '</mj-head><mj-body background-color="#f4f4f4">',
      '<mj-section background-color="#111111" padding="26px 26px 18px">',
      '<mj-column><mj-text color="#ffffff" font-size="15px" font-weight="700" letter-spacing="1px" padding="0">SUSTAINABLE CATALYST</mj-text>',
      '<mj-text color="#aaaaaa" font-size="11px" letter-spacing="1px" padding="12px 0 0">RESEARCH / PUBLICATIONS / MEDIA</mj-text></mj-column>',
      '</mj-section>',
      '<mj-section background-color="#ef0000" padding="0px"><mj-column>',
      '<mj-spacer height="5px" padding="0px" />',
      '</mj-column></mj-section>',
      '<mj-section background-color="#ffffff" padding="38px 30px 30px">',
      '<mj-column>',
      '<mj-text color="#ef0000" font-weight="700" font-size="12px" letter-spacing="1px" padding="0 0 18px">' + eyebrow + '</mj-text>',
      '<mj-text font-size="34px" font-weight="700" line-height="1.14" padding="0 0 18px" color="#111111">' + heading + '</mj-text>',
      '<mj-text font-size="17px" line-height="1.65" padding="0 0 12px" color="#555555">' + esc(introduction) + '</mj-text>',
      '</mj-column></mj-section>',
      '<mj-section background-color="#ffffff" padding="0 30px 20px">',
      '<mj-column><mj-divider border-color="#e9e9e9" border-width="1px" padding="0px" /></mj-column></mj-section>',
      '<mj-section background-color="#ffffff" padding="18px 30px 35px">',
      '<mj-column>',
      '<mj-text font-size="11px" letter-spacing="1px" color="#ef0000" font-weight="700" padding="0 0 10px">FEATURED STORY</mj-text>',
      '<mj-text font-size="23px" font-weight="700" line-height="1.25" padding="0 0 12px">A headline for your lead story</mj-text>',
      '<mj-text padding="0 0 14px">Replace this paragraph with a research finding, editorial summary, or announcement. Link to the original publication where readers can explore the evidence.</mj-text>',
      '<mj-button href="https://sustainablecatalyst.com/" align="left" padding="0">Read the full story</mj-button>',
      '</mj-column></mj-section>',
      '<mj-section background-color="#f8f8f8" padding="24px 30px">',
      '<mj-column>',
      '<mj-text color="#111111" font-size="20px" font-weight="700" padding="0 0 12px">Also in this issue</mj-text>',
      '<mj-text font-size="15px" padding="0">Add highlights, publication links, charts, or upcoming work using the drag-and-drop blocks.</mj-text>',
      '</mj-column></mj-section>',
      '<mj-section background-color="#141414" padding="26px 30px">',
      '<mj-column>',
      '<mj-text font-size="14px" color="#ffffff" padding="0 0 8px" font-weight="700">Sustainable Catalyst</mj-text>',
      '<mj-text font-size="12px" color="#aaaaaa" padding="0">',
      'Independent research, sustainable systems, and institutional knowledge.',
      '</mj-text>',
      '<mj-text font-size="12px" color="#bbbbbb" padding="8px 0 0">',
      '<a href="https://sustainablecatalyst.com/" style="color:#ffffff">sustainablecatalyst.com</a></mj-text>',
      '</mj-column></mj-section>',
      '</mj-body></mjml>'
    ].join('');
  }
  function registerBlocks(instance) {
    var b = instance.BlockManager;
    var blocks = [
      ['sc-hero', 'SC · Feature header',
       '<mj-section background-color="#111111" padding="28px"><mj-column>' +
       '<mj-text color="#ef0000" font-weight="700" font-size="11px">FEATURED</mj-text>' +
       '<mj-text color="#ffffff" font-size="30px" font-weight="700">A powerful headline</mj-text>' +
       '<mj-text color="#ffffff">A short opening that establishes the story and its importance.</mj-text>' +
       '</mj-column></mj-section>'],
      ['sc-story', 'SC · Story card',
       '<mj-section background-color="#ffffff" padding="20px 30px"><mj-column>' +
       '<mj-text font-size="11px" color="#ef0000" font-weight="700">RESEARCH</mj-text>' +
       '<mj-text font-size="23px" font-weight="700">Story title</mj-text>' +
       '<mj-text>Brief editorial summary grounded in a published source.</mj-text>' +
       '<mj-button align="left" href="https://sustainablecatalyst.com/">Read publication</mj-button>' +
       '</mj-column></mj-section>'],
      ['sc-evidence', 'SC · Evidence highlight',
       '<mj-section background-color="#f1f1f1" padding="22px 30px"><mj-column>' +
       '<mj-text font-size="11px" font-weight="700" color="#bb0000">KEY FINDING</mj-text>' +
       '<mj-text font-size="28px" font-weight="700">Evidence at a glance</mj-text>' +
       '<mj-text>State the result, source, assumptions, and uncertainty clearly.</mj-text>' +
       '</mj-column></mj-section>'],
      ['sc-note', 'SC · Editorial note',
       '<mj-section background-color="#ffffff" padding="24px 30px"><mj-column>' +
       '<mj-text font-size="19px" font-weight="700">Editorial perspective</mj-text>' +
       '<mj-text>Add a short commentary or interpretation.</mj-text>' +
       '</mj-column></mj-section>'],
      ['sc-divider', 'SC · Red divider',
       '<mj-section padding="0" background-color="#ffffff"><mj-column>' +
       '<mj-divider border-color="#ef0000" border-width="3px" padding="0 30px" />' +
       '</mj-column></mj-section>'],
      ['sc-citation', 'SC · Source reference',
       '<mj-section background-color="#f5f5f5" padding="12px 30px"><mj-column>' +
       '<mj-text font-size="12px" color="#666666">Source: Author, year. ' +
       '<a href="https://sustainablecatalyst.com/">Read the original publication</a>.</mj-text>' +
       '</mj-column></mj-section>'],
      ['sc-press-brief', 'SC · Press Room announcement',
       '<mj-section background-color="#ffffff" padding="22px 30px"><mj-column>' +
       '<mj-text color="#e00000" font-size="11px" font-weight="700">OFFICIAL ANNOUNCEMENT</mj-text>' +
       '<mj-text font-size="23px" font-weight="700">Press release headline</mj-text>' +
       '<mj-text>A brief, verified summary of an approved institutional announcement.</mj-text>' +
       '<mj-button href="https://sustainablecatalyst.com/press/" align="left" padding="0">Read the official release</mj-button>' +
       '</mj-column></mj-section>']
    ];
    blocks.forEach(function (block) {
      b.add(block[0], { label: block[1], category: 'Sustainable Catalyst',
        content: block[2] });
    });
  }

  function setNew(kind) {
    opening = true;
    window.clearTimeout(autosaveTimer);
    selectedId = 0;
    revision = 0;
    $('scec07-issues').value = '0';
    $('scec07-template').value = kind || 'research';
    $('scec07-title').value = kind === 'policy' ? 'Policy digest'
      : kind === 'institutional' ? 'Institutional update' : 'Research bulletin';
    $('scec07-subject').value = $('scec07-title').value + ' | Sustainable Catalyst';
    $('scec07-preheader').value = 'Research, evidence, and institutional insight.';
    editor.setComponents(template(kind || 'research'));
    $('scec07-revision').textContent = 'New private draft · save to persist';
    message('New draft ready. Drag blocks to the canvas, edit text, and save.');
    opening = false;
    dirty = true;
  }
  function updateSelect(items) {
    var menu = $('scec07-issues'), current = String(selectedId || 0);
    while (menu.options.length > 1) { menu.remove(1); }
    (items || []).forEach(function (entry) {
      var opt = document.createElement('option');
      opt.value = String(entry.id);
      opt.textContent = entry.title + ' · r' + entry.revision;
      menu.appendChild(opt);
    });
    menu.value = current;
  }
  function request(action, fields) {
    var params = new URLSearchParams();
    params.set('action', 'scec07_' + action);
    params.set('nonce', boot.nonce);
    Object.keys(fields || {}).forEach(function (key) { params.set(key, fields[key]); });
    return fetch(boot.ajaxUrl, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8' },
      body: params.toString()
    }).then(function (response) {
      return response.json().catch(function () { throw new Error('Invalid server response'); })
        .then(function (json) {
          if (!response.ok || !json.success) {
            throw new Error((json.data && json.data.message) || 'Request rejected');
          }
          return json.data;
        });
    });
  }
  function save(quiet) {
    if (inFlight || !editor) { return; }
    var title = $('scec07-title').value.trim();
    var subject = $('scec07-subject').value.trim();
    if (!title || !subject) {
      message('Internal title and email subject are required.', true);
      return;
    }
    var project = JSON.stringify(editor.getProjectData());
    if (new TextEncoder().encode(project).length > (boot.maxJsonBytes || 262144)) {
      message('The newsletter project is too large. Remove unused blocks or assets.', true);
      return;
    }
    inFlight = true;
    $('scec07-save').disabled = true;
    var existingId = selectedId;
    var before = JSON.stringify({
      project: project, title: title, subject: subject,
      preheader: $('scec07-preheader').value.trim()
    });
    if (!quiet) { message('Saving private newsletter revision…'); }
    request('save', {
      id: String(selectedId), title: title, subject: subject,
      preheader: $('scec07-preheader').value.trim(),
      revision: String(revision), project: project
    }).then(function (data) {
      selectedId = data.id;
      revision = data.revision;
      // If the user changed the editor during the request, preserve unsaved state.
      dirty = before !== JSON.stringify({
        project: JSON.stringify(editor.getProjectData()),
        title: $('scec07-title').value.trim(),
        subject: $('scec07-subject').value.trim(),
        preheader: $('scec07-preheader').value.trim()
      });
      $('scec07-revision').textContent = 'Saved r' + revision + ' · SHA-256 ' +
        data.sha256.slice(0, 12) + (dirty ? ' · unsaved changes' : '');
      updateSelect(data.issues);
      message((quiet ? 'Autosaved' : 'Saved') + ' private revision ' + revision +
        '. No email or subscriber operation occurred.');
      if (dirty && selectedId) { modified(); }
    }).catch(function (error) {
      dirty = true;
      message('Save failed: ' + error.message, true);
      // Avoid accidental new draft duplicate when interrupted.
      if (!existingId) { message('Save failed; retry manually before creating another draft. ' + error.message, true); }
    }).finally(function () {
      inFlight = false;
      $('scec07-save').disabled = false;
    });
  }
  function load(id) {
    if (!id) { setNew($('scec07-template').value); return; }
    opening = true;
    window.clearTimeout(autosaveTimer);
    message('Loading private newsletter…');
    request('load', { id: String(id) }).then(function (data) {
      editor.loadProjectData(data.project);
      selectedId = data.id;
      revision = data.revision;
      $('scec07-issues').value = String(id);
      $('scec07-title').value = data.title;
      $('scec07-subject').value = data.subject;
      $('scec07-preheader').value = data.preheader;
      $('scec07-revision').textContent = 'Saved r' + revision + ' · SHA-256 ' +
        data.sha256.slice(0, 12);
      dirty = false;
      message('Loaded private revision ' + revision + '. Sending is disabled.');
    }).catch(function (error) {
      message('Could not load draft: ' + error.message, true);
      $('scec07-issues').value = String(selectedId);
    }).finally(function () { opening = false; });
  }
  function compiled() {
    if (!editor || !editor.Commands.has('mjml-code-to-html')) {
      throw new Error('MJML compiler unavailable. Verify editor dependencies.');
    }
    var result = editor.runCommand('mjml-code-to-html');
    if (!result || typeof result.html !== 'string') {
      throw new Error('The MJML compiler did not return email HTML.');
    }
    var errors = Array.isArray(result.errors) ? result.errors : [];
    if (errors.length) {
      throw new Error('MJML validation failed: ' +
        errors.slice(0, 2).map(function (e) {
          return e.formattedMessage || e.message || String(e);
        }).join('; '));
    }
    return result.html;
  }
  function download(name, type, data) {
    var blob = new Blob([data], {type: type});
    var url = URL.createObjectURL(blob);
    var link = document.createElement('a');
    link.href = url;
    link.download = name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }
  function filename(extension) {
    var title = $('scec07-title').value.trim().toLowerCase()
      .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 55);
    return (title || 'newsletter') + '-draft-r' + revision + '.' + extension;
  }
  function runExport(kind) {
    try {
      if (kind === 'html') {
        download(filename('html'), 'text/html;charset=utf-8', compiled());
        message('Downloaded compiled HTML. This is not Substack-compatible custom code.');
      } else if (kind === 'mjml') {
        download(filename('mjml'), 'application/xml;charset=utf-8', editor.getHtml());
        message('Downloaded editable MJML source.');
      } else if (kind === 'json') {
        download(filename('json'), 'application/json;charset=utf-8',
          JSON.stringify(editor.getProjectData(), null, 2));
        message('Downloaded editable GrapesJS project JSON.');
      }
    } catch (error) { message(error.message, true); }
  }
  function inlineMarkup(node) {
    if (node.nodeType === Node.TEXT_NODE) { return esc(node.nodeValue); }
    if (node.nodeType !== Node.ELEMENT_NODE) { return ''; }
    var tag = node.tagName.toLowerCase();
    var children = Array.prototype.map.call(node.childNodes, inlineMarkup).join('');
    var allowed = ['strong','b','em','i','u','code','h1','h2','h3','ul','ol','li','blockquote','p','br'];
    if (tag === 'a') {
      var href = safeURL(node.getAttribute('href') || '');
      return href ? '<a href="' + esc(href) + '">' + children + '</a>' : children;
    }
    if (tag === 'img') {
      var src = safeURL(node.getAttribute('src') || '');
      return src ? '<img src="' + esc(src) + '" alt="' +
        esc(node.getAttribute('alt') || '') + '">' : '';
    }
    return allowed.indexOf(tag) !== -1
      ? '<' + tag + '>' + children + '</' + tag + '>' : children;
  }
  function substackEdition() {
    // Flatten email-only MJML tables/styles into conventional Substack-friendly
    // paragraphs, headings, links and images; fidelity is intentionally limited.
    var doc = new DOMParser().parseFromString(editor.getHtml(), 'text/html');
    var result = [];
    var items = doc.querySelectorAll('mj-text, mj-image, mj-button, mj-divider');
    Array.prototype.forEach.call(items, function (el) {
      var tag = el.tagName.toLowerCase();
      if (tag === 'mj-text') {
        var text = Array.prototype.map.call(el.childNodes, inlineMarkup).join('').trim();
        if (text) {
          var fontsize = parseFloat(el.getAttribute('font-size') || '16');
          result.push(fontsize >= 27 ? '<h1>' + text + '</h1>'
            : fontsize >= 20 ? '<h2>' + text + '</h2>'
            : '<p>' + text + '</p>');
        }
      }
      if (tag === 'mj-image') {
        var src = safeURL(el.getAttribute('src') || '');
        if (src) { result.push('<p><img src="' + esc(src) +
          '" alt="' + esc(el.getAttribute('alt') || '') + '"></p>'); }
      }
      if (tag === 'mj-button') {
        var url = safeURL(el.getAttribute('href') || '');
        var label = esc(el.textContent.trim() || 'Read more');
        result.push(url ? '<p><a href="' + esc(url) + '">' + label + '</a></p>' :
          '<p>' + label + '</p>');
      }
      if (tag === 'mj-divider') { result.push('<hr>'); }
    });
    return '<h1>' + esc($('scec07-subject').value || $('scec07-title').value) + '</h1>' +
      result.join('\n');
  }
  function copySubstack() {
    try {
      var html = substackEdition();
      if (!html || html.length < 30) { throw new Error('Newsletter has no content.'); }
      var plain = new DOMParser().parseFromString(html, 'text/html').body.textContent || '';
      if (navigator.clipboard && window.ClipboardItem && window.isSecureContext) {
        var item = new ClipboardItem({
          'text/html': new Blob([html], {type:'text/html'}),
          'text/plain': new Blob([plain], {type:'text/plain'})
        });
        navigator.clipboard.write([item]).then(function () {
          message('Copied Substack-compatible content. Paste, review formatting/images, then send in Substack.');
        }).catch(function () {
          message('Clipboard permission blocked. Download the HTML/MJML or use browser copy.', true);
        });
      } else if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(plain).then(function () {
          message('Copied text-only edition. Add images and formatting in Substack.');
        });
      } else {
        download(filename('substack.html'), 'text/html;charset=utf-8', html);
        message('Clipboard unavailable: downloaded a simple HTML edition for manual transfer.');
      }
    } catch (error) { message('Substack export failed: ' + error.message, true); }
  }
  function showPreview() {
    try {
      var shade = document.createElement('div');
      shade.className = 'scec07-modal';
      var panel = document.createElement('div');
      panel.className = 'scec07-modal-panel';
      var header = document.createElement('div');
      header.className = 'scec07-modal-header';
      var label = document.createElement('strong');
      label.textContent = 'Full email preview · draft only';
      var close = document.createElement('button');
      close.type = 'button';
      close.className = 'button';
      close.textContent = 'Close';
      close.addEventListener('click', function () { shade.remove(); });
      var frame = document.createElement('iframe');
      frame.title = 'Compiled email preview';
      frame.setAttribute('sandbox', '');
      frame.setAttribute('referrerpolicy', 'no-referrer');
      frame.srcdoc = compiled();
      header.appendChild(label); header.appendChild(close);
      panel.appendChild(header); panel.appendChild(frame); shade.appendChild(panel);
      document.body.appendChild(shade);
    } catch (error) { message(error.message, true); }
  }
  function setDevice(mobile) {
    var list = editor.Devices.getAll();
    var best = list.find(function (device) {
      var name = String(device.get('name') || '').toLowerCase();
      return mobile ? name.indexOf('mobile') !== -1 : name.indexOf('desktop') !== -1;
    });
    if (best) { editor.setDevice(best.get('name')); }
    else if (mobile) {
      editor.Devices.add({name:'SC mobile', width:'375px', widthMedia:'480px'});
      editor.setDevice('SC mobile');
    } else { editor.setDevice(''); }
  }
  function insertImage() {
    if (!window.wp || !wp.media) {
      message('WordPress media library unavailable.', true);
      return;
    }
    var frame = wp.media({title:'Insert newsletter image',
      button:{text:'Use image'}, library:{type:'image'}, multiple:false});
    frame.on('select', function () {
      var item = frame.state().get('selection').first().toJSON();
      var url = safeURL(item.url);
      if (!url || !/^https:/.test(url)) {
        message('Only HTTPS image URLs may be inserted.', true);
        return;
      }
      editor.addComponents('<mj-section background-color="#ffffff" padding="14px 30px"><mj-column>' +
        '<mj-image src="' + esc(url) + '" alt="' +
        esc(item.alt || item.title || 'Newsletter illustration') + '" padding="0" />' +
        '</mj-column></mj-section>');
      message('WordPress image inserted. Add alt text and verify rights before publishing.');
      modified();
    });
    frame.open();
  }
  function confirmDiscard() {
    return !dirty || window.confirm('This newsletter has unsaved edits. Discard changes?');
  }
  function initialize() {
    if (!boot.ajaxUrl || !boot.nonce || !window.grapesjs) {
      message('Editor dependencies unavailable. Verify the approved admin scripts and reload.', true);
      return;
    }
    try {
      editor = window.grapesjs.init({
        container:'#scec07-editor', height:'760px', width:'auto',
        fromElement:false, storageManager:false, noticeOnUnload:false,
        plugins:['grapesjs-mjml'],
        pluginsOpts:{'grapesjs-mjml':{resetDevices:true, useCustomTheme:true}},
        assetManager:{upload:false},
        canvas:{scripts:[]},
      });
    } catch (error) {
      message('Unable to initialize GrapesJS/MJML: ' + error.message, true);
      return;
    }
    editor.on('load', function () {
      registerBlocks(editor);
      updateSelect(boot.issues || []);
      setNew('research');
      editor.on('update', function () { if (!opening) { modified(); } });
      message('Visual editor ready. Use blocks on the left and style controls on the right.');
    });
    $('scec07-new').addEventListener('click', function () {
      if (confirmDiscard()) { setNew($('scec07-template').value); }
    });
    $('scec07-issues').addEventListener('change', function () {
      var id = Number(this.value);
      if (!confirmDiscard()) { this.value = String(selectedId); return; }
      load(id);
    });
    ['title','subject','preheader'].forEach(function (field) {
      $('scec07-' + field).addEventListener('input', modified);
    });
    $('scec07-save').addEventListener('click', function () { save(false); });
    $('scec07-media').addEventListener('click', insertImage);
    $('scec07-desktop').addEventListener('click', function () { setDevice(false); });
    $('scec07-mobile').addEventListener('click', function () { setDevice(true); });
    $('scec07-preview').addEventListener('click', showPreview);
    ['html','mjml','json'].forEach(function (kind) {
      $('scec07-' + kind).addEventListener('click', function () { runExport(kind); });
    });
    $('scec07-substack').addEventListener('click', copySubstack);
    window.addEventListener('beforeunload', function (event) {
      if (dirty) { event.preventDefault(); event.returnValue = ''; }
    });
  }

  document.addEventListener('DOMContentLoaded', initialize);
})();
