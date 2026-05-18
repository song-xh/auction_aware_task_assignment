# ramcom — exp5_ny_default

Default-config comparison (fixed environment).

## ramcom

### Metrics

| metric | value |
| --- | --- |
| TR | 6218.07 |
| CR | 0.281800 |
| BPT | 0.010330 |
| delivered_parcels | 1409 |
| accepted_assignments | 1447 |
| timed_out_parcels | 34 |

### Local Platform

| field | value |
| --- | --- |
| local_matches | 499 |
| cross_platform_matches | 910 |
| unresolved_parcels | 3557 |
| timed_out_parcels | 34 |

### Cooperating Platforms

| platform | own_task_count | accepted_cross | cooperative_revenue |
| --- | --- | --- | --- |
| P1 | 5000 | 241 | 1061.84 |
| P2 | 5200 | 192 | 844.3000 |
| P3 | 5400 | 252 | 1134.87 |
| P4 | 5600 | 225 | 988.3800 |

### Timing

- **started_at**: 2026-05-16T04:01:05+00:00
- **finished_at**: 2026-05-16T04:17:42+00:00
- **duration_seconds**: 996.529703

### Config

```json
{
  "local_payment_ratio_zeta": 0.5,
  "cross_platform_sharing_rate_mu2": 0.3,
  "max_outer_payment_ratio": 0.2
}
```

- **batch_size**: 20
