import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Calendar,
  Hash,
  Users,
  User,
  LogOut,
  ChevronDown,
  Rows3,
  RotateCcw,
  AlertCircle,
} from 'lucide-react';
import { cn } from '../../utils/cn';
import { persistLandingSkip } from '../../utils/filterState';
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
  onResetFilters?: () => void;
  isLoading?: boolean;
  isError?: boolean;
  onRetry?: () => void;
  activeFilterSummary?: string;
  /** Table density is Rankings-only. Hidden on Dashboard. */
  showDensity?: boolean;
}

const DENSITY_LABELS: Record<GridDensity, string> = {
  compact: 'Compact',
  standard: 'Standard',
  expert: 'Expert',
};

export function ControlBar({
  viewMode,
  setViewMode,
  selectedYear,
  setSelectedYear,
  availableYears,
  selectedWeek,
  setSelectedWeek,
  availableWeeks,
  searchQuery,
  setSearchQuery,
  totalPlayers,
  density,
  setDensity,
  onResetFilters,
  isLoading = false,
  isError = false,
  onRetry,
  activeFilterSummary,
  showDensity = true,
}: ControlBarProps) {
  const { user, logout } = useAuth();
  const [showLogin, setShowLogin] = useState(false);
  const [authMenuOpen, setAuthMenuOpen] = useState(false);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 sm:p-5 rounded-2xl glass-card border-white/10">
        <div className="flex items-center gap-3 flex-wrap">
          <div
            className="flex bg-slate-950/60 p-1 rounded-xl border border-white/[0.04] shadow-inner shadow-black/20"
            role="group"
            aria-label="Rankings view mode"
          >
            {(['season', 'weekly'] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                aria-pressed={viewMode === mode}
                onClick={() => setViewMode(mode)}
                className={cn(
                  'relative px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all duration-200',
                  viewMode === mode
                    ? 'text-white'
                    : 'text-slate-500 hover:text-slate-300',
                )}
              >
                {viewMode === mode && (
                  <motion.div
                    layoutId="viewToggle"
                    className="absolute inset-0 bg-blue-600 rounded-lg shadow-lg shadow-blue-500/20"
                    transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                  />
                )}
                <span className="relative z-10">
                  {mode === 'season' ? 'Seasonal' : 'Weekly'}
                </span>
              </button>
            ))}
          </div>

          <div className="w-px h-6 bg-white/[0.04] mx-1 hidden sm:block" />

          <div className="flex items-center gap-2 bg-slate-950/40 pl-3 pr-2 py-1.5 rounded-xl border border-white/[0.04] group hover:border-slate-700/50 transition-colors relative">
            <Calendar className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-400 transition-colors" aria-hidden />
            <div className="relative flex items-center pr-1">
              <label htmlFor="pem-filter-year" className="sr-only">
                Season year
              </label>
              <select
                id="pem-filter-year"
                aria-label="Season year"
                value={selectedYear}
                onChange={(e) => setSelectedYear(e.target.value)}
                disabled={availableYears.length === 0}
                className="bg-transparent text-xs font-bold text-slate-300 outline-none cursor-pointer py-1 pr-6 appearance-none z-10 disabled:opacity-50"
              >
                {availableYears.length === 0 ? (
                  <option value="" className="bg-slate-900 text-slate-200">
                    {isLoading ? 'Loading…' : 'No seasons'}
                  </option>
                ) : (
                  availableYears.map((year) => (
                    <option
                      key={year}
                      value={year.toString()}
                      className="bg-slate-900 text-slate-200"
                    >
                      {year}
                    </option>
                  ))
                )}
              </select>
              <ChevronDown className="absolute right-0 w-3 h-3 text-slate-500 pointer-events-none group-hover:text-slate-400 transition-colors" aria-hidden />
            </div>
          </div>

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
                  <Hash className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-400 transition-colors" aria-hidden />
                  <div className="relative flex items-center pr-1">
                    <label htmlFor="pem-filter-week" className="sr-only">
                      Week number
                    </label>
                    <select
                      id="pem-filter-week"
                      aria-label="Week number"
                      value={selectedWeek}
                      onChange={(e) => setSelectedWeek(e.target.value)}
                      disabled={availableWeeks.length === 0}
                      className="bg-transparent text-xs font-bold text-slate-300 outline-none cursor-pointer py-1 pr-6 appearance-none z-10 disabled:opacity-50"
                    >
                      {availableWeeks.length === 0 ? (
                        <option value="" className="bg-slate-900 text-slate-200">
                          No weeks
                        </option>
                      ) : (
                        availableWeeks.map((week) => (
                          <option
                            key={week}
                            value={week.toString()}
                            className="bg-slate-900 text-slate-200"
                          >
                            Wk {week}
                          </option>
                        ))
                      )}
                    </select>
                    <ChevronDown className="absolute right-0 w-3 h-3 text-slate-500 pointer-events-none group-hover:text-slate-400 transition-colors" aria-hidden />
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {totalPlayers !== undefined && (
            <>
              <div className="w-px h-6 bg-white/[0.04] mx-1 hidden lg:block" />
              <div
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/30 border border-white/[0.04] text-xs text-slate-500"
                aria-live="polite"
              >
                <Users className="w-3.5 h-3.5" aria-hidden />
                <span className="font-semibold text-slate-400">{totalPlayers}</span>
                <span>rows</span>
              </div>
            </>
          )}

          {availableYears.length > 0 && (
            <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-500/10 border border-sky-500/20 text-xs text-sky-300/90">
              <span className="font-semibold">{availableYears.length}</span>
              <span>seasons</span>
            </div>
          )}

          {onResetFilters && (
            <button
              type="button"
              onClick={onResetFilters}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-white/[0.06] bg-slate-950/40 text-xs font-semibold text-slate-400 hover:text-white hover:border-slate-600 transition-colors"
              aria-label="Reset filters"
            >
              <RotateCcw className="w-3.5 h-3.5" aria-hidden />
              Reset
            </button>
          )}

          {showDensity && (
            <>
              <div className="w-px h-6 bg-white/[0.04] mx-1 hidden lg:block" />
              <div className="flex items-center gap-2 bg-slate-950/40 pl-2.5 pr-1.5 py-1 rounded-xl border border-white/[0.04] group hover:border-slate-700/50 transition-colors">
                <Rows3 className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-400 transition-colors" aria-hidden />
                <div className="flex bg-slate-950/80 p-0.5 rounded-lg" role="group" aria-label="Table density">
                  {(['compact', 'standard', 'expert'] as const).map((d) => (
                    <button
                      key={d}
                      type="button"
                      aria-pressed={density === d}
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
            </>
          )}
        </div>

        <div className="flex items-center gap-3 flex-shrink-0 lg:flex-1 max-w-lg justify-end ml-auto">
          <div className="relative flex-1 group min-w-[140px] md:min-w-[200px]">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 group-focus-within:text-blue-400 transition-colors" aria-hidden />
            <label htmlFor="pem-filter-search" className="sr-only">
              Filter visible rows by player or team
            </label>
            <input
              id="pem-filter-search"
              type="search"
              placeholder="Filter visible rows…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950/40 border border-white/[0.04] rounded-xl py-2 pl-10 pr-4 text-xs font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50 focus:border-blue-500/30 transition-all placeholder:text-slate-500"
            />
          </div>

          {user ? (
            <div className="relative">
              <button
                type="button"
                aria-expanded={authMenuOpen}
                aria-haspopup="menu"
                onClick={() => setAuthMenuOpen((o) => !o)}
                onBlur={() => {
                  // Allow menu click before close
                  window.setTimeout(() => setAuthMenuOpen(false), 150);
                }}
                className="flex items-center gap-2 p-1 pl-3 pr-2 rounded-xl bg-slate-950/40 border border-white/[0.04] text-xs font-semibold text-slate-300 hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-blue-500/50"
              >
                <span className="truncate max-w-[100px]">{user.email.split('@')[0]}</span>
                <div className="bg-blue-600/20 text-blue-400 p-1.5 rounded-lg">
                  <User className="w-3.5 h-3.5" aria-hidden />
                </div>
              </button>
              {authMenuOpen && (
                <div
                  role="menu"
                  className="absolute right-0 top-full mt-2 w-48 py-1 rounded-xl bg-slate-800 border border-slate-700 shadow-xl z-20"
                >
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setAuthMenuOpen(false);
                      logout();
                    }}
                    className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-500 hover:bg-slate-700/50 transition-colors text-left"
                  >
                    <LogOut className="w-4 h-4" aria-hidden />
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setShowLogin(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-bold text-white transition-colors shadow-lg shadow-blue-500/20 whitespace-nowrap focus-visible:ring-2 focus-visible:ring-blue-300"
            >
              <User className="w-3.5 h-3.5" aria-hidden />
              Sign In
            </button>
          )}
        </div>

        {showLogin && (
          <LoginModal
            onClose={() => setShowLogin(false)}
            onSuccess={persistLandingSkip}
          />
        )}
      </div>

      {(activeFilterSummary || isError) && (
        <div className="flex flex-wrap items-center justify-between gap-2 px-1">
          {activeFilterSummary && (
            <p className="text-[11px] sm:text-xs font-medium text-slate-400 tracking-wide">
              {activeFilterSummary}
            </p>
          )}
          {isError && (
            <div className="flex items-center gap-2 text-xs text-rose-300" role="alert">
              <AlertCircle className="w-3.5 h-3.5" aria-hidden />
              <span>Failed to load rankings from the API.</span>
              {onRetry && (
                <button
                  type="button"
                  onClick={onRetry}
                  className="underline font-semibold hover:text-white"
                >
                  Retry
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
