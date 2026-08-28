import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { DiagnosePage } from './pages/DiagnosePage';
import { Dashboard } from './pages/Dashboard';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { SessionHistoryPage } from './pages/SessionHistoryPage';
import { SessionDetailPage } from './pages/SessionDetailPage';
import { VehiclesPage } from './pages/VehiclesPage';
import { SettingsPage } from './pages/SettingsPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<DiagnosePage />} />
          <Route path="/diagnose" element={<DiagnosePage />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/history" element={<SessionHistoryPage />} />
          <Route path="/sessions" element={<SessionHistoryPage />} />
          <Route path="/sessions/:id" element={<SessionDetailPage />} />
          <Route path="/history/:id" element={<SessionDetailPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/vehicles" element={<VehiclesPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
