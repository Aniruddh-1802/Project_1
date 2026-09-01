import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import Overview from './pages/Overview.jsx';
import GridExplorer from './pages/GridExplorer.jsx';
import Hotspots from './pages/Hotspots.jsx';
import PredictiveRisk from './pages/PredictiveRisk.jsx';
import PipelineStatus from './pages/PipelineStatus.jsx';
import styles from './App.module.css';

const NAV = [
  { to: '/',            label: 'Overview'      },
  { to: '/grid',        label: 'Grid Explorer' },
  { to: '/hotspots',    label: 'Hotspots'      },
  { to: '/predict',     label: 'Risk'          },
  { to: '/pipeline',    label: 'Pipeline'      },
];

export default function App() {
  return (
    <BrowserRouter>
      <div className={styles.shell}>
        <aside className={styles.sidebar}>
          <div className={styles.brand}>
            <span className={styles.brandDot} />
            NOC · Milan
          </div>
          <nav className={styles.nav}>
            {NAV.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `${styles.navLink} ${isActive ? styles.navActive : ''}`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
          <div className={styles.sidebarFooter}>
            Network Intelligence v1
          </div>
        </aside>

        <main className={styles.main}>
          <Routes>
            <Route path="/"         element={<Overview />} />
            <Route path="/grid"     element={<GridExplorer />} />
            <Route path="/grid/:id" element={<GridExplorer />} />
            <Route path="/hotspots" element={<Hotspots />} />
            <Route path="/predict"  element={<PredictiveRisk />} />
            <Route path="/pipeline" element={<PipelineStatus />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
