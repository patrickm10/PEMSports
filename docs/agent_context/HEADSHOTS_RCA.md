# Headshots RCA (ab152d5 vs 9db1554)

```text
SYMPTOMS: rankings/deploy broke after headshot feat; UUID joins / empty seasons / broken images.
MOST LIKELY ROOT CAUSE: enrich hard-fail in Render build + players.csv numeric espn_id inference skipping players table (bake fail-open) + rankings SQL JOIN rewrite.
FIRST FAILING LAYER: build enrich exit≠0 (then bake players skip, then query_engine JOIN, then UI CDN mangling).
FIX DIRECTION: ALL_VARCHAR bake + fail-open enrich + Python URL attach (no rankings JOIN) + staticAssetUrl http passthrough.
GATE: bake+validate+/seasons 2020–2025 before UI ships.
```
