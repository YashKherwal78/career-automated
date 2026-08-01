import { motion, type Variants } from 'framer-motion';
import { Link } from 'react-router-dom';

const navVariants: Variants = {
  hidden: { opacity: 0, y: -20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' } },
};

const moduleVariants: Variants = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.15, duration: 0.6, ease: 'easeOut' },
  }),
};

export default function LimitlessHome() {
  return (
    <div className="min-h-screen bg-geo-obsidian text-geo-text font-sans overflow-hidden bg-dot-grid relative">
      
      {/* Background glow effects */}
      <div className="absolute top-[-100px] left-[-100px] w-96 h-96 bg-geo-teal/10 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute bottom-[-100px] right-[-100px] w-[500px] h-[500px] bg-geo-amber/5 rounded-full blur-[120px] pointer-events-none" />
      
      {/* Navigation */}
      <motion.nav 
        variants={navVariants}
        initial="hidden"
        animate="visible"
        className="relative z-10 max-w-7xl mx-auto px-6 py-6 flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8">
            <svg viewBox="0 0 32 32">
              <polygon points="16,2 28,10 28,22 16,30 4,22 4,10" fill="none" stroke="#f59e0b" strokeWidth="1.5"/>
              <polygon points="16,8 22,12 22,20 16,24 10,20 10,12" fill="#f59e0b20" stroke="#f59e0b" strokeWidth="0.8"/>
            </svg>
          </div>
          <span className="font-mono text-xl font-bold tracking-wide">
            Limitless <span className="text-geo-amber">AI</span>
          </span>
        </div>
        <div className="hidden md:flex gap-8 text-sm font-mono text-geo-dim">
          <span className="hover:text-geo-amber cursor-pointer transition-colors">Platform</span>
          <span className="hover:text-geo-amber cursor-pointer transition-colors">Pricing</span>
          <span className="hover:text-geo-amber cursor-pointer transition-colors">About</span>
        </div>
        <button className="text-xs font-mono border border-geo-amber/40 text-geo-amber hover:bg-geo-amber/10 px-4 py-2 rounded transition-all">
          Join Waitlist
        </button>
      </motion.nav>

      {/* Hero Section */}
      <main className="relative z-10 max-w-7xl mx-auto px-6 pt-32 pb-24 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20, filter: 'blur(10px)' }}
          animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="space-y-6 max-w-4xl mx-auto"
        >
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-geo-text">
            Automate Your <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-geo-amber to-geo-teal">
              Professional Life
            </span>
          </h1>
          <p className="text-lg md:text-xl text-geo-muted max-w-2xl mx-auto font-light leading-relaxed">
            Limitless AI provides an interconnected ecosystem of intelligent agents 
            designed to scale your career, operations, and outreach. 
          </p>
        </motion.div>

        {/* Modules Grid */}
        <div className="mt-32 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 text-left max-w-5xl mx-auto">
          
          {/* ApplyWithAI Module (The Real One) */}
          <Link to="/applywithai" className="block focus:outline-none">
            <motion.div 
              custom={0}
              variants={moduleVariants}
              initial="hidden"
              animate="visible"
              whileHover={{ y: -8, scale: 1.02 }}
              className="h-full geo-card border border-geo-teal/30 hover:border-geo-teal p-8 relative overflow-hidden group cursor-pointer"
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-geo-teal/10 rounded-bl-full translate-x-16 -translate-y-16 group-hover:scale-150 transition-transform duration-500 ease-out" />
              <div className="relative z-10">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-lg bg-geo-teal/10 flex items-center justify-center text-geo-teal">
                    <svg width="20" height="20" viewBox="0 0 32 32">
                      <polygon points="16,2 28,10 28,22 16,30 4,22 4,10" fill="none" stroke="currentColor" strokeWidth="1.5"/>
                    </svg>
                  </div>
                  <h3 className="font-mono text-xl font-bold text-geo-text group-hover:text-geo-teal transition-colors">ApplyWithAI</h3>
                </div>
                <p className="text-sm text-geo-muted leading-relaxed font-light mb-6">
                  Automated cold emailing, job scraping, and intelligent LaTeX resume tailoring to maximize your callback rates.
                </p>
                <div className="flex items-center gap-2 text-xs font-mono text-geo-teal">
                  <span className="geo-badge-teal px-2 py-0.5 rounded">Live Now</span>
                  <span className="opacity-0 group-hover:opacity-100 transition-opacity ml-auto">Launch Module →</span>
                </div>
              </div>
            </motion.div>
          </Link>

          {/* ConnectWithAI Module (Mock) */}
          <motion.div 
            custom={1}
            variants={moduleVariants}
            initial="hidden"
            animate="visible"
            className="h-full geo-card border border-geo-void p-8 opacity-70 grayscale hover:grayscale-0 transition-all duration-500"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-geo-void flex items-center justify-center text-geo-dim">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M16 21v-2a4 4 0 0 0-4-4H5c-1.1 0-2 .9-2 2v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/></svg>
              </div>
              <h3 className="font-mono text-xl font-bold text-geo-dim">NetworkAI</h3>
            </div>
            <p className="text-sm text-geo-dim leading-relaxed font-light mb-6">
              Autonomous relationship management. Auto-generates follow-ups and CRM notes based on your interactions.
            </p>
            <div className="text-xs font-mono text-geo-dim">
              Coming in Q3
            </div>
          </motion.div>

          {/* SourceWithAI Module (Mock) */}
          <motion.div 
            custom={2}
            variants={moduleVariants}
            initial="hidden"
            animate="visible"
            className="h-full geo-card border border-geo-void p-8 opacity-70 grayscale hover:grayscale-0 transition-all duration-500"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-geo-void flex items-center justify-center text-geo-dim">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              </div>
              <h3 className="font-mono text-xl font-bold text-geo-dim">SourceAI</h3>
            </div>
            <p className="text-sm text-geo-dim leading-relaxed font-light mb-6">
              Intelligent applicant screening and talent discovery. Built for recruiters to analyze massive pools of resumes.
            </p>
            <div className="text-xs font-mono text-geo-dim">
              Coming in Q4
            </div>
          </motion.div>

        </div>
      </main>
    </div>
  );
}
