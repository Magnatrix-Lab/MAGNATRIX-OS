/*
MAGNATRIX-OS Dashboard Live — WebSocket Client
Vanilla JS, auto-reconnect, heartbeat, per-panel updates.
*/

(function() {
  'use strict';

  const WS_URL = 'ws://localhost:8765';
  const RECONNECT_BASE = 1000;
  const RECONNECT_MAX = 30000;

  let ws = null;
  let reconnectTimer = null;
  let reconnectDelay = RECONNECT_BASE;
  let heartbeatTimer = null;
  let statusEl = null;

  function init() {
    statusEl = document.getElementById('ws-status') || createStatusBadge();
    connect();
    // Reconnect when tab becomes visible
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden && (!ws || ws.readyState !== WebSocket.OPEN)) {
        connect();
      }
    });
  }

  function createStatusBadge() {
    const badge = document.createElement('span');
    badge.id = 'ws-status';
    badge.style.cssText = 'position:fixed;top:8px;right:8px;padding:4px 12px;border-radius:12px;font-size:11px;font-weight:600;z-index:9999;transition:all 0.3s;';
    document.body.appendChild(badge);
    return badge;
  }

  function setStatus(state, text) {
    if (!statusEl) return;
    const colors = {
      connecting: { bg: 'rgba(255,171,64,0.2)', fg: '#ffab40', border: 'rgba(255,171,64,0.4)' },
      live: { bg: 'rgba(105,240,174,0.2)', fg: '#69f0ae', border: 'rgba(105,240,174,0.4)' },
      offline: { bg: 'rgba(255,82,82,0.2)', fg: '#ff5252', border: 'rgba(255,82,82,0.4)' },
    };
    const c = colors[state] || colors.offline;
    statusEl.textContent = text;
    statusEl.style.background = c.bg;
    statusEl.style.color = c.fg;
    statusEl.style.border = '1px solid ' + c.border;
  }

  function connect() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
    clearTimeout(reconnectTimer);
    setStatus('connecting', 'Connecting...');

    try {
      ws = new WebSocket(WS_URL);
    } catch (e) {
      scheduleReconnect();
      return;
    }

    ws.onopen = () => {
      reconnectDelay = RECONNECT_BASE;
      setStatus('live', 'Live');
      startHeartbeat();
    };

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        handleMetrics(data);
      } catch (e) {
        console.warn('WS parse error:', e);
      }
    };

    ws.onclose = () => {
      clearInterval(heartbeatTimer);
      setStatus('offline', 'Offline');
      scheduleReconnect();
    };

    ws.onerror = () => {
      ws.close();
    };
  }

  function scheduleReconnect() {
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(() => {
      reconnectDelay = Math.min(reconnectDelay * 2, RECONNECT_MAX);
      connect();
    }, reconnectDelay);
  }

  function startHeartbeat() {
    clearInterval(heartbeatTimer);
    heartbeatTimer = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping', t: Date.now() }));
      }
    }, 30000);
  }

  // ── Per-Panel Update Handlers ─────────────────────────────

  function handleMetrics(data) {
    if (data.system) updateSystemPanel(data.system);
    if (data.llm) updateLLMPanel(data.llm);
    if (data.trading) updateTradingPanel(data.trading);
    if (data.p2p) updateP2PPanel(data.p2p);
    if (data.governance) updateGovernancePanel(data.governance);
    if (data.security) updateSecurityPanel(data.security);
  }

  function updateSystemPanel(d) {
    setText('sys-uptime', d.uptime || '--');
    setText('sys-cpu', d.cpu != null ? d.cpu + '%' : '--');
    setText('sys-memory', d.memory != null ? d.memory + '%' : '--');
    setText('sys-agents', d.agents != null ? d.agents : '--');
  }

  function updateLLMPanel(d) {
    setText('llm-health', d.health || '--');
    setText('llm-tokens', d.tokens != null ? d.tokens.toLocaleString() : '--');
    setText('llm-latency', d.latency != null ? d.latency + 'ms' : '--');
    setText('llm-queue', d.queue != null ? d.queue : '--');
  }

  function updateTradingPanel(d) {
    setText('trade-nav', d.nav != null ? '$' + d.nav.toLocaleString() : '--');
    setText('trade-pnl', d.pnl != null ? (d.pnl >= 0 ? '+' : '') + d.pnl.toFixed(2) + '%' : '--');
    setText('trade-positions', d.positions != null ? d.positions : '--');
    setText('trade-last', d.last_trade || '--');
    const pnlEl = document.getElementById('trade-pnl');
    if (pnlEl && d.pnl != null) {
      pnlEl.style.color = d.pnl >= 0 ? '#69f0ae' : '#ff5252';
    }
  }

  function updateP2PPanel(d) {
    setText('p2p-peers', d.peers != null ? d.peers : '--');
    setText('p2p-bandwidth', d.bandwidth || '--');
    setText('p2p-msg-rate', d.msg_rate != null ? d.msg_rate + '/s' : '--');
  }

  function updateGovernancePanel(d) {
    setText('gov-constitution', d.constitution || '--');
    setText('gov-agents', d.agents != null ? d.agents : '--');
    setText('gov-tasks', d.tasks != null ? d.tasks : '--');
  }

  function updateSecurityPanel(d) {
    setText('sec-threat', d.threat || 'NONE');
    setText('sec-blocked', d.blocked != null ? d.blocked : '0');
    setText('sec-audit', d.audit != null ? d.audit + '%' : '--');
    const threatEl = document.getElementById('sec-threat');
    if (threatEl) {
      threatEl.style.color = d.threat === 'CRITICAL' ? '#ff5252' : d.threat === 'HIGH' ? '#ffab40' : '#69f0ae';
    }
  }

  function setText(id, text) {
    const el = document.getElementById(id);
    if (el && el.textContent !== String(text)) {
      el.textContent = text;
      flash(el);
    }
  }

  function flash(el) {
    el.style.transition = 'none';
    const orig = el.style.background;
    el.style.background = 'rgba(0,229,255,0.15)';
    setTimeout(() => {
      el.style.transition = 'background 0.5s';
      el.style.background = orig || 'transparent';
    }, 100);
  }

  // Start when DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
