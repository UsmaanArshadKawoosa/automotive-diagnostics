import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { DiagnosePage } from './pages/DiagnosePage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<DiagnosePage />} />
          <Route path="/diagnose" element={<DiagnosePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
