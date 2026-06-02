import { NavLink, Route, Routes } from 'react-router-dom';
import AthleteProfile from './pages/AthleteProfile';
import BoneStressPeriods from './pages/BoneStressPeriods';
import CoachingQA from './pages/CoachingQA';
import DailyBriefing from './pages/DailyBriefing';
import DateExplorer from './pages/DateExplorer';
import FrontierOutcomes from './pages/FrontierOutcomes';
import IngestionValidation from './pages/IngestionValidation';
import ProjectOverview from './pages/ProjectOverview';
import Coach from './pages/Coach';
import MethodsResults from './pages/MethodsResults';
import EvaluationReproducibility from './pages/EvaluationReproducibility';

const navItems = [
  { path: '/', label: 'Project overview' },
  { path: '/methods-results', label: 'Methods & results' },
  { path: '/evaluation-reproducibility', label: 'Evaluation & reproducibility' },
  { path: '/athlete-profile', label: 'Athlete profile' },
  { path: '/daily-briefing', label: 'Daily briefing' },
  { path: '/date-explorer', label: 'Date explorer' },
  { path: '/bone-stress-periods', label: 'Bone stress periods' },
  { path: '/frontier-outcomes', label: 'Frontier outcomes' },
  { path: '/ingestion-validation', label: 'Ingestion validation' },
  { path: '/coaching-qa', label: 'Coaching QA (static)' },
  { path: '/coach', label: 'Coach (live)' },
];

export default function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="brand-mark">AS</span>
          <div>
            <h1>Athlete State Lab</h1>
            <p>Garmin risk intelligence</p>
          </div>
        </div>
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            end={item.path === '/'}
          >
            <span>{item.label}</span>
          </NavLink>
        ))}
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<ProjectOverview />} />
          <Route path="/methods-results" element={<MethodsResults />} />
          <Route path="/evaluation-reproducibility" element={<EvaluationReproducibility />} />
          <Route path="/athlete-profile" element={<AthleteProfile />} />
          <Route path="/daily-briefing" element={<DailyBriefing />} />
          <Route path="/date-explorer" element={<DateExplorer />} />
          <Route path="/bone-stress-periods" element={<BoneStressPeriods />} />
          <Route path="/frontier-outcomes" element={<FrontierOutcomes />} />
          <Route path="/ingestion-validation" element={<IngestionValidation />} />
          <Route path="/coaching-qa" element={<CoachingQA />} />
          <Route path="/coach" element={<Coach />} />
        </Routes>
      </main>
    </div>
  );
}
