# capa — exp5_ny_default

Default-config comparison (fixed environment).

## capa

### Metrics

| metric | value |
| --- | --- |
| TR | 11009.31 |
| CR | 0.482000 |
| BPT | 0.008403 |
| delivered_parcels | 2410 |
| accepted_assignments | 2479 |
| timed_out_parcels | 61 |

### Local Platform

| field | value |
| --- | --- |
| local_matches | 618 |
| cross_platform_matches | 1792 |
| unresolved_parcels | 2519 |
| timed_out_parcels | 61 |

### Cooperating Platforms

| platform | own_task_count | accepted_cross | cooperative_revenue |
| --- | --- | --- | --- |
| P1 | 5000 | 356 | 940.4340 |
| P2 | 5200 | 351 | 924.3112 |
| P3 | 5400 | 477 | 1265.49 |
| P4 | 5600 | 608 | 1604.56 |

### Timing

- **started_at**: 2026-05-16T03:53:08+00:00
- **finished_at**: 2026-05-16T03:55:59+00:00
- **duration_seconds**: 171.190698

### Config

```json
{
  "utility_balance_gamma": 0.5,
  "threshold_omega": 0.8,
  "local_payment_ratio_zeta": 0.5,
  "local_sharing_rate_mu1": 0.4,
  "cross_platform_sharing_rate_mu2": 0.3
}
```

- **batch_size**: 30
