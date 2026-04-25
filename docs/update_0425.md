# Update Plan 2026-04-25

本计划按 `docs/review_0425.md` 的审查结论排序。后续执行时每个阶段完成后都需要先跑对应测试，再提交；禁止用 fallback、随机兜底或“失败后退化到 greedy”的逻辑掩盖问题。

## Phase 1: 修复 Chengdu 数据读取与时间窗抽样可验证性

### 1.1 修复 `order_20161101_deal3` 漏读

- 文件：`Tasks_ChengDu.py`
- 函数：`readTask()`
- 修改点：将读取 `Data/order_20161101_deal3` 时的 `count += 1`、`fare != 0` 判断和 append 逻辑缩进回 `for line in f:` 循环内。
- 实现效果：四个 split 文件都完整参与统一实验；当前约 `157065` 个 pick-up 应恢复到约 `209420` 个 pick-up，delivery seed 也应恢复到约 `628272` 个。
- 检查点：
  - 增加或更新一个数据读取测试，验证 `readTask()` 至少读入四个文件的全部记录。
  - 运行一个时间窗抽样小样本，确认 `legacy_pick_task_time_bounds()` 仍返回全局范围，且 `select_station_pick_tasks()` 仍按 seed 确定性抽样。

### 1.2 将时间窗默认与抽样行为显式测试

- 文件：`tests/test_paper_canonical_seed_axes.py` 或新增 `tests/test_chengdu_task_sampling.py`
- 函数：覆盖 `select_station_pick_tasks()` 与 `ChengduEnvironment.build()`
- 修改点：
  - 测试 `task_window_start_seconds=None` / `task_window_end_seconds=None` 时使用数据集最早/最晚时间。
  - 测试相同 `task_sampling_seed` 产生相同任务集合，不同 seed 在候选足够时产生不同任务集合。
  - 测试抽样后任务按 `(s_time, d_time, num)` 排序推进。
- 实现效果：防止后续实验误退回“按时间顺序截取前 N 个包裹”。

## Phase 2: 对齐 CAPA 论文参数与动态阈值口径

### 2.1 修正或显式暴露 paper-faithful 默认参数

- 文件：`capa/config.py`
- 相关常量：
  - `DEFAULT_CAPA_BATCH_SIZE`
  - `DEFAULT_PLATFORM_SHARING_RATE`
  - `DEFAULT_LOCAL_SHARING_RATE_MU1`
  - `DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2`
  - `DEFAULT_PLATFORM_BASE_PRICE`
- 修改点：
  - 若以论文 Table II/III 为默认，`DEFAULT_CAPA_BATCH_SIZE` 应改为 `20`，`DEFAULT_PLATFORM_SHARING_RATE` 应改为 `0.5`。
  - `μ1/μ2` 需要选择论文表中一个默认组合；建议使用 `[0.5, 0.5]`，除非实验配置明确覆盖。
  - 在构造 platform/courier 配置时校验 `μ1 + μ2 <= 1`。
  - 在 DAPA 前校验 `p_min <= (1 - γ) * μ1 * pτ`，如果配置违反论文约束，直接抛错，不做自动修正。
- 实现效果：默认配置与论文表述一致，异常参数显式失败。
- 检查点：
  - 更新 `tests/test_capa_config.py`。
  - 运行 `python3 -m pytest tests/test_capa_config.py`。

### 2.2 修正 courier preference 与 service score 代理方式

- 文件：`env/chengdu.py`
- 函数：
  - `build_framework_chengdu_environment()`
  - `legacy_courier_to_capa()`
- 修改点：
  - 如果论文复现实验要求 per-courier preference 均匀生成，则在 environment seed 构建阶段用固定 seed 为每个 courier 生成 `alpha`，`beta=1-alpha`，并随 canonical seed 持久化。
  - 不要在每次算法运行时重新随机生成，避免同一实验点不同算法环境不一致。
  - `service_score` 若没有真实历史质量数据，应继续作为显式代理参数，但必须固定并写入 seed，而不是隐式默认。
- 实现效果：同一 seed 下所有算法共享相同 courier preference；不同 seed 可复现地变化。
- 检查点：
  - 更新 `experiments/seeding.py` 的 seed 序列化测试。
  - 检查相同 canonical seed 下 CAPA/Greedy/BaseGTA/ImpGTA 的 courier preference 完全一致。

### 2.3 将 CAMA 阈值改成可维护历史累计口径

- 文件：`capa/cama.py`
- 函数：
  - `run_cama()`
  - `calculate_threshold()` 的调用点
- 文件：`env/chengdu.py`
- 结构：`ChengduBatchRuntime`
- 修改点：
  - 在 runtime 中新增 threshold history，例如 `threshold_utility_sum` 与 `threshold_pair_count`。
  - `run_cama()` 增加显式参数，例如 `threshold_history: ThresholdHistory | None`；CAPA 主流程必须传入 runtime history。
  - 当前 batch 的 all feasible pairs 先加入累计，再根据累计平均计算 Eq.(7) `Th`。
  - 单元测试里保留当前 batch-local 行为的测试用例时，应改名为内部 helper 测试，不作为 CAPA 主路径。
- 实现效果：动态阈值与论文 Eq.(7) 的累计候选对平均一致。
- 检查点：
  - 新增 synthetic 两 batch 测试：第二 batch 的 threshold 必须受第一 batch utility 影响。
  - 运行 `python3 -m pytest tests/test_capa_local.py tests/test_full_pipeline.py`。

## Phase 3: 修正 RL-CAPA 第二阶段语义与指标口径

### 3.1 拆分 CAMA candidate 构建与阈值筛选

- 文件：`capa/cama.py`
- 函数：
  - 新增 `build_cama_candidate_pairs()` 或等价内部 helper。
  - 保留 `run_cama()` 作为 CAPA paper path，继续执行动态阈值。
  - 新增 `run_cama_without_threshold()` 或 `run_local_feasible_matching()`，只做本地可行性检查、最佳本地 courier 选择与 route commit，不做 Eq.(7) 阈值筛选。
- 实现效果：CAPA 仍使用动态阈值；RL-CAPA 可以复用 CAMA 可行性和 utility/insertion 逻辑，但不被动态阈值提前分流。
- 检查点：
  - 构造一个 synthetic case：某 parcel 有本地可行 courier 但 utility 低于 CAPA threshold。`run_cama()` 应将其送入 auction pool；`run_cama_without_threshold()` 应本地匹配它。

### 3.2 修改 RL-CAPA 本地阶段

- 文件：`rl_capa/env.py`
- 函数：`RLCAPAEnv.run_local_matching()`
- 修改点：
  - 将当前 `run_cama()` 调用替换为 Phase 3.1 的 threshold-free local matching 函数。
  - `unassigned` 应只包含本地不可行或本地 route/capacity/deadline 不能承接的包裹。
  - 第二阶段仍对 `unassigned` 执行 `a=0 defer` / `a=1 DAPA`。
  - 若后续需求要求“第二阶段对所有 batch parcel 决定 local/cross/defer”，需要另行扩展动作空间；本计划按本轮描述中的“本地无法匹配时可主动 delay/cross”解释执行。
- 实现效果：RL-CAPA 不再使用 CAPA 动态阈值替代第二阶段策略，主动 delay 由 RL 决定。
- 检查点：
  - 更新 `tests/test_rl_env_smoke.py`，验证本地低 utility 但可行的 parcel 不再被动态阈值推入 RL stage2。
  - 验证 `a=1` 且 DAPA 失败时 parcel 进入下一 batch backlog。
  - 验证 `a=0` 的 parcel 进入下一 batch backlog。

### 3.3 对齐 RL-CAPA BPT 口径

- 文件：`rl_capa/evaluate_core.py`
- 函数：`evaluate()`
- 文件：`rl_capa/env.py`
- 函数：`RLCAPAEnv.apply_cross_decisions()`
- 修改点：
  - 不再只统计 `π1/π2` forward inference time。
  - 从 finalized batch report 或 environment timing 中取与 CAPA 一致的 batch assignment processing time。
  - 若项目当前定义要求排除 routing/insertion/movement，则 RL-CAPA 也必须使用相同的 `decision_time_seconds` 累计，不单独使用 policy inference time。
- 实现效果：RL-CAPA 的 BPT 与 CAPA、Greedy、GTA、MRA、RamCOM 处在同一评测口径。
- 检查点：
  - 新增测试比较 RL-CAPA eval 的 BPT 与 batch reports 的 timing 聚合一致。

### 3.4 检查 RL-CAPA state 与训练配置

- 文件：`rl_capa/state_builder.py`
- 函数：
  - `build_stage1_state()`
  - `build_stage2_states()`
- 修改点：
  - 当前实现按 `docs/rl_capa_algo.md` 使用 4 维 stage1 state。如果下一轮要求完全按论文正文，则需要加入 `N_Z^Γ`、`N_Z^C` 两个预测特征，并同步修改 `BatchSizeActor` 和 `StateValueCritic` 输入维度。
  - 当前 optimizer 按 `docs/rl_capa_algo.md` 使用 Adam。如果下一轮要求完全按论文正文，则要改为 RMSprop。
- 实现效果：先明确代码遵循哪一个规格，避免 `docs/rl_capa_algo.md` 与论文正文混用造成伪一致。
- 检查点：
  - 更新 README 与配置说明，明确 RL-CAPA 当前 state/optimizer 规格。

## Phase 4: 修正 ImpGTA 预测与 CAPA-style bid

### 4.1 让 prediction success rate 同时影响 inner 与 outer 条件

- 文件：`baselines/gta.py`
- 函数：
  - `_run_gta_environment()`
  - `future_tasks_within_window()`
  - `should_bid_outer_platform_impgta()`
- 修改点：
  - 删除 outer 条件中的 `future_tasks=[]` 固定空列表。
  - 为每个 cooperating platform 构造独立的 predicted future task window。
  - 如果当前 Chengdu environment 没有 partner 自身 pick-up task stream，则需要先在 `env/chengdu.py::build_framework_chengdu_environment()` 中为每个 partner platform 构造 disjoint own-task stream，并写入 environment seed；不能临时用空列表或随机任务兜底。
  - `prediction_success_rate` 应对 inner 和每个 outer platform 的 predicted future task window 都生效。
- 实现效果：ImpGTA 的 inner/outer 条件都受预测窗口和预测成功率影响。
- 检查点：
  - `prediction_success_rate=0.0` 与 `1.0` 的 ImpGTA 决策数量应可观测不同。
  - 对同一 seed 重复运行结果完全一致。

### 4.2 将 ImpGTA cross bid 从 AIM 改为 CAPA/DLAM bid 原则

- 文件：`baselines/gta.py`
- 函数：
  - `_run_gta_environment()`
  - `settle_aim_auction()`
  - `select_available_courier_for_task()`
- 文件：`capa/dapa.py`
- 函数：
  - `compute_fpsa_bid()`
  - `run_dapa()`
- 修改点：
  - BaseGTA 可继续保留 AIM，因为它是 [17] 原始 baseline。
  - ImpGTA 分支中，outer bidding 不再用 `GTABid.dispatch_cost` 和 `settle_aim_auction()`。
  - ImpGTA 的 cross assignment 应调用 CAPA/DLAM bid 逻辑：第一层用 `compute_fpsa_bid()` 选择 platform 内 winner，第二层用 `run_dapa()` 或等价复用 `capa.dapa` 的 RVA 逻辑选择 platform winner 与 payment。
  - 最终 local platform TR 继续用 `compute_local_platform_revenue_for_cross_completion(fare, platform_payment)`。
  - 不要复制 DAPA 公式到 `baselines/gta.py`；应复用 `capa.dapa`，最多只做 legacy courier/task 到 CAPA model 的 adapter。
- 实现效果：ImpGTA 与 CAPA 的 cross bid/payment 原则一致；二者差异保留在“是否使用预测窗口规则代替 CAPA 动态阈值/分流策略”。
- 检查点：
  - 新增测试：同一 parcel、同一 partner courier/platform，ImpGTA cross bid 的 courier payment 和 platform payment 与 CAPA DAPA 输出一致。
  - 新增测试：BaseGTA 仍走 AIM，ImpGTA 走 CAPA/DLAM，二者路径可区分。

### 4.3 让 ImpGTA 的 BPT 保持统一口径

- 文件：`baselines/gta.py`
- 函数：`_run_gta_environment()`
- 修改点：
  - 当前 GTA BPT 已尝试排除 routing/insertion time；ImpGTA 改用 CAPA DAPA 后，需要继续使用同一 timing accumulator，不要把 route planning 或 insertion warmup 重新算进 BPT。
  - 测试 `BPT >= 0` 且不随纯 routing cache warmup 异常膨胀。
- 实现效果：ImpGTA 修正 bid 后仍保持和其它算法一致的 BPT 口径。

## Phase 5: 统一验证与提交顺序

建议提交顺序：

1. `fix(data): read full chengdu order splits`
2. `test(data): cover seeded task-window sampling`
3. `fix(capa): align paper parameters and threshold history`
4. `fix(rl-capa): remove dynamic threshold from rl local stage`
5. `fix(rl-capa): align evaluation bpt accounting`
6. `fix(impgta): apply prediction success to outer decisions`
7. `fix(impgta): reuse capa dlam bid logic`
8. `docs: update experiment parameter documentation`

每个阶段至少运行：

```bash
python3 -m pytest tests/test_capa_config.py tests/test_capa_local.py
python3 -m pytest tests/test_rl_env_smoke.py tests/test_trainer_smoke.py
python3 -m pytest tests/test_metric_alignment.py
```

最终完整 smoke：

```bash
python3 runner.py compare \
  --algorithms capa greedy basegta impgta mra ramcom rl-capa \
  --axis num_parcels \
  --values 50 \
  --data-dir Data \
  --local-couriers 20 \
  --platforms 2 \
  --couriers-per-platform 10 \
  --courier-capacity 50 \
  --service-radius-km 1.0 \
  --batch-size 20 \
  --task-sampling-seed 1 \
  --episodes 2 \
  --output-dir /tmp/chengdu_0425_smoke
```

验收标准：

- 所有算法在同一 canonical seed 下运行，不重建不同环境。
- CR、TR、BPT 均非 NaN，且 CR 在小样本下不应异常为 0。
- ImpGTA 的 prediction success rate 改变时，inner/outer 决策统计可被测试观察到。
- ImpGTA cross payment 与 CAPA/DLAM payment 公式一致。
- RL-CAPA 的 deferred 与 failed-cross parcel 都会进入下一 batch，而不是被静默丢弃。
