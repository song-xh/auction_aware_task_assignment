# Review 2026-04-25

本审查只阅读代码与本地数据，不修改运行逻辑。重点结论：包裹时间窗抽样逻辑已经接入统一环境，但数据读取存在 `order_20161101_deal3` 漏读问题；CAPA 的主要收益与拍卖公式已实现，但若严格按论文默认参数和 Eq.(7) 累积阈值看仍有偏差；RL-CAPA 当前按旧 `docs/rl_capa_algo.md` 流程运行，第二阶段只处理 CAMA 剩余包裹，并没有完全替代动态阈值；ImpGTA 的预测成功率只影响本地 inner 条件，outer 条件未使用预测，且 cross bid 仍是 AIM/dispatch-cost 逻辑，不是 CAPA 的 FPSA/RVA bid 逻辑。

## 1. 数据集、生成时间、deadline、时间窗抽样

### 当前统一实验实际使用的数据

- 统一 Chengdu 环境入口是 `env/chengdu.py::build_framework_chengdu_environment()`。
- 包裹/初始 drop-off 任务来自 `Tasks_ChengDu.py::readTask()`，该函数读取：
  - `Data/order_20161101_deal1`
  - `Data/order_20161101_deal2`
  - `Data/order_20161101_deal3`
  - `Data/order_20161101_deal4`
- `Data/order_20161101_deal` 目前用于 `env/chengdu.py::load_station_blueprints()` 构造 station 网格范围，不是统一实验直接读取的任务流。
- `Data/delivery_tasks.txt`、`Data/pick_up_tasks.txt` 是预处理后的任务文件，但当前统一环境没有使用它们。

### 当前代码读取的字段

`Tasks_ChengDu.py::parse_task_line()` 将 `order_20161101_deal1..4` 中每行解析为：

- `cols[0]` -> `Task.num`
- `cols[1]` -> `Task.l_lng`
- `cols[2]` -> `Task.l_lat`
- `cols[3]` -> `Task.l_node`
- `cols[4]` -> `Task.s_time`
- `cols[5]` -> `Task.d_time`
- `cols[6]` -> `Task.weight`
- `cols[7]` -> `Task.fare`

其中 `fare != 0` 被作为 pick-up parcel，`fare == 0` 被作为 delivery seed/drop-off background task。

### 当前代码下的时间范围

通过当前 `readTask()` 实际加载后的统计：

- pick-up parcel 数：`157065`
- delivery seed/drop-off 数：`471205`
- pick-up `s_time` 最早：`0.0`
- pick-up `s_time` 最晚：`14398.0`
- delivery seed 的 `s_time` 当前均为 `0.0`

按原始四个 split 文件逐个统计，每个文件实际都有约 `52355` 个 pick-up 与 `157068` 个 delivery seed，四个文件合计应约为 `209420` 个 pick-up 与 `628272` 个 delivery seed。当前 `readTask()` 中 `order_20161101_deal3` 的 append 逻辑缩进在循环外，导致 deal3 只保留最后一行；这是明确的数据 ingestion bug。它不改变当前观测到的全局最早/最晚 pick-up 时间范围，但会少读约四分之一任务。

### 时间窗抽样逻辑

时间窗抽样由 `env/chengdu.py::select_station_pick_tasks()` 实现：

- 若 `window_start_seconds is None`，默认使用当前已加载 pick-up 流的最早 `s_time`。
- 若 `window_end_seconds is None`，默认使用当前已加载 pick-up 流的最晚 `s_time`。
- 函数先按时间窗和 station bounds 过滤候选包裹。
- 若候选数量大于 `num_parcels`，用 `random.Random(sampling_seed).sample(candidates, num_parcels)` 随机抽样。
- 抽样后会再按 `(s_time, d_time, num)` 排序，因此仿真推进仍按时间顺序播放被抽中的任务。

结论：在当前统一环境下，如果命令指定了 `--task-window-start-seconds` / `--task-window-end-seconds`，代码确实是在该时间段内随机选择指定数量包裹；如果没指定时间窗，默认是在当前已加载 pick-up 数据的全时间范围 `[0.0, 14398.0]` 内随机抽样。但这个结论受 `readTask()` 漏读 deal3 的问题影响。

## 2. CAPA 论文参数与代码一致性

### 已实现且基本对齐的部分

- 固定本地 courier payment：论文 Definition 4 使用 `Rc(τ,c)=ζ·pτ`，代码在 `capa/utility.py::compute_local_courier_payment()` 实现，默认 `ζ=0.2`。
- 本地收益：代码在 `compute_local_platform_revenue_for_local_completion()` 中计算 `fare - ζ·fare`。
- 跨平台收益：代码在 `compute_local_platform_revenue_for_cross_completion()` 中计算 `fare - platform_payment`。
- CAMA utility：论文 Eq.(6) 的容量项与绕路项在 `capa/utility.py::calculate_utility()` 中实现，默认 `φ/gamma=0.5`。
- 动态阈值：`capa/cama.py::run_cama()` 会计算 `calculate_threshold()`，并用 `best_pair.utility.value >= threshold` 决定本地匹配或进入 auction pool。
- DLAM 的主要结构：`capa/dapa.py::run_dapa()` 实现了 first-layer courier bid 与 second-layer platform reverse auction，收益结算也复用 CAPA revenue 函数。

### 与论文设置不完全一致的部分

- Batch size 默认值：论文 Table II 给出 `Δb=20s`；代码 `capa/config.py::DEFAULT_CAPA_BATCH_SIZE = 300`，runner 默认也是 `300s`。命令行可覆盖，但默认不是论文默认值。
- 平台 sharing rate `γ`：论文 Table III 中 cooperating platforms 的 `γ=0.5`；代码 `DEFAULT_PLATFORM_SHARING_RATE = DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2 = 0.4`。这是参数默认值不一致。
- `μ1, μ2` 默认组合：代码默认 `μ1=0.5, μ2=0.4`，满足 `μ1+μ2<=1` 且 sum=0.9，但不在论文 Table II 的 `[μ1, μ2]` 枚举列表中。
- Courier preference `α, β`：论文实验说明为均匀生成；当前 legacy courier 的 `w/c` 由 `GenerateOriginSchedule(..., preference=DEFAULT_COURIER_PREFERENCE)` 固定为 `0.5/0.5`，不是 per-courier 随机生成。
- 历史服务质量 `g(c)` 与平台合作质量 `f(P)`：代码用固定 `service_score=0.8` 和平台质量 `1.0, 0.9, ...` 代理，未从历史服务记录估计。
- `p_min` 约束：论文要求 `p_min <= (1-γ)p'_τ`；代码默认 `p_min=1.0`，未在配置构造或 DAPA 中显式校验该约束。
- Eq.(7) 动态阈值口径：论文公式写成到时间 `t` 的累计候选对平均；当前 `run_cama()` 只对当前 batch 的 `all_feasible_pairs` 求平均，没有维护跨 batch 累计的 `M_t` 历史。

结论：收益定义和核心 CAMA/DAPA 机制已有实现，但若按论文默认实验参数严格复现，至少需要修正 `Δb` 默认、platform `γ` 默认、courier preference 生成、以及 Eq.(7) 阈值累计口径。

## 3. RL-CAPA 当前逻辑审查

### 当前已经符合的部分

- 第一阶段动作是离散 batch duration。`rl_capa/config.py::RLCAPAConfig.batch_action_values()` 返回 `[min_batch_size, ..., max_batch_size]`。
- 训练时第一阶段用 `Categorical` 采样；评估时用 argmax。
- 第二阶段 actor 是共享参数的 parcel-level 二分类策略。`rl_capa/networks.py::CrossOrNotActor` 对每个 parcel state 输出一个 Bernoulli distribution。
- 训练时第二阶段按 Bernoulli 采样；评估时用 `prob > 0.5`。这个 0.5 是固定评估阈值，不是学习到的阈值。
- 第二阶段 `a=1` 的包裹进入 `run_chengdu_cross_matching()`，即 DAPA；`a=0` 的包裹进入 backlog。
- 如果 `a=1` 但 DAPA 无法承接，该包裹会被加入 `unresolved_tasks`，最终进入 `runtime.backlog`，下个 batch 再决策。
- 环境推进复用 `env/chengdu.py` 的 `initialize_chengdu_batch_runtime()`、`prepare_chengdu_batch()`、`run_chengdu_cross_matching()`、`finalize_chengdu_batch()`、`finalize_chengdu_runtime()`，不是重新写的推进环境。

### 与本轮需求不一致的部分

当前 `rl_capa/env.py::run_local_matching()` 直接调用 `capa.cama.run_cama()`。由于 `run_cama()` 内部包含动态阈值判断，RL-CAPA 的第二阶段只对 CAMA 后的 `remaining_tasks` 做 cross-or-not。也就是说：

- 本地可行且高于阈值的包裹会直接本地匹配，第二阶段 RL 看不到它们。
- 本地可行但低于阈值的包裹会被 CAMA 放入 auction pool，然后第二阶段 RL 决定 cross 或 delay。
- 本地不可行的包裹也进入第二阶段。

这符合旧 `docs/rl_capa_algo.md` 第 15 节的“调用 CAMA 后对 ΔΓ 做决策”的流程，但不符合本轮提出的“第二阶段直接决定 cross-or-not，不包括 CAPA 动态阈值判断”的更强语义。如果本轮语义是新的实现准则，需要将 RL 的本地阶段改成“只做本地可行性/最优本地插入，不做动态阈值筛选”，让主动 delay/cross 的策略由第二阶段 RL 承担。

### 其他 RL-CAPA 偏差

- 论文正文的第一阶段 state 包含未来供需预测项 `N_Z^Γ, N_Z^C`，当前 `docs/rl_capa_algo.md` 与代码使用 4 维 state，未包含这两个预测特征。
- 论文实验说明用 RMSprop；`docs/rl_capa_algo.md` 与当前代码使用 Adam。若以 `docs/rl_capa_algo.md` 为准这是可接受的；若以论文为准则不一致。
- `rl_capa/evaluate_core.py::evaluate()` 的 BPT 目前只累计 `π1/π2` 推理时间，不包含 CAMA/DAPA 分配处理时间。若要求与 CAPA/Baseline 的 BPT 口径完全一致，需要改成使用统一 batch report/timing 的 assignment processing time。

## 4. ImpGTA 当前逻辑审查

### 预测成功率是否真正使用

`baselines/gta.py::future_tasks_within_window()` 确实使用了 `prediction_success_rate`：

- `<=0` 返回空预测窗口。
- `>=1` 返回窗口内真实未来任务。
- `(0,1)` 用确定性随机数按成功率 down-sample 真实未来任务。

`_run_gta_environment()` 在 `algorithm == "impgta"` 时会为本地平台计算 `local_future_tasks`，并传入 `should_dispatch_inner_task_impgta()`。因此，预测成功率目前确实影响 ImpGTA 的 inner/local 条件。

但 outer 条件没有真正使用预测：`should_bid_outer_platform_impgta(..., future_tasks=[])` 当前固定传空列表，导致 outer platform 侧总是因为 `idle_worker_count > len(future_tasks)` 更容易通过，`prediction_success_rate` 对 outer bidding decision 没有作用。这与参考文献 [17] 中 inner/outer 都基于未来窗口预测判断的 ImpGTA 不一致。

另外，当前预测是“从真实 `remaining_tasks` 中按成功率 down-sample”的简化前瞻，不是参考文献 [17] 中基于历史数据、网格、时间段预测任务数量与收益分布的模型。

### ImpGTA bid 逻辑是否与 CAPA 一致

不一致。当前 ImpGTA 和 BaseGTA 共用 `_run_gta_environment()`：

- 可行 worker 选择使用 `select_available_courier_for_task()`，bid 是 `dispatch_cost=(incremental_distance_km * unit_price_per_km)`。
- 跨平台拍卖使用 `settle_aim_auction()`，即 AIM 的最低 dispatch cost winner 与 critical payment。
- 该路径没有使用 CAPA 的 `compute_fpsa_bid()`、`compute_platform_quality_factor()`、`compute_platform_payment_limit()` 或 `run_dapa()`。

因此当前 ImpGTA 与 CAPA 的差异不只是“预测替代动态阈值”，还包括 cross bid/payment 机制仍是 GTA/AIM。若要满足本轮要求，ImpGTA 的 cross bidding 必须改为 CAPA/DLAM 的 FPSA + RVA 口径，至少在 payment/revenue 和 winner selection 上复用 `capa.dapa` 的实现。

## 5. 需要修改的结论清单

- 修复 `Tasks_ChengDu.py::readTask()` 对 `order_20161101_deal3` 的漏读。
- 决定并修正 paper-faithful 默认参数：`Δb=20s`、platform `γ=0.5`、`μ1/μ2` 默认组合、courier preference 生成方式、`p_min` 约束检查。
- 将 CAMA 动态阈值从当前 batch 平均改为可维护历史累计口径，或明确在文档中声明当前实现是 batch-local 阈值。
- 按本轮需求调整 RL-CAPA：第二阶段应直接承担 cross-or-delay 决策，不能让动态阈值先替 RL 过滤。
- 对齐 RL-CAPA BPT 与统一实验指标口径。
- 修正 ImpGTA outer prediction：outer 条件必须使用预测成功率影响后的未来任务窗口。
- 修正 ImpGTA cross bid：ImpGTA 的 cross bid/payment 应复用 CAPA 的 FPSA/RVA 原则，而不是 AIM dispatch-cost。
