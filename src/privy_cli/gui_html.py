"""Embedded HTML/CSS/JS for the privy GUI."""
from __future__ import annotations

HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>privy</title>
<style>
  :root {
    --bg: #ffffff;
    --fg: #1a1a1a;
    --muted: #6b7280;
    --border: #e5e7eb;
    --drop-bg: #f9fafb;
    --drop-border: #d1d5db;
    --drop-active: #3b82f6;
    --btn-bg: #111827;
    --btn-fg: #ffffff;
    --btn-hover: #374151;
    --btn-disabled: #9ca3af;
    --status-bg: #f3f4f6;
    --success: #059669;
    --error: #dc2626;
    --link: #2563eb;
    --radius: 12px;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #111827;
      --fg: #f9fafb;
      --muted: #9ca3af;
      --border: #374151;
      --drop-bg: #1f2937;
      --drop-border: #4b5563;
      --drop-active: #60a5fa;
      --btn-bg: #f9fafb;
      --btn-fg: #111827;
      --btn-hover: #e5e7eb;
      --btn-disabled: #6b7280;
      --status-bg: #1f2937;
      --success: #34d399;
      --error: #f87171;
      --link: #60a5fa;
    }
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--fg);
    padding: 32px 28px;
    user-select: none;
    -webkit-user-select: none;
  }
  h1 {
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 24px;
    letter-spacing: -0.3px;
  }
  h1 span { color: var(--muted); font-weight: 400; font-size: 13px; margin-left: 8px; }

  /* Drop zone */
  .drop-zone {
    border: 2px dashed var(--drop-border);
    border-radius: var(--radius);
    background: var(--drop-bg);
    padding: 40px 20px;
    text-align: center;
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
    margin-bottom: 20px;
  }
  .drop-zone:hover, .drop-zone.active {
    border-color: var(--drop-active);
    background: color-mix(in srgb, var(--drop-active) 5%, var(--drop-bg));
  }
  .drop-zone p { color: var(--muted); font-size: 14px; line-height: 1.5; }
  .drop-zone .icon { font-size: 32px; margin-bottom: 8px; display: block; }

  /* Selected file */
  .selected {
    font-size: 14px;
    color: var(--fg);
    margin-bottom: 24px;
    padding: 10px 14px;
    background: var(--status-bg);
    border-radius: 8px;
    display: none;
    word-break: break-all;
  }
  .selected.visible { display: block; }
  .selected strong { font-weight: 600; }

  /* Buttons */
  .actions {
    display: flex;
    gap: 12px;
    margin-bottom: 24px;
  }
  .btn {
    flex: 1;
    padding: 12px 20px;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    background: var(--btn-bg);
    color: var(--btn-fg);
    transition: background 0.15s, opacity 0.15s;
  }
  .btn:hover:not(:disabled) { background: var(--btn-hover); }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn.secondary {
    background: transparent;
    color: var(--fg);
    border: 1.5px solid var(--border);
  }
  .btn.secondary:hover:not(:disabled) {
    background: var(--status-bg);
  }

  /* Status area */
  .status {
    border-radius: var(--radius);
    background: var(--status-bg);
    padding: 16px 18px;
    font-size: 13px;
    line-height: 1.6;
    min-height: 60px;
    display: none;
  }
  .status.visible { display: block; }
  .status .message { color: var(--muted); }
  .status .success { color: var(--success); font-weight: 600; }
  .status .error { color: var(--error); }
  .status .path {
    color: var(--link);
    cursor: pointer;
    text-decoration: underline;
    text-decoration-color: color-mix(in srgb, var(--link) 40%, transparent);
    word-break: break-all;
  }
  .status .path:hover { text-decoration-color: var(--link); }
  .status .detail { color: var(--muted); margin-top: 4px; }

  /* Spinner */
  .spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid var(--muted);
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
    vertical-align: middle;
    margin-right: 6px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>

<h1>privy <span>docx anonymizer</span></h1>

<div class="drop-zone" id="dropZone">
  <span class="icon">&#128196;</span>
  <p>Drag &amp; drop a .docx file here<br>or click to browse</p>
</div>

<div class="selected" id="selectedFile">
  <strong>File:</strong> <span id="fileName"></span>
</div>

<div class="actions">
  <button class="btn" id="btnAnonymize" disabled>Anonymize</button>
  <button class="btn secondary" id="btnDeanonymize" disabled>Deanonymize</button>
</div>

<div class="status" id="status"></div>

<script>
(function() {
  const dropZone = document.getElementById('dropZone');
  const selectedFile = document.getElementById('selectedFile');
  const fileName = document.getElementById('fileName');
  const btnAnonymize = document.getElementById('btnAnonymize');
  const btnDeanonymize = document.getElementById('btnDeanonymize');
  const status = document.getElementById('status');

  let busy = false;

  // --- Global status updater (called from Python via evaluate_js) ---
  window.__privyUpdateStatus = function(msg) {
    status.className = 'status visible';
    status.innerHTML = '<span class="spinner"></span><span class="message">' + escapeHtml(msg) + '</span>';
  };

  // --- File selection ---
  function fileSelected(name) {
    fileName.textContent = name;
    selectedFile.className = 'selected visible';
    btnAnonymize.disabled = false;
    btnDeanonymize.disabled = false;
  }

  // Drop zone click → open native file dialog
  dropZone.addEventListener('click', async function() {
    if (busy) return;
    const result = await window.pywebview.api.open_file_dialog();
    if (result && result.name) fileSelected(result.name);
    if (result && result.error) showError(result.error);
  });

  // Drag and drop visual feedback
  dropZone.addEventListener('dragover', function(e) {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.add('active');
  });
  dropZone.addEventListener('dragleave', function(e) {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.remove('active');
  });
  dropZone.addEventListener('drop', function(e) {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.remove('active');
  });

  // pywebview drag-and-drop event (provides real file path)
  window.addEventListener('pywebviewready', function() {
    if (window.pywebview && window.pywebview.dom) {
      window.pywebview.dom.document.events.drop += function(e) {
        var files = e.dataTransfer && e.dataTransfer.files;
        if (files && files.length > 0) {
          var path = files[0].pywebviewFullPath || files[0].name;
          window.pywebview.api.select_file_via_drop(path).then(function(result) {
            if (result && result.name) fileSelected(result.name);
            if (result && result.error) showError(result.error);
          });
        }
      };
    }
  });

  // --- Actions ---
  btnAnonymize.addEventListener('click', async function() {
    if (busy) return;
    setBusy(true);
    showProgress('Preparing...');
    try {
      const result = await window.pywebview.api.anonymize();
      if (result.error) {
        showError(result.error);
      } else {
        showSuccess(
          'Anonymized successfully',
          result.output_path,
          result.report.paragraphs_scanned + ' paragraphs, ' +
          result.report.entities_detected + ' entities found, ' +
          result.report.replacements_applied + ' replacements'
        );
      }
    } catch (err) {
      showError(String(err));
    }
    setBusy(false);
  });

  btnDeanonymize.addEventListener('click', async function() {
    if (busy) return;
    setBusy(true);
    showProgress('Preparing...');
    try {
      const result = await window.pywebview.api.deanonymize();
      if (result.error) {
        showError(result.error);
      } else {
        showSuccess(
          'Restored successfully',
          result.output_path,
          result.report.paragraphs_scanned + ' paragraphs, ' +
          result.report.replacements_applied + ' replacements'
        );
      }
    } catch (err) {
      showError(String(err));
    }
    setBusy(false);
  });

  // --- UI helpers ---
  function setBusy(b) {
    busy = b;
    btnAnonymize.disabled = b;
    btnDeanonymize.disabled = b;
  }

  function showProgress(msg) {
    status.className = 'status visible';
    status.innerHTML = '<span class="spinner"></span><span class="message">' + escapeHtml(msg) + '</span>';
  }

  function showSuccess(msg, outputPath, detail) {
    status.className = 'status visible';
    status.innerHTML =
      '<div class="success">' + escapeHtml(msg) + '</div>' +
      '<div class="path" onclick="window.__privyReveal(this.dataset.path)" data-path="' + escapeAttr(outputPath) + '">' + escapeHtml(outputPath) + '</div>' +
      '<div class="detail">' + escapeHtml(detail) + '</div>';
  }

  function showError(msg) {
    status.className = 'status visible';
    status.innerHTML = '<div class="error">' + escapeHtml(msg) + '</div>';
  }

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function escapeAttr(s) {
    return s.replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  window.__privyReveal = function(path) {
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.reveal_in_finder(path);
    }
  };
})();
</script>
</body>
</html>
"""
