import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getUser, logout, updateProfileSettings, type UserProfile } from '../lib/auth';

const API = 'http://localhost:8002';

/* ── Log Entry Types ───────────────────────────────────────────────── */
type LogEntry = { icon: string; msg: string; ts: number };

function logClass(icon: string): string {
  if (['✅', '📋'].includes(icon)) return 'geo-log-success';
  if (['❌', '🔴'].includes(icon)) return 'geo-log-error';
  if (['⚠️', '⏭️'].includes(icon)) return 'geo-log-warn';
  if (['🔎', '📄', '🌐', '🔄', '🎯', '🏢', '🔍'].includes(icon)) return 'geo-log-info';
  return 'geo-log-dim';
}

/* ── Contact Card ──────────────────────────────────────────────────── */
function ContactCard({ c }: { c: Record<string, any> }) {
  const sourceColors: Record<string, string> = {
    jd_text: 'geo-badge-amber',
    hunter: 'geo-badge-teal',
    hunter_domain: 'geo-badge-teal',
    getprospect: 'geo-badge-dim',
  };
  const badgeClass = sourceColors[c.source] || 'geo-badge-dim';

  return (
    <div className="geo-card p-4 flex items-start justify-between gap-3 animate-crystallize">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-mono text-sm text-geo-text truncate">{c.email}</span>
          <span className={badgeClass}>{c.source?.replace('_', ' ')}</span>
        </div>
        <div className="flex items-center gap-3 text-xs text-geo-muted">
          {c.name && <span>{c.name}</span>}
          {c.position && <span>• {c.position}</span>}
          {c.department && <span>• {c.department}</span>}
        </div>
      </div>
      <div className="flex items-center gap-1.5 shrink-0">
        <div className="w-10 h-1.5 rounded-full bg-geo-void overflow-hidden">
          <div
            className="h-full rounded-full bg-geo-teal transition-all duration-500"
            style={{ width: `${c.confidence || 0}%` }}
          />
        </div>
        <span className="text-[0.6rem] font-mono text-geo-teal">{c.confidence}%</span>
      </div>
    </div>
  );
}

/* ── Profile Settings Modal ────────────────────────────────────────── */
function ProfileSettings({
  user,
  onClose,
  onSave,
}: {
  user: UserProfile;
  onClose: () => void;
  onSave: (s: { name: string; linkedin_url: string; institution: string }) => void;
}) {
  const [name, setName] = useState(user.name);
  const [linkedin, setLinkedin] = useState(user.linkedin_url || '');
  const [inst, setInst] = useState(user.institution || '');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="geo-card p-6 w-full max-w-md animate-crystallize space-y-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-mono text-lg font-semibold text-geo-text">Profile Settings</h3>
          <button onClick={onClose} className="text-geo-muted hover:text-geo-text text-xl">×</button>
        </div>
        <div>
          <label className="block text-xs font-mono text-geo-muted mb-1 uppercase tracking-wider">Display Name</label>
          <input value={name} onChange={e => setName(e.target.value)} className="w-full geo-input" />
        </div>
        <div>
          <label className="block text-xs font-mono text-geo-muted mb-1 uppercase tracking-wider">LinkedIn URL</label>
          <input value={linkedin} onChange={e => setLinkedin(e.target.value)} className="w-full geo-input" placeholder="https://linkedin.com/in/..." />
        </div>
        <div>
          <label className="block text-xs font-mono text-geo-muted mb-1 uppercase tracking-wider">Institution</label>
          <input value={inst} onChange={e => setInst(e.target.value)} className="w-full geo-input" placeholder="IIT Roorkee" />
        </div>
        <div className="flex gap-3 pt-2">
          <button onClick={() => { onSave({ name, linkedin_url: linkedin, institution: inst }); onClose(); }} className="geo-btn flex-1">
            Save
          </button>
          <button onClick={onClose} className="geo-btn-outline flex-1">Cancel</button>
        </div>
      </div>
    </div>
  );
}

/* ── Dashboard ─────────────────────────────────────────────────────── */
export default function Dashboard() {
  const user = getUser()!;
  const [showSettings, setShowSettings] = useState(false);
  const [currentUser, setCurrentUser] = useState(user);

  // Pipeline inputs
  const [jobUrl, setJobUrl] = useState('');
  const [context, setContext] = useState('');
  const [resumeText, setResumeText] = useState('');
  const [uploadedFileName, setUploadedFileName] = useState('');
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // State
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  // Pipeline results — PERSISTENT
  const [contacts, setContacts] = useState<any[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [jobData, setJobData] = useState<any>(null);

  // Email
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [sendTo, setSendTo] = useState('');
  const [sending, setSending] = useState(false);
  const [copied, setCopied] = useState(false);

  const logPanelRef = useRef<HTMLDivElement>(null);

  // Auto-scroll logs
  useEffect(() => {
    if (logPanelRef.current) {
      logPanelRef.current.scrollTop = logPanelRef.current.scrollHeight;
    }
  }, [logs]);

  const addLog = (icon: string, msg: string) => {
    setLogs(prev => [...prev, { icon, msg, ts: Date.now() }]);
  };

  /* ── File Upload ────────────────────────────────────────────────── */
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadedFileName(file.name);
    setResumeFile(file);

    const formData = new FormData();
    formData.append('file', file);
    try {
      addLog('📄', 'Extracting PDF text...');
      setStatusMsg('Extracting PDF...');
      const res = await fetch(`${API}/api/parse-pdf`, { method: 'POST', body: formData });
      const data = await res.json();
      if (res.ok && data.text) {
        setResumeText(data.text);
        addLog('✅', `PDF extracted: ${data.text.length} chars`);
        setStatusMsg('');
      } else {
        addLog('❌', 'Failed to extract PDF');
        setStatusMsg('Failed to extract PDF.');
      }
    } catch {
      addLog('❌', 'Network error extracting PDF');
      setStatusMsg('Error extracting PDF.');
    }
  };

  /* ── Pipeline ───────────────────────────────────────────────────── */
  const handleRunPipeline = async () => {
    if (!jobUrl && !context) { setStatusMsg('Provide Job URL or Context'); return; }
    if (!resumeText) { setStatusMsg('Upload Resume First'); return; }

    setLoading(true);
    setStatusMsg('Running pipeline...');
    addLog('🔄', 'Starting pipeline...');

    try {
      // Stage 1: Parse & Research
      addLog('🌐', 'Analyzing job posting & searching contacts...');
      const res = await fetch(`${API}/api/pipeline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_url: jobUrl, additional_context: context }),
      });

      const data = await res.json();
      if (!res.ok) {
        addLog('❌', data.detail || 'Pipeline failed');
        setStatusMsg(data.detail || 'Pipeline Failed');
        return;
      }

      setJobData(data.job_data);

      // Apply backend logs
      if (data.log) {
        data.log.forEach((l: [string, string]) => addLog(l[0], l[1]));
      }

      // Set contacts
      if (data.all_contacts?.length) {
        setContacts(data.all_contacts);
        const emails = data.all_contacts.map((c: any) => c.email).join(', ');
        setSendTo(emails);
        addLog('📋', `${data.all_contacts.length} contact(s) discovered`);
      } else if (data.best_email) {
        setSendTo(data.best_email);
      }

      if (data.research_data) {
        addLog('🔬', 'Company research complete');
      }

      // Stage 2: Generate Email
      addLog('✍️', 'Generating personalized email...');
      setStatusMsg('Generating email...');

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
          linkedin_url: currentUser.linkedin_url || '',
          institution: currentUser.institution || '',
        }),
      });

      const emailData = await emailRes.json();
      if (emailRes.ok) {
        setSubject(emailData.subject);
        setBody(emailData.body);
        addLog('✅', 'Email generated successfully');
        setStatusMsg('');
      } else {
        addLog('❌', 'Email generation failed');
        setStatusMsg('Email generation failed');
      }
    } catch (err) {
      addLog('❌', `Error: ${err}`);
      setStatusMsg('Network Error');
    } finally {
      setLoading(false);
    }
  };

  /* ── Send ────────────────────────────────────────────────────────── */
  const handleSend = async () => {
    if (!sendTo || !body) return;
    setSending(true);
    addLog('📤', `Sending to ${sendTo.split(',').length} recipient(s)...`);
    setStatusMsg('Sending...');
    try {
      const formData = new FormData();
      formData.append('to_emails', sendTo);
      formData.append('subject', subject);
      formData.append('body', body);
      if (resumeFile) formData.append('resume_file', resumeFile);

      const res = await fetch(`${API}/api/send-email`, { method: 'POST', body: formData });
      const data = await res.json();
      if (res.ok) {
        addLog('✅', data.message);
        setStatusMsg(data.message);
      } else {
        addLog('❌', 'Failed to send');
        setStatusMsg('Failed to send.');
      }
    } catch {
      addLog('❌', 'Network error sending');
      setStatusMsg('Failed to send.');
    } finally {
      setSending(false);
    }
  };

  /* ── Copy email ──────────────────────────────────────────────────── */
  const handleCopy = () => {
    navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSaveProfile = (s: { name: string; linkedin_url: string; institution: string }) => {
    updateProfileSettings(s);
    setCurrentUser({ ...currentUser, ...s });
  };

  return (
    <div className="min-h-screen bg-geo-obsidian bg-dot-grid">
      {showSettings && (
        <ProfileSettings user={currentUser} onClose={() => setShowSettings(false)} onSave={handleSaveProfile} />
      )}

      {/* ── Header ─────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 border-b border-geo-teal/8 backdrop-blur-md bg-geo-obsidian/90">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
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

          {statusMsg && (
            <div className="hidden md:block text-xs font-mono text-geo-amber animate-pulse-glow">
              {statusMsg}
            </div>
          )}

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowSettings(true)}
              className="flex items-center gap-2 hover:bg-geo-slate/40 rounded-md px-3 py-1.5 transition-colors"
            >
              {currentUser.picture ? (
                <img src={currentUser.picture} className="w-6 h-6 rounded-full" alt="" />
              ) : (
                <div className="w-6 h-6 rounded-full bg-geo-teal/20 flex items-center justify-center text-geo-teal text-xs font-mono">
                  {currentUser.name?.[0] || '?'}
                </div>
              )}
              <span className="text-xs text-geo-muted hidden sm:block">{currentUser.name}</span>
            </button>
            <button onClick={logout} className="text-xs text-geo-dim hover:text-geo-muted font-mono transition-colors">
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* ── Main Grid ──────────────────────────────────────────────── */}
      <main className="max-w-7xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-12 gap-6 animate-fade-in">
        
        {/* ── Left: Inputs ─────────────────────────────────────────── */}
        <div className="lg:col-span-4 space-y-5">
          <div className="geo-card p-5 space-y-4">
            <h2 className="font-mono text-sm font-semibold text-geo-text uppercase tracking-wider flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-geo-teal" />
              Pipeline Inputs
            </h2>

            <div>
              <label className="block text-xs font-mono text-geo-muted mb-1.5 uppercase tracking-wider">Job URL</label>
              <input
                type="text"
                value={jobUrl}
                onChange={e => setJobUrl(e.target.value)}
                className="w-full geo-input"
                placeholder="https://linkedin.com/jobs/..."
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-geo-muted mb-1.5 uppercase tracking-wider">Context</label>
              <textarea
                value={context}
                onChange={e => setContext(e.target.value)}
                className="w-full geo-input h-20 resize-none"
                placeholder="Extra skills, contacts..."
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-geo-muted mb-1.5 uppercase tracking-wider">Resume PDF</label>
              <input type="file" ref={fileInputRef} className="hidden" accept=".pdf" onChange={handleFileUpload} />
              <div
                onClick={() => fileInputRef.current?.click()}
                className="w-full border border-dashed border-geo-teal/20 rounded-md p-5 flex items-center justify-center
                         text-xs font-mono text-geo-muted cursor-pointer hover:bg-geo-teal/5 hover:border-geo-teal/40 transition-all"
              >
                {uploadedFileName ? `📄 ${uploadedFileName}` : '↑ Upload Resume PDF'}
              </div>
            </div>

            <button onClick={handleRunPipeline} disabled={loading} className="w-full geo-btn">
              {loading ? '⟳ Processing...' : '▶ Run Pipeline'}
            </button>
          </div>

          {/* ── Logs ───────────────────────────────────────────────── */}
          <div className="geo-card p-5">
            <h2 className="font-mono text-sm font-semibold text-geo-text uppercase tracking-wider flex items-center gap-2 mb-3">
              <span className="w-2 h-2 rounded-full bg-geo-amber" />
              Pipeline Logs
            </h2>
            <div
              ref={logPanelRef}
              className="space-y-0.5 max-h-64 overflow-y-auto rounded bg-geo-void/40 p-2"
            >
              {logs.length === 0 ? (
                <div className="text-xs font-mono text-geo-dim p-2">
                  Awaiting pipeline execution...
                </div>
              ) : (
                logs.map((l, i) => (
                  <div key={i} className={`geo-log ${logClass(l.icon)}`}>
                    <span className="shrink-0">{l.icon}</span>
                    <span className="break-all">{l.msg}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* ── Right: Results ───────────────────────────────────────── */}
        <div className="lg:col-span-8 space-y-5">

          {/* Contacts */}
          <div className="geo-card p-5">
            <h2 className="font-mono text-sm font-semibold text-geo-text uppercase tracking-wider flex items-center gap-2 mb-3">
              <span className="w-2 h-2 rounded-full bg-geo-cyan" />
              Contacts Discovered
              {contacts.length > 0 && (
                <span className="geo-badge-teal ml-auto">{contacts.length}</span>
              )}
            </h2>
            {contacts.length === 0 ? (
              <p className="text-xs font-mono text-geo-dim">Run the pipeline to discover recruiter contacts.</p>
            ) : (
              <div className="space-y-2">
                {contacts.map((c, i) => <ContactCard key={i} c={c} />)}
              </div>
            )}
          </div>

          {/* Job Info */}
          {jobData && (
            <div className="geo-card p-5 animate-crystallize">
              <h2 className="font-mono text-sm font-semibold text-geo-text uppercase tracking-wider flex items-center gap-2 mb-3">
                <span className="w-2 h-2 rounded-full bg-geo-amber" />
                Job Details
              </h2>
              <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                {jobData.company_name && (
                  <div>
                    <span className="text-geo-muted">Company:</span>
                    <span className="text-geo-text ml-2">{jobData.company_name}</span>
                  </div>
                )}
                {jobData.role && (
                  <div>
                    <span className="text-geo-muted">Role:</span>
                    <span className="text-geo-text ml-2">{jobData.role}</span>
                  </div>
                )}
                {jobData.recruiter_name && (
                  <div>
                    <span className="text-geo-muted">Recruiter:</span>
                    <span className="text-geo-text ml-2">{jobData.recruiter_name}</span>
                  </div>
                )}
                {jobData.location && (
                  <div>
                    <span className="text-geo-muted">Location:</span>
                    <span className="text-geo-text ml-2">{jobData.location}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Generated Email */}
          <div className="geo-card p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-mono text-sm font-semibold text-geo-text uppercase tracking-wider flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-geo-teal" />
                Generated Email
              </h2>
              {body && (
                <button onClick={handleCopy} className="geo-badge-teal cursor-pointer hover:bg-geo-teal/20 transition-colors">
                  {copied ? '✓ Copied' : '⎘ Copy'}
                </button>
              )}
            </div>
            <div className="space-y-3">
              <input
                type="text"
                value={subject}
                onChange={e => setSubject(e.target.value)}
                className="w-full geo-input font-medium"
                placeholder="Subject..."
              />
              <textarea
                value={body}
                onChange={e => setBody(e.target.value)}
                className="w-full geo-input h-56 resize-y leading-relaxed text-sm"
                placeholder="Awaiting email generation..."
              />
            </div>
          </div>

          {/* Send */}
          <div className="geo-card p-5 border-l-2 border-l-geo-teal/40">
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-mono text-geo-muted mb-1.5 uppercase tracking-wider">Send To</label>
                <input
                  type="text"
                  value={sendTo}
                  onChange={e => setSendTo(e.target.value)}
                  className="w-full geo-input"
                  placeholder="recruiter@company.com"
                />
              </div>
              <button
                onClick={handleSend}
                disabled={sending || !sendTo || !body}
                className="w-full geo-btn"
              >
                {sending ? '⟳ Sending...' : '📤 Send Email(s)'}
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
