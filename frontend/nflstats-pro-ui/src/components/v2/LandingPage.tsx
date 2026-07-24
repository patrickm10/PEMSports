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
    transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] }
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
    <div className="flex flex-col items-center justify-center min-h-screen bg-[#020617] relative overflow-hidden px-6 text-center">
      {/* Decorative Glows */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-sky-500/10 blur-[120px] rounded-full pointer-events-none" />
      
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="relative z-10 flex flex-col items-center max-w-4xl"
      >
        {/* Logo Badge */}
        <motion.div 
          variants={itemVariants}
          className="flex items-center gap-3 px-4 py-2 rounded-full border border-slate-800 bg-slate-900/50 mb-12"
        >
          <BarChart3 size={18} className="text-sky-400" />
          <span className="text-xs font-bold tracking-[0.2em] uppercase text-slate-400">PEM Sports</span>
        </motion.div>

        {/* Hero Title */}
        <motion.h1 
          variants={itemVariants}
          className="text-6xl md:text-8xl font-black tracking-tight leading-[0.9] text-white italic mb-8"
        >
          ANALYTICS <span className="text-sky-500">REDEFINED</span>
        </motion.h1>

        {/* Hero Subtitle */}
        <motion.p 
          variants={itemVariants}
          className="text-lg md:text-xl text-slate-400 mb-12 max-w-2xl leading-relaxed"
        >
          PEM Sports fantasy analytics — seasonal and weekly rankings across every supported season,
          powered by a DuckDB analytical kernel.
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
          className="grid md:grid-cols-3 gap-8 mt-24 text-left"
        >
          {FEATURES.map((feature) => (
            <div key={feature.title} className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800/50 backdrop-blur-xl transition-colors hover:border-slate-700">
              <feature.icon className={`${feature.color} mb-4`} size={24} />
              <h3 className="text-white font-bold mb-2 uppercase tracking-wide">{feature.title}</h3>
              <p className="text-slate-500 text-sm leading-relaxed">{feature.description}</p>
            </div>
          ))}
        </motion.div>
      </motion.div>

      {/* Footer Branding */}
      <motion.footer 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2 }}
        className="absolute bottom-10 text-[10px] font-bold text-slate-600 tracking-[0.4em] uppercase"
      >
        Verified Analytical Kernel &copy; 2026
      </motion.footer>
    </div>
  );
};
