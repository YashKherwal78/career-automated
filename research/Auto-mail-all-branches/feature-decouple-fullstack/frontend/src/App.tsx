import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import LandingPage from './pages/LandingPage';
import Dashboard from './pages/Dashboard';
import { isLoggedIn, exchangeCodeForTokens } from './lib/auth';

function AuthCallback() {
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    if (code) {
      exchangeCodeForTokens(code)
        .then(() => setDone(true))
        .catch((err) => setError(err.message));
    } else {
      setError('No auth code found');
    }
  }, []);

  if (done) return <Navigate to="/dashboard" replace />;
  if (error) return (
    <div className="min-h-screen bg-geo-obsidian flex items-center justify-center">
      <div className="text-center">
        <p className="font-mono text-geo-ember mb-4">Auth failed: {error}</p>
        <a href="/" className="geo-btn-outline">Back to Home</a>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-geo-obsidian flex items-center justify-center">
      <div className="text-center animate-fade-in">
        <div className="w-12 h-12 mx-auto mb-4">
          <svg viewBox="0 0 32 32" className="w-full h-full animate-hex-rotate" style={{ animationDuration: '2s' }}>
            <polygon points="16,2 28,10 28,22 16,30 4,22 4,10" fill="none" stroke="#14b8a6" strokeWidth="1.5"/>
          </svg>
        </div>
        <p className="font-mono text-sm text-geo-muted">Authenticating...</p>
      </div>
    </div>
  );
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  return isLoggedIn() ? <>{children}</> : <Navigate to="/" replace />;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={isLoggedIn() ? <Navigate to="/dashboard" replace /> : <LandingPage />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
