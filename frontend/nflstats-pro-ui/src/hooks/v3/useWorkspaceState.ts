/**
 * V3 Workspace State Hook
 * Primary high-agility state engine for the Context-First analytics workbench.
 * Syncs URL search params with Base64-encoded situational context.
 */

import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { WorkspaceState } from '../../models/v3/workspace';
import { decodeWorkspaceState, encodeWorkspaceState } from '../../utils/v3/urlState';

const DEFAULT_STATE: WorkspaceState = {
  year: 2024,
  week: 1,
  position: 'qb',
  viewMode: 'grid'
};

export function useWorkspaceState() {
  const [searchParams, setSearchParams] = useSearchParams();

  const state = useMemo(() => {
    const decoded = decodeWorkspaceState(searchParams.toString());
    return { ...DEFAULT_STATE, ...decoded } as WorkspaceState;
  }, [searchParams]);

  const updateState = useCallback((partial: Partial<WorkspaceState>) => {
    const newState = { ...state, ...partial };
    setSearchParams(encodeWorkspaceState(newState));
  }, [state, setSearchParams]);

  const resetFilters = useCallback(() => {
    updateState({ filters: undefined });
  }, [updateState]);

  return {
    state,
    updateState,
    resetFilters,
  };
}
