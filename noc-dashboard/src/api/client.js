const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function apiFetch(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
  const data = await res.json().catch(() => ({}));

  let message = `HTTP ${res.status}`;

  if (Array.isArray(data?.detail)) {
    message = data.detail
      .map(d => `${d.loc.at(-1)}: ${d.msg}`)
      .join(", ");
  } else if (typeof data?.detail === "string") {
    message = data.detail;
  }

  const err = new Error(message);
  err.status = res.status;
  throw err;
}
  return res.json();
}

// ── API1 ──────────────────────────────────────────────────────────────────
export function fetchNetworkSummary(asOf) {
  const params = asOf ? `?as_of=${encodeURIComponent(asOf)}` : '';
  return apiFetch(`/network/summary${params}`);
}

// ── API2 ──────────────────────────────────────────────────────────────────
export function fetchGridActivity(gridId, asOf) {
  const params = asOf ? `?as_of=${encodeURIComponent(asOf)}` : '';
  return apiFetch(`/network/grid/${gridId}${params}`);
}

// ── API3 ──────────────────────────────────────────────────────────────────
export function fetchHotspots({ limit = 20, severity, asOf } = {}) {
  const p = new URLSearchParams();
  if (limit) p.set('limit', limit);
  if (severity) p.set('severity', severity);
  if (asOf) p.set('as_of', asOf);
  return apiFetch(`/network/hotspots?${p}`);
}

export function fetchAlerts({ limit = 20, severity, asOf } = {}) {
  const p = new URLSearchParams();
  if (limit) p.set('limit', limit);
  if (severity) p.set('severity', severity);
  if (asOf) p.set('as_of', asOf);
  return apiFetch(`/network/alerts?${p}`);
}

// ── API4 ──────────────────────────────────────────────────────────────────
export function fetchGridFeatures(gridId) {
  return apiFetch(`/network/grid/${gridId}/features`);
}

// ── API5 ──────────────────────────────────────────────────────────────────
export function postPredictRisk(payload) {
  return apiFetch('/network/predict-risk', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// ── API6 ──────────────────────────────────────────────────────────────────
export function fetchPipelineStatus() {
  return apiFetch('/pipeline/status');
}

export function fetchGridLocation(gridId) {
  return apiFetch(`/network/grid/${gridId}/location`);
}

// ── C5 (additive) ───────────────────────────────────────────────────────
export function fetchTopMovers({ limit = 10, asOf } = {}) {
  const p = new URLSearchParams();
  if (limit) p.set('limit', limit);
  if (asOf) p.set('as_of', asOf);
  return apiFetch(`/network/top-movers?${p}`);
}
