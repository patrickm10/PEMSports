---
name: root-cause-analysis-gate
description: >
  When troubleshooting repeats the same checks twice without progress, stop
  running trivial probes and switch to root-cause analysis (RCA). Produce a plan
  with likely causes and concrete fixes for user approval before continuing.
---

# Root-cause analysis gate (NFLStatsAnalyzer)

## When this applies

Use this skill when:
- You have performed **two rounds** of basic checks (e.g., pinging endpoints, re-running the same curl/IWR, restarting services, repeating netstat checks) and the issue is still not resolved.
- The conversation is showing a loop: “check → same failure → check again”.

## Hard rules

1. **Stop repeating probes.**
   - Do not re-run the same “is it up” check a third time unless it tests a *new* hypothesis.

2. **Switch from verification to diagnosis.**
   - Prefer reading the *source of truth* (startup code, env parsing, routing tables, client fetch wrappers) over repeating runtime pings.

3. **One primary hypothesis at a time.**
   - Pick the most likely root cause, list 1–2 alternates, and drive toward disambiguation with the smallest possible evidence.

4. **Propose fixes for approval before editing.**
   - After two rounds, present a short RCA + fix plan and ask for the scope to implement (even if you expect approval).

## RCA output format (required)

```text
SYMPTOMS:
- ...

MOST LIKELY ROOT CAUSE:
- ...

ALTERNATE CAUSES (1–2):
- ...

PLAN:
- Evidence to gather (≤3 targeted reads or commands)
- Fix (specific files / functions to change)
- Verification (exact endpoint(s) / UI action)

DECISION NEEDED:
- What I need the user to approve (scope/behavior change)
```

## Examples (what “trivial checks” means here)

- Re-running `Invoke-WebRequest`/curl to the same URL repeatedly.
- Repeating `netstat` after already confirming a listener.
- Restarting a service without changing startup parameters or verifying which entrypoint is being executed.

## Preferred evidence sources in this repo

- Backend startup path: `src/backend/main.py` and any `init_db()` call sites
- API routing: `src/backend/api/*_routes.py`
- Query layer: `src/backend/data/query_engine.py`
- Frontend fetch wrappers: `frontend/nflstats-pro-ui/src/api/*`

