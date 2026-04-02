import React from 'react';
import { motion } from 'framer-motion';
import {
  Activity,
  CalendarDays,
  CloudSun,
  Database,
  ChevronRight,
  BarChart3,
  Zap,
  Shield,
} from 'lucide-react';

interface LandingPageProps {
  onLaunch: () => void;
}

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.15, duration: 0.6, ease: [0.16, 1, 0.3, 1] as any },
  }),
};

const scaleIn = {
  hidden: { opacity: 0, scale: 0.9 },
  visible: (i: number) => ({
    opacity: 1,
    scale: 1,
    transition: { delay: 0.4 + i * 0.12, duration: 0.5, ease: [0.16, 1, 0.3, 1] as any },
  }),
};

const FEATURES = [
  {
    icon: Activity,
    title: 'Position Intelligence',
    description: 'Schema-validated analytics across QB, RB, WR, TE, K, and DST — built on verified FantasyPros data.',
    accent: 'from-blue-500/20 to-cyan-500/10',
    iconColor: 'text-blue-400',
  },
  {
    icon: CalendarDays,
    title: 'Weekly Drill-Down',
    description: 'Game-by-game breakdowns with weekly targets, receptions, and yardage for receiving positions.',
    accent: 'from-violet-500/20 to-purple-500/10',
    iconColor: 'text-violet-400',
  },
  {
    icon: CloudSun,
    title: 'Stadium & Weather Context',
    description: 'Enriched matchup data: opponent, venue type, surface, elevation, temperature, humidity, and wind.',
    accent: 'from-emerald-500/20 to-green-500/10',
    iconColor: 'text-emerald-400',
  },
] as const;

const STATS = [
  { value: '6', label: 'Positions', icon: Shield },
  { value: '2020–25', label: 'Coverage', icon: CalendarDays },
  { value: 'DuckDB', label: 'Engine', icon: Database },
  { value: '< 50ms', label: 'Query Time', icon: Zap },
] as const;

export const LandingPage: React.FC<LandingPageProps> = ({ onLaunch }) => {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 overflow-hidden relative">
      {/* Background gradient orbs */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full bg-blue-600/8 blur-[120px]" />
        <div className="absolute bottom-[-15%] right-[-5%] w-[500px] h-[500px] rounded-full bg-violet-600/6 blur-[100px]" />
        <div className="absolute top-[40%] right-[20%] w-[300px] h-[300px] rounded-full bg-cyan-500/4 blur-[80px]" />
      </div>

      {/* Nav */}
      <motion.nav
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-10 flex items-center justify-between px-8 py-6 max-w-7xl mx-auto"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center shadow-lg shadow-blue-500/25">
            <BarChart3 className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold tracking-tight">
            NFLStats<span className="text-blue-400">PRO</span>
          </span>
        </div>
        <button
          onClick={onLaunch}
          className="px-5 py-2.5 text-sm font-semibold text-slate-300 border border-slate-700/60 rounded-xl hover:bg-slate-800/60 hover:text-white hover:border-slate-600 transition-all duration-200"
        >
          Sign In
        </button>
      </motion.nav>

      {/* Hero */}
      <section className="relative z-10 max-w-7xl mx-auto px-8 pt-20 pb-24 text-center">
        <motion.div
          custom={0}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          className="inline-flex items-center gap-2 px-4 py-1.5 mb-8 rounded-full border border-slate-700/50 bg-slate-900/50 text-sm text-slate-400"
        >
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          2025 Season Data Live
        </motion.div>

        <motion.h1
          custom={1}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          className="text-6xl md:text-7xl lg:text-8xl font-extrabold tracking-tight leading-[0.95] mb-6"
        >
          <span className="bg-gradient-to-b from-white via-slate-200 to-slate-500 bg-clip-text text-transparent">
            NFL Analytics
          </span>
          <br />
          <span className="bg-gradient-to-r from-blue-400 via-blue-500 to-violet-500 bg-clip-text text-transparent">
            Engine
          </span>
        </motion.h1>

        <motion.p
          custom={2}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto mb-12 leading-relaxed"
        >
          Production-grade fantasy analytics powered by DuckDB. Schema-validated pipelines,
          enriched matchup metadata, and position-specific intelligence across six years of NFL data.
        </motion.p>

        <motion.div
          custom={3}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          className="flex items-center justify-center gap-4"
        >
          <button
            onClick={onLaunch}
            className="group relative px-8 py-4 bg-gradient-to-r from-blue-600 to-blue-500 text-white font-bold rounded-2xl shadow-2xl shadow-blue-500/25 hover:shadow-blue-500/40 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 flex items-center gap-3 text-lg"
          >
            Launch Dashboard
            <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </button>
        </motion.div>
      </section>

      {/* Features */}
      <section className="relative z-10 max-w-7xl mx-auto px-8 pb-24">
        <div className="grid md:grid-cols-3 gap-6">
          {FEATURES.map((feature, i) => (
            <motion.div
              key={feature.title}
              custom={i}
              variants={scaleIn}
              initial="hidden"
              animate="visible"
              className="group relative p-8 rounded-2xl border border-slate-800/60 bg-slate-900/30 backdrop-blur-sm hover:border-slate-700/80 hover:bg-slate-900/50 transition-all duration-300"
            >
              <div className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${feature.accent} opacity-0 group-hover:opacity-100 transition-opacity duration-300`} />
              <div className="relative z-10">
                <div className={`w-12 h-12 rounded-xl bg-slate-800/80 border border-slate-700/50 flex items-center justify-center mb-5 ${feature.iconColor} group-hover:scale-110 transition-transform`}>
                  <feature.icon className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-bold mb-3 text-slate-100">{feature.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{feature.description}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Stats Bar */}
      <section className="relative z-10 max-w-5xl mx-auto px-8 pb-32">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9, duration: 0.6 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-4"
        >
          {STATS.map((stat) => (
            <div
              key={stat.label}
              className="flex items-center gap-4 p-5 rounded-2xl border border-slate-800/40 bg-slate-900/20"
            >
              <div className="w-10 h-10 rounded-lg bg-slate-800/60 flex items-center justify-center text-slate-500">
                <stat.icon className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xl font-bold text-slate-100">{stat.value}</div>
                <div className="text-xs text-slate-500 font-medium uppercase tracking-wider">{stat.label}</div>
              </div>
            </div>
          ))}
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-slate-800/40 py-8 text-center text-sm text-slate-600">
        &copy; {new Date().getFullYear()} NFLStatsPRO. Schema-validated pipelines. Zero drift.
      </footer>
    </div>
  );
};
