/**
 * Hotspots & Alerts page (RE4)
 * ─────────────────────────────────────────────────────────────────────────
 * - Fetches /network/hotspots and /network/alerts
 * - Loads milano-grid.geojson ONCE from public/reference/
 * - Renders map with only the returned grids (performance constraint)
 * - Join uses properties.cellId, NOT the top-level 0-based id
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApi } from '../api/useApi.js';
import { fetchHotspots, fetchAlerts } from '../api/client.js';
import {
  Loading, ErrorBanner, SectionHead, SeverityBadge, DataTable,
} from '../components/UI.jsx';
import MilanMap from '../components/MilanMap.jsx';
import styles from './Hotspots.module.css';

const LIMITS   = [10, 20, 50];
const SEVERITIES = ['', 'HIGH', 'ATTENTION', 'NORMAL'];

function fmt(n) {
  if (n == null) return '—';
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + 'M';
  if (n >= 1_000)     return (n / 1_000).toFixed(1) + 'K';
  return Number(n).toFixed(1);
}

export default function Hotspots() {
  const navigate = useNavigate();

  const [limit,    setLimit]    = useState(20);
  const [severity, setSeverity] = useState('');
  const [selectedGrid, setSelectedGrid] = useState(null);

  // GeoJSON loaded once, held in state
  const [geojson, setGeojson] = useState(null);
  const [geoError, setGeoError] = useState(null);
  const geojsonLoaded = useRef(false);

  useEffect(() => {
    if (geojsonLoaded.current) return;
    geojsonLoaded.current = true;
    fetch('/reference/milano-grid.geojson')
      .then(r => {
        if (!r.ok) throw new Error(`GeoJSON fetch failed: ${r.status}`);
        return r.json();
      })
      .then(setGeojson)
      .catch(e => setGeoError(e.message));
  }, []);

  const params = { limit, severity: severity || undefined };

  const {
    data: hotspots, loading: hLoad, error: hErr, refetch: hRefetch,
  } = useApi(() => fetchHotspots(params), [limit, severity]);

  const {
    data: alerts, loading: aLoad, error: aErr, refetch: aRefetch,
  } = useApi(() => fetchAlerts(params), [limit, severity]);

  const loading = hLoad || aLoad;
  const error   = hErr || aErr;

  const hotspotList = Array.isArray(hotspots) ? hotspots : hotspots?.hotspots ?? [];
  const alertList   = Array.isArray(alerts)   ? alerts   : alerts?.alerts     ?? [];

  const handleGridClick = useCallback(id => {
    setSelectedGrid(id);
  }, []);

  const goToGrid = id => navigate(`/grid/${id}`);

  const hotspotCols = [
    { key: 'grid_id',       label: 'Grid',    render: (v, row) => (
      <button className={styles.gridLink} onClick={() => goToGrid(v)}>{v}</button>
    )},
    { key: 'total_activity',label: 'Activity', align: 'right', render: fmt },
    { key: 'status',        label: 'Status',   render: (v, row) => (
      <SeverityBadge level={v || row.severity || 'ATTENTION'} />
    )},
    { key: 'timestamp',     label: 'Hour',     render: v => v?.slice(0, 16).replace('T', ' ') },
  ];

  const alertCols = [
    { key: 'grid_id',           label: 'Grid',    render: (v) => (
      <button className={styles.gridLink} onClick={() => goToGrid(v)}>{v}</button>
    )},
    { key: 'alert_type',        label: 'Type'    },
    { key: 'current_activity',  label: 'Current', align: 'right', render: fmt },
    { key: 'baseline_activity', label: 'Baseline',align: 'right', render: fmt },
    { key: 'reason',            label: 'Reason',  render: v => (
      <span className={styles.reason}>{v}</span>
    )},
  ];

  return (
    <div>
      <SectionHead
        title="Hotspots & Alerts"
        subtitle="High-activity grids and rule-based operational alerts — activity indicators only, not congestion"
      />

      <div className={styles.controls}>
        <label className={styles.controlLabel}>
          Limit
          <select value={limit} onChange={e => setLimit(Number(e.target.value))}>
            {LIMITS.map(l => <option key={l} value={l}>{l}</option>)}
          </select>
        </label>
        <label className={styles.controlLabel}>
          Severity
          <select value={severity} onChange={e => setSeverity(e.target.value)}>
            {SEVERITIES.map(s => (
              <option key={s} value={s}>{s || 'All'}</option>
            ))}
          </select>
        </label>
        {selectedGrid && (
          <span className={styles.selectedInfo}>
            Selected: Grid {selectedGrid}
            <button className={styles.clearBtn} onClick={() => setSelectedGrid(null)}>✕</button>
            <button className={styles.exploreBtn} onClick={() => goToGrid(selectedGrid)}>
              Open in Grid Explorer →
            </button>
          </span>
        )}
      </div>

      {loading && <Loading message="Loading hotspots…" />}
      {error   && <ErrorBanner message={error} onRetry={() => { hRefetch(); aRefetch(); }} />}
      {geoError && (
        <ErrorBanner message={`Map unavailable: ${geoError}. Place milano-grid.geojson in public/reference/.`} />
      )}

      {/* Map */}
      <div className={styles.mapSection}>
        <MilanMap
          geojson={geojson}
          hotspots={hotspotList}
          alerts={alertList}
          selectedGridId={selectedGrid}
          onGridClick={handleGridClick}
        />
        {!geojson && !geoError && (
          <p className={styles.geoNote}>
            Map loading… if it stays blank, add <code>milano-grid.geojson</code> to{' '}
            <code>public/reference/</code> in this project.
          </p>
        )}
      </div>

      {/* Hotspot table */}
      {!loading && !error && (
        <div className={styles.tableSection}>
          <h3 className={styles.tableTitle}>
            Top Hotspot Grids
            <span className={styles.tableCount}>{hotspotList.length} grids</span>
          </h3>
          <DataTable
            columns={hotspotCols}
            rows={hotspotList}
            onRowClick={row => setSelectedGrid(row.grid_id)}
            emptyMessage="No hotspots in current window."
          />
        </div>
      )}

      {/* Alert table */}
      {!loading && !error && (
        <div className={styles.tableSection}>
          <h3 className={styles.tableTitle}>
            Active Alerts
            <span className={styles.tableCount}>{alertList.length} alerts</span>
          </h3>
          <DataTable
            columns={alertCols}
            rows={alertList}
            emptyMessage="No active alerts."
          />
        </div>
      )}
    </div>
  );
}
