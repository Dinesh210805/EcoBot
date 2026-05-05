'use strict';

/* ── State ──────────────────────────────────────────────── */
const state = {
  sessionId: null,
  pendingId: null,
  pendingLocation: '',
  currentTab: 'text',
  imageFile: null,
  voiceFile: null,
};

/* ── Constants ──────────────────────────────────────────── */
const BASE = '/api/v1';

const BIN_EMOJI = { green: '🟢', blue: '🔵', red: '🔴', black: '⚫', grey: '⬜' };
const BIN_NAMES = { green: 'Green Bin', blue: 'Blue Bin', red: 'Red Bin', black: 'Black Bin', grey: 'Grey Bin' };

const CAT_ICONS = {
  wet_waste: '🥦', dry_waste: '♻️', hazardous: '☢️',
  e_waste: '📱', sanitary: '🩺', construction: '🏗️', non_recyclable: '🗑️',
};

/* ── API Layer ──────────────────────────────────────────── */
async function apiFetch(path, options = {}) {
  const isFormData = options.body instanceof FormData;
  const headers = isFormData ? {} : { 'Content-Type': 'application/json' };
  const res = await fetch(BASE + path, { ...options, headers: { ...headers, ...options.headers } });
  const data = await res.json().catch(() => ({ detail: 'Invalid JSON response' }));
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data;
}

const api = {
  health: () => apiFetch('/health'),
  getCategories: () => apiFetch('/categories'),
  classifyText: (text, sessionId, location) =>
    apiFetch('/classify/text', {
      method: 'POST',
      body: JSON.stringify({ text, session_id: sessionId, location: location || null, include_facilities: true }),
    }),
  uploadImage: (file, sessionId, location) => {
    const fd = new FormData();
    fd.append('file', file);
    if (sessionId) fd.append('session_id', sessionId);
    if (location)  fd.append('location', location);
    return apiFetch('/classify/image', { method: 'POST', body: fd });
  },
  confirmImage: (pendingId, confirmed, correctedItem, sessionId, location) =>
    apiFetch('/classify/image/confirm', {
      method: 'POST',
      body: JSON.stringify({ pending_id: pendingId, confirmed, corrected_item: correctedItem || null, session_id: sessionId, location: location || null }),
    }),
  uploadVoice: (file, sessionId, location) => {
    const fd = new FormData();
    fd.append('file', file);
    if (sessionId) fd.append('session_id', sessionId);
    if (location)  fd.append('location', location);
    return apiFetch('/classify/voice', { method: 'POST', body: fd });
  },
  confirmVoice: (pendingId, confirmed, sessionId, location) =>
    apiFetch('/classify/voice/confirm', {
      method: 'POST',
      body: JSON.stringify({ pending_id: pendingId, confirmed, session_id: sessionId, location: location || null }),
    }),
  classifyBatch: (items) =>
    apiFetch('/classify/batch', { method: 'POST', body: JSON.stringify({ items }) }),
  chat: (message, sessionId, location) =>
    apiFetch('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, session_id: sessionId, location: location || null }),
    }),
  searchFacilities: (city, pincode, category, limit) =>
    apiFetch('/facilities', {
      method: 'POST',
      body: JSON.stringify({ city: city || null, pincode: pincode || null, category: category || null, limit: limit || 10 }),
    }),
};

/* ── Utilities ──────────────────────────────────────────── */
function showToast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${icons[type] || 'ℹ'}</span><span>${msg}</span>`;
  container.appendChild(toast);
  requestAnimationFrame(() => { requestAnimationFrame(() => toast.classList.add('show')); });
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 350);
  }, 4000);
}

function setButtonLoading(btn, loading, originalHTML) {
  if (loading) {
    btn._original = btn.innerHTML;
    btn.innerHTML = `<span class="spinner spinner-sm"></span>`;
    btn.disabled = true;
  } else {
    btn.innerHTML = originalHTML || btn._original || btn.innerHTML;
    btn.disabled = false;
  }
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function updateChatSession() {
  const input = document.getElementById('chat-message-input');
  const btn = document.getElementById('chat-send-btn');
  const notice = document.getElementById('chat-session-notice');
  const hasSession = !!state.sessionId;
  input.disabled = !hasSession;
  btn.disabled = !hasSession;
  if (notice) notice.classList.toggle('hidden', hasSession);
  if (hasSession) input.placeholder = 'Ask about disposal, recycling…';
}

/* ── Render Result ──────────────────────────────────────── */
function renderResult(result) {
  const empty = document.getElementById('result-empty-state');
  const content = document.getElementById('result-content');
  empty.hidden = true;
  content.hidden = false;
  content.innerHTML = buildResultHTML(result);
  if (result.session_id) {
    state.sessionId = result.session_id;
    updateChatSession();
  }
}

function buildResultHTML(r) {
  const bin = (r.bin_color || 'grey').toLowerCase();
  const confClass = `badge-confidence-${r.confidence || 'low'}`;

  let html = `
    <div class="bin-badge bin-${escHtml(bin)}">
      <div class="bin-swatch"></div>
      <div class="bin-info">
        <span class="bin-item">${escHtml(r.item || 'Unknown Item')}</span>
        <span class="bin-label">${escHtml(BIN_NAMES[bin] || bin)} · ${escHtml(r.bin_label || r.category || '')}</span>
      </div>
    </div>
    <div class="badges-row">
      ${r.recyclable
        ? `<span class="badge badge-recyclable">♻ Recyclable</span>`
        : `<span class="badge badge-not-recyclable">✕ Not Recyclable</span>`}
      <span class="badge ${confClass}">${escHtml(r.confidence || 'unknown')} confidence</span>
      ${r.category === 'hazardous' || r.category === 'e_waste'
        ? `<span class="badge badge-hazardous">⚠ Hazardous</span>`
        : ''}
      ${r.special_facility_required
        ? `<span class="badge badge-special">★ Special Facility</span>`
        : ''}
    </div>`;

  if (r.reason) {
    html += `
      <div class="result-section">
        <p class="result-section-title">Why this bin?</p>
        <p class="result-text">${escHtml(r.reason)}</p>
      </div>`;
  }

  if (r.preparation_steps && r.preparation_steps.length) {
    html += `
      <div class="result-section">
        <p class="result-section-title">Preparation Steps</p>
        <div class="prep-steps">
          ${r.preparation_steps.map((s, i) => `
            <div class="prep-step">
              <span class="step-num">${i + 1}</span>
              <span>${escHtml(s)}</span>
            </div>`).join('')}
        </div>
      </div>`;
  }

  if (r.safety_notes) {
    html += `
      <div class="result-section">
        <p class="result-section-title">Safety Notes</p>
        <div class="info-card safety">${escHtml(r.safety_notes)}</div>
      </div>`;
  }

  if (r.environmental_fact) {
    html += `
      <div class="result-section">
        <p class="result-section-title">🌱 Did you know?</p>
        <div class="info-card env">${escHtml(r.environmental_fact)}</div>
      </div>`;
  }

  if (r.clarification_question) {
    html += `
      <div class="result-section">
        <div class="clarification-card">
          <strong>Clarification needed:</strong> ${escHtml(r.clarification_question)}
        </div>
      </div>`;
  }

  if (r.voice_transcription) {
    html += `
      <div class="result-section">
        <p class="result-section-title">Transcription</p>
        <p class="result-text" style="font-family:var(--font-mono);font-size:13px">"${escHtml(r.voice_transcription)}"</p>
      </div>`;
  }

  if (r.nearby_facilities && r.nearby_facilities.length) {
    html += `
      <div class="result-section">
        <p class="result-section-title">Nearby Facilities</p>
        <div class="nearby-list">
          ${r.nearby_facilities.slice(0, 3).map(f => `
            <div class="nearby-item">
              <div class="nearby-name">${escHtml(f.name)}</div>
              <div class="nearby-addr">${escHtml(f.address || '')}${f.city ? ', ' + escHtml(f.city) : ''}</div>
            </div>`).join('')}
        </div>
      </div>`;
  }

  return html;
}

/* ── Render Batch Results ───────────────────────────────── */
function renderBatchResults(result) {
  const section = document.getElementById('batch-results-section');
  const tbody   = document.getElementById('batch-table-body');
  const summary = document.getElementById('batch-summary');
  section.hidden = false;
  summary.innerHTML = `
    <span class="batch-stat">Total: <strong>${result.total}</strong></span>
    <span class="batch-stat">Hazardous: <strong style="color:var(--danger)">${result.hazardous_count}</strong></span>`;

  tbody.innerHTML = result.items.map((item, i) => {
    const bin = (item.bin_color || 'grey').toLowerCase();
    return `<tr>
      <td style="color:var(--text-muted)">${i + 1}</td>
      <td>${escHtml(item.item || '')}</td>
      <td>${escHtml(item.category || '')}</td>
      <td><span class="bin-dot bin-${bin}"></span>${escHtml(BIN_NAMES[bin] || bin)}</td>
      <td>${item.recyclable ? '<span style="color:var(--green-400)">Yes</span>' : '<span style="color:var(--text-muted)">No</span>'}</td>
      <td><span class="badge badge-confidence-${item.confidence}">${escHtml(item.confidence || '')}</span></td>
    </tr>`;
  }).join('');

  section.scrollIntoView({ behavior: 'smooth', block: 'start' });
  if (result.session_id) { state.sessionId = result.session_id; updateChatSession(); }
}

/* ── Render Facilities ──────────────────────────────────── */
function renderFacilities(result, container) {
  if (!result.facilities || !result.facilities.length) {
    container.innerHTML = `<p class="empty-results">No facilities found. Try a different city or category.</p>`;
    return;
  }
  container.innerHTML = `<div class="facilities-grid">
    ${result.facilities.map(f => `
      <div class="facility-card">
        <div class="facility-header">
          <span class="facility-name">${escHtml(f.name)}</span>
          ${f.verified ? `<span class="facility-verified">✓ Verified</span>` : ''}
        </div>
        <div class="facility-addr">${escHtml(f.address || '')}${f.city ? ', ' + escHtml(f.city) : ''}${f.pincode ? ' - ' + escHtml(f.pincode) : ''}</div>
        <div class="facility-meta">
          ${f.operating_hours ? `<div class="facility-row">🕐 ${escHtml(f.operating_hours)}</div>` : ''}
          ${f.contact        ? `<div class="facility-row">📞 ${escHtml(f.contact)}</div>` : ''}
        </div>
        ${f.accepted_categories && f.accepted_categories.length
          ? `<div class="facility-cats">${f.accepted_categories.map(c => `<span class="facility-cat">${escHtml(c.replace(/_/g, ' '))}</span>`).join('')}</div>`
          : ''}
      </div>`).join('')}
  </div>`;
}

/* ── Tab Initialization ─────────────────────────────────── */
function initTabs() {
  const tabs = document.querySelectorAll('.tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => { t.classList.remove('active'); t.setAttribute('aria-selected', 'false'); });
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');
      const panelId = `panel-${tab.dataset.tab}`;
      document.getElementById(panelId)?.classList.add('active');
      state.currentTab = tab.dataset.tab;
    });
  });
}

/* ── Health Check ───────────────────────────────────────── */
function initHealth() {
  const dot  = document.getElementById('health-dot');
  const text = document.getElementById('health-text');
  api.health()
    .then(data => {
      const up = data.status === 'ok' || data.status === 'healthy';
      dot.className = `health-dot ${up ? 'up' : 'down'}`;
      text.textContent = up ? 'All systems up' : 'Degraded';
    })
    .catch(() => {
      dot.className = 'health-dot down';
      text.textContent = 'Offline';
    });
}

/* ── Text Tab ───────────────────────────────────────────── */
function initTextTab() {
  const btn      = document.getElementById('text-submit');
  const input    = document.getElementById('text-input');
  const location = document.getElementById('text-location');

  async function classify() {
    const text = input.value.trim();
    if (!text) { showToast('Please enter an item to classify', 'warning'); return; }
    setButtonLoading(btn, true);
    try {
      const result = await api.classifyText(text, state.sessionId, location.value.trim());
      renderResult(result);
      showToast(`Classified: ${result.item}`, 'success');
    } catch (err) {
      showToast(err.message || 'Classification failed', 'error');
    } finally {
      setButtonLoading(btn, false);
    }
  }

  btn.addEventListener('click', classify);
  input.addEventListener('keydown', e => { if (e.key === 'Enter' && e.ctrlKey) classify(); });
}

/* ── Dropzone Helper ────────────────────────────────────── */
function makeDropzone(zoneEl, fileInput, onFile) {
  zoneEl.addEventListener('click', e => { if (e.target.closest('.preview-clear')) return; fileInput.click(); });
  zoneEl.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') fileInput.click(); });
  zoneEl.addEventListener('dragover', e => { e.preventDefault(); zoneEl.classList.add('drag-over'); });
  zoneEl.addEventListener('dragleave', () => zoneEl.classList.remove('drag-over'));
  zoneEl.addEventListener('drop', e => {
    e.preventDefault();
    zoneEl.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) onFile(file);
  });
  fileInput.addEventListener('change', () => { if (fileInput.files[0]) onFile(fileInput.files[0]); });
}

/* ── Image Tab ──────────────────────────────────────────── */
function initImageTab() {
  const zone      = document.getElementById('image-dropzone');
  const fileInput = document.getElementById('image-file-input');
  const idle      = document.getElementById('image-dropzone-idle');
  const preview   = document.getElementById('image-dropzone-preview');
  const thumb     = document.getElementById('image-preview-thumb');
  const fname     = document.getElementById('image-filename');
  const clearBtn  = document.getElementById('image-clear');
  const location  = document.getElementById('image-location');
  const uploadBtn = document.getElementById('image-upload-btn');
  const confirmBox    = document.getElementById('image-confirm-box');
  const confirmQ      = document.getElementById('image-confirm-question');
  const confirmYes    = document.getElementById('image-confirm-yes');
  const confirmNo     = document.getElementById('image-confirm-no');

  function setFile(file) {
    state.imageFile = file;
    thumb.src = URL.createObjectURL(file);
    fname.textContent = file.name;
    idle.hidden = true;
    preview.hidden = false;
    confirmBox.hidden = true;
  }

  function clearFile() {
    state.imageFile = null;
    thumb.src = '';
    idle.hidden = false;
    preview.hidden = true;
    confirmBox.hidden = true;
    fileInput.value = '';
    state.pendingId = null;
  }

  makeDropzone(zone, fileInput, setFile);
  clearBtn.addEventListener('click', clearFile);

  uploadBtn.addEventListener('click', async () => {
    if (!state.imageFile) { showToast('Please select an image first', 'warning'); return; }
    setButtonLoading(uploadBtn, true);
    try {
      const pending = await api.uploadImage(state.imageFile, state.sessionId, location.value.trim());
      state.pendingId = pending.pending_id;
      state.pendingLocation = location.value.trim();
      confirmQ.textContent = pending.confirmation_question || `Identified: "${pending.identified_item}". Classify this?`;
      confirmBox.hidden = false;
      showToast('Image identified — please confirm', 'info');
    } catch (err) {
      showToast(err.message || 'Image upload failed', 'error');
    } finally {
      setButtonLoading(uploadBtn, false);
    }
  });

  confirmYes.addEventListener('click', async () => {
    setButtonLoading(confirmYes, true);
    try {
      const result = await api.confirmImage(state.pendingId, true, null, state.sessionId, state.pendingLocation);
      confirmBox.hidden = true;
      renderResult(result);
      showToast(`Classified: ${result.item}`, 'success');
    } catch (err) {
      showToast(err.message || 'Confirmation failed', 'error');
    } finally {
      setButtonLoading(confirmYes, false);
    }
  });

  confirmNo.addEventListener('click', () => {
    confirmBox.hidden = true;
    state.pendingId = null;
    showToast('Classification cancelled', 'info');
  });
}

/* ── Voice Tab ──────────────────────────────────────────── */
function initVoiceTab() {
  const zone      = document.getElementById('voice-dropzone');
  const fileInput = document.getElementById('voice-file-input');
  const idle      = document.getElementById('voice-dropzone-idle');
  const selected  = document.getElementById('voice-dropzone-selected');
  const fname     = document.getElementById('voice-file-name');
  const clearBtn  = document.getElementById('voice-clear');
  const location  = document.getElementById('voice-location');
  const uploadBtn = document.getElementById('voice-upload-btn');
  const confirmBox = document.getElementById('voice-confirm-box');
  const confirmQ   = document.getElementById('voice-confirm-question');
  const confirmYes = document.getElementById('voice-confirm-yes');
  const confirmNo  = document.getElementById('voice-confirm-no');

  function setFile(file) {
    state.voiceFile = file;
    fname.textContent = file.name;
    idle.hidden = true;
    selected.hidden = false;
    confirmBox.hidden = true;
  }

  function clearFile() {
    state.voiceFile = null;
    idle.hidden = false;
    selected.hidden = true;
    confirmBox.hidden = true;
    fileInput.value = '';
    state.pendingId = null;
  }

  makeDropzone(zone, fileInput, setFile);
  clearBtn.addEventListener('click', clearFile);

  uploadBtn.addEventListener('click', async () => {
    if (!state.voiceFile) { showToast('Please select an audio file first', 'warning'); return; }
    setButtonLoading(uploadBtn, true);
    try {
      const pending = await api.uploadVoice(state.voiceFile, state.sessionId, location.value.trim());
      state.pendingId = pending.pending_id;
      state.pendingLocation = location.value.trim();
      const q = pending.confirmation_question || (pending.transcription
        ? `Heard: "${pending.transcription}". Classify this?`
        : `Identified: "${pending.identified_item}". Classify this?`);
      confirmQ.textContent = q;
      confirmBox.hidden = false;
      showToast('Audio transcribed — please confirm', 'info');
    } catch (err) {
      showToast(err.message || 'Voice upload failed', 'error');
    } finally {
      setButtonLoading(uploadBtn, false);
    }
  });

  confirmYes.addEventListener('click', async () => {
    setButtonLoading(confirmYes, true);
    try {
      const result = await api.confirmVoice(state.pendingId, true, state.sessionId, state.pendingLocation);
      confirmBox.hidden = true;
      renderResult(result);
      showToast(`Classified: ${result.item}`, 'success');
    } catch (err) {
      showToast(err.message || 'Confirmation failed', 'error');
    } finally {
      setButtonLoading(confirmYes, false);
    }
  });

  confirmNo.addEventListener('click', () => {
    confirmBox.hidden = true;
    state.pendingId = null;
    showToast('Classification cancelled', 'info');
  });
}

/* ── Batch Tab ──────────────────────────────────────────── */
function initBatchTab() {
  const textarea = document.getElementById('batch-input');
  const counter  = document.getElementById('batch-counter');
  const btn      = document.getElementById('batch-submit');

  function updateCounter() {
    const lines = textarea.value.split('\n').filter(l => l.trim()).length;
    counter.textContent = `${Math.min(lines, 20)} / 20 items`;
    counter.style.color = lines > 20 ? 'var(--danger)' : 'var(--text-muted)';
  }

  textarea.addEventListener('input', updateCounter);

  btn.addEventListener('click', async () => {
    const items = textarea.value.split('\n').map(l => l.trim()).filter(Boolean).slice(0, 20);
    if (!items.length) { showToast('Please enter at least one item', 'warning'); return; }
    setButtonLoading(btn, true);
    try {
      const result = await api.classifyBatch(items);
      renderBatchResults(result);
      showToast(`Classified ${result.total} items`, 'success');
    } catch (err) {
      showToast(err.message || 'Batch classification failed', 'error');
    } finally {
      setButtonLoading(btn, false);
    }
  });
}

/* ── Chat Tab ───────────────────────────────────────────── */
function initChatTab() {
  const input   = document.getElementById('chat-message-input');
  const sendBtn = document.getElementById('chat-send-btn');
  const msgs    = document.getElementById('chat-messages');

  function addMsg(role, content) {
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${role}`;
    const avatar = role === 'bot' ? '🌿' : '👤';
    bubble.innerHTML = `
      <div class="bubble-avatar">${avatar}</div>
      <div class="bubble-content">${escHtml(content)}</div>`;
    msgs.appendChild(bubble);
    msgs.scrollTop = msgs.scrollHeight;
  }

  async function sendMessage() {
    const msg = input.value.trim();
    if (!msg || !state.sessionId) return;
    addMsg('user', msg);
    input.value = '';
    setButtonLoading(sendBtn, true);
    const thinkingEl = document.createElement('div');
    thinkingEl.className = 'chat-bubble bot';
    thinkingEl.innerHTML = `<div class="bubble-avatar">🌿</div><div class="bubble-content"><span class="spinner spinner-sm"></span></div>`;
    msgs.appendChild(thinkingEl);
    msgs.scrollTop = msgs.scrollHeight;
    try {
      const res = await api.chat(msg, state.sessionId, null);
      thinkingEl.remove();
      addMsg('bot', res.reply || 'No response');
      if (res.classification) renderResult(res.classification);
    } catch (err) {
      thinkingEl.remove();
      addMsg('bot', `Sorry, I ran into an error: ${err.message}`);
    } finally {
      setButtonLoading(sendBtn, false);
    }
  }

  sendBtn.addEventListener('click', sendMessage);
  input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });
  updateChatSession();
}

/* ── Categories ─────────────────────────────────────────── */
async function initCategories() {
  const grid = document.getElementById('categories-grid');
  try {
    const data = await api.getCategories();
    const cats = data.categories || data;
    grid.innerHTML = cats.map(cat => {
      const bin = (cat.bin_color || 'grey').toLowerCase();
      const icon = CAT_ICONS[cat.id] || '♻️';
      const examples = (cat.examples || []).slice(0, 4);
      return `
        <div class="category-card bin-${bin}">
          <div class="cat-header">
            <div class="cat-icon">${icon}</div>
            <span class="cat-name">${escHtml(cat.label || cat.name || cat.id)}</span>
          </div>
          <p class="cat-bin">${escHtml(BIN_NAMES[bin] || bin)} · ${escHtml(cat.bin_label || '')}</p>
          <p class="cat-desc">${escHtml(cat.description || '')}</p>
          ${examples.length
            ? `<div class="cat-examples">${examples.map(e => `<span class="cat-example">${escHtml(e)}</span>`).join('')}</div>`
            : ''}
        </div>`;
    }).join('');
  } catch (err) {
    grid.innerHTML = `<p class="empty-results">Could not load categories: ${escHtml(err.message)}</p>`;
  }
}

/* ── Facilities ─────────────────────────────────────────── */
function initFacilities() {
  const cityInput = document.getElementById('facility-city');
  const pinInput  = document.getElementById('facility-pincode');
  const catSelect = document.getElementById('facility-category');
  const searchBtn = document.getElementById('facility-search-btn');
  const results   = document.getElementById('facilities-results');

  async function search() {
    const city = cityInput.value.trim();
    const pin  = pinInput.value.trim();
    if (!city && !pin) { showToast('Please enter a city or pincode', 'warning'); return; }
    setButtonLoading(searchBtn, true);
    results.innerHTML = `<div style="display:flex;justify-content:center;padding:40px"><div class="spinner"></div></div>`;
    try {
      const data = await api.searchFacilities(city, pin, catSelect.value || null, 12);
      renderFacilities(data, results);
    } catch (err) {
      results.innerHTML = `<p class="empty-results">Search failed: ${escHtml(err.message)}</p>`;
    } finally {
      setButtonLoading(searchBtn, false);
    }
  }

  searchBtn.addEventListener('click', search);
  [cityInput, pinInput].forEach(el => el.addEventListener('keydown', e => { if (e.key === 'Enter') search(); }));
}

/* ── Boot ───────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initHealth();
  initTextTab();
  initImageTab();
  initVoiceTab();
  initBatchTab();
  initChatTab();
  initCategories();
  initFacilities();
});
