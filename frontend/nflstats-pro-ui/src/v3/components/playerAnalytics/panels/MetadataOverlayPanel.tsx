import React from 'react';
import type {
  AggregateRow,
  MetadataOverlayModel,
} from '../../../../components/charts/contract';

interface Props {
  data: MetadataOverlayModel | null;
  isLoading?: boolean;
  error?: Error | null;
}

const fmt = (v: number | null) => (v === null ? '—' : v.toFixed(1));

interface CellProps {
  label: string;
  row: AggregateRow;
}

const Cell: React.FC<CellProps> = ({ label, row }) => (
  <div className="flex flex-col gap-0.5 px-3 py-2 rounded-lg bg-slate-950/40 border border-white/[0.05]">
    <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
      {label}
    </span>
    <span className="text-sm font-semibold text-white">{fmt(row.ppr)} PPR</span>
    <span className="text-[11px] text-slate-400">
      {row.games} g · {fmt(row.yards)} yds · {fmt(row.tds)} tds
    </span>
  </div>
);

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({
  title,
  children,
}) => (
  <div>
    <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500 mb-2">
      {title}
    </div>
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">{children}</div>
  </div>
);

export const MetadataOverlayPanel: React.FC<Props> = ({
  data,
  isLoading,
  error,
}) => {
  return (
    <section className="rounded-2xl p-5 glass-card border-white/10 min-w-0 space-y-5">
      <div>
        <h3 className="text-white font-bold text-base">Context overlays</h3>
        <p className="text-slate-400 text-xs mt-1">
          Home/away, rest days, and weather. Missing values show as —.
        </p>
      </div>

      {isLoading && (
        <div className="h-32 rounded-xl bg-slate-900/40 border border-slate-800/40 animate-pulse" />
      )}

      {!isLoading && error && (
        <div className="text-sm text-rose-400">
          Unable to load context overlays.
        </div>
      )}

      {!isLoading && !error && !data && (
        <div className="text-sm text-slate-500">
          No context overlays available for this player.
        </div>
      )}

      {!isLoading && !error && data && (
        <div className="space-y-5">
          <Section title="Home / Away">
            <Cell label="Home" row={data.homeAway.home} />
            <Cell label="Away" row={data.homeAway.away} />
          </Section>

          <Section title="Rest days">
            {data.rest.length === 0 ? (
              <div className="col-span-full text-xs text-slate-500">
                No rest-day buckets reported.
              </div>
            ) : (
              data.rest.map((b) => (
                <Cell key={b.bucket} label={b.bucket} row={b.row} />
              ))
            )}
          </Section>

          <Section title="Weather impact">
            {data.weather.length === 0 ? (
              <div className="col-span-full text-xs text-slate-500">
                No weather buckets reported.
              </div>
            ) : (
              data.weather.map((w) => (
                <Cell key={w.key} label={w.key} row={w.row} />
              ))
            )}
          </Section>
        </div>
      )}
    </section>
  );
};
