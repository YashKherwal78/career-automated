import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { getUser, updateProfileSettings } from '../lib/auth';

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
  const [groqKey, setGroqKey] = useState('');
  const [hunterKey, setHunterKey] = useState('');
  const [getprospectKey, setGetprospectKey] = useState('');
  const [saving, setSaving] = useState(false);

  // LaTeX resume source
  const [latexFileName, setLatexFileName] = useState('');
  const [latexUploaded, setLatexUploaded] = useState(false);
  const latexRef = useRef<HTMLInputElement>(null);

  if (!user) { navigate('/'); return null; }

  const handleLatexUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLatexFileName(file.name);
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      if (text) {
        localStorage.setItem('applywith_latex_source', text);
        setLatexUploaded(true);
      }
    };
    reader.readAsText(file);
  };

  const clearLatex = () => {
    localStorage.removeItem('applywith_latex_source');
    setLatexFileName('');
    setLatexUploaded(false);
    if (latexRef.current) latexRef.current.value = '';
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    await updateProfileSettings({
      name, linkedin_url: linkedin, institution,
      groq_api_1: groqKey, hunter_api_key: hunterKey,
      getprospect_api_key: getprospectKey,
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

        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          {user.picture && (
            <motion.img initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.1 }}
              src={user.picture} alt="Avatar" className="w-12 h-12 rounded-full border-2 border-geo-teal/40" />
          )}
          <div>
            <h1 className="font-mono text-2xl font-bold text-geo-text">Welcome to ApplyWithAI</h1>
            <p className="font-mono text-sm text-geo-muted">Set up your profile to start the pipeline.</p>
          </div>
        </div>

        <form onSubmit={handleSave}>
          <motion.div variants={cardStagger} initial="hidden" animate="show" className="space-y-4">

            {/* Personal Info */}
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

            {/* Resume Upload */}
            <motion.div variants={cardItem} className="geo-card p-5 space-y-4">
              <h3 className="font-mono text-xs font-semibold text-geo-teal uppercase tracking-wider flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-geo-amber" />Resume (LaTeX Source — Optional but Recommended)
              </h3>

              <div className="bg-geo-amber/5 border border-geo-amber/20 rounded-lg p-3 text-xs font-mono text-geo-amber">
                <span className="font-semibold">✨ Smart Resume Mode:</span>
                <span className="text-geo-muted ml-1">
                  Upload your <span className="text-geo-amber">.tex LaTeX source</span> to enable
                  AI-tailored PDF generation per job. The system will modify your resume based on
                  the JD & company research, recompile it, and attach the custom PDF to each email automatically.
                </span>
              </div>

              {/* .tex upload */}
              <input
                ref={latexRef}
                type="file"
                accept=".tex,text/x-tex"
                className="hidden"
                onChange={handleLatexUpload}
              />

              {!latexUploaded ? (
                <button type="button" onClick={() => latexRef.current?.click()}
                  className="w-full border-2 border-dashed border-geo-amber/20 hover:border-geo-amber/40 rounded-xl p-6 flex flex-col items-center justify-center gap-2 text-xs font-mono text-geo-muted hover:text-geo-amber transition-all cursor-pointer">
                  <span className="text-2xl">📝</span>
                  <span>Upload LaTeX Source (.tex)</span>
                  <span className="text-geo-dim">Optional — enables AI resume tailoring per job</span>
                </button>
              ) : (
                <AnimatePresence>
                  <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                    className="flex items-center justify-between bg-geo-amber/5 border border-geo-amber/30 rounded-lg px-4 py-3">
                    <div className="flex items-center gap-2 text-xs font-mono">
                      <span className="text-lg">📝</span>
                      <div>
                        <p className="text-geo-amber font-semibold">{latexFileName}</p>
                        <p className="text-geo-dim">LaTeX source loaded ✅</p>
                      </div>
                    </div>
                    <button type="button" onClick={clearLatex}
                      className="text-geo-dim hover:text-geo-muted text-lg leading-none">×</button>
                  </motion.div>
                </AnimatePresence>
              )}

              <p className="text-[0.6rem] font-mono text-geo-dim">
                Don't have LaTeX? Skip this — your uploaded PDF will be attached as-is.
                You can add your LaTeX source later from Profile Settings.
              </p>
            </motion.div>

            {/* API Keys */}
            <motion.div variants={cardItem} className="geo-card p-5 space-y-4">
              <h3 className="font-mono text-xs font-semibold text-geo-teal uppercase tracking-wider flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-geo-teal" />API Configuration
              </h3>
              <div>
                <label className="block text-xs font-mono text-geo-muted mb-1.5 uppercase tracking-wider">
                  GROQ API Key <span className="text-geo-amber">*</span>
                </label>
                <input required type="password" value={groqKey} onChange={e => setGroqKey(e.target.value)}
                  className="w-full geo-input font-mono" placeholder="gsk_..." />
                <p className="text-[0.6rem] font-mono text-geo-dim mt-1">Required to generate emails using Llama 3.3.</p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-mono text-geo-muted mb-1.5 uppercase tracking-wider">Hunter.io Key (Optional)</label>
                  <input type="password" value={hunterKey} onChange={e => setHunterKey(e.target.value)}
                    className="w-full geo-input font-mono" placeholder="••••••••" />
                </div>
                <div>
                  <label className="block text-xs font-mono text-geo-muted mb-1.5 uppercase tracking-wider">GetProspect Key (Optional)</label>
                  <input type="password" value={getprospectKey} onChange={e => setGetprospectKey(e.target.value)}
                    className="w-full geo-input font-mono" placeholder="••••••••" />
                </div>
              </div>
            </motion.div>

            {/* Submit */}
            <motion.div variants={cardItem}>
              <motion.button type="submit" disabled={saving}
                whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}
                className="w-full geo-btn py-4 text-base font-semibold">
                {saving ? 'Saving...' : 'Complete Setup & Launch Dashboard ▶'}
              </motion.button>
            </motion.div>

          </motion.div>
        </form>
      </motion.div>
    </div>
  );
}
