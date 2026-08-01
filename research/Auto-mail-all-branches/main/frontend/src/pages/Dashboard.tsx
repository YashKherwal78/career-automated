import { useState, useRef, useEffect } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { motion, AnimatePresence, type Variants } from 'framer-motion';
import { getUser, logout, updateProfileSettings, refreshAccessToken, persistUser, type UserProfile } from '../lib/auth';
import { PRODUCT_NAME } from '../lib/branding';

const API = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001';

// ── Types ─────────────────────────────────────────────────────────────────
type Step = 'input' | 'processing' | 'results';
type LogEntry = { icon: string; msg: string; ts: number };

type PipelineResponse = {
  job_data?: Record<string, unknown>;
  log?: [string, string][];
  all_contacts?: Record<string, unknown>[];
  best_email?: string;
  detail?: string;
  research_data?: string;
};

function logClass(icon: string): string {
  if (['✅', '📋'].includes(icon)) return 'geo-log-success';
  if (['❌', '🔴'].includes(icon)) return 'geo-log-error';
  if (['⚠️', '⏭️'].includes(icon)) return 'geo-log-warn';
  if (['🔎', '📄', '🌐', '🔄', '🎯', '🏢', '🔍', '📧', '🔗'].includes(icon)) return 'geo-log-info';
  return 'geo-log-dim';
}

// ── Framer Motion Variants ────────────────────────────────────────────────
const pageVariants: Variants = {
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -16 },
};

const pageTransition = { duration: 0.4, ease: 'easeOut' as const };

const cardStagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07 } },
};

const cardItem: Variants = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: { duration: 0.38, ease: 'easeOut' as const } },
};

// ── LinkedIn URL builder ──────────────────────────────────────────────────
function buildLinkedInSearchUrl(name: string, company?: string) {
  const q = [name, company].filter(Boolean).join(' ');
  return `https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(q)}`;
}

// ── Recruiter Avatar ──────────────────────────────────────────────────────
function RecruiterAvatar({ name, size = 'md' }: { name: string; size?: 'sm' | 'md' | 'lg' }) {
  const initials = name.split(' ').slice(0, 2).map(w => w[0]?.toUpperCase() || '').join('');
  const sz = size === 'lg' ? 'w-14 h-14 text-lg' : size === 'md' ? 'w-10 h-10 text-sm' : 'w-7 h-7 text-xs';
  return (
    <div className={`${sz} rounded-full bg-gradient-to-br from-geo-teal/30 to-geo-amber/20 border border-geo-teal/30 flex items-center justify-center font-mono font-bold text-geo-teal shrink-0`}>
      {initials || '?'}
    </div>
  );
}

// ── Primary Recruiter Card ────────────────────────────────────────────────
function RecruiterProfileCard({ contact, companyName }: { contact: Record<string, unknown>; companyName?: string }) {
  const sourceLabels: Record<string, string> = {
    jd_text: 'Junie · from posting',
    hunter: 'Junie · contact discovery',
    hunter_domain: 'Junie · domain discovery',
    getprospect: 'Junie · contact discovery',
    apollo: 'Junie · contact discovery',
    snov: 'Junie · contact discovery',
    mailmeteor: 'Junie · contact discovery',
    salesql: 'Junie · contact discovery',
  };
  const liUrl = buildLinkedInSearchUrl(String(contact.name ?? ''), companyName);
  return (
    <motion.div variants={cardItem} className="geo-card p-5 border-l-2 border-l-geo-teal/60">
      <div className="flex items-start gap-4">
        <RecruiterAvatar name={String(contact.name ?? 'R')} size="lg" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5 flex-wrap">
            <span className="font-mono font-semibold text-geo-text text-sm">{String(contact.name || 'Unknown Recruiter')}</span>
            {contact.source != null && contact.source !== '' && (
              <span className="geo-badge-teal">{sourceLabels[String(contact.source)] || String(contact.source)}</span>
            )}
          </div>
          {contact.position != null && String(contact.position) !== '' && (
            <p className="text-xs text-geo-muted font-mono mb-0.5">
              {String(contact.position)}{contact.department != null && String(contact.department) !== '' ? ` · ${String(contact.department)}` : ''}
            </p>
          )}
          <p className="text-xs font-mono text-geo-teal break-all">{String(contact.email ?? '')}</p>
          {contact.confidence !== undefined && contact.confidence !== null && (
            <div className="flex items-center gap-2 mt-2">
              <div className="flex-1 h-1 rounded-full bg-geo-void overflow-hidden">
                <motion.div
                  className="h-full rounded-full bg-geo-teal"
                  initial={{ width: 0 }}
                  animate={{ width: `${Number(contact.confidence)}%` }}
                  transition={{ duration: 0.8, delay: 0.3, ease: 'easeOut' }}
                />
              </div>
              <span className="text-[0.6rem] font-mono text-geo-teal">{Number(contact.confidence)}% confidence</span>
            </div>
          )}
        </div>
        {contact.name != null && String(contact.name) !== '' && (
          <a href={liUrl} target="_blank" rel="noopener noreferrer"
            className="shrink-0 flex items-center gap-1.5 text-xs font-mono text-geo-muted hover:text-geo-teal border border-geo-teal/20 hover:border-geo-teal/50 rounded-md px-3 py-1.5 transition-all">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
            </svg>
            LinkedIn
          </a>
        )}
      </div>
    </motion.div>
  );
}

// ── Alt Contact Row ───────────────────────────────────────────────────────
function AltContactRow({ c, companyName }: { c: Record<string, unknown>; companyName?: string }) {
  const liUrl = buildLinkedInSearchUrl(String(c.name ?? ''), companyName);
  return (
    <motion.div variants={cardItem}
      className="flex items-center gap-3 py-2 px-3 rounded-md hover:bg-geo-slate/20 transition-colors group">
      <RecruiterAvatar name={String(c.name ?? '?')} size="sm" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-geo-text truncate">{String(c.email ?? '')}</span>
          {c.name != null && String(c.name) !== '' && (
            <span className="text-xs text-geo-dim truncate hidden sm:block">· {String(c.name)}</span>
          )}
        </div>
        {(c.position != null && String(c.position) !== '') || (c.department != null && String(c.department) !== '') ? (
          <p className="text-[0.6rem] font-mono text-geo-dim">{[c.position, c.department].filter(Boolean).map(String).join(' · ')}</p>
        ) : null}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <div className="w-8 h-1 rounded-full bg-geo-void overflow-hidden">
          <div className="h-full rounded-full bg-geo-teal/60" style={{ width: `${Number(c.confidence ?? 0)}%` }} />
        </div>
        {c.name != null && String(c.name) !== '' && (
          <a href={liUrl} target="_blank" rel="noopener noreferrer"
            className="opacity-0 group-hover:opacity-100 text-[0.6rem] font-mono text-geo-teal hover:underline transition-opacity">
            LinkedIn ↗
          </a>
        )}
      </div>
    </motion.div>
  );
}

// ── Profile Settings Modal ────────────────────────────────────────────────
function ProfileSettings({ user, onClose, onSave }: {
  user: UserProfile; onClose: () => void;
  onSave: (s: Partial<UserProfile>) => void;
}) {
  const [name, setName] = useState(user.name);
  const [linkedin, setLinkedin] = useState(user.linkedin_url || '');
  const [inst, setInst] = useState(user.institution || '');
  const [groq, setGroq] = useState(user.groq_api_1 || '');
  const [hunter, setHunter] = useState(user.hunter_api_key || '');
  const [getprospect, setGetprospect] = useState(user.getprospect_api_key || '');
  const [apollo, setApollo] = useState(user.apollo_api_key || '');
  const [snov, setSnov] = useState(user.snov_api_key || '');
  const [fireworks, setFireworks] = useState(user.fireworks_api_key || '');
  
  const [resumeText, setResumeText] = useState(user.resume_text || '');
  const [resumeBucketUri, setResumeBucketUri] = useState(user.resume_bucket_uri || '');
  const [latexSource, setLatexSource] = useState(user.latex_source || '');
  const [parsing, setParsing] = useState(false);
  const [pdfFileName, setPdfFileName] = useState('');
  const [pdfError, setPdfError] = useState('');
  const [latexFileName, setLatexFileName] = useState('');

  const handlePdfUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setParsing(true);
    setPdfError('');
    setPdfFileName('');
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch(`${API}/api/parse-pdf`, { method: 'POST', body: formData });
      const data = await res.json();
      if (res.ok && data.text) {
        setResumeText(data.text);
        setPdfFileName(file.name);
        if (data.resume_bucket_uri) setResumeBucketUri(data.resume_bucket_uri);
      } else {
        setPdfError(data.detail || 'Failed to upload/parse PDF');
      }
    } catch (err: unknown) {
      console.error("PDF parse failed:", err);
      setPdfError(err instanceof Error ? err.message : 'Network error during upload');
    } finally {
      setParsing(false);
    }
  };

  const handleLatexUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLatexFileName(file.name);
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      if (text) setLatexSource(text);
    };
    reader.readAsText(file);
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto">
      <motion.div
        initial={{ scale: 0.92, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.92, opacity: 0 }} transition={{ type: 'spring', stiffness: 320, damping: 28 }}
        className="geo-card p-6 w-full max-w-2xl space-y-6 my-8">
        
        <div className="flex items-center justify-between border-b border-geo-teal/20 pb-3">
          <h3 className="font-mono text-xl font-semibold text-geo-text">{PRODUCT_NAME} — profile</h3>
          <button onClick={onClose} className="text-geo-muted hover:text-geo-text text-2xl leading-none">&times;</button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Identity & Contact */}
          <div className="space-y-4">
            <h4 className="font-mono text-sm text-geo-teal uppercase tracking-widest border-b border-geo-teal/10 pb-1">Identity Profile</h4>
            {[
              { label: 'Display Name', val: name, set: setName, ph: 'Full Name' },
              { label: 'LinkedIn URL', val: linkedin, set: setLinkedin, ph: 'https://linkedin.com/in/...' },
              { label: 'Institution', val: inst, set: setInst, ph: 'Harvard University' },
            ].map(f => (
              <div key={f.label}>
                <label className="block text-xs font-mono text-geo-muted mb-1">{f.label}</label>
                <input value={f.val} onChange={e => f.set(e.target.value)} className="w-full geo-input" placeholder={f.ph} />
              </div>
            ))}
          </div>

          {/* Master API Endpoints */}
          <div className="space-y-4">
            <h4 className="font-mono text-sm text-geo-teal uppercase tracking-widest border-b border-geo-teal/10 pb-1">API keys for Junie</h4>
            <div className="space-y-3 max-h-60 overflow-y-auto pr-2 custom-scrollbar">
              {[
                { label: 'Groq API Key', val: groq, set: setGroq, type: 'password', req: true },
                { label: 'Hunter.io Key', val: hunter, set: setHunter, type: 'password', req: true },
                { label: 'GetProspect Key', val: getprospect, set: setGetprospect, type: 'password', req: false },
                { label: 'Apollo Key', val: apollo, set: setApollo, type: 'password', req: false },
                { label: 'Snov.io Key', val: snov, set: setSnov, type: 'password', req: false },
                { label: 'Fireworks AI Key', val: fireworks, set: setFireworks, type: 'password', req: false },
              ].map(f => (
                <div key={f.label}>
                  <label className="block text-xs font-mono text-geo-muted mb-1 flex justify-between">
                    <span>{f.label}</span>
                    {!f.req && <span className="text-[0.6rem] text-geo-dim border border-geo-dim/30 rounded px-1">Optional</span>}
                  </label>
                  <input type={f.type} value={f.val} onChange={e => f.set(e.target.value)} className="w-full geo-input py-1.5 text-geo-dim hover:text-geo-text focus:text-geo-text transition-colors" placeholder="••••••••••••" />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Master AI Files */}
        <div className="space-y-4 pt-2">
          <h4 className="font-mono text-sm text-geo-teal uppercase tracking-widest border-b border-geo-teal/10 pb-1">Resume files (synced)</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className={`p-3 border border-dashed rounded-lg bg-geo-surface transition-colors relative cursor-pointer group ${pdfError ? 'border-red-500/50 hover:border-red-500/80' : 'border-geo-teal/30 hover:border-geo-teal/60'}`}>
              <input type="file" accept=".pdf" onChange={handlePdfUpload} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
              <div className="flex items-center gap-3">
                <span className="text-2xl opacity-50 group-hover:opacity-100 transition-opacity">
                  {pdfError ? '❌' : '📄'}
                </span>
                <div>
                  <div className="text-sm font-mono text-geo-text">Master Resume (PDF)</div>
                  <div className="text-xs text-geo-dim">
                    {parsing ? 'Uploading & Extracting...' : 
                     pdfError ? <span className="text-red-400 font-medium">{pdfError}</span> :
                     pdfFileName ? <span className="text-geo-teal font-medium">✅ {pdfFileName}</span> : 
                     resumeText ? `✅ PDF Bound in Bucket` : 
                     'Click to bind PDF'}
                  </div>
                </div>
              </div>
            </div>

            <div className="p-3 border border-dashed border-geo-amber/30 rounded-lg bg-geo-surface hover:border-geo-amber/60 transition-colors relative cursor-pointer group">
              <input type="file" accept=".tex" onChange={handleLatexUpload} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
              <div className="flex items-center gap-3">
                <span className="text-2xl opacity-50 group-hover:opacity-100 transition-opacity">💻</span>
                <div>
                  <div className="text-sm font-mono text-geo-text">LaTeX Source (.tex)</div>
                  <div className="text-xs text-geo-dim">
                    {latexFileName ? <span className="text-geo-amber font-medium">✅ {latexFileName}</span> : 
                     latexSource ? `✅ TeX Bound Internally` : 
                     'Click to bind LaTeX source'}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="flex gap-3 pt-4 border-t border-geo-teal/20">
          <button onClick={() => {
            if (!groq.trim() || !hunter.trim()) {
              alert('Groq and Hunter.io API keys are required for Junie.');
              return;
            }
            onSave({
              name, linkedin_url: linkedin, institution: inst,
              groq_api_1: groq, hunter_api_key: hunter, getprospect_api_key: getprospect,
              apollo_api_key: apollo, snov_api_key: snov,
              fireworks_api_key: fireworks,
              resume_text: resumeText, latex_source: latexSource, resume_bucket_uri: resumeBucketUri
            });
            onClose();
          }} className="geo-btn flex-1">Save profile</button>
          <button onClick={onClose} className="geo-btn-outline px-6">Cancel</button>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ── Tailored Resume Modal ─────────────────────────────────────────────────
function TailoredResumeModal({ text, onClose }: { text: string; onClose: () => void }) {
  const [copied, setCopied] = useState(false);
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <motion.div
        initial={{ scale: 0.92, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.92, opacity: 0 }} transition={{ type: 'spring', stiffness: 320, damping: 28 }}
        className="geo-card p-6 w-full max-w-2xl max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-mono text-lg font-semibold text-geo-text flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-geo-amber animate-pulse" />AI-Tailored Resume Bullets
          </h3>
          <div className="flex gap-2">
            <button onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2e3); }}
              className="geo-badge-teal cursor-pointer hover:bg-geo-teal/20 transition-colors">
              {copied ? '✓ Copied' : '⎘ Copy'}
            </button>
            <button onClick={onClose} className="text-geo-muted hover:text-geo-text text-xl leading-none">×</button>
          </div>
        </div>
        <textarea readOnly value={text} className="flex-1 geo-input text-sm leading-relaxed resize-none min-h-[300px]" />
        <p className="text-[0.65rem] font-mono text-geo-dim mt-3">
          💡 With a .tex source saved in your profile, Junie can compile a tailored PDF per application.
        </p>
      </motion.div>
    </motion.div>
  );
}

// ── Processing View ───────────────────────────────────────────────────────
function ProcessingView({ logs }: { logs: LogEntry[] }) {
  const logRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] gap-8">
      {/* Hex spinner */}
      <div className="relative flex items-center justify-center w-28 h-28">
        <motion.div className="absolute inset-0 rounded-full border border-geo-teal/20"
          animate={{ scale: [1, 1.18, 1], opacity: [0.5, 0.15, 0.5] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }} />
        <motion.div className="absolute w-20 h-20 rounded-full border border-geo-amber/15"
          animate={{ scale: [1, 1.25, 1], opacity: [0.4, 0.1, 0.4] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut', delay: 0.6 }} />
        <motion.svg viewBox="0 0 32 32" className="w-12 h-12"
          animate={{ rotate: 360 }} transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}>
          <polygon points="16,2 28,10 28,22 16,30 4,22 4,10" fill="none" stroke="#14b8a6" strokeWidth="1.5" />
          <polygon points="16,8 22,12 22,20 16,24 10,20 10,12" fill="#14b8a620" stroke="#14b8a6" strokeWidth="0.8" />
        </motion.svg>
      </div>

      <div className="text-center">
        <motion.p animate={{ opacity: [0.6, 1, 0.6] }} transition={{ duration: 1.5, repeat: Infinity }}
          className="font-mono text-geo-text font-semibold mb-1">Junie is working</motion.p>
        <p className="font-mono text-xs text-geo-muted">Reading the posting · Researching the company · Finding contacts · Drafting email</p>
      </div>

      {/* Live log feed */}
      <div ref={logRef}
        className="w-full max-w-lg bg-geo-void/40 border border-geo-teal/10 rounded-xl p-4 max-h-64 overflow-y-auto space-y-0.5">
        {logs.length === 0
          ? <p className="text-xs font-mono text-geo-dim">Initializing...</p>
          : logs.map((l, i) => (
            <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.22 }} className={`geo-log ${logClass(l.icon)}`}>
              <span className="shrink-0">{l.icon}</span>
              <span className="break-all">{l.msg}</span>
            </motion.div>
          ))}
      </div>
    </div>
  );
}

// ── Step Indicator ────────────────────────────────────────────────────────
function StepIndicator({ step }: { step: Step }) {
  const steps: { id: Step; label: string }[] = [
    { id: 'input', label: 'Input' },
    { id: 'processing', label: 'Processing' },
    { id: 'results', label: 'Results' },
  ];
  const activeIdx = steps.findIndex(s => s.id === step);
  return (
    <div className="flex items-center gap-2">
      {steps.map((s, i) => (
        <div key={s.id} className="flex items-center gap-2">
          <div className={`flex items-center gap-1.5 text-[0.65rem] font-mono uppercase tracking-wider transition-colors ${i <= activeIdx ? 'text-geo-teal' : 'text-geo-dim'}`}>
            <div className={`w-1.5 h-1.5 rounded-full transition-colors ${i < activeIdx ? 'bg-geo-teal' : i === activeIdx ? 'bg-geo-teal animate-pulse' : 'bg-geo-void border border-geo-dim'}`} />
            {s.label}
          </div>
          {i < steps.length - 1 && <div className={`w-5 h-px ${i < activeIdx ? 'bg-geo-teal/50' : 'bg-geo-void'}`} />}
        </div>
      ))}
    </div>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────
export default function Dashboard() {
  const user = getUser();

  const [step, setStep] = useState<Step>('input');
  const [showSettings, setShowSettings] = useState(false);
  const [showSuccessOverlay, setShowSuccessOverlay] = useState(false);
  const [profileUser, setProfileUser] = useState<UserProfile | null>(user);

  // Inputs
  const [jobUrl, setJobUrl] = useState('');
  const [context, setContext] = useState('');
  const [resumeText, setResumeText] = useState(user?.resume_text || '');
  const [uploadedFileName, setUploadedFileName] = useState('');
  const [resumeFile, setResumeFile] = useState<File | null>(null);

  // LaTeX resume (synced from Profile Settings / Supabase)
  const [latexSource, setLatexSource] = useState(user?.latex_source || '');

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Results
  const [contacts, setContacts] = useState<Record<string, unknown>[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [jobData, setJobData] = useState<Record<string, unknown> | null>(null);
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [sendTo, setSendTo] = useState('');
  const [sending, setSending] = useState(false);
  const [emailCopied, setEmailCopied] = useState(false);
  const [showAllContacts, setShowAllContacts] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  // Tailor
  const [tailoring, setTailoring] = useState(false);
  const [tailoredText, setTailoredText] = useState('');
  const [showTailoredModal, setShowTailoredModal] = useState(false);

  // Compiled PDF from LaTeX pipeline
  const [compiledPdfBlob, setCompiledPdfBlob] = useState<Blob | null>(null);

  useEffect(() => {
    if (!user?.email) return;
    fetch(`${API}/api/profile?email=${encodeURIComponent(user.email)}`)
      .then(res => res.json())
      .then(data => {
        const latest = getUser();
        if (!data?.profile || !latest) return;
        const p = data.profile;
        const updatedUser = { ...latest, ...p };
        updatedUser.onboarded = true;
        setProfileUser(updatedUser);
        if (p.resume_text) setResumeText(p.resume_text);
        if (p.latex_source) setLatexSource(p.latex_source);
        persistUser(updatedUser);
      })
      .catch(console.error);
  }, [user?.email]);

  if (!user) return <Navigate to="/junie" replace />;
  if (!user.onboarded) return <Navigate to="/onboarding" replace />;

  const currentUser = profileUser ?? user;

  const addLog = (icon: string, msg: string) =>
    setLogs(prev => [...prev, { icon, msg, ts: Date.now() }]);

  // ── File Upload ────────────────────────────────────────────────────────
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadedFileName(file.name);
    setResumeFile(file);
    setCompiledPdfBlob(null); // reset any previous compiled PDF
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch(`${API}/api/parse-pdf`, { method: 'POST', body: formData });
      const data = await res.json();
      if (res.ok && data.text) setResumeText(data.text);
    } catch { /* silent */ }
  };

  // ── Run Pipeline ──────────────────────────────────────────────────────
  const handleRunPipeline = async () => {
    if (!jobUrl && !context) { setStatusMsg('Provide a Job URL or context'); return; }
    if (!resumeText) { setStatusMsg('Upload your resume PDF first'); return; }
    if (!currentUser.hunter_api_key?.trim()) {
      setStatusMsg('Add your Hunter.io API key in profile settings — Junie needs it for contact discovery.');
      return;
    }

    setStatusMsg('');
    setLogs([]);
    setContacts([]);
    setJobData(null);
    setSubject('');
    setBody('');
    setSendTo('');
    setCompiledPdfBlob(null);
    setStep('processing');
    addLog('🔄', 'Starting pipeline...');

    try {
      addLog('🌐', 'Analyzing job posting & searching contacts...');
      const res = await fetch(`${API}/api/pipeline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          job_url: jobUrl, 
          additional_context: context,
          hunter_key: currentUser.hunter_api_key || '',
          getprospect_key: currentUser.getprospect_api_key || '',
          apollo_key: currentUser.apollo_api_key || '',
          snov_key: currentUser.snov_api_key || '',
          groq_key: currentUser.groq_api_1 || '',
          fireworks_key: currentUser.fireworks_api_key || ''
        }),
      });
      const data = (await res.json()) as PipelineResponse;

      if (!res.ok) {
        addLog('❌', data.detail || 'Pipeline failed');
        setStep('input');
        setStatusMsg(data.detail || 'Pipeline failed');
        return;
      }

      setJobData(data.job_data ?? null);
      (data.log || []).forEach((l: [string, string]) => addLog(l[0], l[1]));

      if (data.all_contacts?.length) {
        setContacts(data.all_contacts);
        setSendTo(data.all_contacts.map((c) => String(c.email ?? '')).filter(Boolean).join(', '));
        addLog('📋', `${data.all_contacts.length} contact(s) discovered`);
      } else if (data.best_email) {
        setSendTo(data.best_email);
      }

      // ── LaTeX tailoring (only if user has LaTeX source) ────────────────
      if (latexSource) {
        addLog('✨', 'LaTeX source found — tailoring resume for this job...');
        try {
          const latexRes = await fetch(`${API}/api/tailor-latex`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              latex_source: latexSource,
              job_description: String(data.job_data?.job_description ?? ''),
              company_name: String(data.job_data?.company_name ?? ''),
              company_research: data.research_data || '',
              groq_key: currentUser.groq_api_1 || '',
              fireworks_key: currentUser.fireworks_api_key || ''
            }),
          });
          if (latexRes.ok) {
            const blob = await latexRes.blob();
            setCompiledPdfBlob(blob);
            addLog('✅', 'LaTeX resume tailored & compiled to PDF — will attach to email');
          } else {
            const errData = await latexRes.json().catch(() => ({}));
            addLog('⚠️', `LaTeX compile failed: ${errData.detail || 'using original resume'}`);
          }
        } catch {
          addLog('⚠️', 'LaTeX pipeline error — using original resume');
        }
      }

      let effectiveRecruiterName = String(data.job_data?.recruiter_name ?? '');
      if (!effectiveRecruiterName && data.best_email && data.all_contacts?.length) {
        const contact = data.all_contacts.find((c) => String(c.email ?? '') === data.best_email);
        if (contact?.name != null && String(contact.name) !== '') {
          effectiveRecruiterName = String(contact.name);
        }
      }

      addLog('✍️', 'Generating personalized email...');
      const emailRes = await fetch(`${API}/api/generate-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resume_text: resumeText,
          job_description: String(data.job_data?.job_description ?? ''),
          company_name: String(data.job_data?.company_name ?? ''),
          company_research: data.research_data || '',
          recruiter_name: effectiveRecruiterName,
          additional_context: context,
          user_name: currentUser.name,
          user_email: currentUser.email || '',
          linkedin_url: currentUser.linkedin_url || '',
          institution: currentUser.institution || '',
          job_url: jobUrl,
          groq_key: currentUser.groq_api_1 || '',
          fireworks_key: currentUser.fireworks_api_key || ''
        }),
      });
      const emailData = await emailRes.json();
      if (emailRes.ok) {
        setSubject(emailData.subject);
        setBody(emailData.body);
        addLog('✅', 'Email generated — ready to send!');
      } else {
        addLog('❌', 'Email generation failed');
      }

      await new Promise(r => setTimeout(r, 600));
      setStep('results');
    } catch (err) {
      addLog('❌', `Error: ${err}`);
      setStep('input');
      setStatusMsg('Network error. Is the backend running?');
    }
  };

  // ── Tailor Resume (text summary) ──────────────────────────────────────
  const handleTailorResume = async () => {
    if (!resumeText || !jobData) return;
    setTailoring(true);
    try {
      const res = await fetch(`${API}/api/tailor-resume`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resume_text: resumeText,
          job_description: String(jobData?.job_description ?? ''),
          company_name: String(jobData?.company_name ?? ''),
          groq_key: currentUser.groq_api_1 || '',
          fireworks_key: currentUser.fireworks_api_key || '',
        }),
      });
      const data = await res.json();
      if (res.ok && data.tailored_resume) {
        setTailoredText(data.tailored_resume);
        setShowTailoredModal(true);
      }
    } catch { /* silent */ } finally { setTailoring(false); }
  };

  // ── Send Email ────────────────────────────────────────────────────────
  const handleSend = async () => {
    if (!sendTo || !body) return;
    setSending(true);
    setStatusMsg('');
    try {
      const formData = new FormData();
      formData.append('to_emails', sendTo);
      formData.append('subject', subject);
      formData.append('body', body);
      formData.append('contacts_json', JSON.stringify(contacts));
      
      let currentToken = currentUser.access_token;
      
      // Auto-refresh token if it has expired (or is close to expiring)
      if (currentUser.expires_at && Date.now() > currentUser.expires_at - 60000) {
        setStatusMsg('Refreshing authentication...');
        const refreshed = await refreshAccessToken();
        if (refreshed && refreshed.access_token) {
          currentToken = refreshed.access_token;
          setProfileUser(refreshed);
        }
      }
      
      if (currentToken) {
        formData.append('access_token', currentToken);
      }

      // Prefer compiled PDF from LaTeX if available, otherwise original upload
      if (compiledPdfBlob) {
        formData.append('resume_file', compiledPdfBlob, 'resume_tailored.pdf');
        setStatusMsg('Sending with AI-tailored PDF...');
      } else if (resumeFile) {
        formData.append('resume_file', resumeFile);
      } else if (currentUser.resume_bucket_uri) {
        // Here we just pass the bucket URI, backend will fetch it directly from Supabase Storage
        formData.append('resume_bucket_uri', currentUser.resume_bucket_uri);
      }

      const res = await fetch(`${API}/api/send-email`, { method: 'POST', body: formData });
      const data = await res.json();
      if (res.ok) {
        setStatusMsg(data.message || '✅ Email sent!');
        setShowSuccessOverlay(true);
        setTimeout(() => setShowSuccessOverlay(false), 3500);
      } else {
        setStatusMsg('❌ Failed to send.');
      }
    } catch { setStatusMsg('❌ Network error.'); } finally { setSending(false); }
  };

  const topContact = contacts[0] || null;
  const altContacts = contacts.slice(1);

  return (
    <div className="min-h-screen bg-geo-obsidian bg-dot-grid">
      {/* ── Modals ──────────────────────────────────────────────────── */}
      <AnimatePresence>
        {showSuccessOverlay && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-geo-void/80 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0.8, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.8, y: -20 }}
              className="geo-card !bg-geo-void flex flex-col items-center justify-center p-10 border-geo-teal shadow-[0_0_50px_rgba(45,212,191,0.25)]"
            >
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1, rotate: 360 }}
                transition={{ type: "spring", damping: 12, stiffness: 100 }}
                className="w-20 h-20 rounded-full bg-geo-teal/20 border-2 border-geo-teal flex items-center justify-center text-4xl mb-6 shadow-[0_0_20px_rgba(45,212,191,0.5)]"
              >
                🚀
              </motion.div>
              <h2 className="text-2xl font-bold text-geo-text mb-3 tracking-wide">Application Dispatched!</h2>
              <p className="text-sm text-geo-teal/80 font-mono text-center max-w-[280px] leading-relaxed">
                Junie sent your message through your secure Gmail connection.
              </p>
            </motion.div>
          </motion.div>
        )}

        {showSettings && (
          <ProfileSettings user={currentUser} onClose={() => setShowSettings(false)}
            onSave={s => {
              updateProfileSettings(s as Partial<UserProfile> & { linkedin_url: string; institution: string });
              setProfileUser({ ...currentUser, ...s } as UserProfile); 
              if (s.resume_text !== undefined) setResumeText(s.resume_text);
              if (s.latex_source !== undefined) setLatexSource(s.latex_source);
            }} 
          />
        )}
        {showTailoredModal && tailoredText && (
          <TailoredResumeModal text={tailoredText} onClose={() => setShowTailoredModal(false)} />
        )}
      </AnimatePresence>

      {/* ── Header ──────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 border-b border-geo-teal/8 backdrop-blur-md bg-geo-obsidian/90">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link to="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
              <div className="w-7 h-7">
                <svg viewBox="0 0 32 32">
                  <polygon points="16,2 28,10 28,22 16,30 4,22 4,10" fill="none" stroke="#14b8a6" strokeWidth="1.5"/>
                  <polygon points="16,8 22,12 22,20 16,24 10,20 10,12" fill="#14b8a620" stroke="#14b8a6" strokeWidth="0.8"/>
                </svg>
              </div>
              <span className="font-mono text-sm font-semibold tracking-wide text-geo-text">
                {PRODUCT_NAME}
              </span>
            </Link>
            <StepIndicator step={step} />
          </div>

          <div className="flex items-center gap-3">
            {step === 'results' && (
              <motion.button initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                onClick={() => { setStep('input'); setStatusMsg(''); }}
                className="text-xs font-mono text-geo-muted hover:text-geo-teal border border-geo-teal/20 hover:border-geo-teal/40 rounded-md px-3 py-1.5 transition-all">
                ← New Application
              </motion.button>
            )}
            <button onClick={() => setShowSettings(true)}
              className="flex items-center gap-2 hover:bg-geo-slate/40 rounded-md px-3 py-1.5 transition-colors">
              {currentUser.picture
                ? <img src={currentUser.picture} className="w-6 h-6 rounded-full" alt="" />
                : <div className="w-6 h-6 rounded-full bg-geo-teal/20 flex items-center justify-center text-geo-teal text-xs font-mono">{currentUser.name?.[0] || '?'}</div>}
              <span className="text-xs text-geo-muted hidden sm:block">{currentUser.name}</span>
            </button>
            <button onClick={logout} className="text-xs text-geo-dim hover:text-geo-muted font-mono transition-colors">Logout</button>
          </div>
        </div>
      </header>

      {/* ── Page Content ────────────────────────────────────────────── */}
      <main className="max-w-5xl mx-auto px-6 py-10">
        <AnimatePresence mode="wait">

          {/* ─── STEP 1: INPUT ───────────────────────────────────────── */}
          {step === 'input' && (
            <motion.div key="input"
              variants={pageVariants} initial="initial" animate="animate" exit="exit"
              transition={pageTransition}>
              <motion.div variants={cardStagger} initial="hidden" animate="show" className="space-y-6 max-w-2xl mx-auto">

                <motion.div variants={cardItem} className="text-center mb-4">
                  <h1 className="font-mono text-2xl font-bold text-geo-text mb-2">
                    New <span className="text-gradient-teal">Application</span>
                  </h1>
                  <p className="text-sm text-geo-muted">Paste a LinkedIn job URL, confirm your resume, and let Junie run research, discovery, and drafting.</p>
                </motion.div>

                {/* Job Details Card */}
                <motion.div variants={cardItem} className="geo-card p-6 space-y-5">
                  <h2 className="font-mono text-sm font-semibold text-geo-text uppercase tracking-wider flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-geo-teal" />Job Details
                  </h2>
                  <div>
                    <label className="block text-xs font-mono text-geo-muted mb-2 uppercase tracking-wider">LinkedIn Job URL</label>
                    <input type="text" value={jobUrl} onChange={e => setJobUrl(e.target.value)}
                      className="w-full geo-input" placeholder="https://linkedin.com/jobs/view/..." />
                  </div>
                  <div>
                    <label className="block text-xs font-mono text-geo-muted mb-2 uppercase tracking-wider">
                      Additional Context <span className="normal-case text-geo-dim">(optional)</span>
                    </label>
                    <textarea value={context} onChange={e => setContext(e.target.value)}
                      className="w-full geo-input h-24 resize-none"
                      placeholder="Extra info: skills to highlight, specific contacts, notes..." />
                  </div>
                  <div className="flex items-center justify-between pt-5 border-t border-geo-teal/10 mt-6">
                    <div className="flex items-center gap-3">
                      <span className="text-xl opacity-60">📄</span>
                      <div>
                        <div className="text-[0.65rem] font-mono text-geo-muted uppercase tracking-wider mb-1">Resume Attached</div>
                        <div className="text-xs font-mono text-geo-teal flex items-center gap-2">
                          {uploadedFileName ? `${uploadedFileName}` : 'Using Default Profile Resume'}
                          {latexSource && !uploadedFileName && <span className="bg-geo-amber/10 text-geo-amber px-1.5 py-0.5 rounded text-[0.6rem]">✨ LaTeX Bound</span>}
                        </div>
                      </div>
                    </div>
                    <div>
                      <input type="file" ref={fileInputRef} className="hidden" accept=".pdf" onChange={handleFileUpload} />
                      <button onClick={() => fileInputRef.current?.click()} className="text-xs font-mono text-geo-muted hover:text-geo-amber hover:border-geo-amber/30 border border-geo-teal/20 px-3 py-1.5 rounded-md transition-all">
                        {uploadedFileName ? 'Change Resume' : 'Upload Different Resume'}
                      </button>
                    </div>
                  </div>
                </motion.div>

                {/* CTA */}
                <motion.div variants={cardItem}>
                  {statusMsg && <p className="text-xs font-mono text-geo-amber text-center mb-3">{statusMsg}</p>}
                  <motion.button onClick={handleRunPipeline}
                    whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}
                    className="w-full geo-btn py-4 text-base font-semibold">
                    ▶ Run Junie — discover contacts & draft email
                  </motion.button>
                  <p className="text-center text-xs text-geo-dim font-mono mt-3">
                    Junie reads the posting · Discovers contacts · {latexSource ? 'Can compile tailored PDF ·' : ''} Drafts your outreach
                  </p>
                </motion.div>
              </motion.div>
            </motion.div>
          )}

          {/* ─── STEP 2: PROCESSING ───────────────────────────────────── */}
          {step === 'processing' && (
            <motion.div key="processing"
              variants={pageVariants} initial="initial" animate="animate" exit="exit"
              transition={pageTransition}>
              <ProcessingView logs={logs} />
            </motion.div>
          )}

          {/* ─── STEP 3: RESULTS ──────────────────────────────────────── */}
          {step === 'results' && (
            <motion.div key="results"
              variants={pageVariants} initial="initial" animate="animate" exit="exit"
              transition={pageTransition}>
              <motion.div variants={cardStagger} initial="hidden" animate="show" className="space-y-6">

                {/* Top row: Recruiter + Job Details */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

                  {/* Recruiter */}
                  <motion.div variants={cardItem} className="space-y-3">
                    <h2 className="font-mono text-sm font-semibold text-geo-text uppercase tracking-wider flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-geo-cyan" />Primary contact
                      {contacts.length > 0 && <span className="geo-badge-teal ml-1">{contacts.length}</span>}
                    </h2>
                    {topContact ? (
                      <motion.div variants={cardStagger} initial="hidden" animate="show">
                        <RecruiterProfileCard contact={topContact} companyName={String(jobData?.company_name ?? '')} />
                      </motion.div>
                    ) : (
                      <div className="geo-card p-5 flex flex-col items-center justify-center py-8 text-center">
                        <span className="text-3xl mb-2">🔍</span>
                        <p className="text-xs font-mono text-geo-dim">No recruiter email found.</p>
                      </div>
                    )}
                    {altContacts.length > 0 && (
                      <div>
                        <button onClick={() => setShowAllContacts(p => !p)}
                          className="text-xs font-mono text-geo-muted hover:text-geo-teal transition-colors flex items-center gap-1.5">
                          <span>{showAllContacts ? '▲' : '▼'}</span>
                          {showAllContacts ? 'Hide alternates' : `${altContacts.length} more contact(s)`}
                        </button>
                        <AnimatePresence>
                          {showAllContacts && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.28 }}
                              className="mt-2 border border-geo-teal/10 rounded-md p-1 overflow-hidden">
                              <motion.div variants={cardStagger} initial="hidden" animate="show">
                                {altContacts.map((c, i) => <AltContactRow key={i} c={c} companyName={String(jobData?.company_name ?? '')} />)}
                              </motion.div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    )}
                  </motion.div>

                  {/* Job Details */}
                  <motion.div variants={cardItem} className="geo-card p-5">
                    <h2 className="font-mono text-sm font-semibold text-geo-text uppercase tracking-wider flex items-center gap-2 mb-4">
                      <span className="w-2 h-2 rounded-full bg-geo-amber" />Job Details
                    </h2>
                    {jobData ? (
                      <div className="space-y-2 text-xs font-mono">
                        {[['Company', String(jobData.company_name ?? '')], ['Role', String(jobData.job_title ?? '')], ['Recruiter', String(jobData.recruiter_name ?? '')], ['Website', String(jobData.company_website ?? '')]]
                          .filter(([, v]) => v)
                          .map(([label, value]) => (
                            <div key={label as string} className="flex gap-2">
                              <span className="text-geo-muted w-18 shrink-0">{label}:</span>
                              {label === 'Website'
                                ? <a href={value} target="_blank" rel="noopener noreferrer" className="text-geo-teal hover:underline truncate">{value}</a>
                                : <span className="text-geo-text">{value}</span>}
                            </div>
                          ))}
                      </div>
                    ) : <p className="text-xs text-geo-dim font-mono">No job data extracted.</p>}

                    {/* Resume attachment badge */}
                    {(compiledPdfBlob || resumeFile) && (
                      <div className={`mt-4 flex items-center gap-2 text-[0.65rem] font-mono rounded-md px-3 py-2 border ${compiledPdfBlob ? 'text-geo-amber bg-geo-amber/5 border-geo-amber/20' : 'text-geo-teal bg-geo-teal/5 border-geo-teal/10'}`}>
                        <span>{compiledPdfBlob ? '✨' : '📄'}</span>
                        <span>{compiledPdfBlob ? 'AI-tailored LaTeX PDF ready to attach' : `Attaching: ${uploadedFileName}`}</span>
                      </div>
                    )}

                    {/* Log accordion */}
                    {logs.length > 0 && (
                      <details className="mt-4 group">
                        <summary className="text-[0.65rem] font-mono text-geo-dim cursor-pointer hover:text-geo-muted">Junie activity ({logs.length})</summary>
                        <div className="mt-2 max-h-40 overflow-y-auto space-y-0.5 bg-geo-void/30 rounded p-2">
                          {logs.map((l, i) => (
                            <div key={i} className={`geo-log ${logClass(l.icon)}`}>
                              <span className="shrink-0">{l.icon}</span>
                              <span className="break-all">{l.msg}</span>
                            </div>
                          ))}
                        </div>
                      </details>
                    )}
                  </motion.div>
                </div>

                {/* Generated Email */}
                <motion.div variants={cardItem} className="geo-card p-5">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="font-mono text-sm font-semibold text-geo-text uppercase tracking-wider flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-geo-teal" />Generated Email
                    </h2>
                    <div className="flex gap-2">
                      {jobData && resumeText && (
                        <motion.button onClick={handleTailorResume} disabled={tailoring}
                          whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
                          className="text-[0.65rem] font-mono text-geo-amber hover:text-geo-text border border-geo-amber/30 hover:border-geo-amber/60 rounded px-2.5 py-1 transition-all">
                          {tailoring ? '⟳ Tailoring...' : '✨ Tailor Resume'}
                        </motion.button>
                      )}
                      {body && (
                        <button onClick={() => { navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`); setEmailCopied(true); setTimeout(() => setEmailCopied(false), 2e3); }}
                          className="geo-badge-teal cursor-pointer hover:bg-geo-teal/20 transition-colors">
                          {emailCopied ? '✓ Copied' : '⎘ Copy'}
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="space-y-3">
                    <input type="text" value={subject} onChange={e => setSubject(e.target.value)}
                      className="w-full geo-input font-medium" placeholder="Subject line..." />
                    <textarea value={body} onChange={e => setBody(e.target.value)}
                      className="w-full geo-input h-64 resize-y leading-relaxed text-sm"
                      placeholder="Email body will appear here..." />
                  </div>
                </motion.div>

                {/* Send */}
                <motion.div variants={cardItem} className="geo-card p-5 border-l-2 border-l-geo-teal/40">
                  <h2 className="font-mono text-sm font-semibold text-geo-text uppercase tracking-wider flex items-center gap-2 mb-4">
                    <span className="w-2 h-2 rounded-full bg-geo-teal" />Send Email
                  </h2>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-xs font-mono text-geo-muted mb-1.5 uppercase tracking-wider">Recipients</label>
                      <input type="text" value={sendTo} onChange={e => setSendTo(e.target.value)}
                        className="w-full geo-input" placeholder="recruiter@company.com" />
                    </div>
                    {statusMsg && (
                      <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                        className={`text-xs font-mono ${statusMsg.startsWith('✅') ? 'text-geo-teal' : 'text-geo-amber'}`}>
                        {statusMsg}
                      </motion.p>
                    )}
                    <motion.button onClick={handleSend} disabled={sending || !sendTo || !body}
                      whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}
                      className="w-full geo-btn">
                      {sending ? '⟳ Sending...' : `📤 Send Email${compiledPdfBlob ? ' with AI-tailored PDF' : resumeFile ? ' with Resume' : ''}`}
                    </motion.button>
                  </div>
                </motion.div>

              </motion.div>
            </motion.div>
          )}

        </AnimatePresence>
      </main>
    </div>
  );
}
