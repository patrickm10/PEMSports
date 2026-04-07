import { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { LandingPage } from './components/v2/LandingPage';
import { DashboardV2View } from './views/v2/DashboardV2View';
import { V3Workspace } from './views/v3/V3Workspace';

export default function App() {
  const [showLanding, setShowLanding] = useState(true);

  if (showLanding) {
    return <LandingPage onLaunch={() => setShowLanding(false)} />;
  }

  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Legacy V2 Dashboard Branch */}
          <Route path="/" element={<DashboardV2View />} />
          
          {/* High-Performance V3 Workspace Branch */}
          <Route path="/v3" element={<V3Workspace />} />
          
          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
