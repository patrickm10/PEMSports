import { useState, useMemo, useEffect } from 'react';
import { AnimatePresence } from 'framer-motion';

import type { Ranking } from './models/Ranking';

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
import {
  buildResetFilters,
  formatActiveFilterSummary,
  isValidWeek,
  isValidYear,
  persistLandingSkip,
  pickDefaultWeek,
  pickDefaultYear,
  shouldSkipLanding,
} from './utils/filterState';

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
  const [showLanding, setShowLanding] = useState(() => !shouldSkipLanding());
  const [activeTab, setActiveTab] = useState('qb');
  const [viewMode, setViewMode] = useState<'season' | 'weekly'>('season');
  const [selectedYear, setSelectedYear] = useState('');
  const [selectedWeek, setSelectedWeek] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [density, setDensity] = useState<GridDensity>('standard');
  const [selectedPlayer, setSelectedPlayer] = useState<Ranking | null>(null);
  const [workspaceView, setWorkspaceView] = useState<WorkspaceView>('rankings');

  const openSearch = useSearchStore((s) => s.open);
  const analyticsPlayer = usePlayerAnalyticsStore((s) => s.selectedPlayer);
  const clearAnalytics = usePlayerAnalyticsStore((s) => s.clear);

  useEffect(() => {
    if (!analyticsPlayer) return;
    const pos = analyticsPlayer.position?.toLowerCase();
    if (pos && POSITION_TABS.has(pos) && pos !== activeTab) {
      setActiveTab(pos);
    }
    setWorkspaceView('player');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analyticsPlayer]);

  const {
    data: availableYears = [],
    isLoading: seasonsLoading,
    isError: seasonsError,
    refetch: refetchSeasons,
  } = useSeasons(activeTab);

  const { data: availableWeeks = [] } = useWeeks(activeTab, selectedYear);

  useEffect(() => {
    const next = pickDefaultYear(availableYears, selectedYear);
    if (next !== selectedYear) setSelectedYear(next);
  }, [availableYears, selectedYear]);

  useEffect(() => {
    const next = pickDefaultWeek(availableWeeks, selectedWeek);
    if (next !== selectedWeek) setSelectedWeek(next);
  }, [availableWeeks, selectedWeek]);

  const yearOk = isValidYear(selectedYear, availableYears);
  const weekOk = isValidWeek(selectedWeek, availableWeeks);
  const validYearInput = yearOk ? selectedYear : '';
  const validWeekInput = weekOk ? selectedWeek : '';

  const seasonQuery = useRankings(activeTab, validYearInput);
  const weeklyQuery = useWeeklyRankings(
    activeTab,
    viewMode === 'weekly' ? validYearInput : '',
    viewMode === 'weekly' ? validWeekInput : '',
  );

  const activeQuery = viewMode === 'season' ? seasonQuery : weeklyQuery;
  const {
    data: sortedData = [],
    isLoading,
    isError,
    isFetching,
    refetch,
  } = activeQuery;

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

  const activeFilterSummary = formatActiveFilterSummary(
    activeTab,
    viewMode,
    selectedYear,
    selectedWeek,
    filteredData.length,
    availableYears.length,
  );

  const handleTabChange = (newTab: string) => {
    setActiveTab(newTab);
    setSelectedPlayer(null);
    setWorkspaceView('rankings');
  };

  const handleViewModeChange = (newMode: 'season' | 'weekly') => {
    setViewMode(newMode);
    setSelectedPlayer(null);
  };

  const handleResetFilters = () => {
    const next = buildResetFilters(availableYears, availableWeeks);
    setViewMode(next.viewMode);
    setSelectedYear(next.year);
    setSelectedWeek(next.week);
    setSearchQuery(next.searchQuery);
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

  const handleLaunch = () => {
    persistLandingSkip();
    setShowLanding(false);
  };

  const emptyMessage = (() => {
    if (isError || seasonsError) {
      return 'API request failed. Check connectivity to the rankings service and retry.';
    }
    if (isLoading || seasonsLoading || isFetching) {
      return 'Loading rankings…';
    }
    if (!validYearInput) {
      return 'No seasons available from the API for this position yet.';
    }
    if (viewMode === 'weekly' && !validWeekInput) {
      return `No weeks available for ${selectedYear || 'the selected year'}.`;
    }
    if (searchQuery && sortedData.length > 0 && filteredData.length === 0) {
      return `No players match “${searchQuery}” in the current filters.`;
    }
    return `No records for ${activeTab.toUpperCase()} · ${
      viewMode === 'weekly' ? `${selectedYear} Week ${selectedWeek}` : `${selectedYear} season`
    }. This combination is empty in the serving database.`;
  })();

  if (showLanding) {
    return <LandingPage onLaunch={handleLaunch} />;
  }

  return (
    <AuthProvider>
      <a
        href="#pem-main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:top-2 focus:left-2 focus:px-3 focus:py-2 focus:rounded-lg focus:bg-sky-500 focus:text-white"
      >
        Skip to main content
      </a>
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
        <div id="pem-main-content" className="w-full max-w-[1600px] mx-auto space-y-6">
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
                ? `${analyticsPlayer.position?.toUpperCase() ?? '—'} · ${analyticsPlayer.team?.toUpperCase() ?? '—'} · PEM Sports`
                : `${activeFilterSummary}`}
            </p>
          </header>

          {workspaceView !== 'player' && (
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
              onResetFilters={handleResetFilters}
              isLoading={isLoading || seasonsLoading}
              isError={isError || seasonsError}
              onRetry={() => {
                void refetchSeasons();
                void refetch();
              }}
              activeFilterSummary={activeFilterSummary}
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
                    ? emptyMessage
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
                    ? emptyMessage
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
                    ? emptyMessage
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
                emptyMessage={emptyMessage}
              />
              <div className="rounded-2xl overflow-hidden min-h-[360px] h-[calc(100vh-600px)] glass-card border-white/10">
                <VirtualizedGrid
                  data={filteredData}
                  onRowClick={(row) => setSelectedPlayer(row as Ranking)}
                  viewMode={viewMode}
                  density={density}
                  emptyMessage={emptyMessage}
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
