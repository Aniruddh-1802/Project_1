// C5 — Top Movers card, placed on the Network Overview page (RE2) per the
// approved plan (docs/plans/c5_top_movers_plan.md). Each row links to the
// Grid Explorer (RE3). Ranking happens server-side in
// api/routers/top_movers.py — the client only renders (RE-phase rule).
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiGet } from "./api"; // shared fetch helper from RE1 setup

export default function TopMovers({ asOf }) {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    apiGet(`/network/top-movers?limit=10&as_of=${asOf}`)
      .then((d) => setRows(d.top_movers))
      .catch((e) => setError(String(e))); // report the gap, don't render stale data (C2 rule, applied in UI)
  }, [asOf]);

  if (error) return <div className="card error">Top movers unavailable: {error}</div>;
  return (
    <div className="card">
      {/* Attention language only — never "congested" (CLAUDE.md rule 4) */}
      <h3>Sharpest activity increases vs baseline</h3>
      <table>
        <thead><tr><th>Grid</th><th>Current</th><th>Baseline</th><th>Growth</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.grid_id}>
              <td><Link to={`/grid/${r.grid_id}`}>{r.grid_id}</Link></td>
              <td>{r.current_activity.toFixed(1)}</td>
              <td>{r.baseline_activity.toFixed(1)}</td>
              <td>{r.growth.toFixed(2)}×</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="footnote">
        Activity values are proportional measures, not counts or MB.
      </p>
    </div>
  );
}
