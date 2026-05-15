# Courier Capacity 语义：按 parcel weight 求和，非 parcel 个数

## 1. 现状审计：全栈 weight-based

`--courier-capacity X` 实际表示「该骑手 route 上同时持有的 parcel **weight 之和** 不能超过 X」，而不是「持有的 parcel **个数** 不能超过 X」。整条链路的关键代码点：

| 模块 | 位置 | 行为 |
|------|------|------|
| Tasks_ChengDu.Task | `Tasks_ChengDu.py:22` | `self.weight = weight`：成都数据集 CSV 第 7 列直接成为 `task.weight`。 |
| Framework_ChengDu.Courier | `Framework_ChengDu.py:32` | `self.max_weight = parameter_capacity_c`，CLI `--courier-capacity` 经 `env/chengdu.py:2186-2188` 注入。 |
| Framework_ChengDu.TaskSchedule | `Framework_ChengDu.py:255` | `if temp_cost + temp_last_cost <= 14400 and temp_weight <= parameter_capacity` —— legacy 初始化阶段就用 `temp_weight`（累加 `task.weight`）做约束。 |
| env.chengdu.apply_assignment_to_legacy_courier | `env/chengdu.py:884` | `courier.re_weight += float(task.weight)` —— 每次接单累加 weight，不是 +1。 |
| env.chengdu.legacy_courier_to_capa | `env/chengdu.py:773-774` | `capacity=max_weight`, `current_load=re_weight`，映射到 CAPA `Courier` 时单位一致。 |
| capa.cama.is_feasible_local_match | `capa/cama.py:40` | `if courier.current_load + parcel.weight > courier.capacity: return False`。 |
| capa.cama.is_feasible_local_candidate | `capa/cama.py:66` | 同上。 |
| capa.dapa.is_feasible_cross_match | `capa/dapa.py:32` | 同上。 |
| baselines.greedy / baselines.mra | `baselines/greedy.py:357-358`、`baselines/mra.py:81-82` | `remaining = max_weight − re_weight`；bid 用 `parcel.weight / remaining` 作 capacity_term。 |
| baselines.gta.available_capacity_weight_sum | `baselines/gta.py:357` | `Σ(max_weight − re_weight)` 返回 weight 单位的剩余总容量。 |
| baselines.gta.future_task_weight_demand | `baselines/gta.py:416` | `Σ task.weight` 计算未来需求；与 supply 同口径。 |

结论：**没有任何一处使用 `len(re_schedule)` 或 parcel count 来做 capacity 约束**。`courier.batch_take` 只是诊断计数器，不参与可行性判断。

## 2. 数据集 weight 分布

抽样 `Data/order_20161101_deal1` 前 3789 行：

| stat | mean | median | min | max | p10 | p50 | p90 | p99 |
|------|------|--------|-----|-----|-----|-----|-----|-----|
| weight | 1.147 | 1.020 | 0.000 | 5.240 | 0.190 | 1.020 | 2.300 | 3.290 |

含义：`--courier-capacity 50` ≈ 「该骑手任何时刻 route 上最多 50 weight 单位 ≈ 43 个均价包裹」。如果想表达「最多 5 个包裹」，配置应改为 `--courier-capacity 5`（实际约束 = 5 weight ≈ 4 个均价包裹）。

## 3. 实测一致性检查

`exp1_test_zeta_08`、n=20000、`courier_capacity=50`、`local_couriers=100`：

- MRA local 累计派单 6534 单 → 平均每个 courier lifetime 派 65.34 单。
- 平均每单 weight ≈ 1.15。
- 但 `re_weight ≤ 50` 是 *同时*持单的上限，不是 lifetime —— 每次 deliver 释放 weight，所以 lifetime 远超 50。
- 实测说明 capacity 约束在并发持单层面生效（否则不需要 deadline=240 这类时间约束，骑手已被 weight 上限卡住）。

## 4. 本轮改动

非功能性修复 + 文档化：

1. 把 `baselines/gta.py::count_available_capacity_slots` 重命名为 `available_capacity_weight_sum`，docstring 显式说明单位。该函数从来就在加权，旧名「count_*_slots」纯属误导，没有任何调用方依赖「count」语义。
2. 同步 `tests/test_metric_alignment.py` 的 import 与 `test_impgta_available_supply_counts_capacity_slots` 的引用。
3. 新增三条回归测试：
   - `test_courier_capacity_is_measured_in_parcel_weight_sum`：构造 capacity=6.0、三个 2.0-weight parcel 全过，第四个 2.0 失败；并断言单个 7.0-weight parcel 一次性也不能塞进 capacity=6.0。
   - `test_apply_assignment_accumulates_legacy_re_weight_by_task_weight`：连续 `apply_assignment_to_legacy_courier` 两次，weight 0.5 → 0.5+1.25+0.75 = 2.5，`batch_take=2`；锁定 `re_weight` 是 weight 累加而非计数。
   - `test_available_capacity_weight_sum_returns_weight_units`：三个 courier `Σ(max_weight − re_weight)` = 18.5，验证残余容量是 weight 单位。

任一回归一旦被无意改回「count」语义，相应测试都会立刻失败，把回归卡死在 PR 时刻。

## 5. 不需要改的地方

- `Framework_ChengDu.py:254` 已经是 `temp_weight <= parameter_capacity`。注释里的「`temp_task_num <= 51 parameter_capacity 调参`」属于历史注释，不影响行为。如果担心后续阅读混淆，可以把注释里那段「`temp_task_num <= 51`」删掉，但不算 must-do。
- CLI 参数命名 `--courier-capacity`：保留。若改成 `--courier-capacity-weight` 会破坏现有脚本。文档（本文件 + `docs/tr_cr_analysis.md` §5）已显式标注单位。

## 6. 引用

- 代码：`capa/cama.py:28-77`、`capa/dapa.py:32-`、`env/chengdu.py:444-457, 773-774, 877-885, 2186-2188`、`baselines/gta.py:357-419`、`baselines/greedy.py:357-358`、`baselines/mra.py:81-82`、`Framework_ChengDu.py:32, 255`。
- 测试：`tests/test_metric_alignment.py`（新增三条 + 重命名一处 import）。
- 数据：`Data/order_20161101_deal1` 第 7 列 weight 抽样统计。
