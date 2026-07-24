import React from 'react';
import { GroupedBarChart } from '../../../../components/charts/GroupedBarChart';
import type { CategoricalChartModel } from '../../../../components/charts/contract';

interface Props {
  data: CategoricalChartModel | null;
  isLoading?: boolean;
  error?: Error | null;
}

export const VsOpponentPanel: React.FC<Props> = ({ data, isLoading, error }) => (
  <GroupedBarChart
    data={data}
    title="Vs Opponent"
    subtitle="Average PPR per game by opposing team"
    height={300}
    isLoading={isLoading}
    emptyMessage={
      error
        ? 'Unable to load opponent splits'
        : 'No opponent data available for this player'
    }
    rotateLabels
  />
);
