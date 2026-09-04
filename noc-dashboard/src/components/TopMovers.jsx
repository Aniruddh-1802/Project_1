/**
 * C5 — Top Movers card, placed on the Network Overview page (RE2).
 * ─────────────────────────────────────────────────────────────────────────
 * Reads GET /network/top-movers, which reuses the ML2 activity_growth
 * baseline computed server-side (FastAPI/services.py) — no ranking or
 * growth math happens on the client (RE-phase rule). Each row links to
 * the Grid Explorer (RE3).
 */
import { Link } from 'react-router-dom';
import { useApi } from '../api/useApi.js';
import { fetchTopMovers } from '../api/client.js';
import { Loading, ErrorBanner, DataTable } from './UI.jsx';
import styles from './TopMovers.module.css';

function fmt(n) {
  if (n == null) return '—';
  return Number(n).toFixed(1);
}

export default function TopMovers({ asOf }) {
  const { data, loading, error, refetch } = useApi(
    () => fetchTopMovers({ limit: 10, asOf }),
    [asOf]
  );

  const rows = data?.top_movers ?? [];

  const columns = [
    {
      key: 'grid_id',
      label: 'Grid',
      render: (v) => (
        <Link className={styles.gridLink} to={`/grid/${v}`}>{v}</Link>
      ),
    },
    { key: 'current_activity', label: 'Current', align: 'right', render: fmt },
    { key: 'baseline_activity', label: 'Baseline', align: 'right', render: fmt },
    {
      key: 'growth',
      label: 'Growth',
      align: 'right',
      render: (v) => (v == null ? '—' : `${(v * 100).toFixed(0)}%`),
    },
    { key: 'label', label: 'Note' },
  ];

  return (
    <div className={styles.section}>
      <div className={styles.title}>Sharpest activity increases vs baseline</div>
      <div className={styles.subtitle}>
        Activity values are proportional measures, not counts or MB — attention
        signal, not confirmed congestion.
      </div>

      {loading && <Loading message="Loading top movers…" />}
      {error && <ErrorBanner message={error} onRetry={refetch} />}

      {!loading && !error && (
        <DataTable
          columns={columns}
          rows={rows}
          emptyMessage="No grid feature data available for this window yet."
        />
      )}
    </div>
  );
}
