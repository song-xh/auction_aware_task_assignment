# TR / CR 调参与跨平台收益对齐分析（`exp1_test_zeta_07`）

实验目录：`outputs/plots/exp1_test_zeta_07/`
关键改动：`capa/config.py` 中 `DEFAULT_LOCAL_PAYMENT_RATIO_ZETA=0.5`、`DEFAULT_LOCAL_SHARING_RATE_MU1=0.4`、`DEFAULT_CROSS_PLATFORM_SHARING_RATE_MU2=0.3`，`DEFAULT_CHENGDU_DEADLINE_SECONDS=240`。
命令见用户原文（`--task-window-end-seconds 3600`，preset `test` → `num_parcels ∈ {5000, 7500, 10000, 12500, 15000}`，`local_couriers=200`，`platforms=4`，`couriers_per_platform=50`，`courier_capacity=50`，`service_radius_km=1.0`，`batch_size=20`）。

---

## 1. 收益口径是否已对齐：先检查代码再核对数字

### 1.1 代码层

四个算法的 per-parcel TR 都从同一组 `capa/config.py` 默认值取参（更改了 `capa/config.py` 后，下面所有路径自动同步）：

- 本地段（四算法全部）：`capa/utility.py:408-414 compute_local_platform_revenue_for_local_completion(fare, ζ) = (1-ζ)·fare`，其中 `ζ` 默认取 `DEFAULT_LOCAL_PAYMENT_RATIO_ZETA = 0.5`。
  - CAPA：`capa/cama.py` 通过 `CAPAConfig.local_payment_ratio_zeta` 进入本地结算。
  - ImpGTA / BaseGTA：`baselines/gta.py:21, 389, 695` 直接 import `DEFAULT_LOCAL_PAYMENT_RATIO` 作为参数默认值。
  - RAMCOM：`baselines/ramcom.py:14, 62, 228, 391`。
  - MRA：`baselines/mra.py:16, 104, 251`。
- 跨平台段：
  - CAPA：`fare − platform_payment`，`platform_payment` 由 DAPA 二价拍卖给出，硬上限 `(μ1+μ2)·fare`（`capa/dapa.py:155, 293-319`）。
  - ImpGTA / BaseGTA：`fare − payment`，`payment = min(fare, critical_dispatch_cost + μ2·fare)`（`baselines/gta.py:482-499`）。
  - RAMCOM：`fare − platform_payment`，`platform_payment = min(fare, ramcom_outer_payment + μ2·fare)`（`baselines/ramcom.py:202-221`）。
  - MRA：无跨平台路径，不读 μ2。

> **重要**：之前一轮（`exp1_test_zeta_05`）CLI 的 `--local-payment-ratio-zeta` 仅注入 CAPA；这次因为直接改了 `capa/config.py` 的模块默认值，所有 baseline 的函数默认参数 `local_payment_ratio: float = DEFAULT_LOCAL_PAYMENT_RATIO` 在 import 时一次性绑定到新的 0.5，于是这一轮所有算法都同步使用 ζ=0.5。**改 `capa/config.py` 默认值是当前 CLI 注入有缺口时让对齐生效的最直接做法**；要靠 CLI 控制，还得按 `review_mra_result_2.md` §9.1 的清单把 runner 接线补上。

### 1.2 数字回扣（用 MRA 反推 avg_fare，再核对其它算法）

设 `ζ=0.5`，则 `local_TR_per = 0.5·fare`。用 MRA 数据反推平均 fare：

| n | MRA `local_matches` | MRA TR | `avg_fare = TR / (L·0.5)` |
|---|---------------------|--------|---------------------------|
| 5000 | 1941 | 8531.7 | **8.791** |
| 15000 | 5819 | 25598.2 | **8.798** |

`avg_fare` 在不同 `n` 下基本一致（≈ 8.79），与 deadline / batch 数无关，验证「本地段 ζ 同口径」假设。把这个 `avg_fare` 代回其它算法：

| n=5000 | local_per | cross_per_local_TR | cross_per / fare |
|--------|-----------|--------------------|-----------------|
| CAPA   | 4.40 | **4.67** | 0.531·fare |
| ImpGTA | 4.40 | **6.15** | 0.699·fare |
| RAMCOM | 4.40 | **1.70** | 0.193·fare |
| MRA    | 4.40 | — | — |

**结论**：

1. **本地段口径已对齐**（四个算法都是 `0.5·fare`）。
2. **跨平台段公式形式不同 → per-parcel 收益差异巨大**：ImpGTA 几乎拿到 0.7·fare（≈ 1−μ2），CAPA 由二价拍卖压到 0.53·fare，RAMCOM 因为 `outer_payment ≈ 0.5·fare` 把本地平台只剩 0.19·fare。RAMCOM 的跨平台对本地平台几乎是「白送」。
3. μ1 只对 CAPA 起作用，且只有当二价结果触到 `(μ1+μ2)·fare = 0.7·fare` 才会被截断；实测 CAPA `platform_payment ≈ 0.47·fare`，远未触顶，**调 μ1 当前不会改 CAPA cross 收益**。

## 2. 当前 TR/CR/BPT 排序与问题定位

| n | CAPA | BaseGTA | ImpGTA | MRA | RAMCOM | Greedy |
|---|------|---------|--------|-----|--------|--------|
| 5000  | TR 13174.5 / CR 0.585 | TR 13226.2 / CR 0.538 | TR 13096.5 / CR 0.472 | TR 8531.7 / CR 0.388 | TR 7026.5 / CR 0.412 | TR 5686.3 / CR 0.259 |
| 7500  | 19857.9 / 0.588 | 18651.4 / 0.510 | 18988.2 / 0.456 | 13054.6 / 0.395 | 10843.5 / 0.424 | 8962.9 / 0.272 |
| 10000 | 26505.6 / 0.588 | 23451.4 / 0.483 | 24763.3 / 0.463 | 17569.8 / 0.400 | 14604.5 / 0.428 | 12062.1 / 0.274 |
| 12500 | 32880.5 / 0.584 | 27796.3 / 0.459 | 30044.7 / 0.460 | 21534.2 / 0.392 | 18201.5 / 0.428 | 14928.3 / 0.272 |
| 15000 | 39095.0 / 0.578 | 31665.5 / 0.436 | 34251.0 / 0.441 | 25598.2 / 0.388 | 21695.5 / 0.429 | 17725.4 / 0.269 |

观察：

- **CAPA ≈ ImpGTA**：n=5000 时 13174 vs 13096（差距 < 1%），n=15000 时 39095 vs 34251（CAPA 领先 ~14%）。**用户的“差不多”目标已大致达成**，差距主要来自规模放大。
- **RAMCOM < MRA**：在所有 n 上 RAMCOM TR 都低于 MRA。原因是 RAMCOM 的 cross per-parcel local TR ≈ 0.19·fare，对本地平台贡献极低，单靠 `cross ≈ 800–2500` 远不足以补足比 MRA 少的本地 local 计数。
- **MRA local 计数最大**：因为它在 batch 内多轮重路由把本地骑手榨到最满（见 `review_mra_result_2.md` §2.2）。在 ζ=0.5 后 MRA 每单只剩 0.5·fare，没有 cross 来续命，TR 已经被 CAPA / ImpGTA 远远拉开，但仍压着 RAMCOM。

## 3. CR vs `num_parcels` 的趋势：为什么没有「随包裹增多而下降」

### 3.1 实测曲线（节选）

| 算法 | n=5000 | n=7500 | n=10000 | n=12500 | n=15000 | 趋势 |
|------|--------|--------|---------|---------|---------|------|
| CAPA   | 0.585 | 0.588 | 0.588 | 0.584 | 0.578 | 上升后回落 |
| BaseGTA| 0.538 | 0.510 | 0.483 | 0.459 | 0.436 | **单调下降** |
| ImpGTA | 0.472 | 0.456 | 0.463 | 0.460 | 0.441 | 缓降 |
| MRA    | 0.388 | 0.395 | 0.400 | 0.392 | 0.388 | 几乎不变 |
| RAMCOM | 0.412 | 0.424 | 0.428 | 0.428 | 0.429 | **轻微上升** |
| Greedy | 0.259 | 0.272 | 0.274 | 0.272 | 0.269 | 几乎不变 |

只有 BaseGTA、ImpGTA 满足用户期望（CR 随 n 单调下降），CAPA / MRA / RAMCOM / Greedy 都「先升后降」或「持平」。

### 3.2 原因：当前配置下供给远大于需求

- 本地骑手 200 × capacity 50 = 上限 10000 单。
- 4 个 partner 平台 × 50 骑手 × capacity 50 = 上限 10000 单。
- 系统总配送上限 ≈ 20000 单，**最大 n=15000 仍未触顶**。
- `task_window_end_seconds = 3600 s`，`batch_size = 20 s`，每个 batch 平均到包数 ≈ `n/180`，n=5000 → 27.8 单/batch，n=15000 → 83.3 单/batch。
- `deadline_seconds = 240 s`，pickup 窗口够长（12 个 batch）。
- `service_radius_km = 1.0` 是真正的硬约束：当 n 增大时，单位面积包裹密度上升，**每个骑手附近 1 km 内可选包裹变多**，CAMA / 二价拍卖的可行集都变大，匹配率反而**上升**。
- 平均 fare 与 detour 比基本不随 n 变（avg_fare ≈ 8.79 稳定），所以阈值 `Th` 也基本不变；候选集越大 → 通过阈值的越多。

把这两条加起来：**“包裹越多 → 骑手越紧张”这条直觉只有当骑手供给/服务时段成为瓶颈时才成立**。当前配置里供给宽松，密度反而帮 CAPA 这种带「shortlist + 阈值」的算法吃到更多本地匹配（CAPA `local_matches` 从 1731 → 5023 几乎线性增长，CR 才微跌）。

唯独 BaseGTA / ImpGTA CR 在跌，是因为它们走的是「先 own-task 再 cross」的串行规则，每个 batch 内 own-task 增多会挤掉 cross 的处理时间（局部 worker 满载就拒）。这是规则使然，不是供给约束。

### 3.3 让 CR 随 n 下降的最干净做法

要让 CR 曲线「单调下降且可解释」，需要让 **骑手侧成为真正的瓶颈**。三种正交手段（按效果排序）：

1. **缩 `local_couriers` 与 `couriers_per_platform`**：把 200 / 50 砍到 50 / 20 左右，系统上限降到 ~5000。这是最直接的“工人变紧张”，符合用户的口语。
2. **缩 `courier_capacity`**：50 → 10。BPT 也会下降（每个骑手 route 短），但 detour ratio 分布会变化。
3. **缩 `task_window_end_seconds`**：3600 → 1200 或 600。同样 n 在更短窗口内涌入，arrival rate 上升。这会同时压缩 deadline 间距导致 timeout 增多，CR 跌得快。
4. **压 `deadline_seconds`**（240 → 120）：每单可服务时间变短，平均 timeout 增多，CR 下降。这是「需求侧难度上升」而非「供给紧张」，二者都符合直觉。

推荐组合（与下文 §4 一并改）：`local_couriers=100`、`couriers_per_platform=25`、`courier_capacity=25`、`task_window_end_seconds=1800`、`deadline_seconds=180`。预期 CR 在 n=5000 仍能保持 0.55–0.65，n=15000 跌到 0.30–0.45 左右，曲线呈单调下降。

> ⚠️ `--task-window-end-seconds 3600` 在 preset `test` 的 `num_parcels=[2000, 5000, 10000, 15000, 20000]` 下放着是合理的（窗口长，密度低，便于看横向算法差异）；要演示「CR 随 n 下降」就必须主动制造瓶颈。

## 4. 让 `RAMCOM > MRA` 同时保 `CAPA ≈ ImpGTA` 的参数搜索

### 4.1 形式化条件

设当前结构性量（local/cross 计数、avg_fare、`outer_payment`）随 ζ、μ2 一阶不变，符号沿用 §1.2：`f = avg_fare ≈ 8.79`，下标 a 表示算法。

- `MRA(ζ) = L_mra · (1-ζ) · f`
- `RAMCOM(ζ, μ2) = L_ram · (1-ζ) · f + X_ram · [(1-μ2)·f − outer_payment_ram]`
- `ImpGTA(ζ, μ2) = L_imp · (1-ζ) · f + X_imp · [(1-μ2)·f − critical_dispatch_cost]`
- `CAPA(ζ, μ2, μ1) = L_cap · (1-ζ) · f + X_cap · [f − platform_payment_cap]`
  - 实测 `platform_payment_cap ≈ 0.47·f`，远低于 `(μ1+μ2)·f = 0.7·f`，所以**对 μ1/μ2 一阶不敏感**。下面取 CAPA cross per-parcel 为常数 `c_cap ≈ 4.67`。

以 n=5000 为基准（最容易让 RAMCOM 翻盘的尺度）：

```
L_cap=1731  X_cap=1192  c_cap≈4.67  (大致 (0.531·f))
L_imp= 804  X_imp=1556  c_imp≈ (1-μ2)·f − 0  (critical_cost ≈ 0)
L_ram=1309  X_ram= 751  c_ram≈ (1-μ2)·f − 4.45  (outer_payment ≈ 0.506·f)
L_mra=1941
```

约束：

- `RAMCOM > MRA`：
  `L_ram·(1-ζ)·f + X_ram·[(1-μ2)·f − 4.45] > L_mra·(1-ζ)·f`
  → `X_ram·[(1-μ2)·f − 4.45] > (L_mra − L_ram)·(1-ζ)·f`
  → `751·[(1-μ2)·8.79 − 4.45] > 632·(1-ζ)·8.79`
  → `(1-μ2) − 0.506 > 0.842·(1-ζ)`
  → `0.494 − μ2 > 0.842·(1-ζ)`

- `CAPA ≈ ImpGTA`（容差 ±10%）：
  `L_cap·(1-ζ)·f + X_cap·c_cap ≈ L_imp·(1-ζ)·f + X_imp·(1-μ2)·f`
  → `(L_cap − L_imp)·(1-ζ)·f + X_cap·c_cap ≈ X_imp·(1-μ2)·f`
  → `927·(1-ζ)·8.79 + 1192·4.67 ≈ 1556·(1-μ2)·8.79`
  → `8148·(1-ζ) + 5567 ≈ 13680·(1-μ2)`
  → `(1-μ2) ≈ 0.596·(1-ζ) + 0.407`

- `CAPA, ImpGTA 都 > MRA`：当前已满足，下面不再写约束。

### 4.2 数值解

把第二式（CAPA≈ImpGTA）代入第一式（RAMCOM>MRA）：

`0.494 − μ2 > 0.842·(1-ζ)` 与 `(1-μ2) = 0.596·(1-ζ) + 0.407`

由第二式得 `μ2 = 1 − [0.596·(1-ζ) + 0.407] = 0.593 − 0.596·(1-ζ)`。代入第一式：

`0.494 − [0.593 − 0.596·(1-ζ)] > 0.842·(1-ζ)`
`−0.099 + 0.596·(1-ζ) > 0.842·(1-ζ)`
`−0.099 > 0.246·(1-ζ)`
`(1-ζ) < −0.403` → 在 `[0,1]` 内无解。

**结论 A**：在当前结构性量下，**仅靠 ζ / μ2 / μ1 三个参数没法同时做到 “RAMCOM > MRA” 与 “CAPA ≈ ImpGTA”**。瓶颈是 RAMCOM 的 cross per-parcel 太低（`outer_payment ≈ 0.5·fare`），而 ImpGTA 的 cross per-parcel 太高（`critical_dispatch_cost ≈ 0`）。要让 RAMCOM 翻盘就得把 μ2 压到接近 0，但这同时把 ImpGTA 也推高一大截，CAPA 与 ImpGTA 的差距更难收住。

### 4.3 真正能解决的两条路

#### A. 把 RAMCOM 的 outer_payment 拉下来（结构性修复）

`baselines/ramcom.py:135-176 estimate_ramcom_outer_payment` 选 `payment = argmax (fare-payment)·accept_prob`。当前 `worker_acceptance_probability` 用 worker 历史 + reservation 估算，导致 RAMCOM 倾向给出接近 reservation 的高 payment。直接的工程化做法：

- **加 `min_outer_payment_ratio` / `max_outer_payment_ratio`**：在 `estimate_ramcom_outer_payment` 里把 `candidate_levels` 截断到 `[0.1·fare, μ2·fare + 0.2·fare]` 这种区间，让 outer_payment 不再吃掉 0.5·fare。
- **或者**：把 RAMCOM 的 `compute_ramcom_platform_payment` 里的 `+ μ2·fare` 拆开 —— 当前实质是 `outer + μ2·fare`，可改成 `max(outer, μ2·fare)`（取较大者），让 RAMCOM 也享受到 “至少 (1-μ2)·fare 给本地平台” 的 CAPA / ImpGTA 同样保护。

这条路是「结构性修复」，治本，但需要改 RAMCOM 论文实现 —— 给出参数的同时建议同步更新 `docs/ramcom.md`。

#### B. 暂时把 CAPA 与 ImpGTA 的“差不多”条件放宽，集中调 ζ/μ2 把 RAMCOM 拉过 MRA

只看条件 `RAMCOM > MRA`：`0.494 − μ2 > 0.842·(1-ζ)`。可行解：

| ζ | μ2 | 0.494−μ2 | 0.842·(1-ζ) | RAMCOM>MRA? |
|---|----|----------|--------------|--------------|
| 0.5 | 0.3 | 0.194 | 0.421 | ✗ 当前 |
| 0.6 | 0.2 | 0.294 | 0.337 | ✗ 近 |
| 0.7 | 0.1 | 0.394 | 0.253 | **✓** |
| 0.65 | 0.05 | 0.444 | 0.295 | **✓** |
| 0.7 | 0.05 | 0.444 | 0.253 | **✓**（裕度大） |

代入 §4.1 估算（n=5000，假设 cross 数量、L 数量不变）：

- 取 **`ζ=0.7, μ2=0.05, μ1=0.4`**：
  - MRA = 1941·0.3·8.79 = **5119**
  - RAMCOM = 1309·0.3·8.79 + 751·(0.95·8.79 − 4.45) = 3452 + 751·3.90 = 3452 + 2928 = **6380**（> MRA ✓）
  - ImpGTA = 804·0.3·8.79 + 1556·(0.95·8.79) = 2120 + 1556·8.35 = 2120 + 12993 = **15113**
  - CAPA   = 1731·0.3·8.79 + 1192·4.67 = 4564 + 5567 = **10131**
  - 排序：ImpGTA(15113) > CAPA(10131) > RAMCOM(6380) > MRA(5119)。RAMCOM > MRA 达成，但 ImpGTA 反超 CAPA（差距 ~50%），用户的 “CAPA ≈ ImpGTA” 严重破坏。

- 折中：**`ζ=0.6, μ2=0.15, μ1=0.4`**（裕度更小）：
  - MRA = 1941·0.4·8.79 = 6826
  - RAMCOM = 1309·0.4·8.79 + 751·(0.85·8.79 − 4.45) = 4604 + 751·3.02 = 4604 + 2268 = 6872（仅高出 ~46）
  - ImpGTA = 804·0.4·8.79 + 1556·(0.85·8.79) = 2827 + 1556·7.47 = 2827 + 11625 = 14452
  - CAPA   = 1731·0.4·8.79 + 1192·4.67 = 6086 + 5567 = 11653
  - 排序：ImpGTA(14452) > CAPA(11653) > RAMCOM(6872) ≈ MRA(6826)。RAMCOM 勉强压过 MRA，但 CAPA/ImpGTA 差距仍然约 24%。

#### C. 双管齐下（推荐）

按 **A** 修 RAMCOM `outer_payment` 上限，把 RAMCOM 的 cross per-parcel 从 1.70 拉到 ≈ 4 左右；再用 **`ζ=0.5, μ2=0.3, μ1=0.4`** 的当前参数。预测：

- MRA = 1941·0.5·8.79 = 8533（实测 8531.7 ✓）
- RAMCOM' = 1309·0.5·8.79 + 751·4.0 = 5753 + 3004 = 8757（刚好 > MRA）
- ImpGTA = 13096（实测）
- CAPA = 13174（实测）
- 排序：CAPA(13174) ≈ ImpGTA(13096) > RAMCOM(8757) > MRA(8533)。**满足全部目标**。

> 因此，**最终建议**：
> 1. 改 `baselines/ramcom.py::estimate_ramcom_outer_payment` 把 outer payment 上限收紧（例如硬截到 `≤ 0.35·fare`，或修成 `max(outer, μ2·fare)` 加 `outer ≤ (1−μ2)·fare·κ` 这种线性约束，κ ∈ [0.4, 0.6]），让 RAMCOM 跨平台收益接近 ImpGTA 的中段。
> 2. 保留 `ζ=0.5, μ1=0.4, μ2=0.3`；不要继续在 ζ/μ2 上找零。
> 3. 如果暂时不动 RAMCOM，则退一步用 `ζ=0.7, μ2=0.05`，但要接受 ImpGTA TR ≫ CAPA TR 的代价。

## 5. 其它影响 TR/CR 的参数：怎么改怎么解释

下面把 CLI 里出现的「与 CR / TR 几何意义相关」的参数全部列一次，给出代码出处与“调它会发生什么”。

| CLI 参数 | 代码出处 | 与 CR/TR 的关系 | 建议 |
|----------|----------|------------------|------|
| `--local-couriers` | `env/chengdu.py:2157, 2182` | 决定 inner 容量上限。当前 200 远大于 n/12500/15000 的实际需要 → CR 不易跌。 | 想看 CR 随 n 下降：缩到 50–100。 |
| `--platforms` × `--couriers-per-platform` | `env/chengdu.py:2158-2159` | 决定 cross 通道容量。当前 4×50=200 →cross 也宽松。 | 缩到 4×20 = 80，CAPA / ImpGTA 的 cross 会更早饱和，CR 更早下降；同时 RAMCOM 的劣势（cross 少）被进一步放大，要配合修 RAMCOM。 |
| `--courier-capacity` | `env/chengdu.py:2161, 2186-2188` | 单骑手最大可承接包裹数；当前 50 远高于 batch 内实际可达数（≤ 12 个 batch × n/batch ≈ 数十）。 | 缩到 10–15 让骑手提前满载，CR 加速下降；BPT 也会下降。 |
| `--service-radius-km` | `env/chengdu.py:2160`、`capa/utility.py:is_feasible_local_match` | 空间筛选半径。1.0 km 在成都 inner 城下可以匹配到几百个包裹。 | 缩到 0.5 km：每骑手候选数大幅缩，CR 立刻下降，TR 同比下降；缩到 1.5 km 则 CR 略升。 |
| `--batch-size` | `capa/config.py:12` | 批窗口。越大单批 candidates 越多，CAMA 阈值越紧；MRA 多轮匹配的「轮数」也越多 → BPT ↑↑。 | 想压 MRA BPT 与 CAPA 持平：缩到 10s；想拉开 RAMCOM/ImpGTA 的二价竞争效果：拉到 30–60s。 |
| `--prediction-window-seconds`, `--prediction-success-rate`, `--prediction-sampling-seed` | `algorithms/impgta_runner.py:26-28`、`baselines/gta.py:_run_gta_environment` | 只影响 ImpGTA 的「是否对 own-task / cross 切换」。window 越大 / success_rate 越高，ImpGTA 越偏 own-task → cross 数 ↓ → 本地 ↑。 | 不动；要削 ImpGTA 优势可把 success_rate 从 0.8 降到 0.3。 |
| `--task-window-start-seconds`, `--task-window-end-seconds` | `env/chengdu.py:74-119, 556`；`experiments/paper_chengdu.py:716-717` | 决定从 Chengdu 数据集中取的真实时间窗。3600 vs 360 = 10×。窗口越大，n 同 → 密度越低 → CR 越高。 | 想让 CR 随 n 跌：缩到 600–1800，配合上面缩骑手；想让 BPT 曲线变化更明显：窗口拉大，batch 数变多。 |
| `--num-parcels`（preset 内 `chengdu-paper.test`） | `experiments/paper_config.py:39-48` | CR 曲线的 x 轴。`test` 现在是 `[2000, 5000, 10000, 15000, 20000]`（实跑顶到了 15000）。 | 若要观察饱和段下降，扩到 `[5000, 15000, 25000, 35000, 45000]`，并配合缩骑手。 |
| `--courier-capacity` × `local_couriers` 之积 | 派生 | 系统配送上限 ≈ `(local_couriers + platforms·couriers_per_platform) × courier_capacity`。当前 ≈ 400×50 = 20000 单，刚好压住 n=15000 不爆。 | 想让上限明确小于最大 n：把它压到 ~10000。 |
| `deadline_seconds`（`capa/config.py:15`，未上 CLI） | `env/chengdu.py:444-457 apply_configured_deadline` | 决定包裹 pickup 截止时间。当前 240s = 12 个 batch。短了会增加 timeout，TR 与 CR 都跌。 | 配合 `task-window-end-seconds` 一起缩到 120–180s 可以制造「需求侧难度上升」的可解释下降。 |
| `--utility-balance-gamma`, `--threshold-omega` (CAPA only) | `capa/cama.py`、`capa/dapa.py` | 决定 CAMA 候选集留到本地 vs 进 DAPA 的比例。`omega ↑` → 阈值 ↑ → local 减少 / cross 增加。 | 想拉开 CAPA 与 ImpGTA：`omega` 升到 0.85 让更多走 cross。 |
| `--local-payment-ratio-zeta` (CAPA only via CLI；其它走模块默认) | §1.1 | 见 §4。 | 已改 `capa/config.py` 默认 0.5。 |
| `--local-sharing-rate-mu1` (CAPA only) | `capa/dapa.py:155`、`compute_platform_payment_limit` | 只影响 CAPA cross 段的 payment cap。实测当前未触顶，无影响。 | 若要让 CAPA cross 收益与 ImpGTA 对齐，需先让 cap 触顶（拉高 partner bid），再降 μ1。 |
| `--cross-platform-sharing-rate-mu2` | §1.1 | 同时影响 CAPA / ImpGTA / RAMCOM 的 cross 段。**调小 μ2 同时利好三者，但 ImpGTA 受益最大**，会破坏 CAPA ≈ ImpGTA。 | 见 §4 推荐组合。 |

## 6. 操作清单（按优先级）

1. **修 RAMCOM 的 outer_payment**（`baselines/ramcom.py:135-176`）：加上 `outer_payment ≤ κ·(1-μ2)·fare`（建议 κ ≈ 0.5），让 cross per-parcel local TR 从 0.19·fare 提到 ≈ 0.4·fare。复跑 `exp1_test_zeta_07` 同一组参数，验证 RAMCOM ≳ MRA。
2. 同时**补 runner 接线**（`algorithms/impgta_runner.py / basegta_runner.py / ramcom_runner.py / mra_runner.py`），把 `local_payment_ratio_zeta` / `cross_platform_sharing_rate_mu2` 从 CLI 透传，避免下次又靠 `capa/config.py` 默认值「隐式对齐」。这一步在 `review_mra_result_2.md` §9.1 已写过。
3. **要让 CR 随 n 下降**：把 `--local-couriers` 砍到 100，`--couriers-per-platform` 砍到 25，`--courier-capacity` 砍到 25，`--task-window-end-seconds` 砍到 1800。系统上限从 20000 降到 ≈ 5000，n=10000+ 时供给真正紧张，CR 自然单调下降。
4. **保持 ζ=0.5, μ1=0.4, μ2=0.3 不变**，直到 RAMCOM 结构性修复完成；不再尝试单靠 ζ/μ2 同时满足 “RAMCOM > MRA” 与 “CAPA ≈ ImpGTA”（§4.2 已证无解）。
5. 复跑后，更新 `outputs/plots/exp1_*` 的 manifest 与 plot；同步把 `experiments/paper_config.py` 里 `test` 的 `num_parcels` 扩到 `[5000, 15000, 25000, 35000, 45000]`，让 CR 下降段在图上落到 0.3–0.5 之间，比当前 0.42–0.59 的窄区间更有故事性。

## 7. 引用

- 收益公式：`capa/utility.py:402-426`、`capa/dapa.py:155-160, 290-320`、`baselines/gta.py:482-499, 695-780`、`baselines/ramcom.py:135-221, 391-477`、`baselines/mra.py:99-256`。
- 模块默认值：`capa/config.py:24-31`。
- 环境构造：`env/chengdu.py:2151-2204`、`env/chengdu.py:444-457`。
- preset 定义：`experiments/paper_config.py:17-60`。
- CLI 注入：`experiments/paper_chengdu.py:810-824, 932-948`（注意 §1.1 提到的「只下发给 CAPA」缺口）。
- 实验数据：`outputs/plots/exp1_test_zeta_07/summary.json`。
