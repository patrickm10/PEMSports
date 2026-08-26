import { useEffect, useMemo } from 'react';
import type { InsightContext } from '../../../api/insightsTypes';
import { useInsightsContextValues } from '../../../hooks/useInsights';
import { useInsightsStore } from '../../../stores/insightsStore';

const CONTEXTS: { id: InsightContext; label: string }[] = [
  { id: 'surface', label: 'Surface' },
  { id: 'opponent', label: 'Opponent' },
  { id: 'stadium', label: 'Stadium' },
  { id: 'home_away', label: 'Home vs Away' },
];

const SURFACE_DEFAULTS = ['Grass', 'Turf'];
const HOME_AWAY_DEFAULTS = ['Home', 'Away'];

interface ContextSelectorProps {
  year: string;
}

export function ContextSelector({ year }: ContextSelectorProps) {
  const position = useInsightsStore((s) => s.position);
  const context = useInsightsStore((s) => s.context);
  const contextValue = useInsightsStore((s) => s.contextValue);
  const setContext = useInsightsStore((s) => s.setContext);
  const setContextValue = useInsightsStore((s) => s.setContextValue);

  const { data: contextData } = useInsightsContextValues(position, context, year);

  const values = useMemo(() => {
    if (context === 'surface') return SURFACE_DEFAULTS;
    if (context === 'home_away') return HOME_AWAY_DEFAULTS;
    return contextData?.values ?? [];
  }, [context, contextData?.values]);

  useEffect(() => {
    if (!values.length) return;
    if (!values.includes(contextValue)) {
      setContextValue(values[0]);
    }
  }, [context, values, contextValue, setContextValue]);

  return (
    <div className="glass-card rounded-xl p-4 space-y-3">
      <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
        Context
      </div>
      <div className="flex flex-wrap gap-2">
        {CONTEXTS.map((ctx) => (
          <button
            key={ctx.id}
            type="button"
            onClick={() => setContext(ctx.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
              context === ctx.id
                ? 'bg-white/10 text-white border-white/20'
                : 'text-slate-400 border-transparent hover:bg-white/[0.04]'
            }`}
          >
            {ctx.label}
          </button>
        ))}
      </div>

      {values.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-1">
          {values.map((val) => (
            <button
              key={val}
              type="button"
              onClick={() => setContextValue(val)}
              className={`px-3 py-1 rounded-md text-xs font-medium border transition-colors ${
                contextValue === val
                  ? 'bg-sky-500/15 text-sky-300 border-sky-500/30'
                  : 'text-slate-400 border-white/10 hover:text-slate-200'
              }`}
            >
              {val}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
