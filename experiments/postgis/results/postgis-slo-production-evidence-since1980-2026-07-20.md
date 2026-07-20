# PostGIS open-loop production evidence

- Conservative repeated-window lower bound: **10,000 TPS**
- First failed target: **12,000 TPS**
- Completed transactions in repeated windows: **18,864,158**
- Maximum exploratory completion rate: **43,898.03 TPS**

Passing requires zero database transaction failures, completion p99 at or below 20 ms, and skipped arrivals at or below 0.100% in every repeat.
pgbench skips only after 100 ms; completion latency is measured from scheduled start and includes queueing.

| Target TPS | mean completed TPS | max p99 ms | max skip rate | DB failures | all 3 pass |
|---:|---:|---:|---:|---:|---:|
| 10000 | 9984.45 | 13.044 | 0.0576% | 0 | True |
| 12000 | 11981.26 | 15.661 | 0.1333% | 0 | False |
| 14000 | 14001.19 | 27.636 | 0.0351% | 0 | False |
| 16000 | 14479.36 | 149.193 | 21.4666% | 0 | False |
| 18000 | 17969.70 | 92.737 | 0.4448% | 0 | False |
| 19000 | 16787.92 | 134.653 | 19.0239% | 0 | False |
| 20000 | 19915.10 | 100.170 | 0.5748% | 0 | False |

## Decision rule

The conservative repeated-window lower bound is the highest target in the contiguous ascending prefix for which every 60-second repeat passes. A higher isolated pass after the first failed target is reported but cannot raise the lower bound.
