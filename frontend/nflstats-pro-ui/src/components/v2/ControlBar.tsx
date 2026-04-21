import { useState, forwardRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Calendar, Hash, Users, User, LogOut, ChevronDown, Rows3 } from 'lucide-react';
import { cn } from '../../utils/cn';
import { useAuth } from '../../contexts/AuthContext';
import { LoginModal } from './Auth/LoginModal';
import type { GridDensity } from '../VirtualizedGrid';

interface ControlBarProps {
  viewMode: 'season' | 'weekly';
  setViewMode: (mode: 'season' | 'weekly') => void;
  selectedYear: string;
  setSelectedYear: (year: string) => void;
  availableYears: number[];
  selectedWeek: string;
  setSelectedWeek: (week: string) => void;
  availableWeeks: number[];
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  totalPlayers?: number;
  density: GridDensity;
  setDensity: (d: GridDensity) => void;
}

const DENSITY_LABELS: Record<GridDensity, string> = {
  compact: 'Compact',
  standard: 'Standard',
  expert: 'Expert',
};

export const ControlBar = forwardRef<HTMLInputElement, ControlBarProps>(function ControlBar(
  {
    viewMode, setViewMode, selectedYear, setSelectedYear, availableYears,
    selectedWeek, setSelectedWeek, availableWeeks, searchQuery, setSearchQuery,
    totalPlayers, density, setDensity,
  },
  ref,
) {
  const { user, logout } = useAuth();
  const [showLogin, setShowLogin] = useState(false);

  return (
    <div className="flex flex-wrap items-center justify-between gap-4 p-5 rounded-2xl glass-card border-white/10">
      <div className="flex items-center gap-3 flex-wrap">
        {/* View Toggle */}
        <div className="flex bg-slate-950/60 p-1 rounded-xl border border-white/[0.04] shadow-inner shadow-black/20">
          {(['season', 'weekly'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={cn(
                "relative px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all duration-200",
                viewMode === mode
                  ? "text-white"
                  : "text-slate-500 hover:text-slate-300"
              )}
            >
              {viewMode === mode && (
                <motion.div
                  layoutId="viewToggle"
                  className="absolute inset-0 bg-blue-600 rounded-lg shadow-lg shadow-blue-500/20"
                  transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                />
              )}
              <span className="relative z-10">{mode === 'season' ? 'Seasonal' : 'Weekly'}</span>
            </button>
          ))}
        </div>

        {/* Separator */}
        <div className="w-px h-6 bg-white/[0.04] mx-1 hidden sm:block" />

        {/* Year Select */}
        <div className="flex items-center gap-2 bg-slate-950/40 pl-3 pr-2 py-1.5 rounded-xl border border-white/[0.04] group hover:border-slate-700/50 transition-colors relative">
          <Calendar className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-400 transition-colors" />
          <div className="relative flex items-center pr-1">
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(e.target.value)}
              className="bg-transparent text-xs font-bold text-slate-300 outline-none cursor-pointer py-1 pr-6 appearance-none z-10"
            >
              {availableYears.map(year => (
                <option key={year} value={year.toString()} className="bg-slate-900 text-slate-200">{year}</option>
              ))}
            </select>
            <ChevronDown className="absolute right-0 w-3 h-3 text-slate-500 pointer-events-none group-hover:text-slate-400 transition-colors" />
          </div>
        </div>

        {/* Week Select (Conditional) */}
        <AnimatePresence>
          {viewMode === 'weekly' && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95, width: 0 }}
              animate={{ opacity: 1, scale: 1, width: 'auto' }}
              exit={{ opacity: 0, scale: 0.95, width: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="flex items-center gap-2 bg-slate-950/40 pl-3 pr-2 py-1.5 rounded-xl border border-white/[0.04] group hover:border-slate-700/50 transition-colors relative">
                <Hash className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-400 transition-colors" />
                <div className="relative flex items-center pr-1">
                  <select
                    value={selectedWeek}
                    onChange={(e) => setSelectedWeek(e.target.value)}
                    className="bg-transparent text-xs font-bold text-slate-300 outline-none cursor-pointer py-1 pr-6 appearance-none z-10"
                  >
                    {availableWeeks.map(week => (
                      <option key={week} value={week.toString()} className="bg-slate-900 text-slate-200">Wk {week}</option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-0 w-3 h-3 text-slate-500 pointer-events-none group-hover:text-slate-400 transition-colors" />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Player Count Badge */}
        {totalPlayers !== undefined && totalPlayers > 0 && (
          <>
            <div className="w-px h-6 bg-white/[0.04] mx-1 hidden lg:block" />
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/30 border border-white/[0.04] text-xs text-slate-500">
              <Users className="w-3.5 h-3.5" />
              <span className="font-semibold text-slate-400">{totalPlayers}</span>
              <span>players</span>
            </div>
          </>
        )}

        {/* Density Toggle */}
        <div className="w-px h-6 bg-white/[0.04] mx-1 hidden lg:block" />
        <div className="flex items-center gap-2 bg-slate-950/40 pl-2.5 pr-1.5 py-1 rounded-xl border border-white/[0.04] group hover:border-slate-700/50 transition-colors">
          <Rows3 className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-400 transition-colors" />
          <div className="flex bg-slate-950/80 p-0.5 rounded-lg">
            {(['compact', 'standard', 'expert'] as const).map((d) => (
              <button
                key={d}
                onClick={() => setDensity(d)}
                className={cn(
                  'px-2 py-1 text-[10px] font-bold uppercase tracking-wider rounded-md transition-colors',
                  density === d
                    ? 'bg-blue-600 text-white shadow shadow-blue-500/20'
                    : 'text-slate-500 hover:text-slate-300',
                )}
                title={`${DENSITY_LABELS[d]} density`}
              >
                {DENSITY_LABELS[d].slice(0, 3)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Search */}
      {/* Search and Auth Context */}
      <div className="flex items-center gap-3 flex-shrink-0 lg:flex-1 max-w-lg justify-end ml-auto">
        <div className="relative flex-1 group min-w-[140px] md:min-w-[200px]">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 group-focus-within:text-blue-400 transition-colors" />
          <input
            ref={ref}
            type="text"
            placeholder="Search players..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950/40 border border-white/[0.04] rounded-xl py-2 pl-10 pr-4 text-xs font-medium focus:outline-none focus:ring-1 focus:ring-blue-500/40 focus:border-blue-500/30 transition-all placeholder:text-slate-600"
          />
        </div>

        {/* User / Login Trigger */}
        {user ? (
          <div className="relative group/auth">
            <button className="flex items-center gap-2 p-1 pl-3 pr-2 rounded-xl bg-slate-950/40 border border-white/[0.04] text-xs font-semibold text-slate-300 hover:text-white transition-colors">
              <span className="truncate max-w-[100px]">{user.email.split('@')[0]}</span>
              <div className="bg-blue-600/20 text-blue-400 p-1.5 rounded-lg">
                <User className="w-3.5 h-3.5" />
              </div>
            </button>
            <div className="absolute right-0 top-full mt-2 w-48 py-1 rounded-xl bg-slate-800 border border-slate-700 shadow-xl opacity-0 invisible group-hover/auth:opacity-100 group-hover/auth:visible transition-all z-20">
              <button
                onClick={logout}
                className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-500 hover:bg-slate-700/50 transition-colors text-left"
              >
                <LogOut className="w-4 h-4" />
                Sign Out
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setShowLogin(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-bold text-white transition-colors shadow-lg shadow-blue-500/20 whitespace-nowrap"
          >
            <User className="w-3.5 h-3.5" />
            Sign In
          </button>
        )}
      </div>

      {showLogin && <LoginModal onClose={() => setShowLogin(false)} />}
    </div>
  );
});
