/** Display names for position ids. Keys stay lowercase API ids. */
export const POSITION_FULL_NAME: Record<string, string> = {
  qb: 'Quarterback',
  rb: 'Running Back',
  wr: 'Wide Receiver',
  te: 'Tight End',
  k: 'Kicker',
  dst: 'Defense / Special Teams',
};

export function positionFullName(id: string): string {
  return POSITION_FULL_NAME[id.toLowerCase()] ?? id.toUpperCase();
}
