import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Search, Loader2, X, History, Sparkles } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { Modal } from '../modals/Modal';
import { useSearchStore } from '../../../stores/searchStore';
import { usePlayerAnalyticsStore } from '../../../stores/playerAnalyticsStore';
import { usePlayerSearch } from '../../../hooks/usePlayerSearch';
import type { PlayerRef } from '../../../stores/types';
import type { PlayerSearchHit } from '../../../api/playerTypes';
import { staticAssetUrl, PUBLIC_DEFAULT_PLAYER_IMG } from '../../../utils/backendOrigin';

const cn = (...c: Array<string | false | null | undefined>) =>
  twMerge(clsx(c));

function hitToRef(hit: PlayerSearchHit): PlayerRef {
  return {
    player_id: hit.player_id,
    player_name: hit.player_name,
    position: hit.position,
    team: hit.team,
    headshot_url: hit.headshot_url,
  };
}

function resolveHeadshot(headshot: string | null | undefined): string {
  if (!headshot) return PUBLIC_DEFAULT_PLAYER_IMG;
  if (headshot.startsWith('http')) return headshot;
  return staticAssetUrl(headshot);
}

interface SuggestionItemProps {
  player: PlayerRef;
  highlighted: boolean;
  onSelect: () => void;
  id: string;
  trailing?: React.ReactNode;
}

const SuggestionItem: React.FC<SuggestionItemProps> = ({
  player,
  highlighted,
  onSelect,
  id,
  trailing,
}) => (
  <li
    id={id}
    role="option"
    aria-selected={highlighted}
    onClick={onSelect}
    onMouseDown={(e) => e.preventDefault()}
    className={cn(
      'flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer border border-transparent transition-colors',
      highlighted
        ? 'bg-sky-500/10 border-sky-400/30 text-white'
        : 'text-slate-300 hover:bg-white/[0.04]',
    )}
  >
    <img
      src={resolveHeadshot(player.headshot_url)}
      alt=""
      className="w-9 h-9 rounded-full bg-slate-800 object-cover border border-white/10 shrink-0"
      onError={(e) => {
        (e.currentTarget as HTMLImageElement).src = PUBLIC_DEFAULT_PLAYER_IMG;
      }}
    />
    <div className="flex-1 min-w-0">
      <div className="text-sm font-semibold truncate">{player.player_name}</div>
      <div className="text-[11px] text-slate-500 uppercase tracking-wider">
        {player.position?.toUpperCase() ?? '—'} ·{' '}
        {player.team?.toUpperCase() ?? '—'}
      </div>
    </div>
    {trailing && <div className="shrink-0 text-xs text-slate-500">{trailing}</div>}
  </li>
);

interface SearchModalProps {
  /**
   * Optional side-effect callback. Fires AFTER the store is updated
   * with the selected player. Use it for non-store-owned concerns (e.g.
   * navigation in App.tsx is handled by useEffect on selectedPlayer,
   * so most consumers will leave this undefined).
   */
  onPlayerSelected?: (player: PlayerRef) => void;
}

/**
 * Single-component search modal: input, debounced suggestions, recents.
 * State lives in zustand stores (`useSearchStore`, `usePlayerAnalyticsStore`).
 * No navigation side effects originate here — selection only mutates the
 * UI stores; App.tsx subscribes and updates navigation.
 */
export const SearchModal: React.FC<SearchModalProps> = ({ onPlayerSelected }) => {
  const isOpen = useSearchStore((s) => s.isOpen);
  const close = useSearchStore((s) => s.close);
  const query = useSearchStore((s) => s.query);
  const setQuery = useSearchStore((s) => s.setQuery);
  const clearQuery = useSearchStore((s) => s.clearQuery);
  const recents = useSearchStore((s) => s.recentPlayers);
  const pushRecent = useSearchStore((s) => s.pushRecent);

  const selectPlayer = usePlayerAnalyticsStore((s) => s.selectPlayer);
  const setComparison = usePlayerAnalyticsStore((s) => s.setComparison);
  const selectedPlayer = usePlayerAnalyticsStore((s) => s.selectedPlayer);
  const pickMode = useSearchStore((s) => s.pickMode);

  const inputRef = useRef<HTMLInputElement>(null);
  const { results, isLoading, isReady, error } = usePlayerSearch(query);

  const items: PlayerRef[] = useMemo(() => {
    if (isReady) return results.map(hitToRef);
    return recents;
  }, [isReady, results, recents]);

  const itemsSignature = useMemo(
    () => items.map((p) => p.player_id).join('|'),
    [items],
  );

  const [highlightState, setHighlightState] = useState({ sig: '', index: 0 });
  const highlightIndex =
    highlightState.sig === itemsSignature ? highlightState.index : 0;

  const setHighlightIndex = (index: number | ((i: number) => number)) => {
    setHighlightState((prev) => {
      const current = prev.sig === itemsSignature ? prev.index : 0;
      const next = typeof index === 'function' ? index(current) : index;
      return { sig: itemsSignature, index: next };
    });
  };

  useEffect(() => {
    if (isOpen) {
      const id = window.setTimeout(() => inputRef.current?.focus(), 30);
      return () => window.clearTimeout(id);
    }
  }, [isOpen]);

  const handleSelect = (player: PlayerRef) => {
    if (
      pickMode === 'compare' &&
      selectedPlayer &&
      selectedPlayer.player_id !== player.player_id
    ) {
      setComparison(player);
    } else {
      selectPlayer(player);
    }
    pushRecent(player);
    onPlayerSelected?.(player);
    close();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightIndex((i) => Math.min(i + 1, items.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const target = items[highlightIndex];
      if (target) handleSelect(target);
    }
  };

  const showRecents = !isReady && items.length > 0;
  const showEmpty =
    isReady && !isLoading && !error && items.length === 0;
  const trailingForRecent = (
    <span className="inline-flex items-center gap-1">
      <History size={12} /> Recent
    </span>
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={close}
      size="md"
      title={pickMode === 'compare' ? 'Compare player' : 'Search'}
      description="Find a player at any position."
      contentClassName="px-4 pb-4 pt-3"
      initialFocusRef={inputRef as React.RefObject<HTMLElement | null>}
    >
      <div className="relative mb-3">
        <Search
          size={16}
          className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500"
        />
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-label="Find a player"
          aria-expanded={isOpen}
          aria-controls="search-suggestions"
          aria-activedescendant={
            items.length > 0 ? `search-option-${highlightIndex}` : undefined
          }
          aria-autocomplete="list"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Try “Justin Jefferson” or “Mahomes”…"
          className="w-full bg-slate-950/60 border border-white/[0.08] rounded-xl py-2.5 pl-10 pr-10 text-sm text-slate-100 placeholder:text-slate-600 outline-none focus:border-sky-500/40 focus:ring-1 focus:ring-sky-500/30"
        />
        {query && (
          <button
            type="button"
            onClick={clearQuery}
            aria-label="Clear search"
            className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 rounded-md text-slate-500 hover:text-slate-200 hover:bg-white/[0.06]"
          >
            <X size={14} />
          </button>
        )}
        {isLoading && (
          <Loader2
            size={14}
            className="absolute right-9 top-1/2 -translate-y-1/2 text-sky-400 animate-spin"
          />
        )}
      </div>

      {showRecents && (
        <div className="mb-2 px-1 text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em]">
          Recent
        </div>
      )}
      {!isReady && items.length === 0 && (
        <div className="flex items-center gap-2 text-xs text-slate-500 px-2 py-3">
          <Sparkles size={14} className="text-sky-400" />
          Start typing to search across QB, RB, WR, TE, K, and DST.
        </div>
      )}

      <ul
        id="search-suggestions"
        role="listbox"
        aria-label="Player suggestions"
        className="space-y-1 max-h-[55vh] overflow-y-auto custom-scrollbar pr-1"
      >
        {items.map((player, idx) => (
          <SuggestionItem
            key={player.player_id}
            id={`search-option-${idx}`}
            player={player}
            highlighted={idx === highlightIndex}
            onSelect={() => handleSelect(player)}
            trailing={!isReady ? trailingForRecent : undefined}
          />
        ))}
      </ul>

      {showEmpty && (
        <div className="text-center py-6 text-sm text-slate-500">
          No players found for “{query}”.
        </div>
      )}
      {error && (
        <div className="text-center py-4 text-sm text-rose-400" role="alert">
          Search is unavailable right now. Try again in a moment.
        </div>
      )}
    </Modal>
  );
};
