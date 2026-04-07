import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import type { WorkspaceState } from '../../models/v3/workspace';

const API_BASE = 'http://127.0.0.1:8000/api';

export function useV3Rankings(state: WorkspaceState) {
  return useQuery({
    queryKey: ['v3-rankings', state.position, state.year, state.week, state.filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (state.year) params.set('year', state.year.toString());
      if (state.week) params.set('week', state.week.toString());
      
      // Pass the encoded filter bucket if present
      if (state.filters) {
        const json = JSON.stringify({ filters: state.filters });
        const encoded = btoa(unescape(encodeURIComponent(json)));
        params.set('f', encoded);
      }

      const { data } = await axios.get(`${API_BASE}/${state.position}s/stats`, { params });
      return data;
    },
    enabled: !!state.position,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}
