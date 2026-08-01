import { useState, useRef, useEffect } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { motion, AnimatePresence, type Variants } from 'framer-motion';
import { getUser, logout, updateProfileSettings, type UserProfile } from '../lib/auth';

const API = 'http://127.0.0.1:8001';

// ── Types ─────────────────────────────────────────────────────────────────
type Step = 'input' | 'processing' | 'results';
type LogEntry = { icon: string; msg: string; ts: number };

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
function RecruiterProfileCard({ contact, companyName }: { contact: Record<string, any>; companyName?: string }) {
  const sourceLabels: Record<string, string> = {
    jd_text: 'Found in JD', hunter: 'Hunter.io', hunter_domain: 'Hunter Domain',
    getprospect: 'GetProspect', mailmeteor: 'MailMeteor', salesql: 'SalesQL',
  };
  const liUrl = buildLinkedInSearchUrl(contact.name || '', companyName);
  return (
    <motion.div variants={cardItem} className="geo-card p-5 border-l-2 border-l-geo-teal/60">
      <div className="flex items-start gap-4">
        <RecruiterAvatar name={contact.name || 'R'} size="lg" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5 flex-wrap">
            <span className="font-mono font-semibold text-geo-text text-sm">{contact.name || 'Unknown Recruiter'}</span>
            {contact.source && <span className="geo-badge-teal">{sourceLabels[contact.source] || contact.source}</span>}
          </div>
          {contact.position && (
            <p className="text-xs text-geo-muted font-mono mb-0.5">
              {contact.position}{contact.department ? ` · ${contact.department}` : ''}
            </p>
          )}
          <p className="text-xs font-mono text-geo-teal break-all">{contact.email}</p>
          {contact.confidence !== undefined && (
            <div className="flex items-center gap-2 mt-2">
              <div className="flex-1 h-1 rounded-full bg-geo-void overflow-hidden">
                <motion.div
                  className="h-full rounded-full bg-geo-teal"
                  initial={{ width: 0 }}
                  animate={{ width: `${contact.confidence}%` }}
                  transition={{ duration: 0.8, delay: 0.3, ease: 'easeOut' }}
                />
              </div>
              <span className="text-[0.6rem] font-mono text-geo-teal">{contact.confidence}% confidence</span>
            </div>
          )}
        </div>
        {contact.name && (
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
function AltContactRow({ c, companyName }: { c: Record<string, any>; companyName?: string }) {
  const liUrl = buildLinkedInSearchUrl(c.name || '', companyName);
  return (
    <motion.div variants={cardItem}
      className="flex items-center gap-3 py-2 px-3 rounded-md hover:bg-geo-slate/20 transition-colors group">
      <RecruiterAvatar name={c.name || '?'} size="sm" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-geo-text truncate">{c.email}</span>
          {c.name && <span className="text-xs text-geo-dim truncate hidden sm:block">· {c.name}</span>}
        </div>
        {(c.position || c.department) && (
          <p className="text-[0.6rem] font-mono text-geo-dim">{[c.position, c.department].filter(Boolean).join(' · ')}</p>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <div className="w-8 h-1 rounded-full bg-geo-void overflow-hidden">
          <div className="h-full rounded-full bg-geo-teal/60" style={{ width: `${c.confidence || 0}%` }} />
        </div>
        {c.name && (
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
  
  const [resumeText, setResumeText] = useState(user.resume_text || '');
  const [resumePdfBase64, setResumePdfBase64] = useState(user.resume_pdf_base64 || '');
  const [latexSource, setLatexSource] = useState(user.latex_source || '');
  const [parsing, setParsing] = useState(false);

  const handlePdfUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setParsing(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch(`${API}/api/parse-pdf`, { method: 'POST', body: formData });
      const data = await res.json();
      if (res.ok && data.text) {
        setResumeText(data.text);
        if (data.pdf_base64) setResumePdfBase64(data.pdf_base64);
      }
    } catch (err) {
      console.error("PDF parse failed:", err);
    } finally {
      setParsing(false);
    }
  };

  const handleLatexUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
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
          <h3 className="font-mono text-xl font-semibold text-geo-text">Master Profile Configuration</h3>
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
            <h4 className="font-mono text-sm text-geo-teal uppercase tracking-widest border-b border-geo-teal/10 pb-1">Pipeline Endpoints</h4>
            {[
              { label: 'Groq API Key', val: groq, set: setGroq, type: 'password' },
              { label: 'Hunter.io Key', val: hunter, set: setHunter, type: 'password' },
              { label: 'GetProspect Key', val: getprospect, set: setGetprospect, type: 'password' },
            ].map(f => (
              <div key={f.label}>
                <label className="block text-xs font-mono text-geo-muted mb-1">{f.label}</label>
                <input type={f.type} value={f.val} onChange={e => f.set(e.target.value)} className="w-full geo-input text-geo-dim hover:text-geo-text focus:text-geo-text transition-colors" placeholder="••••••••••••" />
              </div>
            ))}
          </div>
        </div>

        {/* Master AI Files */}
        <div className="space-y-4 pt-2">
          <h4 className="font-mono text-sm text-geo-teal uppercase tracking-widest border-b border-geo-teal/10 pb-1">AI Pipeline Files (Supabase Sync)</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-3 border border-dashed border-geo-teal/30 rounded-lg bg-geo-surface hover:border-geo-teal/60 transition-colors relative cursor-pointer group">
              <input type="file" accept=".pdf" onChange={handlePdfUpload} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
              <div className="flex items-center gap-3">
                <span className="text-2xl opacity-50 group-hover:opacity-100 transition-opacity">📄</span>
                <div>
                  <div className="text-sm font-mono text-geo-text">Master Resume (PDF)</div>
                  <div className="text-xs text-geo-dim">{parsing ? 'Extracting text...' : resumeText ? `✅ Stored (${resumeText.length} chars)` : 'Click to bind PDF'}</div>
                </div>
              </div>
            </div>

            <div className="p-3 border border-dashed border-geo-amber/30 rounded-lg bg-geo-surface hover:border-geo-amber/60 transition-colors relative cursor-pointer group">
              <input type="file" accept=".tex" onChange={handleLatexUpload} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
              <div className="flex items-center gap-3">
                <span className="text-2xl opacity-50 group-hover:opacity-100 transition-opacity">💻</span>
                <div>
                  <div className="text-sm font-mono text-geo-text">LaTeX Source (.tex)</div>
                  <div className="text-xs text-geo-dim">{latexSource ? `✅ Stored (${latexSource.length} chars)` : 'Click to bind LaTeX source'}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="flex gap-3 pt-4 border-t border-geo-teal/20">
          <button onClick={() => { 
            onSave({ 
              name, linkedin_url: linkedin, institution: inst, 
              groq_api_1: groq, hunter_api_key: hunter, getprospect_api_key: getprospect,
              resume_text: resumeText, latex_source: latexSource, resume_pdf_base64: resumePdfBase64
            }); 
            onClose(); 
          }} className="geo-btn flex-1">Sync Profile to Supabase</button>
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
          💡 LaTeX auto-compile: upload your .tex source in Onboarding to get a compiled PDF sent automatically.
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
          className="font-mono text-geo-text font-semibold mb-1">Running Pipeline</motion.p>
        <p className="font-mono text-xs text-geo-muted">Scraping · Researching · Finding contacts · Generating email</p>
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
  const user = getUser()!;
  if (user && !user.onboarded) return <Navigate to="/onboarding" replace />;

  const [step, setStep] = useState<Step>('input');
  const [showSettings, setShowSettings] = useState(false);
  const [currentUser, setCurrentUser] = useState(user);

  // Inputs
  const [jobUrl, setJobUrl] = useState('');
  const [context, setContext] = useState('');
  const [resumeText, setResumeText] = useState(currentUser.resume_text || '');
  const [uploadedFileName, setUploadedFileName] = useState('');
  const [resumeFile, setResumeFile] = useState<File | null>(null);

  // LaTeX resume (synced from Profile Settings / Supabase)
  const [latexSource, setLatexSource] = useState(currentUser.latex_source || '');


  const fileInputRef = useRef<HTMLInputElement>(null);

  // Results
  const [contacts, setContacts] = useState<any[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [jobData, setJobData] = useState<any>(null);
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
        body: JSON.stringify({ job_url: jobUrl, additional_context: context }),
      });
      const data = await res.json();

      if (!res.ok) {
        addLog('❌', data.detail || 'Pipeline failed');
        setStep('input');
        setStatusMsg(data.detail || 'Pipeline failed');
        return;
      }

      setJobData(data.job_data);
      (data.log || []).forEach((l: [string, string]) => addLog(l[0], l[1]));

      if (data.all_contacts?.length) {
        setContacts(data.all_contacts);
        setSendTo(data.all_contacts.map((c: any) => c.email).join(', '));
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
              job_description: data.job_data?.job_description || '',
              company_name: data.job_data?.company_name || '',
              company_research: data.research_data || '',
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

      addLog('✍️', 'Generating personalized email...');
      const emailRes = await fetch(`${API}/api/generate-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resume_text: resumeText,
          job_description: data.job_data?.job_description || '',
          company_name: data.job_data?.company_name || '',
          company_research: data.research_data || '',
          recruiter_name: data.job_data?.recruiter_name || '',
          additional_context: context,
          user_name: currentUser.name,
          user_email: currentUser.email || '',
          linkedin_url: currentUser.linkedin_url || '',
          institution: currentUser.institution || '',
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
          job_description: jobData.job_description || '',
          company_name: jobData.company_name || '',
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

      // Prefer compiled PDF from LaTeX if available, otherwise original upload
      if (compiledPdfBlob) {
        formData.append('resume_file', compiledPdfBlob, 'resume_tailored.pdf');
        setStatusMsg('Sending with AI-tailored PDF...');
      } else if (resumeFile) {
        formData.append('resume_file', resumeFile);
      } else if (currentUser.resume_pdf_base64) {
        try {
          const byteStr = atob(currentUser.resume_pdf_base64);
          const bytes = new Uint8Array(byteStr.length);
          for (let i = 0; i < byteStr.length; i++) bytes[i] = byteStr.charCodeAt(i);
          const blob = new Blob([bytes], { type: 'application/pdf' });
          formData.append('resume_file', blob, 'resume.pdf');
        } catch (e) {
          console.error("Base64 PDF decode failed", e);
        }
      }

      const res = await fetch(`${API}/api/send-email`, { method: 'POST', body: formData });
      const data = await res.json();
      setStatusMsg(res.ok ? (data.message || '✅ Email sent!') : '❌ Failed to send.');
    } catch { setStatusMsg('❌ Network error.'); } finally { setSending(false); }
  };

  const topContact = contacts[0] || null;
  const altContacts = contacts.slice(1);

  return (
    <div className="min-h-screen bg-geo-obsidian bg-dot-grid">
      {/* ── Modals ──────────────────────────────────────────────────── */}
      <AnimatePresence>
        {showSettings && (
          <ProfileSettings user={currentUser} onClose={() => setShowSettings(false)}
            onSave={s => { 
              updateProfileSettings(s as any); 
              setCurrentUser({ ...currentUser, ...s } as UserProfile); 
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
                Apply<span className="text-geo-teal">With</span>AI
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
                  <p className="text-sm text-geo-muted">Paste a LinkedIn job URL, upload your resume, and let the pipeline do the rest.</p>
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
                </motion.div>

                {/* Resume Upload Card */}
                <motion.div variants={cardItem} className="geo-card p-6 space-y-4">
                  <h2 className="font-mono text-sm font-semibold text-geo-text uppercase tracking-wider flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-geo-amber" />Resume
                  </h2>
                  <input type="file" ref={fileInputRef} className="hidden" accept=".pdf" onChange={handleFileUpload} />
                  <div onClick={() => fileInputRef.current?.click()}
                    className="w-full border-2 border-dashed border-geo-teal/20 rounded-xl p-8 flex flex-col items-center justify-center gap-3 text-sm font-mono text-geo-muted cursor-pointer hover:bg-geo-teal/5 hover:border-geo-teal/40 transition-all">
                    {uploadedFileName ? (
                      <><span className="text-2xl">📄</span><span className="text-geo-teal">{uploadedFileName}</span><span className="text-xs text-geo-dim">Click to change</span></>
                    ) : (
                      <><span className="text-3xl opacity-40">↑</span><span>Upload Resume PDF</span><span className="text-xs text-geo-dim">PDF only</span></>
                    )}
                  </div>
                  {resumeText && (
                    <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-xs text-geo-teal font-mono">
                      ✅ {resumeText.length} characters extracted
                    </motion.p>
                  )}
                  {/* LaTeX badge */}
                  {latexSource && (
                    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                      className="flex items-center gap-2 text-[0.65rem] font-mono text-geo-amber bg-geo-amber/5 border border-geo-amber/20 rounded-md px-3 py-2">
                      <span>✨</span>
                      <span>LaTeX source loaded — resume will be auto-tailored & compiled for each job</span>
                    </motion.div>
                  )}
                </motion.div>

                {/* CTA */}
                <motion.div variants={cardItem}>
                  {statusMsg && <p className="text-xs font-mono text-geo-amber text-center mb-3">{statusMsg}</p>}
                  <motion.button onClick={handleRunPipeline}
                    whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}
                    className="w-full geo-btn py-4 text-base font-semibold">
                    ▶ Run Pipeline — Find Recruiter & Generate Email
                  </motion.button>
                  <p className="text-center text-xs text-geo-dim font-mono mt-3">
                    Scrapes job · Finds recruiter email · {latexSource ? 'Compiles tailored PDF ·' : ''} Generates personalized cold email
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
                      <span className="w-2 h-2 rounded-full bg-geo-cyan" />Recruiter Found
                      {contacts.length > 0 && <span className="geo-badge-teal ml-1">{contacts.length}</span>}
                    </h2>
                    {topContact ? (
                      <motion.div variants={cardStagger} initial="hidden" animate="show">
                        <RecruiterProfileCard contact={topContact} companyName={jobData?.company_name} />
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
                                {altContacts.map((c, i) => <AltContactRow key={i} c={c} companyName={jobData?.company_name} />)}
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
                        {[['Company', jobData.company_name], ['Role', jobData.job_title], ['Recruiter', jobData.recruiter_name], ['Website', jobData.company_website]]
                          .filter(([, v]) => v)
                          .map(([label, value]) => (
                            <div key={label as string} className="flex gap-2">
                              <span className="text-geo-muted w-18 shrink-0">{label}:</span>
                              {label === 'Website'
                                ? <a href={value as string} target="_blank" rel="noopener noreferrer" className="text-geo-teal hover:underline truncate">{value}</a>
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
                        <summary className="text-[0.65rem] font-mono text-geo-dim cursor-pointer hover:text-geo-muted">Pipeline Logs ({logs.length})</summary>
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
