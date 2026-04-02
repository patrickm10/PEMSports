import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Calendar, Hash, Users } from 'lucide-react';
import { cn } from '../../utils/cn';

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
}

export const ControlBar: React.FC<ControlBarProps> = ({
  viewMode, setViewMode, selectedYear, setSelectedYear, availableYears,
  selectedWeek, setSelectedWeek, availableWeeks, searchQuery, setSearchQuery,
  totalPlayers,
}) => {
  return (
    <div className="flex flex-wrap items-center justify-between gap-4 p-5 bg-slate-900/30 backdrop-blur-xl border border-slate-800/40 rounded-2xl">
      <div className="flex items-center gap-3 flex-wrap">
        {/* View Toggle */}
        <div className="flex bg-slate-950/60 p-1 rounded-xl border border-white/[0.04]">
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

        {/* Year Select */}
        <div className="flex items-center gap-2 bg-slate-950/40 pl-3 pr-1 py-1.5 rounded-xl border border-white/[0.04] group hover:border-slate-700/50 transition-colors">
          <Calendar className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-400 transition-colors" />
          <select
            value={selectedYear}
            onChange={(e) => setSelectedYear(e.target.value)}
            className="bg-transparent text-xs font-bold text-slate-300 outline-none cursor-pointer py-1 pr-2 appearance-none"
          >
            {availableYears.map(year => (
              <option key={year} value={year.toString()} className="bg-slate-900 text-slate-200">{year}</option>
            ))}
          </select>
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
              <div className="flex items-center gap-2 bg-slate-950/40 pl-3 pr-1 py-1.5 rounded-xl border border-white/[0.04] group hover:border-slate-700/50 transition-colors">
                <Hash className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-400 transition-colors" />
                <select
                  value={selectedWeek}
                  onChange={(e) => setSelectedWeek(e.target.value)}
                  className="bg-transparent text-xs font-bold text-slate-300 outline-none cursor-pointer py-1 pr-2 appearance-none"
                >
                  {availableWeeks.map(week => (
                    <option key={week} value={week.toString()} className="bg-slate-900 text-slate-200">Wk {week}</option>
                  ))}
                </select>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Player Count Badge */}
        {totalPlayers !== undefined && totalPlayers > 0 && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/30 border border-white/[0.04] text-xs text-slate-500">
            <Users className="w-3.5 h-3.5" />
            <span className="font-semibold text-slate-400">{totalPlayers}</span>
            <span>players</span>
          </div>
        )}
      </div>

      {/* Search */}
      <div className="flex items-center gap-3 flex-1 max-w-sm min-w-[200px]">
        <div className="relative flex-1 group">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 group-focus-within:text-blue-400 transition-colors" />
          <input
            type="text"
            placeholder="Search players or teams..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950/40 border border-white/[0.04] rounded-xl py-2.5 pl-10 pr-4 text-xs font-medium focus:outline-none focus:ring-1 focus:ring-blue-500/40 focus:border-blue-500/30 transition-all placeholder:text-slate-600"
          />
        </div>
      </div>
    </div>
  );
};
