---
name: offline-audit
description: "You MUST use this when debugging data issues, validating pipelines, or investigating inconsistencies. Prevents inline script execution and enforces structured, reviewable audit workflows."
---

# Offline Audit First Workflow

Convert all debugging, validation, and audit work into structured, reviewable artifacts instead of executing ad hoc scripts in the interaction loop.

This ensures clarity, reproducibility, and controlled execution.

<HARD-GATE>
Do NOT execute shell commands, Python scripts, or multi-step validation logic inline.

Do NOT pipe scripts into the terminal or run one-off audit checks.

All validation logic MUST be proposed first, written to a task.md file, and explicitly approved by the user before execution.
</HARD-GATE>

## Anti-Pattern: "Quick Inline Validation"

Running large inline scripts (pandas, duckdb, shell pipelines) directly in the chat loop creates noise, is hard to review, and breaks iteration flow.

This includes:
- `echo "...python script..." | python`
- `python -c "..."`
- Ad hoc multi-source comparisons executed immediately

These are NEVER allowed without approval.

## Checklist

You MUST create a task for each of these items and complete them in order:

1. **Summarize the issue** — what is broken or inconsistent
2. **Form a hypothesis** — likely root cause
3. **Design validation strategy** — what needs to be checked and why
4. **Propose queries/scripts** — DO NOT execute
5. **Write to task.md** — structured and reviewable
6. **Request approval** — wait before execution
7. **Execute only after approval** — then report findings

## Output Format

All audit responses MUST follow this structure:

```markdown
**Issue:** [brief description]

**Hypothesis:** [root cause explanation]

**Validation Plan:**
- [what will be checked]
- [why this matters]

**Proposed Queries/Scripts:**
```

## Execution Flow

1. **User reports issue**
2. **You summarize and hypothesize**
3. **Design validation strategy**
4. **Propose queries/scripts**
5. **Write to task.md**
6. **Request approval**
7. **User approves**
8. **You execute and report findings**

## Anti-Patterns to Avoid

- Running scripts inline
- Skipping the task.md step
- Assuming you can execute without approval
- Not proposing the validation strategy first

## When to Use This Skill

- Data inconsistencies detected
- Pipeline validation needed
- Source-to-target comparisons
- Debugging data quality issues
- Verifying ETL/ELT logic

## When NOT to Use This Skill

- Simple information retrieval
- Quick file lookups
- Non-data-related tasks
- Tasks that don't involve validation or debugging

## Key Principles

- **Review before execution** — always
- **Structured artifacts** — task.md first
- **Clear separation** — design vs execution
- **User control** — explicit approval required
- **Reproducible audits** — documented and testable

## Example Flow

User: "The player stats in the dashboard don't match the source files."

You:
1. Summarize: "Data mismatch between dashboard and source files"
2. Hypothesize: "Possible ETL transformation error or data ingestion gap"
3. Design: "Compare source files with aggregated dashboard data"
4. Propose: [SQL queries and Python script]
5. Write: task.md with full validation plan
6. Request approval: "Ready to execute validation queries?"
7. User approves
8. Execute and report findings

## Terminal vs Browser Decision

- **Use terminal** for executing approved queries/scripts
- **Use browser** for reviewing source files or data previews
- **Always decide per question** — don't default to one or the other

## Key Output

The terminal output should be:

```
Validation plan documented in task.md
User approved execution
Queries/scripts executed successfully
Findings reported
```

## When to Break the Pattern

NEVER. This skill is mandatory for all audit and debugging work.
