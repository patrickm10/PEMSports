---
name: continuous-learning-v2
description: Instinct-based learning system that observes sessions via hooks, creates atomic instincts with confidence scoring, and evolves them into skills/commands/agents. v2.1 adds project-scoped instincts to prevent cross-project contamination.
origin: ECC
version: 2.1.0
---

# Continuous Learning v2.1 - Instinct-Based Architecture

An advanced learning system that turns your Claude Code sessions into reusable knowledge through atomic "instincts" - small learned behaviors with confidence scoring.

## When to Activate
- Setting up automatic learning from Claude Code sessions
- Configuring instinct-based behavior extraction via hooks
- Tuning confidence thresholds for learned behaviors
- Reviewing, exporting, or importing instinct libraries
- Evolving instincts into full skills, commands, or agents
- Managing project-scoped vs global instincts

## The Instinct Model
An instinct is a small learned behavior:
```yaml
---
id: prefer-functional-style
trigger: "when writing new functions"
confidence: 0.7
domain: "code-style"
source: "session-observation"
scope: project
---
# Prefer Functional Style
## Action
Use functional patterns over classes when appropriate.
```

**Properties:**
- **Atomic** -- one trigger, one action
- **Confidence-weighted** -- 0.3 = tentative, 0.9 = near certain
- **Domain-tagged** -- code-style, testing, git, debugging, etc.
- **Scope-aware** -- `project` (default) or `global`

## How It Works
1. **Hooks** capture prompts + tool use deterministically.
2. **Observer agent** analyzes patterns in the background.
3. **Instincts** are created/updated with confidence scores.
4. **Evolution** clusters related instincts into skills/commands.

## Commands
| Command | Description |
|---------|-------------|
| `/instinct-status` | Show all instincts (project-scoped + global) with confidence |
| `/evolve` | Cluster related instincts into skills/commands, suggest promotions |
| `/instinct-export` | Export instincts to file |
| `/instinct-import` | Import instincts from others |
| `/promote` | Promote project instincts to global scope |
| `/projects` | List all known projects and their instinct counts |

## Scope Decision Guide
| Pattern Type | Scope | Examples |
|-------------|-------|---------|
| Language/framework conventions | **project** | "Use React hooks", "Follow Django REST patterns" |
| File structure preferences | **project** | "Tests in `__tests__`/", "Components in src/components/" |
| Security practices | **global** | "Validate user input", "Sanitize SQL" |
| Tool workflow preferences | **global** | "Grep before Edit", "Read before Write" |

## Confidence Scoring
| Score | Meaning | Behavior |
|-------|---------|----------|
| 0.3 | Tentative | Suggested but not enforced |
| 0.5 | Moderate | Applied when relevant |
| 0.7 | Strong | Auto-approved for application |
| 0.9 | Near-certain | Core behavior |

## Privacy
- Observations stay **local** on your machine.
- Only **instincts** (patterns) can be exported — not raw data.
- You control what gets exported and promoted.