import { useState, useMemo, useEffect } from 'react';

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
import { EChart } from './components/charts/EChart';
import {
  buildMetricByFacetOption,
  buildRankingsTopTenOption,
} from './components/charts/chartOptions';
import { resolvePrimaryMetric } from './utils/metrics';
import { rankingToPlayerRef } from './utils/rankingToPlayerRef';
import { positionFullName } from './utils/positionLabels';
import {
  buildResetFilters,
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
import { InsightsView } from './v3/components/insights/InsightsView';
import { useSearchStore } from './stores/searchStore';
import { usePlayerAnalyticsStore } from './stores/playerAnalyticsStore';
import { useInsightsStore } from './stores/insightsStore';
import type { InsightPosition } from './api/insightsTypes';
import { useMediaQuery } from './hooks/useMediaQuery';

type WorkspaceView = 'dashboard' | 'rankings' | 'player' | 'insights';

const INSIGHT_POSITIONS: ReadonlySet<string> = new Set(['qb', 'rb', 'wr', 'te']);

function syncInsightsPosition(position: string) {
  if (!INSIGHT_POSITIONS.has(position)) return;
  useInsightsStore
    .getState()
    .setPosition(position as Exclude<InsightPosition, 'all'>);
}

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
  const [workspaceView, setWorkspaceView] = useState<WorkspaceView>('rankings');

  const openSearch = useSearchStore((s) => s.open);
  const pushRecent = useSearchStore((s) => s.pushRecent);
  const analyticsPlayer = usePlayerAnalyticsStore((s) => s.selectedPlayer);
  const selectPlayer = usePlayerAnalyticsStore((s) => s.selectPlayer);
  const clearAnalytics = usePlayerAnalyticsStore((s) => s.clear);
  const isMobile = useMediaQuery('(max-width: 768px)');
  const lockRankingsFill = workspaceView === 'rankings' && !isMobile;

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

  const rankingsEnabled = workspaceView !== 'insights';
  const seasonQuery = useRankings(
    activeTab,
    validYearInput,
    rankingsEnabled && viewMode === 'season',
  );
  const weeklyQuery = useWeeklyRankings(
    activeTab,
    viewMode === 'weekly' ? validYearInput : '',
    viewMode === 'weekly' ? validWeekInput : '',
    rankingsEnabled,
  );

  const activeQuery = viewMode === 'season' ? seasonQuery : weeklyQuery;
  const {
    data: queryData = [],
    isLoading,
    isError,
    isPlaceholderData,
    refetch,
  } = activeQuery;

  const sortedData = useMemo(
    () => (isPlaceholderData ? [] : (queryData as Ranking[])),
    [isPlaceholderData, queryData],
  );
  const rankingsBusy = isLoading || seasonsLoading || isPlaceholderData;

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
    if (workspaceView === 'insights') {
      syncInsightsPosition(newTab);
    }
  };

  useEffect(() => {
    if (workspaceView === 'insights') {
      syncInsightsPosition(activeTab);
    }
  }, [workspaceView, activeTab]);

  const handleViewModeChange = (newMode: 'season' | 'weekly') => {
    setViewMode(newMode);
  };

  const handleResetFilters = () => {
    const next = buildResetFilters(availableYears, availableWeeks);
    setViewMode(next.viewMode);
    setSelectedYear(next.year);
    setSelectedWeek(next.week);
    setSearchQuery(next.searchQuery);
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

  const handleRankingsRowClick = (row: Record<string, unknown>) => {
    const player = rankingToPlayerRef(row, activeTab);
    selectPlayer(player);
    pushRecent(player);
  };

  const handleLaunch = () => {
    persistLandingSkip();
    setShowLanding(false);
  };

  const emptyMessage = (() => {
    if (isError || seasonsError) {
      return 'Couldn’t load rankings. Check your connection and try again.';
    }
    if (rankingsBusy) {
      return 'Loading rankings…';
    }
    if (!validYearInput) {
      return `No seasons yet for ${positionFullName(activeTab)}.`;
    }
    if (viewMode === 'weekly' && !validWeekInput) {
      return `No weeks yet for ${selectedYear || 'the selected year'}.`;
    }
    if (searchQuery && sortedData.length > 0 && filteredData.length === 0) {
      return `No players match “${searchQuery}”.`;
    }
    const slice =
      viewMode === 'weekly'
        ? `${selectedYear} week ${selectedWeek}`
        : `${selectedYear} season`;
    return `No ${positionFullName(activeTab)} ${slice} rankings yet.`;
  })();

  if (showLanding) {
    return <LandingPage onLaunch={handleLaunch} />;
  }

  return (
    <>
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
        viewMode={viewMode}
        selectedYear={selectedYear}
        selectedWeek={selectedWeek}
      >
        <div
          id="pem-main-content"
          className={
            lockRankingsFill
              ? 'w-full max-w-[1600px] mx-auto h-full min-h-0 flex flex-col gap-6'
              : 'w-full max-w-[1600px] mx-auto space-y-4'
          }
        >
          {workspaceView !== 'player' && (
            <div className={lockRankingsFill ? 'shrink-0' : undefined}>
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
                density={density}
                setDensity={setDensity}
                showDensity={workspaceView === 'rankings'}
                showSearch={workspaceView !== 'insights'}
                onResetFilters={handleResetFilters}
                isLoading={workspaceView === 'rankings' && rankingsBusy}
                isError={workspaceView === 'rankings' && (isError || seasonsError)}
                onRetry={() => {
                  void refetchSeasons();
                  void refetch();
                }}
              />
            </div>
          )}

          {workspaceView === 'dashboard' && (
            <div>
              <StatsSummary
                data={filteredData}
                metric={resolvedMetric}
                isLoading={isLoading}
              />
            </div>
          )}

          {workspaceView === 'dashboard' && viewMode === 'season' && (
            <EChart
              title="Top 10"
              subtitle={`Highest ${resolvedMetric?.label ?? 'metric'} within current filters`}
              option={rankingsTopTenOption}
              isLoading={isLoading}
              emptyMessage={emptyMessage}
            />
          )}

          {workspaceView === 'dashboard' && viewMode === 'weekly' && (
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
              <EChart
                title="By opponent"
                subtitle={`Average ${resolvedMetric?.label ?? 'metric'} by opponent`}
                option={opponentOption}
                isLoading={isLoading}
                emptyMessage={emptyMessage}
              />
              <EChart
                title="By surface"
                subtitle={`Average ${resolvedMetric?.label ?? 'metric'} by surface`}
                option={surfaceOption}
                isLoading={isLoading}
                emptyMessage={emptyMessage}
              />
              <EChart
                title="By venue"
                subtitle={`Average ${resolvedMetric?.label ?? 'metric'} by venue type`}
                option={venueOption}
                isLoading={isLoading}
                emptyMessage={emptyMessage}
              />
            </div>
          )}

          {workspaceView === 'rankings' && (
            <div
              className={
                lockRankingsFill
                  ? 'flex-1 min-h-0 min-w-0'
                  : 'h-[70vh] min-h-[360px]'
              }
            >
                <VirtualizedGrid
                  data={filteredData}
                  onRowClick={handleRankingsRowClick}
                  viewMode={viewMode}
                  density={density}
                  emptyMessage={emptyMessage}
                  resolvedMetric={resolvedMetric}
                />
            </div>
          )}

          {workspaceView === 'player' && (
            <PlayerAnalyticsView onBack={handleBackFromAnalytics} />
          )}

          {workspaceView === 'insights' && (
            <InsightsView
              selectedYear={selectedYear}
              selectedWeek={selectedWeek}
              viewMode={viewMode}
              onPositionChange={setActiveTab}
            />
          )}
        </div>
      </ResponsiveDock>

      <SearchModal />
    </>
  );
}
