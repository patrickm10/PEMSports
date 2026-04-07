import { useWorkspaceState } from '../../../hooks/v3/useWorkspaceState';
import { LucideChevronRight, LucideFilter, LucideRefreshCw } from 'lucide-react';

export function V3ContextBar() {
  const { state, updateState, resetFilters } = useWorkspaceState();

  const POSITIONS = ['qb', 'rb', 'wr', 'te', 'k'];
  const YEARS = [2020, 2021, 2022, 2023, 2024, 2025, 2026];

  return (
    <header className="h-14 border-b border-white/5 bg-[#020617]/80 backdrop-blur-md flex items-center px-6 justify-between z-20">
      {/* Breadcrumbs / Context Path */}
      <div className="flex items-center gap-3 text-sm font-medium">
        <span className="text-slate-500">Workspace</span>
        <LucideChevronRight className="w-4 h-4 text-slate-700" />
        <span className="text-blue-400 capitalize">{state.position}</span>
        <LucideChevronRight className="w-4 h-4 text-slate-700" />
        <span className="text-slate-300">{state.year} Analytics</span>
      </div>

      {/* Dynamic Filter Controls */}
      <div className="flex items-center gap-4">
        {/* Position Select */}
        <div className="flex bg-slate-900/50 rounded-lg p-1 border border-white/5">
          {POSITIONS.map(pos => (
            <button
              key={pos}
              onClick={() => updateState({ position: pos })}
              className={`px-3 py-1 text-xs font-bold uppercase rounded-md transition-all ${
                state.position === pos 
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/30' 
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              {pos}
            </button>
          ))}
        </div>

        {/* Year Select */}
        <select
          value={state.year}
          onChange={(e) => updateState({ year: parseInt(e.target.value) })}
          className="bg-slate-900/50 border border-white/5 rounded-lg px-3 py-1.5 text-xs font-bold text-slate-300 focus:outline-none focus:border-blue-500/50 transition-all cursor-pointer appearance-none pr-8 relative"
        >
          {YEARS.map(y => <option key={y} value={y}>{y} Season</option>)}
        </select>

        {/* Action Group */}
        <div className="h-6 w-px bg-white/5 mx-2" />
        
        <button 
          onClick={resetFilters}
          className="p-2 rounded-lg hover:bg-white/5 text-slate-400 hover:text-slate-200 transition-all relative group"
          title="Reset Filters"
        >
          <LucideRefreshCw className="w-4 h-4" />
          {state.filters && (
            <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" />
          )}
        </button>

        <button className="flex items-center gap-2 px-3 py-1.5 bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 border border-blue-500/20 rounded-lg text-xs font-bold transition-all">
          <LucideFilter className="w-4 h-4" />
          Advanced Filters
        </button>
      </div>
    </header>
  );
}
