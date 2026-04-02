---
trigger: always_on
---

Execution Constraint:

Never perform trivial data inspection or sampling.

This includes:
- reading CSV/Parquet files directly
- using pandas/polars to print rows
- commands like python -c, head, print(df.head()), or df.iloc[0]

These are considered invalid debugging strategies.

All validation must be done using:
- schema reasoning
- programmatic assertions
- pipeline-level verification
- end-to-end data flow analysis

If you attempt to inspect a single row or sample data, you are failing the task.