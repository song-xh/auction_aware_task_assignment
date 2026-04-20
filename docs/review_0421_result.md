# review_0421 审查结果：BaseGTA / ImpGTA 相对于 CAPA 的 TR-CR 倒挂排查

日期：2026-04-21
关联实验：`result/exp1_formal/summary.json`
审查范围：`baselines/gta.py`、`capa/cama.py`、`capa/dapa.py`、`capa/utility.py`、`env/chengdu.py`

## 0. 结论速览

| 指标口径 | BaseGTA 对 CAPA 的偏差 | ImpGTA 对 CAPA 的偏差 | 判定 |
| --- | --- | --- | --- |
| 本地 (inner) 收益公式 `fare·(1−ζ)` | 一致 | 一致 | 无 bug |
| 跨平台 (cross) 收益 `fare − critical_payment` | critical_payment 的**语义单位不同** | 同上，且占比更高 | ⚠ 实现口径不统一 |
| `su_ij` 在 CPUL 下的适配 | 使用 `ready_location → l_node` 的**直线距离**而非插入增量 `Δdist` | 同上 | ⚠ 实现口径不统一 |
| completion 定义 | 与 CAPA 一致（均以 `re_schedule` 清空为准） | 一致 | 无 bug |
| revenue 记账时机 | accept 时记，drain 后 `accepted == delivered` | 同上 | 无 bug |
| BPT 聚合单位 | **每任务累计** | **每任务累计** | ⚠ 与 CAPA 的**每 batch 累计**不同 |
| immediate-permanent vs deferred-retry | GTA 逐任务、无 batch 内 retry；CAPA 一次 batch 内也不 retry（单轮 process） | 同上 | 行为一致，口径一致 |

**关键判定**：

1. BaseGTA 的 `TR > TR_CAPA` 主要是**真实 trade-off**：BaseGTA 在本地可行时永不进入 AIM，所以每条被接受的任务都按 `0.8·fare` 计入，而 CAPA 会因 Eq.7 门限把部分低效用 pair 丢入 DAPA，而 DAPA 的 local platform revenue 受 `(μ₁+μ₂)·fare` 压顶，显著低于 `0.8·fare`。BaseGTA 少做 14 单（N=1000: 986 vs 1000），但其收益分布整体更高。
2. ImpGTA 的 `TR` 进一步偏高，其主导原因是 **cross 收益口径错误**：GTA 的 AIM critical_payment 是“次低 courier 公里运价”（基于 `dispatch_cost`），而 CAPA 的 critical_payment 是“次低平台 bid”（含 `μ₁·fare + μ₂·fare` 等平台留存项）。移植到 CPUL 后，ImpGTA 在条件满足时绕过本地、进入 AIM，其 local platform revenue 被高估至约 `fare − small_courier_wage ≈ 0.95·fare`，远高于 CAPA 在同一任务上的 `fare − platform_payment ≈ 0.1·fare` 的量级。
3. `su_ij` 当前只看 `ready_location→l_node` 的**单段直线**，而不是 CPUL 下真实的 schedule 插入增量 `Δdist(c, τ)`，这会进一步**低估** courier 的真实成本、**抬高** critical_payment 的“便宜度”幻觉，从另一侧面放大 GTA 跨平台收益。
4. BPT 的聚合单位目前按 per-parcel 分母 vs CAPA per-batch 分母，对比表格上的 BPT 数字不可直接比。

下面给出具体的定位和修复步骤（指到函数和公式）。

---

## 1. 证据与量化复核

### 1.1 单位净收益对照（来自 `result/exp1_formal/summary.json`）

| N | 算法 | TR | delivered | TR/delivered |
| --- | --- | --- | --- | --- |
| 1000 | CAPA | 6331.13 | 1000 | 6.33 |
| 1000 | BaseGTA | 7018.29 | 986 | **7.12** |
| 1000 | ImpGTA | 7731.74 | 979 | **7.90** |
| 5000 | CAPA | 28866.82 | 4989 | 5.78 |
| 5000 | BaseGTA | 35160.74 | 4955 | **7.10** |
| 5000 | ImpGTA | 38995.67 | 4910 | **7.94** |

若 local-only 下 `revenue = 0.8·fare`，则 BaseGTA 的 `TR/delivered ≈ 7.1` 直接对应 `fare_avg ≈ 8.88`。ImpGTA 的 `TR/delivered ≈ 7.9 > 0.8·fare_avg`，只能来自 cross 通道的“单条高收益”，这与 CAPA 的 cross 通道单条低收益形成反向压差。

### 1.2 公式对齐

- **Local（两种算法一致）**
  - `capa/cama.py::build_local_assignment` → `local_platform_revenue = fare − ζ·fare`
  - `baselines/gta.py::compute_local_platform_revenue_for_local_completion`（复用同函数，见 `capa/utility.py:408`）→ `fare − ζ·fare`
  - ✅ 无偏差。

- **Cross（两种算法公式一致但“critical_payment”不同）**
  - CAPA：`compute_local_platform_revenue_for_cross_completion(fare, platform_payment)` with  
    `platform_payment = second_lowest(platform_bid_values)`、`platform_bid = courier_bid + q·μ₂·fare`、`courier_bid = base_price + (α·detour + β·score)·γ·μ₁·fare`。此 payment 含平台 retention。
  - BaseGTA/ImpGTA：`settle_aim_auction`（`baselines/gta.py:276-291`）中  
    `critical_payment = ordered_bids[1].dispatch_cost`，其中 `dispatch_cost = (distance_m/1000)·unit_price_per_km`。此 payment **只含 courier 的公里运费**，完全没有 cooperating platform 的分成。
  - 同样叫 `critical_payment`，单位语义相差 `(μ₁+μ₂)·fare` 量级 —— 这就是 cross 通道 TR 被高估的根。

### 1.3 其它口径复核

- `compute_delivered_legacy_task_count`（`env/chengdu.py:598`）与 `drain_legacy_routes`（`env/chengdu.py:701`）保证 `accepted == delivered`，两边对齐。✅
- `_run_gta_environment`（`baselines/gta.py:317`）在接受时 `total_profit += revenue`，`completed_flag`/`accepted_task_ids.add` 同步，不存在重复计入。✅
- BaseGTA 逻辑 `if algorithm == "basegta" or should_dispatch_inner_task_impgta(...)`（`baselines/gta.py:394`）决定 local 可行即取 local，绝不进入 AIM；ImpGTA 可能跳过 local 进入 AIM。这是观察到的 TR 行为差异的控制点。

---

## 2. 定位到的具体问题与必改点

### 问题 P1：跨平台 critical_payment 的语义不统一（主因，影响 cross revenue）

- 位置：`baselines/gta.py::settle_aim_auction`（L276–L291）和 `baselines/gta.py::_run_gta_environment` 中对跨平台 outcome 调用 `compute_local_platform_revenue_for_cross_completion(fare, outcome.payment)`（L465–L468）。
- 现象：`outcome.payment` 是 courier 间 AIM 的次低 `dispatch_cost`，没有 cooperating-platform retention；CAPA 的同名入参是 DAPA 的平台 bid，包含 `(μ₁+μ₂)·fare` 的平台侧分成。两者带入同一函数 `fare − payment` 后单位语义不同。
- 判定：**主评测口径错误**，需要统一。

### 问题 P2：`su_ij` 在 CPUL 下仅用直线距离，不做插入增量（影响 critical_payment 的绝对值）

- 位置：`baselines/gta.py::compute_dispatch_cost`（L66–L74）、`compute_dispatch_cost_from_location`（L77–L85）和 `legacy_courier_ready_state`（L56–L64）。
- 现状：  
  `dispatch_cost = (distance(courier_or_ready_location, task.l_node)/1000) · unit_price`  
  对已有 schedule 的 courier，直接从 `ready_location`（最后一段 `l_node`）直线拉到 `task.l_node`，**不计入**把该任务插入现有 schedule 后的真实增量距离（review_0421 Checkpoint 1.4 要求的 `min_{c∈C_i^{feas}} u_c · Δdist(c, τ)`）。
- 影响：对长队列 courier，实际插入成本被大幅低估；AIM 次低 bid 相应偏低；local platform 误以为“别人家 courier 很便宜”，`fare − payment` 偏大。
- 判定：**实现口径错误**，与 CAPA 的插入式 detour（`capa/utility.py::find_best_local_insertion`）不对齐。

### 问题 P3：BPT 聚合单位不一致（影响 BPT 对比，不影响 TR/CR）

- 位置：`baselines/gta.py::_run_gta_environment` 中 `processing_time_seconds` 是按每个 task 累计 `perf_counter` 差值（L379–L483）；CAPA 是按 batch 累计 `process_batch` 耗时（`capa/runner.py:44`）。
- 现状：GTA 的 BPT 实际近似总决策时间 ≈ N_task × avg_per_task；CAPA 是 total_decision_time ≈ N_batch × avg_per_batch。两者量纲一致（秒），但**单次决策覆盖的任务数**不同。
- 判定：**表面一致但对比口径失真**，需要在 summary 中明确“是否除以 batch 数”，或让 GTA 也按 arrival-epoch 聚合。

### 非问题（已排查）

- Inner revenue 公式：BaseGTA 与 CAPA 均通过 `compute_local_platform_revenue_for_local_completion`（`capa/utility.py:408`）得到 `fare − ζ·fare`，没有 review_0421 1.1 描述的 `U_t = v_t` 问题。
- cross revenue 公式：没有 `fare − bid` 或 `fare − su` 的误用（review_0421 1.2），函数签名就是 `fare − payment`。问题在 **payment 的构造方式**（见 P1），不在公式本身。
- AIM 支付是否为次低：`settle_aim_auction` 正确地 `ordered_bids[1].dispatch_cost`，且 `payment = min(fare, critical_payment)`；`payment < winner.dispatch_cost → return None`，三条规则（winner=最低、payment=次低、payment<fare 容忍）齐备（review_0421 1.3 通过）。
- completion 定义：GTA 与 CAPA 都以 `re_schedule` 清空作为 CPUL pickup 完成（`env/chengdu.py::compute_delivered_legacy_task_count`），不再沿用原 GTA 的“source→destination 全任务完成”（review_0421 1.5 通过）。
- 重复计入：`accepted_task_ids` 是 `set`，`apply_assignment_to_legacy_courier` 单次调用，不存在双记。
- Immediate vs deferred：两边都没有 batch-内 retry（CAPA 未把 `unassigned_parcels` 回填下一 batch，GTA 无 retry），review_0421 Task 2 的悬念此实验中不触发。

---

## 3. 修改步骤（按优先级）

> 原则：**保留各算法的内部机制，不人为给 GTA 加 DAPA**；只统一 **评测口径**（local_platform_revenue 的计算）和 **CPUL 下 su_ij 的语义**。

### Fix F1：为 GTA 的 AIM outcome 增加 cooperating-platform retention，统一 cross revenue 语义

**目标**：让 `_run_gta_environment` 中 `total_profit` 的 cross 部分与 CAPA 同单位。

**具体改动**：

1. 在 `baselines/gta.py::settle_aim_auction`（L276）返回的 `AIMOutcome` 上，新增“向 cooperating 平台支付的 platform-level payment”概念。最小改动：引入一个参数 `cross_platform_sharing_rate_mu2`（默认沿用 `DEFAULT_CAPA_MU2 = 0.4`），令
   ```python
   platform_payment = min(
       fare,
       critical_payment + cross_platform_sharing_rate_mu2 * fare,
   )
   ```
   作为返回的 `AIMOutcome.payment`。  
   解读：把 GTA 的 courier-wage 次低价加上 CAPA 公式里 `μ₂·fare` 的平台分成，复原“local 平台向 cooperating 平台付的钱”。
2. 在 `_run_gta_environment`（L427–L468）调用 `compute_local_platform_revenue_for_cross_completion(fare, outcome.payment)` 时，`outcome.payment` 已是含平台分成的 payment，无需再改公式本身。
3. 在 `run_basegta_baseline_environment` / `run_impgta_baseline_environment` 的签名新增 `cross_platform_sharing_rate_mu2` 参数（默认 `DEFAULT_CAPA_MU2`），透传到 `settle_aim_auction`。
4. 相关常量集中到 `capa/config.py`，确保 CAPA / GTA 共享同一份 `μ₁, μ₂, ζ`。

> 注：这一改动**只改评测口径**，不改变 GTA 的竞标/中标逻辑本身；winner 仍按原 GTA 选法，只是局部平台记账时承认“你是请别家平台帮跑”。

### Fix F2：用插入增量 `Δdist` 重写 CPUL 下的 dispatch_cost

**目标**：`su_ij^CPUL = min_{c∈C_i^{feas}} u_c · Δdist(c, τ)`。

**具体改动**：

1. 在 `baselines/gta.py::compute_dispatch_cost_from_location`（L77）之外新增
   ```python
   def compute_incremental_dispatch_cost(task, courier, travel_model, unit_price_per_km):
       base, detour = _best_insertion_increment(courier, task.l_node, travel_model)
       return (detour / 1000.0) * unit_price_per_km
   ```
   其中 `_best_insertion_increment` 复用 `capa/utility.py::find_best_local_insertion` 的思路，返回 `Δdist = min_k (d(r_k, p) + d(p, r_{k+1}) − d(r_k, r_{k+1}))`；当 courier 为 idle 时退化为 `d(location, p)`。
2. 让 `select_idle_courier_for_task`（L163）与 `select_available_courier_for_task`（L198）在生成 `GTABid.dispatch_cost` 时调用 `compute_incremental_dispatch_cost`，取代现有的 `compute_dispatch_cost` / `compute_dispatch_cost_from_location`。
3. `is_idle_courier_feasible` / `is_available_courier_feasible` 的 deadline 校验同步使用“插入点到达时刻”。如果实现成本过高，可分两阶段：阶段 1 先把 bid 换成增量距离；阶段 2 再把 deadline 校验换成插入点到达时刻。

### Fix F3：统一 BPT 聚合单位

**目标**：summary.json 里的 BPT 能直接对比。

**具体改动**：

1. 在 `baselines/gta.py::_run_gta_environment` 里增加 `batch_seconds` 或 `per_arrival_epoch=True` 两种模式的计时路径。
2. 推荐做法：每次 `while task_index < total_task_count:` 的 epoch 看作一个“批”，把 `perf_counter() − started` 求和后，再除以 epoch 数；或者直接与 `capa/runner.py::process_batch` 一致，在 GTA 每个 arrival 时刻聚合一次 `perf_counter` 差值，作为 `batch_processing_time`。
3. 在 `summary.json` 附带 `"BPT_unit": "per_arrival_epoch"` 字段，避免后续再次混淆。

### Fix F4：在 Assignment 记录里同时保留 gross/net 两种 revenue

**目标**：让后续审查可以直接区分“是否已扣 platform retention”。

**具体改动**：

1. 在 `capa/models.py::Assignment` 上添加 `cooperating_platform_payment: float`（已有 `platform_payment`，可直接借用）和 `gross_platform_profit: float`（= `fare − courier_payment`）字段。
2. GTA 的 `_run_gta_environment` 也产出 `Assignment`（目前只累 `total_profit`），用 `capa/metrics.py::compute_total_revenue` 统一重算；把 `baselines/gta.py::total_profit` 的手写累加删除，改为对 `Assignment` 列表做 `sum(a.local_platform_revenue)`。
3. 输出 summary 时，新增 `avg_rev_per_completed = TR / delivered`、`avg_cross_payment = mean(platform_payment for cross)`，review_0421 Goal C 中 `avg_rev_per_completed` 的拆分即可直接读取。

---

## 4. 验证步骤

在实施 F1–F2 后，预期：

1. `TR_basegta(N=1000)` 基本不变（BaseGTA 几乎不进 AIM，cross 改动影响很小），`TR_impgta(N=1000)` 明显下降，与 `TR_CAPA` 的差距显著缩小。
2. `TR_basegta / delivered` 仍 ≈ `0.8 · fare_avg`；`TR_impgta / delivered` 不再超过 `0.8 · fare_avg` 太多。
3. 若 F1 实施后仍然观察到 `TR_basegta > TR_CAPA`，可判定为 review_0421 Goal C 所述的**真实 trade-off**：BaseGTA 在 local 可行时永不进入 cross，使每条 accepted 都拿 `0.8·fare` 的满额；CAPA 的 Eq.7 门限会把部分 low-utility pair 丢入 DAPA 从而接受较低的 `fare − platform_payment`。这是机制本身带来的差异，不再是 bug。

建议补一组单元测试：

- `tests/test_gta_cross_payment_parity.py`：构造同一个 parcel、同一个 CAPA/GTA 环境，断言 `_run_gta_environment` 产出的 `Assignment.local_platform_revenue` 与 `run_dapa` 产出的同名字段量级一致（±10%）。
- `tests/test_gta_incremental_dispatch_cost.py`：给一个带 2-段 schedule 的 courier 和一个新任务，断言 F2 的 `Δdist` 小于旧 `ready_location→l_node` 直线距离的情形被检出（反例），以及 idle courier 退化到直线距离的情形保持一致。

---

## 5. 备注：本次审查**未动代码**

本轮仅完成问题定位。修改点集中在 `baselines/gta.py`、`capa/utility.py`、`capa/config.py`、`capa/metrics.py`、`capa/models.py`，建议按 F1 → F2 → F3 → F4 顺序提交独立 commit，并在每个 commit 附带 `result/exp1_formal` 的重跑 summary，便于回归核对。
