/**
 * MAGNATRIX.IO — Super AI Control Plane
 * Frontend Application — Vanilla JS SPA
 */

(function() {
  'use strict';

  // ═══════════════════════════════════════════════════════════════════════
  // CONFIG
  // ═══════════════════════════════════════════════════════════════════════
  const CONFIG = {
    API_BASE: (() => {
      const host = window.location.hostname === 'localhost' ? 'http://localhost:8080' : '';
      return host || window.location.origin;
    })(),
    WS_URL: (() => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${protocol}//${window.location.host}/ws`;
    })(),
    REFRESH_INTERVAL: 5000,
    BOOT_DURATION: 2000,
  };

  // ═══════════════════════════════════════════════════════════════════════
  // STATE
  // ═══════════════════════════════════════════════════════════════════════
  const State = {
    authenticated: false,
    currentPage: 'dashboard',
    wsConnected: false,
    agents: [],
    skills: [],
    logsPaused: false,
    logsFilter: 'all',
    uptime: 0,
    metrics: {},
  };

  // ═══════════════════════════════════════════════════════════════════════
  // DOM REFS
  // ═══════════════════════════════════════════════════════════════════════
  const $ = id => document.getElementById(id);
  const $$ = sel => document.querySelectorAll(sel);

  // ═══════════════════════════════════════════════════════════════════════
  // API CLIENT
  // ═══════════════════════════════════════════════════════════════════════
  const API = {
    async request(method, path, body = null) {
      const url = `${CONFIG.API_BASE}${path}`;
      const opts = { method, headers: { 'Content-Type': 'application/json' } };
      if (body) opts.body = JSON.stringify(body);
      try {
        const res = await fetch(url, opts);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
      } catch (e) {
        console.error('[API]', e);
        return { error: e.message };
      }
    },
    get(path) { return this.request('GET', path); },
    post(path, body) { return this.request('POST', path, body); },
    health() { return this.get('/health'); },
    status() { return this.get('/status'); },
    agents() { return this.get('/api/v1/agents'); },
    createAgent(role, superior, task) { return this.post('/api/v1/agents', { role, superior_id: superior, task }); },
    skills() { return this.get('/api/v1/skills'); },
    invokeSkill(name, params) { return this.post('/api/v1/skills/invoke', { skill_name: name, parameters: params }); },
    tradingStatus() { return this.get('/api/v1/trading/status'); },
    knowledgeQuery(query, topK) { return this.post('/api/v1/knowledge/query', { query, top_k: topK }); },
    browserAction(url, action) { return this.post('/api/v1/browser', { url, action }); },
    meshNodes() { return this.get('/api/v1/mesh/nodes'); },
  };

  // ═══════════════════════════════════════════════════════════════════════
  // WEBSOCKET
  // ═══════════════════════════════════════════════════════════════════════
  let ws = null;
  const WS = {
    connect() {
      try {
        ws = new WebSocket(CONFIG.WS_URL);
        ws.onopen = () => {
          State.wsConnected = true;
          updateWSIndicator();
          ws.send(JSON.stringify({ type: 'subscribe', channels: ['system', 'agents', 'trading', 'logs'] }));
        };
        ws.onmessage = (ev) => {
          try {
            const msg = JSON.parse(ev.data);
            handleWSMessage(msg);
          } catch (e) {}
        };
        ws.onclose = () => {
          State.wsConnected = false;
          updateWSIndicator();
          setTimeout(() => WS.connect(), 3000);
        };
        ws.onerror = () => {
          State.wsConnected = false;
          updateWSIndicator();
        };
      } catch (e) {
        console.warn('[WS] Connection failed:', e);
      }
    },
    send(data) {
      if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(data));
    },
  };

  function updateWSIndicator() {
    const el = $('ws-indicator');
    if (!el) return;
    el.classList.toggle('connected', State.wsConnected);
    el.title = State.wsConnected ? 'WebSocket connected' : 'WebSocket disconnected';
    el.style.color = State.wsConnected ? 'var(--success)' : 'var(--text-muted)';
  }

  function handleWSMessage(msg) {
    if (msg.type === 'system_event') {
      addActivity(msg.payload);
    } else if (msg.type === 'agent_update') {
      refreshAgents();
    } else if (msg.type === 'log_line') {
      if (!State.logsPaused) appendLog(msg.payload);
    } else if (msg.type === 'metric_update') {
      State.metrics = { ...State.metrics, ...msg.payload };
      updateMetrics();
    }
  }

  // ═══════════════════════════════════════════════════════════════════════
  // BOOT SEQUENCE
  // ═══════════════════════════════════════════════════════════════════════
  async function bootSequence() {
    const steps = [
      { pct: 15, text: 'Loading kernel modules...' },
      { pct: 30, text: 'Initializing protocol layer...' },
      { pct: 45, text: 'Mounting collective brain...' },
      { pct: 60, text: 'Syncing knowledge graph...' },
      { pct: 75, text: 'Connecting to P2P mesh...' },
      { pct: 90, text: 'Loading control plane UI...' },
      { pct: 100, text: 'MAGNATRIX READY' },
    ];

    for (const step of steps) {
      await sleep(CONFIG.BOOT_DURATION / steps.length);
      $('boot-bar').style.width = step.pct + '%';
      $('boot-status').textContent = step.text;
    }

    await sleep(300);
    $('boot-screen').classList.add('hidden');

    // Check if already authenticated (session)
    if (sessionStorage.getItem('magnatrix_auth')) {
      State.authenticated = true;
      showDashboard();
    } else {
      $('auth-gate').classList.remove('hidden');
    }
  }

  // ═══════════════════════════════════════════════════════════════════════
  // AUTH
  // ═══════════════════════════════════════════════════════════════════════
  function initAuth() {
    $('auth-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const user = $('auth-user').value.trim();
      const pass = $('auth-pass').value.trim();
      // Simple auth — in production: JWT from identity_manager
      if (user && pass) {
        State.authenticated = true;
        sessionStorage.setItem('magnatrix_auth', JSON.stringify({ user, time: Date.now() }));
        $('auth-gate').classList.add('hidden');
        showDashboard();
      } else {
        Toast.error('Invalid credentials');
      }
    });
  }

  // ═══════════════════════════════════════════════════════════════════════
  // DASHBOARD
  // ═══════════════════════════════════════════════════════════════════════
  function showDashboard() {
    $('dashboard').classList.remove('hidden');
    WS.connect();
    initSidebar();
    initRouter();
    initDashboard();
    initAgents();
    initSkills();
    initTrading();
    initKnowledge();
    initBrowser();
    initSecurity();
    initMesh();
    initLogs();
    initSettings();
    startPolling();
    startUptimeCounter();
    navigate('dashboard');
  }

  function initDashboard() {
    $('btn-refresh-all').addEventListener('click', () => {
      refreshAll();
      Toast.info('System refreshed');
    });
    $('btn-deploy-trigger').addEventListener('click', () => {
      Toast.info('Deploy triggered — check Hostinger');
    });

    // Quick actions
    $$('.qa-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const action = btn.dataset.action;
        handleQuickAction(action);
      });
    });

    // Knowledge mini
    $('knowledge-mini-btn').addEventListener('click', async () => {
      const q = $('knowledge-mini-input').value.trim();
      if (!q) return;
      const res = await API.knowledgeQuery(q, 3);
      $('knowledge-mini-result').textContent = res.results?.[0]?.content || res.error || 'No results';
    });

    // Layer list
    renderLayerList();
  }

  function renderLayerList() {
    const layers = [
      { name: 'Kernel', status: 'ok' },
      { name: 'Protocol', status: 'ok' },
      { name: 'Identity', status: 'ok' },
      { name: 'Runtime', status: 'ok' },
      { name: 'P2P Mesh', status: 'ok' },
      { name: 'Knowledge', status: 'ok' },
      { name: 'Skills', status: 'ok' },
      { name: 'Browser', status: 'ok' },
      { name: 'Trading', status: 'ok' },
      { name: 'Security', status: 'ok' },
      { name: 'Uncensored AI', status: 'ok' },
      { name: 'Governance', status: 'ok' },
      { name: 'IDE', status: 'ok' },
      { name: 'Offensive', status: 'ok' },
      { name: 'Collective Brain', status: 'ok' },
    ];
    const html = layers.map(l => `
      <div class="layer-row">
        <div class="layer-name">
          <span style="color:var(--accent)">◉</span> ${l.name}
        </div>
        <span class="layer-status ${l.status}">● ${l.status}</span>
      </div>
    `).join('');
    $('layer-list').innerHTML = html;
  }

  function handleQuickAction(action) {
    switch (action) {
      case 'agent-create': navigate('agents'); Modal.open('Create Agent', agentCreateForm()); break;
      case 'skill-invoke': navigate('skills'); break;
      case 'repo-hunt': Toast.info('Repo hunt started — check logs'); break;
      case 'snapshot': Toast.success('System snapshot saved'); break;
    }
  }

  // ═══════════════════════════════════════════════════════════════════════
  // SIDEBAR & ROUTER
  // ═══════════════════════════════════════════════════════════════════════
  function initSidebar() {
    $('sidebar-toggle').addEventListener('click', () => {
      $('sidebar').classList.toggle('collapsed');
    });

    $$('.nav-item').forEach(item => {
      item.addEventListener('click', (e) => {
        e.preventDefault();
        const page = item.dataset.page;
        navigate(page);
      });
    });
  }

  function navigate(page) {
    State.currentPage = page;

    // Update sidebar
    $$('.nav-item').forEach(item => {
      item.classList.toggle('active', item.dataset.page === page);
    });

    // Update page title
    const titles = {
      dashboard: 'DASHBOARD', agents: 'AGENT MANAGEMENT', skills: 'SKILL MARKETPLACE',
      trading: 'HFT TRADING', knowledge: 'KNOWLEDGE GRAPH', browser: 'BROWSER AUTOMATION',
      security: 'SECURITY OPS', mesh: 'P2P MESH', logs: 'SYSTEM LOGS', settings: 'SETTINGS',
    };
    $('page-title').textContent = titles[page] || page.toUpperCase();

    // Show/hide pages
    $$('.page').forEach(p => p.classList.add('hidden'));
    const target = $(`page-${page}`);
    if (target) target.classList.remove('hidden');

    // Page-specific init
    if (page === 'agents') refreshAgents();
    if (page === 'skills') refreshSkills();
    if (page === 'trading') refreshTrading();
    if (page === 'mesh') refreshMesh();
  }

  function initRouter() {
    window.addEventListener('hashchange', () => {
      const hash = window.location.hash.replace('#', '') || 'dashboard';
      navigate(hash);
    });
    if (window.location.hash) {
      navigate(window.location.hash.replace('#', ''));
    }
  }

  // ═══════════════════════════════════════════════════════════════════════
  // AGENTS
  // ═══════════════════════════════════════════════════════════════════════
  function initAgents() {
    $('btn-create-agent').addEventListener('click', () => {
      Modal.open('Create Agent', agentCreateForm(), [
        { text: 'Cancel', class: 'btn-ghost', onClick: Modal.close },
        { text: 'Create', class: 'btn-primary', onClick: () => {
          const role = $('new-agent-role').value;
          API.createAgent(role).then(res => {
            Toast.success(`Agent created: ${res.agent_id}`);
            Modal.close();
            refreshAgents();
          });
        }},
      ]);
    });

    $('btn-delegate-task').addEventListener('click', () => {
      Modal.open('Delegate Task', `
        <div class="field"><label>Agent ID</label><input class="input" id="delegate-agent" placeholder="agent-id"></div>
        <div class="field"><label>Task Description</label><textarea class="input" id="delegate-task" rows="3"></textarea></div>
      `, [
        { text: 'Cancel', class: 'btn-ghost', onClick: Modal.close },
        { text: 'Delegate', class: 'btn-primary', onClick: () => {
          Toast.success('Task delegated');
          Modal.close();
        }},
      ]);
    });

    $('console-input').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const cmd = e.target.value.trim();
        if (cmd) {
          appendConsole(`agent> ${cmd}`);
          appendConsole(`[processed] ${cmd}`);
          e.target.value = '';
        }
      }
    });

    $('agent-search').addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase();
      $$('.agent-card').forEach(card => {
        const name = card.querySelector('.agent-name').textContent.toLowerCase();
        card.style.display = name.includes(q) ? '' : 'none';
      });
    });
  }

  function agentCreateForm() {
    return `
      <div class="field"><label>Role</label>
        <select class="input" id="new-agent-role">
          <option value="generalist">Generalist</option>
          <option value="researcher">Researcher</option>
          <option value="trader">Trader</option>
          <option value="security">Security</option>
          <option value="orchestrator">Orchestrator</option>
        </select>
      </div>
      <div class="field"><label>Superior Agent (optional)</label><input class="input" id="new-agent-superior" placeholder="agent-id"></div>
      <div class="field"><label>Initial Task (optional)</label><textarea class="input" id="new-agent-task" rows="2"></textarea></div>
    `;
  }

  async function refreshAgents() {
    const res = await API.agents();
    State.agents = res.agents || [];
    $('badge-agents').textContent = State.agents.length;

    const html = State.agents.map(a => `
      <div class="agent-card">
        <div class="agent-card-header">
          <div class="agent-avatar">${a.id.slice(-2).toUpperCase()}</div>
          <div class="agent-info">
            <div class="agent-name">${a.id}</div>
            <div class="agent-role">${a.role}</div>
          </div>
          <span class="agent-status-badge ${a.status === 'active' ? 'badge-ok' : 'badge-warn'}">${a.status}</span>
        </div>
        <div class="agent-stats">
          <span>Mem: 0</span>
          <span>Tools: 0</span>
          <span>Tasks: 0</span>
        </div>
      </div>
    `).join('');

    const grid = $('agent-grid');
    if (grid) grid.innerHTML = html || '<div style="color:var(--text-muted);padding:32px;text-align:center">No agents</div>';

    // Hierarchy
    $('hierarchy-view').innerHTML = `
      <div style="padding:16px;color:var(--text-muted);font-size:12px">
        <div style="margin-bottom:8px"><span style="color:var(--accent)">◈</span> agent-alpha (orchestrator)</div>
        <div style="padding-left:20px"><span style="color:var(--accent-light)">◆</span> agent-beta (researcher)</div>
      </div>
    `;
  }

  function appendConsole(text) {
    const out = $('console-output');
    if (!out) return;
    const line = document.createElement('div');
    line.textContent = text;
    line.style.marginBottom = '2px';
    out.appendChild(line);
    out.scrollTop = out.scrollHeight;
  }

  // ═══════════════════════════════════════════════════════════════════════
  // SKILLS
  // ═══════════════════════════════════════════════════════════════════════
  function initSkills() {
    $('btn-install-skill').addEventListener('click', () => {
      Modal.open('Install Skill', `
        <div class="field"><label>Skill URL or Name</label><input class="input" id="install-skill-url" placeholder="https://github.com/... or skill-name"></div>
      `, [
        { text: 'Cancel', class: 'btn-ghost', onClick: Modal.close },
        { text: 'Install', class: 'btn-primary', onClick: () => { Toast.success('Skill installed'); Modal.close(); refreshSkills(); }},
      ]);
    });

    $('btn-invoke-skill').addEventListener('click', async () => {
      const name = $('invoke-skill-select').value;
      const params = $('invoke-skill-params').value.trim();
      if (!name) { Toast.error('Select a skill'); return; }
      const res = await API.invokeSkill(name, params ? JSON.parse(params) : {});
      $('invoke-result').textContent = JSON.stringify(res, null, 2);
    });

    $('skill-search').addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase();
      $$('.skill-row').forEach(row => {
        row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
    });
  }

  async function refreshSkills() {
    const res = await API.skills();
    State.skills = res.skills || [];
    $('badge-skills').textContent = State.skills.length;

    const html = State.skills.map(s => `
      <div class="skill-row">
        <div class="skill-icon">⚡</div>
        <div class="skill-info">
          <div class="skill-name">${s.name}</div>
          <div class="skill-desc">${s.category}</div>
        </div>
        <span class="skill-cat">${s.category}</span>
      </div>
    `).join('');

    const list = $('skill-list');
    if (list) list.innerHTML = html || '<div style="color:var(--text-muted);padding:32px;text-align:center">No skills</div>';

    // Populate select
    const select = $('invoke-skill-select');
    if (select) {
      select.innerHTML = '<option value="">Select skill...</option>' +
        State.skills.map(s => `<option value="${s.name}">${s.name}</option>`).join('');
    }
  }

  // ═══════════════════════════════════════════════════════════════════════
  // TRADING
  // ═══════════════════════════════════════════════════════════════════════
  function initTrading() {
    $('btn-start-trading').addEventListener('click', () => Toast.success('Trading engine started'));
    $('btn-stop-trading').addEventListener('click', () => Toast.info('Trading engine stopped'));
    $('btn-paper-toggle').addEventListener('click', function() {
      const isPaper = this.textContent.includes('ON');
      this.textContent = isPaper ? 'Paper Mode: OFF' : 'Paper Mode: ON';
      Toast.info(`Paper mode ${isPaper ? 'disabled' : 'enabled'}`);
    });
  }

  async function refreshTrading() {
    const res = await API.tradingStatus();
    $('trading-portfolio').textContent = `$${(res.balance || 0).toFixed(2)}`;
    $('trading-positions').textContent = (res.positions || []).length;
    $('trading-pnl').textContent = `$${(res.pnl || 0).toFixed(2)}`;
    $('trading-strategies').textContent = res.active_strategies || 0;
  }

  // ═══════════════════════════════════════════════════════════════════════
  // KNOWLEDGE
  // ═══════════════════════════════════════════════════════════════════════
  function initKnowledge() {
    $('btn-knowledge-query').addEventListener('click', async () => {
      const q = $('knowledge-input').value.trim();
      const k = parseInt($('knowledge-topk').value) || 5;
      if (!q) return;
      $('knowledge-result').textContent = 'Querying knowledge graph...';
      const res = await API.knowledgeQuery(q, k);
      const results = res.results || [];
      $('knowledge-result').innerHTML = results.map(r => `
        <div style="margin-bottom:10px;padding:8px;background:var(--bg-primary);border-radius:4px">
          <div style="font-size:11px;color:var(--accent);margin-bottom:4px">Source: ${r.source} | Score: ${r.score}</div>
          <div>${r.content}</div>
        </div>
      `).join('') || 'No results found';
    });
  }

  // ═══════════════════════════════════════════════════════════════════════
  // BROWSER
  // ═══════════════════════════════════════════════════════════════════════
  function initBrowser() {
    $('btn-browser-navigate').addEventListener('click', async () => {
      const url = $('browser-url').value.trim();
      if (!url) return;
      const res = await API.browserAction(url, 'navigate');
      appendBrowserLog(`Navigate: ${url} — ${res.success ? 'OK' : 'FAIL'}`);
    });
    $('btn-browser-screenshot').addEventListener('click', async () => {
      const res = await API.browserAction($('browser-url').value, 'screenshot');
      appendBrowserLog(`Screenshot: ${res.path || 'saved'}`);
    });
    $('btn-browser-extract').addEventListener('click', async () => {
      const res = await API.browserAction($('browser-url').value, 'extract');
      appendBrowserLog(`Extract: ${res.count || 0} elements`);
    });
  }

  function appendBrowserLog(text) {
    const el = $('browser-logs');
    if (!el) return;
    const line = document.createElement('div');
    line.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;
    el.appendChild(line);
    el.scrollTop = el.scrollHeight;
  }

  // ═══════════════════════════════════════════════════════════════════════
  // SECURITY
  // ═══════════════════════════════════════════════════════════════════════
  function initSecurity() {
    // Static for now
  }

  // ═══════════════════════════════════════════════════════════════════════
  // MESH
  // ═══════════════════════════════════════════════════════════════════════
  async function refreshMesh() {
    const res = await API.meshNodes();
    const nodes = res.nodes || [];
    const peers = nodes.filter(n => n.id !== 'node-local');
    $('peer-list').innerHTML = peers.length
      ? peers.map(p => `
        <div class="layer-row">
          <div class="layer-name"><span style="color:var(--accent)">※</span> ${p.id}</div>
          <span class="layer-status ok">${p.status}</span>
        </div>
      `).join('')
      : '<div class="peer-empty">No peers connected</div>';
  }

  // ═══════════════════════════════════════════════════════════════════════
  // LOGS
  // ═══════════════════════════════════════════════════════════════════════
  function initLogs() {
    $('btn-logs-pause').addEventListener('click', function() {
      State.logsPaused = !State.logsPaused;
      this.textContent = State.logsPaused ? '▶ Resume' : '⏸ Pause';
    });
    $('btn-logs-clear').addEventListener('click', () => {
      $('log-stream').innerHTML = '';
    });
    $('logs-level').addEventListener('change', (e) => {
      State.logsFilter = e.target.value;
      filterLogs();
    });

    // Seed some logs
    seedLogs();
  }

  function seedLogs() {
    const lines = [
      { level: 'info', msg: 'MAGNATRIX kernel initialized — 15 layers mounted' },
      { level: 'info', msg: 'Protocol layer: gRPC on :50051, WS on :50052, REST on :50053' },
      { level: 'info', msg: 'Collective Brain: AgentZeroCore, HermesOrchestrator loaded' },
      { level: 'info', msg: 'Knowledge graph: 0 nodes, initializing...' },
      { level: 'warn', msg: 'P2P mesh: no bootstrap nodes configured' },
      { level: 'info', msg: 'Trading engine: paper mode active' },
      { level: 'info', msg: 'Security: AgentShield, RuntimeEnforcer active' },
      { level: 'info', msg: 'Uncensored AI: Hermes-3 model router ready' },
      { level: 'info', msg: 'Refero Design Skill: craft knowledge loaded' },
      { level: 'info', msg: 'Web UI Control Plane listening on :8082' },
    ];
    lines.forEach(l => appendLog(l));
  }

  function appendLog(log) {
    const stream = $('log-stream');
    if (!stream) return;

    const ts = log.timestamp || new Date().toISOString().split('T')[1].split('.')[0];
    const level = log.level || 'info';
    const msg = log.msg || log.message || JSON.stringify(log);

    const line = document.createElement('div');
    line.className = `log-line log-${level}`;
    line.innerHTML = `
      <span class="log-ts">${ts}</span>
      <span class="log-level log-level-${level}">${level}</span>
      <span class="log-msg">${escapeHtml(msg)}</span>
    `;
    stream.appendChild(line);
    stream.scrollTop = stream.scrollHeight;

    // Trim old
    while (stream.children.length > 500) {
      stream.removeChild(stream.firstChild);
    }
  }

  function filterLogs() {
    const f = State.logsFilter;
    $$('.log-line').forEach(line => {
      if (f === 'all') { line.style.display = ''; return; }
      line.style.display = line.classList.contains(`log-${f}`) ? '' : 'none';
    });
  }

  // ═══════════════════════════════════════════════════════════════════════
  // SETTINGS
  // ═══════════════════════════════════════════════════════════════════════
  function initSettings() {
    const layers = [
      'Kernel', 'Protocol', 'Identity', 'Runtime', 'P2P Mesh',
      'Knowledge', 'Skills', 'Browser', 'Trading', 'Security',
      'Uncensored AI', 'Governance', 'IDE', 'Offensive', 'Collective Brain',
    ];
    $('layer-controls').innerHTML = layers.map(l => `
      <div class="layer-toggle">
        <span class="layer-toggle-name">${l}</span>
        <label class="toggle">
          <input type="checkbox" checked disabled><span></span>
        </label>
      </div>
    `).join('');

    $('btn-save-settings').addEventListener('click', () => {
      CONFIG.API_BASE = $('setting-api-url').value;
      CONFIG.WS_URL = $('setting-ws-url').value;
      CONFIG.REFRESH_INTERVAL = parseInt($('setting-refresh').value) || 5000;
      Toast.success('Settings saved');
    });

    $('theme-toggle').addEventListener('click', () => {
      document.body.classList.toggle('light-theme');
    });
  }

  // ═══════════════════════════════════════════════════════════════════════
  // POLLING & METRICS
  // ═══════════════════════════════════════════════════════════════════════
  function startPolling() {
    refreshAll();
    setInterval(() => {
      if (State.currentPage === 'dashboard') refreshMetrics();
      if (State.currentPage === 'trading') refreshTrading();
      if (State.currentPage === 'agents') refreshAgents();
      if (State.currentPage === 'skills') refreshSkills();
    }, CONFIG.REFRESH_INTERVAL);
  }

  async function refreshAll() {
    refreshMetrics();
    refreshAgents();
    refreshSkills();
    refreshTrading();
    refreshMesh();
  }

  async function refreshMetrics() {
    const res = await API.status();
    if (res.error) return;

    const layers = res.layers || {};
    const ok = Object.values(layers).filter(Boolean).length;
    const total = Object.keys(layers).length;
    $('badge-layers-ok').textContent = `${ok}/${total} OK`;

    const resources = res.resources || {};
    $('metric-cpu').textContent = `${resources.cpu_percent?.toFixed(1) || '--'}%`;
    $('metric-cpu-bar').style.width = `${resources.cpu_percent || 0}%`;
    $('metric-mem').textContent = `${resources.memory_used_mb || '--'} / ${resources.memory_total_mb || '--'} MB`;
    $('metric-mem-bar').style.width = `${resources.memory_percent || 0}%`;

    $('metric-agents').textContent = res.agents?.length || State.agents.length || 0;
    $('metric-pnl').textContent = `$${(res.trading?.pnl || 0).toFixed(2)}`;
  }

  function updateMetrics() {
    const m = State.metrics;
    if (m.cpu !== undefined) {
      $('metric-cpu').textContent = `${m.cpu}%`;
      $('metric-cpu-bar').style.width = `${m.cpu}%`;
    }
  }

  function startUptimeCounter() {
    setInterval(() => {
      State.uptime++;
      const h = Math.floor(State.uptime / 3600).toString().padStart(2, '0');
      const m = Math.floor((State.uptime % 3600) / 60).toString().padStart(2, '0');
      const s = (State.uptime % 60).toString().padStart(2, '0');
      const el = $('uptime');
      if (el) el.textContent = `${h}:${m}:${s}`;
    }, 1000);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // ACTIVITY FEED
  // ═══════════════════════════════════════════════════════════════════════
  function addActivity(payload) {
    const feed = $('activity-feed');
    if (!feed) return;
    const empty = feed.querySelector('.activity-empty');
    if (empty) empty.remove();

    const item = document.createElement('div');
    item.className = 'activity-item';
    const time = new Date().toLocaleTimeString();
    item.innerHTML = `
      <span class="activity-time">${time}</span>
      <span class="activity-text">${escapeHtml(payload.message || JSON.stringify(payload))}</span>
    `;
    feed.insertBefore(item, feed.firstChild);
    while (feed.children.length > 50) feed.removeChild(feed.lastChild);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // TOAST
  // ═══════════════════════════════════════════════════════════════════════
  const Toast = {
    container: null,
    init() { this.container = $('toast-container'); },
    show(msg, type = 'info', duration = 3000) {
      if (!this.container) this.init();
      const el = document.createElement('div');
      el.className = `toast toast-${type}`;
      el.innerHTML = `<span>${escapeHtml(msg)}</span>`;
      this.container.appendChild(el);
      setTimeout(() => {
        el.style.opacity = '0';
        el.style.transform = 'translateX(20px)';
        setTimeout(() => el.remove(), 300);
      }, duration);
    },
    info(msg) { this.show(msg, 'info'); },
    success(msg) { this.show(msg, 'success'); },
    error(msg) { this.show(msg, 'error', 5000); },
  };

  // ═══════════════════════════════════════════════════════════════════════
  // MODAL
  // ═══════════════════════════════════════════════════════════════════════
  const Modal = {
    open(title, bodyHtml, buttons = []) {
      $('modal-title').textContent = title;
      $('modal-body').innerHTML = bodyHtml;

      const footer = $('modal-footer');
      footer.innerHTML = '';
      buttons.forEach(b => {
        const btn = document.createElement('button');
        btn.className = b.class || 'btn-ghost';
        btn.textContent = b.text;
        btn.addEventListener('click', b.onClick || Modal.close);
        footer.appendChild(btn);
      });

      $('modal-overlay').classList.remove('hidden');
    },
    close() {
      $('modal-overlay').classList.add('hidden');
    },
  };

  $('modal-overlay').addEventListener('click', (e) => {
    if (e.target === $('modal-overlay')) Modal.close();
  });
  $('modal-close').addEventListener('click', Modal.close);

  // ═══════════════════════════════════════════════════════════════════════
  // UTILS
  // ═══════════════════════════════════════════════════════════════════════
  function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
  }

  // ═══════════════════════════════════════════════════════════════════════
  // INIT
  // ═══════════════════════════════════════════════════════════════════════
  document.addEventListener('DOMContentLoaded', () => {
    bootSequence();
    initAuth();
  });

})();
