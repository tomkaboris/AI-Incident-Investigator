const state = {
  view: 'overview',
  incidents: [],
  overview: null,
  selectedIncident: null,
  selectedInvestigation: null,
  investigations: [],
  archiveAnalysis: null,
  archiveArtifacts: [],
  archiveTimeline: [],
  uploadMode: 'single',
  selectedFile: null,
  logText: '',
  logFilter: 'all',
  currentUser: null,
  csrfToken: null,
};

const root = document.getElementById('view-root');
const navItems = [...document.querySelectorAll('[data-view]')];
const sidebar = document.getElementById('sidebar');
const globalSearch = document.getElementById('global-search');

const api = async (url, options = {}) => {
  const method=(options.method||'GET').toUpperCase();
  if(!['GET','HEAD','OPTIONS'].includes(method) && state.csrfToken){options.headers={...(options.headers||{}),'X-CSRF-Token':state.csrfToken};}
  const response = await fetch(url, options);
  if (response.status === 401) { location.href = '/login'; throw new Error('Authentication required.'); }
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }
  const contentType = response.headers.get('content-type') || '';
  return contentType.includes('application/json') ? response.json() : response.text();
};

const esc = (value) => String(value ?? '')
  .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;').replaceAll("'", '&#039;');

const titleCase = (value) => String(value || 'unknown').replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
const pct = (value) => `${Math.round((Number(value) || 0) * 100)}%`;
const bytes = (value) => {
  const n = Number(value) || 0;
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} MB`;
  return `${(n / 1024 ** 3).toFixed(1)} GB`;
};
const duration = (ms) => ms == null ? '—' : ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`;
const money = (value, currency = 'USD') => value == null
  ? '—'
  : new Intl.NumberFormat('en-US', {
      style: 'currency', currency, minimumFractionDigits: 4, maximumFractionDigits: 8,
    }).format(Number(value));
const number = (value) => value == null ? '—' : new Intl.NumberFormat().format(Number(value));
const archiveExtensions = ['.zip','.tar','.tgz','.tar.gz','.tbz2','.tar.bz2','.txz','.tar.xz','.gz','.bz2','.xz'];
const isArchiveFile = (file) => {
  const name = String(file?.name || '').toLowerCase();
  return archiveExtensions.some(extension => name.endsWith(extension));
};
const costStatusText = (item) => {
  if (item?.cost_status === 'estimated') return 'Estimated from configured rates';
  if (item?.cost_status === 'pricing_unconfigured') return 'Configure model pricing to calculate cost';
  return 'Provider did not return token usage';
};
const usageCostCard = (label, item, provider, model) => `
  <div class="usage-card">
    <div class="usage-card-head"><strong>${esc(label)}</strong><span class="badge ${item?.cost_status === 'estimated' ? 'success' : 'neutral'}">${esc(item?.cost_status === 'estimated' ? money(item.estimated_cost_usd, item.cost_currency || 'USD') : 'Unavailable')}</span></div>
    <div class="usage-model">${esc(provider || 'Unknown provider')} · ${esc(model || 'Unknown model')}</div>
    <div class="usage-stats"><span>Input <strong>${number(item?.input_tokens)}</strong></span><span>Output <strong>${number(item?.output_tokens)}</strong></span><span>Total <strong>${number(item?.total_tokens)}</strong></span></div>
    <p>${esc(costStatusText(item))}</p>
  </div>`;
const dateTime = (value) => new Intl.DateTimeFormat(undefined, {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(value));
const relative = (value) => {
  const delta = Date.now() - new Date(value).getTime();
  const mins = Math.floor(delta / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
};

function toast(message, kind = '') {
  const region = document.getElementById('toast-region');
  const item = document.createElement('div');
  item.className = `toast ${kind}`;
  item.textContent = message;
  region.append(item);
  setTimeout(() => item.remove(), 4200);
}

function setActive(view) {
  state.view = view;
  document.querySelectorAll('.nav-item').forEach(item => item.classList.toggle('active', item.dataset.view === view));
  sidebar.classList.remove('open');
  window.location.hash = view;
}

function pageHeader(eyebrow, title, subtitle, actions = '') {
  return `<div class="page-head"><div><p class="eyebrow">${esc(eyebrow)}</p><h1>${esc(title)}</h1><p class="page-subtitle">${esc(subtitle)}</p></div><div class="actions">${actions}</div></div>`;
}

function severityBadge(severity) {
  const value = String(severity || 'unknown').toLowerCase();
  return `<span class="badge ${esc(value)}">${esc(value)}</span>`;
}

function confidence(value) {
  const percent = Math.round((Number(value) || 0) * 100);
  return `<div class="confidence"><div class="confidence-track"><div class="confidence-fill" style="width:${percent}%"></div></div><span class="confidence-value">${percent}%</span></div>`;
}

function incidentRows(items) {
  if (!items.length) return `<tr><td colspan="7"><div class="empty-state"><strong>No incidents found</strong>Upload a log to begin your first AI investigation.</div></td></tr>`;
  return items.map(item => `
    <tr data-incident="${esc(item.id)}">
      <td>${severityBadge(item.severity)}</td>
      <td><div class="cell-title">${esc(item.title)}</div><div class="cell-subtitle">${esc(item.problem_description || item.filename)} · Created by ${esc(item.created_by_name || "Unknown")}</div></td>
      <td><span class="badge neutral">${esc(titleCase(item.category))}</span></td>
      <td><div class="cell-title">${esc(item.probable_root_cause)}</div></td>
      <td>${confidence(item.latest_root_cause_confidence ?? item.confidence)}</td>
      <td><span class="badge ${item.requires_human_review ? 'medium' : 'success'}">${item.requires_human_review ? 'Review' : item.status}</span></td>
      <td><span title="${esc(dateTime(item.created_at))}">${esc(relative(item.created_at))}</span></td>
    </tr>`).join('');
}

function chartRows(data = {}) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...entries.map(([, value]) => value), 1);
  return entries.length ? entries.map(([name, value]) => `
    <div class="chart-row"><span class="chart-label">${esc(titleCase(name))}</span><div class="chart-bar"><span style="width:${Math.max(5, value / max * 100)}%"></span></div><span class="chart-value">${value}</span></div>`).join('') : '<div class="empty-state">No data yet.</div>';
}

async function loadOverview() {
  setActive('overview');
  root.innerHTML = `<div class="skeleton" style="height:120px"></div><div style="height:16px"></div><div class="skeleton" style="height:420px"></div>`;
  try {
    state.overview = await api('/api/v1/dashboard/overview');
    const o = state.overview;
    root.innerHTML = `${pageHeader('Operational intelligence', 'Incident command center', 'A focused view of reliability, AI investigations, and issues that need human attention.', '<button class="secondary" data-view="incidents">View incidents</button><button class="primary" data-view="new">＋ New investigation</button>')}
      <div class="metrics">
        ${metric('Open incidents', o.open_incidents, `${o.total_incidents} total`, '◫')}
        ${metric('Critical incidents', o.critical_incidents, 'Requires immediate focus', '!')}
        ${metric('Investigations', o.investigations_total, 'Multi-agent runs', '◇')}
        ${metric('Average confidence', pct(o.average_confidence), 'Initial analysis confidence', '◎')}
        ${metric('Human review', o.human_review_required, `Avg. ${duration(o.average_analysis_duration_ms)}`, '⌁')}
      </div>
      <div class="grid-2">
        <section class="panel"><div class="panel-header"><div><h2>Recent incidents</h2><p class="page-subtitle">Latest analyzed logs and their probable root causes.</p></div><button class="panel-link" data-view="incidents">View all →</button></div><div class="table-wrap"><table><thead><tr><th>Severity</th><th>Incident</th><th>Category</th><th>Probable root cause</th><th>Confidence</th><th>Status</th><th>Created</th></tr></thead><tbody>${incidentRows(o.recent_incidents)}</tbody></table></div></section>
        <div class="stack">
          <section class="panel"><div class="panel-header"><h2>Severity distribution</h2></div><div class="panel-body chart-list">${chartRows(o.incidents_by_severity)}</div></section>
          <section class="panel"><div class="panel-header"><h2>Storage</h2><span class="badge success">Verified</span></div><div class="panel-body"><div class="metric-value">${bytes(o.storage_bytes)}</div><p class="page-subtitle">Externalized log objects protected by SHA-256 integrity checks.</p></div></section>
        </div>
      </div>
      <div class="grid-3">
        <section class="panel"><div class="panel-header"><h2>Incident categories</h2></div><div class="panel-body chart-list">${chartRows(o.incidents_by_category)}</div></section>
        <section class="panel"><div class="panel-header"><h2>AI workflow</h2><span class="badge success">Ready</span></div><div class="panel-body"><div class="timeline"><div class="chain-step">1. Classify incident</div><div class="chain-step">2. Investigate root cause</div><div class="chain-step">3. Generate safe remediation</div><div class="chain-step">4. Produce incident report</div></div></div></section>
        <section class="panel"><div class="panel-header"><h2>Recommended next step</h2></div><div class="panel-body"><p class="page-subtitle">Add a problem description with symptoms and recent changes before uploading the log. The AI treats it as context while technical evidence remains the source of truth.</p><button class="primary" data-view="new" style="margin-top:16px;width:100%">Start an investigation</button></div></section>
      </div>`;
    bindDynamic();
  } catch (error) { renderError(error); }
}

function metric(label, value, note, icon) {
  return `<div class="metric-card"><div class="metric-top"><span>${esc(label)}</span><span class="metric-icon">${esc(icon)}</span></div><div><div class="metric-value">${esc(value)}</div><div class="metric-note">${esc(note)}</div></div></div>`;
}

async function loadIncidents(search = '') {
  setActive('incidents');
  root.innerHTML = `${pageHeader('Investigation library', 'Incidents', 'Search, filter, and open every analyzed incident in the workspace.', '<button class="primary" data-view="new">＋ New investigation</button>')}<div class="skeleton" style="height:450px"></div>`;
  try {
    const query = new URLSearchParams();
    if (search) query.set('search', search);
    state.incidents = await api(`/api/v1/dashboard/incidents?${query}`);
    renderIncidents();
  } catch (error) { renderError(error); }
}

function renderIncidents() {
  root.innerHTML = `${pageHeader('Investigation library', 'Incidents', `${state.incidents.length} incidents available in this workspace.`, '<button class="primary" data-view="new">＋ New investigation</button>')}
    <div class="filters"><input class="input" id="incident-search" type="search" placeholder="Search title, filename, summary or problem description"><select class="select" id="severity-filter"><option value="">All severities</option><option>critical</option><option>high</option><option>medium</option><option>low</option></select><select class="select" id="category-filter"><option value="">All categories</option>${[...new Set(state.incidents.map(i => i.category))].map(v => `<option value="${esc(v)}">${esc(titleCase(v))}</option>`).join('')}</select></div>
    <section class="panel"><div class="table-wrap"><table><thead><tr><th>Severity</th><th>Incident</th><th>Category</th><th>Probable root cause</th><th>Confidence</th><th>Status</th><th>Created</th></tr></thead><tbody id="incident-table-body">${incidentRows(state.incidents)}</tbody></table></div></section>`;
  document.getElementById('incident-search').addEventListener('input', filterIncidentTable);
  document.getElementById('severity-filter').addEventListener('change', filterIncidentTable);
  document.getElementById('category-filter').addEventListener('change', filterIncidentTable);
  bindIncidentRows(); bindDynamic();
}

function filterIncidentTable() {
  const term = document.getElementById('incident-search').value.toLowerCase();
  const severity = document.getElementById('severity-filter').value;
  const category = document.getElementById('category-filter').value;
  const filtered = state.incidents.filter(item => {
    const haystack = `${item.title} ${item.filename} ${item.summary} ${item.problem_description || ''} ${item.probable_root_cause}`.toLowerCase();
    return (!term || haystack.includes(term)) && (!severity || item.severity === severity) && (!category || item.category === category);
  });
  document.getElementById('incident-table-body').innerHTML = incidentRows(filtered);
  bindIncidentRows();
}

function renderNew() {
  setActive('new');
  state.selectedFile = null;
  state.uploadMode = 'single';
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  root.innerHTML = `${pageHeader('Guided analysis', 'New investigation', 'Use one premium form for a single log or a recursively extracted support bundle.')}
    <form id="upload-form" class="panel">
      <div class="panel-body">
        <div class="upload-mode" id="upload-mode">
          <div class="mode-card active" data-mode="single"><span class="mode-icon">▤</span><div><strong>Single log</strong><p>Fast analysis of one LOG, TXT, JSON, CSV or YAML file.</p></div></div>
          <div class="mode-card" data-mode="archive"><span class="mode-icon">▦</span><div><strong>Support bundle</strong><p>ZIP, TAR or compressed archive with nested logs and components.</p></div></div>
        </div>
      </div>
      <div class="panel-body upload-layout" style="padding-top:0">
        <div>
          <input id="file-input" type="file" hidden accept=".log,.txt,.out,.err,.json,.jsonl,.csv,.yaml,.yml,.zip,.tar,.tgz,.tar.gz,.tbz2,.tar.bz2,.txz,.tar.xz,.gz,.bz2,.xz">
          <div class="upload-zone" id="upload-zone" tabindex="0" role="button">
            <div><div class="upload-icon">⇧</div><strong id="upload-title">Drop a log or support bundle here</strong><p id="upload-copy">The file type is detected automatically.<br>Nested archives are processed by the secure archive backend.</p><div class="selected-file" id="selected-file"></div></div>
          </div>
          <div class="archive-security-note hidden" id="archive-security-note"><strong>Archive safety enabled</strong><span>Path traversal, symlinks, file count, extraction size, depth and compression ratio are validated before analysis.</span></div>
        </div>
        <div>
          <div class="form-group"><label for="problem-description">Observed problem <span id="description-required" style="color:var(--muted);font-weight:400">(optional for a single log)</span></label><textarea class="textarea" id="problem-description" maxlength="5000" placeholder="Describe symptoms, affected environment, timing, expected behavior and recent changes."></textarea><div class="form-help"><span id="description-count">0</span>/5000 characters</div></div>
          <div class="archive-options hidden" id="archive-options">
            <div class="form-group"><label for="system-name">System or product</label><input class="input" id="system-name" maxlength="255" placeholder="Example: payments-production-cluster"></div>
            <div class="field-grid"><div class="form-group"><label for="incident-time">Approximate incident time</label><input class="input" id="incident-time" type="datetime-local"></div><div class="form-group"><label for="incident-timezone">Timezone</label><input class="input" id="incident-timezone" value="${esc(timezone)}" required></div></div>
          </div>
          <div class="description-box"><strong style="color:var(--text)">Evidence-first AI</strong><br>Descriptions are unverified context. Technical logs and correlated archive events remain the source of truth.</div>
        </div>
      </div>
      <div class="panel-body" style="padding-top:0"><div class="form-footer"><div class="trust-note" id="upload-trust">The original file is checksum-protected. Token usage and estimated provider cost are saved with the investigation when available.</div><button class="primary" id="analyze-button" type="submit">Start AI investigation →</button></div><div class="progress-wrap" id="progress"><div class="progress-track"><span></span></div><p class="page-subtitle" id="progress-label">Validating and analyzing technical evidence...</p></div></div>
    </form>`;
  const zone = document.getElementById('upload-zone');
  const input = document.getElementById('file-input');
  const description = document.getElementById('problem-description');
  zone.addEventListener('click', () => input.click());
  zone.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') input.click(); });
  input.addEventListener('change', () => selectFile(input.files[0]));
  ['dragenter','dragover'].forEach(type => zone.addEventListener(type, event => { event.preventDefault(); zone.classList.add('dragging'); }));
  ['dragleave','drop'].forEach(type => zone.addEventListener(type, event => { event.preventDefault(); zone.classList.remove('dragging'); }));
  zone.addEventListener('drop', event => selectFile(event.dataTransfer.files[0]));
  description.addEventListener('input', () => document.getElementById('description-count').textContent = description.value.length);
  document.querySelectorAll('[data-mode]').forEach(card => card.addEventListener('click', () => setUploadMode(card.dataset.mode)));
  document.getElementById('upload-form').addEventListener('submit', submitIncident);
}

function setUploadMode(mode) {
  state.uploadMode = mode;
  document.querySelectorAll('[data-mode]').forEach(card => card.classList.toggle('active', card.dataset.mode === mode));
  document.getElementById('archive-options')?.classList.toggle('hidden', mode !== 'archive');
  document.getElementById('archive-security-note')?.classList.toggle('hidden', mode !== 'archive');
  const required = document.getElementById('description-required');
  if (required) required.textContent = mode === 'archive' ? '(required for a support bundle)' : '(optional for a single log)';
  const progress = document.getElementById('progress-label');
  if (progress) progress.textContent = mode === 'archive'
    ? 'Securely extracting, indexing, correlating and analyzing bundle artifacts...'
    : 'Validating and analyzing technical evidence...';
}

function selectFile(file) {
  if (!file) return;
  state.selectedFile = file;
  setUploadMode(isArchiveFile(file) ? 'archive' : 'single');
  const selected = document.getElementById('selected-file');
  selected.classList.add('visible');
  selected.innerHTML = `<div class="file-kind">${state.uploadMode === 'archive' ? 'SUPPORT BUNDLE' : 'SINGLE LOG'}</div><strong>${esc(file.name)}</strong><p>${bytes(file.size)} · ${esc(file.type || 'application/octet-stream')}</p>`;
}

async function submitIncident(event) {
  event.preventDefault();
  if (!state.selectedFile) return toast('Choose a log file or support bundle first.', 'error');
  const description = document.getElementById('problem-description').value.trim();
  if (state.uploadMode === 'archive' && description.length < 3) {
    return toast('Describe the observed problem before analyzing a support bundle.', 'error');
  }
  const button = document.getElementById('analyze-button');
  const progress = document.getElementById('progress');
  button.disabled = true;
  progress.classList.add('visible');
  const form = new FormData();
  let endpoint;
  if (state.uploadMode === 'archive') {
    endpoint = '/api/v1/incidents/analyze-archive';
    form.append('archive_file', state.selectedFile);
    form.append('problem_description', description);
    form.append('timezone', document.getElementById('incident-timezone').value.trim() || 'UTC');
    const incidentTime = document.getElementById('incident-time').value;
    const systemName = document.getElementById('system-name').value.trim();
    if (incidentTime) form.append('incident_time', incidentTime);
    if (systemName) form.append('system_name', systemName);
  } else {
    endpoint = '/api/v1/incidents/analyze';
    form.append('log_file', state.selectedFile);
    if (description) form.append('problem_description', description);
  }
  try {
    const result = await api(endpoint, {method: 'POST', body: form});
    toast(state.uploadMode === 'archive' ? 'Support bundle analyzed successfully.' : 'Incident analyzed successfully.', 'success');
    await openIncident(result.incident_id || result.id);
  } catch (error) {
    toast(error.message, 'error');
    button.disabled = false;
    progress.classList.remove('visible');
  }
}

async function openIncident(id) {
  root.innerHTML = `<div class="skeleton" style="height:160px"></div><div style="height:18px"></div><div class="skeleton" style="height:520px"></div>`;
  try {
    const [incident, investigations] = await Promise.all([
      api(`/api/v1/incidents/${id}`),
      api(`/api/v1/incidents/${id}/investigations`),
    ]);
    let archiveAnalysis = null;
    try { archiveAnalysis = await api(`/api/v1/incidents/${id}/archive-analysis`); } catch (_) {}
    let artifacts = [];
    let timeline = [];
    if (archiveAnalysis) {
      [artifacts, timeline] = await Promise.all([
        api(`/api/v1/incidents/${id}/artifacts`),
        api(`/api/v1/incidents/${id}/timeline`),
      ]);
    }
    state.selectedIncident = incident;
    state.investigations = investigations;
    state.selectedInvestigation = investigations[0] || null;
    state.archiveAnalysis = archiveAnalysis;
    state.archiveArtifacts = artifacts;
    state.archiveTimeline = timeline;
    state.logText = '';
    state.view = 'detail';
    window.location.hash = `incident/${id}`;
    renderIncidentWorkspace();
  } catch (error) { renderError(error); }
}

function renderIncidentWorkspace() {
  const incident = state.selectedIncident;
  const archiveStored = state.archiveAnalysis;
  const archive = archiveStored?.analysis;
  const analysis = archive || incident.analysis;
  const investigation = state.selectedInvestigation;
  const full = investigation?.full_result;
  const rc = full?.root_cause;
  const classification = full?.classification;
  const report = full?.report;
  const isArchive = Boolean(archiveStored);
  const displayConfidence = rc?.confidence ?? analysis.confidence;
  const reportText = archive?.markdown_report || report?.markdown;
  const estimatedItems = [];
  if (isArchive) estimatedItems.push(archiveStored);
  else estimatedItems.push({
    input_tokens: incident.initial_input_tokens,
    output_tokens: incident.initial_output_tokens,
    total_tokens: incident.initial_total_tokens,
    estimated_cost_usd: incident.initial_estimated_cost_usd,
    cost_status: incident.initial_cost_status,
    cost_currency: incident.initial_cost_currency,
  });
  estimatedItems.push(...state.investigations);
  const totalCost = estimatedItems.reduce((sum, item) => sum + (item?.estimated_cost_usd == null ? 0 : Number(item.estimated_cost_usd)), 0);
  const allEstimated = estimatedItems.length > 0 && estimatedItems.every(item => item?.cost_status === 'estimated');
  const tabs = isArchive
    ? `<button class="tab-button active" data-tab="archive-overview">Bundle overview</button><button class="tab-button" data-tab="evidence">Evidence</button><button class="tab-button" data-tab="chain">Causal chain</button><button class="tab-button" data-tab="fixes">Recommended fixes</button><button class="tab-button" data-tab="artifacts">Artifacts</button><button class="tab-button" data-tab="timeline-events">Timeline</button><button class="tab-button" data-tab="report">Report</button><button class="tab-button" data-tab="activity">Activity</button>`
    : `<button class="tab-button active" data-tab="evidence">Evidence</button><button class="tab-button" data-tab="chain">Causal chain</button><button class="tab-button" data-tab="fixes">Recommended fixes</button><button class="tab-button" data-tab="report">Report</button><button class="tab-button" data-tab="log">Log viewer</button><button class="tab-button" data-tab="activity">Activity</button>`;
  root.innerHTML = `
    <div class="incident-head"><div class="incident-title-row"><div><div style="display:flex;gap:8px;align-items:center;margin-bottom:10px">${severityBadge(analysis.severity)}<span class="badge neutral">INC-${esc(incident.id.slice(0,8).toUpperCase())}</span>${isArchive ? '<span class="badge archive">Support bundle</span>' : '<span class="badge neutral">Single log</span>'}${analysis.requires_human_review ? '<span class="badge medium">Human review</span>' : '<span class="badge success">AI analyzed</span>'}</div><h1>${esc(analysis.title)}</h1><p class="page-subtitle">${esc(analysis.executive_summary || analysis.summary)}</p><div class="incident-meta"><span>${esc(titleCase(analysis.category))}</span><span>•</span><span>${esc(incident.filename)}</span><span>•</span><span>${esc(dateTime(incident.created_at))}</span><span>•</span><span>Created by ${esc(incident.created_by_name || 'Unknown')}</span></div></div><div class="actions"><button class="secondary" id="mark-resolved">Mark resolved</button><button class="secondary" id="download-log">Download original</button><button class="secondary" id="copy-report" ${reportText ? '' : 'disabled'}>Copy report</button>${isArchive ? '<span class="badge success action-status">Archive analysis complete</span>' : `<button class="primary" id="orchestrate-button">${investigation ? 'Re-run investigation' : 'Run multi-agent investigation'}</button>`}</div></div></div>
    <div class="workspace-grid">
      <div class="stack">
        <section class="panel root-cause-hero"><div class="root-cause-label">Probable root cause</div><div class="root-cause-text">${esc(rc?.probable_root_cause || analysis.probable_root_cause)}</div><div class="confidence-large">${confidence(displayConfidence)}<span class="badge ${displayConfidence >= .85 ? 'success' : 'medium'}">${displayConfidence >= .85 ? 'Strong support' : 'Review suggested'}</span></div></section>
        ${incident.problem_description ? `<section class="panel"><div class="panel-header"><h2>Reported problem</h2><span class="badge neutral">Context</span></div><div class="panel-body"><div class="description-box">${esc(incident.problem_description)}</div></div></section>` : ''}
        <section class="panel"><div class="tab-list">${tabs}</div><div class="panel-body" id="workspace-tab"></div></section>
      </div>
      <aside class="stack">
        <section class="panel"><div class="panel-header"><h2>AI usage & cost</h2><span class="badge ${allEstimated ? 'success' : 'neutral'}">${allEstimated ? money(totalCost) : 'Partial estimate'}</span></div><div class="panel-body usage-list">${isArchive ? usageCostCard('Archive analysis', archiveStored, archiveStored.provider_name, archiveStored.model_name) : usageCostCard('Initial analysis', {input_tokens:incident.initial_input_tokens,output_tokens:incident.initial_output_tokens,total_tokens:incident.initial_total_tokens,estimated_cost_usd:incident.initial_estimated_cost_usd,cost_status:incident.initial_cost_status,cost_currency:incident.initial_cost_currency}, incident.initial_provider_name, incident.initial_model_name)}${state.investigations.map((item,index)=>usageCostCard(`Multi-agent run ${state.investigations.length-index}`,item,item.provider_name,item.model_name)).join('')}</div></section>
        ${isArchive ? `<section class="panel"><div class="panel-header"><h2>Bundle metadata</h2><span class="badge archive">${number(state.archiveArtifacts.length)} artifacts</span></div><div class="panel-body meta-grid"><div class="meta-item"><span>System</span><strong>${esc(archiveStored.system_name || 'Not specified')}</strong></div><div class="meta-item"><span>Timezone</span><strong>${esc(archiveStored.timezone || 'UTC')}</strong></div><div class="meta-item"><span>Extracted size</span><strong>${bytes(archiveStored.total_extracted_size_bytes)}</strong></div><div class="meta-item"><span>Nested depth</span><strong>${number(archiveStored.max_depth_reached)}</strong></div><div class="meta-item"><span>Components</span><strong>${number(archive.affected_components?.length || 0)}</strong></div><div class="meta-item"><span>Timeline events</span><strong>${number(state.archiveTimeline.length)}</strong></div></div></section>` : ''}
        <section class="panel"><div class="panel-header"><h2>Incident metadata</h2></div><div class="panel-body meta-grid"><div class="meta-item"><span>Created by</span><strong>${esc(incident.created_by_name || 'Unknown')}</strong></div><div class="meta-item"><span>Assigned to</span><strong>${esc(incident.assigned_to_name || 'Unassigned')}</strong></div><div class="meta-item"><span>Category</span><strong>${esc(titleCase(classification?.category || analysis.category))}</strong></div><div class="meta-item"><span>Storage</span><strong>${esc(titleCase(incident.log_storage_backend))}</strong></div><div class="meta-item"><span>Original size</span><strong>${bytes(incident.log_size_bytes)}</strong></div><div class="meta-item"><span>Investigations</span><strong>${number(state.investigations.length + 1)}</strong></div></div></section>
        <section class="panel"><div class="panel-header"><h2>Integrity</h2><span class="badge success">SHA-256 verified</span></div><div class="panel-body"><p class="page-subtitle checksum">${esc(incident.log_checksum_sha256)}</p></div></section>
      </aside>
    </div>`;
  renderWorkspaceTab(isArchive ? 'archive-overview' : 'evidence');
  document.querySelectorAll('.tab-button').forEach(button => button.addEventListener('click', () => {
    document.querySelectorAll('.tab-button').forEach(item => item.classList.remove('active'));
    button.classList.add('active');
    renderWorkspaceTab(button.dataset.tab);
  }));
  document.getElementById('orchestrate-button')?.addEventListener('click', runOrchestration);
  document.getElementById('mark-resolved').addEventListener('click', markResolved);
  document.getElementById('download-log').addEventListener('click', () => window.open(`/api/v1/incidents/${incident.id}/log`, '_blank'));
  document.getElementById('copy-report').addEventListener('click', async () => {
    if (reportText) { await navigator.clipboard.writeText(reportText); toast('Incident report copied.', 'success'); }
  });
}

function renderWorkspaceTab(tab) {
  const target = document.getElementById('workspace-tab');
  const analysis = state.selectedIncident.analysis;
  const archive = state.archiveAnalysis?.analysis;
  const full = state.selectedInvestigation?.full_result;
  const rc = full?.root_cause;
  const fix = full?.fix_recommendation;
  const report = full?.report;
  if (tab === 'archive-overview') {
    const components = archive?.affected_components || [];
    const events = archive?.correlated_events || [];
    target.innerHTML = `<div class="archive-summary"><div class="summary-stat"><span>Artifacts</span><strong>${number(state.archiveArtifacts.length)}</strong></div><div class="summary-stat"><span>Log candidates</span><strong>${number(state.archiveArtifacts.filter(item=>item.is_log_candidate).length)}</strong></div><div class="summary-stat"><span>Components</span><strong>${number(components.length)}</strong></div><div class="summary-stat"><span>Correlated events</span><strong>${number(events.length)}</strong></div></div><div class="grid-2 archive-detail"><div><h3>Affected components</h3><div class="chip-list">${components.length ? components.map(item=>`<span class="chip">${esc(item)}</span>`).join('') : '<span class="page-subtitle">No components identified.</span>'}</div></div><div><h3>Analysis window</h3><p class="page-subtitle">${archive?.analyzed_time_window_start ? esc(dateTime(archive.analyzed_time_window_start)) : 'Unbounded'} → ${archive?.analyzed_time_window_end ? esc(dateTime(archive.analyzed_time_window_end)) : 'Unbounded'}</p></div></div>`;
  } else if (tab === 'evidence') {
    const evidence = archive?.supporting_evidence || rc?.evidence || analysis.evidence || [];
    target.innerHTML = `<div class="evidence-list">${evidence.length ? evidence.map((item,index)=>`<div class="evidence-card"><div class="evidence-source">Evidence ${index+1}${item.path ? ` · ${esc(item.path)}` : ''}${item.line_start ? ` · Lines ${item.line_start}${item.line_end && item.line_end!==item.line_start ? `–${item.line_end}` : ''}` : item.line_number ? ` · Line ${item.line_number}` : ''}${item.timestamp_utc ? ` · ${esc(dateTime(item.timestamp_utc))}` : ''}</div><code>${esc(item.excerpt)}</code><p>${esc(item.explanation)}</p></div>`).join('') : '<div class="empty-state"><strong>No structured evidence</strong>No evidence was returned by the selected model.</div>'}</div>`;
  } else if (tab === 'chain') {
    const chain = archive?.causal_chain || rc?.failure_chain || [];
    target.innerHTML = chain.length ? `<div class="causal-chain">${chain.map((step,i)=>`<div class="chain-step">${esc(step)}</div>${i<chain.length-1?'<div class="chain-arrow">↓</div>':''}`).join('')}</div>` : '<div class="empty-state"><strong>Causal chain not generated</strong>There was not enough structured evidence to create a failure sequence.</div>';
  } else if (tab === 'fixes') {
    if (archive) {
      const immediate = archive.immediate_actions || [];
      const longTerm = archive.long_term_actions || [];
      target.innerHTML = `<div class="fix-section"><h3>Immediate mitigation</h3><div class="action-list">${immediate.map((item,index)=>`<div class="action-card"><div class="action-title"><span>${index+1}. ${esc(item)}</span><span class="badge medium">Review first</span></div></div>`).join('') || '<p class="page-subtitle">No immediate actions returned.</p>'}</div></div><div class="fix-section"><h3>Long-term prevention</h3><div class="action-list">${longTerm.map((item,index)=>`<div class="action-card"><div class="action-title"><span>${index+1}. ${esc(item)}</span></div></div>`).join('') || '<p class="page-subtitle">No long-term actions returned.</p>'}</div></div>`;
    } else {
      const actions = [...(fix?.immediate_actions || []), ...(fix?.long_term_actions || [])];
      target.innerHTML = actions.length ? `<div class="action-list"><p class="page-subtitle">${esc(fix.recommended_strategy)}</p>${actions.map(action=>`<div class="action-card"><div class="action-title"><span>${esc(action.title)}</span><span class="badge ${esc(action.risk)}">${esc(action.risk)} risk</span></div><p>${esc(action.description)}</p><p><strong>Why:</strong> ${esc(action.rationale)}</p></div>`).join('')}</div>` : `<div class="action-list">${analysis.recommended_actions.map((action,index)=>`<div class="action-card"><div class="action-title"><span>${index+1}. ${esc(action)}</span></div></div>`).join('')}</div>`;
    }
  } else if (tab === 'artifacts') {
    const rows = state.archiveArtifacts;
    target.innerHTML = `<div class="artifact-toolbar"><input class="input" id="artifact-search" type="search" placeholder="Search paths, components or formats"><select class="select" id="artifact-kind"><option value="all">All artifacts</option><option value="logs">Log candidates</option><option value="archives">Nested archives</option></select></div><div class="table-wrap"><table class="artifact-table"><thead><tr><th>Artifact</th><th>Component</th><th>Format</th><th>Depth</th><th>Size</th><th>Time range</th></tr></thead><tbody id="artifact-body"></tbody></table></div>`;
    const renderArtifacts = () => {
      const term=(document.getElementById('artifact-search').value||'').toLowerCase();
      const kind=document.getElementById('artifact-kind').value;
      const filtered=rows.filter(item=>(!term||`${item.original_path} ${item.component||''} ${item.log_format||''}`.toLowerCase().includes(term))&&(kind==='all'||(kind==='logs'&&item.is_log_candidate)||(kind==='archives'&&item.is_archive)));
      document.getElementById('artifact-body').innerHTML=filtered.map(item=>`<tr><td><div class="cell-title">${esc(item.filename)}</div><div class="cell-sub">${esc(item.original_path)}</div></td><td>${esc(item.component||'Unknown')}</td><td>${esc(item.log_format||item.extension||'Unknown')}</td><td>${number(item.archive_depth)}</td><td>${bytes(item.size_bytes)}</td><td><div class="cell-sub">${item.earliest_timestamp?esc(dateTime(item.earliest_timestamp)):'—'}<br>${item.latest_timestamp?esc(dateTime(item.latest_timestamp)):'—'}</div></td></tr>`).join('') || '<tr><td colspan="6"><div class="empty-state"><strong>No matching artifacts</strong>Change the artifact filters.</div></td></tr>';
    };
    document.getElementById('artifact-search').addEventListener('input',renderArtifacts);
    document.getElementById('artifact-kind').addEventListener('change',renderArtifacts);
    renderArtifacts();
  } else if (tab === 'timeline-events') {
    const rows=state.archiveTimeline;
    target.innerHTML=`<div class="artifact-toolbar"><input class="input" id="timeline-search" type="search" placeholder="Search event message, path or component"><select class="select" id="timeline-severity"><option value="all">All severities</option><option value="error">Error</option><option value="warn">Warning</option><option value="info">Info</option></select></div><div class="event-timeline" id="event-timeline"></div>`;
    const renderEvents=()=>{const term=(document.getElementById('timeline-search').value||'').toLowerCase();const level=document.getElementById('timeline-severity').value;const filtered=rows.filter(item=>(!term||`${item.message} ${item.path} ${item.component}`.toLowerCase().includes(term))&&(level==='all'||String(item.severity||'').toLowerCase().includes(level)));document.getElementById('event-timeline').innerHTML=filtered.slice(0,1000).map(item=>`<div class="event-row"><div class="event-time">${item.timestamp_utc?esc(dateTime(item.timestamp_utc)):esc(item.original_timestamp||'Unknown time')}</div><div class="event-marker ${esc(String(item.severity||'').toLowerCase())}"></div><div class="event-content"><div><span class="badge neutral">${esc(item.component)}</span>${item.severity?` <span class="badge ${String(item.severity).toLowerCase().includes('error')?'critical':'neutral'}">${esc(item.severity)}</span>`:''}</div><strong>${esc(item.message)}</strong><p>${esc(item.path)}${item.line_number?` · line ${item.line_number}`:''}</p></div></div>`).join('')||'<div class="empty-state"><strong>No matching events</strong>Change the timeline filters.</div>';};document.getElementById('timeline-search').addEventListener('input',renderEvents);document.getElementById('timeline-severity').addEventListener('change',renderEvents);renderEvents();
  } else if (tab === 'report') {
    const markdown = archive?.markdown_report || report?.markdown;
    target.innerHTML = markdown ? `<div class="actions" style="margin-bottom:12px"><button class="secondary" id="copy-markdown">Copy Markdown</button></div><div class="report-markdown">${esc(markdown)}</div>` : '<div class="empty-state"><strong>No report available</strong>The selected model did not return a report.</div>';
    document.getElementById('copy-markdown')?.addEventListener('click', async()=>{await navigator.clipboard.writeText(markdown);toast('Markdown copied.','success');});
  } else if (tab === 'activity') {
    target.innerHTML='<div class="skeleton" style="height:180px"></div>';
    api(`/api/v1/incidents/${state.selectedIncident.id}/activities`).then(items=>{target.innerHTML=items.length?`<div class="action-list">${items.map(item=>`<div class="action-card"><div class="action-title"><span>${esc(titleCase(item.action))}</span><span class="badge neutral">${esc(relative(item.created_at))}</span></div><p>${esc(item.user_name)} · ${esc(dateTime(item.created_at))}</p></div>`).join('')}</div>`:'<div class="empty-state"><strong>No activity yet</strong>Actions on this incident will appear here.</div>';});
  } else if (tab === 'log') {
    target.innerHTML=`<div class="log-toolbar"><input class="input" id="log-search" type="search" placeholder="Search log"><select class="select" id="log-level"><option value="all">All levels</option><option value="error">Errors</option><option value="warn">Warnings</option><option value="info">Info</option></select><button class="secondary" id="load-log">${state.logText?'Refresh':'Load verified log'}</button></div><pre class="log-viewer" id="log-viewer">${state.logText?formatLog(state.logText):'The log is loaded only when requested.'}</pre>`;
    document.getElementById('load-log').addEventListener('click',loadLog);document.getElementById('log-search').addEventListener('input',renderLog);document.getElementById('log-level').addEventListener('change',renderLog);
  }
}

async function loadLog() {
  try {
    state.logText = await api(`/api/v1/incidents/${state.selectedIncident.id}/log`);
    renderLog(); toast('Verified log loaded.', 'success');
  } catch (error) { toast(error.message, 'error'); }
}
function renderLog() {
  const viewer = document.getElementById('log-viewer'); if (!viewer) return;
  const term = (document.getElementById('log-search')?.value || '').toLowerCase();
  const level = document.getElementById('log-level')?.value || 'all';
  const text = state.logText.split('\n').filter(line => (!term || line.toLowerCase().includes(term)) && (level === 'all' || line.toLowerCase().includes(level))).join('\n');
  viewer.innerHTML = formatLog(text);
}
function formatLog(text) {
  return esc(text).split('\n').map((line, i) => {
    const lower = line.toLowerCase(); const cls = lower.includes('error') || lower.includes('exception') || lower.includes('fatal') ? 'error' : lower.includes('warn') ? 'warn' : lower.includes('info') ? 'info' : '';
    return `<span class="log-line ${cls}">${String(i + 1).padStart(5, ' ')}  ${line}</span>`;
  }).join('\n');
}

async function markResolved(){
  try{await api(`/api/v1/incidents/${state.selectedIncident.id}/status`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:'resolved'})});toast('Incident marked resolved.','success');await openIncident(state.selectedIncident.id)}catch(error){toast(error.message,'error')}
}

async function runOrchestration() {
  const button = document.getElementById('orchestrate-button'); button.disabled = true; button.textContent = 'Investigating...';
  try {
    await api(`/api/v1/incidents/${state.selectedIncident.id}/orchestrate`, {method: 'POST'});
    toast('Multi-agent investigation completed.', 'success'); await openIncident(state.selectedIncident.id);
  } catch (error) { toast(error.message, 'error'); button.disabled = false; button.textContent = 'Run multi-agent investigation'; }
}

function renderAnalytics() {
  setActive('analytics');
  const o = state.overview;
  if (!o) return loadOverview().then(renderAnalytics);
  root.innerHTML = `${pageHeader('Reliability intelligence', 'Analytics', 'Understand recurring failure patterns, model performance indicators, and storage growth.')}
    <div class="metrics">${metric('Incident volume', o.total_incidents, 'All time', '◫')}${metric('Critical share', o.total_incidents ? `${Math.round(o.critical_incidents/o.total_incidents*100)}%` : '0%', 'Of all incidents', '!')}${metric('Review backlog', o.human_review_required, 'Human validation needed', '⌁')}${metric('Storage footprint', bytes(o.storage_bytes), 'Externalized logs', '◇')}${metric('Avg. duration', duration(o.average_analysis_duration_ms), 'Multi-agent investigation', '◎')}</div>
    <div class="grid-2"><section class="panel"><div class="panel-header"><h2>Root-cause categories</h2></div><div class="panel-body chart-list">${chartRows(o.incidents_by_category)}</div></section><section class="panel"><div class="panel-header"><h2>Severity profile</h2></div><div class="panel-body chart-list">${chartRows(o.incidents_by_severity)}</div></section></div>
    <section class="panel"><div class="panel-header"><h2>Model performance indicators</h2><span class="badge neutral">Ground truth required for accuracy</span></div><div class="panel-body"><p class="page-subtitle">Provider/model usage, token accounting and operator-confirmed root causes will populate this area as those fields become available. Confidence is an AI self-assessment and must not be presented as measured accuracy.</p></div></section>`;
}

async function renderSettings() {
  setActive('settings');
  root.innerHTML = `${pageHeader('Workspace configuration', 'Settings', 'Inspect active AI, database, storage, and security configuration. Secrets are never exposed here.')}<div class="skeleton" style="height:400px"></div>`;
  try {
    const health = await api('/health');
    root.innerHTML = `${pageHeader('Workspace configuration', 'Settings', 'Inspect active AI, database, storage, and security configuration. Secrets are never exposed here.')}
      <div class="settings-grid">
        <section class="panel"><div class="panel-header"><h2>AI provider</h2><span class="badge success">Connected</span></div><div class="panel-body"><div class="setting-row"><span>Provider</span><strong>${esc(titleCase(health.ai_provider))}</strong></div><div class="setting-row"><span>Default model</span><strong>${esc(health.ai_model)}</strong></div><div class="setting-row"><span>Cost estimation</span><strong>${health.ai_pricing_configured === 'true' ? 'Configured' : 'Pricing required'}</strong></div><div class="setting-row"><span>Multi-agent workflow</span><strong>Enabled</strong></div><p class="form-help">Change provider settings through environment variables, then restart the application.</p></div></section>
        <section class="panel"><div class="panel-header"><h2>Storage</h2><span class="badge success">Integrity enabled</span></div><div class="panel-body"><div class="setting-row"><span>Backend</span><strong>${esc(titleCase(health.storage_backend))}</strong></div><div class="setting-row"><span>Checksum</span><strong>SHA-256</strong></div><div class="setting-row"><span>Database</span><strong>${esc(titleCase(health.database))}</strong></div></div></section>
        <section class="panel"><div class="panel-header"><h2>Useful endpoints</h2></div><div class="panel-body"><div class="code-block">Dashboard: /dashboard\nREST API: /api/v1\nSwagger: /docs\nHealth: /health</div></div></section>
        <section class="panel"><div class="panel-header"><h2>Security posture</h2></div><div class="panel-body"><div class="setting-row"><span>Externalized logs</span><strong>Enabled</strong></div><div class="setting-row"><span>Binary rejection</span><strong>Configurable</strong></div><div class="setting-row"><span>Upload constraints</span><strong>Extension, MIME, size</strong></div><div class="setting-row"><span>Problem description</span><strong>Unverified context</strong></div></div></section>
      </div>`;
  } catch (error) { renderError(error); }
}

function renderError(error) {
  root.innerHTML = `<div class="empty-state"><strong>Unable to load the dashboard</strong>${esc(error.message)}<div style="margin-top:16px"><button class="primary" onclick="location.reload()">Retry</button></div></div>`;
}

function bindIncidentRows() {
  document.querySelectorAll('[data-incident]').forEach(row => row.addEventListener('click', () => openIncident(row.dataset.incident)));
}
function bindDynamic() {
  document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => navigate(button.dataset.view)));
  bindIncidentRows();
}
function navigate(view) {
  if (view === 'overview') loadOverview();
  else if (view === 'incidents') loadIncidents();
  else if (view === 'new') renderNew();
  else if (view === 'analytics') renderAnalytics();
  else if (view === 'team') renderTeam();
  else if (view === 'help') renderHelp();
  else if (view === 'settings') renderSettings();
}

navItems.forEach(item => item.addEventListener('click', () => navigate(item.dataset.view)));
document.getElementById('mobile-menu').addEventListener('click', () => sidebar.classList.toggle('open'));
document.getElementById('theme-toggle').addEventListener('click', () => {
  const next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
  document.documentElement.dataset.theme = next; localStorage.setItem('aii-theme', next);
});
document.documentElement.dataset.theme = localStorage.getItem('aii-theme') || 'dark';
globalSearch.addEventListener('keydown', event => { if (event.key === 'Enter') loadIncidents(globalSearch.value.trim()); });
document.addEventListener('keydown', event => { if (event.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') { event.preventDefault(); globalSearch.focus(); } });

const route = window.location.hash.slice(1);
if (route.startsWith('incident/')) openIncident(route.split('/')[1]);
else bootstrap();

async function renderHelp(){setActive('help');root.innerHTML=`${pageHeader('Product guidance','Help center','Learn the incident workflow and what every important action does.')}<div class="grid-2"><section class="panel"><div class="panel-header"><h2>1. Initial AI analysis</h2><span class="badge success">Fast assessment</span></div><div class="panel-body"><p>Upload a log and optionally describe the observed problem. The description is contextual information; the log remains the primary evidence.</p><ol><li>Validates file type, size and binary content</li><li>Stores the log and calculates SHA-256</li><li>Combines log evidence with the optional description</li><li>Returns severity, category, probable cause and actions</li></ol><p class="form-help"><strong>Start AI Investigation</strong> runs one configured AI agent and is best for a quick first assessment.</p></div></section><section class="panel"><div class="panel-header"><h2>2. Multi-agent investigation</h2><span class="badge medium">Deep analysis</span></div><div class="panel-body"><p>Use this for critical incidents, uncertain root causes, multiple affected systems or a formal postmortem.</p><ul><li><strong>Classifier:</strong> determines primary and secondary categories.</li><li><strong>Root Cause Investigator:</strong> maps evidence and the failure chain.</li><li><strong>Fix Generator:</strong> separates mitigation, prevention, risk and verification.</li><li><strong>Documentation Agent:</strong> creates the incident report.</li><li><strong>Orchestrator:</strong> combines and checks specialist outputs.</li></ul></div></section></div><section class="panel"><div class="panel-header"><h2>Button reference</h2></div><div class="panel-body settings-grid"><div class="setting-row"><span>Run multi-agent investigation</span><strong>Starts all specialist agents</strong></div><div class="setting-row"><span>Load verified log</span><strong>Reads storage and validates checksum</strong></div><div class="setting-row"><span>Copy Markdown</span><strong>Copies a reusable postmortem</strong></div><div class="setting-row"><span>Mark resolved</span><strong>Closes work but preserves history</strong></div></div></section>`}
async function renderTeam(){setActive('team');root.innerHTML=`${pageHeader('Workspace collaboration','Team','Members share incident history, while actions remain attributed to the user who performed them.')}<div class="skeleton" style="height:240px"></div>`;try{const members=await api('/api/v1/auth/team');const canManage=['owner','admin'].includes(state.currentUser.role);root.innerHTML=`${pageHeader('Workspace collaboration','Team','Members share incident history, while actions remain attributed to the user who performed them.',canManage?'<button class="primary" id="add-member">＋ Add member</button>':'')}<section class="panel"><div class="panel-header"><h2>${esc(state.currentUser.organization_name)}</h2><span class="badge neutral">${members.length} members</span></div><div class="panel-body"><table><thead><tr><th>Member</th><th>Email</th><th>Role</th><th>Joined</th></tr></thead><tbody>${members.map(m=>`<tr><td><div class="cell-title">${esc(m.full_name)}</div></td><td>${esc(m.email)}</td><td><span class="badge neutral">${esc(titleCase(m.role))}</span></td><td>${esc(dateTime(m.joined_at))}</td></tr>`).join('')}</tbody></table></div></section>`;document.getElementById('add-member')?.addEventListener('click',showAddMember)}catch(e){toast(e.message,'error')}}
function showAddMember(){const modal=document.getElementById('modal'),backdrop=document.getElementById('modal-backdrop');modal.innerHTML=`<h2>Add workspace member</h2><p class="page-subtitle">Create a team account with a temporary password. Share it through a secure channel.</p><form id="member-form" class="auth-form"><label>Full name<input class="input" name="full_name" required></label><label>Email<input class="input" name="email" type="email" required></label><label>Temporary password<input class="input" name="temporary_password" type="password" minlength="10" required></label><label>Role<select class="select" name="role"><option value="investigator">Investigator</option><option value="viewer">Viewer</option><option value="admin">Admin</option></select></label><div class="actions"><button type="button" class="secondary" id="member-cancel">Cancel</button><button class="primary">Create member</button></div></form>`;backdrop.classList.remove('hidden');document.getElementById('member-cancel').onclick=()=>backdrop.classList.add('hidden');document.getElementById('member-form').onsubmit=async e=>{e.preventDefault();const body=Object.fromEntries(new FormData(e.target));try{await api('/api/v1/auth/team',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});backdrop.classList.add('hidden');toast('Team member created.','success');renderTeam()}catch(err){toast(err.message,'error')}}}
async function renderProfile(){setActive('profile');root.innerHTML=`${pageHeader('Personal workspace identity','My profile','Your account, organization membership and session controls.','<button class="secondary" id="sign-out">Sign out</button>')}<div class="settings-grid"><section class="panel"><div class="panel-header"><h2>${esc(state.currentUser.full_name)}</h2><span class="badge neutral">${esc(titleCase(state.currentUser.role))}</span></div><div class="panel-body"><div class="setting-row"><span>Email</span><strong>${esc(state.currentUser.email)}</strong></div><div class="setting-row"><span>Organization</span><strong>${esc(state.currentUser.organization_name)}</strong></div><div class="setting-row"><span>Member since</span><strong>${esc(dateTime(state.currentUser.created_at))}</strong></div><div class="setting-row"><span>Onboarding</span><strong>${state.currentUser.onboarding_completed?'Completed':'In progress'}</strong></div></div></section><section class="panel"><div class="panel-header"><h2>Security</h2></div><div class="panel-body"><p class="page-subtitle">Authentication uses an HTTP-only signed session cookie, SameSite protection and CSRF tokens for state-changing browser requests.</p></div></section></div>`;document.getElementById('sign-out').onclick=async()=>{await api('/api/v1/auth/logout',{method:'POST'});location.href='/login'}}
async function bootstrap(){
  try{
    state.currentUser=await api('/api/v1/auth/me');
    state.csrfToken=(await api('/api/v1/auth/csrf')).csrf_token;
    const avatar=document.getElementById('user-menu');
    avatar.textContent=state.currentUser.full_name.split(/\s+/).map(x=>x[0]).join('').slice(0,2).toUpperCase();
    avatar.title=`${state.currentUser.full_name} · ${titleCase(state.currentUser.role)}`;
    avatar.onclick=()=>renderProfile();
    if(!state.currentUser.onboarding_completed){showOnboarding();}
    const initial=['overview','incidents','new','analytics','team','help','settings'].includes(route)?route:'overview';
    navigate(initial);
  }catch(e){if(!location.pathname.includes('/login'))location.href='/login'}
}
function showOnboarding(){
 const modal=document.getElementById('modal'),backdrop=document.getElementById('modal-backdrop');
 modal.innerHTML=`<p class="eyebrow">Welcome to ${esc(state.currentUser.organization_name)}</p><h2>Your incident workflow</h2><div class="action-list"><div class="action-card"><strong>1. Create an incident</strong><p>Upload a log and describe the observed symptoms.</p></div><div class="action-card"><strong>2. Review initial analysis</strong><p>Check severity, evidence, confidence and recommended actions.</p></div><div class="action-card"><strong>3. Run multiple agents</strong><p>Use specialist agents for root cause, fixes and a formal report.</p></div><div class="action-card"><strong>4. Collaborate</strong><p>Shared incidents retain the creator, assignee and audit history.</p></div></div><div class="actions"><button class="secondary" id="onboarding-help">Open Help</button><button class="primary" id="onboarding-done">Start investigating</button></div>`;
 backdrop.classList.remove('hidden');
 document.getElementById('onboarding-help').onclick=()=>{backdrop.classList.add('hidden');renderHelp()};
 document.getElementById('onboarding-done').onclick=async()=>{await api('/api/v1/auth/onboarding/complete',{method:'POST'});state.currentUser.onboarding_completed=true;backdrop.classList.add('hidden')};
}
