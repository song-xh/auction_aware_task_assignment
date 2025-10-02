# config.py
# 论文关键参数与全局开关

# -------- CAMA（本地匹配） ----------
# 效用：u(τ,c) = γ * Δw + (1-γ) * Δd
GAMMA_UTILITY: float = 0.5         # γ
OMEGA_THRESHOLD: float = 1.0       # ω, 动态阈值敏感系数

# KM 指派使用的权重：True 用 utility 做最大权匹配；False 用“收益/报价”矩阵
KM_USE_UTILITY: bool = True

# -------- DLAM（双层拍卖） ----------
# 外露运费：p'_τ = μ1 * p_τ
MU_1: float = 0.8
# 平台间奖励/补偿项：μ2 * p_τ（乘以合作质量 f(P)）
MU_2: float = 0.1

# FPSA（平台内快递员）出价：BF(c,τ) = p_min + (α * Δd + β * g(c)) * γ_share * p'_τ
ALPHA_DETOUR: float = 0.7   # α
BETA_PERF: float = 0.3      # β
COURIER_SHARE_GAMMA: float = 0.8     # γ_share（合作平台分成比例，控制一价上界）

# 底价（可按需要更细化到任务/平台）
COURIER_BID_FLOOR: float = 0.0

# -------- 本地付款 R_c（给本地快递员） ----------
# R_c(τ,c) = ζ * p_τ
ZETA_LOCAL_PAYMENT_RATIO: float = 0.7

# -------- 合作质量 f(P)（平台间 RVA 中使用，≤1） ----------
# 可在运行时覆盖
COOP_QUALITY = {
    # platform_id: quality in [0,1]
    2: 1.0,
    3: 0.8,
    4: 0.6,
}

# -------- 其他运行参数 ----------
# 是否在跨平台插入时重算最优插入点（或复用本地阶段计算结果）
RECOMPUTE_INSERT_AT_PARTNER: bool = True

# 日志/调试
VERBOSE: bool = True
