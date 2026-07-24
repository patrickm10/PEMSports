import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { PlayersApi } from '../api/playersApi';
import type { PlayerSearchResponse } from '../api/playerTypes';

const DEBOUNCE_MS = 250;
const MIN_QUERY_LENGTH = 2;

function useDebouncedValue<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), ms);
    return () => window.clearTimeout(id);
  }, [value, ms]);
  return debounced;
}

interface UsePlayerSearch {
  results: PlayerSearchResponse['results'];
  isLoading: boolean;
  error: Error | null;
  isReady: boolean;
}

export function usePlayerSearch(rawQuery: string): UsePlayerSearch {
  const debounced = useDebouncedValue(rawQuery.trim(), DEBOUNCE_MS);
  const enabled = debounced.length >= MIN_QUERY_LENGTH;

  const query = useQuery({
    queryKey: ['players', 'search', debounced],
    queryFn: ({ signal }) => PlayersApi.search(debounced, 10, signal),
    enabled,
    staleTime: 30_000,
  });

  return {
    results: enabled ? query.data?.results ?? [] : [],
    isLoading: enabled && query.isFetching,
    error: (query.error as Error) ?? null,
    isReady: enabled,
  };
}
