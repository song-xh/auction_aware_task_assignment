# 项目超参数汇总（以当前代码与 README 命令为准）

来源：`README.md`、`capa/config.py`、`capa/models.py`、`rl_capa/config.py`、`rl_capa/state_builder.py`、`rl_capa/networks.py`、`rl_capa/trainer.py`、`runner.py`、`experiments/paper_config.py`、`experiments/paper_chengdu.py`、`env/chengdu.py`。

说明：本文档只分三部分：CAPA 超参数、RL-CAPA 超参数、实验环境 preset 默认设置。RL-CAPA 部分以 `README.md` 中给出的 RL 命令显式设置为准；代码默认值仅在命令未显式给出时作为补充。

## 1. CAPA 超参数

| 符号 / 参数 | 简单定义 | 当前代码默认值 | 实验 / preset 设置 |
|---|---|---:|---|
| `Δb` / `batch_size` / `DEFAULT_CAPA_BATCH_SIZE` | CAPA 批处理时间窗口，batch 结束后执行 CAMA + DAPA | `30` 秒 | paper fixed preset 使用 `30`；README 旧写法示例曾用 `300` |
| `φ` / `utility_balance_gamma` | CAMA Eq.6 中容量剩余比与绕路比的权衡系数 | `0.5` | `detour-favoring` round 使用 `0.3` |
| `ω` / `threshold_omega` | CAMA Eq.7 动态阈值调节因子 | `0.8` | omega sensitivity: `{0.5,0.6,0.7,0.8,0.9,1.0}` |
| `ζ` / `local_payment_ratio_zeta` | 本地骑手固定报酬比例，`Rc(τ,c)=ζ·pτ` | `0.2` | zeta sensitivity: baseline `0.2`，变体 `{0.1,0.3,0.4,0.5}` |
| `μ1` / `local_sharing_rate_mu1` | Loc 第一层共享率，决定 `p'τ=μ1·pτ` | `0.5` | μ sensitivity 中由 `μ1=r·μ` 生成 |
| `μ2` / `cross_platform_sharing_rate_mu2` | Loc 第二层共享率，进入平台层 RVA 支付 | `0.5` | μ sensitivity 中由 `μ2=(1-r)·μ` 生成 |
| `μ=μ1+μ2` | Loc 总共享率 | `1.0` | μ sensitivity 默认中心 `0.7`，sweep `{0.5,0.6,0.7,0.8,0.9}` |
| `r` / `sharing-ratio-r` | μ 拆分比例，`μ1=rμ` | 无全局默认 | μ/r sensitivity 默认中心 `0.5`，sweep `{0.2,0.3,0.4,0.5,0.6,0.7,0.8}` |
| `γ` / `platform_sharing_rate_gamma` | 合作平台给跨平台骑手报价的共享率 | `0.5` | 每个平台默认相同 |
| `p_min` / `base_price` | FPSA 一层骑手报价基础价格 | `1.0` | 对所有合作平台默认赋 `1.0` |
| `α` / `courier_alpha` | 跨平台骑手绕路偏好权重 | `0.5` | formal/ny sweep `{0.1,0.3,0.5,0.7,0.9}`；smoke `{0.3,0.7}` |
| `β` / `courier_beta` | 跨平台骑手服务质量偏好权重 | `1-α=0.5` | 校验要求 `α+β=1` |
| `g(c)` / `courier_service_score` | 骑手历史服务表现代理值 | `0.8` | 成都适配层固定代理值 |
| `f(P)` / `platform_quality_start` | 合作平台历史合作质量起始代理值 | `1.0` | P1 从 `1.0` 开始 |
| `platform_quality_step` | 不同合作平台历史合作质量递减步长 | `0.1` | P2 起每个平台递减 `0.1` |
| `MIN_PLATFORM_QUALITY` | 合作平台质量代理值下限 | `0.5` | `build_default_platform_qualities()` 中截断 |
| `λ_c` / `courier_expected_income_ratio_lambda_c` | μ sensitivity 扩展：跨平台骑手固定期望收益比例 | `None`，默认关闭 | μ sensitivity 调参值 `0.4` |
| `λ_p` / `platform_expected_income_ratio_lambda_p` | μ sensitivity 扩展：合作平台固定期望收益比例 | `None`，默认关闭 | μ sensitivity 调参值 `0.4` |
| `fixed_local_revenue_threshold` | 固定本地收益阈值，绕过动态 Eq.7 阈值 | `None` | zeta sensitivity 先跑 baseline 读取 `Th*` 后再固定 |

## 2. RL-CAPA 超参数

### 2.1 README 中 RL-CAPA 命令设置

| 符号 / 参数 | 简单定义 | README smoke 命令 | README stable 命令 | README stage1 命令 | README stage2 命令 | README ablation 命令 |
|---|---|---:|---:|---:|---:|---:|
| `E` / `--episodes` | 训练轮数 | `500` | `2000` | `500` | `500` | `1500` |
| `η_actor` / `--rl-lr-actor` | 两个 actor 的 Adam 学习率 | `0.001` | `0.0003` | `0.0003` | `0.0003` | `0.0003` |
| `η_critic` / `--rl-lr-critic` | critic / value 网络 Adam 学习率 | `0.001` | `0.0005` | `0.0005` | `0.0005` | `0.0005` |
| `γ_RL` / `--rl-discount-factor` | Monte-Carlo discounted return 折扣因子 | `0.9` | `0.95` | `0.95` | `0.95` | `0.95` |
| `κ` / `--rl-entropy-coeff` | policy entropy 正则系数 | `0.01` | `0.03` | `0.03` | `0.03` | `0.03` |
| `G_max` / `--rl-max-grad-norm` | 梯度裁剪阈值 | `0.5` | `0.5` | `0.5` | `0.5` | `0.5` |
| `A_b` / `--rl-batch-actions` | 第一阶段 batch-duration 动作集合 | `{10,15,20}` | `{10,20,30,45}` | `{10,15,20}` | 不适用 | `{10,15,20,25,30}` |
| `Δb_fixed` / `--batch-size` | stage2-only 固定 batch size | 未显式设置 | 未显式设置 | 未显式设置 | `30` | `30` |
| `step_seconds` / `--step-seconds` | RL 环境推进步长 | `60` | `60` | `60` | `60` | `60` |
| `norm_adv` | actor advantage 标准化 | 默认开启 | 默认开启；可追加关闭 | 默认开启 | 默认开启 | 默认开启 |
| `--rl-disable-advantage-normalization` | 关闭 advantage 标准化 | 未启用 | 可选追加 | 未启用 | 未启用 | 未启用 |
| `output_dir` | 输出目录 | `outputs/plots/rl_capa_run` | `outputs/plots/rl_capa_stable` | `outputs/plots/rl_capa_stage1` | `outputs/plots/rl_capa_stage2` | `outputs/plots/rl_capa_ablation` |

### 2.2 README 之外的 RL-CAPA 当前代码默认

| 符号 / 参数 | 简单定义 | 当前代码默认值 / 说明 |
|---|---|---|
| `h_L` / `--min-batch-size` | 未提供 `--rl-batch-actions` 时的 batch action 下界 | `10` 秒 |
| `h_M` / `--max-batch-size` | 未提供 `--rl-batch-actions` 时的 batch action 上界 | `20` 秒 |
| `S_b` / `STAGE1_STATE_DIM` | 第一阶段状态维度 | `8` |
| `S_m` / `STAGE2_STATE_DIM` | 第二阶段 parcel 状态维度 | `11` |
| `S_m+slack` / `STAGE2_SERVICE_SLACK_DIM` | 启用 service slack 后的第二阶段状态维度 | `12` |
| `--rl-future-feature-window-seconds` | stage-1 真实未来特征统计窗口 | `300` 秒 |
| `--rl-use-service-slack` | 是否追加 service slack 特征 | 默认关闭 |
| `--rl-warmup-episodes` | normalizer-only / critic warmup episodes | `0` |
| `--rl-entropy-start` | entropy 线性退火起始值 | `None` |
| `--rl-entropy-end` | entropy 线性退火结束值 | `None` |
| `--rl-entropy-decay-episodes` | entropy 退火轮数 | `None` |
| `T_max` / `max_steps_per_episode` | 单 episode 最大决策步数 | `500` |
| `ε_adv` | advantage 标准化数值稳定项 | `1e-8` |
| `device` / `--rl-device` | torch 设备 | 默认 `None`，自动选择 CUDA 或 CPU |
| `H` / `hidden_dim` | actor / critic MLP 隐藏层宽度 | `128` |
| `L` | actor / critic MLP 隐藏层数 | `2` |
| `act` | MLP 激活函数 | `ReLU` |
| `π1` | batch-size actor | `BatchSizeActor(state_dim=8, hidden_dim=128, num_actions=|A_b|)` |
| `π2` | cross-or-not actor | `CrossOrNotActor(state_dim=11/12, hidden_dim=128)` |
| `Q1` | stage-1 action-value critic | `BatchSizeQCritic(state_dim=8, hidden_dim=128, num_actions=|A_b|)` |
| `V1` | stage-1 value critic | `StateValueCritic(state_dim=8, hidden_dim=128)` |
| `V2` | stage-2 conditional value critic | `ConditionalValueCritic(state_dim=11/12, hidden_dim=128)` |
| `b_π1`, `W_π1` | `π1` 输出层初始化 | bias `0`，weight `0` |
| `b_π2` | `π2` cross logit 初始 bias | `-2.0` |
| `P_cross_init` | `π2` 初始 cross 概率 | `sigmoid(-2.0)≈0.12` |
| `optimizer` | RL 优化器 | 当前训练器使用 `Adam` |
| `R_t` | 训练 reward | 当前 batch 平台收益 |
| `Rhat_t` | discounted return | `compute_discounted_returns(rewards, γ_RL)` |
| `A1` | 第一阶段 advantage | `Q1(s,a)-Σ_a'π1(a'|s)Q1(s,a')` |
| `A2` | 第二阶段 advantage | `r_t-V2(s2_agg)` |
| `s2_agg` | 第二阶段聚合状态 | parcel states mean pooling |
| `log_prob_2` | 第二阶段联合动作 log probability | batch 内 parcel Bernoulli log_prob 求和 |
| `--rl-train-delay-max-seconds` | 训练期随机 delay 最大值 | `0.0`，表示关闭 |
| `--rl-train-delay-window` | 训练期随机 delay 作用窗口 | `None` |
| `train_delay_seed` | 训练期 delay 随机种子 | `17` |
| checkpoint files | RL checkpoint 输出 | `pi1.pt`, `pi2.pt`, `q1.pt`, `v1.pt`, `v2.pt`, `normalizers.pt` |

### 2.3 README 中 RL-CAPA 命令对应环境规模

| 命令 | `|Γ|` / 包裹数 | `|C|` / 本地骑手 | `|P|` / 平台数 | 每平台骑手 | 时间窗 | partner history |
|---|---:|---:|---:|---:|---|---|
| smoke `rl-capa` | `100` | `10` | `2` | `5` | `[0,30]` 秒 | start `200`, step `0` |
| stable `rl-capa` | `500` | `12` | `4` | `8` | `[0,600]` 秒 | start `200`, step `0` |
| `rl-capa-stage1` | `500` | `20` | `4` | `5` | `[0,300]` 秒 | start `200`, step `0` |
| `rl-capa-stage2` | `500` | `20` | `4` | `5` | `[0,300]` 秒 | start `200`, step `0` |
| `rl-capa-ablation` | `500` | `10` | `2` | `5` | `[0,180]` 秒 | start `200`, step `0` |

## 3. 实验环境 preset 默认设置

### 3.1 runner 单次运行默认环境

| 参数 | 简单定义 | 默认值 |
|---|---|---:|
| `--data-dir` | Chengdu 数据目录 | `Data` |
| `--num-parcels` | 包裹数量 `|Γ|` | `100` |
| `--local-couriers` | 本地平台骑手数量 `|C|` | `10` |
| `--platforms` | 合作平台数量 `|P|` | `2` |
| `--couriers-per-platform` | 每个合作平台骑手数量 | `5` |
| `--courier-capacity` | 骑手容量覆盖值 | `None`；环境构造未传时使用 `75` |
| `--service-radius-km` | 服务半径覆盖值 | `None` |
| `--task-window-start-seconds` | 任务采样窗口起点 | `None` |
| `--task-window-end-seconds` | 任务采样窗口终点 | `None` |
| `--task-sampling-seed` | 任务采样随机种子 | `1` |
| `--partner-history-task-count-start` | 第一合作平台自有任务流规模 | CLI 默认 `None`；env 默认 `25000` |
| `--partner-history-task-count-step` | 后续合作平台自有任务流增量 | CLI 默认 `None`；env 默认 `2500` |
| `--courier-alpha` | 骑手绕路偏好权重 | `0.5` |
| `--courier-beta` | 骑手服务质量偏好权重 | `None`，自动设为 `1-alpha` |
| `--courier-service-score` | 骑手服务质量代理值 | `0.8` |
| `--platform-quality-start` | 平台质量代理起始值 | `1.0` |
| `--platform-quality-step` | 平台质量代理递减步长 | `0.1` |
| `--deadline-seconds` | 统一 deadline 覆盖 | `None` |
| `--courier-speed-kmh` | 骑手速度覆盖 | `30.0 km/h` |
| station split | Chengdu legacy station 网格分割参数 | `11`，形成 `10x10` 网格 |

### 3.2 paper fixed 默认环境

| 参数 | formal 默认值 | ny 默认值 |
|---|---:|---:|
| `num_parcels` | `50000` | `50000` |
| `local_couriers` | `3000` | `300` |
| `platforms` | `4` | `4` |
| `couriers_per_platform` | `500` | `50` |
| `courier_capacity` | `50.0` | `50.0` |
| `service_radius_km` | `1.0` | `1.0` |
| `batch_size` | `30` | `30` |
| `deadline_seconds` | `720` | `720` |
| `task_window_start_seconds` | `0` | `0` |
| `task_window_end_seconds` | `14398` | `3600` |
| `task_sampling_seed` | `1` | `1` |
| `partner_history_task_count_start` | `5000` | `5000` |
| `partner_history_task_count_step` | `200` | `200` |
| `courier_alpha` | `0.5` | `0.5` |
| `courier_beta` | `None -> 0.5` | `None -> 0.5` |
| `courier_service_score` | `0.8` | `0.8` |
| `platform_quality_start` | `1.0` | `1.0` |
| `platform_quality_step` | `0.1` | `0.1` |

### 3.3 suite preset sweep 网格

| preset | sweep 参数 | 默认网格 |
|---|---|---|
| `smoke` | `num_parcels` | `{20,50}` |
| `smoke` | `local_couriers` | `{2,4}` |
| `smoke` | `service_radius` | `{0.5,1.5}` |
| `smoke` | `platforms` | `{1,2}` |
| `smoke` | `courier_capacity` | `{25,50}` |
| `smoke` | `courier_alpha` | `{0.3,0.7}` |
| `smoke` | `deadline_delay` | `{5,10}` |
| `smoke` | `deadline_noise` | `{-20,0,20}` |
| `formal` | `num_parcels` | `{5000,20000,50000,100000,200000}` |
| `formal` | `local_couriers` | `{1000,2000,3000,4000,5000}` |
| `formal` | `service_radius` | `{0.5,1.0,1.5,2.0,2.5}` |
| `formal` | `platforms` | `{2,4,8,12,16}` |
| `formal` | `courier_capacity` | `{25,50,75,100,125}` |
| `formal` | `courier_alpha` | `{0.1,0.3,0.5,0.7,0.9}` |
| `formal` | `deadline_delay` | `{0,5,10,20,30,60}` |
| `formal` | `deadline_noise` | `{-20,-15,-10,-5,0,5,10,15,20}` |
| `ny` | `num_parcels` | `{500,2000,5000,10000,20000}` |
| `ny` | `local_couriers` | `{100,200,300,400,500}` |
| `ny` | `service_radius` | `{0.5,1.0,1.5,2.0,2.5}` |
| `ny` | `platforms` | `{2,4,8,12,16}` |
| `ny` | `courier_capacity` | `{25,50,75,100,125}` |
| `ny` | `courier_alpha` | `{0.1,0.3,0.5,0.7,0.9}` |
| `ny` | `deadline_delay` | `{5,10,15,20,30,60}` |
| `ny` | `deadline_noise` | `{-20,-15,-10,-5,0,5,10,15,20}` |

### 3.4 robustness / sensitivity 默认点

| 参数 / 脚本 | 简单定义 | 默认值 |
|---|---|---|
| `DEADLINE_DELAY_VALUES` | deadline delay sweep | `{5,10,15,20,30,60}` 秒 |
| `DEFAULT_FIXED_DELAY_VALUES` | Exp-7 fixed delay compare | `{5,10,20,30,60}` 秒 |
| `DEADLINE_NOISE_VALUES` | perceived deadline noise sweep | `{-20,-15,-10,-5,0,5,10,15,20}` % |
| `FORMAL_POINTS` | CAPA Exp-1 formal parcel 点 | `{5000,20000,50000,100000,200000}` |
| `NY_POINTS` | CAPA Exp-1 ny parcel 点 | `{500,2000,5000,10000,20000}` |
| `ZETA_VARIANTS` | CAPA zeta sensitivity 非 baseline 点 | `{0.1,0.3,0.4,0.5}` |
| `OMEGA_VARIANTS` | CAPA omega sensitivity 点 | `{0.5,0.6,0.7,0.8,0.9,1.0}` |
| `MU_VALUES` | CAPA μ sensitivity 点 | `{0.5,0.6,0.7,0.8,0.9}` |
| `R_VALUES` | CAPA μ 拆分比 sensitivity 点 | `{0.2,0.3,0.4,0.5,0.6,0.7,0.8}` |
| `SENS_POINTS` | μ sensitivity 固定规模 | formal `50000`，ny `5000` |
