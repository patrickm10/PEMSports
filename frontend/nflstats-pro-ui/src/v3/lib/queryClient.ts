import { QueryClient } from '@tanstack/react-query';

/**
 * Global TanStack Query Client for V3
 * Configured with 5-minute stale-time and 10-minute cache-time.
 * Retries are disabled by default for 404/Schema-Failures to avoid resource waste.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 10,   // 10 minutes
      retry: (failureCount, error: any) => {
        if (error?.status === 404) return false;
        return failureCount < 2;
      },
      refetchOnWindowFocus: false,
    },
  },
});
