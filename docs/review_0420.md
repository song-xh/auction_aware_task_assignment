# review_0420

## 目标

为当前 **CPUL / CAPA / RL-CAPA** 实验框架补充并接入文献 **[17] Competition and Cooperation: Global Task Assignment in Spatial Crowdsourcing** 中的两类方法：

- **BaseGTA**
- **ImpGTA**

并完成如下工作：

1. **准确复现 [17] 的方法逻辑与匹配机制**，包括其平台级单层拍卖机制 **AIM**、BaseGTA 的贪心分配逻辑、ImpGTA 的预测窗口驱动决策逻辑。
2. **将 BaseGTA / ImpGTA 融入现有实验框架**，但要注意：
   - **保留其原始“匹配/竞价决策机制”**；
   - **不要保留其原文的独立 profit 统计口径作为主实验结果**；
   - **主实验中的收益、TR、CR、BPT、推进与评测逻辑必须与现有方法完全统一**。
3. 明确区分：
   - **“方法内部决策机制不同”**；
   - **“实验环境、收益记账方式、评测协议统一”**。
4. 在代码、配置、日志、实验输出中体现：
   - GTA 基线是 **ported baseline**，不是照搬原论文独立实验脚本；
   - 与现有 CAPA / RL-CAPA 的对比是 **公平对比**。

---

## 一、必须先理解并复核的文献方法要点

### 1.1 文献 [17] 的问题视角

[17] 的 GTA（Global Task Assignment）是 **平台级跨平台任务分配**：

- 决策者是 **platform**，不是 individual worker；
- 当 inner platform 无法服务任务时，会把任务发送给 outer platforms；
- outer platforms 以 **平台级 bidding** 的方式参与竞价；
- winner platform 再派自己的 worker 执行任务。

### 1.2 文献 [17] 的收益 / payment 核心定义

Codex 必须先核查并写入代码注释中的核心定义：

#### 任务对内平台的利润贡献（原文口径）

对于任务 \(t_j\)，[17] 定义 inner platform 的 profit contribution：

\[
U_{t_j}=
\begin{cases}
0, & \text{rejected}\\
v_{t_j}, & \text{served by an inner worker}\\
v_{t_j}-r_{ij}, & \text{served by an outer worker}
\end{cases}
\]

其中：

- \(v_{t_j}\)：任务 reward；
- \(r_{ij}\)：支付给 outer platform \(p_i\) 的 critical payment。

#### 最小可接受外部调度成本

[17] 原文定义：

\[
su_{ij}=u_w \cdot \Big(dis(l_t^s,l_w)+dis(l_t^s,l_t^d)\Big)
\]

表示 outer platform 派出 worker 服务该任务的最低可接受成本。

### 1.3 文献 [17] 的竞价机制 AIM

Codex 必须复核并实现下列机制，而不是随意改写：

- outer platforms 提交 bidding price；
- inner platform 选择 **最低 bid** 的平台作为 winner；
- 采用 **second-lowest bid** 作为 critical payment；
- payment 不应超过任务 reward；
- 机制要保留 [17] 的单层平台级 auction 特征，**不能替换为当前论文的 DLAM 双层 auction**。

### 1.4 BaseGTA 的逻辑

BaseGTA 是贪心基线：

- 新任务到达；
- inner platform 优先尝试本地分配；
- 若本地分配失败，则把任务发给 outer platforms；
- 只要 outer platform 存在可行 worker，就参与 bidding；
- 通过 AIM 选择 winner，winner platform 派 worker 执行。

### 1.5 ImpGTA 的逻辑

ImpGTA 在 BaseGTA 之上增加未来窗口 \(\Delta\tau\) 的预测驱动策略：

- 使用未来时间窗中的任务分布 / 预期收益；
- 内平台决定是否用 inner worker 服务当前任务；
- 外平台决定是否参加 bidding；
- 关注未来 supply-demand gap，避免 worker 被低价值任务占用。

Codex 必须识别：

- **ImpGTA 不是简单的静态阈值过滤器**；
- 它的本质是 **future-window guided dispatch / bidding policy**。

---

## 二、融入现有实验框架时的总原则

## 2.1 只允许“方法决策逻辑不同”，不允许“实验协议不同”

这是本次修改的最高优先级要求。

在接入 BaseGTA / ImpGTA 后，以下内容必须对所有方法统一：

- 同一数据流（parcel stream / courier state stream）；
- 同一道路网络与距离计算；
- 同一可行性检查；
- 同一批处理推进逻辑（若当前框架为 batch 驱动，则 GTA baseline 也按相同批次推进参与统计）；
- 同一收益记账方式；
- 同一指标定义：**TR / CR / BPT**；
- 同一日志、随机种子、配置管理方式。

### 不能出现的错误

1. **GTA baseline 仍沿用原论文自己的 Total Profit 口径作为主表结果**。
2. **GTA baseline 使用不同的环境推进方式，导致 BPT、CR 不可比**。
3. **直接把 [17] 的 task / worker 模型照搬，而绕过当前框架的 capacity、deadline、schedule 可行性检查**。
4. **将 [17] 的 AIM 替换成当前论文的 DLAM，却仍声称是 BaseGTA / ImpGTA baseline**。

---

## 三、BaseGTA / ImpGTA 的移植原则

## 3.1 保留的方法部分

Codex 在移植时，必须保留 [17] 的以下“方法内核”：

### BaseGTA 保留项

- inner-first greedy dispatch；
- 本地失败后 outer bidding；
- outer 平台只要存在可行 worker 即可参与；
- 平台级 AIM 单层竞价与 critical payment 规则。

### ImpGTA 保留项

- future-window \(\Delta\tau\)；
- 基于未来任务分布 / expected reward 的 inner decision；
- 基于未来任务分布 / expected reward 的 outer participation decision；
- AIM 单层竞价。

## 3.2 必须适配当前框架的部分

不能把 [17] 的 taxi-task 场景直接生搬硬套到 CPUL。必须适配如下部分：

### 适配项 A：任务实体映射

将 [17] 中的 task 映射到当前框架中的 **pick-up parcel**：

- \(v_t \leftrightarrow p_\tau\)；
- GTA 中的 task reward 统一映射为当前框架中的 parcel fare。

### 适配项 B：可行性检查统一

BaseGTA / ImpGTA 的 `LocalTaskAssign` 或 `feasible worker` 检查，必须统一调用当前框架中的 feasibility logic，而不是使用 [17] 的简化条件。

至少统一以下约束：

- capacity constraint；
- parcel deadline constraint；
- courier deadline / return constraint；
- schedule insertion feasibility；
- 当前框架已有的任何有效约束。

### 适配项 C：outer platform 最低可接受成本

由于 [17] 原文使用的是 source-destination 任务模型，而当前 CPUL 的 pick-up parcel 在 courier 到达 pick-up location 即视为完成，因此不能直接用原式：

\[
su_{ij}=u_w \cdot \Big(dis(l_t^s,l_w)+dis(l_t^s,l_t^d)\Big)
\]

在当前框架中，建议改写为：

\[
su^{CPUL}_{ij} = \min_{c\in\mathcal{C}^{feas}_i(\tau)} u_c \cdot \Delta dist(c,\tau)
\]

其中：

- \(\mathcal{C}^{feas}_i(\tau)\)：platform \(p_i\) 中对 parcel \(\tau\) 可行的 courier 集合；
- \(\Delta dist(c,\tau)\)：将 parcel \(\tau\) 插入 courier \(c\) 当前 schedule 后带来的增量路程；
- \(u_c\)：courier 的单位距离成本（若当前框架无此参数，则需要统一设定并在配置中管理）。

该定义必须做到：

- 与 [17] 的“最低可接受 dispatch 成本”思想一致；
- 与当前框架的 schedule insertion 模型一致；
- 与当前的 revenue 记账兼容。

---

## 四、收益计算与主实验指标统一规则（最高优先级）

这是本任务最关键的修改点。Codex 需要重点审查并避免口径混乱。

## 4.1 主实验中不得直接使用 [17] 原始 Total Profit 作为最终对比结果

原因：

- [17] 对 inner-served task 的收益直接记为 \(v_t\)；
- 当前论文对 inner-served parcel 的 revenue 是 \(p_\tau - Rc(\tau,c)\)；
- 若直接使用 [17] 原始 profit，会导致 GTA baseline 在 inner tasks 上不扣本地 courier payment，从而与 CAPA / RL-CAPA **不公平**。

## 4.2 主实验统一收益定义

对 **所有方法**（包括 CAPA / RL-CAPA / BaseGTA / ImpGTA），统一按当前论文的 local-platform revenue 口径记账：

对于本地平台的一个 parcel \(\tau\)：

\[
R(\tau)=
\begin{cases}
0, & \tau \text{ rejected}\\
p_\tau - Rc(\tau,c), & \tau \text{ served by an inner courier } c\\
p_\tau - Pay^{out}(\tau), & \tau \text{ served by an outer platform / cross courier}
\end{cases}
\]

并统一计算：

\[
TR=\sum_{\tau\in\Gamma_L}R(\tau)
\]

## 4.3 GTA baseline 在统一收益口径下的具体实现

### 情况 A：BaseGTA / ImpGTA 将 parcel 分给 inner courier

统一记为：

\[
R^{main}_{inner}(\tau)=p_\tau - Rc(\tau,c)
\]

若当前框架按原论文设置：

\[
Rc(\tau,c)=\zeta p_\tau
\]

则：

\[
R^{main}_{inner}(\tau)=(1-\zeta)p_\tau
\]

### 情况 B：BaseGTA / ImpGTA 将 parcel 分给 outer platform

保留 [17] 的 AIM payment 机制，设最终 outer payment 为 \(r_{ij}\)，则统一记为：

\[
R^{main}_{cross}(\tau)=p_\tau-r_{ij}
\]

其中：

- \(r_{ij}\) 必须来自 GTA baseline 自己的 AIM；
- **不能替换成当前论文 DLAM 的 \(p'(\tau,c)\)**；
- 若 \(r_{ij}>p_\tau\)，则该 parcel 应视为 reject 或 zero-revenue，不能记为负盈利接单。

## 4.4 辅助统计（可选，但建议保留）

为了验证 baseline 移植正确性，允许保留 GTA-native statistics 作为辅助日志或附录输出，例如：

- native profit（按 [17] 原口径）；
- acceptance ratio；
- payment ratio；
- response time。

但这些 **不得替代主实验的 TR / CR / BPT**。

---

## 五、BPT、CR 与推进逻辑的统一要求

## 5.1 CR 必须统一

主实验中所有方法统一使用当前论文的 **Completion Rate (CR)**：

\[
CR = \frac{\#\text{completed local parcels}}{\#\text{all local parcels}}
\]

禁止使用 [17] 原文的 `Acceptance Ratio = accepted outer tasks / all dispatched outer tasks` 直接替代 CR。

## 5.2 BPT 必须统一

主实验中所有方法统一使用当前框架的 **Batch Processing Time (BPT)**：

- 若当前实验是 batch-based，则 GTA baseline 也必须在同样的 batch 粒度下运行与计时；
- 不允许继续使用 [17] 原文单任务 response time 作为主对比时间指标。

## 5.3 推进逻辑必须统一

Codex 必须审查当前实验框架的核心推进逻辑，例如：

- parcel arrival 如何进入 batch；
- batch 边界如何判定；
- local assignment 与 cross assignment 在一个 batch 内的调用顺序；
- 未完成 / 未分配任务如何进入下一个 batch；
- RL-CAPA 的 batch decision 如何与 baseline 的固定推进兼容。

要求：

- BaseGTA / ImpGTA 作为 baseline **不得私自改动全局实验推进方式**；
- 它们应该只是当前 batch 内的一个 `assignment policy / matching policy`；
- 同一批输入流下，不同方法只是在“如何做 inner dispatch / outer bidding / cross assignment”上不同。

---

## 六、建议 Codex 审查的代码步骤

## Step 1：梳理当前实验框架的最小闭环

Codex 先不要急于改代码，先输出一份审查结果，回答以下问题：

1. 当前主实验入口在哪个脚本？
2. batch 是如何形成的？
3. local assignment 的接口是什么？
4. cross-platform assignment 的接口是什么？
5. revenue / TR 在哪里记账？
6. CR / BPT 在哪里统计？
7. feasibility check 的统一入口在哪里？
8. RL-CAPA 和 CAPA 共用哪些环境函数？

### 检查点

- 是否存在分散记账逻辑；
- 是否不同方法各自维护一套收益统计；
- 是否 BPT 在不同方法中计时口径不同；
- 是否 cross payment 在不同方法中使用了不同数据结构且缺少统一封装。

---

## Step 2：抽象统一接口

Codex 需要把 baseline 接入点抽象为统一策略接口，例如：

- `assign_batch_with_policy(policy_name, batch_state, env_state)`
- `compute_outer_payment(policy_name, candidate_platforms, parcel, env_state)`
- `record_assignment_outcome(parcel, assignment_result, metric_state)`

### 检查点

- 不同 policy 是否共享同一个 metrics recorder；
- 不同 policy 是否共享同一个 feasibility check；
- 不同 policy 是否共享同一个 batch driver。

---

## Step 3：实现 GTA-ported baseline

Codex 需要接入两个 baseline：

- `BaseGTAAdapter`
- `ImpGTAAdapter`

要求：

1. 适配当前 parcel / courier / platform 数据结构；
2. 调用当前 schedule insertion 与 feasibility 函数；
3. 保留 AIM payment 机制；
4. 支持输出 native GTA debug stats 与 unified main metrics。

### 检查点

- `AIM winner` 是否真的是 lowest bid；
- `critical payment` 是否真的是 second-lowest bid；
- 是否对 `payment > parcel fare` 做了 reject 保护；
- `su^{CPUL}_{ij}` 是否是基于增量路程而不是错误地按直线距离乱算；
- ImpGTA 的 future-window logic 是否真的使用预测窗口，而不是写成一个静态阈值。

---

## Step 4：统一收益记账模块

Codex 需要新增或重构一个统一记账模块，例如：

- `UnifiedRevenueRecorder`
- `MetricEvaluator`

该模块负责：

- 对 inner assignment 一律记 \(p_\tau-Rc(\tau,c)\)；
- 对 cross assignment 一律记 \(p_\tau-Pay^{out}(\tau)\)；
- 对 reject 记 0；
- 汇总 TR / CR / BPT。

### 检查点

- 是否仍有某些 baseline 绕过该 recorder 自己记 profit；
- 是否存在“inner 不扣 payment、outer 扣 payment”的不对称逻辑；
- 是否同一个 parcel 被重复计入收益；
- 是否 task/parcel 在重试进入下一 batch 时被重复统计。

---

## Step 5：统一日志与输出结构

建议所有方法输出统一字段：

- `method_name`
- `total_revenue_tr`
- `completion_rate_cr`
- `batch_processing_time_bpt`
- `num_local_completed`
- `num_cross_completed`
- `num_rejected`
- `total_outer_payment`
- `native_gta_profit`（仅 GTA baseline 可选）
- `native_acceptance_ratio`（仅 GTA baseline 可选）

### 检查点

- 主表使用的字段是否只有统一指标；
- debug 字段是否与主表字段混淆；
- 是否能够从日志中单独复核 inner / cross / reject 三类贡献。

---

## 七、建议 Codex 进行的测试点

## 7.1 单元测试：收益记账正确性

### Test A：inner assignment

输入：

- parcel fare = 10
- \(\zeta=0.3\)
- inner courier 成功接单

预期：

- revenue = 7
- CR += 1 completed
- outer payment = 0

### Test B：outer assignment with AIM

输入：

- parcel fare = 10
- outer platform bids = {5.2, 6.1, 7.4}
- lowest bid winner = 5.2
- payment = second-lowest = 6.1

预期：

- winner 为第一个平台
- recorded revenue = 3.9
- 不允许误记为 4.8（错误地用 lowest bid 结算）

### Test C：outer payment exceeds fare

输入：

- parcel fare = 10
- valid bids = {10.5, 11.0}

预期：

- 该 parcel reject 或 zero-revenue
- 不得记为负收益接单

---

## 7.2 单元测试：AIM 正确性

### Test D：winner/payment 规则

验证：

- winner == argmin(bid)
- payment == second_min(bid)
- 当只有一个外平台参与时，是否有合理 fallback 逻辑，并且不会超过 fare

### Test E：bid 约束

验证：

- outer platform bid 不小于 \(su^{CPUL}_{ij}\)
- 若无可行 courier，则该平台不得参与 bidding

---

## 7.3 单元测试：ImpGTA 的 future-window 决策

### Test F：future window 高负载

构造未来窗口任务很多、预期奖励高的场景：

预期：

- inner platform 不应轻易让当前低价值任务占用 inner courier；
- outer platform 对低收益任务的参与率下降。

### Test G：future window 低负载

构造未来窗口空闲场景：

预期：

- ImpGTA 行为接近 BaseGTA；
- outer 平台参与率提升。

---

## 7.4 集成测试：主实验协议统一

### Test H：同一 batch、不同 policy 的输入一致性

检查：

- 在同一 seed 下，不同 policy 接收到的 parcel batch 是否完全一致；
- inner / outer courier pool 的初始状态是否一致；
- BPT 计时边界是否一致。

### Test I：主指标统一来源

检查：

- CAPA / RL-CAPA / BaseGTA / ImpGTA 的 TR 是否全部来自同一个 recorder；
- CR、BPT 是否全部由同一 evaluator 统计；
- 没有某个 baseline 额外走自己的独立统计代码。

---

## 八、建议 Codex 输出的审查结论格式

Codex 不要只改代码，必须同步输出一份审查报告，至少包含：

### 8.1 方法层面

- [17] 的 BaseGTA / ImpGTA / AIM 是否被正确识别与实现；
- 当前 CPUL 环境与 [17] 场景的关键差异是什么；
- 哪些地方保留原方法，哪些地方做了场景适配。

### 8.2 评测层面

- 主实验是否真正做到“只换匹配机制，不换评测协议”；
- 收益/TR 的记账口径是否对所有方法一致；
- BPT / CR 是否对所有方法一致。

### 8.3 风险层面

列出仍可能不公平或不严谨的点，例如：

- `u_c` 的设定是否影响 GTA baseline；
- ImpGTA 的预测模块是否需要单独训练或简化；
- GTA baseline 在 batch 环境中的行为是否会因环境差异偏离原论文。

---

## 九、推荐的修改步骤（实际执行顺序）

1. **先审查，不改代码**：梳理当前实验入口、收益统计、可行性检查、batch driver。
2. **抽象统一 recorder / evaluator**：把 TR / CR / BPT 统一到一个模块。
3. **接入 BaseGTAAdapter**：先实现最简单 greedy baseline。
4. **完成 AIM 单层 auction**：确保 winner/payment 规则正确。
5. **完成 ImpGTAAdapter**：引入 future-window decision logic。
6. **做单元测试**：先验证收益统计与 payment。
7. **做集成测试**：验证 batch 输入与主指标统一。
8. **输出审查报告**：说明哪些是 faithful port，哪些是 CPUL adaptation。
9. **最后再跑正式实验**。

---

## 十、最终验收标准

若 Codex 完成后，必须满足以下标准：

### A. 方法正确性

- BaseGTA / ImpGTA / AIM 都被正确实现；
- GTA baseline 保留平台级单层 auction；
- ImpGTA 真的使用 future-window 信息。

### B. 公平性

- CAPA / RL-CAPA / BaseGTA / ImpGTA 使用同一个环境推进；
- 同一套 feasibility check；
- 同一套 TR / CR / BPT 统计。

### C. 收益口径统一

- inner assignment：统一记 \(p_\tau-Rc(\tau,c)\)
- outer assignment：统一记 \(p_\tau-Pay^{out}(\tau)\)
- reject：统一记 0
- 不允许某个 baseline 保留自己独立的主收益定义。

### D. 可复核性

- 日志中可拆分 inner / outer / reject 三类结果；
- 可复核 outer payment 是否来自 AIM；
- 可复核 GTA-native 辅助统计与 unified main metrics。

---

## 十一、给 Codex 的一句话总要求

> 将文献 [17] 的 BaseGTA 和 ImpGTA 作为 **faithful but CPUL-adapted baselines** 接入现有实验框架；保留其原始匹配与 AIM 竞价机制，但统一使用当前框架的可行性检查、batch 推进和 **TR / CR / BPT** 评测协议；确保主实验中不同方法的差异仅体现在 **assignment / bidding policy**，而不体现在收益记账口径、时间统计边界和实验推进逻辑上。
