import React from 'react';
import { GroupedBarChart } from '../../../../components/charts/GroupedBarChart';
import type { CategoricalChartModel } from '../../../../components/charts/contract';

interface Props {
  data: CategoricalChartModel | null;
  isLoading?: boolean;
  error?: Error | null;
}

export const StadiumPanel: React.FC<Props> = ({ data, isLoading, error }) => (
  <GroupedBarChart
    data={data}
    title="By Stadium"
    subtitle="Average PPR per game by stadium context"
    height={300}
    isLoading={isLoading}
    emptyMessage={
      error
        ? 'Unable to load stadium splits'
        : 'No stadium data available for this player'
    }
    rotateLabels
  />
);
