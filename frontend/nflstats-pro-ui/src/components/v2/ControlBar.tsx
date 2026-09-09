import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Calendar,
  Hash,
  ChevronDown,
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

const FOCUS =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500/50';

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
    <div className="space-y-2">
      <div
        role="toolbar"
        aria-label="Rankings filters"
        className="flex flex-wrap items-center justify-between gap-2 w-full min-h-8 px-0"
      >
        <div className="flex items-center gap-2 flex-wrap">
          <div
            className="flex items-center gap-0.5 bg-slate-950/60 p-0.5 rounded-lg border border-white/[0.06]"
            role="group"
            aria-label="Season or weekly"
          >
            {(['season', 'weekly'] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                aria-pressed={viewMode === mode}
                onClick={() => setViewMode(mode)}
                className={cn(
                  'relative inline-flex items-center justify-center h-7 min-w-[3.5rem] px-3 rounded-md text-xs font-semibold leading-none whitespace-nowrap transition-all duration-200',
                  FOCUS,
                  viewMode === mode
                    ? 'text-white'
                    : 'text-slate-400 hover:text-slate-200',
                )}
              >
                {viewMode === mode && (
                  <motion.div
                    layoutId="viewToggle"
                    className="absolute inset-0 bg-[var(--accent)] rounded-md shadow-lg shadow-blue-500/20"
                    transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                  />
                )}
                <span className="relative z-10">
                  {mode === 'season' ? 'Season' : 'Weekly'}
                </span>
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1.5 h-8 bg-slate-950/40 pl-2.5 pr-2 rounded-lg border border-white/[0.06]">
            <Calendar className="w-3.5 h-3.5 text-slate-500 shrink-0" aria-hidden />
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
                className={cn(
                  'bg-transparent min-w-[5.5rem] text-xs font-medium leading-none text-slate-300 cursor-pointer py-1 pr-5 appearance-none z-10 disabled:opacity-50',
                  FOCUS,
                )}
              >
                {availableYears.length === 0 ? (
                  <option value="" className="bg-slate-900 text-slate-200">
                    {isLoading ? 'Loading seasons…' : 'No seasons yet'}
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
              <ChevronDown className="absolute right-0 w-3 h-3 text-slate-500 pointer-events-none" aria-hidden />
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
                <div className="flex items-center gap-1.5 h-8 bg-slate-950/40 pl-2.5 pr-2 rounded-lg border border-white/[0.06]">
                  <Hash className="w-3.5 h-3.5 text-slate-500 shrink-0" aria-hidden />
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
                      className={cn(
                        'bg-transparent min-w-[5rem] text-xs font-medium leading-none text-slate-300 cursor-pointer py-1 pr-5 appearance-none z-10 disabled:opacity-50',
                        FOCUS,
                      )}
                    >
                      {availableWeeks.length === 0 ? (
                        <option value="" className="bg-slate-900 text-slate-200">
                          No weeks yet
                        </option>
                      ) : (
                        availableWeeks.map((week) => (
                          <option
                            key={week}
                            value={week.toString()}
                            className="bg-slate-900 text-slate-200"
                          >
                            Week {week}
                          </option>
                        ))
                      )}
                    </select>
                    <ChevronDown className="absolute right-0 w-3 h-3 text-slate-500 pointer-events-none" aria-hidden />
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {onResetFilters && (
            <>
              <div className="w-px h-5 bg-white/[0.07] hidden sm:block" />
              <button
                type="button"
                onClick={onResetFilters}
                className={cn(
                  'inline-flex items-center gap-1.5 h-8 px-2.5 rounded-lg text-xs font-medium leading-none text-slate-400 hover:text-white transition-colors',
                  FOCUS,
                )}
                aria-label="Reset filters"
              >
                <RotateCcw className="w-3.5 h-3.5" aria-hidden />
                Reset filters
              </button>
            </>
          )}
        </div>

        {(showDensity || showSearch) && (
          <div className="flex items-center gap-2 ml-auto flex-wrap">
            {showDensity && (
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-medium text-slate-500">Density</span>
                <div
                  className="flex items-center gap-0.5 bg-slate-950/60 p-0.5 rounded-lg border border-white/[0.06]"
                  role="group"
                  aria-label="Table density"
                >
                  {(['compact', 'standard', 'expert'] as const).map((d) => (
                    <button
                      key={d}
                      type="button"
                      aria-pressed={density === d}
                      aria-label={DENSITY_LABELS[d]}
                      onClick={() => setDensity(d)}
                      className={cn(
                        'inline-flex items-center justify-center h-7 min-w-[4rem] px-2.5 text-xs font-medium leading-none whitespace-nowrap rounded-md transition-colors',
                        FOCUS,
                        density === d
                          ? 'bg-white/[0.09] text-white'
                          : 'text-slate-400 hover:text-slate-200',
                      )}
                      title={`${DENSITY_LABELS[d]} density`}
                    >
                      {DENSITY_LABELS[d]}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {showSearch && (
              <div className="relative w-full max-w-[14rem] group">
                <Search
                  className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 group-focus-within:text-blue-400 transition-colors"
                  aria-hidden
                />
                <label htmlFor="pem-filter-search" className="sr-only">
                  Filter by player or team
                </label>
                <input
                  id="pem-filter-search"
                  type="search"
                  placeholder="Search players or teams"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className={cn(
                    'w-full bg-slate-950/40 rounded-lg h-8 py-1.5 !pl-9 pr-3 text-xs font-medium leading-none placeholder:text-slate-500 border border-white/[0.07]',
                    FOCUS,
                  )}
                />
              </div>
            )}
          </div>
        )}
      </div>

      {isError && (
        <div className="flex flex-wrap items-center justify-between gap-2 px-0">
          <div className="flex items-center gap-2 text-xs text-rose-300" role="alert">
            <AlertCircle className="w-3.5 h-3.5" aria-hidden />
            <span>Couldn’t load rankings.</span>
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className={cn('underline font-semibold hover:text-white', FOCUS)}
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
