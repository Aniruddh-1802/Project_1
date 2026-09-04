import { useApi } from '../api/useApi.js';
import { fetchNetworkSummary } from '../api/client.js';
import { Loading, ErrorBanner, MetricCard, SectionHead, AsOfChip } from '../components/UI.jsx';
import TopMovers from '../components/TopMovers.jsx';
import styles from './Overview.module.css';

function fmt(n) {
  if (n == null) return '—';
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + 'M';
  if (n >= 1_000)     return (n / 1_000).toFixed(1) + 'K';
  return String(n);
}

export default function Overview() {
  const { data, loading, error, refetch } = useApi(
    () => fetchNetworkSummary(),
    []
  );

  return (
    <div>
      <div className={styles.header}>
        <SectionHead
          title="Network Overview"
          subtitle="Current reporting window — activity indicators for the Milan grid"
        />
        {data?.as_of && <AsOfChip value={data.as_of} />}
      </div>

      {loading && <Loading message="Fetching network summary…" />}
      {error   && <ErrorBanner message={error} onRetry={refetch} />}

      {data && (
        <>
          <div className={styles.kpiGrid}>
            <MetricCard
              label="Total Activity"
              value={fmt(data.total_activity)}
              accent="var(--accent)"
            />
            <MetricCard
              label="Active Grids"
              value={fmt(data.active_grids)}
              accent="var(--ok)"
            />
            <MetricCard
              label="Peak Hour"
              value={data.peak_hour ?? '—'}
              accent="var(--warn)"
            />
            <MetricCard
              label="Top Grid"
              value={data.top_grid ?? '—'}
              accent="var(--danger)"
            />
          </div>

          <div className={styles.note}>
            Activity values are proportional indicators — not message counts,
            call counts or megabytes. High activity is an operational attention
            signal, not a confirmed fault.
          </div>

          <TopMovers asOf={data.as_of} />
        </>
      )}
    </div>
  );
}
