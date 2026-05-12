Review 0512 — Exp-7 / Exp-8 检查（deadline 延迟与 deadline 噪声）
范围：experiments/run_chengdu_exp7_deadline_delay.py、experiments/run_chengdu_exp8_deadline_noise.py，及它们依赖的扰动注入、环境推进、RL-CAPA 状态/奖励链路、RamCOM baseline 链路。

结论概览：

扰动注入语义（exp7 用 observed_s_time，exp8 用 observed_d_time）正确实现，与论文设计一致。
真实 deadline / release time 仍用于环境 ground-truth 判定（到期、on-time 奖励），算法只看到 perceived 值 —— 这是两个实验能跑出 “模型感知偏差导致 TR 损失” 的关键。
存在 5 个需要关注的问题，其中 P1、P2 直接影响 exp7/exp8 的结论是否成立。
现有 state 没有显式的 disturbance 特征；是否需要重新训练取决于使用 rl-capa（每点重训）还是 rl-capa-infer（加载默认 checkpoint）。两条路线下面分别给出建议。
1. 扰动注入语义复核
1.1 Exp-7 delay（experiments/deadline_disturbance.py:17-33）
for task in tasks:
    setattr(task, "observed_s_time", get_true_release_time(task) + delay)
只改 observed_s_time，不改 d_time。任务真实到达时间不变。
prepare_chengdu_batch（env/chengdu.py:1475-1481）按 get_model_release_time 收纳任务 → 算法侧任务延迟出现。
eligible_tasks 过滤用 get_true_deadline（env/chengdu.py:1485-1488）→ 真实 deadline 不会因 observed_* 而被推迟，对应 “等效 slack 缩水”。
✓ 符合 exp7 设计：延迟越长，真实 slack 越小 → 两个模型 TR 都下降。

1.2 Exp-8 noise（experiments/deadline_disturbance.py:55-68）
ratio = float(noise_percent) / 100.0
for task in tasks:
    slack = max(0.0, get_true_deadline(task) - get_true_release_time(task))
    setattr(task, "observed_d_time", get_true_deadline(task) + round(slack * ratio))
正噪声：observed_d_time > true_d_time → 模型“以为还来得及”。
负噪声：observed_d_time < true_d_time → 模型“以为来不及”。
真实 release / deadline 不变；get_true_deadline 在批次到期判定（env/chengdu.py:1114, 1485, 1488）和 RamCOM 的 current_time 比较（baselines/ramcom.py:316）里仍是真值。
✓ 符合 exp8 设计：正向噪声损失 fare（任务真实过期），负向噪声损失部分收益（提前“放弃”或紧迫处理）。

1.3 算法侧 perceived 值的传递
legacy_task_to_parcel(task, use_observed_deadline=True) 默认走 get_model_deadline（env/chengdu.py:707-728）。
调用方：
rl_capa/env.py:136, 181（stage1/stage2 state 用 parcel.deadline）
baselines/common.py:141（RamCOM 与 MRA 可行性判断走该 parcel；其内部 is_feasible_local_match 用 parcel.deadline，即 observed 值）
CAPA is_feasible_local_match / is_deadline_feasible_by_geo 也均使用 parcel.deadline
⚠ baselines/ramcom.py:287 仅在 trace 写入 get_true_deadline（diagnostic），但实际可行性/插入决策已经从 legacy_task_to_parcel 拿到 observed 值，所以 RamCOM 实际是会受 exp8 噪声影响的（早期我担心 baseline 看不到噪声，复核后确认无此问题）。
2. 关键问题
P1（严重）—— exp7 / exp8 的默认 algorithms 是 ("rl-capa", "ramcom")
experiments/run_chengdu_exp7_deadline_delay.py:22：

DEFAULT_DEADLINE_DISTURBANCE_ALGORITHMS = ("rl-capa", "ramcom")
"rl-capa" runner 走 每个点重新训练 路径（experiments/paper_chengdu.py:817 注册的训练用 kwargs：episodes / lr_actor / lr_critic 等）。
其他 paper 实验默认 "rl-capa-infer"（paper_config.py:14，加载 rl_checkpoint_dir 下 checkpoint）。
后果：
若使用 "rl-capa"：每个 delay ∈ {5..60} 与 noise ∈ {±5..±20} 都从零训练一次，在 “含扰动” 的 env 上学到对应策略。RL-CAPA 的鲁棒性优势主要来自 “按扰动重训”，而 RamCOM 不能重训。这条 narrative 是 “online adaptive learning”，与你描述的 “执行过程中自适应学习这种噪声” 在语义上能勉强对齐，但训练成本极大，且不符合 paper 通常的 “一次训练多次推断” 范式。
若使用 "rl-capa-infer"：固定 checkpoint，跨扰动幅度推断。这才是常见的 “鲁棒性测试”。但若 checkpoint 是在 clean 默认配置下训出的，agent 在推断时无法识别噪声，只能依靠默认 deadline 分布隐式泛化。
建议：

确认实验意图。若是“鲁棒性”实验 → 默认应改为 "rl-capa-infer"，并使用 一次训练好的 clean checkpoint；同时记录 checkpoint 来源（rl_checkpoint_dir）。
若是“自适应学习”实验 → 保留 "rl-capa"，但需要在论文里明确写 “每个扰动幅度均重新训练”，否则评审会质疑这是 sweep training 而非鲁棒性。
二选一最稳妥的写法：把默认改成 ("rl-capa-infer", "ramcom") + 提供一个 --include-rl-train 开关（或单独 algorithms 覆盖）跑“训练 vs 推断”对照。
P2（严重）—— 数据集覆盖：脚本只跑 Chengdu，论述提到 NYTaxi 与 Synthetic
当前两个脚本文件名前缀 run_chengdu_，进入的是 paper_chengdu 模块；preset "ny" 仅改 sweep 取值范围（paper_config.py:39-48），不改 data_dir，仍读 Data/ 下 Chengdu 数据（paper_chengdu.py:48, 208, 606）。
没有任何 NYTaxi loader 或 Synthetic loader 与 derive_deadline_delay_environment / derive_deadline_noise_environment 对接（搜不到 NYTaxi/Synthetic environment 类）。
建议：

若 NYTaxi/Synthetic 已在仓库其它处实现（如 experiments/paper_nytaxi.py 之类），需要新增 run_nytaxi_exp7/8、run_synth_exp7/8，并在各自 environment 上挂 apply_processing_delay / apply_deadline_noise。
若尚未实现，本次 exp7/8 只能在 Chengdu 上跑。需要先补 NYTaxi/Synthetic 的数据通路与种子化（experiments/seeding.py:611-612 已能读 observed_* 字段，是好兆头），再扩展到这两个数据集。
P3（中）—— RL-CAPA state 没有“扰动信号”维度
rl_capa/state_builder.py：
stage1（8 维）：[pending, available, future_parcel, future_courier, avg_distance, avg_urgency, delivered_ratio, expired_ratio]
stage2（9 维）：[parcel.deadline, current_time, v_tau, unassigned_count, available_local, avg_remaining_cap, cross_courier_count, avg_cross_bid, batch_size]
两套 state 用的 parcel.deadline 即 observed_d_time（exp8 注入的噪声值），arrival_time 来自 observed_s_time（exp7 注入的延迟值）。
没有任何特征显式编码 “真实 vs 感知偏差”、“delay 幅度”、“噪声幅度”、“近期 deadline 命中率” 等。
影响：
训练 + 在线适应（rl-capa 路线）：奖励信号来自 真实 on-time 投递（env/chengdu.py:1119, 1485-1488 + rl_capa/env.py:516-528 的 _drain_new_delivered_revenue），所以 agent 即便看不到 “噪声幅度” 也能通过 reward 反推 “感知 deadline 不可信” → 倾向更紧凑批 / 更激进 cross-match。这条路在理论上 OK。
仅推断（rl-capa-infer 路线）：agent 不能在 inference 阶段更新参数；如果 checkpoint 是在 clean 上训出的，agent 只能凭分布泛化，“自适应学习”这一说法成立度低。
建议：是否新增特征取决于走哪条路线：

走 rl-capa-infer + clean checkpoint：建议新增 1~2 个特征以提供分布漂移信号，例如：
recent_expired_ratio（最近 K 个 batch 内 perceived-feasible 却真实过期的比率）；
mean_observed_minus_true_delivery_gap（已完成任务的实际完成时间相对 observed deadline 的偏差均值）。
这两个量只能从“已经回流”的真实结果里算，不会泄露未知 ground truth。
走 rl-capa 每点重训：可不加，但必须重训（见 P4）。
P4（中）—— 是否需要重新训练
路线	是否需要重新训练	备注
rl-capa 每点训练（exp7/8 当前默认）	每个 axis 点本身就在训	自动覆盖扰动分布。代价：训练总轮数 ≈ episodes × len(axis_values) × 2 (delay+noise) × 2 (NYTaxi+Synth)。
rl-capa-infer 用现有 clean checkpoint	可以不重训，但要承认 agent 不感知扰动	TR 下降幅度可能与 RamCOM 接近，narrative 受削弱。
rl-capa-infer 用 “扰动增强训练” checkpoint	需要新训 1 份 checkpoint：在训练 episode 内随机采样 delay/noise 幅度（domain randomization）	一次性训练，跨扰动推断；与 paper 中 “learn from noisy env” narrative 最契合，且与 P3 的状态扩展互补。推荐方案。
推荐：选第三条 —— 在训练循环里对每个 episode 随机抽样 delay ∈ DEADLINE_DELAY_VALUES ∪ {0} 与 noise ∈ DEADLINE_NOISE_VALUES ∪ {0}，沿用 derive_deadline_*_environment 注入，让 agent 见过多种感知偏差。然后 exp7/8 用 rl-capa-infer 加载这份 “robust checkpoint”，与 RamCOM 公平对比。

P5（轻）—— RamCOM 在 exp8 下的可行性逻辑
复核确认 RamCOM 决策路径实际会受 perceived deadline 影响（baselines/common.py:141 → is_feasible_local_match(parcel, ...) 内部判 parcel.deadline，即 observed）。trace 字段 "deadline" 写的是 true 值，仅供 diagnostic 使用，不影响决策。

不过有两个细节值得记录：

baselines/ramcom.py:316 用 get_true_deadline(task) < current_time 做硬剔除。这意味着 正向噪声 下：任务即便已过真实 deadline，RamCOM 仍可能在 perceived 内放进可行候选（feasibility 判定基于 observed），但若 current_time 已超过 true deadline，前一行会先剔除。两者结合后，RamCOM 在正向噪声下的损失主要发生在 “完成时刻 > 真实 deadline” 而非 “被剔除”，这与你预期的 “任务真实过期，损失整 fare” 一致（drain 阶段 env/chengdu.py:1114, 1119 用 true deadline 判 on-time）。
RamCOM 行内的 arrival_time = get_model_release_time(task) —— exp7 下到达时间会推迟，行为符合预期。
结论：RamCOM 侧无需改动，但建议在 exp7/8 输出 summary 里加 expired_due_to_true_deadline 与 accepted_but_timed_out 两个细分计数，方便 paper 解读 TR 下降来源。检查现有 summary：

grep -n "timed_out\|expired\|on_time" baselines/ramcom.py rl_capa/env.py
需要确认这些指标都已经在 summary 里被采集；若缺，需要在 metric 聚合处补字段。

3. RL step / env 推进与 deadline 的耦合点（事实清单）
任务进入 batch：prepare_chengdu_batch 用 get_model_release_time（observed） —— exp7 起作用。
batch 内 eligible 过滤：get_true_deadline —— 真实剔除。
CAPA / RL 可行性：legacy_task_to_parcel 默认走 observed → parcel.deadline = observed_d_time —— exp8 影响 agent / RamCOM 决策。
on-time 判定 / 奖励 / drain：get_true_deadline —— 真实 ground truth 永远是奖励 anchor，agent 训练能学到“感知不可信”。
RL state（stage1 urgency、stage2 deadline 维度）：均来自 observed 值。
⇒ env 实现是自洽的：算法侧统一看 observed，奖励侧统一看 true。两个实验的语义在底层成立。

4. 改动建议清单（按优先级）
 P1：决定 exp7/8 的算法集语义（“在线 retrain” vs “固定 checkpoint inference”）。若选第二种，把 DEFAULT_DEADLINE_DISTURBANCE_ALGORITHMS 改为 ("rl-capa-infer", "ramcom")，并在 README/exp 文档里明确 checkpoint 来源。
 P2：补 NYTaxi、Synthetic 的 environment 与 derive_deadline_*_environment 适配；新增 experiments/run_nytaxi_exp7/8.py、experiments/run_synth_exp7/8.py 或在现有脚本里加 --dataset {chengdu,nytaxi,synth} 路由。
 P4 推荐方案：训练一份 “domain-randomized” RL-CAPA checkpoint —— 在 rl_capa/train*.py 的 episode 起点处随机采样 (delay, noise) 并调用 apply_processing_delay / apply_deadline_noise 注入；存档为 rl_capa_robust/。exp7/8 用 rl-capa-infer 指向这份 checkpoint。
 P3：可选 —— 给 state 加入 recent_expired_ratio、mean_perceived_vs_true_gap 等漂移特征，让 inference 也能识别扰动。需要同步调整 STAGE1_STATE_DIM / STAGE2_STATE_DIM 与 actor/critic 网络输入维度，并配套训练。
 P5：在 summary 里区分 expired_at_intake、accepted_but_timed_out、rejected_observed_deadline，便于 paper 写 TR 损失成因。
5. 是否需要重训？一句话回答
需要。在保持当前 state 维度的前提下，至少要训一份 “在训练过程中随机注入 deadline delay/noise” 的 robust checkpoint，并把 exp7/8 改为加载这个 checkpoint（rl-capa-infer）。否则要么 RL-CAPA 的鲁棒性来源说不清（P1），要么 inference 阶段几乎等同于裸推断，难以支撑 “自适应学习扰动” 的论述（P3 后半）。如果选择 P4 的“按点重训” 路线，则现有 state 已经够用，但训练成本会随 axis 值数量线性放大。