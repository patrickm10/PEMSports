import { useEffect, useRef } from 'react';

import { ApiError } from '../api/rankingsApi';
import { useToast } from '../contexts/ToastContext';

/**
 * Surfaces NFLStats API failures as toasts (TanStack Query v5 removed useQuery `onError`).
 */
export function useQueryErrorToast(error: Error | null | undefined, isError: boolean) {
  const { showError } = useToast();
  const lastSig = useRef<string | null>(null);

  useEffect(() => {
    if (!isError) {
      lastSig.current = null;
      return;
    }
    if (!error) return;
    const sig = `${error.message}:${error instanceof ApiError ? error.code ?? '' : ''}`;
    if (lastSig.current === sig) return;
    lastSig.current = sig;
    const code = error instanceof ApiError ? error.code : undefined;
    showError(error.message, code);
  }, [isError, error, showError]);
}
