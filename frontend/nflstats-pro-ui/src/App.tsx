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
import { EChart } from './components/charts/EChart';
import {
  buildMetricByFacetOption,
  buildRankingsTopTenOption,
} from './components/charts/chartOptions';
import { resolvePrimaryMetric } from './utils/metrics';

import { ResponsiveDock } from './v3/components/layout/ResponsiveDock';
import { SearchModal } from './v3/components/search/SearchModal';
import { PlayerAnalyticsView } from './v3/components/playerAnalytics/PlayerAnalyticsView';
import { useSearchStore } from './stores/searchStore';
import { usePlayerAnalyticsStore } from './stores/playerAnalyticsStore';

type WorkspaceView = 'dashboard' | 'rankings' | 'player';

const POSITION_TABS: ReadonlySet<string> = new Set([
  'qb',
  'rb',
  'wr',
  'te',
  'k',
  'dst',
]);

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
  const [workspaceView, setWorkspaceView] = useState<WorkspaceView>('rankings');

  const openSearch = useSearchStore((s) => s.open);
  const analyticsPlayer = usePlayerAnalyticsStore((s) => s.selectedPlayer);
  const clearAnalytics = usePlayerAnalyticsStore((s) => s.clear);

  // App owns navigation. The store mutates UI state only; this effect
  // reacts to store changes and updates navigation imperatively. The
  // store does NOT call setWorkspaceView or setActiveTab.
  useEffect(() => {
    if (!analyticsPlayer) return;
    const pos = analyticsPlayer.position?.toLowerCase();
    if (pos && POSITION_TABS.has(pos) && pos !== activeTab) {
      setActiveTab(pos);
      setSortBy('rank');
      setSortOrder('asc');
    }
    setWorkspaceView('player');
    // intentionally no dep on activeTab — we only react to selection changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analyticsPlayer]);

  const { data: rawYears = [] } = useSeasons(activeTab);
  const availableYears = useMemo(() => rawYears, [rawYears]);

  useEffect(() => {
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.debug('[seasons chain]', { activeTab, rawYears, availableYears });
    }
  }, [activeTab, rawYears, availableYears]);

  const { data: availableWeeks = [] } = useWeeks(activeTab, selectedYear);

  useEffect(() => {
    if (availableYears.length > 0) {
      const parsed = Number.parseInt(selectedYear, 10);
      const selectedIsValid = Number.isFinite(parsed) && availableYears.includes(parsed);
      if (!selectedIsValid) setSelectedYear(availableYears[0].toString());
    }
  }, [availableYears, selectedYear]);

  useEffect(() => {
    if (availableWeeks.length > 0) {
      if (!selectedWeek || !availableWeeks.includes(parseInt(selectedWeek))) {
        setSelectedWeek(availableWeeks[0].toString());
      }
    }
  }, [availableWeeks, selectedWeek]);

  const isYearValid = Boolean(selectedYear && availableYears.includes(parseInt(selectedYear)));
  const isWeekValid = Boolean(selectedWeek && availableWeeks.includes(parseInt(selectedWeek)));
  const validYearInput = isYearValid ? selectedYear : '';
  const validWeekInput = isWeekValid ? selectedWeek : '';

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

  const filteredData = useMemo<Ranking[]>(() => {
    if (!searchQuery) return sortedData as Ranking[];
    const q = searchQuery.toLowerCase();
    return (sortedData as Ranking[]).filter(
      (p) =>
        p.player_name.toLowerCase().includes(q) ||
        (p.team?.toLowerCase() || '').includes(q),
    );
  }, [sortedData, searchQuery]);
  const resolvedMetric = useMemo(
    () => resolvePrimaryMetric(filteredData),
    [filteredData],
  );
  const rankingsTopTenOption = useMemo(
    () => buildRankingsTopTenOption(filteredData, resolvedMetric),
    [filteredData, resolvedMetric],
  );
  const opponentOption = useMemo(
    () => buildMetricByFacetOption(filteredData, resolvedMetric, 'opponent'),
    [filteredData, resolvedMetric],
  );
  const surfaceOption = useMemo(
    () => buildMetricByFacetOption(filteredData, resolvedMetric, 'surface_type'),
    [filteredData, resolvedMetric],
  );
  const venueOption = useMemo(
    () => buildMetricByFacetOption(filteredData, resolvedMetric, 'indoor_outdoor'),
    [filteredData, resolvedMetric],
  );

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

  const handleWorkspaceViewChange = (v: WorkspaceView) => {
    if (v === 'player' && !analyticsPlayer) {
      openSearch();
      return;
    }
    setWorkspaceView(v);
  };

  const handleBackFromAnalytics = () => {
    clearAnalytics();
    setWorkspaceView('rankings');
  };

  if (showLanding) {
    return <LandingPage onLaunch={() => setShowLanding(false)} />;
  }

  return (
    <AuthProvider>
      <ResponsiveDock
        activePosition={activeTab}
        onPositionChange={handleTabChange}
        workspaceView={workspaceView}
        onWorkspaceViewChange={handleWorkspaceViewChange}
        hasSelectedPlayer={Boolean(analyticsPlayer)}
        onOpenSearch={openSearch}
        density={density}
        setDensity={setDensity}
      >
        <div className="w-full max-w-[1600px] mx-auto space-y-6">
          <header className="space-y-1">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              {workspaceView === 'dashboard' && 'Command center'}
              {workspaceView === 'rankings' && (
                <>
                  {activeTab.toUpperCase()}{' '}
                  <span className="text-sky-400">performance</span>
                </>
              )}
              {workspaceView === 'player' && analyticsPlayer && (
                <>
                  {analyticsPlayer.player_name}{' '}
                  <span className="text-sky-400">analytics</span>
                </>
              )}
            </h1>
            <p className="text-slate-400 text-xs sm:text-sm font-medium tracking-wide uppercase">
              {workspaceView === 'player' && analyticsPlayer
                ? `${analyticsPlayer.position?.toUpperCase() ?? '—'} · ${analyticsPlayer.team?.toUpperCase() ?? '—'} · DuckDB Analytical Kernel`
                : `${selectedYear} ${viewMode === 'weekly' ? `Week ${selectedWeek}` : 'Season'} · DuckDB Analytical Kernel`}
            </p>
          </header>

          {workspaceView === 'rankings' && (
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
          )}

          {workspaceView !== 'player' && (
            <StatsSummary
              data={filteredData}
              metric={resolvedMetric}
              isLoading={isLoading}
            />
          )}

          {workspaceView === 'dashboard' && (
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
              <EChart
                title="Opponent Efficiency"
                subtitle={`Average ${resolvedMetric?.label ?? 'metric'} by opponent`}
                option={opponentOption}
                isLoading={isLoading}
                emptyMessage={
                  viewMode === 'weekly'
                    ? 'No opponent metadata for the current filters'
                    : 'Switch to weekly rankings to compare opponents'
                }
              />
              <EChart
                title="Surface Split"
                subtitle={`Average ${resolvedMetric?.label ?? 'metric'} by surface`}
                option={surfaceOption}
                isLoading={isLoading}
                emptyMessage={
                  viewMode === 'weekly'
                    ? 'No surface metadata for the current filters'
                    : 'Switch to weekly rankings to compare surfaces'
                }
              />
              <EChart
                title="Venue Split"
                subtitle={`Average ${resolvedMetric?.label ?? 'metric'} by venue type`}
                option={venueOption}
                isLoading={isLoading}
                emptyMessage={
                  viewMode === 'weekly'
                    ? 'No venue metadata for the current filters'
                    : 'Switch to weekly rankings to compare venue types'
                }
              />
            </div>
          )}

          {workspaceView === 'rankings' && (
            <>
              <EChart
                title="Top 10 Rankings"
                subtitle={`Highest ${resolvedMetric?.label ?? 'metric'} within current filters`}
                option={rankingsTopTenOption}
                isLoading={isLoading}
                height={260}
                emptyMessage="No ranking data for the current filters"
              />
              <div className="rounded-2xl overflow-hidden min-h-[360px] h-[calc(100vh-600px)] glass-card border-white/10">
                <VirtualizedGrid
                  data={filteredData}
                  onRowClick={setSelectedPlayer}
                  viewMode={viewMode}
                  density={density}
                />
              </div>
            </>
          )}

          {workspaceView === 'player' && (
            <PlayerAnalyticsView onBack={handleBackFromAnalytics} />
          )}
        </div>
      </ResponsiveDock>

      <SearchModal />

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
