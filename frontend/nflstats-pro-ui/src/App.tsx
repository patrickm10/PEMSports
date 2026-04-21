import { useState, useMemo, useEffect, useRef } from 'react';
import { AnimatePresence } from 'framer-motion';

import type { Ranking, SortField, SortOrder } from './models/Ranking';

import { useRankings } from './hooks/useRankings';
import { useSeasons } from './hooks/useSeasons';
import { useWeeklyRankings } from './hooks/useWeeklyRankings';
import { useWeeks } from './hooks/useWeeks';

import { LandingPage } from './components/v2/LandingPage';
import { VirtualizedGrid } from './components/VirtualizedGrid';
import type { GridDensity } from './components/VirtualizedGrid';
import { ControlBar } from './components/v2/ControlBar';
import { StatsSummary } from './components/v2/StatsSummary';
import { PlayerDetail } from './components/PlayerDetail';
import { AuthProvider } from './contexts/AuthContext';

import { ResponsiveDock } from './v3/components/layout/ResponsiveDock';

export default function App() {
  const [showLanding, setShowLanding] = useState(true);
  const [activeTab, setActiveTab] = useState('qb');
  const [viewMode, setViewMode] = useState<'season' | 'weekly'>('season');
  const [selectedYear, setSelectedYear] = useState('');
  const [selectedWeek, setSelectedWeek] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<SortField>('rank');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');
  const [density, setDensity] = useState<GridDensity>('standard');
  const [selectedPlayer, setSelectedPlayer] = useState<Ranking | null>(null);
  const [workspaceView, setWorkspaceView] = useState<'dashboard' | 'rankings'>('rankings');
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Seasons — cached separately
  const { data: rawYears = [] } = useSeasons(activeTab);
  const availableYears = useMemo(() => rawYears.filter(y => y !== 2026), [rawYears]);

  // Weeks — only fetched in weekly mode
  const { data: availableWeeks = [] } = useWeeks(activeTab, selectedYear);

  // Sync selectedYear whenever position changes
  useEffect(() => {
    if (availableYears.length > 0) {
      if (!selectedYear || !availableYears.includes(parseInt(selectedYear))) {
        setSelectedYear(availableYears.includes(2025) ? '2025' : availableYears[0].toString());
      }
    }
  }, [availableYears, selectedYear]);

  // Sync selectedWeek whenever year/position changes
  useEffect(() => {
    if (availableWeeks.length > 0) {
      if (!selectedWeek || !availableWeeks.includes(parseInt(selectedWeek))) {
        setSelectedWeek(availableWeeks[0].toString());
      }
    }
  }, [availableWeeks, selectedWeek]);

  // Validated parameter combinations
  const isYearValid = Boolean(selectedYear && availableYears.includes(parseInt(selectedYear)));
  const isWeekValid = Boolean(selectedWeek && availableWeeks.includes(parseInt(selectedWeek)));
  const validYearInput = isYearValid ? selectedYear : '';
  const validWeekInput = isWeekValid ? selectedWeek : '';

  /** Season year on the clicked row (weekly grid rows carry `year` for this filter). */
  const profileYear = useMemo(() => {
    if (!selectedPlayer) return '';
    const y = (selectedPlayer as { year?: number }).year;
    if (y == null || Number.isNaN(Number(y))) return validYearInput;
    return String(Math.floor(Number(y)));
  }, [selectedPlayer, validYearInput]);

  // Rankings queries — sortBy/sortOrder preserved for API compatibility but
  // sorting itself is now owned by TanStack Table inside VirtualizedGrid.
  const seasonQuery = useRankings(activeTab, validYearInput, sortBy, sortOrder);
  const weeklyQuery = useWeeklyRankings(
    activeTab,
    viewMode === 'weekly' ? validYearInput : '',
    viewMode === 'weekly' ? validWeekInput : '',
    sortBy,
    sortOrder
  );

  const activeQuery = (viewMode === 'season' ? seasonQuery : weeklyQuery) as any;
  const { data: sortedData = [], isLoading } = activeQuery;

  // Client-side search filter
  const filteredData = useMemo(() => {
    if (!searchQuery) return sortedData;
    const q = searchQuery.toLowerCase();
    return (sortedData as Ranking[]).filter(
      (p) =>
        p.player_name.toLowerCase().includes(q) ||
        (p.team?.toLowerCase() || "").includes(q),
    );
  }, [sortedData, searchQuery]);

  const handleTabChange = (newTab: string) => {
    setActiveTab(newTab);
    setSortBy('rank');
    setSortOrder('asc');
    setSelectedPlayer(null);
    setWorkspaceView('rankings');
  };


  const handleViewModeChange = (newMode: 'season' | 'weekly') => {
    setViewMode(newMode);
    setSortBy('rank');
    setSortOrder('asc');
    setSelectedPlayer(null);
  };

  // ── Landing Page ──────────────────────────────────────────────────
  if (showLanding) {
    return <LandingPage onLaunch={() => setShowLanding(false)} />;
  }

  return (
    <AuthProvider>
      <ResponsiveDock
        activePosition={activeTab}
        onPositionChange={handleTabChange}
        workspaceView={workspaceView}
        onWorkspaceViewChange={setWorkspaceView}
        onSearchFocus={() => {
          setWorkspaceView('rankings');
          requestAnimationFrame(() => searchInputRef.current?.focus());
        }}
        density={density}
        setDensity={setDensity}
      >
        <div className="w-full max-w-[1600px] mx-auto space-y-6">
          <header className="space-y-1">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              {workspaceView === 'dashboard' ? (
                'Command center'
              ) : (
                <>
                  {activeTab.toUpperCase()}{' '}
                  <span className="text-sky-400">performance</span>
                </>
              )}
            </h1>
            <p className="text-slate-400 text-xs sm:text-sm font-medium tracking-wide uppercase">
              {selectedYear}{' '}
              {viewMode === 'weekly' ? `Week ${selectedWeek}` : 'Season'} · DuckDB Analytical Kernel
            </p>
          </header>

          {workspaceView === 'rankings' && (
            <ControlBar
              ref={searchInputRef}
              viewMode={viewMode}
              setViewMode={handleViewModeChange}
              selectedYear={selectedYear}
              setSelectedYear={setSelectedYear}
              availableYears={availableYears}
              selectedWeek={selectedWeek}
              setSelectedWeek={setSelectedWeek}
              availableWeeks={availableWeeks}
              searchQuery={searchQuery}
              setSearchQuery={setSearchQuery}
              totalPlayers={filteredData.length}
              density={density}
              setDensity={setDensity}
            />
          )}

          <StatsSummary data={filteredData} isLoading={isLoading} />

          {workspaceView === 'dashboard' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="rounded-2xl p-6 glass-card border-white/10">
                <p className="text-slate-400 text-xs font-semibold uppercase tracking-widest mb-2">Snapshot</p>
                <p className="text-white font-bold text-lg mb-2">Rankings &amp; filters</p>
                <p className="text-slate-400 text-sm leading-relaxed">
                  Open <span className="text-white font-semibold">Rankings</span> in the sidebar to browse the virtualized
                  leaderboard, density modes, and weekly or seasonal context.
                </p>
              </div>
              <div className="rounded-2xl p-6 glass-card border-white/10">
                <p className="text-slate-400 text-xs font-semibold uppercase tracking-widest mb-2">Shortcuts</p>
                <p className="text-white font-bold text-lg mb-2">Search &amp; settings</p>
                <p className="text-slate-400 text-sm leading-relaxed">
                  Use <span className="text-white font-semibold">Search</span> to focus the player query, or{' '}
                  <span className="text-white font-semibold">Settings</span> for compact / standard / expert density.
                </p>
              </div>
            </div>
          )}

          {workspaceView === 'rankings' && (
            <div className="rounded-2xl overflow-hidden min-h-[min(70vh,900px)] h-[calc(100vh-320px)] sm:h-[calc(100vh-280px)] glass-card border-white/10">
              <VirtualizedGrid
                data={filteredData}
                onRowClick={setSelectedPlayer}
                viewMode={viewMode}
                density={density}
              />
            </div>
          )}
        </div>
      </ResponsiveDock>

      <AnimatePresence>
        {selectedPlayer && profileYear && (
          <PlayerDetail
            key={`${selectedPlayer.player_id}-${profileYear}`}
            playerId={selectedPlayer.player_id}
            position={activeTab}
            year={profileYear}
            snapshot={selectedPlayer}
            onClose={() => setSelectedPlayer(null)}
          />
        )}
      </AnimatePresence>
    </AuthProvider>
  );
}
