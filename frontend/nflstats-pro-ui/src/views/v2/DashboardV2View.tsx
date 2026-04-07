import { useState, useMemo, useEffect } from 'react';
import type { Ranking, SortField, SortOrder } from '../../models/Ranking';

import { useRankings } from '../../hooks/useRankings';
import { useSeasons } from '../../hooks/useSeasons';
import { useWeeklyRankings } from '../../hooks/useWeeklyRankings';
import { useWeeks } from '../../hooks/useWeeks';

import { DashboardV2 } from '../../components/v2/DashboardV2';
import { RankingsTableV2 } from '../../components/v2/RankingsTableV2';
import { ControlBar } from '../../components/v2/ControlBar';
import { StatsSummary } from '../../components/v2/StatsSummary';
import { PlayerDetail } from '../../components/PlayerDetail';
import { ProInsightsDrawer } from '../../components/ProInsightsDrawer';

export function DashboardV2View() {
  const [activeTab, setActiveTab] = useState('qb');
  const [viewMode, setViewMode] = useState<'season' | 'weekly'>('season');
  const [selectedYear, setSelectedYear] = useState('');
  const [selectedWeek, setSelectedWeek] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<SortField>('fpts_ppr');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [selectedPlayer, setSelectedPlayer] = useState<Ranking | null>(null);
  const [insightPlayer, setInsightPlayer] = useState<any | null>(null);

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

  // Rankings queries
  const seasonQuery = useRankings(activeTab, validYearInput, sortBy, sortOrder);
  const weeklyQuery = useWeeklyRankings(
    activeTab,
    viewMode === 'weekly' ? validYearInput : '',
    viewMode === 'weekly' ? validWeekInput : '',
    sortBy,
    sortOrder
  );

  const activeQuery = viewMode === 'season' ? seasonQuery : weeklyQuery;
  const { data: sortedData = [], isLoading } = activeQuery;

  // Client-side search filter
  const filteredData = useMemo(() => {
    if (!searchQuery) return sortedData;
    const q = searchQuery.toLowerCase();
    return sortedData.filter(
      (p) =>
        p.player_name.toLowerCase().includes(q) ||
        p.team.toLowerCase().includes(q),
    );
  }, [sortedData, searchQuery]);

  const handleSort = (field: SortField) => {
    if (sortBy === field) {
      setSortOrder((o) => (o === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const handleTabChange = (newTab: string) => {
    setActiveTab(newTab);
    setSortBy('fpts_ppr');
    setSortOrder('desc');
    setSelectedPlayer(null);
  };

  const handleViewModeChange = (newMode: 'season' | 'weekly') => {
    setViewMode(newMode);
    setSortBy('fpts_ppr');
    setSortOrder('desc');
    setSelectedPlayer(null);
  };

  return (
    <DashboardV2
      activePosition={activeTab}
      onPositionChange={handleTabChange}
      isDarkMode={true}
    >
      <div className="space-y-6">
        <header>
          <h1 className="text-3xl font-extrabold tracking-tight">
            {activeTab.toUpperCase()} Performance
            <span className="text-blue-500 ml-2">Analytics</span>
          </h1>
          <p className="text-slate-400 mt-1.5 text-sm font-medium">
            {selectedYear} {viewMode === 'weekly' ? `Week ${selectedWeek}` : 'Season'} · Powered by DuckDB
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
        />

        <StatsSummary data={filteredData} isLoading={isLoading} />

        <RankingsTableV2
          data={filteredData}
          sortBy={sortBy}
          sortOrder={sortOrder}
          onSort={handleSort}
          onRowClick={(p) => {
            if (viewMode === 'weekly' && p.predicted_alpha !== undefined) {
              setInsightPlayer(p);
            } else {
              setSelectedPlayer(p);
            }
          }}
          activeTab={activeTab}
          isLoading={isLoading}
        />
      </div>

      <PlayerDetail
        player={selectedPlayer}
        onClose={() => setSelectedPlayer(null)}
      />

      <ProInsightsDrawer
        player={insightPlayer}
        isOpen={Boolean(insightPlayer)}
        onClose={() => setInsightPlayer(null)}
      />
    </DashboardV2>
  );
}
