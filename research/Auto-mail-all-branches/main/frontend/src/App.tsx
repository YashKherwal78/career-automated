import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect, useRef } from 'react';
import LandingPage from './pages/LandingPage';
import Dashboard from './pages/Dashboard';
import Onboarding from './pages/Onboarding';
import { getUser, isLoggedIn, exchangeCodeForTokens, ensureValidSession } from './lib/auth';

import LimitlessHome from './pages/LimitlessHome';

function AuthCallback() {
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');
  const hasFetched = useRef(false);

  useEffect(() => {
    if (hasFetched.current) return;
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    if (code) {
      hasFetched.current = true;
      exchangeCodeForTokens(code)
        .then(() => setDone(true))
        .catch((err) => setError(err.message));
    } else {
      queueMicrotask(() => setError('No auth code found'));
    }
  }, []);

  if (done) {
    const user = getUser();
    if (user && !user.onboarded) return <Navigate to="/onboarding" replace />;
    return <Navigate to="/dashboard" replace />;
  }
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

/** Refreshes OAuth access token when expired; redirects to sign-in if session is dead. */
function SessionGate({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [ok, setOk] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const valid = await ensureValidSession();
      if (!cancelled) {
        setOk(valid);
        setReady(true);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (!ready) {
    return (
      <div className="min-h-screen bg-geo-obsidian flex items-center justify-center">
        <p className="font-mono text-sm text-geo-muted">Loading session…</p>
      </div>
    );
  }
  if (!ok) return <Navigate to="/junie" replace />;
  return <>{children}</>;
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  return isLoggedIn() ? <SessionGate>{children}</SessionGate> : <Navigate to="/junie" replace />;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LimitlessHome />} />
        <Route path="/junie" element={<LandingPage />} />
        <Route path="/applywithai" element={<Navigate to="/junie" replace />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="/onboarding" element={<ProtectedRoute><Onboarding /></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
