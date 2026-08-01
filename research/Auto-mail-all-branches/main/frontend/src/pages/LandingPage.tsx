import { useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ensureValidSession, getGoogleAuthUrl, getUser } from '../lib/auth';
import { PRODUCT_NAME } from '../lib/branding';

/* ── SVG Hexagonal Constellation ───────────────────────────────────── */
function HexConstellation() {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;

    // Generate hexagonal grid points
    const hexPoints: { x: number; y: number }[] = [];
    const size = 50;
    const cols = 14, rows = 8;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const x = c * size * 1.5 + (r % 2 ? size * 0.75 : 0);
        const y = r * size * 0.866;
        hexPoints.push({ x: x - 50, y: y - 50 });
      }
    }

    // Create subtle connecting lines
    const lines = svg.querySelectorAll('.hex-line');
    lines.forEach(l => l.remove());

    for (let i = 0; i < hexPoints.length; i++) {
      for (let j = i + 1; j < hexPoints.length; j++) {
        const dx = hexPoints[j].x - hexPoints[i].x;
        const dy = hexPoints[j].y - hexPoints[i].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < size * 1.8 && Math.random() > 0.4) {
          const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
          line.setAttribute('x1', String(hexPoints[i].x));
          line.setAttribute('y1', String(hexPoints[i].y));
          line.setAttribute('x2', String(hexPoints[j].x));
          line.setAttribute('y2', String(hexPoints[j].y));
          line.setAttribute('stroke', '#14b8a6');
          line.setAttribute('stroke-width', '0.5');
          line.setAttribute('opacity', String(0.05 + Math.random() * 0.12));
          line.classList.add('hex-line');
          svg.appendChild(line);
        }
      }
    }

    // Create dots at hex vertices
    hexPoints.forEach((p) => {
      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('cx', String(p.x));
      circle.setAttribute('cy', String(p.y));
      circle.setAttribute('r', String(1 + Math.random() * 1.5));
      circle.setAttribute('fill', Math.random() > 0.7 ? '#f59e0b' : '#14b8a6');
      circle.setAttribute('opacity', String(0.15 + Math.random() * 0.35));
      circle.classList.add('hex-line');
      svg.appendChild(circle);
    });
  }, []);

  return (
    <svg
      ref={svgRef}
      viewBox="-50 -50 900 500"
      className="absolute inset-0 w-full h-full opacity-60"
      preserveAspectRatio="xMidYMid slice"
    >
      {/* Central hex ring - animated */}
      <g className="animate-hex-rotate" style={{ transformOrigin: '400px 200px' }}>
        <polygon
          points="400,140 452,170 452,230 400,260 348,230 348,170"
          fill="none"
          stroke="#14b8a6"
          strokeWidth="0.8"
          opacity="0.25"
        />
      </g>
      <g className="animate-counter-spin" style={{ transformOrigin: '400px 200px' }}>
        <polygon
          points="400,120 466,160 466,240 400,280 334,240 334,160"
          fill="none"
          stroke="#f59e0b"
          strokeWidth="0.4"
          opacity="0.15"
        />
      </g>
    </svg>
  );
}

/* ── Google icon SVG ───────────────────────────────────────────────── */
function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
  );
}

/* ── Feature Hex Card ──────────────────────────────────────────────── */
function FeatureCard({ icon, title, desc, delay }: { icon: string; title: string; desc: string; delay: string }) {
  return (
    <div
      className={`geo-card-hover p-6 animate-slide-up ${delay} group`}
    >
      <div className="flex items-center gap-4 mb-4">
        <div className="w-12 h-12 flex items-center justify-center text-2xl
                      bg-geo-teal/10 border border-geo-teal/20 rounded-lg
                      group-hover:bg-geo-teal/20 group-hover:border-geo-teal/40 transition-all duration-300">
          {icon}
        </div>
        <h3 className="font-mono text-base font-semibold text-geo-text tracking-wide">{title}</h3>
      </div>
      <p className="text-sm text-geo-muted leading-relaxed">{desc}</p>
    </div>
  );
}

/* ── Metric Crystal ────────────────────────────────────────────────── */
function MetricCrystal({ value, label, delay }: { value: string; label: string; delay: string }) {
  return (
    <div className={`text-center animate-slide-up ${delay}`}>
      <div className="font-mono text-4xl font-bold text-gradient-teal mb-2">{value}</div>
      <div className="font-mono text-xs text-geo-muted uppercase tracking-[0.2em]">{label}</div>
    </div>
  );
}

/* ── Landing Page ──────────────────────────────────────────────────── */
export default function LandingPage() {
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const ok = await ensureValidSession();
      if (cancelled || !ok) return;
      const u = getUser();
      if (!u) return;
      navigate(u.onboarded ? '/dashboard' : '/onboarding', { replace: true });
    })();
    return () => { cancelled = true; };
  }, [navigate]);

  const handleGoogleLogin = () => {
    const url = getGoogleAuthUrl();
    if (!url.includes('client_id=&')) {
      window.location.href = url;
    } else {
      alert('Please set VITE_GOOGLE_CLIENT_ID in your .env file.\nSee the GCP setup guide.');
    }
  };

  return (
    <div className="min-h-screen bg-geo-obsidian overflow-hidden">

      {/* ── Navigation ─────────────────────────────────────────────── */}
      <nav className="fixed top-0 w-full z-50 border-b border-geo-teal/8 backdrop-blur-md bg-geo-obsidian/80">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <div className="w-8 h-8 relative">
              <svg viewBox="0 0 32 32" className="w-full h-full">
                <polygon points="16,2 28,10 28,22 16,30 4,22 4,10" fill="none" stroke="#14b8a6" strokeWidth="1.5"/>
                <polygon points="16,8 22,12 22,20 16,24 10,20 10,12" fill="#14b8a620" stroke="#14b8a6" strokeWidth="0.8"/>
              </svg>
            </div>
            <span className="font-mono text-lg font-semibold tracking-wide text-geo-text">
              {PRODUCT_NAME.split(' ')[0]}<span className="text-geo-teal"> {PRODUCT_NAME.split(' ')[1] || ''}</span>
            </span>
          </Link>
          <button onClick={handleGoogleLogin} className="geo-btn text-xs py-2 px-4">
            Get Started
          </button>
        </div>
      </nav>

      {/* ── Hero ───────────────────────────────────────────────────── */}
      <section className="relative min-h-screen flex items-center justify-center pt-20 bg-hex-grid animate-tessellate">
        <HexConstellation />
        
        <div className="relative z-10 text-center max-w-3xl mx-auto px-6">
          <div className="animate-fade-in mb-6">
            <span className="geo-badge-teal">
              <span className="w-1.5 h-1.5 rounded-full bg-geo-teal animate-pulse-glow" />
              {PRODUCT_NAME}
            </span>
          </div>

          <h1 className="font-mono text-5xl md:text-6xl lg:text-7xl font-bold leading-[1.1] mb-6 animate-slide-up">
            <span className="text-geo-text">Job applications</span>
            <br />
            <span className="text-gradient-teal">with geometric</span>
            <br />
            <span className="text-gradient-amber">precision</span>
          </h1>

          <p className="text-lg text-geo-muted max-w-xl mx-auto mb-10 leading-relaxed animate-slide-up delay-200 font-body">
            Junie reads the posting, researches the company, discovers the right contacts, writes your outreach,
            and sends through your Gmail — one flow, your brand of precision.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center animate-slide-up delay-400">
            <button onClick={handleGoogleLogin} className="geo-btn-google w-64">
              <GoogleIcon />
              <span>Sign in with Google</span>
            </button>
            <a href="#features" className="geo-btn-outline w-64 text-center">
              How it works
            </a>
          </div>

          <p className="text-xs text-geo-dim mt-6 animate-fade-in delay-600">
            Gmail permissions required for sending. Your credentials stay with Google.
          </p>
        </div>

        {/* Bottom fade */}
        <div className="absolute bottom-0 left-0 w-full h-32 bg-gradient-to-t from-geo-obsidian to-transparent" />
      </section>

      {/* ── Features ───────────────────────────────────────────────── */}
      <section id="features" className="py-28 relative">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="font-mono text-3xl font-bold text-geo-text mb-3">
              How <span className="text-gradient-teal">Junie</span> works
            </h2>
            <p className="text-geo-muted text-sm max-w-md mx-auto">
              Four stages. One assistant. Junie orchestrates every step.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <FeatureCard
              icon="🔬"
              title="Understand the role"
              desc="Paste a LinkedIn job URL. Junie extracts the JD, company, recruiter hints, and site context in seconds."
              delay="delay-100"
            />
            <FeatureCard
              icon="🔎"
              title="Discover contacts"
              desc="Junie runs multi-source contact discovery (including Hunter.io and fallbacks) with smart rotation for coverage."
              delay="delay-200"
            />
            <FeatureCard
              icon="✍️"
              title="Draft outreach"
              desc="Junie composes a personalized email from the role, company research, and your background — powered by Groq."
              delay="delay-300"
            />
            <FeatureCard
              icon="📤"
              title="Send from your Gmail"
              desc="Junie sends through your account via OAuth. No app passwords. Your resume PDF goes along automatically."
              delay="delay-400"
            />
          </div>
        </div>
      </section>

      {/* ── Metrics ────────────────────────────────────────────────── */}
      <section className="py-20 border-y border-geo-teal/8">
        <div className="max-w-4xl mx-auto px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <MetricCrystal value="500+" label="Emails Sent" delay="delay-100" />
            <MetricCrystal value="3x" label="Response Rate" delay="delay-200" />
            <MetricCrystal value="4" label="API Integrations" delay="delay-300" />
            <MetricCrystal value="< 30s" label="Per Application" delay="delay-400" />
          </div>
        </div>
      </section>

      {/* ── Final CTA ──────────────────────────────────────────────── */}
      <section className="py-28 relative bg-hex-grid animate-tessellate">
        <div className="max-w-xl mx-auto px-6 text-center">
          <div className="relative">
            {/* Converging lines decoration */}
            <svg viewBox="0 0 400 60" className="w-full mb-8 opacity-30">
              <line x1="0" y1="0" x2="200" y2="60" stroke="#14b8a6" strokeWidth="0.5" />
              <line x1="400" y1="0" x2="200" y2="60" stroke="#14b8a6" strokeWidth="0.5" />
              <line x1="100" y1="0" x2="200" y2="60" stroke="#f59e0b" strokeWidth="0.3" />
              <line x1="300" y1="0" x2="200" y2="60" stroke="#f59e0b" strokeWidth="0.3" />
              <circle cx="200" cy="60" r="3" fill="#14b8a6" opacity="0.6" />
            </svg>
          </div>
          <h2 className="font-mono text-3xl font-bold text-geo-text mb-4">
            Start <span className="text-gradient-teal">applying</span> smarter
          </h2>
          <p className="text-geo-muted mb-8 text-sm">
            Connect your Google account. Run the pipeline. Land interviews.
          </p>
          <button onClick={handleGoogleLogin} className="geo-btn-google w-72 mx-auto">
            <GoogleIcon />
            <span>Sign in with Google</span>
          </button>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────────── */}
      <footer className="py-8 border-t border-geo-teal/5">
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-between text-xs text-geo-dim">
          <span className="font-mono">{PRODUCT_NAME}</span>
          <span>Built with precision.</span>
        </div>
      </footer>
    </div>
  );
}
