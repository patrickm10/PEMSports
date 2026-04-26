import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Users, TrendingUp, Crown } from 'lucide-react';
import type { Ranking } from '../../models/Ranking';
import type { ResolvedMetric } from '../../utils/metrics';
import { formatMetricValue } from '../../utils/metrics';

interface StatsSummaryProps {
  data: Ranking[];
  metric: ResolvedMetric | null;
  isLoading?: boolean;
}

const cardVariant = {
  hidden: { opacity: 0, y: 12 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.08, duration: 0.35, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] },
  }),
};

export const StatsSummary: React.FC<StatsSummaryProps> = ({ data, metric, isLoading }) => {
  const stats = useMemo(() => {
    if (data.length === 0 || !metric) return null;

    const total = data.length;
    const values = data
      .map((row) => ({ row, value: metric.getValue(row) }))
      .filter((item): item is { row: Ranking; value: number } => item.value !== null);

    if (values.length === 0) return null;

    const averageMetric = values.reduce((sum, item) => sum + item.value, 0) / values.length;
    const top = values.reduce((best, item) => (item.value > best.value ? item : best), values[0]);

    return { total, averageMetric, topPlayer: top.row, topValue: top.value };
  }, [data, metric]);

  if (isLoading || !stats) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[0, 1, 2].map(i => (
          <div key={i} className="h-24 rounded-2xl bg-slate-900/40 border border-slate-800/40 animate-pulse" />
        ))}
      </div>
    );
  }

  const cards = [
    {
      icon: Users,
      label: 'Total Players',
      value: stats.total.toString(),
      accent: 'text-blue-400',
      iconBg: 'bg-blue-500/10 border-blue-500/20',
    },
    {
      icon: TrendingUp,
      label: `Avg ${metric?.shortLabel ?? 'Metric'}`,
      value: formatMetricValue(stats.averageMetric),
      accent: 'text-emerald-400',
      iconBg: 'bg-emerald-500/10 border-emerald-500/20',
    },
    {
      icon: Crown,
      label: 'Top Performer',
      value: stats.topPlayer.player_name,
      subValue: `${formatMetricValue(stats.topValue)} ${metric?.shortLabel ?? ''}`.trim(),
      accent: 'text-amber-400',
      iconBg: 'bg-amber-500/10 border-amber-500/20',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {cards.map((card, i) => (
        <motion.div
          key={card.label}
          custom={i}
          variants={cardVariant}
          initial="hidden"
          animate="visible"
          className="flex items-center gap-4 p-5 rounded-2xl bg-slate-900/30 backdrop-blur-sm border border-slate-800/40 hover:border-slate-700/60 transition-colors"
        >
          <div className={`w-11 h-11 rounded-xl ${card.iconBg} border flex items-center justify-center shrink-0`}>
            <card.icon className={`w-5 h-5 ${card.accent}`} />
          </div>
          <div className="min-w-0">
            <div className="text-xs text-slate-500 font-medium uppercase tracking-wider mb-0.5">
              {card.label}
            </div>
            <div className={`text-lg font-bold truncate ${card.accent}`}>
              {card.value}
            </div>
            {card.subValue && (
              <div className="text-xs text-slate-500">{card.subValue}</div>
            )}
          </div>
        </motion.div>
      ))}
    </div>
  );
};
