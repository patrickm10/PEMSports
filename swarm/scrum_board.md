# Scrum Board & Task Tracker

**Last Sync:** 2026-07-23

## Coverage + UI Overhaul Swarm (active)

| Agent | Role | Status | Notes |
| :--- | :--- | :---: | :--- |
| **Lead / Orchestrator** | Edit + reconcile | STOPPED | Handoff written; FE lint/test/build unverified |
| **Discovery: Data** | Read-only | DONE | Seasonal HEAD 2025-only for skill positions |
| **Discovery: Backend** | Read-only | DONE | No year=2025 API default; prod seasonal gap |
| **Discovery: Frontend** | Read-only | DONE | API-driven years; UI overhaul partially applied |
| **Discovery: Production** | Read-only | DONE | API up; branding + seasonal stale |
| **Adversarial: Coverage** | Read-only | NOT STARTED | Blocked by handoff stop |
| **Adversarial: UI** | Read-only | NOT STARTED | Blocked by handoff stop |

### Gates

| Gate | Status |
|------|--------|
| G1 Root cause documented | DONE (`DATA_COVERAGE_AUDIT.md`) |
| G2 Local bake + pytest | DONE (168 passed) |
| G3 Frontend lint/test/build | **PENDING** |
| G4 Adversarial reviews + docs | **PENDING** |
| G5 Commit restored seasonal parquet | **PENDING** (uncommitted) |
| G6 Render redeploy with validate | **PENDING** |
| G7 Vercel redeploy (brand + UI) | **PENDING** |
| G8 Live `/QB/seasons` = 2020–2025 | **PENDING** |

**Playbook:** [`coverage_overhaul_orchestration.md`](coverage_overhaul_orchestration.md)  
**Handoff:** [`../state_handoff.md`](../state_handoff.md)

---

## Go-Live Swarm (superseded facts — see DEPLOYMENT_STATUS + handoff)

| Gate | 2026-07-22 doc | 2026-07-23 live |
|------|----------------|-----------------|
| G1 Data plane | API timeout | API **up** but seasonal skill positions **2025-only** |
| G3 Frontend | Live | Live; **pre-rebrand** bundle |

---

## Swarm Infrastructure

- [x] [Go-Live Orchestration](go_live_orchestration.md)
- [x] [Coverage Overhaul Orchestration](coverage_overhaul_orchestration.md)
- [x] [V3 Feature Roadmap](v3_feature_roadmap.md)
- [x] [Subagent Verification Checklist](subagent_verification_checklist.md)
- [x] [Automated Swarm Auditor](../scripts/verify_swarm.py)
- [x] [Standardized Reasoning Template](reasoning.md)
- [x] [PEM data coverage skill](../.agents/skills/pem-data-coverage/SKILL.md)

---

*Maintained by Lead Orchestrator*
