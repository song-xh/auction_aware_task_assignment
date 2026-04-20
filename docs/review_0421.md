请围绕以下目标开展代码审查与实验排查：

### Goal A：验证指标口径是否统一

确保 `BaseGTA` / `ImpGTA` / `CAPA` / `RL-CAPA` 在当前实验框架中满足：

- **TR 口径统一**：全部按当前论文的 local-platform revenue 定义统一评估；
- **CR 口径统一**：全部按相同 episode / batch 结束后的最终完成率统计；
- **BPT 口径统一**：全部按当前框架定义的 batch processing time 统计，而不是使用 GTA 原文的 response time。

### Goal B：定位 TR 异常偏高的根源

重点排查 GTA baseline 是否存在以下问题：

- inner revenue 仍然沿用原论文的 `U_t = v_t`，未统一扣除 inner courier payment；
- cross revenue 误用 `fare - bid` 或 `fare - su`，而非 `fare - critical_payment`；
- `su_ij` 在 CPUL 环境中的适配方式错误，导致 outer-platform cost 被低估；
- 某些 parcel 被重复计入 revenue；
- `completed_flag` 与 `revenue > 0` 的逻辑不一致。

### Goal C：判断这是 bug 还是机制 trade-off

最终需要判断：

- 若 GTA 完成任务更少，但单任务平均净收益更高，则说明这是**真实 trade-off**；
- 若 GTA 的 payment / revenue 统计存在低估成本、重复计数、口径不统一，则说明这是**实现 bug**。

---

## 

对于任意算法，在统一评测口径下应满足：

\[
TR = \sum_{\tau \in \Gamma_L} rev(\tau)
\]

\[
CR = \frac{\#\text{completed parcels}}{\#\text{all local parcels}}
\]

因此：

\[
TR = N \cdot CR \cdot \overline{rev}_{completed}
\]

其中：

- \(N\)：总 parcel 数；
- \(CR\)：完成率；
- \(\overline{rev}_{completed}\)：已完成任务的平均净收益。

这意味着：

- **更高的 CR 不必然带来更高的 TR**；
- 若某方法更偏向挑选高净收益 parcel，则可能出现：
  - `CR` 更低，
  - 但 `TR` 更高。

因此需要拆开审查：

1. 是否 `avg_rev_per_completed` 在 GTA 中显著更高；
2. 是否这种更高来自合理的任务筛选；
3. 或者来自实现口径错误。

## Task 1：审查 BaseGTA / ImpGTA 的移植是否真的遵循统一协议

这是本任务的重中之重。

### 检查点 1.1：inner revenue 是否仍沿用 GTA 原文口径

请搜索所有 GTA baseline 相关代码中是否存在如下逻辑：

```python
profit += fare
revenue += fare
U_t = v_t
```

如果这是 GTA baseline 在主实验中的 inner 收益记账，则说明口径错误，必须改为：

```python
revenue += fare - zeta * fare
```

### 检查点 1.2：cross revenue 是否误用了 bid 或 su

请搜索所有 GTA baseline 中是否存在：

```python
revenue = fare - bid
revenue = fare - su
revenue = fare - min_dispatch_cost
```

若存在，则判定为主评测口径错误。应统一改为：

```python
revenue = fare - critical_payment
```

其中 `critical_payment` 必须是 AIM 最终支付值。

### 检查点 1.3：AIM 的 payment 是否正确记录为 second-lowest bid

对 GTA baseline，必须确认：

- winner = lowest bid platform
- payment = second-lowest bid (critical payment)
- 若 payment > fare，则应 reject 或 clip according to framework policy

请核对当前实现是否真的满足以上三点。

### 检查点 1.4：`su_ij` 是否正确适配到 CPUL 环境

[17] 原始 GTA 使用：

\[
su_{ij} = u_w \cdot (dis(l_t^s,l_w)+dis(l_t^s,l_t^d))
\]

而当前 CPUL 环境中：

- pick-up parcel 到达 pick-up location 即视为完成；
- courier 存在已有 schedule；
- 新 parcel 通过 schedule insertion 完成。

因此，请确认 GTA baseline 在 CPUL 中是否已将 `su_ij` 改写为：

\[
su_{ij}^{CPUL} = \min_{c\in C_i^{feas}(\tau)} u_c \cdot \Delta dist(c, \tau)
\]

其中：

- `C_i^{feas}(τ)`：平台 i 中所有满足 capacity / deadline / insertion feasibility 的 courier；
- `Δdist(c, τ)`：parcel 插入当前 schedule 后带来的增量路程。

若当前仍然使用原 GTA 的 source-destination task cost，则需报告并修正。

### 检查点 1.5：completion 定义是否与 CPUL 一致

CPUL 环境中，pick-up parcel 到达 pick-up location 即完成。请检查：

- GTA baseline 是否仍然沿用原 GTA 的“source-destination 全任务完成”定义；
- 若是，则必须统一改为 CPUL completion 定义。

否则会导致：

- CR 统计不一致；
- BPT 统计不一致；
- payment / cost 估计不一致。

---

## Task 2：审查 batch 推进逻辑是否统一

当前 CAPA / RL-CAPA 存在如下特性：

- 某些 parcel 在当前 batch 未分配成功时，会重新进入下一 batch 再尝试；
- 局部 matching 与 cross matching 是 batch 内推进的。

请重点检查 GTA baseline 在当前框架中是否存在以下问题：

### 问题 A：GTA 采用 immediate permanent decision

即 parcel 一到即立刻拒绝或分配，且不进入后续 batch；

### 问题 B：CAPA 采用 deferred retry decision

即 parcel 可在后续 batch 再次尝试。

如果两者并存，就必须确认最终统计时：

- 所有算法都在相同 episode 结束后统一统计 completed/rejected；
- 不允许 GTA 的 reject 在中途就提前计入最终失败，而 CAPA 的 deferred 直到后续 batch 才补完成。

请 Claude 检查：

- parcel 生命周期状态机是否统一；
- `deferred -> completed` 是否被 CR 正确计入；
- GTA 的 immediate reject 是否被错误地提前结算。