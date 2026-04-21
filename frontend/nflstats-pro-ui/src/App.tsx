import { useState, useMemo, useEffect } from 'react';
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
      >
        <div className="w-full space-y-4">
          <header>
            <h1 className="text-3xl font-extrabold tracking-tight text-white italic">
              {activeTab.toUpperCase()} <span className="text-[#38bdf8]">PERFORMANCE</span>
            </h1>
            <p className="text-slate-500 mt-1.5 text-xs font-bold tracking-widest uppercase">
              {selectedYear} {viewMode === 'weekly' ? `Week ${selectedWeek}` : 'Season'} · DuckDB Analytical Kernel
            </p>
          </header>

          <ControlBar
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

          <div className="bg-[#1e293b4d] rounded-2xl border border-[#ffffff0a] overflow-hidden shadow-2xl h-[calc(100vh-360px)] min-h-[480px]">
            <VirtualizedGrid
              data={filteredData}
              onRowClick={setSelectedPlayer}
              viewMode={viewMode}
              density={density}
            />
          </div>
        </div>
      </ResponsiveDock>

      <AnimatePresence>
        {selectedPlayer && (
          <PlayerDetail
            player={selectedPlayer}
            onClose={() => setSelectedPlayer(null)}
          />
        )}
      </AnimatePresence>
    </AuthProvider>
  );
}
