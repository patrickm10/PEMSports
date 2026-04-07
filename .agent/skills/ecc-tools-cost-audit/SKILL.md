---
name: ecc-tools-cost-audit
description: Audit the token cost and ROI of ECC skills, rules, and agents to optimize the context budget.
origin: ECC direct-port adaptation
version: "1.0.0"
---

# ECC Tools Cost Audit

Use this when you need to measure the token overhead of your ECC setup and identify candidates for compression or removal.

## When to Use
- "Audit my current session's token overhead"
- "Calculate ROI for my installed skills"
- "Identify the heaviest components in my context budget"
- "Generate a report for context optimization"

## Workflow

### 1. Measure Token Overhead
Use the `ECC_TOKENIZER` to get precise counts for each component (Skills, Rules, MCP Tools, Metadata).

### 2. Calculate ROI
Evaluate each component using the formula:
`ROI = (usage * importance) / token_cost`

### 3. Classify Components
Based on the ROI score and frequency of use, classify components as:
- **Always-on core**: High ROI, high usage.
- **Lazy-load candidates**: High cost, low usage (load only when needed).
- **Compression targets**: High cost, high importance (optimize for space).
- **Removal candidates**: Low ROI, low usage.

### 4. Propose Optimizations
Provide an actionable report explicitly classifying components and suggesting specific removals or compressions to reclaim context space.

## Related Skills
- `context-budget`
- `dashboard-builder`
