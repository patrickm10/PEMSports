# Swarm Communication Protocol

## 🛡️ The Architecture Guardrail

All agents MUST read `swarm/architect_critique.md` before making changes.

## 🧠 The Reasoning Loop

BEFORE coding, any implementation agent MUST:

1. Document their plan in `swarm/reasoning.md`.
2. Ensure compliance with the **High-Hardness Baseline** in `swarm/architect_critique.md`.
3. Tag the **Architect** for a review.
4. Wait for "APPROVED" in `swarm/architect_critique.md`. The Architect has absolute VETO power over non-compliant plans.

## 📊 The Status Heartbeat

At the end of every turn, agents MUST update `swarm/scrum_board.md` with:

- Current Task
- Blockers
- % Complete

## 🚦 The Merge Gate

Only the **Merge Master** is allowed to run `git merge main` or merge feature branches.
All agents work in their assigned branches.
