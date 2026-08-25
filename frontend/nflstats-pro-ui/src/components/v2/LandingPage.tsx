import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  BarChart3,
  LayoutDashboard,
  UserSearch,
  ChevronRight,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { LoginModal } from './Auth/LoginModal';

interface LandingPageProps {
  onLaunch: () => void;
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.3,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] },
  },
};

const EXPLORE = [
  {
    icon: BarChart3,
    title: 'Rankings',
    description: 'Seasonal and weekly leaderboards for QB, RB, WR, TE, K, and DST.',
    color: 'text-sky-400',
  },
  {
    icon: LayoutDashboard,
    title: 'Dashboard',
    description: 'Charts for the same season, week, and position filters you use on rankings.',
    color: 'text-emerald-400',
  },
  {
    icon: UserSearch,
    title: 'Player',
    description: 'Open a player to see weekly trends and situational splits.',
    color: 'text-amber-400',
  },
];

function displayName(email: string): string {
  const local = email.split('@')[0];
  return local || email;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onLaunch }) => {
  const { user, token } = useAuth();
  const [showLogin, setShowLogin] = useState(false);

  const signedIn = Boolean(user);
  const primaryLabel = user
    ? `Continue as ${displayName(user.email)}`
    : 'Continue as Guest';

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-[#020617] relative overflow-hidden px-6 text-center">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-sky-500/10 blur-[120px] rounded-full pointer-events-none" />

      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="relative z-10 flex flex-col items-center max-w-4xl"
      >
        <motion.div
          variants={itemVariants}
          className="flex items-center gap-3 px-4 py-2 rounded-full border border-slate-800 bg-slate-900/50 mb-12"
        >
          <BarChart3 size={18} className="text-sky-400" />
          <span className="text-xs font-bold tracking-[0.2em] uppercase text-slate-400">
            PEM Sports
          </span>
        </motion.div>

        <motion.h1
          variants={itemVariants}
          className="text-4xl sm:text-6xl md:text-7xl font-black tracking-tight leading-[0.95] text-white mb-6"
        >
          NFL fantasy rankings
          <span className="block text-sky-500 mt-2">and player analytics</span>
        </motion.h1>

        <motion.p
          variants={itemVariants}
          className="text-base md:text-xl text-slate-400 mb-10 max-w-2xl leading-relaxed"
        >
          Explore seasonal and weekly leaderboards, then open any player for trends
          and matchup splits. No account required.
        </motion.p>

        <motion.div
          variants={itemVariants}
          className="flex flex-col sm:flex-row items-center gap-3 sm:gap-4"
        >
          <button
            type="button"
            onClick={onLaunch}
            className="group relative px-10 py-5 bg-sky-500 rounded-2xl text-white font-black tracking-widest uppercase text-sm shadow-[0_20px_40px_rgba(56,189,248,0.3)] hover:shadow-[0_25px_50px_rgba(56,189,248,0.4)] transition-all flex items-center gap-3 focus-visible:ring-2 focus-visible:ring-sky-300"
          >
            {primaryLabel}
            <ChevronRight size={18} className="group-hover:translate-x-1 transition-transform" />
          </button>
          {!signedIn && (
            <button
              type="button"
              onClick={() => setShowLogin(true)}
              className="px-8 py-4 rounded-2xl border border-white/15 bg-slate-900/50 text-slate-200 font-bold tracking-wider uppercase text-sm hover:border-slate-500 hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-sky-500/50"
            >
              Sign In
            </button>
          )}
        </motion.div>

        <motion.p
          variants={itemVariants}
          className="mt-5 max-w-lg text-sm text-slate-500 leading-relaxed"
        >
          {token && !user
            ? 'Checking your session. You can continue as a guest now — sign in is optional and does not change rankings data.'
            : 'Sign in is optional. It does not change the rankings or analytics you can view.'}
        </motion.p>

        <motion.div
          variants={itemVariants}
          className="grid md:grid-cols-3 gap-8 mt-20 text-left"
        >
          {EXPLORE.map((item) => (
            <div
              key={item.title}
              className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800/50 backdrop-blur-xl transition-colors hover:border-slate-700"
            >
              <item.icon className={`${item.color} mb-4`} size={24} aria-hidden />
              <h2 className="text-white font-bold mb-2 uppercase tracking-wide">
                {item.title}
              </h2>
              <p className="text-slate-500 text-sm leading-relaxed">{item.description}</p>
            </div>
          ))}
        </motion.div>
      </motion.div>

      <motion.footer
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.2 }}
        className="absolute bottom-8 text-[10px] font-bold text-slate-600 tracking-[0.25em] uppercase"
      >
        PEM Sports &copy; 2026
      </motion.footer>

      {showLogin && (
        <LoginModal
          onClose={() => setShowLogin(false)}
          onSuccess={onLaunch}
        />
      )}
    </div>
  );
};
