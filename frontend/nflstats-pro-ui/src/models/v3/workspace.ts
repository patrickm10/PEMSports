/**
 * V3 Workspace Model Definitions
 * Strictly typed structures for the "Context-First" analytics workbench.
 */

export type FilterOperator = 'eq' | 'neq' | 'gt' | 'gte' | 'lt' | 'lte' | 'contains' | 'in';

export interface FilterCondition {
  field: string;
  operator: FilterOperator;
  value: any;
}

export interface WorkspaceFilter {
  conjunction: 'AND' | 'OR';
  conditions: FilterCondition[];
}

export const WORKSPACE_VERSION = '3.0.0'; // Dummy export for ESM compatibility

export interface WorkspaceState {
  // Standard sync params (human readable)
  year: number;
  week: number;
  position: string;
  
  // Encoded context (Base64)
  filters?: WorkspaceFilter;
  
  // View specific state
  focusId?: string; // Selected player/entity
  viewMode?: 'grid' | 'delta' | 'compare';
}
