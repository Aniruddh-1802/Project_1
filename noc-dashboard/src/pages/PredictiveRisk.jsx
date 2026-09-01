/**
 * Predictive Risk View (RE5)
 * ─────────────────────────────────────────────────────────────────────────
 * Submits feature values to POST /network/predict-risk and displays:
 *   - Model output (risk_score, risk_level, model_version) — visually distinct
 *   - Placeholder "Explain with AI" section (future C1/C2 integration)
 *
 * The two regions are deliberately separated so the user can tell at a
 * glance which number came from the model and which words came from an LLM.
 */
import { useState } from 'react';
import { useApi } from '../api/useApi.js';
import { fetchGridFeatures, postPredictRisk } from '../api/client.js';
import {
  Loading, ErrorBanner, SectionHead, SeverityBadge, Spinner,
} from '../components/UI.jsx';
import styles from './PredictiveRisk.module.css';

const DEFAULT_FEATURES = {
  avg_activity:     '',
  activity_growth:  '',
  active_hours:     '',
  peak_ratio:       '',
  variability:      '',
  internet_share:   '',
};

function RiskGauge({ score }) {
  const pct  = Math.min(100, Math.max(0, (score || 0) * 100));
  const color = pct > 66 ? 'var(--danger)' : pct > 33 ? 'var(--warn)' : 'var(--ok)';
  return (
    <div className={styles.gaugeWrap}>
      <div className={styles.gaugeTrack}>
        <div
          className={styles.gaugeFill}
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className={styles.gaugeLabel} style={{ color }}>
        {(score * 100).toFixed(1)}%
      </span>
    </div>
  );
}

export default function PredictiveRisk() {
  const [gridId,   setGridId]   = useState('');
  const [features, setFeatures] = useState(DEFAULT_FEATURES);
  const [result,   setResult]   = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [autoloaded, setAutoloaded] = useState(false);

  // Auto-load features for a grid
  const { loading: featLoad, error: featErr, refetch: loadFeatures } = useApi(
    () => fetchGridFeatures(gridId).then(d => {
      const f = {
        avg_activity:    d.avg_activity    ?? '',
        activity_growth: d.activity_growth ?? '',
        active_hours:    d.active_hours    ?? '',
        peak_ratio:      d.peak_ratio      ?? '',
        variability:     d.variability     ?? '',
        internet_share:  d.internet_share  ?? '',
      };
      setFeatures(f);
      setAutoloaded(true);
    }),
    [gridId],
    true // skip on mount — only run when user clicks Load
  );

  const handleLoadFeatures = () => {
    if (!gridId || isNaN(Number(gridId))) return;
    setAutoloaded(false);
    loadFeatures();
  };

  const handleChange = e => {
    setFeatures(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async e => {
    e.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    setResult(null);
    try {
      const payload = Object.fromEntries(
        Object.entries(features).map(([k, v]) => [k, Number(v)])
      );
      const res = await postPredictRisk(payload);
      setResult(res);
    } catch (err) {
  setSubmitError(
    err.message || "Prediction failed."
  );
}
    finally {
      setSubmitting(false);
    }
  };

  const FEATURE_LABELS = {
    avg_activity:    'Avg Activity',
    activity_growth: 'Activity Growth',
    active_hours:    'Active Hours',
    peak_ratio:      'Peak Ratio',
    variability:     'Variability',
    internet_share:  'Internet Share',
  };

  return (
    <div>
      <SectionHead
        title="Predictive Risk"
        subtitle="Submit feature values to the risk model — output is an attention signal, not a confirmed fault"
      />

      <div className={styles.layout}>
        {/* ── Input panel ─────────────────────────────────────── */}
        <div className={styles.inputPanel}>
          <div className={styles.autoLoad}>
            <span className={styles.panelLabel}>Auto-load from grid</span>
            <div className={styles.autoLoadRow}>
              <input
                type="number"
                min="1" max="10000"
                placeholder="Grid ID"
                value={gridId}
                onChange={e => setGridId(e.target.value)}
                className={styles.gridInput}
              />
              <button
                type="button"
                onClick={handleLoadFeatures}
                disabled={featLoad || !gridId}
                className={styles.loadBtn}
              >
                {featLoad ? <Spinner size={14} /> : 'Load Features'}
              </button>
            </div>
            {featErr  && <p className={styles.smallError}>{featErr}</p>}
            {autoloaded && <p className={styles.smallOk}>Features loaded for grid {gridId}.</p>}
          </div>

          <form onSubmit={handleSubmit} className={styles.form}>
            <span className={styles.panelLabel}>Feature values (ML2 schema)</span>
            {Object.entries(FEATURE_LABELS).map(([key, label]) => (
              <label key={key} className={styles.fieldRow}>
                <span className={styles.fieldLabel}>{label}</span>
                <input
                  type="number"
                  step="any"
                  name={key}
                  value={features[key]}
                  onChange={handleChange}
                  required
                  placeholder="0.0"
                  className={styles.fieldInput}
                />
              </label>
            ))}

            <button
              type="submit"
              disabled={submitting}
              className={styles.predictBtn}
            >
              {submitting ? <><Spinner size={14} /> Running…</> : 'Predict Risk'}
            </button>
          </form>

          {submitError && <ErrorBanner message={submitError} />}
        </div>

        {/* ── Output panel ─────────────────────────────────────── */}
        <div className={styles.outputPanel}>
          <div className={styles.modelOutput}>
            <span className={styles.panelLabel}>Model output</span>
            {!result && !submitting && (
              <p className={styles.emptyOut}>
                Submit feature values to see the risk assessment.
              </p>
            )}
            {submitting && <Loading message="Running model…" />}
            {result && (
              <div className={styles.resultCard}>
                <div className={styles.resultRow}>
                  <span className={styles.resultKey}>Risk Level</span>
                  <SeverityBadge level={result.risk_level} />
                </div>
                <div className={styles.resultRow}>
                  <span className={styles.resultKey}>Risk Score</span>
                  {result.risk_score != null
                    ? <RiskGauge score={result.risk_score} />
                    : <span className={styles.resultVal}>—</span>
                  }
                </div>
                <div className={styles.resultRow}>
                  <span className={styles.resultKey}>Model Version</span>
                  <span className={styles.resultVal}>{result.model_version ?? '—'}</span>
                </div>
                {result.explanation_note && (
                  <div className={styles.explanationNote}>
                    {result.explanation_note}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Deliberately separate region for future LLM explanation */}
          <div className={styles.aiSection}>
            <span className={styles.panelLabel}>AI Explanation</span>
            <div className={styles.aiPlaceholder}>
              <div className={styles.aiPlaceholderIcon}>🔭</div>
              <p className={styles.aiPlaceholderText}>
                "Explain with AI" will be wired here in Phase 7
                (Claude Network Operations Assistant).
              </p>
              <p className={styles.aiPlaceholderSub}>
                The model output above and the AI narrative will remain
                visually separate so you can tell at a glance which number
                came from the model and which words came from an LLM.
              </p>
              <button className={styles.aiBtn} disabled>
                Explain with AI (coming in C1)
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
