import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Calendar,
  Hash,
  ChevronDown,
  Rows3,
  RotateCcw,
  AlertCircle,
} from 'lucide-react';
import { cn } from '../../utils/cn';
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
  density: GridDensity;
  setDensity: (d: GridDensity) => void;
  onResetFilters?: () => void;
  isLoading?: boolean;
  isError?: boolean;
  onRetry?: () => void;
  /** Table density is Rankings-only. Hidden on Dashboard. */
  showDensity?: boolean;
  /** Rankings row search. Hidden on Insights (filters are year/week/context). */
  showSearch?: boolean;
}

const DENSITY_LABELS: Record<GridDensity, string> = {
  compact: 'Compact',
  standard: 'Standard',
  expert: 'Expert',
};

const DENSITY_SHORT: Record<GridDensity, string> = {
  compact: 'Comp',
  standard: 'Sta',
  expert: 'Exp',
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
  density,
  setDensity,
  onResetFilters,
  isLoading = false,
  isError = false,
  onRetry,
  showDensity = true,
  showSearch = true,
}: ControlBarProps) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3 min-h-14 sm:min-h-16 px-3 sm:px-4 rounded-2xl glass-card border-white/10">
        {showSearch && (
          <div className="relative w-40 sm:w-48 shrink-0 group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 group-focus-within:text-blue-400 transition-colors" aria-hidden />
            <label htmlFor="pem-filter-search" className="sr-only">
              Filter visible rows by player or team
            </label>
            <input
              id="pem-filter-search"
              type="search"
              placeholder="Filter visible rows…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950/40 border border-white/[0.04] rounded-xl h-9 py-1.5 !pl-10 pr-3 text-[11px] font-medium leading-none focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50 focus:border-blue-500/30 transition-all placeholder:text-slate-500"
            />
          </div>
        )}

        <div className="flex items-center gap-2 sm:gap-3 flex-wrap shrink-0">
          <div
            className="flex items-center gap-0.5 bg-slate-950/60 p-0.5 rounded-xl border border-white/[0.04] shadow-inner shadow-black/20"
            role="group"
            aria-label="Time grain"
          >
            {(['season', 'weekly'] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                aria-pressed={viewMode === mode}
                onClick={() => setViewMode(mode)}
                className={cn(
                  'relative inline-flex items-center justify-center h-8 min-w-[3.75rem] px-3 rounded-lg text-[11px] font-semibold leading-none whitespace-nowrap transition-all duration-200',
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
                  {mode === 'season' ? 'Season' : 'Weekly'}
                </span>
              </button>
            ))}
          </div>

          <div className="w-px h-6 bg-white/[0.04] hidden sm:block" />

          <div className="flex items-center gap-1.5 h-9 bg-slate-950/40 pl-2.5 pr-2 rounded-xl border border-white/[0.04] group hover:border-slate-700/50 transition-colors relative">
            <Calendar className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-400 transition-colors shrink-0" aria-hidden />
            <div className="relative flex items-center">
              <label htmlFor="pem-filter-year" className="sr-only">
                Season year
              </label>
              <select
                id="pem-filter-year"
                aria-label="Season year"
                value={selectedYear}
                onChange={(e) => setSelectedYear(e.target.value)}
                disabled={availableYears.length === 0}
                className="bg-transparent min-w-[6.5rem] text-[11px] font-semibold leading-none text-slate-300 outline-none cursor-pointer py-1 pr-5 appearance-none z-10 disabled:opacity-50"
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
                <div className="flex items-center gap-1.5 h-9 bg-slate-950/40 pl-2.5 pr-2 rounded-xl border border-white/[0.04] group hover:border-slate-700/50 transition-colors relative">
                  <Hash className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-400 transition-colors shrink-0" aria-hidden />
                  <div className="relative flex items-center">
                    <label htmlFor="pem-filter-week" className="sr-only">
                      Week number
                    </label>
                    <select
                      id="pem-filter-week"
                      aria-label="Week number"
                      value={selectedWeek}
                      onChange={(e) => setSelectedWeek(e.target.value)}
                      disabled={availableWeeks.length === 0}
                      className="bg-transparent min-w-[4.75rem] text-[11px] font-semibold leading-none text-slate-300 outline-none cursor-pointer py-1 pr-5 appearance-none z-10 disabled:opacity-50"
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

          {onResetFilters && (
            <button
              type="button"
              onClick={onResetFilters}
              className="inline-flex items-center gap-1.5 h-9 px-3 rounded-xl border border-white/[0.06] bg-slate-950/40 text-[11px] font-semibold leading-none text-slate-400 hover:text-white hover:border-slate-600 transition-colors"
              aria-label="Reset filters"
            >
              <RotateCcw className="w-3.5 h-3.5" aria-hidden />
              Reset
            </button>
          )}
        </div>

        {showDensity && (
          <div className="flex items-center gap-1.5 h-9 bg-slate-950/40 pl-2 pr-1 rounded-xl border border-white/[0.04] group hover:border-slate-700/50 transition-colors shrink-0">
            <Rows3 className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-400 transition-colors shrink-0" aria-hidden />
            <div className="flex items-center gap-0.5 bg-slate-950/80 p-0.5 rounded-lg" role="group" aria-label="View mode">
              {(['compact', 'standard', 'expert'] as const).map((d) => (
                <button
                  key={d}
                  type="button"
                  aria-pressed={density === d}
                  onClick={() => setDensity(d)}
                  className={cn(
                    'inline-flex items-center justify-center h-7 min-w-[2.25rem] px-2.5 text-[10px] font-semibold leading-none whitespace-nowrap rounded-md transition-colors',
                    density === d
                      ? 'bg-blue-600 text-white shadow shadow-blue-500/20'
                      : 'text-slate-500 hover:text-slate-300',
                  )}
                  title={`${DENSITY_LABELS[d]} density`}
                >
                  {DENSITY_SHORT[d]}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {isError && (
        <div className="flex flex-wrap items-center justify-between gap-2 px-1">
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
        </div>
      )}
    </div>
  );
}
