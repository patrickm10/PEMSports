import { useState, useMemo, useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';

import type { Ranking, SortField, SortOrder } from './models/Ranking';

import { useRankings } from './hooks/useRankings';
import { useSeasons } from './hooks/useSeasons';
import { useWeeklyRankings } from './hooks/useWeeklyRankings';
import { useWeeks } from './hooks/useWeeks';

import { LandingPage } from './components/v2/LandingPage';
import { SituationalDashboard } from './components/v2/SituationalDashboard';
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
  const { data: rawYears = [] as number[] } = useSeasons(activeTab);
  const availableYears = useMemo(() => rawYears.filter((y: number) => y !== 2026), [rawYears]);

  // Weeks — only fetched in weekly mode
  const { data: availableWeeks = [] as number[] } = useWeeks(activeTab, selectedYear);

  // Sync selectedYear whenever position changes
  useEffect(() => {
    if (availableYears.length > 0) {
      if (!selectedYear || !availableYears.includes(parseInt(selectedYear))) {
        setSelectedYear(availableYears[0].toString());
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
        <motion.div layout className="w-full max-w-[1600px] mx-auto space-y-6">
          <motion.header layout className="space-y-1 text-center sm:text-left">
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
          </motion.header>

          <AnimatePresence mode="wait">
            {workspaceView === 'dashboard' ? (
              <motion.div
                key="workspace-dashboard"
                layout
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
              >
                <SituationalDashboard
                  position={activeTab}
                  year={validYearInput || selectedYear}
                  roster={filteredData as Ranking[]}
                />
              </motion.div>
            ) : (
              <motion.div
                key="workspace-rankings"
                layout
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
                className="space-y-6"
              >
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

                <StatsSummary data={filteredData} isLoading={isLoading} />

                <div className="rounded-2xl overflow-hidden min-h-[min(70vh,900px)] h-[calc(100vh-320px)] sm:h-[calc(100vh-280px)] glass-card border-white/10">
                  <VirtualizedGrid
                    data={filteredData}
                    onRowClick={setSelectedPlayer}
                    viewMode={viewMode}
                    density={density}
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
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
