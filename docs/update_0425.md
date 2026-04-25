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

### 2.2 将 courier preference、service score 等收益相关参数显式配置化

- 文件：`capa/config.py`
- 修改点：
  - 增加显式默认参数，例如 `DEFAULT_COURIER_ALPHA`、`DEFAULT_COURIER_BETA`、`DEFAULT_COURIER_SERVICE_SCORE`、`DEFAULT_PLATFORM_QUALITY_START`、`DEFAULT_PLATFORM_QUALITY_STEP`。
  - `alpha` 必须作为可配置实验参数保留，因为后续需要 sweep `alpha` 对收益、bid 与平台选择的影响。
  - 默认 `beta` 可由 `1-alpha` 推导，但代码里要明确校验 `alpha + beta == 1` 或提供清晰的 normalize/validation 入口；不能在运行中隐式随机。
- 文件：`env/chengdu.py`
- 函数：
  - `ChengduEnvironment.build()`
  - `build_framework_chengdu_environment()`
  - `legacy_courier_to_capa()`
- 修改点：
  - 为环境构建入口增加 `courier_alpha`、`courier_beta`、`courier_service_score`、`platform_quality_start`、`platform_quality_step` 等显式参数。
  - `GenerateOriginSchedule(..., preference=...)` 不再硬编码 `DEFAULT_COURIER_PREFERENCE`，而是使用命令或 config 传入的 `courier_alpha`。
  - 对 legacy courier 生成后显式写入 `courier.w = courier_alpha`、`courier.c = courier_beta`、`courier.service_score = courier_service_score`，并让 `legacy_courier_to_capa()` 只读取这些显式字段。
  - 平台质量 `f(P)` 相关参数也必须从 config 构造并写入 environment seed，不应只依赖隐藏默认值。
- 文件：
  - `experiments/config.py`
  - `runner.py`
  - `experiments/paper_chengdu.py`
  - `experiments/seeding.py`
- 修改点：
  - 将上述参数加入统一 CLI、experiment config、paper experiment fixed config、canonical seed 序列化。
  - 增加 sweep axis，例如 `courier_alpha`，用于后续实验直接比较不同 `alpha` 设置对 TR/CR/BPT 的影响。
- 实现效果：`alpha`、`beta`、`service_score`、平台质量等都会成为可复现实验参数；同一 canonical seed 下所有算法共享完全相同的 courier/platform 属性。
- 检查点：
  - 更新 `tests/test_capa_config.py`，验证默认参数、`alpha/beta` 校验与 platform quality 构造。
  - 更新 `tests/test_paper_canonical_seed_axes.py`，验证 `courier_alpha` sweep 只改变 courier preference，不改变 parcel 抽样、courier 初始位置、站点等无关环境状态。
  - 检查相同 canonical seed 下 CAPA、Greedy、BaseGTA、ImpGTA、MRA、RamCOM、RL-CAPA 的 courier preference 与 service score 完全一致。

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

### 3.1 增加 RL-CAPA 专用的直接本地匹配入口

- 文件：`env/chengdu.py`
- 新增函数：`run_chengdu_direct_local_matching()`
- 修改点：
  - 输入为 RL 第二阶段选择 `a=0` 的 legacy tasks，而不是 CAMA 生成的 auction pool。
  - 只做本地可行性、容量、deadline、service radius、真实路网插入位置检查。
  - 不调用 `capa.cama.run_cama()`，不计算 CAMA utility，不计算动态阈值，不根据效用筛选。
  - 对每个待本地处理的 parcel，选择一个可行本地 courier 并插入路线；选择准则应是明确、确定、与环境一致的本地执行规则，例如最小增量距离、最早可达时间、再按 courier id 稳定打破平局。
  - 本地不可行的 parcel 不进入 DAPA，也不被丢弃，而是返回 unresolved list，后续进入下一 batch。
- 可复用函数：
  - `legacy_task_to_parcel()`
  - `find_best_local_insertion()`
  - `apply_assignment_to_legacy_courier()`
  - `is_feasible_local_match()` 中的约束检查逻辑，但不能复用 `run_cama()` 的 utility/threshold 筛选。
- 实现效果：RL-CAPA 的 `a=0` 代表“直接进入本地匹配阶段”，而不是“defer”或“低阈值 CAMA”。
- 检查点：
  - 构造一个 utility 低于 CAPA threshold 但本地可行的 parcel：CAPA CAMA 应可把它送入 auction pool；RL `a=0` 应直接本地匹配它。
  - 构造一个本地不可行 parcel：RL `a=0` 后必须进入 backlog，在下一 batch 再决策。

### 3.2 修改 RL-CAPA 第二阶段为全 batch parcel 的 local-vs-cross 决策

- 文件：`rl_capa/env.py`
- 函数：
  - `RLCAPAEnv.run_local_matching()`
  - `RLCAPAEnv.get_stage2_states()`
  - `RLCAPAEnv.apply_cross_decisions()`
- 修改点：
  - 删除训练/评估流程中“先 CAMA、再对 CAMA 剩余包裹做 RL 决策”的语义。
  - `apply_batch_size()` 后，第二阶段状态应针对 `prepared_batch.eligible_tasks` 中的所有 eligible parcel 构建，而不是针对 CAMA leftovers。
  - 将 `apply_cross_decisions()` 重命名或语义调整为 `apply_stage2_decisions()`：输入是 `{parcel_id: 0|1}`，覆盖当前 eligible batch 的全部 parcel。
  - `a=0`：该 parcel 进入 `run_chengdu_direct_local_matching()`；若本地匹配失败，自动进入下一 batch backlog。
  - `a=1`：该 parcel 进入 `run_chengdu_cross_matching()` / DAPA；若跨平台匹配失败，自动进入下一 batch backlog。
  - 第二阶段不包含主动 defer 动作；进入下一 batch 只发生在所选阶段无法承接时。
  - 第二阶段不计算 CAPA utility，也不计算动态阈值；RL policy 自己决定 local 或 cross。
- 文件：`rl_capa/trainer.py`
- 函数：`RLCAPATrainer._collect_step()`
- 修改点：
  - 删除 `local_assignments, unassigned = self.env.run_local_matching()` 这一前置调用。
  - 改为 `batch_parcels = self.env.current_eligible_parcels()` 或等价方法，然后对所有 batch parcels 调用 `pi2`。
  - `num_cross` 统计 `a=1` 数量；`num_local` 统计 `a=0` 数量；cross rate 分母应为当前 eligible batch parcel 数。
- 文件：`rl_capa/evaluate_core.py`
- 函数：`evaluate()`
- 修改点：
  - 与训练流程一致：评估时 `pi2` 对全部 eligible batch parcels 用 `prob > 0.5` 决定 local/cross。
  - 不再先执行 CAMA。
- 实现效果：RL-CAPA 的两个决策点严格是 `batch_size` 与 `cross-or-not`；`a=0` 本地、`a=1` 跨平台，失败则进入下一 batch。
- 检查点：
  - 更新 `tests/test_rl_env_smoke.py`：构造两个 parcel，一个全部 `a=0` 能本地匹配，一个全部 `a=1` 能跨平台匹配，验证路径不同且都进入统一 route 推进。
  - 新增失败回流测试：`a=0` 本地失败和 `a=1` 跨平台失败都进入下一 batch backlog。
  - 新增防回归测试：mock/spy `capa.cama.run_cama()`，RL-CAPA step 不应调用它。

### 3.3 对齐 RL-CAPA BPT 口径

- 文件：`rl_capa/evaluate_core.py`
- 函数：`evaluate()`
- 文件：`rl_capa/env.py`
- 函数：`RLCAPAEnv.apply_stage2_decisions()` 或调整后的 `apply_cross_decisions()`
- 修改点：
  - 不再只统计 `π1/π2` forward inference time。
  - 从 finalized batch report 或 environment timing 中取与 CAPA 一致的 batch assignment processing time。
  - 若项目当前定义要求排除 routing/insertion/movement，则 RL-CAPA 也必须使用相同的 `decision_time_seconds` 累计，不单独使用 policy inference time。
  - 新增直接本地匹配入口后，本地阶段与跨平台阶段都要纳入同一 timing accumulator，避免 RL-CAPA 的 BPT 只包含 policy forward。
- 实现效果：RL-CAPA 的 BPT 与 CAPA、Greedy、GTA、MRA、RamCOM 处在同一评测口径。
- 检查点：
  - 新增测试比较 RL-CAPA eval 的 BPT 与 batch reports 的 timing 聚合一致。

### 3.4 用真实未来数据补齐 RL-CAPA stage-1 预测特征，optimizer 保持 Adam

- 文件：`rl_capa/state_builder.py`
- 函数：
  - `build_stage1_state()`
  - `build_stage2_states()`
- 修改点：
  - stage-1 state 从当前 4 维扩展为论文正文中的 6 维：`(|Γ_t^Loc|, |C_t^Loc|, N_Z^Γ, N_Z^C, |D|, |T|)`。
  - 不实现预测模型；按本轮要求直接用真实未来数据替代预测特征。
  - `N_Z^Γ`：从 `runtime.sorted_tasks` 中统计未来窗口内真实 pick-up parcel 数量，窗口长度作为显式 config 参数，例如 `rl_future_feature_window_seconds`。
  - `N_Z^C`：统计未来窗口内会变为可用的本地 courier 数量，可基于 legacy route 的 ready time 或当前 runtime courier state 推导。
  - `build_stage2_states()` 继续保留 9 维 per-parcel 状态，但输入 parcel 集合改为当前 eligible batch 全量 parcels。
- 文件：`rl_capa/networks.py`
- 类：
  - `BatchSizeActor`
  - `StateValueCritic`
- 修改点：
  - `state_dim` 从 `4` 改为 `6`，并同步 trainer/evaluator 的 normalizer 维度。
- 文件：
  - `rl_capa/config.py`
  - `algorithms/rl_capa_runner.py`
  - `runner.py`
  - `experiments/config.py`
- 修改点：
  - 增加 `rl_future_feature_window_seconds`，用于控制真实未来特征统计窗口。
  - optimizer 仍保持当前 Adam，不改 RMSprop。
- 实现效果：stage-1 state 与论文正文特征对齐，但预测项用真实未来窗口替代；训练 optimizer 继续遵循当前 actor-critic 实现的 Adam。
- 检查点：
  - 更新 `tests/test_trainer_smoke.py` 与 `tests/test_rl_env_smoke.py`，验证 stage-1 state shape 为 `(6,)`。
  - 测试 `rl_future_feature_window_seconds` 改变时 `N_Z^Γ`/`N_Z^C` 可观测变化。
  - 测试 trainer 仍构建 `torch.optim.Adam`，不切换 RMSprop。

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
3. `fix(config): expose courier preference and quality parameters`
4. `fix(capa): align paper parameters and threshold history`
5. `fix(rl-capa): make stage2 choose local or cross for full batch`
6. `fix(rl-capa): add true-future stage1 features and align bpt`
7. `fix(impgta): apply prediction success to outer decisions`
8. `fix(impgta): reuse capa dlam bid logic`
9. `docs: update experiment parameter documentation`

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
  --courier-alpha 0.5 \
  --courier-service-score 0.8 \
  --rl-future-feature-window-seconds 300 \
  --episodes 2 \
  --output-dir /tmp/chengdu_0425_smoke
```

验收标准：

- 所有算法在同一 canonical seed 下运行，不重建不同环境。
- CR、TR、BPT 均非 NaN，且 CR 在小样本下不应异常为 0。
- ImpGTA 的 prediction success rate 改变时，inner/outer 决策统计可被测试观察到。
- ImpGTA cross payment 与 CAPA/DLAM payment 公式一致。
- RL-CAPA 的 `a=0` parcel 直接走本地匹配，`a=1` parcel 直接走跨平台匹配；本地失败与跨平台失败的 parcel 都会进入下一 batch，而不是被静默丢弃。
