# CAPA Utility Slimming Design

**Background**

当前 `capa/` 目录同时承载了三类职责：

1. 核心算法与运行编排：`cama.py`、`dapa.py`、`runner.py`
2. 核心领域模型与指标：`models.py`、`metrics.py`、`config.py`
3. 纯工具层：缓存、几何下界、定时包装、批量距离预热、兼容性 re-export

工具层文件过多，导致 `capa/` 目录被大量小模块切碎，阅读 CAPA 主逻辑时需要在多个工具文件之间跳转。

**Goal**

在不改变 CAPA 算法行为的前提下，对 `capa/` 做一次保守瘦身：

- 保留核心算法文件：`cama.py`、`dapa.py`、`runner.py`
- 保留核心领域/实验文件：`models.py`、`metrics.py`、`config.py`、`experiments.py`
- 将纯工具层逻辑统一收拢到 `capa/utility.py`
- 删除被吸收后的旧工具模块文件

**Recommended Boundary**

并入 `capa/utility.py` 的文件：

- `capa/cache.py`
- `capa/geo.py`
- `capa/timing.py`
- `capa/batch_distance.py`
- `capa/travel.py`
- `capa/revenue.py`

保留独立的文件：

- `capa/constraints.py`

原因：

- `constraints.py` 虽然体量小，但表达的是 CAPA / baseline 共用的约束语义，而不是纯粹的基础工具。
- 将其与 `utility.py` 分离后，目录中仍然保留“算法逻辑”和“约束逻辑”的清晰边界。

**Architecture**

重构后的职责划分如下：

- `utility.py`
  - 路由插入缓存
  - Haversine 几何索引
  - 批量距离缓存与预热
  - timing 辅助类
  - travel / revenue 的兼容逻辑
  - 既有的效用、收益、插入计算函数
- `cama.py`
  - 本地匹配筛选与执行
- `dapa.py`
  - 双层拍卖筛选、竞价与执行
- `runner.py`
  - Algorithm 1 的批处理驱动
- `constraints.py`
  - 约束判断：半径、几何 deadline 下界

**Key Constraint**

`timing.py` 里的 `BatchTimingBreakdown` 目前被 `models.py` 引用。如果直接把它移入 `utility.py`，会导致：

- `models.py -> utility.py`
- `utility.py -> models.py`

形成循环依赖。

因此本次重构采用更保守的处理：

- `BatchTimingBreakdown` 继续保留在 `models.py`
- 只把 `TimingAccumulator` 与 `TimedTravelModel` 迁入 `utility.py`
- 删除 `timing.py`

这仍符合“工具类逻辑进 `utility.py`”的目标，同时不破坏现有导入图。

**Migration Map**

导入迁移如下：

- `from capa.cache import InsertionCache` -> `from capa.utility import InsertionCache`
- `from capa.geo import GeoIndex` -> `from capa.utility import GeoIndex`
- `from capa.timing import TimingAccumulator, TimedTravelModel` -> `from capa.utility import TimingAccumulator, TimedTravelModel`
- `from capa.batch_distance import BatchDistanceMatrix, PersistentDirectedDistanceCache` -> `from capa.utility import BatchDistanceMatrix, PersistentDirectedDistanceCache`
- `from capa.travel import DistanceMatrixTravelModel` -> `from capa.utility import DistanceMatrixTravelModel`
- `from capa.revenue import ...` -> `from capa.utility import ...`

**Testing Strategy**

先写失败测试，锁住两类目标：

1. `utility.py` 暴露被迁移后的工具 API
2. 原工具文件被删除后，核心模块与现有测试仍能正常导入和运行

验证范围：

- 新增一个 refactor 回归测试，检查 `utility.py` 是否导出目标类/函数，且旧文件不存在
- 运行现有 CAPA 与 Chengdu 相关测试，确认行为不变

**Non-Goals**

- 不改 CAPA 论文算法公式
- 不改 `constraints.py` 的独立模块边界
- 不顺手重写 `experiments.py`
- 不调整 baseline 逻辑，只改工具导入路径
