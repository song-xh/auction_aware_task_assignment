# RL-CAPA 0419 修复计划

## 目标

以 [docs/rl_capa_algo.md](/root/code/auction_aware_task_assignment/docs/rl_capa_algo.md) 为唯一算法规范，对当前 RL 代码进行一次结构化修复规划。

这次规划的目标不是继续沿用旧的 `DDQN` 方案，也不是把两套 RL 实现并存，而是明确：

1. **保留 `src/rl/` 这套 actor-critic 实现作为唯一的 RL-CAPA 主线**
2. **让 RL 环境严格复用当前主体实验环境**，尤其是 [env/chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py) 的初始化、batch 推进、backlog、终局清理与评估语义
3. **把统一 `runner.py / experiments / README` 接到修正后的 actor-critic 实现**
4. **在不改变实验思路的前提下修复结构、指标与参数配置问题**

本文件只给出问题、原因、修复思路、文件级修改顺序和测试点，不修改代码。

---

## 一、当前代码现状与主要问题

### 1. RL 实现当前分裂成两套，且统一入口走错了主线

当前仓库里有两套 RL 代码：

- 新的 actor-critic 实现：`src/rl/`
- 旧的 DDQN 实现：`rl_capa/`

但统一实验入口 [algorithms/rl_capa_runner.py](/root/code/auction_aware_task_assignment/algorithms/rl_capa_runner.py) 仍然导入并执行：

- [rl_capa/train.py](/root/code/auction_aware_task_assignment/rl_capa/train.py)
- [rl_capa/evaluate.py](/root/code/auction_aware_task_assignment/rl_capa/evaluate.py)

而不是 `src/rl/*`。

这与 [docs/rl_capa_algo.md](/root/code/auction_aware_task_assignment/docs/rl_capa_algo.md) 的要求冲突，因为该文档明确规定：

- 算法应为 **two-stage hierarchical actor-critic**
- 文件结构应位于 `src/rl/`
- 旧版 DDQN 已废弃

因此第一优先级不是“继续微调现有 runner”，而是：

- **统一 RL 主线**
- **移除“旧 DDQN 仍在正式入口里执行”的状态**

### 2. `src/rl/env.py` 没有严格对齐主体环境主流程

当前 `src/rl/env.py` 虽然调用了：

- `run_cama`
- `run_dapa`
- `apply_assignment_to_legacy_courier`
- `legacy_*` 转换器

但它没有复用主体环境 [env/chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py) 的真实 batch 主流程，而是自己重写了一套简化版逻辑：

- 自己维护 `self._tasks / self._next_task_index / self._deferred_tasks`
- 自己在 `apply_batch_size()` 里做时间推进和任务累积
- 自己在 `is_done()` 里定义 episode 结束

这会导致与正式 CAPA 主流程不一致，主要体现在：

1. **没有复用 `bucketize_legacy_tasks_by_batch()`**
2. **没有复用 `eligible / expired / backlog` 分流**
3. **没有复用 `partition_terminal_backlog()`**
4. **没有复用 `PersistentDirectedDistanceCache / InsertionCache / snapshot cache`**
5. **没有复用 `BatchReport / delivered / unresolved` 语义**
6. **episode 的 done 条件只是“没有 future task 且没有 deferred task”**
7. **评估时虽然调用 `drain_routes()`，但训练阶段的 step 语义与主流程已偏离**

这意味着当前 `src/rl/env.py` 只是“看起来复用了 CAPA 模块”，但**没有真正嵌回主体实验环境**。

### 3. `src/rl` 的结构方向对了，但仍未完全按规范收口

[docs/rl_capa_algo.md](/root/code/auction_aware_task_assignment/docs/rl_capa_algo.md) 要求：

- `src/rl/networks.py`
- `src/rl/state_builder.py`
- `src/rl/env.py`
- `src/rl/trainer.py`
- `src/rl/evaluate.py`
- `src/rl/utils.py`
- `src/rl/visualize.py`

当前 `src/rl/` 已有：

- [src/rl/networks.py](/root/code/auction_aware_task_assignment/src/rl/networks.py)
- [src/rl/state_builder.py](/root/code/auction_aware_task_assignment/src/rl/state_builder.py)
- [src/rl/env.py](/root/code/auction_aware_task_assignment/src/rl/env.py)
- [src/rl/trainer.py](/root/code/auction_aware_task_assignment/src/rl/trainer.py)
- [src/rl/evaluate.py](/root/code/auction_aware_task_assignment/src/rl/evaluate.py)
- [src/rl/visualize.py](/root/code/auction_aware_task_assignment/src/rl/visualize.py)

缺失或偏差：

1. `utils.py` 不存在，折扣回报和部分归一化辅助逻辑散落在 `trainer.py` / `state_builder.py`
2. `env.py` 自己重复实现了 stage-1 / stage-2 state 构建，而没有明确以 `state_builder.py` 为单一来源
3. 训练与评估命令尚未接入正式 runner / experiments / README

### 4. GPU、参数配置、实验配置链路未闭环

当前 `src/rl/trainer.py` 默认：

- `device="cpu"`

没有：

- 自动 `cuda if available else cpu`
- 从统一 experiment config 显式读取 device
- 在 README 中给出正式训练/评估命令

同时，[experiments/config.py](/root/code/auction_aware_task_assignment/experiments/config.py) 中没有正式 RL 参数字段，目前 runner 只有临时 CLI 参数：

- `--min-batch-size`
- `--max-batch-size`
- `--step-seconds`
- `--episodes`

而 actor-critic 主线真正需要的训练参数还包括：

- `lr_actor`
- `lr_critic`
- `discount_factor`
- `entropy_coeff`
- `max_grad_norm`
- `device`
- 可选 `normalize_states`

所以现在的问题不是“参数值不对”，而是**参数没有正式进入统一实验配置层**。

### 5. BPT、训练/评估流程、实验入口没有完全对齐主体指标口径

[docs/rl_capa_algo.md](/root/code/auction_aware_task_assignment/docs/rl_capa_algo.md) 要求评估输出：

- `TR`
- `CR`
- `BPT`

并且与 CAPA 对齐。

当前 `src/rl/evaluate.py` 的 `BPT` 是：

- 从 `apply_batch_size()`
- 到 `run_local_matching()`
- 再到 `apply_cross_decisions()`

整段 wall-clock 都记进去。

这与当前主体实验中“BPT 只统计决策时间、不把 movement / shortest-path / 插入搜索完整算入”的口径并不一致。  
因此即使 RL 训练逻辑本身正确，**评估指标也还不能直接与主体实验结果比较**。

---

## 二、修复原则

### 原则 1：以 `docs/rl_capa_algo.md` 为准，不再沿用论文旧 DDQN

这次修复必须明确：

- **保留 `src/rl/`**
- **淘汰 `rl_capa/` 作为正式执行主线**

旧 `rl_capa/` 可以在过渡阶段保留兼容壳，但不能继续作为统一 runner 的真正实现。

### 原则 2：RL 不能复制主流程，只能嵌入主流程

RL 不是重新写一个“类似 Chengdu 环境”的环境，而是：

- 在主体 batch 语义下插入两个决策点
  - batch size
  - cross-or-not

因此修复方向不应是“继续扩展 `src/rl/env.py` 自己的局部状态机”，而应是：

- **从 [env/chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py) 提炼 RL 可复用的 batch-step 运行骨架**
- 再让 `src/rl/env.py` 成为这个骨架的策略层封装

### 原则 3：实验、配置、命令、README 必须只有一条可信链路

修复完成后必须保证：

1. `runner.py --algorithm rl-capa` 跑的就是 `src/rl/`
2. `experiments/*` 可以透传 RL 参数
3. README 写的是实际可运行、与当前代码一致的命令
4. `docs/rl_capa_algo.md` 的 actor-critic 结构与正式实验入口一致

---

## 三、总体修复方案

## Phase A：统一 RL 主线，停止正式入口调用旧 DDQN

### 目标

让 `src/rl/` 成为唯一正式 RL-CAPA 实现主线，旧 `rl_capa/` 退出正式执行链路。

### 涉及文件

- [algorithms/rl_capa_runner.py](/root/code/auction_aware_task_assignment/algorithms/rl_capa_runner.py)
- [runner.py](/root/code/auction_aware_task_assignment/runner.py)
- [experiments/compare.py](/root/code/auction_aware_task_assignment/experiments/compare.py)
- [experiments/sweep.py](/root/code/auction_aware_task_assignment/experiments/sweep.py)
- `src/rl/*`
- `rl_capa/*`

### 修改思路

1. 先把 [algorithms/rl_capa_runner.py](/root/code/auction_aware_task_assignment/algorithms/rl_capa_runner.py) 从旧 `rl_capa.train/evaluate` 切到新的：
   - `src.rl.env`
   - `src.rl.trainer`
   - `src.rl.evaluate`
2. 明确 `rl_capa/` 旧包的角色：
   - 要么删除
   - 要么仅作为临时兼容 re-export 层
3. 所有正式命令、实验入口和 README 都只引用一套 RL 实现

### 风险

- 切换 runner 后，当前所有 RL 相关 smoke/test 可能一起失效
- 需要先修环境主流程对齐问题，否则切换到 `src/rl` 只会把问题暴露出来

### 测试点

1. `runner.py run --algorithm rl-capa ...` 实际进入 `src/rl`
2. `compare/sweep/suite` 中的 `rl-capa` 不再调用旧 `rl_capa/*`
3. 旧 `rl_capa/` 不再是正式执行主线

---

## Phase B：把 RL 环境嵌回主体 Chengdu batch 主流程

### 目标

让 RL 环境与 [env/chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py) 的正式 CAPA 流程严格对齐：

- 相同初始化
- 相同 batch 边界
- 相同 movement
- 相同 backlog / expired / terminal 剪枝
- 相同本地匹配与跨平台拍卖逻辑

### 当前问题

当前 [src/rl/env.py](/root/code/auction_aware_task_assignment/src/rl/env.py) 的 `apply_batch_size()` / `run_local_matching()` / `apply_cross_decisions()` 虽然复用了 `run_cama` 和 `run_dapa`，但没有复用主流程的核心中间语义。

### 修复方向

不要继续在 `src/rl/env.py` 里手写完整 batch 管理逻辑。  
应该把 [env/chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py) 中 `run_time_stepped_chengdu_batches()` 的 monolithic 逻辑拆成几个可复用阶段函数。

### 建议提炼的共享函数

在 [env/chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py) 内新增或抽出：

1. `advance_to_batch_end(...)`
   - 负责 movement 和时间推进
2. `collect_batch_input_tasks(...)`
   - 负责 `bucket + backlog`
   - 产出 `input / eligible / expired`
3. `build_local_matching_runtime(...)`
   - 负责 local snapshots / timing wrapper / insertion cache / batch distance
4. `run_local_stage(...)`
   - 统一调用 `run_cama`
   - 统一写回 local assignments
5. `build_partner_matching_runtime(...)`
   - 负责 partner snapshots
6. `run_cross_stage(...)`
   - 统一调用 `run_dapa`
   - 统一写回 cross assignments
7. `finalize_backlog(...)`
   - 负责 retry backlog 与 terminal backlog 剪枝
8. `build_batch_report(...)`
   - 负责生成与 CAPA 一致的 report / delivered 统计

### `src/rl/env.py` 应如何改

改造后的 `src/rl/env.py` 不应再自己维护一套“平行主流程”，而应变成：

- 通过共享 helper 获取当前 batch 上下文
- 在“固定进入 DAPA”之前插入第二阶段 actor 决策
- 对 `a=0` parcel 放入 defer
- 对 `a=1` parcel 调共享 cross stage
- 最终用共享 finalize/report 逻辑收尾

### 这样做的直接收益

1. RL 与 CAPA 在真实环境语义上严格一致
2. 之前在 CAPA 主流程上做的：
   - persistent distance cache
   - insertion cache
   - geo 预筛
   - terminal backlog 剪枝  
   都可以直接被 RL 环境继承
3. 训练与评估终于能和主体实验结果对齐

### 测试点

1. 在固定策略下，RL 环境一步的 local / cross / deferred 语义与主体环境一致
2. `a=1 for all` 时，RL 环境行为应退化到“CAMA 后全部走 DAPA”的 CAPA 语义
3. `a=0 for all` 时，未分配 parcel 必须进入下一轮 backlog，而不是消失
4. expired / terminal backlog 必须与主体环境一致

---

## Phase C：收口 actor-critic 结构，让 `src/rl/` 完全遵从算法规范

### 目标

让 `src/rl/` 完整符合 [docs/rl_capa_algo.md](/root/code/auction_aware_task_assignment/docs/rl_capa_algo.md) 的结构与分工。

### 当前问题

1. `state_builder.py` 存在，但 `env.py` 仍然重复构建状态
2. 缺少 `utils.py`
3. 某些训练逻辑、归一化和回报辅助函数未收口

### 修改思路

#### C1. 让 `state_builder.py` 成为唯一状态构建入口

涉及文件：

- [src/rl/state_builder.py](/root/code/auction_aware_task_assignment/src/rl/state_builder.py)
- [src/rl/env.py](/root/code/auction_aware_task_assignment/src/rl/env.py)

操作：

1. 保留 `build_stage1_state()`
2. 保留 `build_stage2_states()`
3. 保留 `aggregate_stage2_states()`
4. 把 [src/rl/env.py](/root/code/auction_aware_task_assignment/src/rl/env.py) 里重复写的 `get_stage1_state()` / `get_stage2_states()` 改为显式调用 `state_builder.py`

#### C2. 新增 `src/rl/utils.py`

涉及文件：

- Create: `src/rl/utils.py`
- Modify: `src/rl/trainer.py`
- Modify: `src/rl/evaluate.py`

操作：

1. 把 discounted return 计算从 `trainer.py` 挪到 `utils.py`
2. 把 device 选择、tensor helper、可选归一化辅助也收口到 `utils.py`
3. 让 `trainer.py / evaluate.py` 更清晰，只负责训练与评估流程

#### C3. 保持网络与优势定义不变

当前 [src/rl/networks.py](/root/code/auction_aware_task_assignment/src/rl/networks.py) 和 [src/rl/trainer.py](/root/code/auction_aware_task_assignment/src/rl/trainer.py) 的大方向是对的：

- 4 网络
- 4 optimizer
- `A1 = V2 - V1`
- `A2 = R_hat - V2`
- actor loss 与 critic loss 分开反传

这一部分应尽量少改，只修与环境对齐和配置接入有关的问题。

### 测试点

1. `src/rl/env.py` 不再手写状态公式
2. `trainer.py` 中回报计算走 `utils.py`
3. `pi1/pi2/V1/V2` 维度与 `docs/rl_capa_algo.md` 一致

---

## Phase D：把 RL 参数正式并入统一配置层

### 目标

让 RL 参数不再只靠临时 CLI 透传，而是正式存在于实验配置层。

### 涉及文件

- [experiments/config.py](/root/code/auction_aware_task_assignment/experiments/config.py)
- [runner.py](/root/code/auction_aware_task_assignment/runner.py)
- [experiments/compare.py](/root/code/auction_aware_task_assignment/experiments/compare.py)
- [experiments/sweep.py](/root/code/auction_aware_task_assignment/experiments/sweep.py)
- [README.md](/root/code/auction_aware_task_assignment/README.md)

### 修改思路

在 `ExperimentConfig.extra` 的“弱透传”之外，新增正式 RL 字段，例如：

- `rl_min_batch_size`
- `rl_max_batch_size`
- `rl_step_seconds`
- `rl_episodes`
- `rl_lr_actor`
- `rl_lr_critic`
- `rl_discount_factor`
- `rl_entropy_coeff`
- `rl_max_grad_norm`
- `rl_device`

然后：

1. `runner.py` CLI 显式支持这些参数
2. `compare/sweep` 可以透传这些参数给 `rl-capa`
3. 统一 formal experiment 命令有正式参数来源

### 关于 GPU

当前设计建议：

1. 默认 `device="auto"`
2. `auto` 时采用：
   - `cuda` if available
   - else `cpu`
3. 把最终选择的 device 写入 training summary

这一步不意味着必须有 GPU，只是让训练设备选择可配置、可记录、可复现。

### 测试点

1. `runner.py --algorithm rl-capa` 能接受并解析正式 RL 参数
2. 训练 summary 中记录最终 device
3. CPU / CUDA 两种路径至少在设备选择上逻辑正确

---

## Phase E：修正评估口径，使 RL 与 CAPA 正式可比

### 目标

让 RL 评估阶段的：

- `TR`
- `CR`
- `BPT`

与主体实验口径一致。

### 当前问题

[src/rl/evaluate.py](/root/code/auction_aware_task_assignment/src/rl/evaluate.py) 当前把整段 step wall-clock 都算入 `BPT`，这与当前 CAPA 实验的 BPT 口径不一致。

### 修改思路

1. 明确 `BPT` 在 RL 中只统计：
   - `pi1` 推理时间
   - `pi2` 推理时间
   - 必要的轻量决策整理时间
2. 不把：
   - movement
   - shortest-path
   - insertion search
   - route drain
   完整并入 RL 的 `BPT`
3. 与当前 CAPA / baseline 已采用的 BPT 口径保持一致

### `CR` 的注意点

评估时不能只看 accepted assignments，还要与主体环境 delivered 语义一致。  
如果当前主口径以 accepted 作为 completion，就保持一致；如果当前主口径要求 `drain_routes()` 后按 delivered 算，则 RL 也必须同样处理。

### 测试点

1. RL 评估输出字段与 CAPA experiment summary 对齐
2. `TR/CR/BPT` 键名与正式 compare/sweep 兼容
3. `BPT` 不再把整个环境推进整段时间全部吞进去

---

## Phase F：统一 README、正式命令与实验入口

### 目标

在 RL 逻辑真的跑通并接入正式实验链路之后，再写 README。  
在此之前，不允许把不可运行或走错主线的命令写进 README。

### 涉及文件

- [README.md](/root/code/auction_aware_task_assignment/README.md)
- [runner.py](/root/code/auction_aware_task_assignment/runner.py)
- 可能新增：
  - `scripts/train_rl_capa.py`
  - `scripts/evaluate_rl_capa.py`
  或保持统一 `runner.py` 风格

### 建议命令链

修复完成后应形成唯一可信命令，例如：

1. 训练：
   - `python3 runner.py run --algorithm rl-capa ... --episodes ...`
2. 评估：
   - 训练后自动输出 eval summary
   - 或单独脚本/子命令
3. 论文正式实验：
   - 以当前 Chengdu 统一环境参数为准
   - 与 `Exp-1 ~ Exp-6` 兼容

### 测试点

1. README 中的 RL 命令可真实执行
2. 输出目录中有：
   - training summary
   - checkpoint
   - eval summary
   - 可视化曲线
3. 命令不再引用旧 `rl_capa/` DDQN 路径

---

## 四、文件级修改顺序建议

建议按下面顺序实施，避免一次性大改导致无法验证。

### Step 1：先统一主线

修改：

- [algorithms/rl_capa_runner.py](/root/code/auction_aware_task_assignment/algorithms/rl_capa_runner.py)
- [runner.py](/root/code/auction_aware_task_assignment/runner.py)

目标：

- 正式入口不再跑旧 DDQN
- 明确 `src/rl/` 是唯一 RL 主线

### Step 2：抽取主体环境共享 batch helper

修改：

- [env/chengdu.py](/root/code/auction_aware_task_assignment/env/chengdu.py)

目标：

- 把 monolithic `run_time_stepped_chengdu_batches()` 拆出 RL 可复用的共享步骤

### Step 3：重写 `src/rl/env.py` 的 batch 驱动

修改：

- [src/rl/env.py](/root/code/auction_aware_task_assignment/src/rl/env.py)
- [src/rl/state_builder.py](/root/code/auction_aware_task_assignment/src/rl/state_builder.py)

目标：

- RL 环境严格走主体 batch/backlog 逻辑
- 只在两个决策点插入 actor 决策

### Step 4：清理 actor-critic 结构

修改：

- [src/rl/trainer.py](/root/code/auction_aware_task_assignment/src/rl/trainer.py)
- Create: `src/rl/utils.py`
- [src/rl/evaluate.py](/root/code/auction_aware_task_assignment/src/rl/evaluate.py)
- [src/rl/visualize.py](/root/code/auction_aware_task_assignment/src/rl/visualize.py)

目标：

- 保持 actor-critic 训练逻辑
- 修正评估和工具组织

### Step 5：接 experiment config 和 README

修改：

- [experiments/config.py](/root/code/auction_aware_task_assignment/experiments/config.py)
- [runner.py](/root/code/auction_aware_task_assignment/runner.py)
- [experiments/compare.py](/root/code/auction_aware_task_assignment/experiments/compare.py)
- [experiments/sweep.py](/root/code/auction_aware_task_assignment/experiments/sweep.py)
- [README.md](/root/code/auction_aware_task_assignment/README.md)

目标：

- 完成统一命令链和正式参数配置

### Step 6：淘汰或降级旧 `rl_capa/`

修改：

- `rl_capa/*`

目标：

- 不再让仓库中存在两条正式 RL 主线
- 若保留，也只能是兼容 re-export，不得继续作为正式实验入口

---

## 五、测试矩阵

本轮修复必须补一组分层验证，而不是只跑一个大的 smoke。

### A. 结构与导入测试

目标：

- `runner.py` 的 `rl-capa` 实际进入 `src/rl`
- 旧 `rl_capa` 不再被正式调用

建议测试：

- `tests/test_rl_runner_entrypoint.py`

检查：

1. `build_algorithm_runner("rl-capa")` 的执行路径
2. `summary.json` 中的训练/评估输出来源

### B. 环境一致性测试

目标：

- RL batch 推进与 `env/chengdu.py` 主流程一致

建议测试：

- `tests/test_rl_env_alignment.py`

检查：

1. 相同 seed 下，固定策略的 RL 环境与 CAPA 主流程在：
   - batch 时间边界
   - eligible / expired
   - backlog
   - defer
   上一致
2. `a=1 all` 时与“全部进入 DAPA”的 CAPA 语义一致
3. `a=0 all` 时 backlog 留存正确

### C. 状态与动作测试

目标：

- `S_b / S_m / A_b / A_m` 与文档一致

建议测试：

- `tests/test_rl_states_and_actions.py`

检查：

1. `s1.shape == (4,)`
2. `s2.shape == (9,)`
3. `Δb` 的来源正确
4. `cross bid average` 滑动窗口更新正确

### D. 训练循环测试

目标：

- actor-critic 四网络更新逻辑正确

建议测试：

- `tests/test_rl_actor_critic_training.py`

检查：

1. `A1 = V2 - V1`
2. `A2 = R_hat - V2`
3. advantage 用于 actor 时已 detach
4. 4 个 optimizer 独立工作
5. loss 和 reward 不是常数

### E. 评估口径测试

目标：

- `TR / CR / BPT` 与主体实验一致

建议测试：

- `tests/test_rl_evaluate_metrics.py`

检查：

1. `TR` 统计口径一致
2. `CR` 统计口径一致
3. `BPT` 不错误吞并 movement 和整段路由开销

### F. 小规模端到端 smoke

目标：

- 证明整条 RL 命令链可运行

建议测试：

- `tests/test_rl_pipeline_smoke.py`

检查：

1. 训练若干 episode 成功
2. checkpoint 成功写出
3. evaluate 成功写出
4. visualize 成功输出训练曲线

---

## 六、提交策略

这轮后续实现建议按下面粒度提交：

1. `refactor(rl): route unified runner to actor-critic src/rl pipeline`
2. `refactor(env): extract reusable Chengdu batch helpers for rl-capa`
3. `feat(rl/env): align actor-critic environment with unified Chengdu batch flow`
4. `refactor(rl): centralize actor-critic utilities and state builders`
5. `fix(rl/eval): align rl-capa metrics and bpt accounting with capa`
6. `config(rl): add formal rl-capa experiment parameters to experiment config`
7. `docs(readme): document actor-critic rl-capa commands and parameters`

---

## 七、本次规划结论

当前仓库中，真正需要修复的不是“某一个训练细节”，而是三件根问题：

1. **正式入口走错了 RL 主线**
2. **actor-critic 环境没有对齐主体 Chengdu batch/backlog 主流程**
3. **配置、指标、命令和 README 没有形成一条可信执行链**

因此后续实现必须优先做：

- 统一 RL 主线
- 主流程对齐
- 参数与评估链路闭环

在这三点完成之前，不应把 `src/rl/` 当作“已经通过审查的正式 RL-CAPA 实现”。
