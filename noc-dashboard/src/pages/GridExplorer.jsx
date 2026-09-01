import { useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useApi } from '../api/useApi.js';
import { fetchGridActivity } from '../api/client.js';
import {
  Loading, ErrorBanner, SectionHead, AsOfChip, DataTable,
} from '../components/UI.jsx';
import ActivityChart, { SERIES } from '../components/ActivityChart.jsx';
import styles from './GridExplorer.module.css';

function isValidGridId(id) {
  const n = Number(id);
  return Number.isInteger(n) && n >= 1 && n <= 10000;
}

export default function GridExplorer() {
  const { id: routeId } = useParams();
  const navigate = useNavigate();

  const [inputVal, setInputVal] = useState(routeId || '');
  const [gridId, setGridId] = useState(routeId || '');
  const [validationMsg, setValidationMsg] = useState('');
  const [visibleSeries, setVisibleSeries] = useState(SERIES.map(s => s.key));

  const { data, loading, error, refetch } = useApi(
    () => fetchGridActivity(gridId),
    [gridId],
    !gridId
  );

  const handleSubmit = useCallback(e => {
    e.preventDefault();
    const v = inputVal.trim();
    if (!v) { setValidationMsg('Enter a grid ID.'); return; }
    if (!isValidGridId(v)) {
      setValidationMsg('Grid ID must be an integer between 1 and 10 000.');
      return;
    }
    setValidationMsg('');
    setGridId(v);
    navigate(`/grid/${v}`, { replace: true });
  }, [inputVal, navigate]);

  const toggleSeries = key => {
    setVisibleSeries(prev =>
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    );
  };

 const tableColumns = [
  { key: 'timestamp', label: 'Timestamp' },
  { key: 'total_activity', label: 'Total Activity', align: 'right' },
  { key: 'internet_activity', label: 'Internet', align: 'right' },
  { key: 'sms_activity', label: 'SMS Activity', align: 'right' },
  { key: 'call_activity', label: 'Call Activity', align: 'right' },
 ];

  // Normalise response — some APIs return {data: [...]} or just [...]
const rows = data?.activity || [];

  return (
    <div>
      <SectionHead
        title="Grid Explorer"
        subtitle="Select a grid cell (1–10 000) to view its hourly activity trend"
      />

      <form onSubmit={handleSubmit} className={styles.form}>
        <input
          type="number"
          min="1"
          max="10000"
          value={inputVal}
          onChange={e => setInputVal(e.target.value)}
          placeholder="Grid ID, e.g. 4821"
          className={styles.input}
          aria-label="Grid ID"
        />
        <button type="submit" className={styles.submitBtn}>
          Load Grid
        </button>
        {gridId && data?.as_of && <AsOfChip value={data.as_of} />}
      </form>

      {validationMsg && (
        <p className={styles.validationMsg}>{validationMsg}</p>
      )}

      {!gridId && (
        <p className={styles.prompt}>Enter a grid ID above to begin.</p>
      )}

      {gridId && loading && <Loading message={`Loading grid ${gridId}…`} />}

      {gridId && error && (
        <ErrorBanner
          message={
            error.includes('404') || error.includes('422')
              ? `Grid ${gridId} not found — ID must be 1–10 000.`
              : error
          }
          onRetry={refetch}
        />
      )}

      {gridId && !loading && !error && rows.length > 0 && (
        <>
          <div className={styles.chartSection}>
            <div className={styles.chartHeader}>
              <h3 className={styles.chartTitle}>Hourly Activity — Grid {gridId}</h3>
              <div className={styles.seriesToggle}>
                {SERIES.map(s => (
                  <button
                    key={s.key}
                    onClick={() => toggleSeries(s.key)}
                    className={`${styles.toggleBtn} ${
                      visibleSeries.includes(s.key) ? styles.toggleActive : ''
                    }`}
                    style={{ '--dot-color': s.color }}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
            <ActivityChart data={rows} selectedSeries={visibleSeries} />
          </div>

          <div className={styles.tableSection}>
            <h3 className={styles.chartTitle}>Hourly Detail</h3>
            <DataTable columns={tableColumns} rows={rows} emptyMessage="No rows." />
          </div>
        </>
      )}

      {gridId && !loading && !error && rows.length === 0 && (
        <p className={styles.prompt}>No activity data for grid {gridId}.</p>
      )}
    </div>
  );
}
