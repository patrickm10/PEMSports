import { describe, it, expect } from 'vitest';
import { encodeWorkspaceState, decodeWorkspaceState } from './urlState';
import { WorkspaceState } from '../../models/v3/workspace';

describe('V3 URL State Serialization', () => {
  it('should encode and decode standard params correctly', () => {
    const state: WorkspaceState = {
      year: 2025,
      week: 4,
      position: 'wr',
      viewMode: 'grid'
    };
    
    const params = encodeWorkspaceState(state);
    expect(params.get('y')).toBe('2025');
    expect(params.get('w')).toBe('4');
    expect(params.get('p')).toBe('wr');
    
    const decoded = decodeWorkspaceState(params.toString());
    expect(decoded.year).toBe(2025);
    expect(decoded.week).toBe(4);
    expect(decoded.position).toBe('wr');
  });

  it('should handle complex logical filters via Base64', () => {
    const state: WorkspaceState = {
      year: 2024,
      week: 1,
      position: 'qb',
      filters: {
        conjunction: 'AND',
        conditions: [
          { field: 'FPTS', operator: 'gt', value: 250 },
          { field: 'Team Name', operator: 'in', value: ['KC', 'PHI'] }
        ]
      }
    };
    
    const params = encodeWorkspaceState(state);
    expect(params.has('f')).toBe(true);
    
    const decoded = decodeWorkspaceState(params.toString());
    expect(decoded.filters).toEqual(state.filters);
    expect(decoded.filters?.conditions[0].field).toBe('FPTS');
  });

  it('should be resilient to malformed Base64', () => {
    const decoded = decodeWorkspaceState('f=invalid-base64');
    expect(decoded).toEqual({});
  });
});
