# RL-CAPA Ablation 反常分析（rl-capa < rl-capa-stage2）

日期：2026-05-07  
数据：`outputs/plots/rl_capa_ablation_CD/`（1800 episodes）  
本文档结合 `rl_capa/` 代码、`docs/rl_capa_algo.md` 规范、论文（Section III-D / 公式 5、8–14）与训练日志，定位 rl-capa 反而劣于 stage2 的根因，并给出修复路径。

---

## 1. 实验事实

| 变体 | 末 100 ep mean reward | mean_batch_size 末 100 | entropy_pi1 末 100 | 末段每 ep 步数 |
|------|-----------------------|------------------------|--------------------|----------------|
| rl-capa | **1835.3** | **60.0**（崩塌单点） | 0.003 | 52–64 |
| rl-capa-stage1 | 1490.5 | 29.6 | 1.673 | 125–139 |
| rl-capa-stage2 | **1910.4**（最优） | 30（固定） | – | 103 |

观察到的现象：
1. `rl-capa` 的 π1 在训练 ~500 episode 后完全坍塌到 a=60s（动作分布从均匀过渡到 100% 选 60）。
2. 末期每 episode 仅 ~52 步（stage2 对照 ~103 步、stage1 ~135 步）。
3. `rl-capa` 末期总收益反而比 stage2（fixed batch=30s）少 ~75 单位，相对差距 ≈ 4%。
4. 配置中 CLI 写的是 `--rl-batch-actions 10 15 20 25 30`，但实际记录的动作集合是 `{10,15,20,25,30,60}`（6 个动作），见 §6.0。

⇒ π1 学到了「永远选最大批量」，但这恰恰**不是**真正最优的策略；同时 π2 因此只在 Δb=60 的分布下被训练，与 stage2 在 Δb=30 上的训练分布并不可比。

---

## 2. 核心结论（一句话）

**γ<1 的折扣回报与「批量越大、回合步数越少」的结构性耦合，让 V2−V1 系统性地偏向更大的 batch；π1 因此快速坍塌到最大批量，并把 π2 的训练分布锁死在一个并非全局最优的 Δb 上。**

stage1 的注释里其实已经识别到了这一类风险并以 γ=1 规避，但 `RLCAPATrainer` 仍按 spec/CLI 用 γ=0.95——这是同一陷阱在主算法上的复发。

---

## 3. 根因分解

### 3.1 γ<1 + 步数与批量负相关 ⇒ V2 系统性偏置 ★★★（首要）

设一个 episode 的真实总收益为 R（与 batch_size 几乎无关，因为最终都要消化完同一批 parcel），平均每步收益 r̄ = R/T，T 与批量呈反比。`compute_discounted_returns` 给出的折扣初始回报：

```
R̂_0 = Σ_{t=0..T-1} γ^t · r̄  =  (R/T) · (1−γ^T)/(1−γ)
```

代入 γ=0.95、R≈1900：
- T=52 (batch=60s): R̂_0 ≈ 36.5 · 18.46 ≈ **674**
- T=103 (batch=30s): R̂_0 ≈ 18.4 · 19.95 ≈ **367**
- T=135 (batch=20s): R̂_0 ≈ 14.1 · 19.95 ≈ **281**

V1、V2 的回归目标都是 R̂_t；既然「相同 R 但 T 更小」可让 R̂_0 翻倍，**V2(s2_agg|Δb=60) 在监督信号上就被天然抬高一倍**。`A1 = V2 − V1` 始终给 a1=60 一个正向 advantage，即使该选择并未带来真实收益增长。

stage1_trainer.py 第 132–145 行已用注释把 γ=1 的修正写进去，可惜方向也有点写反（实际是 γ<1 偏向更"少"步数=更大批量，注释里说"smaller batch ⇒ 更多步⇒ 更大 sum"是反过来），但**结论"必须用 γ=1"是对的**。`RLCAPATrainer` 没继承这个修正——这是现状最大裂缝。

### 3.2 V1 与 V2 共享同一回归目标 ⇒ A1 在收敛后塌缩为 0 ★★

按规范：
```
L_V1 = (V1(s1) − R̂_t)²
L_V2 = (V2(s2_agg) − R̂_t)²
```

两个 critic 拟合相同的标量 R̂_t，区别只在输入。π1 一旦坍塌到确定动作 a*，s2_agg 的 Δb 维度就退化为常量，V1 和 V2 在功能上变成对同一回报的两次拟合，于是 `A1 = V2 − V1 → 噪声`，π1 失去任何梯度信号。日志中 `loss_pi1 末100=−0.0000`、`entropy_pi1=0.003` 正是这种"梯度死亡"。

注意：如果 §3.1 的 γ 偏置先把 π1 推到 a=60，§3.2 接着把 π1 锁住，使其再也回不来。

### 3.3 entropy bonus 太弱，π1 早期即坍塌 ★★

`entropy_coeff=0.03`、动作集 6 维。π1 的最大熵约 ln 6 ≈ 1.79，但 `entropy_pi1` 在 ~episode 500 内就跌到 < 0.01，说明 entropy 项远不足以维持探索。一旦 π1 收敛到单点，π2 的训练分布（Δb 维度）随之冻结，整个层级丢失对其他 batch 的 counterfactual。

### 3.4 advantage 在每 episode 内 z-score 归一化，会把"相同 sign"的信号拉平 ★

`_normalize_advantages` 对单 episode 内 advantage 减均值除标准差。当 π1 几乎只采样一种动作时，A1 序列方差→0，归一化分支返回全零（`std<=epsilon → zeros_like`），即使原始 V2−V1 偏差仍存在。早期阶段 advantage 偏正会被减去整体均值，原本"对最大批量"的统一正向信号反而被剥离——但因为 §3.1 在「跨 episode」累积上仍偏向 a=60 的 V2（监督目标更高），**π1 仍倾向坍塌**，只是过程更曲折。简言之归一化把信号"洗成 0"，无法反向纠错 §3.1 的偏置。

### 3.5 π2 的训练分布被 π1 锁死 ⇒ stage2 反而在更稳的分布上学得更好 ★★

stage2 训练时 Δb≡30、103 步/ep，π2 接收的 s2 分布稳定。完整 RL-CAPA 中 π2 在前期看到 [10..60] 全谱，500 ep 后突然全部变成 60。这种 covariate shift 会损坏 π2 的训练信号；末期 π2 在 Δb=60 上的有效样本量远少于 stage2 在 Δb=30 上的样本量（步数少一半），即便没有 §3.1 偏置，π2 也学不过 stage2。

### 3.6 stage1（γ=1）依然较弱：不是 π1 的问题，而是 stage1 走的是 `apply_capa_batch` 全 CAMA 路径 ★

stage1 调用 `RLCAPAEnv.apply_capa_batch`（CAMA 阈值 + 全 ΔΓ → DAPA），而 stage2/RL-CAPA 都用 `apply_stage2_decisions`（按 π2 决策直接 KM 或 DAPA）。
- stage1 reward 1490.5 < stage2 1910.4，说明**π2 替换 CAMA 阈值机制本身就是个收益增益**（π2 比 ω·avg-utility 阈值更好）。
- 这同时说明：在本环境下 π2 才是收益主贡献者，而 π1 的边际收益本就不大。π1 一旦受偏置干扰，整体净效应可能为负。

### 3.7 V2 输入与规范的微小不一致（次要）

`networks.ConditionalValueCritic` 输入是 9 维 s2_agg，未把 a_t^(1) 做单独 one-hot 拼接。spec §7.4 允许两种实现，但当前实现下 V2 完全依赖 s2_agg 中的 Δb 维度区分批量；该维度与其他 8 维一起被 RunningNormalizer 中心化，到归一化后 Δb 信号可能被淹没——这放大了 §3.2 的塌缩问题（V2 难以真正区分不同 a1）。

### 3.8 论文公式本身有歧义点（论文层面）

- 论文 Eq. 8：`R_t = Rev_S^t(...)` 仅说"两阶段共用同一奖励"，未规定折扣方案。配合 Eq. 13–14 的 R̂_t（"empirical discounted return"）即落入 §3.1 陷阱。
- 论文未声明 episode 是否定长（"is_done=所有 parcel 处理完毕"），导致折扣放大了"批量−步数"的耦合。
- 论文 Section III-D 把 V1、V2 都写成"拟合 R̂_t"，结构上必然出现 §3.2 塌缩。规范层应该让 V1=E_a[Q(s,a)]、V2=Q(s,a) 才是真正的"coarse-to-fine"。

---

## 4. 修复路线

按"必改 → 强烈建议 → 可选"分层。

### 4.1 必改（P0）

1. **取消折扣 / 改用每步标准化奖励**（针对 §3.1）  
   - 方案 A（最稳）：`RLCAPATrainer` 默认 γ=1，episode 是真正终止状态；与 stage1 一致。  
   - 方案 B（保留 γ）：每步奖励改为"单位时间收益率" `r_t' = R_t / Δb_t`，让总回报与 T 解耦。  
   修改点：`rl_capa/trainer.py` 第 49 行 `discount_factor: float = 0.9` 改 1.0；或在 `_compute_discounted_returns` 之前预处理 reward。

2. **修正 stage1_trainer 注释方向错误**（不影响行为，但避免误导后续维护者）  
   注释里"smaller batch → larger discounted sum"实际反了：γ<1 抬高的是步数更"少"的回报。文字反过来即可。

3. **校核 batch_actions 实际配置与 CLI 的一致性**（针对 §6.0）  
   现有 6 维动作（含 60s）与 CLI 5 维不符。需确认 `RLCAPAConfig.batch_action_values()` 是否在某条路径上把 `step_seconds` 注入；若有就移除，避免出现"训练时把最坏选项给加进来"的隐式 bug。

### 4.2 强烈建议（P1）

4. **去掉 V1 与 V2 的 target 塌缩**（针对 §3.2）  
   规范层修订建议（覆盖 `docs/rl_capa_algo.md` §6.1）：  
   - V2 改为 Q1：直接以 (s_t^(1), a_t^(1)) 为输入，回归 R̂_t；π1 用 `A1 = Q1(s,a) − Σ_a' π1(a'|s)·Q1(s,a')` 或 GAE。  
   - V1 改为 baseline，仅服务方差降低，不再与 V2 同回归同一 R̂_t。  
   实现量：新增 `BatchSizeQCritic` 网络（输入 6 维 s + one-hot a1，输出标量），替换或补充 `ConditionalValueCritic`。

5. **加强 π1 的 entropy 调度**（针对 §3.3）  
   - `entropy_coeff` 起始 0.05–0.1，按 episode 线性退火到 0.005。  
   - 或在 π1 网络末端加温度系数 τ，初始 τ=2.0 退到 1.0。  
   - 同时把 `_normalize_advantages` 在 advantages 方差过低时的 fallback 从"全零"改成"返回 raw advantage"（针对 §3.4），保住信号。

6. **解耦 π2 的 reward credit**（针对 §3.5）  
   - π2 的 advantage 应当只看「本 batch 内 cross-or-not 的边际差」，而不是吃整个 R̂_t。  
   - 方案：每 batch 内做一次 counterfactual 估计（对每个 parcel 计算 a=0 和 a=1 的预估收益差，作为 per-parcel advantage）。  
   - 简化版：用"本 batch 收益 r_t" 替代 R̂_t 给 π2，让 stage1 + stage2 两段策略不再共享 long-horizon 噪声。

### 4.3 可选（P2）

7. **V2 显式拼接 a1 one-hot**（§3.7）：让 V2 真正"条件于 a1"，避免被 RunningNormalizer 抹平。

8. **状态扩展**：`s_t^(1)` 加入「当前 episode 内已选过的 batch sizes 直方图」、「已交付率」、「expired 比例」，让 π1 有更多区分度。

9. **分阶段 lr**：critic 的 lr 应明显高于 actor（已设 5e-4 vs 3e-4，差距偏小），可调到 1e-3 vs 2e-4。

10. **奖励监控**：训练日志同时记录"未折扣 episode 总收益"和"折扣 R̂_0"，方便发现 §3.1 类偏置；建议作为 visualize.py 的额外曲线。

---

## 5. 修复实施步骤与检查点

下面给出最小闭环；`checkpoint X` 处需通过对应验证才可继续。

### Step 1：修 γ（P0-1，预计收益最大）
- 修改 `rl_capa/config.py:60` 默认 `discount_factor=1.0`，CLI 默认随之改为 1.0。  
- 重跑相同 ablation。  
- **checkpoint A**：rl-capa 末 100 ep reward ≥ stage2 末 100 ep reward；π1 不再 100% 选最大动作。  
  预期：rl-capa 至少 ~1900；mean_batch_size 末段在 [25, 35] 区间。

### Step 2：核对 batch_action_values（P0-3）
- 跑 `python3 -c "from rl_capa.config import RLCAPAConfig; print(RLCAPAConfig(min_batch_size=10,max_batch_size=20,batch_actions=[10,15,20,25,30],step_seconds=60).batch_action_values())"`，应只有 5 个值。  
- 在 `RLCAPATrainer` 入口 assert `set(batch_action_values) == set(rl_config.batch_actions)`。  
- **checkpoint B**：训练日志的 `batch_size_sequences` 不再出现非 CLI 列表内的值。

### Step 3：修 stage1_trainer 注释方向（P0-2）
- `rl_capa/stage1_trainer.py:132–145`：把"smaller batch → more steps → larger sum"反过来为"fewer steps → less discount → larger discounted sum"。一行改动。

### Step 4：上 entropy schedule（P1-5）
- 在 `TrainingConfig` 加 `entropy_start`, `entropy_end`, `entropy_decay_episodes`；`_update_networks` 处用线性退火值。  
- **checkpoint C**：π1 entropy 在前 30% episodes 保持 ≥ 1.0，最终降至 0.1–0.3；π1 动作分布维持非退化。

### Step 5：解耦 V1/V2 target（P1-4）（如 Step 1 已修复指标，可推迟）
- 引入 Q1 critic：`networks.py` 加 `BatchSizeQCritic(state_dim=6, num_actions, hidden=128)`；输出每个动作的 Q。  
- `trainer._update_networks` 用 `A1 = Q1(s,a) − sum_a' π1(a')·Q1(s,a')`。  
- V1 保留为 R̂_t baseline（可选）。  
- **checkpoint D**：训练后期 π1 entropy 不再坍塌至 0；A1 方差稳定 > 0.05。

### Step 6：advantages 归一化兜底（P1-5 后半）
- `_normalize_advantages` 当 std≤ε 时返回 `advantages − advantages.mean()` 而不是全零。  
- **checkpoint E**：episode advantage 的 magnitude 在收敛后仍 > 0。

### Step 7：π2 局部 credit（P1-6，可作为 Tier-2）
- 在 trainer 收 reward 阶段，按 batch 切分 r_t；π2 用本 batch r_t 作为优势 baseline。  
- **checkpoint F**：rl-capa 收益超过 stage2 ≥ 5%；π2 entropy 末段不显著低于 stage2。

每个 checkpoint 通过后再进入下一步；P0 三步即可大概率扭转 rl-capa < stage2 的反常结果。

---

## 6. 旁支：CLI 与实际 action space 的不一致（待确认）

### 6.0 现象
- 用户 CLI：`--rl-batch-actions 10 15 20 25 30`（5 个动作）。
- 实际训练记录的 batch_size_sequences 包含 `{10,15,20,25,30,60}`（6 个动作）。
- 当前 `RLCAPAConfig.batch_action_values()` 在显式 batch_actions 模式下不会注入 step_seconds=60。

### 6.1 可能原因
1. 训练时使用了与当前 master 不同的代码（git log 见 `c6a61aa feat(rl-capa): support explicit batch action sets` 是 4-27 引入显式动作集；此前可能默认 union step_seconds）。
2. 实际 CLI 与文档示例略有不同（如真实跑的是 `--rl-batch-actions 10 15 20 25 30 60`）。

### 6.2 处理建议
- 在 `train.py` / `train_stage1.py` 把 `batch_action_values` 写入 `training_summary.json`，保留实际配置审计。  
- 在 `RLCAPATrainer.__init__` 补 `assert num_batch_actions == len(rl_config.batch_action_values())`。  
- 重新跑实验时使用统一脚本，并记录 `--rl-batch-actions` 与 git commit。

---

## 7. 预期效果总览

| 修复阶段 | 期望末段 reward | 期望现象 |
|----------|----------------|---------|
| 现状 | 1835 | π1 全选 60，π2 受 covariate shift 损耗 |
| Step 1 (γ=1) | ≥ 1900 | π1 不再单点；mean_batch ≈ 25–35 |
| Step 1+4 (γ=1+entropy) | ≥ 1920 | π1 entropy 不退化；探索-利用平衡 |
| Step 1+4+5 (Q1 critic) | ≥ 1950 | A1 信号稳定，rl-capa 显著超过 stage2 |
| 全量 | ≥ 1980 | π2 不再被 covariate shift 拖累 |

stage2 既然已经 1910，超过它意味着 rl-capa 必须真正利用动态批量带来的"忙时缩短/闲时扩大"红利；当前的 γ + critic 设计无法表达这种红利。

---

## 8. 论文层面的修订建议

为下一版论文准确描述算法：
1. 明确写出"R_t 是单步收益、R̂_t 是 MC return、训练目标用 γ=1（finite-horizon）"，避免 §3.1 陷阱。
2. 把 V2 重新定义为 Q(s,a)，A1 用 Q-baseline 而非 V2−V1，规避 §3.2 同 target 塌缩。
3. 在状态空间里显式声明 `s_t^(1)` 与 `s_t^(2)` 的归一化方案，并给出 entropy schedule。
4. 在实验章节补一组 sweep（Δb 集合大小、γ）来佐证新公式不再敏感。

