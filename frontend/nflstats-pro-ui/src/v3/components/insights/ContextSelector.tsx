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

/** Canonical observed surfaces — only Grass/Turf are normalized server-side. */
const SURFACE_VALUES = ['Grass', 'Turf'];

interface ContextSelectorProps {
  year: string;
}

export function ContextSelector({ year }: ContextSelectorProps) {
  const position = useInsightsStore((s) => s.position);
  const context = useInsightsStore((s) => s.context);
  const contextValue = useInsightsStore((s) => s.contextValue);
  const setContext = useInsightsStore((s) => s.setContext);
  const setContextValue = useInsightsStore((s) => s.setContextValue);

  const needsRemoteValues = context !== 'surface';
  const { data: contextData, isLoading, isError, refetch } = useInsightsContextValues(
    position,
    context,
    year,
    needsRemoteValues,
  );

  const values = useMemo(() => {
    if (context === 'surface') return SURFACE_VALUES;
    return contextData?.values ?? [];
  }, [context, contextData?.values]);

  useEffect(() => {
    if (!values.length) return;
    if (!values.includes(contextValue)) {
      setContextValue(values[0]);
    }
  }, [context, values, contextValue, setContextValue]);

  const emptyHint =
    context === 'home_away'
      ? 'Home vs away isn’t available for this selection.'
      : context === 'opponent'
        ? 'No opponents found for this season.'
        : context === 'stadium'
          ? 'No stadiums found for this season.'
          : null;

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
            aria-pressed={context === ctx.id}
            onClick={() => setContext(ctx.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500/50 ${
              context === ctx.id
                ? 'bg-white/10 text-white border-white/20'
                : 'text-slate-400 border-transparent hover:bg-white/[0.04]'
            }`}
          >
            {ctx.label}
          </button>
        ))}
      </div>

      {needsRemoteValues && isLoading && (
        <p className="text-xs text-slate-500 animate-pulse">Loading context values…</p>
      )}

      {needsRemoteValues && isError && (
        <div className="text-xs text-rose-300" role="alert">
          Could not load context values.{' '}
          <button type="button" onClick={() => void refetch()} className="underline font-semibold">
            Retry
          </button>
        </div>
      )}

      {needsRemoteValues && !isLoading && !isError && values.length === 0 && emptyHint && (
        <p className="text-xs text-slate-500">{emptyHint}</p>
      )}

      {values.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-1 max-h-36 overflow-y-auto custom-scrollbar">
          {values.map((val) => (
              <button
                key={val}
                type="button"
                aria-pressed={contextValue === val}
                onClick={() => setContextValue(val)}
                className={`px-3 py-1 rounded-md text-xs font-medium border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500/50 ${
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
