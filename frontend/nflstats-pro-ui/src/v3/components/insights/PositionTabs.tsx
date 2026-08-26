import type { InsightPosition } from '../../../api/insightsTypes';

const POSITIONS: { id: InsightPosition; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'qb', label: 'QB' },
  { id: 'rb', label: 'RB' },
  { id: 'wr', label: 'WR' },
  { id: 'te', label: 'TE' },
];

interface PositionTabsProps {
  active: InsightPosition;
  onChange: (position: InsightPosition) => void;
}

export function PositionTabs({ active, onChange }: PositionTabsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {POSITIONS.map((pos) => (
        <button
          key={pos.id}
          type="button"
          onClick={() => onChange(pos.id)}
          className={`px-4 py-1.5 rounded-lg text-sm font-semibold transition-colors border ${
            active === pos.id
              ? 'bg-sky-500/20 text-sky-300 border-sky-500/40'
              : 'bg-white/[0.03] text-slate-400 border-white/10 hover:text-white hover:bg-white/[0.06]'
          }`}
        >
          {pos.label}
        </button>
      ))}
    </div>
  );
}
