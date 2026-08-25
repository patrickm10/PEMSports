import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  BarChart3,
  LayoutDashboard,
  UserSearch,
  ChevronRight,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { sessionStatusCopy } from '../../utils/authSession';
import { LoginModal } from './Auth/LoginModal';

interface LandingPageProps {
  onLaunch: () => void;
}

const EXPLORE = [
  {
    icon: BarChart3,
    title: 'Rankings',
    description: 'Season and weekly leaderboards by position.',
  },
  {
    icon: LayoutDashboard,
    title: 'Dashboard',
    description: 'Top-10 and matchup splits from the same filters.',
  },
  {
    icon: UserSearch,
    title: 'Player',
    description: 'Weekly trends, opponents, stadium, and surface.',
  },
];

function displayName(email: string): string {
  const local = email.split('@')[0];
  return local || email;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onLaunch }) => {
  const { user, isLoading } = useAuth();
  const [showLogin, setShowLogin] = useState(false);

  const signedIn = Boolean(user);
  const primaryLabel = user
    ? `Continue as ${displayName(user.email)}`
    : 'Enter the rankings';

  return (
    <div className="relative min-h-screen bg-[#020617] overflow-hidden text-left">
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.11]"
        style={{
          backgroundImage:
            'repeating-linear-gradient(90deg, transparent 0, transparent 47px, rgba(56,189,248,0.22) 47px, rgba(56,189,248,0.22) 48px), repeating-linear-gradient(0deg, transparent 0, transparent 79px, rgba(148,163,184,0.12) 79px, rgba(148,163,184,0.12) 80px)',
        }}
      />
      <div className="pointer-events-none absolute -top-24 left-1/4 h-[420px] w-[420px] rounded-full bg-sky-500/15 blur-[120px]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[320px] w-[320px] rounded-full bg-emerald-500/10 blur-[100px]" />

      <div className="relative z-10 mx-auto flex min-h-screen max-w-6xl flex-col justify-center gap-12 px-6 py-16 lg:flex-row lg:items-center lg:gap-20">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="max-w-xl"
        >
          <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
            <span className="text-[11px] font-bold uppercase tracking-[0.22em] text-sky-300">
              PEM Sports
            </span>
          </div>

          <h1 className="text-4xl font-black tracking-tight text-white sm:text-5xl lg:text-6xl leading-[1.05]">
            See who is actually
            <span className="mt-1 block text-sky-400">winning their position.</span>
          </h1>

          <p className="mt-6 max-w-lg text-base leading-relaxed text-slate-400 sm:text-lg">
            Fantasy rankings and player splits for QB, RB, WR, TE, K, and DST.
            Open the board as a guest — an account is optional.
          </p>

          <div className="mt-10 flex flex-col gap-3 sm:flex-row sm:items-center">
            <button
              type="button"
              onClick={onLaunch}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-sky-500 px-7 py-3.5 text-sm font-bold uppercase tracking-wider text-white shadow-[0_16px_40px_rgba(56,189,248,0.28)] transition-colors hover:bg-sky-400 focus-visible:ring-2 focus-visible:ring-sky-200"
            >
              {primaryLabel}
              <ChevronRight size={16} aria-hidden />
            </button>
            {!signedIn && (
              <button
                type="button"
                onClick={() => setShowLogin(true)}
                className="inline-flex min-h-11 items-center justify-center rounded-xl border border-white/15 bg-white/[0.03] px-7 py-3.5 text-sm font-bold uppercase tracking-wider text-slate-200 transition-colors hover:border-sky-500/40 hover:text-white focus-visible:ring-2 focus-visible:ring-sky-500/50"
              >
                Sign in
              </button>
            )}
          </div>

          <p className="mt-4 text-sm text-slate-500">
            {sessionStatusCopy(isLoading, signedIn)}
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.08, ease: [0.16, 1, 0.3, 1] }}
          className="w-full max-w-md"
        >
          <div className="overflow-hidden rounded-2xl border border-white/10 bg-slate-950/70 shadow-2xl shadow-black/40 backdrop-blur-xl">
            <div className="border-b border-white/[0.06] px-5 py-3">
              <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-500">
                What you can open
              </p>
            </div>
            <ul>
              {EXPLORE.map((item, i) => (
                <li
                  key={item.title}
                  className={
                    i < EXPLORE.length - 1
                      ? 'border-b border-white/[0.06]'
                      : undefined
                  }
                >
                  <div className="flex gap-4 px-5 py-4">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-sky-500/10 text-sky-400">
                      <item.icon size={18} aria-hidden />
                    </div>
                    <div>
                      <h2 className="text-sm font-bold text-white">{item.title}</h2>
                      <p className="mt-1 text-sm leading-relaxed text-slate-400">
                        {item.description}
                      </p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </motion.div>
      </div>

      {showLogin && (
        <LoginModal
          onClose={() => setShowLogin(false)}
          onSuccess={onLaunch}
          onContinueAsGuest={onLaunch}
        />
      )}
    </div>
  );
};
