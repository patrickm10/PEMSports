import React from 'react';
import { GroupedBarChart } from '../../../../components/charts/GroupedBarChart';
import type { CategoricalChartModel } from '../../../../components/charts/contract';

interface Props {
  data: CategoricalChartModel | null;
  isLoading?: boolean;
  error?: Error | null;
}

export const SurfacePanel: React.FC<Props> = ({ data, isLoading, error }) => (
  <GroupedBarChart
    data={data}
    title="Surface Split"
    subtitle="Turf vs grass — average PPR per game"
    height={260}
    isLoading={isLoading}
    emptyMessage={
      error
        ? 'Unable to load surface splits'
        : 'No surface data available for this player'
    }
  />
);
