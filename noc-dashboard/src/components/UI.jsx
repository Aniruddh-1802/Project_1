import styles from './UI.module.css';

/* ── Loading spinner ───────────────────────────────────────────── */
export function Spinner({ size = 24 }) {
  return (
    <span
      className={styles.spinner}
      style={{ width: size, height: size }}
      aria-label="Loading"
    />
  );
}

/* ── Full-width loading state ──────────────────────────────────── */
export function Loading({ message = 'Loading…' }) {
  return (
    <div className={styles.loadingWrap}>
      <Spinner size={28} />
      <span className={styles.loadingMsg}>{message}</span>
    </div>
  );
}

/* ── Error banner ──────────────────────────────────────────────── */
export function ErrorBanner({ message, onRetry }) {
  return (
    <div className={styles.error} role="alert">
      <span>⚠ {message || 'Could not reach the API.'}</span>
      {onRetry && (
        <button className={styles.retryBtn} onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

/* ── Metric card ───────────────────────────────────────────────── */
export function MetricCard({ label, value, unit, accent }) {
  return (
    <div className={styles.metricCard} style={accent ? { borderTopColor: accent } : {}}>
      <div className={styles.metricLabel}>{label}</div>
      <div className={styles.metricValue}>
        {value ?? '—'}
        {unit && <span className={styles.metricUnit}> {unit}</span>}
      </div>
    </div>
  );
}

/* ── Section heading ───────────────────────────────────────────── */
export function SectionHead({ title, subtitle }) {
  return (
    <div className={styles.sectionHead}>
      <h2 className={styles.sectionTitle}>{title}</h2>
      {subtitle && <p className={styles.sectionSub}>{subtitle}</p>}
    </div>
  );
}

/* ── Severity badge ────────────────────────────────────────────── */
export function SeverityBadge({ level }) {
  const map = {
    HIGH:      styles.badgeHigh,
    ATTENTION: styles.badgeAttention,
    NORMAL:    styles.badgeNormal,
  };
  const cls = map[level?.toUpperCase()] || styles.badgeNormal;
  return <span className={`${styles.badge} ${cls}`}>{level || 'NORMAL'}</span>;
}

/* ── Timestamp chip ────────────────────────────────────────────── */
export function AsOfChip({ value }) {
  if (!value) return null;
  return (
    <span className={styles.asOf} title="Reporting timestamp from the API (not browser clock)">
      as of {value}
    </span>
  );
}

/* ── Simple table ──────────────────────────────────────────────── */
export function DataTable({ columns, rows, onRowClick, emptyMessage = 'No data.' }) {
  if (!rows || rows.length === 0) {
    return <p className={styles.empty}>{emptyMessage}</p>;
  }
  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            {columns.map(col => (
              <th key={col.key} style={col.align ? { textAlign: col.align } : {}}>
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={onRowClick ? styles.clickableRow : ''}
            >
              {columns.map(col => (
                <td key={col.key} style={col.align ? { textAlign: col.align } : {}}>
                  {col.render ? col.render(row[col.key], row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
