# RL-CAPA 算法实现细节分析

> 本文档基于论文 Section 3.4 "Dual-Stage Adaptive Assignment Optimization" 和 Section 4.1 实验设置，
> 逐字逐句分析 RL-CAPA 的完整实现逻辑。供 Claude Code 在当前代码架构下实现算法时参考。

---

## 1. RL-CAPA 与 CAPA 的关系：不是替换，而是增强

### 1.1 CAPA（Algorithm 1）的固定决策点

CAPA 中有两个固定的决策：

| 决策点 | CAPA 的做法 | 位置 |
|--------|-----------|------|
| 批次大小 | 固定值 `Δb`（作为输入参数） | Algorithm 1 Line 5: `if t_cum == Δb` |
| 未分配 parcel 去向 | CAMA 产生的 `L_cr` 全部送入 DAPA | Algorithm 1 Line 9: `M_cr ← DAPA(P_S, L_cr)` |

### 1.2 RL-CAPA 的改动范围

RL-CAPA **保留了 CAMA 和 DAPA 的全部内部逻辑不变**，只用 DDQN 替换了上面两个决策点：

| 决策点 | RL-CAPA 的做法 | 对应 MDP |
|--------|---------------|---------|
| 批次大小 | DDQN-1 从离散动作空间 `A_b = [h_L, ..., h_M]` 中选择 | M_b |
| 未分配 parcel 去向 | DDQN-2 对每个未分配 parcel 做 binary 决策：送去 DAPA (a_m=1) 或推迟到下一批次 (a_m=0) | M_m |

**关键理解**：CAMA 仍然正常执行——它仍然会：
- 计算 utility u(τ,c)
- 计算 threshold T_h
- 将 u ≥ T_h 的 parcel 分配到 M_lo（本地匹配）
- 将 u < T_h 或无可行 courier 的 parcel 输出到 L_cr

RL-CAPA 的 M_m 只作用于 CAMA 输出的 `L_cr`（auction pool），而不是所有 parcel。

---

## 2. RL-CAPA 的完整执行流程

下面用伪代码展示一个 episode 内的完整执行流程，精确标注每一步对应论文的哪段描述。

```
输入：parcel stream Γ, couriers C, cooperating platforms P
输出：matching plan M

M ← ∅
Γ_carry ← ∅                          # 被推迟的 parcels（上一批次 M_m 决策 a_m=0 的）
t_cur ← 0                            # 当前时间指针

while timeline t is not terminal:     # 一个 episode = 一天的完整时间线

    #===== 阶段 1：M_b 决策——选择批次大小 =====
    # 论文："The local platform is modeled as an agent that observes the environment
    #        and selects a batch size from the discrete action space A_b"
    
    s_b ← observe_batch_state(t_cur)  # 构建 S_b 状态
    a_b ← DDQN_batch.select(s_b)      # 选择批次持续时间（秒）
    
    #===== 阶段 2：按批次大小累积 parcels =====
    # 这对应 Algorithm 1 Lines 2-4 但用 a_b 替换了固定的 Δb
    
    Γ_batch ← ∅
    for each time step t in [t_cur, t_cur + a_b):
        Γ_t ← retrieve_arriving_parcels(t)
        Γ_batch ← Γ_batch ∪ Γ_t
    Γ_batch ← Γ_batch ∪ Γ_carry       # 合并上一批次推迟过来的 parcels
    Γ_carry ← ∅                        # 清空 carry 池
    t_cur ← t_cur + a_b
    
    #===== 阶段 3：执行 CAMA 本地匹配 =====
    # 论文 Algorithm 1 Line 8，完全不变
    
    C_S ← retrieve_available_inner_couriers()
    M_lo, L_cr ← CAMA(Γ_batch, C_S)
    
    # 此时：
    # M_lo = 本地匹配成功的 (parcel, courier) 对
    # L_cr = CAMA 认为应该进入跨平台拍卖的 parcels
    #        包括：u < T_h 的 parcels + 没有 feasible courier 的 parcels
    
    #===== 阶段 4：M_m 决策——对 L_cr 中每个 parcel 做 cross-or-not =====
    # 论文："each parcel is treated as an agent making the cross-or-not decision"
    # 注意：M_m 的决策对象是 L_cr，不是全部 parcels
    
    L_cross ← ∅     # 最终送去 DAPA 的 parcels
    for each parcel τ in L_cr:
        s_m ← observe_parcel_state(τ, t_cur, a_b)  # 构建 S_m 状态
        a_m ← DDQN_cross.select(s_m)               # binary: 0 or 1
        
        if a_m == 1:
            L_cross ← L_cross ∪ {τ}    # 送去跨平台拍卖
        else:  # a_m == 0
            Γ_carry ← Γ_carry ∪ {τ}    # 推迟到下一批次
    
    #===== 阶段 5：执行 DAPA 跨平台拍卖 =====
    # 论文 Algorithm 1 Line 9，对 L_cross（不是原始 L_cr）执行
    
    P_S ← retrieve_available_platforms()
    M_cr ← DAPA(P_S, L_cross)
    
    #===== 阶段 6：合并结果 =====
    M ← M ∪ M_lo ∪ M_cr
    
    #===== 阶段 7：处理 DAPA 也未能分配的 parcels =====
    # 论文 Section 3.2："The parcels that are not allocated in the current batch
    #                    will reenter the next batch for re-matching"
    # M_m 决策 a_m=1 但 DAPA 也没有匹配上的 parcels
    
    L_dapa_failed ← L_cross \ {τ | (τ, c) ∈ M_cr}
    Γ_carry ← Γ_carry ∪ L_dapa_failed
    
    #===== 阶段 8：计算 rewards，存储 transitions =====
    # (详见第 4 节 reward 计算)
    
    r_b ← compute_batch_reward(M_lo, M_cr)
    for each parcel τ and its action a_m:
        r_m ← compute_parcel_reward(τ, a_m)
    
    # 存储到 replay buffers 并优化（详见第 6 节）

return M
```

---

## 3. MDP M_b：批次大小选择（全局级决策）

### 3.1 时间粒度

论文给出了一个例子：`h_L = 10, h_M = 20`，动作空间为 `{10, 11, ..., 20}`，单位是**秒**。
每个 action 代表一个 "specific batch duration"。

### 3.2 状态空间 S_b

论文原文定义：

```
s_t = (|Γ_t^Loc|, |C_t^Loc|, |D|, |T|)
```

四个分量的含义和计算方式：

| 分量 | 含义 | 计算方式 |
|------|------|---------|
| `|Γ_t^Loc|` | 当前待处理 parcels 数量 | 当前时刻 local platform 的 pending parcels 数量（包括新到达的 + carry over 的） |
| `|C_t^Loc|` | 当前可用 couriers 数量 | local platform 的 available inner couriers 数量（排除已满载或已过 deadline 的） |
| `|D|` | courier 与 pick-up tasks 的平均距离 | `mean(dist(c, τ)) for all feasible (c, τ) pairs`，论文说 "lower values imply closer proximity" |
| `|T|` | 任务紧迫度 | 论文引用 [22] 的定义："task urgency relative to the current time slice and task deadline"，具体计算为 `mean((t_τ - t_cur) / t_τ)` 或类似的归一化紧迫度 |

**状态维度：4**

### 3.3 实现要点

- 状态在**每个批次开始前**观测一次（即选择 a_b 之前）
- `|D|` 的计算需要在选择批次大小之前就能得到——用上一个时刻的 courier 位置和当前 pending parcels 的位置计算
- `|T|` 需要归一化，论文引用 [22] 的处理方式

### 3.4 动作空间 A_b

```
A_b = [h_L, h_L+1, ..., h_M]
```

- 离散动作，动作数量 = `h_M - h_L + 1`
- 论文例子：h_L=10, h_M=20 → 11 个动作
- 每个动作对应一个**时间持续时长（秒）**
- Q 网络的输出维度 = `h_M - h_L + 1`
- 实际批次大小 = `h_L + action_index`

### 3.5 奖励函数 R_b

论文原文：

> "the agent receives an immediate reward R(s_{t+1} | s_t, a_t), defined as the total matching revenue Rev_S(Γ_Loc, C_Loc, P) obtained in the batch (see Eq. 5)"

```
R_b = Rev_S(Γ_Loc, C_Loc, P)
    = Σ_{(τ_i, c_i) ∈ M_lo} (p_τ_i - Rc(τ_i, c_i))     # 本地匹配的收入
    + Σ_{(τ_j, c_j) ∈ M_cr} (p_τ_j - p'(τ_j, c_j))      # 跨平台匹配的收入
```

其中 `Rc(τ, c) = ζ · p_τ`（本地 courier 支付），`p'(τ, c)` 是 DAPA 决定的跨平台支付。

**R_b 是整个批次执行完毕后（CAMA + M_m决策 + DAPA 全部完成后）才能计算的。**

### 3.6 transition 定义

一个 transition for M_b:
```
(s_b, a_b, r_b, s_b_next, done)
```
- `s_b`：批次开始前的全局状态
- `a_b`：选择的批次大小
- `r_b`：该批次的总收入（Eq.5）
- `s_b_next`：下一个批次开始前的全局状态
- `done`：时间线是否结束

---

## 4. MDP M_m：Cross-or-not 决策（parcel 级决策）

### 4.1 决策对象

**M_m 的决策对象是 CAMA 输出的 `L_cr` 中的每一个 parcel**，不是全部 parcel。

论文原文："each parcel is treated as an agent making the cross-or-not decision. Action a_m = 1 assigns the parcel to the cross-platform auction pool, while a_m = 0 defers it to the next batch."

### 4.2 状态空间 S_m

论文原文定义：

```
s_m = (|ΔΓ|, t_τ, t_cur, Δb)
```

| 分量 | 含义 | 计算方式 |
|------|------|---------|
| `|ΔΓ|` | 未分配 parcels 的数量 | `len(L_cr)` — 即 CAMA 输出的 auction pool 大小 |
| `t_τ` | 当前 parcel 的 deadline | parcel 的属性 `t_τ`，直接使用 |
| `t_cur` | 当前时间 | 当前时间指针 |
| `Δb` | 本批次的批次大小 | **来自 M_b 的 action**——这是两个 MDP 耦合的关键 |

**状态维度：4**

### 4.3 关于耦合的实现细节

`Δb` 出现在 S_m 中意味着：
- 每个 parcel agent 在做 cross-or-not 决策时，知道当前批次有多大
- 如果 M_b 选了一个较小的 Δb，parcel 知道批次较短，可能更倾向于 cross（因为下一批次来得快）
- 如果 M_b 选了一个较大的 Δb，parcel 知道批次较长，可能更倾向于 defer（积累更多 parcels）

### 4.4 动作空间 A_m

```
A_m = {0, 1}
```
- `a_m = 0`：推迟到下一批次（defer）
- `a_m = 1`：进入跨平台 auction pool（cross）

Q 网络的输出维度 = 2

### 4.5 奖励函数 R_m（三分支）

论文给出了明确的三分支定义：

```
R_m(s_m, a_m) = {
    p_τ - Rc(τ, c)      if a_m = 0 AND I(τ) = 1    # Case 1
    p_τ - p'_τ(τ, c)    if a_m = 1 AND I(τ) = 1    # Case 2
    0                    otherwise                    # Case 3
}
```

**对每个 case 的详细分析：**

**Case 1：a_m = 0 且 I(τ) = 1**
- parcel 被推迟到下一批次
- 在下一批次中，这个 parcel 重新进入 CAMA
- 如果在下一批次中被 CAMA 成功分配给 inner courier（I(τ)=1），reward = 本地收入 = `p_τ - ζ·p_τ`
- **实现难点**：这个 reward 不是立即可得的，需要等到下一批次执行完才能确定

**Case 2：a_m = 1 且 I(τ) = 1**
- parcel 进入 DAPA
- DAPA 成功将其分配给 cross courier（I(τ)=1），reward = 跨平台收入 = `p_τ - p'(τ, c)`
- `p'(τ, c)` 是 DAPA 拍卖产生的支付价格
- **这个 reward 在当前批次结束时就可以得到**

**Case 3：otherwise（I(τ) = 0）**
- 不管选了 a_m=0 还是 a_m=1，parcel 最终未被分配
- reward = 0
- 如果 a_m=0：被推迟到下一批次，下一批次也没分配上 → reward = 0
- 如果 a_m=1：进入 DAPA 但没有平台/courier 能接 → reward = 0
- **论文明确说明**："if a parcel τ is not assigned, i.e., I(τ) = 0, it reappears as a new agent in the next batch to re-evaluate the cross-or-not decision"

### 4.6 R_m 的 reward 时机问题——实现策略

上面的分析揭示了一个关键的实现问题：

- 如果 `a_m = 1`（cross）：reward 在**当前批次** DAPA 执行后就能知道
- 如果 `a_m = 0`（defer）：reward 要等到**下一个（或更后面的）批次**才能知道

**推荐的实现策略**：

```
对 a_m = 1 的 parcels:
    DAPA 执行后，立即计算 reward：
    - 如果 DAPA 匹配成功：r_m = p_τ - p'(τ, c)
    - 如果 DAPA 匹配失败：r_m = 0（parcel 进入 carry）

对 a_m = 0 的 parcels:
    当前批次不计算 reward，将 parcel 放入 carry 池。
    在 parcel 最终被分配或确定无法分配时，回填 reward：
    - 如果在后续某个批次被 CAMA 本地分配：r_m = p_τ - ζ·p_τ
    - 如果在后续某个批次被再次送入 DAPA 并成功：不适用（那时是一个新的 M_m 决策）
    - 如果直到 episode 结束仍未分配：r_m = 0
```

**简化方案**（更易实现，也合理）：

由于 a_m=0 的 parcel 在下一批次重新进入 CAMA → 可能再次进入 L_cr → 做新的 M_m 决策，
本质上是一个新的 episode step。因此可以将 a_m=0 视为：
```
r_m = 0（defer 本身没有立即 reward）
parcel 以新 agent 身份出现在下一批次
```

这个简化与论文"it reappears as a new agent in the next batch"一致。

### 4.7 transition 定义

一个 transition for M_m (per parcel):
```
(s_m, a_m, r_m, s_m_next, done)
```

- `s_m`：该 parcel 在当前批次的状态 (|ΔΓ|, t_τ, t_cur, Δb)
- `a_m`：0 或 1
- `r_m`：按上面的三分支计算
- `s_m_next`：
  - 如果 a_m=1 且成功分配：terminal state（该 parcel 已完成）
  - 如果 a_m=1 且 DAPA 失败：parcel 进入下一批次的状态
  - 如果 a_m=0：parcel 进入下一批次的状态
- `done`：时间线是否结束 或 parcel 是否被分配/过期

### 4.8 Centralized Q-network

论文原文：

> "the number of decision agents (i.e., parcels) varies dynamically across matching batches, making decentralized learning approaches infeasible... we adopt a centralized Q-network framework, where all agents share a common Q-function that generalizes across varying parcel states and actions."

实现含义：
- 只有**一个** CrossQNetwork 实例
- 每个 parcel 输入自己的 s_m，通过同一个网络得到 Q(s_m, 0) 和 Q(s_m, 1)
- 一个批次中所有 parcel 的 transitions 都存入同一个 replay buffer
- 训练时从这个 buffer 采样 mini-batch 更新同一个网络

---

## 5. DDQN 网络架构与训练细节

### 5.1 网络架构

论文没有指定具体的网络层数和宽度，只说使用 DDQN。合理的设计：

```python
# BatchQNetwork (M_b)
# 输入: s_b ∈ R^4
# 输出: Q(s_b, a) for each a ∈ A_b, 维度 = h_M - h_L + 1
class BatchQNetwork(nn.Module):
    Linear(4, 128) → ReLU
    Linear(128, 128) → ReLU
    Linear(128, |A_b|)

# CrossQNetwork (M_m)  
# 输入: s_m ∈ R^4
# 输出: Q(s_m, 0), Q(s_m, 1), 维度 = 2
class CrossQNetwork(nn.Module):
    Linear(4, 128) → ReLU
    Linear(128, 128) → ReLU
    Linear(128, 2)
```

### 5.2 DDQN 更新规则

DDQN（Double DQN）与普通 DQN 的区别：

```
普通 DQN:
    target = r + γ · max_a Q_target(s', a)

Double DQN (论文使用):
    a* = argmax_a Q_online(s', a)       ← 用 online 网络选动作
    target = r + γ · Q_target(s', a*)   ← 用 target 网络评估
```

### 5.3 训练超参数（论文 Section 4.1 明确给出）

| 参数 | 值 | 来源 |
|------|-----|------|
| 优化器 | RMSprop | "we use the RMSprop optimizer" |
| 学习率 | 0.001 | "with a learning rate of 0.001" |
| 折扣因子 γ | 0.9 | "and a discount factor of 0.9" |

以下参数论文未明确指定，需要合理设置：

| 参数 | 建议值 | 理由 |
|------|--------|------|
| Replay buffer 容量 | 50000 | 标准 DDQN 配置 |
| Mini-batch size | 64 | 标准配置 |
| Target network 更新频率 | 每 100 steps hard update | 标准配置 |
| Epsilon 初始值 | 1.0 | 标准 exploration |
| Epsilon 终止值 | 0.01 | 标准配置 |
| Epsilon 衰减 | 线性或指数衰减 | 按 episode 数调整 |
| 训练 episode 数 | 需实验确定 | 观察收敛曲线 |

---

## 6. 联合训练算法

### 6.1 论文关于联合训练的原文

> "we jointly train the DDQN models for M_b and M_m. During joint training, the shared environment is updated based on the combined outcomes of both decision processes, allowing each agent to account for the downstream impact of its actions and improve long-term revenue optimization under dynamic system conditions."

### 6.2 联合训练的精确实现

```python
# 初始化
batch_agent = DDQNAgent(BatchQNetwork, ...)      # M_b 的 DDQN
cross_agent = DDQNAgent(CrossQNetwork, ...)      # M_m 的 DDQN
batch_buffer = ReplayBuffer(capacity)
cross_buffer = ReplayBuffer(capacity)
env = CAPAEnvironment(config)

for episode in range(num_episodes):
    s_b = env.reset()           # 重置环境，返回初始 batch state
    episode_return = 0
    done = False
    
    while not done:
        #--- M_b 决策 ---
        a_b = batch_agent.select_action(s_b)
        
        #--- 按 a_b 累积 parcels + 执行 CAMA ---
        Γ_batch, C_S = env.accumulate_and_get_cama_inputs(a_b)
        M_lo, L_cr = CAMA(Γ_batch, C_S)          # 直接调用 CAMA
        
        #--- M_m 决策（对 L_cr 中的每个 parcel） ---
        L_cross = []
        parcel_transitions = []
        
        for τ in L_cr:
            s_m = build_parcel_state(τ, env, a_b)
            a_m = cross_agent.select_action(s_m)
            
            if a_m == 1:
                L_cross.append(τ)
            else:
                env.defer_parcel(τ)               # 推迟到下一批次
        
        #--- 执行 DAPA ---
        P_S = env.get_available_platforms()
        M_cr = DAPA(P_S, L_cross)                 # 直接调用 DAPA
        
        #--- 处理 DAPA 也失败的 parcels ---
        for τ in L_cross:
            if τ not in M_cr:
                env.defer_parcel(τ)
        
        #--- 更新环境状态 ---
        env.apply_assignments(M_lo, M_cr)
        
        #--- 计算 rewards ---
        r_b = compute_total_revenue(M_lo, M_cr)   # Eq.5
        
        for τ in L_cr:
            a_m = ... # 该 parcel 的动作
            if a_m == 1:
                if τ in M_cr:
                    r_m = p_τ - p'(τ, c)          # Case 2
                else:
                    r_m = 0                        # Case 3
            else:  # a_m == 0
                r_m = 0  # defer 的即时 reward 为 0（论文简化）
            
            s_m_next = ...  # 下一状态或 terminal
            cross_buffer.push(s_m, a_m, r_m, s_m_next, done_parcel)
        
        s_b_next = env.get_batch_state()
        done = env.is_terminal()
        
        #--- 存储 M_b transition ---
        batch_buffer.push(s_b, a_b, r_b, s_b_next, done)
        
        #--- 训练两个 DDQN ---
        if len(batch_buffer) >= min_buffer_size:
            loss_b = batch_agent.train_step(batch_buffer)
        if len(cross_buffer) >= min_buffer_size:
            loss_m = cross_agent.train_step(cross_buffer)
        
        #--- 更新 target networks ---
        batch_agent.maybe_update_target()
        cross_agent.maybe_update_target()
        
        episode_return += r_b
        s_b = s_b_next
    
    #--- Episode 结束 ---
    log_metrics(episode, episode_return, loss_b, loss_m, epsilon, ...)
```

### 6.3 双向耦合的具体体现

论文说两个 MDP "closely coupled and mutually affect"，具体在代码中体现为：

**M_b → M_m 的影响：**
- `a_b`（批次大小）出现在 M_m 的状态 `s_m = (..., Δb)` 中
- 较小的 a_b → 批次中 parcels 更少 → |ΔΓ| 可能更小 → M_m 面对的 L_cr 更小
- 较大的 a_b → 批次中 parcels 更多 → CAMA 有更多匹配机会 → L_cr 可能更小也可能更大

**M_m → M_b 的影响：**
- M_m 决策 a_m=0（defer）→ parcel 进入 carry 池 → 下一批次的 |Γ_t^Loc| 增加 → 影响下一个 s_b
- M_m 决策 a_m=1（cross）→ parcel 被 DAPA 处理 → 可能影响 courier 可用性 → 影响下一个 s_b 的 |C_t^Loc|

---

## 7. 在当前代码架构下的实现对接点

### 7.1 env 需要从 CAPA 模块导入的接口

```python
from src.capa.cama import cama_assign       # Algorithm 2
from src.capa.dapa import dapa_assign       # Algorithm 3
from src.core.revenue import compute_total_revenue  # Eq.5
from src.core.constraints import check_feasibility
```

env 不应该重新实现 CAMA 或 DAPA 的任何逻辑。

### 7.2 env 需要额外维护的状态

```python
class CAPAEnvironment:
    self.parcel_stream        # 完整的 parcel 时间序列
    self.couriers             # 所有 couriers（状态会动态变化）
    self.platforms            # 所有 cooperating platforms
    self.t_cur                # 当前时间指针
    self.carry_parcels        # 被 M_m defer 的 parcels（跨批次携带）
    self.total_parcels        # episode 的总 parcel 数（用于计算 CR）
    self.completed_parcels    # 已完成的 parcels 数
```

### 7.3 env.reset() 的行为

```python
def reset(self):
    self.t_cur = 0
    self.carry_parcels = []
    self.completed_parcels = 0
    # 重置所有 courier 状态（位置、容量、schedule）
    # 返回初始 s_b
```

### 7.4 关于 episode 的定义

- 一个 episode = 模拟一天的完整时间线
- 时间线从 t=0 开始，到 t=T_max（如一天 86400 秒）结束
- 每个 batch step 消耗 a_b 秒的时间
- done = True when t_cur ≥ T_max

---

## 8. 关键实现约束（禁止兜底）

| 场景 | 正确做法 | 禁止做法 |
|------|---------|---------|
| L_cr 为空（CAMA 全部本地分配） | M_m 无需执行，直接 finalize | 不要人为往 L_cr 里加 parcel |
| DAPA 返回空匹配 | parcel 进入 carry 池，r_m=0 | 不要用 random assignment 补救 |
| carry_parcels 中的 parcel deadline 已过 | 该 parcel 视为过期，r_m=0，不再参与 | 不要延长 deadline |
| Replay buffer 不够大 | 等 buffer 积累足够再开始训练 | 不要用随机数据填充 |
| 某个 batch 没有可用 courier | CAMA 返回 M_lo=∅, L_cr=全部 | 不要 skip 这个 batch |
| a_b 导致批次超过时间线末尾 | 截断到时间线末尾 | 不要跳过这个最后的 batch |

---

## 9. 评估模式

评估时与训练的区别：
- epsilon = 0（纯 exploitation，不做 exploration）
- 不更新 replay buffer
- 不做 gradient 更新
- 记录 TR, CR, BPT 等指标

---

## 10. 需要实现的文件清单

| 文件 | 核心职责 |
|------|---------|
| `src/rl/state_builder.py` | build_batch_state(), build_parcel_state() |
| `src/rl/env.py` | CAPAEnvironment (reset, accumulate, step, defer, finalize) |
| `src/rl/replay_buffer.py` | ReplayBuffer (push, sample, len) |
| `src/rl/models.py` | BatchQNetwork, CrossQNetwork |
| `src/rl/ddqn_agent.py` | DDQNAgent (select_action, train_step, update_target, save, load) |
| `src/rl/train_rl_capa.py` | 联合训练主循环 + metric logging |
| `src/rl/evaluate_rl_capa.py` | 评估循环 |
| `src/rl/visualize.py` | 训练曲线绘图 |

---

## 11. 需要记录的 Metrics

### 训练阶段（每 episode 记录）

| Metric | 含义 | 用途 |
|--------|------|------|
| episode_return | 整个 episode 的 R_b 总和 | reward 曲线 |
| loss_batch | M_b DDQN 的 Q loss | 收敛监控 |
| loss_cross | M_m DDQN 的 Q loss | 收敛监控 |
| epsilon | 当前 exploration 率 | epsilon 衰减曲线 |
| avg_batch_size | episode 中选择的平均 batch size | 策略分析 |
| cross_ratio | episode 中选择 a_m=1 的比例 | 策略分析 |
| completion_rate | episode 的 CR | 性能监控 |
| total_revenue | episode 的 TR | 性能监控 |
| bpt | 平均 batch processing time | 效率监控 |

### 评估阶段（每 eval 周期记录）

| Metric | 含义 |
|--------|------|
| eval_return | 评估 episode 的总 return |
| eval_tr | 评估的 TR |
| eval_cr | 评估的 CR |
| eval_bpt | 评估的 BPT |
