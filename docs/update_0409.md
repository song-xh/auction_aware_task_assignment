# 2026-04-09 审查与修正计划

> 范围：结合当前实验结果、`CAPA`/`RL-CAPA`/baseline 代码、论文 `docs/Auction-Aware Crowdsourced Parcel Assignment for Cooperative Urban Logistics.md` 与对比算法论文 `docs/MinerU_markdown_Competition_and_Cooperation_Global_Task_Assignment_in_Spatial_Crowdsourcing_2039180845507551232.md`，分析 3 个问题：
> 1. 为什么当前结果里 `CAPA` 的 `CR` 高于 `GTA`，但 `TR` 反而明显更低。
> 2. 为什么 `MRA` 的 `BPT` 显著高于其他算法。
> 3. 当前 `ImpGTA` 是否真正实现了论文中的预测逻辑。

## 执行计划

1. 核对 `result/` 中 `Exp-1` 和默认对比实验的 `TR/CR/BPT` 数值，确认现象不是绘图或汇总错误。
2. 审查 `CAPA` 的收益计算、批处理重试流程、合作平台环境初始化，以及 `GTA/ImpGTA` 的收益与派单逻辑。
3. 审查 `MRA` 的 `BPT` 计时链路和热点循环，判断是口径问题还是算法复杂度问题。
4. 审查 `ImpGTA` 的“预测窗口”实现，核对其是否符合参考论文中“历史数据预测 + 未来分布阈值决策”的定义。
5. 输出每个问题的结论、代码证据、成因、修正思路、具体修复步骤与审查点。

---

## 问题一：`CAPA` 的 `CR` 高于 `GTA`，但 `TR` 更低

### 结论

当前结果里“`CAPA` 的 `CR` 更高但 `TR` 更低”并不自动说明汇总错误，但**当前实现里同时存在 3 类因素**：

1. **指标本身不要求单调**：`CR` 高不代表 `TR` 一定高，因为 `TR` 取决于每个已完成任务的净收益，而不是只取决于完成数。
2. **`CAPA` 与 `GTA` 的每单收益模型并不相同**：即使完成数量接近，`GTA/ImpGTA` 的单单收益也可能更高。
3. **当前项目中的 `CAPA` 和 `GTA` 都存在与论文不完全一致的实现偏差**，这些偏差会放大当前差异，尤其是：
   - `CAPA` 侧对已有 route 的时序约束检查过弱，容易把 parcel 判成“可服务”；
   - `GTA/ImpGTA` 侧允许“完成当前 route 后可用”的 courier 参与，而不是论文 [17] 中的“idle worker only”。

换言之，当前观察到的结果不是单一原因造成的，而是“收益定义差异 + 实现偏差 + 实验环境设定”共同作用的结果。

### 结果证据

`result/exp1_formal/summary.json` 显示，`CAPA` 的 `CR` 基本在 `0.9978 ~ 1.0`，但 `TR` 始终低于 `BaseGTA/ImpGTA`：

- `|Γ|=1000`：
  - `CAPA`: `CR=1.0`, `TR=6331.13`
  - `BaseGTA`: `CR=0.986`, `TR=7018.29`
  - `ImpGTA`: `CR=0.979`, `TR=7731.74`
- `|Γ|=5000`：
  - `CAPA`: `CR=0.9978`, `TR=28866.82`
  - `BaseGTA`: `CR=0.991`, `TR=35160.74`
  - `ImpGTA`: `CR=0.982`, `TR=38995.67`

把 `TR / accepted_assignments` 作为“平均每单本地平台收益”后，可以看到差距更清楚：

- `CAPA`: 约 `5.79 ~ 6.33`
- `BaseGTA`: 约 `7.09 ~ 7.12`
- `ImpGTA`: 约 `7.89 ~ 7.94`

也就是说，当前现象的直接原因不是“`CAPA` 完成得少”，而是“`CAPA` 完成的很多任务本地净收益更低”。

### 原因 A：`TR` 和 `CR` 在定义上就不要求同步增长

论文中：

- `CAPA` 论文把 `TR` 定义为本地平台从本地任务和跨平台任务中获得的总收益。
- `CAPA` 论文把 `CR` 定义为本地任务完成数占总本地任务数的比例。
- `GTA` 论文的核心指标是 `Total Profit` 与 `Acceptance Ratio`，其中 `Acceptance Ratio` 原始含义更偏“被合作平台接受的比例”，并不是 CPUL 论文中的同一个 `CR` 定义。

当前项目为了统一绘图，把 baseline 也统一输出成 `TR/CR/BPT`。这让实验对比更方便，但也意味着：

- `CR` 只是“完成了多少单”
- `TR` 是“完成后平台净赚多少”

如果一个算法完成了更多低利润跨平台任务，它完全可能出现：

- `CR` 更高
- `TR` 反而更低

### 原因 B：当前 `CAPA` 的跨平台任务单单收益显著低于本地任务

代码中：

- 本地任务收益在 `capa/utility.py` 中定义为
  - `Rev_loc = p_tau - zeta * p_tau`
  - 当前默认 `zeta = 0.2`
  - 所以本地任务固定得到 `0.8 * fare`
- 跨平台任务收益定义为
  - `Rev_cross = p_tau - platform_payment`
  - `platform_payment` 由 `DAPA` 的第二层平台拍卖支付决定

对一个 200 parcel 的 smoke 运行做统计时，得到：

- 总接单 `196`
- 本地任务 `106`
- 跨平台任务 `90`
- 本地任务平均收益约 `7.07`
- 跨平台任务平均收益约 `3.09`
- 跨平台平均平台支付约 `5.67`

这说明只要 `CAPA` 中有相当比例任务被送进 DAPA，`TR` 就会被显著拉低，即使 `CR` 很高也是如此。

### 原因 C：`GTA/ImpGTA` 的跨平台收益模型本来就更“赚钱”

当前 `BaseGTA/ImpGTA` 代码中：

- 本地任务收益仍然是 `fare - 0.2 * fare`
- 但跨平台任务收益是 `fare - AIM payment`
- `AIM payment` 来自各平台 `dispatch_cost` 的 second-price 结果
- `dispatch_cost` 由 `distance * unit_price_per_km` 计算，当前默认 `3.0/km`

这意味着 `BaseGTA/ImpGTA` 的跨平台支付更像“外平台最低可接受派单成本”，而不是 `CAPA` 论文里那种显式包含：

- courier detour/quality 偏好
- platform base price
- platform sharing rate
- platform quality factor
- 上限支付约束

因此，**即使 `CAPA` 与 `GTA` 的 `CR` 接近，`GTA` 也可能凭借更低的跨平台支付得到更高 `TR`**。这一点在当前结果中是可见的。

### 原因 D：`CAPA` 的高 `CR` 不是因为合作平台 courier 没有历史任务

这点已经核对过环境初始化，结论是否定的。

`env/chengdu.py` 里 `build_framework_chengdu_environment()` 调用 `Framework_ChengDu.GenerateOriginSchedule()` 生成所有 courier，而 `Framework_ChengDu.GenerateOriginSchedule()` 本身会用 delivery task 先为 courier 生成初始 `re_schedule`。

抽样和默认规模统计结果都表明：

- 本地 courier 和合作平台 courier 初始 `re_schedule` 都不是空的
- 默认实验规模 `3000 parcels / 200 local / 4x50 partner` 下：
  - local 平均 route 长度约 `38.44`
  - `P1 ~ P4` 平均 route 长度约 `37.10 ~ 39.06`
  - 所有 courier 的 `re_schedule` 都非空

所以，`CAPA` 的高 `CR` **不是**因为“合作平台 courier 没有历史任务需要完成”。

### 原因 E：`CAPA` 当前确实会高估 courier 的可服务能力

虽然 partner courier 不是空 route，但当前 `CAPA` 对“已有 route 的时序约束”处理得不够严格，这会**放大可行匹配数量**，从而抬高 `CR`。

主要问题有 3 个：

1. `legacy_courier_to_capa()` 把所有 courier 的 `available_from` 固定成 `0`
   - 位置：`env/chengdu.py`
   - 结果：`capa/cama.py` 和 `capa/dapa.py` 中 `is_courier_available()` 对所有 courier 几乎总是返回 `True`

2. `is_feasible_local_match()` / `is_feasible_cross_match()` 只检查
   - 当前点到 parcel 的直达 deadline feasibility
   - 当前容量
   - 服务半径
   - 但**没有检查 parcel 插入到现有 route 某个位置后，是否仍能在真正到达时刻前完成**

3. `find_best_local_insertion()` 只优化 detour ratio 和插入位置
   - 但**不验证插入后 route 前缀的累计 travel time**
   - 也不验证 route 里已有 drop-off/pick-up 任务的时序影响

这意味着当前 `CAPA` 实际上更接近：

- “只要从当前点直接赶得到 parcel，就把它视为 feasible”

而不是论文中更严格的：

- “在已有任务序列和实际插入位置下，parcel 仍然按时可完成”

这会显著抬高 `CAMA/DAPA` 的候选集合，使 `CR` 偏高。

### 原因 F：`CAPA` 的 batch retry 机制本来就会推高 `CR`

论文中明确写到：

- 本 batch 没有分配成功的 parcel 会回到下一 batch 重新匹配

当前实现也确实如此：

- `run_time_stepped_chengdu_batches()` 中 `backlog` 会持续进入下一轮
- 直到最后 arrival window 结束后，只要 route 还在推进，backlog 仍可继续重试

这会带来两个后果：

1. `CAPA` 的 `CR` 天然比“到达即刻决策、失败即丢弃”的算法更容易高。
2. 很多 parcel 是在更晚批次才被分配出去的，其中一部分会变成低利润 cross 任务，进一步拉低 `TR`。

因此，当前 `CAPA` 的高 `CR` 一部分是论文机制本身，一部分是约束过宽实现造成的。

### 原因 G：当前 `BaseGTA/ImpGTA` 也偏离论文 [17]

参考论文 [17] 的 BaseGTA/ImpGTA 核心条件是：

- inner/outer condition 依赖“idle worker”

而当前项目实现里，`BaseGTA/ImpGTA` 使用的是：

- `select_available_courier_for_task()`
- `count_available_couriers()`

这两个函数都不是“当前 idle”，而是：

- courier 当前 idle
  或
- courier 在当前 route 结束后、deadline 前能接这个任务

也就是说，当前 baseline 实际允许：

- 已经有 route 的 courier 在“未来 ready”后参与派单

这比论文 [17] 的“idle worker only”更强，会抬高 `BaseGTA/ImpGTA` 的 `CR` 和 `TR`。

因此，当前 `CAPA vs GTA` 的结果不是纯论文对论文，而是：

- 一侧 `CAPA` 的 route feasibility 偏松
- 一侧 `GTA/ImpGTA` 的 worker availability 也偏强

### 小结

当前 “`CAPA` 的 `CR` 高但 `TR` 低” 的主要解释是：

1. `TR` 与 `CR` 本来就不是单调关系。
2. `CAPA` 的跨平台收益显著低于本地收益，导致高 `CR` 不一定高 `TR`。
3. `GTA/ImpGTA` 的跨平台支付模型本来就更有利于本地平台赚钱。
4. `CAPA` 当前的 route feasibility 检查偏松，会把 `CR` 往上抬。
5. `CAPA` 的 backlog retry 机制本来就会提升 `CR`。
6. `GTA/ImpGTA` 当前也比 [17] 论文更强，会抬高其 `TR/CR`。

---

## 问题一的修正思路

### 修正目标

1. 让 `CAPA` 的可行性判断真正尊重已有 route 的时间约束。
2. 让 `GTA/ImpGTA` 的 worker availability 与 [17] 的 idle-worker 设定对齐。
3. 在实验输出中补充局部/跨平台收益拆分，避免只看 `TR/CR` 误判。

### 具体修复步骤

1. 修复 `CAPA` courier availability 语义
   - 在 `legacy_courier_to_capa()` 中不再把 `available_from` 固定为 `0`
   - 把 courier 的真实 earliest-feasible insertion time 或至少 route-ready time 映射进 snapshot

2. 修复 `CAPA` route-aware deadline check
   - 在 `find_best_local_insertion()` 的同时返回插入后的累计到达时间
   - 新增 `validate_insertion_timing()`，显式验证 parcel 在插入位置上的实际完成时刻是否晚于 deadline
   - `CAMA` 和 `DAPA` 都改为用“插入后真实时序可行”替代“当前点直达可行”

3. 修复 `CAPA` route prefix / suffix consistency
   - 明确已有 route 中任务的 reach/depart 语义
   - 至少保证“新 parcel 插入后不会破坏已有 route 的顺序与累计时长”

4. 修复 `BaseGTA/ImpGTA` 的 worker availability
   - 区分“严格 idle 版本”和“route-ready 版本”
   - 论文对齐实验应只允许当前 idle worker 参与本轮 inner/outer condition

5. 为实验补充收益拆分指标
   - 输出 `local_TR`, `cross_TR`, `local_assignments`, `cross_assignments`
   - 输出 `avg_revenue_per_local`, `avg_revenue_per_cross`
   - 这样可以直接解释为什么某算法 `CR` 高但 `TR` 低

### 审查点

1. `CAPA` 在默认规模下的 `CR` 是否仍长期贴近 `1.0`
2. `CAPA` 的 `cross/local` 收益拆分是否符合直觉
3. `GTA/ImpGTA` 改为 idle-only 后，`TR/CR` 是否明显回落，更接近 [17] 论文行为
4. `CAPA` 和 `GTA` 在同一实验脚本下的 metric 语义是否继续保持统一

---

## 问题二：`MRA` 的 `BPT` 为什么比其他算法大很多

### 结论

当前 `MRA` 的 `BPT` **不是因为它还在用“整批处理墙钟时间”**。现在的 `MRA` 已经和 `CAPA` 一样，返回的是 `timing.decision_time_seconds`。因此，`MRA` 比其他算法大很多，主要原因是**算法本身在当前实现中做了大量重复计算**。

### 代码证据

`baselines/mra.py` 当前返回：

- `BPT = timing.decision_time_seconds`

并不是旧版那种包含整批 movement/routing 的粗口径。

但 `MRA` 的 decision 部分本身就很重，原因在于：

1. 每个 batch 都可能进入多轮 `while remaining`
2. 每一轮都对每个 `remaining task` 全量重建 feasible graph
3. `build_legacy_feasible_insertions()` 已经做了一次 insertion 搜索
4. `compute_mra_bid()` 为了计算 detour term，又再次调用 `find_best_local_insertion()`
5. 选边时又对 `graph_edges` 做重复扫描：
   - 对每条边都 `min(candidate for candidate in graph_edges if same task)`

也就是说，当前 `MRA` 存在明显的“重复可行性计算 + 重复插入计算 + 重复边扫描”。

### 运行证据

在一个 `120 task / 20 local / 2x10 partner` 的小型 profile 中：

- `MRA`：
  - `BPT ≈ 0.1766s`
  - 总 runtime 约 `0.376s`
  - 热点集中在：
    - `build_legacy_feasible_insertions`
    - `is_feasible_local_match`
    - `find_best_local_insertion`
    - `getShortestDistance`
- `BaseGTA`：
  - `BPT ≈ 0.0299s`
  - 总 runtime 约 `0.188s`

这说明：

1. `MRA` 的 decision-time 确实比其他算法大。
2. 主要不是计时口径问题，而是 graph 构造和 detour 计算的重复开销。

### 具体原因

#### 原因 A：多轮匹配

`MRA` 每个 batch 不是一次分配完成，而是：

- 构图
- 选一轮匹配
- 移除已分配任务
- 对 `remaining` 再重复一轮

这使得 batch 内 decision 次数与 `remaining` 规模耦合，任务越多越重。

#### 原因 B：重复 insertion

`build_legacy_feasible_insertions()` 已经计算了每个 `(task, courier)` 的最优插入位置；
但 `compute_mra_bid()` 又把同一个 courier-task pair 重新投影成 CAPA snapshot，再调用一次 `find_best_local_insertion()` 来得到 detour term。

这部分重复工作在大规模 batch 下会迅速放大。

#### 原因 C：选边阶段重复扫描整张图

当前代码在遍历 `ordered_edges` 时，对每条 edge 都再次执行：

- “找出该 task 的最小 bid edge”

这相当于在大 edge set 上嵌套了一层按 task 过滤的扫描，纯 Python 开销很高。

### 小结

当前 `MRA` 的 `BPT` 大，主要是：

1. 多轮构图
2. 同一 `(task, courier)` 的 detour 重算
3. 选边时反复扫描 `graph_edges`

因此，这个问题本质上是**算法实现效率问题**，不是当前 `BPT` 口径没有和其他算法对齐。

---

## 问题二的修正思路

### 修正目标

在不改变 `MRA` 算法选择结果的前提下，减少重复计算，把 `BPT` 压回“与其他 baseline 同数量级但仍高于 Greedy/GTA”的合理区间。

### 具体修复步骤

1. 复用 feasible insertion 结果
   - 让 `build_legacy_feasible_insertions()` 返回 detour ratio 或可直接用于 `MRA bid` 的中间量
   - `compute_mra_bid()` 不再二次调用 `find_best_local_insertion()`

2. 预聚合 `best bid per task`
   - 在构完 `graph_edges` 后先建立 `task_id -> best_edge`
   - 选边时不要在循环里反复 `min(...)`

3. 降低 snapshot 和 cache 抖动
   - 尽量在同一轮内复用 `project_courier_to_capa()` 结果
   - 减少同一 courier 被多次重复投影

4. 评估是否保留“每轮全量重构”
   - 若不改变行为，可以只对受上一轮影响的 courier/task 重新计算边
   - 若实现复杂度过高，可先做前 3 项

### 审查点

1. 修复前后同一 seed 的 `TR/CR` 必须完全一致
2. `MRA` 的 `BPT` 应明显下降，但仍高于 `Greedy/BaseGTA`
3. profile 热点中 `find_best_local_insertion()` 与 `graph_edges` 扫描占比应明显下降

---

## 问题三：当前 `ImpGTA` 是否实现了论文中的预测

### 结论

**没有。当前 baseline 中的 `ImpGTA` 只实现了“未来窗口过滤”的一个简化近似，而且还是部分实现，不是论文 [17] 中真正的 prediction-based ImpGTA。**

更具体地说：

1. 当前实现没有历史数据训练/预测模块。
2. 当前实现没有网格化时空预测结果 `~T_{Δτ}`。
3. 当前实现没有按平台维护未来分布预测。
4. 当前 outer platform 的预测逻辑实际上是失效的。

### 与论文 [17] 的要求对比

论文 [17] 中的 ImpGTA 要求：

1. 基于历史数据预测未来窗口 `Δτ` 内的任务分布
2. 预测结果不是“未来真实任务列表”，而是：
   - 某窗口内任务数量
   - 奖励分布
   - `U_exp`
3. inner / outer condition 都要基于该预测结果决策

当前代码没有做到这些。

### 当前实现的实际行为

#### 行为 A：local side 用的是“未来真实任务”，不是“预测结果”

当前代码里：

- `local_future_tasks = future_tasks_within_window(remaining_tasks, current_time, prediction_window_seconds)`

这里的 `remaining_tasks` 是实验输入中已经已知的后续真实任务流，因此它更接近：

- oracle lookahead

而不是：

- 基于历史数据训练得到的预测分布

这与论文 [17] 的设定不同。

#### 行为 B：outer side 的预测条件实际上没有生效

当前代码里，outer platform 调用：

- `should_bid_outer_platform_impgta(..., future_tasks=[])`

而 `should_bid_outer_platform_impgta()` 的逻辑是：

- 如果 `idle_worker_count > len(future_tasks)`，返回 `True`
- 否则判断 `dispatch_cost >= expected_future_reward(future_tasks)`

由于这里传入的是空列表：

- `len(future_tasks) = 0`
- `expected_future_reward([]) = 0`

所以只要 platform 有至少一个可用 courier，outer condition 基本恒成立。也就是说：

- **当前 `ImpGTA` 的 outer prediction 逻辑几乎被关闭了**

#### 行为 C：没有 per-platform future demand

论文 [17] 中 outer platform 应该依据“自己平台在未来窗口内的任务分布”决定是否参与 bidding。

当前实现中：

- local 只看全局 `remaining_tasks`
- outer 根本没有自己的 future task prediction

因此它没有实现论文里 platform-specific 的 future supply-demand balancing。

### 小结

当前 `ImpGTA` 最准确的描述应当是：

- “带未来窗口启发式过滤的 GTA”

而不是：

- “论文 [17] 意义上的预测型 ImpGTA”

---

## 问题三的修正思路

### 修正目标

把当前 `ImpGTA` 从“future lookahead heuristic”修成“基于历史预测结果的 paper-faithful baseline”。

### 具体修复步骤

1. 定义预测接口
   - 新增 `predict_task_distribution(platform_id, now, delta_tau)` 接口
   - 输出至少包含：
     - predicted task count
     - expected reward `U_exp`
     - 可选：空间网格分布

2. 构建历史数据来源
   - 从训练日或历史窗口中提取任务记录
   - 不能直接读取当前 run 中未来真实任务作为“预测结果”

3. 重写 inner condition
   - 按论文 [17] 使用：
     - `|W^pk| > |~T_Δτ^pk|`
     - 或 `v_tj >= U_exp(~T_Δτ^pk)`

4. 重写 outer condition
   - 每个 partner platform 都必须基于自己的预测任务集判断：
     - `|W^pi| > |~T_Δτ^pi|`
     - 或 `su_ij >= U_exp(~T_Δτ^pi)`

5. 保留 baseline 与 oracle 两种模式
   - baseline 正式实验只允许使用历史预测
   - 若要保留当前 lookahead 版本，应明确标成 ablation 或 oracle-upper-bound

### 审查点

1. `ImpGTA` 代码中不应再直接使用 `remaining_tasks` 作为预测结果
2. outer platform 的 `future_tasks` 不应再是空列表
3. 调节 `prediction_window_seconds` 时，`ImpGTA` 的 `TR/CR/BPT` 应体现论文中“Δτ 影响 prediction quality”的趋势
4. baseline 报告中应明确写明“prediction”来自历史预测而不是未来真值

---

## 总体修复优先级

### P0：先修实验可信度

1. 修 `CAPA` 的 route-aware feasibility
2. 修 `BaseGTA/ImpGTA` 的 idle-worker 语义
3. 修 `ImpGTA` 的 outer prediction 失效问题

### P1：再修性能与可解释性

1. 修 `MRA` 的重复 insertion / 重复扫描
2. 增加 `local/cross` 收益拆分输出
3. 增加 `CAPA` backlog retry 轮数与 cross share 的诊断指标

### P2：最后修论文忠实性

1. 为 `ImpGTA` 接入真正的历史预测接口
2. 明确区分：
   - paper-faithful baseline
   - Chengdu adaptation
   - oracle/lookahead ablation

---

## 最终判断

1. `CAPA` 当前 `CR` 高但 `TR` 低，并不是单纯的结果错误；但当前实现确实存在会放大该现象的代码偏差。
2. `CAPA` 的高 `CR` 不是因为合作平台 courier 没有历史任务；合作平台 courier 初始 route 也是满的。更关键的问题是当前 `CAPA` 没有严格尊重已有 route 的时间约束。
3. `MRA` 的 `BPT` 大，当前主要是算法实现重复计算过多，不是口径仍未对齐。
4. 当前 `ImpGTA` 并没有实现论文 [17] 中真正的 prediction-based baseline，只是实现了一个局部 future-window 启发式，而且 outer prediction 逻辑基本失效。
