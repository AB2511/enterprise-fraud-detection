# Train/Validation/Test Split Benchmark Report

**Date:** 2026-08-02

## Performance Metrics

| Metric | Value |
|--------|-------|
| Cold Run (First Execution) | 166.19s |
| Warm Run (Cached Artifact) | 9.65s |
| Speedup Factor | 17.22x |
| Cold Throughput | 3,553 rows/sec |
| Warm Throughput | 61,207 rows/sec |
| Peak Memory | 2742.29 MB |
| Output Size | 97.81 MB |
| Total Rows | 590,540 |

## Analysis

- **Cold run** includes feature dropping + engineering + splitting
- **Warm run** uses cached intermediate artifact (after_engineering.parquet)
- **Speedup:** 17.2x faster with caching
- **Time saved:** 156.5 seconds
