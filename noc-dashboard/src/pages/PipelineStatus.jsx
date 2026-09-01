/**
 * Pipeline Status page (API6 / DE7 sanction evidence source)
 * ─────────────────────────────────────────────────────────────────────────
 * Reads GET /pipeline/status — the machine-readable record written by the
 * DE7 quality_check task. This is the single source of truth for data
 * trustworthiness; the Claude assistant will call this same endpoint.
 */
import { useApi } from '../api/useApi.js';
import { fetchPipelineStatus } from '../api/client.js';
import {
  Loading, ErrorBanner, SectionHead, AsOfChip, MetricCard,
} from '../components/UI.jsx';
import styles from './PipelineStatus.module.css';

function StatusDot({ ok }) {
  return (
    <span
      className={styles.dot}
      style={{ background: ok ? 'var(--ok)' : 'var(--danger)' }}
      title={ok ? 'Healthy' : 'Unhealthy'}
    />
  );
}

function TaskRow({ name, status }) {
  const ok = (status || '').toLowerCase() === 'success';
  return (
    <tr>
      <td className={styles.taskName}>{name}</td>
      <td>
        <span className={`${styles.taskStatus} ${ok ? styles.taskOk : styles.taskFail}`}>
          {status || '—'}
        </span>
      </td>
    </tr>
  );
}

function fmt(n) {
  if (n == null) return '—';
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + 'M';
  if (n >= 1_000)     return (n / 1_000).toFixed(1) + 'K';
  return String(n);
}

export default function PipelineStatus() {
  const { data, loading, error, refetch } = useApi(
    () => fetchPipelineStatus(),
    [],
    false
  );

  const isHealthy = data?.healthy ?? false;
  const tasks     = data?.task_status ?? data?.tasks ?? {};
  const reasons   = data?.reasons ?? [];

  return (
    <div>
      <div className={styles.header}>
        <SectionHead
          title="Pipeline Status"
          subtitle="Live view of the last Airflow run — the sanctioned evidence source for data trustworthiness"
        />
        <button className={styles.refreshBtn} onClick={refetch} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {loading && <Loading message="Checking pipeline…" />}
      {error   && <ErrorBanner message={error} onRetry={refetch} />}

      {data && (
        <>
          {/* Health banner */}
          <div
            className={`${styles.healthBanner} ${
              isHealthy ? styles.healthOk : styles.healthFail
            }`}
          >
            <StatusDot ok={isHealthy} />
            <span className={styles.healthLabel}>
              {isHealthy ? 'Pipeline Healthy' : 'Pipeline Unhealthy'}
            </span>
            {data.as_of && <AsOfChip value={data.as_of} />}
          </div>

          {/* Reason list */}
          {reasons.length > 0 && (
            <div className={styles.reasons}>
              {reasons.map((r, i) => (
                <div key={i} className={styles.reason}>⚠ {r}</div>
              ))}
            </div>
          )}

          {/* Row counters */}
          <div className={styles.kpiGrid}>
            <MetricCard label="Rows In"       value={fmt(data.rows_in)}        accent="var(--accent)" />
            <MetricCard label="Rows Rejected" value={fmt(data.rows_rejected)}  accent="var(--danger)" />
            <MetricCard label="Nulls Handled" value={fmt(data.nulls_handled)}  accent="var(--warn)"   />
            <MetricCard label="Rows Published"value={fmt(data.rows_published)} accent="var(--ok)"     />
          </div>

          {/* Task table */}
          <div className={styles.taskSection}>
            <h3 className={styles.taskTitle}>Task Status</h3>
            {Object.keys(tasks).length === 0 ? (
              <p className={styles.noTasks}>No task detail available.</p>
            ) : (
              <div className={styles.taskTableWrap}>
                <table className={styles.taskTable}>
                  <thead>
                    <tr>
                      <th>Task</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(tasks).map(([name, status]) => (
                      <TaskRow key={name} name={name} status={status} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Run metadata */}
          <div className={styles.metaGrid}>
            {data.run_id && (
              <div className={styles.metaItem}>
                <span className={styles.metaKey}>Run ID</span>
                <span className={styles.metaVal}>{data.run_id}</span>
              </div>
            )}
            {data.run_timestamp && (
              <div className={styles.metaItem}>
                <span className={styles.metaKey}>Run Timestamp</span>
                <span className={styles.metaVal}>{data.run_timestamp}</span>
              </div>
            )}
            {data.freshness_hours != null && (
              <div className={styles.metaItem}>
                <span className={styles.metaKey}>Data Freshness</span>
                <span className={styles.metaVal}>{data.freshness_hours}h old</span>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
