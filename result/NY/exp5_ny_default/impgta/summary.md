# impgta — exp5_ny_default

Default-config comparison (fixed environment).

## impgta

### Metrics

| metric | value |
| --- | --- |
| TR | 13981.21 |
| CR | 0.493400 |
| BPT | 0.072461 |
| delivered_parcels | 2467 |
| accepted_assignments | 2658 |
| timed_out_parcels | 180 |

### Local Platform

| field | value |
| --- | --- |
| local_matches | 619 |
| cross_platform_matches | 1848 |
| unresolved_parcels | 2353 |
| timed_out_parcels | 180 |

### Cooperating Platforms

| platform | own_task_count | accepted_cross | cooperative_revenue |
| --- | --- | --- | --- |
| P1 | 5000 | 455 | 1221.35 |
| P2 | 5200 | 447 | 1199.36 |
| P3 | 5400 | 423 | 1140.73 |
| P4 | 5600 | 523 | 1420.86 |

### Timing

- **started_at**: 2026-05-16T04:37:29+00:00
- **finished_at**: 2026-05-16T04:56:41+00:00
- **duration_seconds**: 1152.284871

### Config

```json
{
  "local_payment_ratio_zeta": 0.5,
  "cross_platform_sharing_rate_mu2": 0.3
}
```
