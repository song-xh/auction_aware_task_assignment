# RL-CAPA Implementation Specification

本文档是 RL-CAPA 的唯一有效实现规范。所有实现必须严格遵循此文档。
旧版 DDQN 设计已废弃，不再适用。

---

## 1. 总体架构

RL-CAPA 是一个**两阶段 hierarchical actor-critic** 方法，包含 4 个网络：

| 网络 | 符号 | 参数 | 输入 | 输出 | 角色 |
|------|------|------|------|------|------|
| Actor 1 | π1 | θ1 | s_t^(1) | a_t^(1) 的概率分布 | 选择 batch time-window size |
| Actor 2 | π2 | θ2 | s_{t,i}^(2), a_t^(1) | a_{t,i} 的概率 (0 or 1) | 每个 parcel 的 cross-or-not 决策 |
| Critic 1 | V1 | φ1 | s_t^(1) | 标量 | 第一阶段决策前的状态价值 |
| Critic 2 | V2 | φ2 | s_t^(2), a_t^(1) | 标量 | 第一阶段动作确定后的条件状态价值 |

关键设计：
- V2 将 a_t^(1) 视为**已知环境条件**（非待选动作），因为进入第二阶段时 batch size 已确定
- π2 按 parcel 因子化：π2(a_t^(2) | s_t^(2), a_t^(1)) = ∏_i π2(a_{t,i} | s_{t,i}^(2), a_t^(1))，所有 parcel 共享同一网络参数
- 所有网络共享同一个环境，优化同一个平台级回报 R_t

---

## 2. 与 CAPA 的关系

RL-CAPA 不替换 CAPA，只替换 Algorithm 1 中的**两个固定决策点**：

| CAPA 中的固定决策 | RL-CAPA 的替换 |
|-------------------|---------------|
| 固定 batch size Δb | π1 动态选择 a_t^(1) ∈ A_b |
| 自动路由到 DAPA（所有未匹配 parcel 进入拍卖池） | π2 逐 parcel 决策 a_{t,i} ∈ {0, 1} |

CAMA、DAPA、utility 计算、约束检查等**全部复用** CAPA 的模块，通过 import 调用。

---

## 3. 状态空间定义

### 3.1 第一阶段状态 S_b

```
s_t^(1) = (|Γ_t^Loc|, |C_t^Loc|, |D|, |T|)
```

| 特征 | 符号 | 含义 | 计算方式 |
|------|------|------|----------|
| 待处理 parcel 数 | \|Γ_t^Loc\| | 本地平台当前待分配 parcel 数量 | 直接计数 |
| 可用 courier 数 | \|C_t^Loc\| | 本地平台当前可用 courier 数量 | 直接计数 |
| 平均距离 | \|D\| | courier 与 pick-up 任务的平均距离 | 对所有可行 (courier, parcel) 对求平均距离 |
| 任务紧迫度 | \|T\| | 相对于当前时间和 deadline 的紧迫程度 | 对所有 parcel 求 (deadline - t_cur) 的平均值 |

维度：4

### 3.2 第二阶段状态 S_m（per-parcel）

```
s_{t,i}^(2) = (t_τi, t_cur, v_τi, |ΔΓ_t|, |C_t^Loc|, ū_t^Loc, |C_t^Cross|, b̄_t^Cross, Δb)
```

| 特征 | 符号 | 含义 | 计算方式 |
|------|------|------|----------|
| parcel deadline | t_τi | parcel τ_i 的截止时间 | 从 parcel 对象读取 |
| 当前时间 | t_cur | 当前环境时间 | 从环境读取 |
| 估计本地净收益 | v_τi | p_τi - Rc_hat(τi) | parcel 价格减去估计服务成本 |
| 未分配 parcel 数 | \|ΔΓ_t\| | 当前 batch 内未分配 parcel 数 | 直接计数 |
| 本地可用 courier 数 | \|C_t^Loc\| | 同 S_b 中的定义 | 直接计数 |
| 本地 courier 平均剩余容量 | ū_t^Loc | 本地 courier 的平均剩余载货容量 | 对可用 courier 求平均 remaining_capacity |
| 跨平台可用 courier 总数 | \|C_t^Cross\| | 所有合作平台可用 courier 的总和 | 对各平台可用 courier 求和 |
| 跨平台近期平均中标价 | b̄_t^Cross | 近 N 个 batch 的 cross-platform 中标价滑动平均 | 维护一个滑动窗口 |
| batch size | Δb | 第一阶段选定的 batch 时间窗 | = a_t^(1) |

维度：9

**实现注意**：
- v_τi 中的 Rc_hat(τi) 可简化为到最近可用 courier 的路由成本估计
- b̄_t^Cross 在训练初期（无历史数据时）初始化为 0 或全局平均 parcel 价格
- 所有特征需要做归一化（建议用 running mean/std 或 min-max）

---

## 4. 动作空间定义

### 4.1 第一阶段动作 A_b

离散动作空间：A_b = {h_L, h_{L+1}, ..., h_M}

- h_L = 最小 batch 时长（秒），例如 10
- h_M = 最大 batch 时长（秒），例如 20
- π1 输出 |A_b| 维 softmax 概率，采样 a_t^(1)

### 4.2 第二阶段动作 A_m

每个 parcel 的二元动作：a_{t,i} ∈ {0, 1}
- 0 = defer to next batch
- 1 = send to cross-platform auction pool

π2 输出每个 parcel 的 sigmoid 概率，独立采样 a_{t,i}

---

## 5. 奖励定义

**平台级总奖励**（两阶段共用同一个奖励）：

```
R_t = Rev_S^t(Γ_Loc, C_Loc, P)
```

即论文 Eq.5 的 matching revenue，包括本地匹配收益和跨平台匹配收益。

**不要**为两个阶段设计不同的奖励函数。两个 stage 的策略通过各自的 advantage 来区分梯度信号，但 target return 是同一个 R_t。

---

## 6. 优势函数与策略更新

### 6.1 两个 Advantage

```
A_t^(1) = V2(s_t^(2), a_t^(1)) - V1(s_t^(1))
```

含义：选择该 batch time-window 后的条件状态价值，相比决策前的状态价值的增益。

```
A_t^(2) = R_t - V2(s_t^(2), a_t^(1))
```

含义：实际回报相比第二阶段条件预期的增益。

两者形成 coarse-to-fine 的价值链：V1 → V2 → R_t

### 6.2 策略梯度更新

```
∇J1(θ1) = E[∇log π1(a_t^(1) | s_t^(1); θ1) · A_t^(1)]
∇J2(θ2) = E[∇log π2(a_t^(2) | s_t^(2), a_t^(1); θ2) · A_t^(2)]
```

对于 π2 的因子化形式：
```
log π2(a_t^(2) | ...) = Σ_i log π2(a_{t,i} | s_{t,i}^(2), a_t^(1))
```

### 6.3 Critic 更新

```
L_V1(φ1) = E[(V1(s_t^(1); φ1) - R̂_t)²]
L_V2(φ2) = E[(V2(s_t^(2), a_t^(1); φ2) - R̂_t)²]
```

其中 R̂_t 是 empirical discounted return（Monte Carlo 回报）。

### 6.4 训练目标

```
max_{θ1,θ2}  J1(θ1) + J2(θ2)
min_{φ1,φ2}  L_V1(φ1) + L_V2(φ2)
```

**关键实现细节**：
- 4 个网络各有独立的 optimizer
- A_t^(1) 和 A_t^(2) 在送入 policy gradient 时必须 **detach**（stop-gradient on V1, V2）
- 不要把 4 个 loss 合成一个 loss 反传

---

## 7. 网络结构

### 7.1 π1（Batch Size Actor）
```
Input:  s_t^(1) ∈ R^4
Hidden: 2 层 MLP, 隐藏维度 128, ReLU
Output: softmax over |A_b| actions
```

### 7.2 π2（Cross-or-Not Actor，per-parcel 共享参数）
```
Input:  [s_{t,i}^(2), a_t^(1)] ∈ R^10  (9-dim state + 1-dim batch size)
Hidden: 2 层 MLP, 隐藏维度 128, ReLU
Output: sigmoid → P(a_{t,i}=1)
```

注意：a_t^(1) 在 s_{t,i}^(2) 中已包含为 Δb，所以 π2 的输入直接是 s_{t,i}^(2) 的 9 维向量。
不需要再额外拼接 a_t^(1)。

### 7.3 V1（State Value Critic）
```
Input:  s_t^(1) ∈ R^4
Hidden: 2 层 MLP, 隐藏维度 128, ReLU
Output: 标量 value
```

### 7.4 V2（Conditional State Value Critic）
```
Input:  [s_t^(2)_aggregated, a_t^(1)] ∈ R^(d_agg + 1)
Hidden: 2 层 MLP, 隐藏维度 128, ReLU
Output: 标量 value
```

**V2 的输入聚合问题**：π2 有多个 per-parcel 状态 s_{t,i}^(2)，但 V2 输出一个标量。
处理方式：将 batch 内所有 parcel 的 s_{t,i}^(2) 做 mean-pooling 得到 s_t^(2)_aggregated，
再拼接 a_t^(1)。

```python
s2_agg = mean([s_{t,i}^(2) for i in range(|ΔΓ_t|)])  # shape: (9,)
v2_input = concat([s2_agg, a_t^(1)])                   # shape: (10,)
# 注意: s2_agg 中已包含 Δb = a_t^(1)，所以也可以直接用 s2_agg 作为输入 (9,)
# 选择哪种方式取决于实验效果，建议先用 s2_agg (9,) 作为输入
```

---

## 8. 训练循环（伪代码）

```
initialize π1(θ1), π2(θ2), V1(φ1), V2(φ2)
initialize 4 optimizers: opt_π1, opt_π2, opt_V1, opt_V2

for episode in range(num_episodes):
    reset environment → get initial state
    episode_buffer = []
    
    while not done:
        # === 第一阶段 ===
        构建 s_t^(1) from environment
        a_t^(1) ~ π1(· | s_t^(1))          # 采样 batch size
        log_prob_1 = log π1(a_t^(1) | s_t^(1))
        
        # 环境按 a_t^(1) 推进时间，积累 parcel batch
        env.advance_time(a_t^(1))
        
        # === CAMA 本地匹配 ===
        M_lo, unassigned_parcels = CAMA(batch_parcels, available_couriers)
        
        # === 第二阶段 ===
        构建每个 parcel 的 s_{t,i}^(2)
        for each parcel τ_i in unassigned_parcels:
            a_{t,i} ~ π2(· | s_{t,i}^(2))     # 采样 cross-or-not
        log_prob_2 = Σ_i log π2(a_{t,i} | s_{t,i}^(2))
        
        # 按 a_{t,i} 分流：a=1 进拍卖池，a=0 defer
        auction_pool = [τ_i for a_{t,i}=1]
        deferred = [τ_i for a_{t,i}=0]
        
        # === DAPA 跨平台拍卖 ===
        M_cr = DAPA(auction_pool, cooperating_platforms)
        
        # === 计算奖励 ===
        R_t = compute_platform_revenue(M_lo, M_cr)  # 论文 Eq.5
        
        # === 记录 ===
        v1 = V1(s_t^(1))
        s2_agg = mean_pool([s_{t,i}^(2)])
        v2 = V2(s2_agg)
        
        episode_buffer.append({
            s1, a1, log_prob_1, s2_agg, v1, v2, R_t, log_prob_2
        })
    
    # === Episode 结束，计算 discounted returns ===
    compute R̂_t for all t using γ (backward cumulative)
    
    # === 计算 advantages ===
    for each step t:
        A_t^(1) = v2_t - v1_t               # detach v1, v2
        A_t^(2) = R̂_t - v2_t               # detach v2
    
    # === 更新 4 个网络 ===
    # Actor 1
    loss_π1 = -mean(log_prob_1 * A_t^(1).detach())
    opt_π1.zero_grad(); loss_π1.backward(); opt_π1.step()
    
    # Actor 2
    loss_π2 = -mean(log_prob_2 * A_t^(2).detach())
    opt_π2.zero_grad(); loss_π2.backward(); opt_π2.step()
    
    # Critic 1
    loss_V1 = mean((V1(s_t^(1)) - R̂_t.detach())²)
    opt_V1.zero_grad(); loss_V1.backward(); opt_V1.step()
    
    # Critic 2
    loss_V2 = mean((V2(s2_agg) - R̂_t.detach())²)
    opt_V2.zero_grad(); loss_V2.backward(); opt_V2.step()
    
    # === 日志 ===
    log: episode_reward, loss_V1, loss_V2, loss_π1, loss_π2
```

---

## 9. 文件结构

```
src/rl/
├── networks.py         # π1, π2, V1, V2 的网络定义
├── state_builder.py    # 从环境提取 s_t^(1), s_{t,i}^(2) 的逻辑
├── env.py              # RL 环境封装（wrap CAPA pipeline）
├── trainer.py          # 训练循环（Section 8 的实现）
├── evaluate.py         # 评估（无探索，用 argmax/greedy）
├── utils.py            # discount return 计算、归一化等工具函数
└── visualize.py        # 训练曲线绘制
```

### 9.1 networks.py 要求

```python
class BatchSizeActor(nn.Module):
    """π1: 输入 s_t^(1), 输出 |A_b| 维 softmax 概率分布"""

class CrossOrNotActor(nn.Module):
    """π2: 输入 s_{t,i}^(2) (9-dim), 输出 sigmoid 概率 P(a=1)
    参数在所有 parcel 间共享"""

class StateValueCritic(nn.Module):
    """V1: 输入 s_t^(1) (4-dim), 输出标量 value"""

class ConditionalValueCritic(nn.Module):
    """V2: 输入 s_t^(2)_aggregated (9-dim, mean-pooled), 输出标量 value
    a_t^(1) 已包含在 s_t^(2) 的 Δb 分量中"""
```

### 9.2 state_builder.py 要求

```python
def build_stage1_state(env) -> np.ndarray:
    """从环境构建 s_t^(1)，返回 shape (4,) 的数组"""

def build_stage2_states(env, unassigned_parcels, batch_size) -> List[np.ndarray]:
    """为每个未分配 parcel 构建 s_{t,i}^(2)，返回 List of shape (9,) 数组"""

def aggregate_stage2_states(states: List[np.ndarray]) -> np.ndarray:
    """对 per-parcel 状态做 mean-pooling，返回 shape (9,) 的聚合状态"""
```

### 9.3 env.py 要求

RL 环境必须 wrap 现有的 CAPA pipeline：

```python
class RLCAPAEnv:
    """
    RL-CAPA 环境。
    
    与 CAPA 共享同一套数据加载、courier/parcel 生成、时间推进、
    CAMA 匹配、DAPA 拍卖的逻辑，全部通过 import 调用。
    
    RL 只替换两个决策点：batch size 和 cross-or-not。
    """
    
    def reset(self) -> dict:
        """重置环境，返回初始状态"""
    
    def get_stage1_state(self) -> np.ndarray:
        """返回当前 s_t^(1)"""
    
    def apply_batch_size(self, batch_size: int):
        """按选定的 batch size 推进时间，积累 parcel"""
    
    def run_local_matching(self) -> Tuple[MatchingResult, List[Parcel]]:
        """调用 CAMA，返回本地匹配结果和未分配 parcel 列表"""
    
    def get_stage2_states(self, unassigned: List[Parcel]) -> List[np.ndarray]:
        """返回每个未分配 parcel 的 s_{t,i}^(2)"""
    
    def apply_cross_decisions(self, decisions: Dict[Parcel, int]) -> float:
        """
        按决策分流 parcel：
        - a=1 的进入拍卖池，调用 DAPA
        - a=0 的 defer 到下一 batch
        返回 R_t（平台级总收益）
        """
    
    def is_done(self) -> bool:
        """是否所有 parcel 处理完毕"""
```

---

## 10. 超参数

| 参数 | 建议值 | 说明 |
|------|--------|------|
| γ (discount) | 0.9 | 论文已指定 |
| lr_actor | 0.001 | 两个 actor 相同 |
| lr_critic | 0.001 | 两个 critic 相同 |
| optimizer | Adam | 替换原来的 RMSprop（actor-critic 中 Adam 更稳定） |
| hidden_dim | 128 | 两层 MLP |
| num_episodes | 根据收敛情况调整 | 先用 500 做 smoke test |
| h_L (min batch) | 10 | 论文已指定 |
| h_M (max batch) | 20 | 论文已指定 |
| entropy_coeff | 0.01 | 可选，防止策略过早收敛 |
| max_grad_norm | 0.5 | 梯度裁剪 |

---

## 11. 可视化要求

训练过程必须记录并绘制以下曲线：

| 曲线 | 说明 |
|------|------|
| Episode Reward (R_t) | 每 episode 的平台总收益 |
| L_V1 | Critic 1 的 loss |
| L_V2 | Critic 2 的 loss |
| Policy Loss π1 | Actor 1 的 policy gradient loss |
| Policy Loss π2 | Actor 2 的 policy gradient loss |
| Batch Size Distribution | 训练过程中 π1 选择的 batch size 分布变化 |
| Cross Rate | 训练过程中被 π2 送入拍卖池的 parcel 比例 |

所有曲线使用 sliding window 平滑（window=50）。

---

## 12. 评估模式

评估时：
- π1 用 argmax（选概率最大的 batch size）
- π2 用阈值 0.5（P(a=1) > 0.5 则跨平台）
- 不做梯度更新
- 记录 TR, CR, BPT 三个指标（与 CAPA 对齐）

---

## 13. 实现检查清单

在每个步骤完成后逐条验证：

### 13.1 环境层
- [ ] env.py 通过 import 调用 CAPA 的 CAMA、DAPA 模块
- [ ] env.reset() 正确初始化所有状态
- [ ] env.apply_batch_size() 按 a_t^(1) 秒推进时间并积累 parcel
- [ ] env.run_local_matching() 调用 CAMA 并返回正确的未分配列表
- [ ] env.apply_cross_decisions() 对 a=1 的 parcel 调用 DAPA
- [ ] R_t 的计算与论文 Eq.5 一致
- [ ] deferred parcel 正确保留到下一个 batch

### 13.2 状态层
- [ ] s_t^(1) 是 4 维向量
- [ ] s_{t,i}^(2) 是 9 维向量
- [ ] v_τi 计算正确（parcel 价格减估计服务成本）
- [ ] ū_t^Loc 正确反映 courier 剩余容量
- [ ] |C_t^Cross| 正确聚合所有合作平台
- [ ] b̄_t^Cross 维护了滑动平均
- [ ] Δb 等于 a_t^(1)
- [ ] 所有特征做了归一化

### 13.3 网络层
- [ ] π1 输出 softmax 概率，维度 = |A_b|
- [ ] π2 输出 sigmoid 概率，每个 parcel 独立，共享参数
- [ ] V1 输入 4 维，输出标量
- [ ] V2 输入 mean-pooled 的 s_t^(2)（9维），输出标量
- [ ] 4 个网络各有独立 optimizer

### 13.4 训练层
- [ ] advantage 计算正确：A1 = V2 - V1, A2 = R̂_t - V2
- [ ] advantage 在送入 actor 时做了 detach
- [ ] log_prob 计算正确（π2 是所有 parcel 的 log_prob 之和）
- [ ] discounted return R̂_t 的计算是从 episode 末尾向前累积
- [ ] 4 个 loss 分别反传，不合并
- [ ] 训练曲线在记录

### 13.5 评估层
- [ ] 评估模式下无梯度更新
- [ ] π1 用 argmax
- [ ] π2 用 0.5 阈值
- [ ] 输出 TR, CR, BPT 与 CAPA 的评估方式一致

---

## 14. 常见错误及排查

| 错误现象 | 可能原因 | 排查方式 |
|----------|----------|----------|
| reward 始终为 0 | CAMA/DAPA 未正确调用 | 打印 M_lo, M_cr 检查匹配结果 |
| V1 loss 不降 | R̂_t 计算错误或未归一化 | 打印 R̂_t 分布 |
| π1 只选一个动作 | entropy 坍塌 | 加 entropy bonus |
| π2 全选 0 或全选 1 | advantage 信号太弱 | 检查 V2 是否正确接收 s_t^(2) |
| V2 loss 远大于 V1 | V2 输入维度或聚合方式有误 | 打印 V2 的输入 shape |
| 训练不收敛 | 学习率过大或梯度爆炸 | 加 grad clipping，降 lr |

---

## 15. 与 CAPA 环境流程的对齐

```
CAPA (Algorithm 1):                    RL-CAPA:
─────────────────────                  ─────────────
1. 固定 Δb                             1. π1 选择 a_t^(1) = Δb
2. 按 Δb 积累 parcel batch             2. 按 a_t^(1) 积累 parcel batch  [相同]
3. 调用 CAMA → M_lo, ΔΓ               3. 调用 CAMA → M_lo, ΔΓ        [相同]
4. 全部 ΔΓ 进入拍卖池                   4. π2 逐 parcel 决策 cross-or-not
5. 调用 DAPA → M_cr                    5. 只有 a=1 的进入 DAPA         [部分]
6. 计算收益                             6. a=0 的 defer 到下一 batch     [新增]
                                       7. 计算 R_t                     [相同]
```

这个对齐关系是实现的核心约束。环境的 step 函数必须严格按照此流程执行。