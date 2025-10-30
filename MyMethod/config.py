# ===================== CONFIG 
# 效用与阈值
GAMMA_UTILITY: float = 0.5
OMEGA_THRESHOLD: float = 0.85

# 收益与竞拍参数
MU_1: float = 0.8     # 本地平台“可见价”比例（合作侧可见）
MU_2: float = 0.12    # 平台间加权系数
ZETA_LOCAL_PAYMENT_RATIO: float = 0.7   # 本地支付给骑手比例
COOP_QUALITY = {2: 1.0, 3: 0.9, 4: 0.8}  # 合作平台质量（可配置）

# 批窗口与小步
BATCH_SECONDS: int = 10 * 60
STEP_SECONDS: int = 60                 # 每小步 60s

# 平台规模
NUM_STATIONS_LOCAL = 6
COURIERS_PER_STATION = 40
NUM_PARTNER_PLATFORMS = 2
PARTNER_COURIERS_PER_PLATFORM = 40

# 数据与工程开关
REMAP_TASKS_TO_LCC: bool = True
WARMUP_BATCHES_FOR_SEEDING: int = 1
KMEANS_MAX_ITERS: int = 15
ENABLE_BACKLOG: bool = True
RUN_BASELINE_LOCAL_ONLY: bool = True

# 候选规模与缓存
K_NEAREST_COURIERS: int = 120
LRU_DIST_CACHE_SIZE: int = 100_000

# 进度打印心跳（每处理 N 条或每 T 秒打印一次）
PRINT_HEARTBEAT_N = 200
PRINT_HEARTBEAT_SEC = 0.3

# 每步/每批内的限制（防爆内存/时间）
MAX_TASKS_PER_STEP: int = 4000
MAX_ASSIGN_ROUNDS_PER_STEP: int = 2
MAX_TASKS_PER_COURIER_PER_BATCH: int = 6

# 骑手边际成本（FPSA 报价）
LAMBDA_D = 0.002   # /meter
LAMBDA_T = 0.10    # /second
THETA_BID = 0.9

# 本地阶段是否用 KM；False 则用候选贪心
USE_KM_FOR_LOCAL: bool = False
