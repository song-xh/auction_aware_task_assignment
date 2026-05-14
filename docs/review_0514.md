# Review 2026-05-14 — Robust-500 训练与 Exp-7/Exp-8 评估审查

## 1. RL-CAPA Robust-500 训练: reward 不收敛而 loss 近似收敛的根因

详细分析见 [`docs/rl_capa_robust500_analysis.md`](./rl_capa_robust500_analysis.md). 结论摘要:

- **不是代码 bug**. 梯度流、advantage 归一化、DR 采样 (1500 episodes 内 63 个唯一 `(delay, noise)` 组合)、V2 输入含 `Δ_b` (a₁) 全部按规格工作.
- **"loss 近似收敛" 是表象**:
  - `loss_pi1 → 1e-6`: π1 退化为 deterministic ⇒ `log_prob_1 → log 1 = 0` ⇒ `−log_prob·adv → 0`. 这是退化的副作用, 不代表学习收敛.
  - `loss_v1: 5.5e5 → 2.4e3`: V1 学到 state-mean, 残差 std≈49 是 DR 引入的不可约噪声.
  - `loss_pi2: 23 → 2`: 因 `|adv_2| → 0` (V2 拟合每步奖励) 自然变小.
- **reward 真不收敛** (2094→2046, 均值与方差几乎不变):
  - π1 在 ~ep 500 退化到 `batch=10` (最小批) 并保持. Q1 counterfactual advantage 持续推 π1 朝最高 Q 动作 (DR 下小批受扰动影响小).
  - **π2 logit 卡在 ≈0 整 1500 ep, entropy 永远 = ln 2 ≈ 0.693, 跨平台概率恒为 0.5** (从 ckpt 加载验证: `pi2.probs ∈ [0.43, 0.53]`, `pi2.logit std=0.11`).
  - 机制: `A2 = r_t − V2(s2_agg)`, V2 拟合每步奖励 ⇒ |A2| → 噪声; `entropy_coeff ∈ [0.005, 0.05]` 的熵奖励压过噪声梯度 ⇒ logit 永不离开 0.
- **reward 远低于无 DR 基线**: 对比 `result/rl_capa_run` (无 DR, 5000 ep) returns 2415→3516; Robust-500 returns ≈ 2050 ≈ 58% 干净基线. 部分是 DR 平均下的结构性下降, 部分是策略卡死无法获益.

**改进步骤** (待训练侧重训时执行):

| 步骤 | 改动 | 检查点 |
|---|---|---|
| S1 | `--rl-entropy-start 0.005 --rl-entropy-end 0.0005` | 训练 200 ep 后 `entropy_pi2 < 0.6`, 说明 π2 logit 离开 0 |
| S2 | `--rl-entropy-decay-episodes 500` (更快衰减), `--episodes 3000` | 1000 ep 后 `mean_batch_size ≠ 10.0` (π1 不再死锁) |
| S3 | DR curriculum: 前 500 ep clean, 之后线性引入扰动 | 500 ep 时 returns ≥ 3000 (与无 DR 对齐), 然后看 robust 阶段下降幅度 |
| S4 | 可选: 把当 episode 的 `(delay, noise)` 暴露给 V1/V2 (oracle critic, actor 不见) | `loss_v1` 应能降到 ~50 数量级 |

---

## 2. Exp-7 (deadline_delay) 对 RamCOM 无影响的根因

### 现象

500-parcel 评估:

```
deadline_delay   5  → ramcom TR=895.7 CR=0.266
deadline_delay  10  → ramcom TR=895.7 CR=0.266
deadline_delay  15  → ramcom TR=895.7 CR=0.266
deadline_delay  20  → ramcom TR=895.7 CR=0.266
deadline_delay  30  → ramcom TR=895.7 CR=0.266
deadline_delay  60  → ramcom TR=895.7 CR=0.266
```

逐字节相同. RL-CAPA 在同样轴上变化也非常小 (2355.8→2324.9, 仅降 1.3%).

### 代码审查

`baselines/ramcom.py:318`:

```python
if get_true_deadline(task) < current_time:
    ...  # intake reject
```

**Bug**: 此处 `get_true_deadline` 直接读 `task.d_time`, 忽略 exp8 写入的 `observed_d_time`. 应改为 `get_model_deadline`. 其余基线 (greedy/basegta/impgta/mra/capa) 走 `legacy_task_to_parcel(task)` 路径, 默认 `use_observed_deadline=True`, 因此都能感知 exp8 噪声; 仅 ramcom 例外.

### 但这不是 exp7 (delay) 不动的主因

对 exp7 而言, `apply_processing_delay` 设置 `observed_s_time = true_s + delay`. RamCOM 的 `current_time` 通过 `get_model_release_time(task)` (line 264, 302) 正确读取 `observed_s_time` ⇒ 算法时钟确实推进 delay 秒. 那为什么 TR 完全不变?

**根因 (exp7 设计层面, 非代码 bug)**:

1. **任务 slack ≫ delay 范围**. Chengdu 数据典型 `d_time − s_time` 在数百~数千秒, 而 delay 取 [5, 60] 秒. 算法侧:
   - intake reject 条件 `true_d < current_time = true_s + delay` 几乎从不触发 (slack 远大于 60s).
   - feasibility 走 `legacy_task_to_parcel` 用 model deadline = true deadline (exp7 不改 `observed_d_time`), 仍可路由插入.
2. **均匀 delay 不改变相对顺序**. 所有任务都 +δ ⇒ 任务排序不变, 批次划分不变.
3. **`random.Random(DEFAULT_RAMCOM_RANDOM_SEED)` 固定种子**. 在相同可行集下 `rng.choice` 序列相同 ⇒ 决策完全可复现.
4. **小数据规模 (500 parcels / 10 local couriers)**. 快递员充裕, 不存在因延迟而错过新机会的"机会成本".

综合 (1)+(2)+(3) ⇒ 算法看到的可行集与 rng 序列与 delay=0 case 完全一致 ⇒ TR 逐字节相同.

RL-CAPA 也是同理 (推理时 `dist.sample` 在固定 seed 下相同, π1 已退化为常量 `batch=10`), 但状态特征里的 `recent_timeout_ratio` 等漂移信号在不同 delay 下会有微小差异, 因此 TR 有 1.3% 的微弱下降 — 仍远不及预期的"延迟显著伤 TR".

### 实验逻辑是否有问题

是. 当前 `experiments/deadline_disturbance.py` 的 `apply_processing_delay`:

```python
delay = float(delay_seconds)
for task in tasks:
    setattr(task, "observed_s_time", get_true_release_time(task) + delay)
```

应用相同 delay 给所有任务 ⇒ 仅相当于全局时间偏移. **预期是 (a) delay 大于典型 slack, 或 (b) per-task 抖动**.

### 修改步骤与检查点

| # | 改动 | 文件 | 检查点 |
|---|---|---|---|
| F1 | RamCOM intake reject 改用 model deadline | `baselines/ramcom.py:318` 把 `get_true_deadline(task)` → `get_model_deadline(task)`; 同步 import | 单测 / 重跑 exp8 看 TR 应随 \|noise\| 增加而下降 |
| F2 | Trace 字段补加 model deadline 便于 debug | `baselines/ramcom.py:289` 增加 `"observed_deadline": float(get_model_deadline(task))` | trace JSON 可见两个字段 |
| F3 | Exp-7 axis 重新设计: delay 上限提升到 task slack 量级 (例如 0/60/120/240/480 s) | `experiments/deadline_disturbance.py:DEADLINE_DELAY_VALUES` | delay=480 时所有算法 CR 应明显下降 |
| F4 | 可选: 引入 per-task 抖动而非均匀 delay (例如 `delay_seconds * U[0.5, 1.5]`) | `experiments/deadline_disturbance.py:apply_processing_delay` 增加可选 `jitter_rng` 参数 | 同一 delay 下 ramcom 可见非平凡 TR 波动 |
| F5 | 检查 RL-CAPA `--rl-domain-randomize-delays` / `--rl-domain-randomize-noises` 范围与 eval 轴对齐. 训练用 0-60s, eval 也应在此范围以下才公平 | `runner.py` arg defaults | DR 训练分布与 eval 轴 overlap |

### 验证检查表

- [ ] F1 后, `ramcom` 在 exp8 的 TR/CR 随 \|noise\| 单调变化 (负噪声: 算法过度拒绝 → TR↓; 正噪声: 算法过度乐观 → 真实 timeout 增加 → CR↓)
- [ ] F3 后, `ramcom` 在 exp7 的 TR 在 delay≥240 时显著下降 (>5%)
- [ ] RL-CAPA 在 exp7/exp8 的 TR 下降幅度小于 RamCOM (验证训练自适应优势)
- [ ] 如果 RL-CAPA 不优于 RamCOM, 回到 §1 改进步骤继续训练

---

## 3. 包裹数量太少导致的副作用

是, 但不是唯一原因. 500 parcels / 10 couriers 设置:

- 快递员充裕, 单条路由 slack 大 ⇒ 即便算法略错也能补救.
- 单 episode reward variance 主要来自数据的固定结构, 不是来自策略选择.
- DR 噪声相对于 episode reward (2050) 占比小, 信号比劣化.

建议评估时使用与 paper 同等规模 (例如 5000 parcels / 1000 couriers) 才能凸显算法差异. 当前 500-parcel 评估只能算 "smoke test".

---

## 4. 当前 Eval 状态

已终止. 仅 exp7 完成 6 点 (见 `outputs/plots/rl_capa_robust_500/eval/exp7/point_*/summary.json`). exp8 未启动. 待 §2 的 F1 修复后重新跑两轴评估.
