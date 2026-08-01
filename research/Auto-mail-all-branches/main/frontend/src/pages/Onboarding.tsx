import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { getUser, updateProfileSettings, API_BASE } from '../lib/auth';
import { LEGACY_STORAGE_KEYS, PRODUCT_NAME } from '../lib/branding';

const cardItem = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: 'easeOut' as const } },
};
const cardStagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07 } },
};

export default function Onboarding() {
  const navigate = useNavigate();
  const user = getUser();

  const [name, setName] = useState(user?.name || '');
  const [linkedin, setLinkedin] = useState(user?.linkedin_url || '');
  const [institution, setInstitution] = useState(user?.institution || '');
  const [groqKey, setGroqKey] = useState(user?.groq_api_1 || '');
  const [hunterKey, setHunterKey] = useState(user?.hunter_api_key || '');
  const [getprospectKey, setGetprospectKey] = useState(user?.getprospect_api_key || '');
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');

  const [resumeText, setResumeText] = useState(user?.resume_text || '');
  const [resumeBucketUri, setResumeBucketUri] = useState(user?.resume_bucket_uri || '');
  const [pdfParsing, setPdfParsing] = useState(false);
  const [pdfFileName, setPdfFileName] = useState(user?.resume_text ? 'Saved resume' : '');
  const [pdfError, setPdfError] = useState('');

  const [latexSource, setLatexSource] = useState(user?.latex_source || '');
  const [latexFileName, setLatexFileName] = useState('');
  const latexRef = useRef<HTMLInputElement>(null);

  if (!user) { navigate('/'); return null; }

  const handlePdfUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPdfParsing(true);
    setPdfError('');
    setPdfFileName('');
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch(`${API_BASE}/api/parse-pdf`, { method: 'POST', body: formData });
      const data = await res.json();
      if (res.ok && data.text) {
        setResumeText(data.text);
        setPdfFileName(file.name);
        if (data.resume_bucket_uri) setResumeBucketUri(data.resume_bucket_uri);
      } else {
        setPdfError(data.detail || 'Failed to upload or parse PDF');
      }
    } catch {
      setPdfError('Network error during upload');
    } finally {
      setPdfParsing(false);
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

  const clearLatex = () => {
    setLatexSource('');
    setLatexFileName('');
    localStorage.removeItem(LEGACY_STORAGE_KEYS.latexDraft);
    if (latexRef.current) latexRef.current.value = '';
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');
    if (!resumeText.trim()) {
      setFormError('Please upload your resume PDF so Junie can attach it to applications.');
      return;
    }
    if (!hunterKey.trim()) {
      setFormError("Hunter.io API key is required for Junie's contact discovery.");
      return;
    }
    if (!groqKey.trim()) {
      setFormError('Groq API key is required.');
      return;
    }
    setSaving(true);
    await updateProfileSettings({
      name, linkedin_url: linkedin, institution,
      groq_api_1: groqKey, hunter_api_key: hunterKey,
      getprospect_api_key: getprospectKey,
      resume_text: resumeText,
      resume_bucket_uri: resumeBucketUri,
      latex_source: latexSource,
    });
    setSaving(false);
    navigate('/dashboard', { replace: true });
  };

  return (
    <div className="min-h-screen bg-geo-obsidian bg-dot-grid flex flex-col items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="w-full max-w-xl">

        <div className="flex items-center gap-4 mb-6">
          {user.picture && (
            <motion.img initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.1 }}
              src={user.picture} alt="Avatar" className="w-12 h-12 rounded-full border-2 border-geo-teal/40" />
          )}
          <div>
            <h1 className="font-mono text-2xl font-bold text-geo-text">Welcome to {PRODUCT_NAME}</h1>
            <p className="font-mono text-sm text-geo-muted">Junie will use this to research roles, find contacts, and send mail for you.</p>
          </div>
        </div>

        <form onSubmit={handleSave}>
          <motion.div variants={cardStagger} initial="hidden" animate="show" className="space-y-4">

            <motion.div variants={cardItem} className="geo-card p-5 space-y-4">
              <h3 className="font-mono text-xs font-semibold text-geo-teal uppercase tracking-wider flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-geo-teal" />Personal Info
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-mono text-geo-muted mb-1.5 uppercase tracking-wider">Full Name</label>
                  <input required value={name} onChange={e => setName(e.target.value)} className="w-full geo-input" />
                </div>
                <div>
                  <label className="block text-xs font-mono text-geo-muted mb-1.5 uppercase tracking-wider">LinkedIn URL</label>
                  <input required value={linkedin} onChange={e => setLinkedin(e.target.value)}
                    className="w-full geo-input" placeholder="https://linkedin.com/in/..." />
                </div>
              </div>
              <div>
                <label className="block text-xs font-mono text-geo-muted mb-1.5 uppercase tracking-wider">Institution / College</label>
                <input required value={institution} onChange={e => setInstitution(e.target.value)}
                  className="w-full geo-input" placeholder="e.g. IIT Roorkee" />
              </div>
            </motion.div>

            {/* Resume PDF — required */}
            <motion.div variants={cardItem} className="geo-card p-5 space-y-4">
              <h3 className="font-mono text-xs font-semibold text-geo-teal uppercase tracking-wider flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-geo-teal" />Resume (PDF) <span className="text-geo-amber">*</span>
              </h3>
              <p className="text-xs font-mono text-geo-muted">
                Junie attaches this PDF when you send applications. You can replace it anytime from the dashboard.
              </p>
              <label className={`block border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${pdfError ? 'border-red-500/40' : 'border-geo-teal/20 hover:border-geo-teal/45'}`}>
                <input type="file" accept="application/pdf,.pdf" className="hidden" onChange={handlePdfUpload} />
                <span className="text-2xl block mb-2">📄</span>
                <span className="text-xs font-mono text-geo-muted block">
                  {pdfParsing ? 'Uploading & extracting text…' : pdfFileName ? `✅ ${pdfFileName}` : 'Click to upload resume PDF'}
                </span>
              </label>
              {pdfError && <p className="text-xs font-mono text-red-400">{pdfError}</p>}
            </motion.div>

            {/* LaTeX optional */}
            <motion.div variants={cardItem} className="geo-card p-5 space-y-4">
              <h3 className="font-mono text-xs font-semibold text-geo-teal uppercase tracking-wider flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-geo-amber" />LaTeX source <span className="text-geo-dim font-normal normal-case">(optional)</span>
              </h3>

              <div className="bg-geo-amber/5 border border-geo-amber/20 rounded-lg p-3 text-xs font-mono text-geo-amber">
                <span className="font-semibold">Smart resume mode:</span>
                <span className="text-geo-muted ml-1">
                  Upload <span className="text-geo-amber">.tex</span> so Junie can tailor and recompile your resume per job before sending.
                </span>
              </div>

              <input
                ref={latexRef}
                type="file"
                accept=".tex,text/x-tex"
                className="hidden"
                onChange={handleLatexUpload}
              />

              {!latexSource && !latexFileName ? (
                <button type="button" onClick={() => latexRef.current?.click()}
                  className="w-full border-2 border-dashed border-geo-amber/20 hover:border-geo-amber/40 rounded-xl p-6 flex flex-col items-center justify-center gap-2 text-xs font-mono text-geo-muted hover:text-geo-amber transition-all cursor-pointer">
                  <span className="text-2xl">📝</span>
                  <span>Upload LaTeX source (.tex)</span>
                  <span className="text-geo-dim">Optional — enables tailored PDFs per application</span>
                </button>
              ) : (
                <AnimatePresence>
                  <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                    className="flex items-center justify-between bg-geo-amber/5 border border-geo-amber/30 rounded-lg px-4 py-3">
                    <div className="flex items-center gap-2 text-xs font-mono">
                      <span className="text-lg">📝</span>
                      <div>
                        <p className="text-geo-amber font-semibold">{latexFileName || 'LaTeX source'}</p>
                        <p className="text-geo-dim">Loaded — Junie can tailor per job</p>
                      </div>
                    </div>
                    <button type="button" onClick={clearLatex}
                      className="text-geo-dim hover:text-geo-muted text-lg leading-none">×</button>
                  </motion.div>
                </AnimatePresence>
              )}

              <p className="text-[0.6rem] font-mono text-geo-dim">
                You can add or change this later from profile settings in the dashboard.
              </p>
            </motion.div>

            <motion.div variants={cardItem} className="geo-card p-5 space-y-4">
              <h3 className="font-mono text-xs font-semibold text-geo-teal uppercase tracking-wider flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-geo-teal" />API configuration
              </h3>
              <div>
                <label className="block text-xs font-mono text-geo-muted mb-1.5 uppercase tracking-wider">
                  GROQ API Key <span className="text-geo-amber">*</span>
                </label>
                <input required type="password" value={groqKey} onChange={e => setGroqKey(e.target.value)}
                  className="w-full geo-input font-mono" placeholder="gsk_..." />
                <p className="text-[0.6rem] font-mono text-geo-dim mt-1">Powers Junie's email drafting.</p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-mono text-geo-muted mb-1.5 uppercase tracking-wider">
                    Hunter.io key <span className="text-geo-amber">*</span>
                  </label>
                  <input required type="password" value={hunterKey} onChange={e => setHunterKey(e.target.value)}
                    className="w-full geo-input font-mono" placeholder="••••••••" />
                  <p className="text-[0.6rem] font-mono text-geo-dim mt-1">Required for Junie's contact discovery.</p>
                </div>
                <div>
                  <label className="block text-xs font-mono text-geo-muted mb-1.5 uppercase tracking-wider">GetProspect key <span className="text-geo-dim">(optional)</span></label>
                  <input type="password" value={getprospectKey} onChange={e => setGetprospectKey(e.target.value)}
                    className="w-full geo-input font-mono" placeholder="••••••••" />
                </div>
              </div>
            </motion.div>

            {formError && (
              <p className="text-xs font-mono text-geo-amber text-center">{formError}</p>
            )}

            <motion.div variants={cardItem}>
              <motion.button type="submit" disabled={saving}
                whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}
                className="w-full geo-btn py-4 text-base font-semibold">
                {saving ? 'Saving...' : 'Complete setup & open dashboard ▶'}
              </motion.button>
            </motion.div>

          </motion.div>
        </form>
      </motion.div>
    </div>
  );
}
