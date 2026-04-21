import React from 'react';
import { motion } from 'framer-motion';
import {
  Activity,
  CloudSun,
  Database,
  ChevronRight,
  BarChart3,
} from 'lucide-react';


interface LandingPageProps {
  onLaunch: () => void;
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.3
    }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: { 
    opacity: 1, 
    y: 0, 
    transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] as any } 
  }

};

const FEATURES = [
  {
    icon: Activity,
    title: 'Position Intelligence',
    description: 'Schema-validated analytics across QB, RB, WR, TE, K, and DST.',
    color: 'text-sky-400'
  },
  {
    icon: Database,
    title: 'Analytical Kernel',
    description: 'High-performance DuckDB processing with < 50ms query latency.',
    color: 'text-emerald-400'
  },
  {
    icon: CloudSun,
    title: 'Enriched Insights',
    description: 'Stadium, weather, and elevation data for precise situational split analysis.',
    color: 'text-amber-400'
  }
];

export const LandingPage: React.FC<LandingPageProps> = ({ onLaunch }) => {
  return (
    <div className="relative flex min-h-screen flex-col items-center overflow-x-hidden bg-[#020617] px-6 pb-32 pt-16 text-center sm:px-8 sm:pb-40 sm:pt-20">
      {/* Decorative Glows */}
      <div className="pointer-events-none absolute left-1/2 top-[12%] h-[400px] w-[min(800px,110vw)] -translate-x-1/2 rounded-full bg-sky-500/10 blur-[120px]" />
      
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="relative z-10 flex w-full max-w-4xl flex-col items-center"
      >
        {/* Logo Badge */}
        <motion.div 
          variants={itemVariants}
          className="flex items-center gap-3 px-4 py-2 rounded-full border border-slate-800 bg-slate-900/50 mb-12"
        >
          <BarChart3 size={18} className="text-sky-400" />
          <span className="text-xs font-bold tracking-[0.2em] uppercase text-slate-400">NFLStatsPro V3</span>
        </motion.div>

        {/* Hero Title */}
        <motion.h1 
          variants={itemVariants}
          className="mb-8 text-center text-5xl font-black italic leading-[1.02] tracking-tight text-white sm:text-6xl md:text-8xl md:leading-[0.95]"
        >
          ANALYTICS <span className="text-sky-500">REDEFINED</span>
        </motion.h1>

        {/* Hero Subtitle */}
        <motion.p 
          variants={itemVariants}
          className="mb-12 max-w-2xl px-1 text-center text-base leading-relaxed text-slate-400 sm:text-lg md:text-xl"
        >
          The world's most advanced NFL data exploration suite. 
          Harness the power of DuckDB to visualize high-density performance metrics in real-time.
        </motion.p>

        {/* Launch Button */}
        <motion.button
          variants={itemVariants}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.98 }}
          onClick={onLaunch}
          className="group relative px-10 py-5 bg-sky-500 rounded-2xl text-white font-black tracking-widest uppercase text-sm shadow-[0_20px_40px_rgba(56,189,248,0.3)] hover:shadow-[0_25px_50px_rgba(56,189,248,0.4)] transition-all flex items-center gap-3"
        >
          Launch Analysis Desk
          <ChevronRight size={18} className="group-hover:translate-x-1 transition-transform" />
        </motion.button>

        {/* Features Grid */}
        <motion.div 
          variants={itemVariants}
          className="mt-20 grid w-full max-w-5xl gap-8 sm:mt-24 md:grid-cols-3 md:gap-6 lg:gap-8"
        >
          {FEATURES.map((feature) => (
            <div
              key={feature.title}
              className="flex flex-col items-center rounded-2xl border border-slate-800/50 bg-slate-900/40 p-7 text-center backdrop-blur-xl transition-colors hover:border-slate-700 sm:p-8"
            >
              <feature.icon className={`${feature.color} mb-4 shrink-0`} size={24} aria-hidden />
              <h3 className="mb-2 text-center text-sm font-bold uppercase tracking-wide text-white sm:text-base">
                {feature.title}
              </h3>
              <p className="text-center text-sm leading-relaxed text-slate-500">{feature.description}</p>
            </div>
          ))}
        </motion.div>
      </motion.div>

      {/* Footer Branding */}
      <motion.footer 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2 }}
        className="pointer-events-none mt-auto w-full px-4 pb-8 pt-12 text-center text-[10px] font-bold uppercase tracking-[0.35em] text-slate-600 sm:absolute sm:bottom-8 sm:left-0 sm:pb-0 sm:pt-0"
      >
        Verified Analytical Kernel &copy; 2025
      </motion.footer>
    </div>
  );
};
