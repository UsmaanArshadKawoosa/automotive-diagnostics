import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { DiagnosePage } from './pages/DiagnosePage';
import { SessionHistoryPage } from './pages/SessionHistoryPage';
import { SessionDetailPage } from './pages/SessionDetailPage';
import { AnalyticsPage } from './pages/AnalyticsPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/diagnose" element={<DiagnosePage />} />
          <Route path="/sessions" element={<SessionHistoryPage />} />
          <Route path="/sessions/:sessionId" element={<SessionDetailPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
