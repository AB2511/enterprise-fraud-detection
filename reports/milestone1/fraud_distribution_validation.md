# Fraud Distribution Validation Report

**Date:** 2026-08-02

## Distribution Summary

| Split | Fraud Rate | Absolute Deviation | Relative Deviation | Status |
|-------|------------|-------------------|-------------------|--------|
| Overall | 3.4990% | — | — | Baseline |
| Train | 3.3833% | -0.1157% | -3.31% | ✅ PASS |
| Validation | 3.9041% | +0.4051% | +11.58% | ✅ PASS |
| Test | 3.4409% | -0.0581% | -1.66% | ✅ PASS |

## Engineering Interpretation

**Acceptable Range:** ±50.0% (±0.500)

✅ **Verdict: ACCEPTABLE TEMPORAL DRIFT**

All splits are within the acceptable ±0.5% deviation range. Fraud rate variation is a natural consequence of temporal ordering.

**Implications:**
- Model must generalize across time periods with varying fraud rates
- This reflects realistic production deployment scenarios
- No corrective action required
