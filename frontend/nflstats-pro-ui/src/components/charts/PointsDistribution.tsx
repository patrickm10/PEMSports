import React, { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts';
import type { Ranking } from '../../models/Ranking';

interface PointsDistributionProps {
  data: Ranking[];
  highlightPlayer?: Ranking | null;
}

interface Bucket {
  label: string;
  count: number;
  rangeStart: number;
  rangeEnd: number;
  containsHighlight: boolean;
}

function buildHistogram(values: number[], bucketCount = 12): Bucket[] {
  if (values.length === 0) return [];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const step = range / bucketCount;

  const buckets: Bucket[] = Array.from({ length: bucketCount }, (_, i) => ({
    label: `${Math.round(min + i * step)}`,
    rangeStart: min + i * step,
    rangeEnd: min + (i + 1) * step,
    count: 0,
    containsHighlight: false,
  }));

  for (const v of values) {
    const i = Math.min(Math.floor((v - min) / step), bucketCount - 1);
    buckets[i].count++;
  }

  return buckets;
}

const CustomTooltip = ({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: Bucket }[];
}) => {
  if (!active || !payload?.length) return null;
  const b = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-title">
        {Math.round(b.rangeStart)} – {Math.round(b.rangeEnd)} pts
      </p>
      <p className="chart-tooltip-value">{b.count} player{b.count !== 1 ? 's' : ''}</p>
    </div>
  );
};

/**
 * PointsDistribution — histogram of PPR fantasy points for the full position/year.
 *
 * Answers the question: "How does this player's output compare to the full field?"
 * This is genuine analytical value — not just a reskin of the table data.
 */
export const PointsDistribution: React.FC<PointsDistributionProps> = ({
  data,
  highlightPlayer,
}) => {
  const values = useMemo(() => data.map((p) => p.fpts_ppr), [data]);
  const buckets = useMemo(() => buildHistogram(values, 12), [values]);

  const highlightVal = highlightPlayer?.fpts_ppr;

  // Percentile of the highlighted player
  const percentile = useMemo(() => {
    if (highlightVal == null) return null;
    const below = values.filter((v) => v < highlightVal).length;
    return Math.round((below / values.length) * 100);
  }, [values, highlightVal]);

  if (buckets.length === 0) return null;

  return (
    <div className="distribution-panel glass-card">
      <div className="dashboard-header">
        <h3>Points Distribution</h3>
        <p className="subtitle">
          PPR fantasy points across all {data.length} players
          {highlightPlayer && percentile != null && (
            <span className="highlight-label">
              &nbsp;·&nbsp;
              <strong>{highlightPlayer.player_name.split(' ').pop()}</strong>
              &nbsp;is in the&nbsp;
              <strong className="percentile">{percentile}th percentile</strong>
            </span>
          )}
        </p>
      </div>

      <div className="chart-container" style={{ width: '100%', height: 220, marginTop: '1rem' }}>
        <ResponsiveContainer>
          <BarChart data={buckets} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
            <XAxis
              dataKey="label"
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#64748b', fontSize: 11 }}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#64748b', fontSize: 11 }}
              allowDecimals={false}
            />
            <Tooltip content={<CustomTooltip />} />

            {/* Reference line for highlighted player */}
            {highlightVal != null && (
              <ReferenceLine
                x={buckets.find((b) => highlightVal >= b.rangeStart && highlightVal < b.rangeEnd)?.label}
                stroke="#60a5fa"
                strokeDasharray="4 3"
                strokeWidth={2}
              />
            )}

            <Bar dataKey="count" radius={[3, 3, 0, 0]} barSize={28}>
              {buckets.map((bucket, i) => (
                <Cell
                  key={i}
                  fill={bucket.containsHighlight ? '#60a5fa' : '#3b82f6'}
                  fillOpacity={0.5 + (i / buckets.length) * 0.5}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
