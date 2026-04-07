/**
 * V3 URL State Serialization Utility
 * High-agility Base64 encoding for complex situational filters.
 * Reclaims context space in the URL while allowing full deep-linking.
 */

import type { WorkspaceFilter, WorkspaceState } from "../../models/v3/workspace";

const ENCODED_PARAM = 'f'; // 'f' for filters/focus

export function encodeWorkspaceState(state: WorkspaceState): URLSearchParams {
  const params = new URLSearchParams();
  
  // Standard sync params (human readable)
  params.set('y', state.year.toString());
  params.set('w', state.week.toString());
  params.set('p', state.position.toLowerCase());
  
  // Encoded bucket (Base64)
  const context: Partial<WorkspaceState> = {};
  if (state.filters) context.filters = state.filters;
  if (state.focusId) context.focusId = state.focusId;
  if (state.viewMode) context.viewMode = state.viewMode;
  
  if (Object.keys(context).length > 0) {
    const json = JSON.stringify(context);
    const base64 = btoa(unescape(encodeURIComponent(json)));
    params.set(ENCODED_PARAM, base64);
  }
  
  return params;
}

export function decodeWorkspaceState(search: string): Partial<WorkspaceState> {
  const params = new URLSearchParams(search);
  const state: Partial<WorkspaceState> = {};
  
  // Parse standard params
  const y = params.get('y');
  const w = params.get('w');
  const p = params.get('p');
  
  if (y) state.year = parseInt(y, 10);
  if (w) state.week = parseInt(w, 10);
  if (p) state.position = p;
  
  // Parse encoded context bucket
  const encoded = params.get(ENCODED_PARAM);
  if (encoded) {
    try {
      const json = decodeURIComponent(escape(atob(encoded)));
      const context = JSON.parse(json) as Partial<WorkspaceState>;
      Object.assign(state, context);
    } catch (e) {
      console.error("Failed to decode workspace context:", e);
    }
  }
  
  return state;
}
