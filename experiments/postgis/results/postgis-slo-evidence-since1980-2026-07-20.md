# PostGIS open-loop production evidence

- Conservative repeated-window lower bound: **5,000 TPS**
- First failed target: **5,500 TPS**
- Completed transactions in repeated windows: **14,801,450**
- Maximum exploratory completion rate: **25,166.22 TPS**

Passing requires zero database transaction failures, completion p99 at or below 20 ms, and skipped arrivals at or below 0.100% in every repeat.

| Target TPS | mean completed TPS | max p99 ms | max skip rate | DB failures | all 3 pass |
|---:|---:|---:|---:|---:|---:|
| 5000 | 4986.15 | 5.778 | 0.0678% | 0 | True |
| 5500 | 5490.06 | 6.177 | 0.1929% | 0 | False |
| 6000 | 6003.99 | 5.857 | 0.1214% | 0 | False |
| 6500 | 6497.41 | 5.714 | 0.0963% | 0 | True |
| 7000 | 6996.42 | 5.991 | 0.1150% | 0 | False |
| 7500 | 7489.51 | 5.993 | 0.1959% | 0 | False |
| 10000 | 9994.51 | 6.321 | 0.1458% | 0 | False |
| 15000 | 14958.69 | 9.603 | 0.2913% | 0 | False |
| 20000 | 19817.76 | 22.957 | 1.3387% | 0 | False |

## Five-minute sustained checks

| Target TPS | completed TPS | p99 ms | skip rate | DB failures | pass |
|---:|---:|---:|---:|---:|---:|
| 6500 | 6494.67 | 5.858 | 0.1117% | 0 | False |
| 7000 | 6987.24 | 6.770 | 0.1423% | 0 | False |

## Decision rule

The conservative repeated-window lower bound is the highest target in the contiguous ascending prefix for which every 60-second repeat passes. A higher isolated pass after the first failed target is reported but cannot raise the lower bound.
