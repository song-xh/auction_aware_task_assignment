# basegta — exp5_ny_default

Default-config comparison (fixed environment).

## basegta

### Metrics

| metric | value |
| --- | --- |
| TR | 14144.50 |
| CR | 0.514600 |
| BPT | 0.011906 |
| delivered_parcels | 2573 |
| accepted_assignments | 2777 |
| timed_out_parcels | 191 |

### Local Platform

| field | value |
| --- | --- |
| local_matches | 915 |
| cross_platform_matches | 1658 |
| unresolved_parcels | 2236 |
| timed_out_parcels | 191 |

### Cooperating Platforms

| platform | own_task_count | accepted_cross | cooperative_revenue |
| --- | --- | --- | --- |
| P1 | 5000 | 411 | 1119.88 |
| P2 | 5200 | 401 | 1087.23 |
| P3 | 5400 | 412 | 1118.30 |
| P4 | 5600 | 434 | 1193.37 |

### Timing

- **started_at**: 2026-05-16T04:20:56+00:00
- **finished_at**: 2026-05-16T04:37:14+00:00
- **duration_seconds**: 978.535707

### Config

```json
{
  "local_payment_ratio_zeta": 0.5,
  "cross_platform_sharing_rate_mu2": 0.3
}
```
