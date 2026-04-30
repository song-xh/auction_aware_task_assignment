下面这份可以直接保存为 `review_ramcom.md`。我依据 RamCOM 原文的算法说明：RamCOM 是 COM 问题中的 randomized cross online matching，用随机阈值保留高价值请求给内部工人，并对外部匹配使用最大期望收益支付；原文给出了 (\theta=\lceil\ln(\max(v_r)+1)\rceil)、均匀随机采样 (k)、阈值 (e^k)、最大期望收益 (E(v_r^0,W)=(v_r-v_r^0)\cdot pr(v_r^0,W)) 等机制。当前 CPUL 稿件中，RamCOM 已作为 baseline，并与 CAPA/RL-CAPA 使用统一的 TR、CR、BPT 指标进行比较。

~~~markdown
# review_ramcom.md

# RamCOM 适配 CPUL 实验框架的复现与审查任务书

## 0. 目标

本任务用于审查、补全和规范化 RamCOM baseline 在 CPUL（Cross-Platform Urban Logistics）实验框架中的复现实现。

核心原则：

1. 只保留 RamCOM 的“决策机制”：
   - 随机价值阈值；
   - 高价值包裹优先尝试本地 courier；
   - 低价值包裹或本地不可行包裹进入跨平台外部 courier 决策；
   - 外部分配通过最大期望收益选择 outer payment；
   - 按接受概率模拟外部 courier 是否接受；
   - 在接受集合中选择一个外部 courier 完成分配。

2. 不复刻 RamCOM 原文中的简化可行性、简化收益和简化实验统计逻辑。

3. 接入 CPUL 后，以下部分必须与当前论文实验框架对齐：
   - parcel/courier/platform 数据结构；
   - 路网距离、路径插入、容量、deadline、courier schedule 等可行性判断；
   - 本地收益、跨平台收益、总收益 TR 的计算；
   - 完成率 CR 的计算；
   - 批处理时间 BPT 的统计；
   - batch 输入、随机种子、重复实验、日志保存方式。

4. RamCOM 不应调用 CAPA 的动态阈值策略、DAPA 双层拍卖、FPSA/RVA、RL-CAPA 的 DDQN 或 actor-critic 模块。

---

## 1. 原始 RamCOM 的算法机制总结

### 1.1 原始问题映射

RamCOM 原文解决的是 Cross Online Matching, COM 问题。基本对象如下：

| 原始 COM/RamCOM 对象 | 含义 |
|---|---|
| request `r` | 动态到达的空间众包请求 |
| request value `v_r` | 请求完成后平台可获得的价值 |
| inner workers `W_in` | 目标平台自身工人 |
| outer workers `W_out` | 其他平台可借用工人 |
| outer payment `v_r^0` | 目标平台支付给外部工人的报酬 |
| revenue by inner worker | `v_r` |
| revenue by outer worker | `v_r - v_r^0` |

RamCOM 的目标不是做双层拍卖，而是在在线到达的请求中决定：
- 是否使用本地工人；
- 是否使用外部工人；
- 外部工人应支付多少；
- 外部工人是否接受；
- 最终匹配对象是谁。

### 1.2 原始 RamCOM 的默认/内生决策参数

只列出 RamCOM 决策机制中明确存在的默认/内生参数，不引入额外实验参数。

| 参数 | 原文机制 | 说明 |
|---|---|---|
| `max(v_r)` | 所有请求价值的最大值 | 用于计算随机阈值范围 |
| `theta` | `ceil(ln(max(v_r) + 1))` | 随机阈值上界 |
| `k` | 从 `{1, ..., theta}` 中以 `1/theta` 概率均匀随机采样 | 控制高价值请求阈值 |
| `threshold` | `exp(k)` | 若 `v_r > exp(k)`，优先尝试本地工人 |
| outer payment domain | `0 < v_r^0 <= v_r` | 外部支付不能超过请求价值 |
| expected revenue | `E(v_r^0, W) = (v_r - v_r^0) * Pr(v_r^0, W)` | 外部分配时最大化期望收益 |
| acceptance sampling | 对每个外部工人采样 `x ~ U(0,1)`，若 `x <= pr(v_r^0, w)` 则视为接受 | 原文中的外部接受模拟 |
| high-value local assignment | 对满足条件的本地工人随机选择一个 | RamCOM Algorithm 3 中为 random assign |

注意：
- 原文没有给出固定 random seed。
- 原文没有给出 batch size，因为 RamCOM 是 online 逐请求处理算法。
- 原文没有 FPSA/RVA、sharing rate `mu_1/mu_2`、CAPA threshold、RL 训练超参数。
- 原文 RamCOM 外部支付估计调用已有最大期望收益估计算法；若当前项目中使用离散搜索或网格搜索，这是 CPUL 适配实现细节，不是 RamCOM 原文默认参数。
- 原文 DemCOM 中有 Monte Carlo 最小外部支付估计的 `xi/eta` 精度参数，但 RamCOM 核心使用的是最大期望收益支付，不要把 DemCOM 的最小支付估计误当成 RamCOM 的必须参数。

---

## 2. CPUL 适配原则

### 2.1 对象映射

| RamCOM 原始对象 | CPUL 对象 | 适配说明 |
|---|---|---|
| request `r` | pick-up parcel `tau` | 每个待取件包裹视为一个在线请求 |
| value `v_r` | parcel fare `p_tau` | RamCOM 阈值判断只使用包裹 fare |
| inner workers `W_in` | local couriers `C_Loc` | 本地平台 courier |
| outer workers `W_out` | all cross-platform couriers `union(C_P)` | 将所有合作平台 courier 合并为外部 courier 池 |
| outer payment `v_r^0` / `v_r^e` | `ramcom_payment(tau, c)` | RamCOM 自己估计的外部支付，不走 DAPA |
| local assignment | `(tau, c_local)` | 使用 CPUL 本地可行性与收益计算 |
| cross assignment | `(tau, c_cross, P_owner, payment)` | 记录 courier 所属合作平台，但不进行平台层 RVA |
| reject | unassigned / failed parcel | 按统一 CR 统计未完成 |

### 2.2 必须与 CPUL 对齐的部分

RamCOM 只决定“走本地 / 走外部 / 拒绝”。以下逻辑必须使用 CPUL 当前实验框架已有函数或等价实现：

1. 可行性判断：
   - courier 是否空闲或可插入新 parcel；
   - capacity constraint；
   - parcel deadline；
   - courier return deadline；
   - drop-off/pick-up schedule；
   - route insertion；
   - service radius；
   - road-network distance；
   - one parcel only assigned once；
   - assignment immutable after commit。

2. 状态更新：
   - 一旦分配，更新 courier schedule；
   - 更新 courier remaining capacity；
   - 更新 parcel assigned/completed 状态；
   - 不允许同一 courier 在同一时间片被非法重复分配；
   - 不允许同一 parcel 被本地和外部同时分配。

3. 收益计算：
   - 不要直接使用原文 `Rev += v_r` 和 `Rev += v_r - v_r^0` 作为最终实验指标。
   - RamCOM 可以在内部用 `p_tau` 和 `payment` 做决策，但最终 TR 必须调用当前 CPUL 的统一收益函数。
   - 本地完成收益应与 CAPA/Greedy/RMA 一致，例如：
     - `local_revenue = compute_local_revenue(tau, c_local)`
     - 若论文实现采用 `p_tau - Rc(tau, c)`，则使用同一实现。
   - 跨平台完成收益应与 CPUL 的跨平台收益定义对齐，例如：
     - `cross_revenue = compute_cross_revenue(tau, c_cross, payment=ramcom_payment)`
     - 对 RamCOM 来说，`payment` 是最大期望收益步骤选出的外部支付，不是 DAPA 的 FPSA/RVA 支付。
   - 不要在 RamCOM 内部另写一套 TR/CR/BPT 统计公式。

4. 评估指标：
   - TR：调用统一 evaluator；
   - CR：调用统一 evaluator；
   - BPT：从每个 batch 开始到 RamCOM 对 batch 内所有 parcel 决策完成为止；
   - 多随机种子平均；
   - 保存 mean/std；
   - 与 CAPA/RL-CAPA/RMA/Greedy 使用完全相同的数据划分和默认实验参数。

---

## 3. 适配后的完整流程

### 3.1 高层流程

RamCOM 原文是逐请求在线算法。接入 CPUL batch 实验框架时，采用如下方式：

1. 外部实验仍按当前 CPUL 框架产生 batch。
2. 在每个 batch 内，RamCOM 按 parcel 的到达时间顺序逐个处理。
3. 对每个 parcel，执行 RamCOM 决策：
   - 若 `p_tau > exp(k)`，优先尝试本地 courier；
   - 若本地可行 courier 存在，随机选择一个本地 courier 并 commit；
   - 若本地不可行，或 `p_tau <= exp(k)`，进入外部 courier 分配流程；
   - 若外部可行 courier 为空，reject；
   - 若外部可行 courier 非空，估计最大期望收益对应的外部支付；
   - 基于外部支付与接受概率，采样外部 courier 是否接受；
   - 若接受集合非空，选择一个外部 courier 并 commit；
   - 否则 reject。

4. batch 结束后，将 RamCOM 的匹配结果交给统一 evaluator 计算 TR/CR/BPT。
5. 不对 RamCOM rejected parcel 使用 CAPA 的 defer-to-next-batch 策略，除非当前实验框架对所有 baseline 都统一采用 requeue 机制。若存在统一 requeue 机制，必须在日志中注明，并保证 CAPA/RL-CAPA/RMA/Greedy/RamCOM 一致。

### 3.2 推荐函数结构

Codex 应优先搜索当前项目中已有的实体类和函数，而不是新建重复逻辑。

建议接口：

```python
def run_ramcom_cpul(
    parcel_stream_or_batches,
    local_couriers,
    cooperating_platforms,
    config,
    rng,
    evaluator_hooks=None,
):
    """
    Return:
        assignments: list[Assignment]
        rejected: list[Parcel]
        trace: list[DecisionTrace]
    """
~~~

建议拆分函数：

```python
def compute_ramcom_threshold(parcels, rng):
    max_value = max(tau.fare for tau in parcels)
    theta = ceil(log(max_value + 1))
    k = rng.randint(1, theta)  # inclusive
    threshold = exp(k)
    return threshold, theta, k
def get_feasible_inner_couriers(tau, local_couriers, env_state):
    # Must call CPUL unified feasibility checker.
    # Do not implement simplified Euclidean/radius-only checks here.
    return [c for c in local_couriers if can_assign_parcel(tau, c, env_state)]
def get_feasible_outer_couriers(tau, cooperating_platforms, env_state):
    # Flatten couriers from all cooperating platforms.
    # Preserve platform owner id for logging and revenue attribution.
    candidates = []
    for P in cooperating_platforms:
        for c in P.couriers:
            if can_assign_parcel(tau, c, env_state):
                candidates.append((P, c))
    return candidates
def estimate_ramcom_outer_payment(tau, feasible_outer, config):
    """
    Estimate p_e = argmax_p (tau.fare - p) * Pr_accept(p, feasible_outer).

    Must satisfy:
        0 < p <= tau.fare

    Return:
        p_e, expected_revenue, accept_prob_set
    """
def sample_accepted_outer_couriers(tau, feasible_outer, payment, rng, config):
    accepted = []
    for P, c in feasible_outer:
        prob = estimate_worker_accept_prob(tau, c, payment, config)
        x = rng.random()
        if x <= prob:
            accepted.append((P, c, prob))
    return accepted
def select_outer_courier_ramcom(tau, accepted_outer, env_state, config):
    """
    Original DemCOM outer step says greedily assign one outer worker.
    In CPUL adaptation, use a deterministic greedy rule aligned with the framework:
        preferred: choose candidate with maximum CPUL cross net revenue;
        fallback: choose candidate with minimum insertion cost / detour;
        final tie-break: stable id order or seeded random choice.
    Must log which rule is used.
    """
def commit_ramcom_assignment(tau, courier, platform, mode, payment, env_state):
    """
    mode in {"local", "cross"}
    Must use CPUL's unified commit/update function.
    Do not directly mutate partial state unless existing code uses that style.
    """
```

------

## 4. 外部支付与接受概率的适配细节

### 4.1 最大期望收益支付

RamCOM 外部支付选择的核心公式：

```text
E(payment, feasible_outer) = (p_tau - payment) * Pr_accept(payment, feasible_outer)
payment_e = argmax_{0 < payment <= p_tau} E(payment, feasible_outer)
```

其中：

- `p_tau` 是 parcel fare；
- `payment` 是 RamCOM 给外部 courier 的支付；
- `Pr_accept(payment, feasible_outer)` 是外部 courier 集合接受该支付的概率。

### 4.2 支付搜索域

优先级：

1. 若当前代码中 fare 是整数或以最小货币单位离散化：
   - 搜索 `payment in {1, 2, ..., p_tau}`；
   - 复杂度与原文 `O(max(v_r))` 一致。
2. 若 fare 是浮点数：
   - 使用统一配置 `ramcom_payment_grid_size` 或 `payment_step`；
   - 这是 CPUL 实现细节，不是 RamCOM 原文默认参数；
   - 必须写入 config 和实验日志。
3. 更推荐的无额外参数方式：
   - 构造候选支付集合为所有可行外部 courier 的估计 reservation/payment threshold，再加上 `p_tau`；
   - 排序后逐个评估；
   - 这种方式避免任意网格步长，但需要已有函数能计算 courier 的最低接受支付或近似 reservation cost。

### 4.3 接受概率模型

Codex 必须先审查当前项目是否已经实现 worker acceptance probability。

优先级如下：

#### Priority A: 已有历史接受数据

如果已有历史服务记录或历史 payment acceptance 数据，则使用经验分布：

```text
pr(payment, c) = count(historical_accepted_payment_c <= payment) / count(history_c)
```

集合接受概率：

```text
Pr_accept(payment, W) = 1 - product_{c in W}(1 - pr(payment, c))
```

#### Priority B: 已有 courier reservation / bid / cost 估计函数

如果没有显式历史接受记录，但当前 CPUL 框架已有 courier 对 parcel 的成本、绕路代价、最低接受价格或 bid 估计函数，则：

```text
reservation = estimate_reservation_payment(tau, c)
pr(payment, c) = monotonic_acceptance(payment, reservation)
```

要求：

- 不调用 DAPA；
- 不执行 FPSA；
- 不执行 RVA；
- 只能把已有 courier-level 成本/偏好函数作为接受概率的输入特征；
- 必须在日志中标记为 `acceptance_model = reservation_based`.

可采用最简 monotonic fallback：

```text
if reservation <= 0:
    pr = 1
else:
    pr = min(1, max(0, payment / reservation))
```

这不是 RamCOM 原文默认参数，而是缺失真实接受数据时的 CPUL 复现假设。必须写入实验说明。

#### Priority C: 项目中已经有 RamCOM baseline 的旧实现

如果项目中已有旧版 RamCOM：

- 不要直接信任；
- 审查它是否错误使用 CAPA threshold、DAPA auction、双层平台竞价或原文简化收益；
- 保留其 acceptance probability 逻辑中合理的部分；
- 将可行性、收益、评估全部迁移到统一 CPUL 函数。

### 4.4 Tie-breaking

支付搜索中若多个 payment 的 expected revenue 相同：

1. 首选较小 payment，因为平台净收益更高；
2. 若 payment 相同，选择集合接受概率更高者；
3. 若仍相同，使用稳定排序或 seeded random；
4. 必须保证同一 seed 下结果可复现。

------

## 5. 适配后 RamCOM 的伪代码

```text
Input:
    Batches or stream of pick-up parcels Γ
    Local couriers C_Loc
    Cooperating platforms P = {P_1, ..., P_k}
    Unified CPUL environment/state
    Unified feasibility checker
    Unified revenue evaluator
    Random generator rng

Output:
    Matching plan M_ramcom
    Rejected parcels U_ramcom
    Decision traces T_ramcom

Step 0: Initialization
    M_ramcom = empty
    U_ramcom = empty
    trace = empty

Step 1: Compute RamCOM random threshold
    max_value = max(p_tau for tau in Γ)
    theta = ceil(ln(max_value + 1))
    k ~ Uniform({1, ..., theta})
    threshold = exp(k)

Step 2: Process each batch
    for each batch b:
        start timer for BPT
        sort parcels in b by arrival_time, then parcel_id

        for each parcel tau in sorted batch:

            if tau is already assigned:
                continue

            # RamCOM high-value branch
            if p_tau > threshold:
                inner_candidates = get_feasible_inner_couriers(tau, C_Loc, env_state)

                if inner_candidates is not empty:
                    c = random_choice(inner_candidates, rng)
                    commit local assignment (tau, c)
                    append trace:
                        parcel_id, branch="high_value_local",
                        threshold, p_tau, selected_courier=c.id
                    continue

                # high-value but no local feasible courier
                # falls through to outer assignment

            # RamCOM outer branch:
            # entered by low-value parcels or high-value parcels without local candidate
            outer_candidates = get_feasible_outer_couriers(tau, P, env_state)

            if outer_candidates is empty:
                reject tau
                append trace:
                    parcel_id, branch="outer_no_candidate",
                    threshold, p_tau, reason="no_feasible_outer"
                continue

            payment_e, expected_revenue, set_accept_prob = estimate_ramcom_outer_payment(
                tau, outer_candidates
            )

            if payment_e <= 0 or payment_e > p_tau:
                reject tau
                append trace:
                    parcel_id, branch="outer_invalid_payment",
                    payment_e, p_tau
                continue

            accepted_outer = sample_accepted_outer_couriers(
                tau, outer_candidates, payment_e, rng
            )

            if accepted_outer is empty:
                reject tau
                append trace:
                    parcel_id, branch="outer_rejected_by_all",
                    payment_e, set_accept_prob
                continue

            selected_platform, selected_courier = select_outer_courier_ramcom(
                tau, accepted_outer, env_state
            )

            commit cross assignment:
                tau assigned to selected_courier
                owner platform = selected_platform
                ramcom_payment = payment_e

            append trace:
                parcel_id, branch="outer_success",
                payment_e, expected_revenue,
                selected_platform, selected_courier

        end timer for BPT of this batch

Step 3: Evaluation
    Pass M_ramcom and rejected parcels to unified evaluator.
    Compute:
        TR, CR, BPT
    Save:
        assignments
        rejected
        trace
        random threshold theta/k/exp(k)
        seed
        acceptance model
        payment search setting
```

------

## 6. 代码审查任务清单

Codex 请按以下步骤逐步审查和修改。

### Step 1: 定位现有实现

执行代码搜索：

```bash
grep -R "RamCOM\|ramcom\|DemCOM\|COM" -n .
grep -R "compute.*revenue\|revenue\|TR\|CR\|BPT" -n .
grep -R "feasible\|can_assign\|insert\|deadline\|capacity" -n .
grep -R "DAPA\|CAMA\|FPSA\|RVA\|auction" -n .
```

需要确认：

- 是否已有 RamCOM 类或函数；
- 是否已有统一可行性检查函数；
- 是否已有统一收益计算函数；
- 是否已有统一 evaluator；
- 是否已有 random seed 管理；
- 是否已有 batch runner；
- 是否已有 baseline registry。

审查输出：

- 在 `review_ramcom_result.md` 中记录找到的文件路径、函数名和当前问题。
- 不要在未理解现有框架前重写大段代码。

### Step 2: 检查 RamCOM 是否误用 CAPA/DAPA/RL 逻辑

逐项确认：

-  RamCOM 没有调用 CAMA 的 dynamic utility threshold。
-  RamCOM 没有调用 DAPA。
-  RamCOM 没有执行 FPSA。
-  RamCOM 没有执行 RVA。
-  RamCOM 没有使用 RL-CAPA/DDQN/actor/critic。
-  RamCOM 没有使用 CAPA 的 defer low-quality parcel to auction pool 逻辑。
-  RamCOM 的本地/外部选择由随机阈值 `exp(k)` 和外部最大期望收益支付控制。
-  RamCOM 的跨平台部分只在 courier 层面决策，不在 platform 层面做二次拍卖。

若发现混用：

- 保留公共可行性函数和公共收益函数；
- 移除 CAPA/DAPA/RL 专属决策逻辑；
- 在 `review_ramcom_result.md` 中说明修改前后的差异。

### Step 3: 检查随机阈值实现

必须满足：

```python
theta = ceil(log(max_fare + 1))
k = rng.randint(1, theta)  # inclusive
threshold = exp(k)
```

审查点：

-  `max_fare` 来自本次实验 RamCOM 所处理的全部 parcels，而不是当前单个 batch，除非实验明确按 batch 重采样阈值。
-  推荐整次 run 只采样一次 `k`，与原始 RamCOM 对输入请求集合采样一次阈值一致。
-  所有随机数使用统一 `rng`，不要直接调用全局 `random` 或 `np.random`。
-  seed 相同则 `k`、threshold、结果一致。
-  日志保存 `theta`、`k`、`threshold`、`max_fare`。

### Step 4: 检查高价值本地分配分支

当 `p_tau > threshold`：

1. 调用统一 CPUL 可行性函数获取本地 feasible couriers。
2. 若存在本地 feasible couriers：
   - 原始 RamCOM 为 random assign；
   - 使用 seeded random choice；
   - commit local assignment；
   - 进入下一个 parcel。
3. 若不存在本地 feasible couriers：
   - 不 reject；
   - 转入外部 courier 流程。

审查点：

-  本地可行性检查包含 capacity/deadline/schedule/insertion/radius。
-  本地成功分配后更新 courier schedule。
-  本地成功分配后该 parcel 不再进入外部流程。
-  本地分配收益不在 RamCOM 内部用 `Rev += p_tau` 简化计算，而由统一 evaluator 计算。
-  本地选择使用 random，而不是 CAPA 的 max utility，除非配置中明确记录为 `local_selection=greedy_adapted`。

### Step 5: 检查低价值与本地不可行外部分支

进入外部分支的条件：

```text
p_tau <= threshold
OR
p_tau > threshold but no feasible local courier exists
```

外部分支流程：

1. 获取所有合作平台下的 feasible cross couriers。
2. 若为空，reject。
3. 若非空，估计最大期望收益支付 `payment_e`。
4. 用 `payment_e` 计算每个外部 courier 的接受概率。
5. 独立采样每个外部 courier 是否接受。
6. 若无人接受，reject。
7. 若至少一人接受，选择一个外部 courier 并 commit cross assignment。

审查点：

-  外部 candidates 是所有 cooperating platforms 的 courier flatten 结果。
-  保留 platform owner id，但不进行 platform-level bidding。
-  不调用 DAPA。
-  不调用 FPSA/RVA。
-  payment 必须满足 `0 < payment <= p_tau`。
-  若 payment 超过 fare，该 parcel 必须 reject 或将 payment clamp 前重新评估；不得产生负收益后仍成功分配。
-  接受概率必须在 `[0,1]`。
-  采样过程可复现。
-  cross assignment commit 后更新 cross courier schedule/capacity。
-  cross assignment 记录 `payment_e`，供统一收益函数计算跨平台收益。

### Step 6: 检查外部支付最大期望收益实现

需要实现或审查：

```python
def estimate_ramcom_outer_payment(tau, outer_candidates, config):
    best_payment = None
    best_expected_revenue = -inf
    best_accept_prob = None

    for payment in candidate_payments(tau, outer_candidates, config):
        accept_prob = aggregate_accept_prob(tau, outer_candidates, payment, config)
        expected_revenue = (tau.fare - payment) * accept_prob

        if expected_revenue better than current best:
            update best

    return best_payment, best_expected_revenue, best_accept_prob
```

审查点：

-  搜索域不包含 `payment <= 0`。
-  搜索域不包含 `payment > p_tau`。
-  expected revenue 使用 RamCOM 公式，而不是 CPUL 最终收益公式。
-  最终实验 TR 不直接使用 expected revenue。
-  tie-breaking 规则稳定。
-  payment 搜索设置写入 config/log。
-  若使用网格搜索，记录 grid size 或 step。
-  若使用 reservation 候选集合，记录 reservation 函数来源。

### Step 7: 检查接受概率模型

Codex 必须明确当前实现采用哪一种：

- `empirical_history`
- `reservation_based`
- `legacy_ramcom`
- `synthetic_monotonic_fallback`

审查点：

-  不允许没有说明地使用随机常数。
-  不允许直接令所有外部 courier 必然接受。
-  不允许直接令所有外部 courier 必然拒绝。
-  不允许使用 CAPA/RL-CAPA 的决策结果作为接受概率。
-  不允许使用 DAPA 最终赢家来反推接受概率。
-  必须记录每个 parcel 的 `payment_e`、集合接受概率、每个 sampled courier 的接受概率和采样结果。

### Step 8: 检查收益计算对齐

RamCOM 运行结束后只输出 matching，不独立作为最终成绩。

统一 evaluator 应计算：

```text
TR = sum local revenues + sum cross revenues
CR = completed parcels / total local pick-up parcels
BPT = batch matching elapsed time
```

审查点：

-  本地收益调用与 CAPA/Greedy/RMA 相同函数。
-  跨平台收益调用与 CAPA/Greedy/RMA 相同函数，但 payment 参数使用 RamCOM 的 `payment_e`。
-  不用原文 `Rev += v_r` 作为最终 TR。
-  不用原文 `Rev += v_r - v_r^0` 作为最终 TR，除非 CPUL 统一收益函数本身正是该形式。
-  rejected parcel 不计入 completed。
-  每个 completed parcel 只计一次 revenue。
-  若出现负 revenue，必须记录并检查 payment/cost 逻辑，不得静默吞掉。
-  TR/CR/BPT 的输出字段名与其他 baseline 一致。

### Step 9: 检查 batch 与 online 顺序

RamCOM 是 online 算法，CPUL 实验可能是 batch 框架。适配方式：

```text
for each batch:
    sort parcels by arrival time
    process parcels one by one using RamCOM decision mechanism
```

审查点：

-  batch 内按 arrival time 排序。
-  同 arrival time 用 parcel id 稳定排序。
-  不在 batch 内做全局最优匹配。
-  不使用 Hungarian/KM 替代 RamCOM 决策。
-  BPT 统计覆盖整个 batch 内 RamCOM 处理时间。
-  若当前实验框架将所有算法按 batch 运行，RamCOM 也必须按相同 batch 输入运行。
-  若当前框架支持 streaming 模式，RamCOM 可逐 parcel 运行，但评估聚合方式必须与其他 baseline 可比。

### Step 10: 检查状态一致性

每次 commit 后必须满足：

-  parcel 状态从 pending 变为 assigned/completed。
-  courier schedule 已插入该 parcel。
-  courier remaining capacity 已更新。
-  courier deadline 仍满足。
-  parcel deadline 仍满足。
-  同一 parcel 不会重复进入后续匹配。
-  同一 courier 不会违反 capacity/deadline/invariable constraints。
-  rejected parcel 状态明确记录。
-  所有状态变化可被 evaluator 读取。

------

## 7. 单元测试建议

### Test 1: 阈值可复现

构造 fares `[1, 2, 5, 10]`，固定 seed。

检查：

- `theta = ceil(log(10 + 1))`
- 同一 seed 下 `k` 一致；
- threshold 一致；
- 不同 seed 下允许不同。

### Test 2: 高价值本地可行

构造一个 parcel `p_tau > threshold`，且存在一个本地 courier 可行。

预期：

- branch = `high_value_local`
- 不进入外部流程；
- assignment mode = `local`
- revenue 由统一 evaluator 计算；
- trace 中存在 threshold/k/payment 字段，其中 payment 可为空。

### Test 3: 高价值本地不可行但外部可行

构造一个 parcel `p_tau > threshold`，本地 courier 全部不可行，外部 courier 可行。

预期：

- 进入 outer branch；
- 估计 `payment_e`；
- 若采样接受，则 mode = `cross`；
- 若采样拒绝，则 rejected；
- 不允许直接 reject 高价值本地不可行 parcel。

### Test 4: 低价值直接外部

构造一个 parcel `p_tau <= threshold`，即使本地 courier 可行，也应进入 outer branch。

预期：

- branch = `outer_by_low_value`
- 不调用本地 commit；
- 若外部成功接受，则 cross assignment；
- 这体现 RamCOM “低价值留给外部，高价值保留本地”的核心机制。

### Test 5: 外部无人可行

构造低价值 parcel，但所有外部 courier 均不可行。

预期：

- rejected；
- reason = `no_feasible_outer`；
- 不产生收益；
- 不更新任何 courier schedule。

### Test 6: payment bound

构造 fare 很小的 parcel。

检查：

- `0 < payment_e <= p_tau`
- 若找不到合法 payment，reject；
- 不得出现 `payment_e > p_tau` 后仍成功分配。

### Test 7: capacity/deadline 统一检查

构造一个从距离上可达、但 capacity 不满足的 courier。

预期：

- 不进入 feasible candidates；
- 本地/外部都不能绕过统一 feasibility checker。

### Test 8: no DAPA/FPSA/RVA dependency

用 mock 或 grep 检查 RamCOM 文件中不应出现：

```text
run_dapa
DAPA
FPSA
RVA
reverse_vickrey
first_price_sealed
dual_layer_auction
```

如果公共工具函数名称中包含 auction 但只用于计算已有 courier 成本，必须在 review 中说明原因，并避免调用完整拍卖流程。

------

## 8. 集成测试建议

### Small deterministic scenario

构造：

- 5 parcels；
- 2 local couriers；
- 2 cooperating platforms；
- each platform 2 cross couriers；
- 固定 seed；
- 固定 fare；
- 固定位置；
- 固定 deadlines。

检查输出：

-  每个 parcel 至多被分配一次。
-  每个 assigned parcel 有 mode。
-  cross parcel 有 owner platform 和 payment。
-  local parcel 没有 cross payment。
-  rejected parcel 有 reason。
-  所有 assigned parcel 均满足 CPUL feasibility。
-  evaluator 能输出 TR/CR/BPT。
-  重复运行同一 seed 结果完全一致。

### Baseline comparison smoke test

在同一小数据上运行：

```bash
python run_experiment.py --methods greedy,ramcom,capa --seed 42 --small
```

检查：

-  三个方法使用同一数据输入；
-  三个方法输出同样字段；
-  RamCOM 没有训练时间；
-  RamCOM BPT 统计正常；
-  RamCOM TR/CR 不为 NaN；
-  RamCOM trace 可读。

------

## 9. 日志字段要求

每次 RamCOM run 至少保存：

```json
{
  "method": "RamCOM-CPUL",
  "seed": 42,
  "theta": "...",
  "k": "...",
  "threshold": "...",
  "max_fare": "...",
  "acceptance_model": "...",
  "payment_search": "...",
  "num_parcels": "...",
  "num_local_couriers": "...",
  "num_cross_couriers": "...",
  "num_platforms": "...",
  "TR": "...",
  "CR": "...",
  "BPT": "...",
  "num_local_assignments": "...",
  "num_cross_assignments": "...",
  "num_rejected": "..."
}
```

每个 parcel 的 trace 至少保存：

```json
{
  "parcel_id": "...",
  "fare": "...",
  "arrival_time": "...",
  "deadline": "...",
  "threshold": "...",
  "branch": "high_value_local | outer_by_low_value | outer_after_local_fail | outer_no_candidate | outer_rejected_by_all | outer_success",
  "num_feasible_inner": "...",
  "num_feasible_outer": "...",
  "payment_e": "...",
  "expected_revenue": "...",
  "set_accept_prob": "...",
  "selected_courier": "...",
  "selected_platform": "...",
  "reject_reason": "..."
}
```

------

## 10. 常见错误与修复建议

### Error 1: RamCOM 直接调用 DAPA

问题：

- 这会把 RamCOM 变成 CAPA/DLAM 的变体，而不是原始 RamCOM baseline。

修复：

- RamCOM 外部分配只 flatten cross couriers；
- 不做平台间 RVA；
- 不做 courier 间 FPSA；
- 只用 payment + acceptance probability + greedy/select 机制。

### Error 2: RamCOM 使用 CAPA 动态 utility threshold

问题：

- RamCOM 原文阈值是 `exp(k)`，其中 `k` 从 `{1,...,theta}` 均匀随机采样；
- CAPA threshold 是基于 batch matching utility 的动态阈值，两者含义不同。

修复：

- 移除 CAPA threshold；
- 使用 RamCOM threshold；
- 日志记录 `theta/k/threshold`。

### Error 3: RamCOM 用原文 Rev 直接作为 TR

问题：

- 原文收益模型比 CPUL 简化；
- 与 CAPA/RL-CAPA/RMA/Greedy 对比不公平。

修复：

- RamCOM 只输出 matching 和 payment；
- TR 交给统一 evaluator。

### Error 4: 外部 acceptance probability 未实现，直接默认接受

问题：

- 这会显著抬高 RamCOM CR/TR；
- 违背 RamCOM 外部激励机制。

修复：

- 使用已有历史接受模型；
- 或使用 reservation-based monotonic fallback；
- 明确记录 `acceptance_model`。

### Error 5: low-value parcel 仍优先本地匹配

问题：

- 违背 RamCOM 的核心思想；
- RamCOM 正是为了避免低价值请求占用本地工人。

修复：

- 只有 `p_tau > threshold` 才尝试本地；
- `p_tau <= threshold` 直接进入外部分支。

### Error 6: 高价值本地失败后直接拒绝

问题：

- 原始 RamCOM 高价值但本地不可行时应进入外部分支。

修复：

- local candidates 为空时 fall through to outer branch。

### Error 7: 随机不可复现

问题：

- RamCOM 有随机 threshold、随机本地选择、随机外部接受；
- 若不用统一 seed，实验结果不可复查。

修复：

- 所有随机数来自同一个 `rng`；
- 保存 seed；
- 保存 trace。

------

## 11. 最终交付要求

Codex 完成后应输出或更新：

1. RamCOM CPUL baseline 实现代码。
2. 单元测试。
3. 小规模集成测试。
4. 实验日志字段。
5. `review_ramcom_result.md`，包括：
   - 修改了哪些文件；
   - RamCOM 原始机制如何保留；
   - 哪些部分与 CPUL 统一框架对齐；
   - 是否发现旧实现混用了 CAPA/DAPA/RL；
   - 接受概率模型采用哪一种；
   - payment 搜索方式；
   - 单元测试结果；
   - small experiment 结果；
   - 仍需人工确认的问题。

------

## 12. 最终审查标准

实现通过的最低标准：

-  RamCOM 使用 `theta/k/exp(k)` 随机阈值。
-  高价值 parcel 优先尝试 local courier。
-  低价值 parcel 直接进入 outer courier 决策。
-  高价值但 local 不可行时进入 outer courier 决策。
-  outer payment 通过最大期望收益估计。
-  outer courier 接受通过 probability sampling 或明确的 monotonic acceptance model。
-  RamCOM 不调用 DAPA/FPSA/RVA。
-  RamCOM 不调用 RL-CAPA。
-  可行性判断与 CPUL 统一。
-  收益计算与 CPUL 统一。
-  TR/CR/BPT 与其他 baseline 使用同一 evaluator。
-  所有随机过程可复现。
-  有完整 trace 便于排查异常结果。

```
::contentReference[oaicite:2]{index=2}
```

