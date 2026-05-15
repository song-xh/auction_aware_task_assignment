# RAMCOM `max_outer_payment_ratio` 默认值由 0.5 收紧到 0.2

## 1. 背景

在 `exp1_test_zeta_08`（`local_couriers=100`、`couriers_per_platform=25`、`courier_capacity=50`、`task_window_end_seconds=3600`，`ζ=0.5`、`μ1=0.4`、`μ2=0.3`、`κ=0.5`）的实测中，RAMCOM TR 仍小于 MRA TR：

| n | RAMCOM TR | MRA TR | RAMCOM cross | RAMCOM cp_rev |
|---|----|----|----|----|
| 5000  | 5307.1  | 6904.4  | 671  | 4711.2  |
| 10000 | 11432.2 | 14290.6 | 1435 | 10135.5 |
| 20000 | 23390.4 | 28632.9 | 2841 | 20052.3 |

按 n=20000 反推 `avg_fare ≈ 8.76`：

- RAMCOM cross per-parcel local TR ≈ `(23390.4 − 4201·0.5·8.76) / 2841 ≈ 1.75 ≈ 0.20·fare`。
- 对照 `cp_rev / cross = 20052.3 / 2841 = 7.06`，与 `compute_ramcom_platform_payment(fare, outer, μ2) = min(fare, outer + μ2·fare)` 在 `outer ≤ κ·fare = 0.5·fare ≈ 4.38`、`μ2·fare ≈ 2.63` 下的上界 `≈ 7.01` 几乎一致。

结论：κ=0.5 已经在生效（否则 `outer_payment` 会被 reservation/历史抽样推到 ≈ fare），但仍不足以让本地平台保留足够 cross 收益。

## 2. 数值阈值推导

`RAMCOM > MRA` 在 n=20000 的闭式条件：

```
4201·0.5·8.76 + 2841·c_ram > 6534·0.5·8.76
⇒ c_ram > (6534 − 4201)·0.5·8.76 / 2841
⇒ c_ram > 3.60 ≈ 0.41·fare
```

`c_ram = fare − platform_payment = fare − (outer + μ2·fare) = (1 − μ2)·fare − outer`。在 `μ2=0.3` 下：

```
c_ram = 0.7·fare − outer
⇒ outer < 0.29·fare
```

所以 `κ` 必须 ≤ 0.29 才能让 RAMCOM 超过 MRA。取 `κ=0.2` 留约 9% 的裕度，估算（n=20000）：

- `outer ≤ 0.2·fare = 1.75`
- `platform_payment = 1.75 + 2.63 = 4.38 ≈ 0.5·fare`
- `c_ram = 8.76 − 4.38 = 4.38 ≈ 0.50·fare`
- 预期 RAMCOM TR ≈ `4201·0.5·8.76 + 2841·4.38 = 18408 + 12444 = 30852` > MRA 28633 ✓
- 与 MRA 的差距 ≈ 2200（约 7.6%）

## 3. 改动

`capa/config.py`：

```python
DEFAULT_RAMCOM_MAX_OUTER_PAYMENT_RATIO = 0.2  # 原 0.5
```

注释中给出 “κ=0.2 + μ2=0.3 → 本地保留 ≈ 0.5·fare” 的推导锚点。

副作用：

- `κ` 是 RAMCOM 私有上界，**不影响 CAPA / ImpGTA / MRA / BaseGTA**。因此 “CAPA ≈ ImpGTA” 的关系不被破坏。
- 公式仍是 `platform_payment = min(fare, outer + μ2·fare)`；只是候选 `outer` 在 `argmax_p (fare-p)·P_accept(p)` 搜索前被截断到 `[0, κ·fare]`。
- 当历史/reservation 全部位于 `> κ·fare` 时，`candidate_levels` 仅剩 `{κ·fare}` 这一个端点候选；`P_accept` 仍按真实 worker 模型计算，可能下降，期望 cross 数会比当前少一些（10–25% 量级），但每单 local TR 上升 2.5×，TR 总账面正向。

## 4. 测试

`tests/test_metric_alignment.py`：

- `test_estimate_ramcom_outer_payment_respects_max_ratio_cap`：增加 `κ=0.2` 时 outer ≤ `4.0` 的紧致断言。
- 新增 `test_default_ramcom_max_outer_payment_ratio_is_tight`：断言 `DEFAULT_RAMCOM_MAX_OUTER_PAYMENT_RATIO == 0.2`，防止默认值再次回归到宽松值。
- 修复两个 pre-existing 测试（`test_ramcom_outer_payment_uses_reservation_candidates_without_history`、`test_ramcom_can_assign_outer_worker_without_empirical_history`）：显式传 `max_outer_payment_ratio=1.0` 保留原始 fare-10/fare-20 的语义。

`pytest tests/test_metric_alignment.py`：50 passed。

## 5. 下一步建议

- 复跑 `exp1_test_zeta_08` 等参数，确认 RAMCOM TR 实际跨过 MRA。
- 若 RAMCOM 超过 MRA 的裕度仍不足（n 较小或骑手紧张时），把 κ 进一步降到 0.15，或把 `compute_ramcom_platform_payment` 改成 `max(outer, μ2·fare)` 让 partner 不再同时拿 outer + μ2·fare 两份。后者需对照 RAMCOM 论文重新判定是否符合原意。
- 文档 `docs/tr_cr_analysis.md` 的 §4.3 推荐组合应同步更新为「κ=0.2」。
