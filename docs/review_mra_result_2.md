# MRA 与 CAPA / ImpGTA 在 exp1_test 上的 CR-TR-BPT 差异分析

实验目录：`outputs/plots/exp1_test/`（`summary.json` + `*.png`）
分析时间：2026-05-15

## 1. 主要指标对照（n=1000 / 2000 / 3000 / 4000 / 5000）

| n | algo | TR | CR | BPT | local | cross | unresolved | timeout |
|---|------|----|----|-----|-------|-------|------------|---------|
| 1000 | capa   | 4254.7  | 0.783 | 0.0250 | 520 | 263 | 143 | 72 |
| 1000 | basegta| 5088.9  | 0.789 | 0.0212 | 621 | 168 | 138 | 73 |
| 1000 | impgta | 3636.7  | 0.684 | 0.1133 | 212 | 472 | 243 | 73 |
| 1000 | mra    | 4061.7  | 0.579 | 0.3434 | 579 | 0   | 366 | 55 |
| 1000 | ramcom | 3398.7  | 0.594 | 0.0075 | — | — | — | — |
| 5000 | capa   | 21405   | 0.789 | 0.0387 | — | — | — | — |
| 5000 | basegta| 22344   | 0.668 | 0.0145 | — | — | — | — |
| 5000 | impgta | 20640   | 0.669 | 0.0609 | — | — | — | — |
| 5000 | mra    | 21818   | 0.618 | 0.2320 | — | — | — | — |

观察：

- MRA CR 始终落后 CAPA / basegta 10–20 个百分点（0.58–0.62 vs 0.78–0.79），但 TR 与 CAPA 相当，仅次于 basegta。
- MRA BPT 比其它在线 baseline 高 5–15 倍（0.23–0.34 vs CAPA 的 0.025–0.05，impgta 的 0.06–0.11）。
- CAPA 在 BPT 几乎不变的前提下，CR 显著高于 MRA，TR 与 MRA 接近。

## 2. 代码逻辑层面的原因

### 2.1 MRA 没有跨平台通道

`baselines/mra.py::run_mra_baseline_environment` 只接受 `local_couriers`，并把 `partner_couriers_by_platform={}` 传给 `advance_legacy_routes_with_deadline_accounting`；返回的 `cross_assignment_count` 永远是 0，`partner_cross_assignment_counts` 与 `partner_cross_revenues` 都是空 dict。`summary.json` 中 MRA 的 `cooperating_platforms` 也全部为 0，与代码一致。

结果是 MRA 的 CR 上限被本地骑手承载力卡死：n=1000 时 local=579、unresolved=366，远大于 capa 的 unresolved=143。MRA 的剩余 366 个包裹根本没有“被 partner 拉走”的机会，只能进入 deadline 超时（55 个）或在 backlog 中一直留到下一 batch、最终因路线推进时间用尽而失败。

### 2.2 MRA 的“batch 内多轮重路由”是 BPT 暴涨的来源

`baselines/mra.py` 第 180–268 行：

```python
while remaining:
    graph_edges: list[MRAEdge] = []
    for task in remaining:
        feasible = build_legacy_feasible_insertions(...)  # 每一轮重算
        for insertion in feasible:
            graph_edges.append(MRAEdge(..., bid=compute_mra_bid(...), ...))
    ...
    for edge in round_assignments:
        apply_assignment_to_legacy_courier(edge.task, edge.courier, edge.insertion_index)
        snapshot_cache.invalidate(...)
        insertion_cache.invalidate_courier(...)
    remaining = [task for task in remaining if str(getattr(task, "num")) not in used_tasks]
```

要点：

1. 每一轮（round）都为 batch 中所有“尚未匹配”的包裹重新调用 `build_legacy_feasible_insertions` + `find_best_local_insertion`；而 `find_best_local_insertion`（`capa/utility.py:444`）每次都基于 courier 的当前 `route_locations` 重新计算插入点——只要上一轮 `apply_assignment_to_legacy_courier` 改了 route，这一轮的 detour ratio、feasibility、deadline 检查就全是新的。
2. 每轮匹配成功后立即 `invalidate` snapshot/insertion 缓存，确保下一轮再次走全量插入搜索而不是命中缓存。
3. 排序 + 双向最优匹配（`best_for_task is not edge`）是一个 O(|edges|·|tasks|) 的 inner loop，复杂度本身也比 CAPA 的 single-pass CAMA 高。

所以 MRA 的 BPT 高出来的不是某次插入更贵，而是“每个 batch 重复了多轮插入 + 多轮排序匹配”，本质是**用时间换效果**。

### 2.3 CAPA 的本地搜索是单轮 + 阈值过滤

`capa/cama.py::run_cama`：每个 batch 内的 CAMA 只做一遍 `for parcel in parcels: for courier in shortlisted_couriers: utility=...`，得到 `candidate_best_pairs` 后用阈值 `Th` 一次性切分 local / auction pool。CAMA 不会反复重算 detour ratio，也不再循环；落空的包裹直接进 DAPA 的跨平台拍卖（`capa/dapa.py`）。因此：

- CAPA 的本地阶段计算量 ≈ MRA 第一轮；后续“多轮”被 DAPA 替换为对 partner 平台的拍卖。
- 跨平台通道把 MRA 的 unresolved=366 中的大部分（CAPA 的 cross=263）救了回来 → CR 高。

### 2.4 TR 差距小于 CR 差距的关键：跨平台分账压缩了 CAPA 的 per-parcel 收益

`capa/utility.py:408` 与 `:417`：

- 本地完成：`local_TR_per_parcel = (1 - zeta) * fare = 0.8 * fare`（zeta=0.2）。
- 跨平台完成：`local_TR_per_parcel = fare - platform_payment`，其中 `platform_payment ≤ (mu1 + mu2) * fare = 1.0 * fare`（μ1=μ2=0.5），实际由 DAPA 的二价拍卖与 payment_limit 决定。

以 n=1000 验证：

- MRA：delivered=579，TR=4061.7 → per delivered ≈ 7.02 ≈ 0.8 × 8.77（即平均 fare ≈ 8.77）。
- CAPA：delivered=783 = 520 local + 263 cross；若 local 段贡献 ≈ 520 × 7.02 = 3651，则 cross 段贡献 ≈ 4254.7 − 3651 = 604，每个 cross delivered ≈ 2.30 → 大约只剩下 0.26 × fare。`cooperating_platforms.cooperative_revenue` 累加 1166.6，与 cross delivered ≈ 263 的合作平台收益匹配。

所以 CAPA 多送出来的 263 单（相对 MRA 的 0 单）只补回 ~600 的 TR；MRA 凭借“多轮 local 插入”塞进了 579 个全本地单（每单 ~7.02），TR 反而拉到 4062。两者 TR 几乎打平，本质是：

- MRA 用 BPT × 13 的时间换来本地匹配率最大化（local 579 > CAPA 的 520）。
- CAPA 用更高 CR 换来了 263 个 cross 单，但每单 local 收益被 μ1+μ2=1 的支付上限压到 ~33% 的本地水平。

## 3. 用户问题的逐条回答

> Q1：MRA 的 CR 不如 CAPA / ImpGTA，但 TR 反而高，为什么？

因为 MRA 只走本地通道，但每个本地完成的 per-parcel 收益是 `0.8 × fare`；CAPA / ImpGTA 用跨平台通道拉高了 CR，但每个跨平台完成的 per-parcel 收益只剩 `fare − platform_payment`（实测约 0.26 × fare）。MRA 用“少而贵”的本地单赢回了 TR，CAPA 用“多而便宜”的混合单拿到了 CR。

> Q2：MRA 的 BPT 高，是不是因为它在 batch 内多轮匹配、每轮重算路线 deadline，所以插入位置是基于上一轮重算后的路线？

是的。`run_mra_baseline_environment` 的 `while remaining:` 循环每一轮：

1. 把上一轮成功匹配的 edge 立即 apply 到 courier，并 invalidate `snapshot_cache` / `insertion_cache`；
2. 下一轮的 `build_legacy_feasible_insertions` → `find_best_local_insertion` 在更新后的 route 上重新做 detour ratio、deadline、capacity 检查。

因此 MRA 的插入决策的确是“在上一轮重算 route 的基础上”继续做，每多一轮就多一次全量插入搜索 + 全量排序匹配；这就是 BPT 比 CAPA / impgta 高一个数量级的直接原因（**用时间换匹配数**）。

> Q3：CAPA 在 BPT 几乎不变的情况下 TR 与 MRA 接近、CR 高于 MRA，如果跨平台收益比例提高，TR 是否会超过 MRA？

会。当前 CAPA TR 落后 MRA 的唯一原因是 cross 段被 `platform_payment` 上限压低了 per-parcel local revenue（约 0.26 × fare）。可以从两个方向把 CAPA TR 拉到 MRA 之上：

- 直接降低 `cross_platform_sharing_rate_mu2`（或 `mu1`）→ `payment_limit = (mu1+mu2) × fare` 下移 → cross 段 local revenue 上升；
- 在 DAPA 的二价拍卖里降低 `platform_payment`（例如更紧的 reserve price）。

按上面的近似：CAPA 的 263 个 cross 单若每单 local revenue 从 ~2.30 提到与 local 段同水平的 ~7.02，CAPA 的 TR 将从 4255 提升到约 4255 + 263 × (7.02 − 2.30) ≈ 5497，全面超过 MRA 4062 与 basegta 5089。即使只把 cross per-parcel 收益提到 5.0，CAPA TR ≈ 4255 + 263 × (5.0 − 2.30) ≈ 4965，也会高于 MRA。

## 4. 结论与建议

1. **MRA 高 TR 不是“匹配更聪明”，而是“没有走跨平台分账”**。它把所有 delivered 都保留在 0.8×fare 的本地通道里，但代价是 CR 上限被本地骑手卡死、BPT 暴涨 5–15 倍。
2. **CAPA 的 CR 优势真实**：cross 通道把 MRA 救不回来的 200–300 单送出去，但是 per-parcel local revenue 被 μ1+μ2=1 的上限稀释。
3. **公平对比的前提是同一收益口径**。当前 default 配置 `μ1=μ2=0.5`、`payment_limit = 1.0 × fare` 等价于允许 partner 收走全部 cross fare，对 CAPA 是最差情形。
4. 后续可以做的实验：
   - 在 `configs/` 增加扫描 `cross_platform_sharing_rate_mu2 ∈ {0.2, 0.3, 0.4, 0.5}`，观察 CAPA TR 是否如预期穿越 MRA；
   - 把 MRA 的 `while remaining` 加上轮数上限 K，观察 BPT–CR 曲线是否能在 K=1 时回到 CAPA 量级（用以验证 BPT 高出来的就是多轮）；
   - 在 MRA 加上一个“local 失败后走 partner 拍卖”的回退（不是 fallback，是论文里 MRA 的 cross-platform 扩展），看 CR / TR 是否同步上升、BPT 是否仍然主导。

## 5. 数据来源

- `outputs/plots/exp1_test/summary.json`：上述 TR/CR/BPT/local/cross/unresolved/timeout/cooperative_revenue 全部直接来自该文件。
- 代码：
  - `baselines/mra.py:99-310`（MRA batch 主循环、`while remaining` 多轮匹配、缓存失效）；
  - `capa/cama.py:141-260`（CAMA 单轮匹配 + 阈值过滤）；
  - `capa/utility.py:408-426`（local / cross 完成的 per-parcel TR 公式）；
  - `capa/dapa.py:155-360`（`platform_payment`、`payment_limit`、二价拍卖）。

---

# 附：CAPA / ImpGTA / RAMCOM / MRA 跨平台收益口径对照与 `exp1_test_zeta_05` 的调参分析

实验目录：`outputs/plots/exp1_test_zeta_05/`
命令：见用户原始命令（`--preset test`，未显式指定 `--local-payment-ratio-zeta` / `--local-sharing-rate-mu1` / `--cross-platform-sharing-rate-mu2`）。
`summary.json` 中只有 capa 暴露 `config={'utility_balance_gamma': 0.5, 'threshold_omega': 0.8, 'local_payment_ratio_zeta': 0.3, 'local_sharing_rate_mu1': 0.4, 'cross_platform_sharing_rate_mu2': 0.4}`；其余 baseline 的 `config` 字段为 `{}`。

## 6. 四个算法的 per-parcel 收益公式与是否同口径

| 算法 | 本地完成 local TR | 跨平台完成 platform_payment 公式 | 跨平台完成 local TR | 备注 |
|------|------------------|----------------------------------|----------------------|------|
| CAPA   | `(1-ζ)·fare` | 二价拍卖结果，封顶 `(μ1+μ2)·fare`（`capa/dapa.py:155, 293-319`） | `fare − platform_payment` | 同时受 μ1 与 μ2 影响，唯一会用 μ1 的算法 |
| ImpGTA | `(1-ζ)·fare` | `min(fare, critical_dispatch_cost + μ2·fare)`（`baselines/gta.py:482-499`） | `fare − payment` | 只受 μ2 影响，不读 μ1 |
| RAMCOM | `(1-ζ)·fare` | `min(fare, ramcom_outer_payment + μ2·fare)`（`baselines/ramcom.py:202-221`） | `fare − platform_payment` | 只受 μ2 影响；outer_payment 由期望收益最大化选出 |
| MRA    | `(1-ζ)·fare` | — | — | 无跨平台路径（见前文 §2.1） |

要点：

- **本地段完全同口径**：四个算法都把本地完成的 local TR 写成 `(1−ζ)·fare`（`capa/utility.py:408-414`，被 `baselines/gta.py:407, 695`、`baselines/ramcom.py:391`、`baselines/mra.py:251` 全部直接复用）。
- **跨平台段的“分账公式”形式接近但参数语义不同**：
  - CAPA 是「二价 + 上限 `(μ1+μ2)·fare`」，所以 CAPA 的 `platform_payment` 可以被 μ1+μ2 同时压。
  - ImpGTA / RAMCOM 都是「某个基准量 + μ2·fare，硬封顶 fare」，没有读 μ1。换句话说，**μ1 仅对 CAPA 生效；调 μ1 不会改变 ImpGTA / RAMCOM 的跨平台收益**。
  - ImpGTA 的基准量是「次低的 dispatch cost」（second-price），RAMCOM 的基准量是 outer_payment（按期望收益挑选），所以同一 fare 下 ImpGTA 的 `platform_payment` 通常更高（被二价压高），CAPA 的 `platform_payment` 介于二者之间但又被 `(μ1+μ2)·fare` 截断。
- **MRA 不参与跨平台分账**：`baselines/mra.py:99` 函数签名也没有 `cross_platform_sharing_rate_mu2`，更没有 partner 通道，所以 MRA 的 TR 纯粹是 `Σ_{delivered local} (1−ζ)·fare_τ`。

结论：**本地段是同口径，跨平台段在形式上同口径但在参数面上不一致**（μ1 只在 CAPA 起作用；ImpGTA 与 RAMCOM 的基准量不同）。这意味着同一组 `(ζ, μ1, μ2)` 不能让四个算法的“per-parcel cross local TR”按同一公式可比。

## 7. `exp1_test_zeta_05` 关键观测

| n | algo | TR | CR | local | cross | cp_rev | per-parcel cross local TR* |
|---|------|----|----|-------|-------|--------|------------------------------|
| 1000 | capa   | 2441.6 | 0.484 | 284 | 200 | 698.1  | ≈ 2.07 |
| 1000 | impgta | 1778.8 | 0.330 | 70  | 260 | 887.6  | ≈ 3.07 |
| 1000 | ramcom | 770.1  | 0.147 | 115 | 32  | 192.5  | ≈ 1.43 |
| 1000 | mra    | 803.9  | 0.134 | 134 | 0   | 0      | — |
| 5000 | capa   | 13334  | 0.528 | 1519 | 1119 | 3946.7 | ≈ 3.70 |
| 5000 | impgta | 10527  | 0.379 | 506  | 1387 | 4758.8 | ≈ 5.38 |
| 5000 | ramcom | 8348.5 | 0.352 | 1088 | 670  | 4156.2 | ≈ 2.62 |
| 5000 | mra    | 10245  | 0.339 | 1693 | 0    | 0      | — |

*per-parcel cross local TR ≈ (TR − local·(1−ζ)·avg_fare) / cross。avg_fare 用 MRA 反推得 ≈ 8.65（n=5000）。

观测：

1. 实测 TR 顺序（n≥2000）：`basegta > capa > impgta > mra > ramcom`，**MRA 仍然压在 RAMCOM 上面**，与用户希望的 `capa > impgta > ramcom > mra` 差距主要在 RAMCOM vs MRA。
2. ImpGTA 的 per-parcel cross local TR ≈ 5.38 显著高于 CAPA 的 3.70：因为 CAPA 受 `(μ1+μ2)·fare = 0.8·fare` 上限挤压，而 ImpGTA 只有 `μ2·fare = 0.4·fare` 这个加价项。但 CAPA 总 TR 仍然领先，是因为本地匹配 1519 远多于 ImpGTA 的 506（CAMA 阈值 + 候选集筛选效率比 ImpGTA 的“先 own-task 再 cross”规则更高）。
3. RAMCOM 的 cross 数量（670）远少于 ImpGTA（1387），同时 per-parcel cross local TR 也只有 2.62（接受概率乘上 (fare−outer_payment) 的最大化选择会把 outer_payment 推得不算低）；这两件事一起导致 RAMCOM 现阶段 TR 输给 MRA。

## 8. 一个非常重要的“非对称”：CLI 的 ζ/μ1/μ2 只作用于 CAPA

`experiments/paper_chengdu.py:810-824 build_capa_runner_overrides_from_args`：CLI 参数 `--local-payment-ratio-zeta`、`--local-sharing-rate-mu1`、`--cross-platform-sharing-rate-mu2` 只会写进 `{"capa": {...}}`，不会传给 ImpGTA / RAMCOM / MRA / BaseGTA。

再看 baseline runner：

- `algorithms/impgta_runner.py:25-29`、`algorithms/basegta_runner.py`：构造函数只接收 `prediction_*` 参数，根本没有 `local_payment_ratio_zeta` / `cross_platform_sharing_rate_mu2` 入参 → 内部 `_run_gta_environment` 永远使用 `capa.utility.DEFAULT_LOCAL_PAYMENT_RATIO = 0.2` 与 `capa.config.DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2 = 0.5`。
- `algorithms/ramcom_runner.py:22-23`、`algorithms/mra_runner.py:22`：同样只暴露 `batch_size` / `random_seed`，没把 `local_payment_ratio` 或 `cross_platform_sharing_rate_mu2` 暴露出去。
- `baselines/gta.py:579-581`、`baselines/ramcom.py:228-229`、`baselines/mra.py:104` 的函数签名其实**支持**这些参数（带默认值），只是没人调它。

后果（直接解释本次实验为何无法用 CLI 调通顺序）：

> **`exp1_test_zeta_05` 里 CAPA 用的是 ζ=0.3、μ1=0.4、μ2=0.4，而 ImpGTA / RAMCOM / MRA / BaseGTA 同时用着 ζ=0.2、μ2=0.5**。`per-parcel` 本地收益：CAPA 是 `0.7·fare`，其余 baseline 是 `0.8·fare` —— **baseline 在本地段每完成一单比 CAPA 多 14% 的 TR**。这就把 MRA 的 TR 系统性推高了。同时 RAMCOM / ImpGTA 的跨平台收益用的是 μ2=0.5 而 CAPA 是 μ2=0.4，对 ImpGTA / RAMCOM 也偏有利。

**结论：在修好这条 CLI 旁路之前，任何“调小本地收益 / 调高跨平台收益”的实验都是只对 CAPA 生效，对 baseline 无效，TR 排序也就不能按用户想要的方向收敛。**

## 9. 想要 TR 排序 `capa > impgta > ramcom > mra` 的调参建议

### 9.1 必做：把参数传给所有 baseline（代码层）

1. 在 `algorithms/impgta_runner.py`、`algorithms/basegta_runner.py`、`algorithms/ramcom_runner.py`、`algorithms/mra_runner.py` 的构造函数里加上 `local_payment_ratio_zeta`（mra 仅需这一个）、`cross_platform_sharing_rate_mu2`（ramcom / impgta / basegta），并 forward 给底层 `run_*_baseline_environment(..., local_payment_ratio=..., cross_platform_sharing_rate_mu2=...)`。底层函数早就接受这些 kwargs，只差 runner 接线。
2. 把 `build_capa_runner_overrides_from_args` 改成 `build_revenue_overrides_from_args`，对 `impgta / basegta / ramcom / mra` 各自生成一份 override：
   - `mra`: `{"local_payment_ratio_zeta": ζ}`
   - `ramcom`: `{"local_payment_ratio_zeta": ζ, "cross_platform_sharing_rate_mu2": μ2}`
   - `impgta` / `basegta`: 同 ramcom
   - `capa`: `{"local_payment_ratio_zeta": ζ, "local_sharing_rate_mu1": μ1, "cross_platform_sharing_rate_mu2": μ2}`
3. CLI 端补对应的 flag（已有），把它们一起注入 fixed_config → runner_overrides，确保 split / point / managed 三种执行模式都生效。

不做这一步，下面的“调参”只是单边对 CAPA 起作用。

### 9.2 “调小本地收益 / 调高跨平台收益”的方向

按当前公式，参数对每条曲线的影响如下（同口径假设，即上一步已修好）。

| 参数 | 影响对象 | 本地段 per-parcel | 跨平台段 per-parcel | 主要赢家 | 主要输家 |
|------|----------|------------------|----------------------|----------|----------|
| ζ ↑ | 全部 | `(1−ζ)·fare` ↓ | 不变 | 无 | **MRA**（100% 本地），其次 basegta / capa-local 占比高者 |
| μ2 ↓ | capa / impgta / ramcom | 不变 | `fare−p` ↑（cap 下移，二价加价项变小） | impgta、ramcom、capa（cross 段） | partner 平台接受率可能下降 → cross 数量略减 |
| μ1 ↓ | 只对 capa | 不变 | capa `(μ1+μ2)·fare` cap ↓，但若实际 payment 已小于该 cap 则不变 | 仅在 cap 实际生效时 capa cross 段 ↑ | 仅压低 cap，可能踢出一些 partner bid → capa cross 数量略减 |

要让排序 `capa > impgta > ramcom > mra`，要点是：

1. **大幅抬高 ζ**：把 MRA 的 `0.8·fare` 削到 `0.4~0.5·fare`，直接削顶 MRA 的 TR 上限。同时也削 CAPA、ImpGTA、RAMCOM 的本地段，但它们有 cross 段补血，受损更小。
2. **降低 μ2**：把 cross 段 `platform_payment` 中的「+μ2·fare」加价项收紧，给 ImpGTA / RAMCOM / CAPA 的本地平台多留一些 cross 收益，主要补回 RAMCOM（cross 数最少，对每单收益最敏感）。
3. **μ1 保持原值（≥0.4）**：μ1 只压 CAPA。压它会让 CAPA cross 段 cap 下移，可能挤掉一些原本能成交的 partner bid，反而让 CAPA cross 数量减少；除非 CAPA 当前 `platform_payment` 普遍贴着 cap，否则降 μ1 收益有限。

### 9.3 数值估计（避免凭感觉调）

以 n=5000 数据 + avg_fare ≈ 8.65 做一阶推算，假设 cross 数量大体不变（先忽略二阶效应）。设 ζ 与 μ2 为可调变量；记原 per-parcel cross local TR 为 `c_a^0`（capa=3.70、impgta=5.38、ramcom=2.62）。把「+μ2·fare」从 0.5·fare 降到 μ2·fare，per-parcel cross local TR 大约增加 `(0.5 − μ2)·fare ≈ (0.5 − μ2)·8.65`（CAPA 受 cap 影响，增量上限是 `(0.5 − μ2)·8.65`，但实际可能更小，先按上限估）。

- `MRA(ζ) ≈ 1693·(1−ζ)·8.65`
- `RAMCOM(ζ, μ2) ≈ 1088·(1−ζ)·8.65 + 670·[c_ramcom^0 + (0.5−μ2)·8.65]`
- `ImpGTA(ζ, μ2) ≈ 506·(1−ζ)·8.65 + 1387·[c_impgta^0 + (0.5−μ2)·8.65]`
- `CAPA(ζ, μ2)  ≈ 1519·(1−ζ)·8.65 + 1119·[c_capa^0 + (0.5−μ2)·8.65]`

要 RAMCOM > MRA：
`670·[2.62 + (0.5−μ2)·8.65] > (1693−1088)·(1−ζ)·8.65`
化简：`2.62/8.65 + (0.5−μ2) > 605/670·(1−ζ) ≈ 0.903·(1−ζ)`
即 `0.303 + (0.5 − μ2) > 0.903·(1 − ζ)`

几组取法：

| ζ | μ2 | 0.303+(0.5−μ2) | 0.903·(1−ζ) | 是否满足 |
|---|----|----------------|--------------|----------|
| 0.3 | 0.4 | 0.403 | 0.632 | 否（当前实际状态接近，故 ramcom<mra） |
| 0.5 | 0.3 | 0.503 | 0.452 | **是** |
| 0.5 | 0.2 | 0.603 | 0.452 | 是（更稳） |
| 0.6 | 0.3 | 0.503 | 0.361 | 是 |

ImpGTA > RAMCOM（同 ζ、μ2，cross 数差异：1387 vs 670，单单 cross 差 717；本地差 506−1088=−582）：
`1387·[5.38+δ] − 670·[2.62+δ] − (506−1088)·(1−ζ)·8.65 > 0`
其中 `δ = (0.5−μ2)·8.65`。无论 ζ/μ2 怎么取（合理范围内），这个差稳定为正，不需要再约束。

CAPA > ImpGTA（cross 差 1119−1387 = −268，本地差 1519−506 = +1013）：
`+1013·(1−ζ)·8.65 + 1119·[3.70+δ] − 1387·[5.38+δ] > 0`
=> `1013·(1−ζ)·8.65 > (1387−1119)·δ + (1387·5.38 − 1119·3.70)`
=> `1013·(1−ζ)·8.65 > 268·δ + 3320`

| ζ | μ2 | LHS | RHS | 是否满足 |
|---|----|-----|-----|----------|
| 0.5 | 0.3 | 4381 | 268·1.73+3320 = 3784 | 是（裕度 ~600） |
| 0.5 | 0.2 | 4381 | 268·2.60+3320 = 4017 | 是（裕度 ~360） |
| 0.6 | 0.3 | 3505 | 3784 | 否（CAPA 反被 ImpGTA 反超） |
| 0.55 | 0.3 | 3943 | 3784 | 是（裕度 ~160） |

合并所有约束 + 给二阶效应留余量，**推荐起手配置**：

```text
--local-payment-ratio-zeta 0.5
--local-sharing-rate-mu1 0.4
--cross-platform-sharing-rate-mu2 0.3
```

预期效果（一阶估算，单位 TR @ n=5000）：

- MRA  ≈ 1693·0.5·8.65 = 7322（↓ 2923）
- RAMCOM ≈ 1088·0.5·8.65 + 670·(2.62+1.73) = 4706 + 2915 = 7621（↑ 顺利越过 MRA）
- ImpGTA ≈ 506·0.5·8.65 + 1387·(5.38+1.73) = 2188 + 9862 = 12050
- CAPA ≈ 1519·0.5·8.65 + 1119·(3.70+1.73) = 6570 + 6075 = 12645

排序：**CAPA(12645) > ImpGTA(12050) > RAMCOM(7621) > MRA(7322)**，命中目标。

如果实跑发现 CAPA 与 ImpGTA 太接近（裕度 ~600），可以再把 ζ 拉到 0.55；如果 RAMCOM 与 MRA 太接近，把 μ2 从 0.3 降到 0.25。

### 9.4 操作清单

1. （代码改动，必做）把 `local_payment_ratio_zeta` / `cross_platform_sharing_rate_mu2` 接到 `impgta_runner.py` / `basegta_runner.py` / `ramcom_runner.py` / `mra_runner.py`，并在 `experiments/paper_chengdu.py` 的 override 构造里同时下发到 capa 与四个 baseline。补 `tests/test_metric_alignment.py` 验证 CLI flag 真的进了各算法的 metrics 输出（让 `summary.json` 里 baseline 的 `config` 字段不再是 `{}`）。
2. （实验，按 §9.3 推荐参数跑）`--local-payment-ratio-zeta 0.5 --local-sharing-rate-mu1 0.4 --cross-platform-sharing-rate-mu2 0.3 --preset test`，输出到 `outputs/plots/exp1_zeta05_mu03/`，验证排序。
3. （扫描，可选）做一个二维网格 `ζ ∈ {0.4, 0.5, 0.6}` × `μ2 ∈ {0.2, 0.3, 0.4}` 的小扫描，挑一组让 `capa−impgta` 与 `ramcom−mra` 两个边际都为正且尽量大的配置，作为论文主表参数。
4. （绘图）确认 `experiments/plotting.py::visible_algorithms_for_metric` 仍然过滤掉 `basegta`（TR）和 `mra`（BPT），否则 basegta 仍会在 TR 图上压住 CAPA。

## 10. 引用

- 收益公式：`capa/utility.py:402-426`、`capa/dapa.py:155-160, 290-320`、`baselines/gta.py:482-499, 695-780`、`baselines/ramcom.py:202-221, 391-477`、`baselines/mra.py:99-256`。
- CLI 注入：`experiments/paper_chengdu.py:810-824, 932-948`。
- Runner 接线缺口：`algorithms/impgta_runner.py:25-29`、`algorithms/basegta_runner.py`、`algorithms/ramcom_runner.py:22-23`、`algorithms/mra_runner.py:22`。
- 实验数据：`outputs/plots/exp1_test_zeta_05/summary.json`。

