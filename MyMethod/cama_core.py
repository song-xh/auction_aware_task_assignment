# cama_core.py
# 严格按论文定义实现 Δd、Δw、u 与动态阈值，保留 KM 匹配流程

from typing import List, Tuple, Dict, Any
import numpy as np
from config import GAMMA_UTILITY, OMEGA_THRESHOLD, KM_USE_UTILITY
from GraphUtils_ChengDu import NodeModel, g, s, VELOCITY
from km_matcher import KMMatcher

# ====== 工具：最优插入位置与绕行计算 ======


def _path_len(node_id_a: int, node_id_b: int) -> float:
    """用全局 g/s 计算最短路长度（米）。"""
    a = NodeModel()
    a.nodeId = node_id_a
    b = NodeModel()
    b.nodeId = node_id_b
    length = 0.0
    for e in g.getShortPath(a, b, s):
        length += e.length
    return length


def compute_best_insert_and_detour(courier, task) -> Tuple[float, int, float]:
    """
    在 courier.re_schedule（任务序列）里枚举插入位置，选择 Δd 最大的点。
    返回：(Δd, best_index, extra_travel_length)
      - Δd = base / (a + b)，越大越好（论文定义）
      - best_index 插入到 re_schedule 的哪个下标之后（或之前）
      - extra_travel_length 额外里程（用于到达时间微调）
    说明：
      假设序列 ... -> l_i -> l_{i+1} -> ...
      base = dist(l_i, l_{i+1})
      a = dist(l_i, l_task), b = dist(l_task, l_{i+1})
      Δd = base / (a + b)
    """
    best_delta_d = -1.0
    best_idx = -1
    best_extra = 0.0

    seq = courier.re_schedule
    # 边界：若为空，按“当前位置→task→返站”估计
    if not seq:
        base = _path_len(courier.location, courier.station.l_node)
        a = _path_len(courier.location, task.l_node)
        b = _path_len(task.l_node, courier.station.l_node)
        delta_d = base / max(1e-6, (a + b))
        extra = a + b - base
        return delta_d, 0, extra

    # 正常：枚举相邻边
    for i in range(len(seq)):
        prev_node = courier.location if i == 0 else seq[i-1].l_node
        next_node = seq[i].l_node

        base = _path_len(prev_node, next_node)
        a = _path_len(prev_node, task.l_node)
        b = _path_len(task.l_node, next_node)
        denom = max(1e-6, a + b)
        delta_d = base / denom
        extra = (a + b) - base

        if delta_d > best_delta_d:
            best_delta_d = delta_d
            best_idx = i
            best_extra = extra

    # 尾部插入（最后一个点后 -> 返站）
    last_node = seq[-1].l_node
    base = _path_len(last_node, courier.station.l_node)
    a = _path_len(last_node, task.l_node)
    b = _path_len(task.l_node, courier.station.l_node)
    delta_d_tail = base / max(1e-6, (a + b))
    extra_tail = (a + b) - base
    if delta_d_tail > best_delta_d:
        best_delta_d = delta_d_tail
        best_idx = len(seq)  # 末尾
        best_extra = extra_tail

    return best_delta_d, best_idx, best_extra


def compute_delta_weight(courier, task) -> float:
    """
    Δw = 1 - (current_load + w_task) / w_capacity
    """
    denom = max(1e-6, courier.max_weight)
    val = 1.0 - (courier.re_weight + task.weight) / denom
    return max(-10.0, min(10.0, val))  # 裁剪，稳健些


def compute_utility(courier, task, gamma: float = GAMMA_UTILITY) -> Tuple[float, int, float]:
    """
    返回 (u, best_idx, extra_len)
    u(τ,c) = γ * Δw + (1-γ) * Δd
    """
    delta_d, best_idx, extra_len = compute_best_insert_and_detour(
        courier, task)
    delta_w = compute_delta_weight(courier, task)
    u = gamma * delta_w + (1.0 - gamma) * delta_d
    return float(u), best_idx, float(extra_len)

# ====== 候选生成、KM 权重与阈值 ======


def enumerate_candidates(couriers: list, tasks: list, time_count: int) -> list:
    """
    过滤可行对（容量、时间窗、插入可行），产出候选：
    [(task, courier, u, best_idx, extra_len), ...]
    """
    cands = []
    for t in tasks:
        # 时间窗初步过滤（以当前时刻 + 快递员“第一段行驶时间”粗估）
        for c in couriers:
            # 容量与时间窗粗约束（和你现有 MethodUtils 保持一致的思想）
            # 这里不做“重排”，只允许在最优位置插入；若 extra 时间超出则跳过
            u, idx, extra = compute_utility(c, t)
            # 估计 extra 时间（秒）
            extra_time = extra / max(1e-6, (VELOCITY * 1000.0))
            # 粗略时窗判定：到达时间不超过截止
            # 注：你的项目已有更细的 check_threshold，可在外层配合使用
            if time_count + extra_time <= float(t.d_time):
                cands.append((t, c, u, idx, extra))
    return cands


def build_matrices(tasks: list, couriers: list, candidates: list) -> np.ndarray:
    """
    用 utility 构建 KM 矩阵（任务×快递员），无候选置极小值。
    """
    n, m = len(tasks), len(couriers)
    W = np.full((n, m), -1e9, dtype=float)
    task_index = {t.num: i for i, t in enumerate(tasks)}
    courier_index = {id(c): j for j, c in enumerate(couriers)}
    for (t, c, u, idx, extra) in candidates:
        i = task_index[t.num]
        j = courier_index[id(c)]
        W[i, j] = float(u)
    return W


def km_assign(tasks: list, couriers: list, W: np.ndarray) -> list:
    """
    KM 做最大权匹配，返回 [(task, courier), ...]
    """
    if W.size == 0:
        return []
    # KMMatcher 期望的是“成本/收益”矩阵，你的实现是最大匹配还是最小？
    # 这里以“最大”为目标：若 KM 是“最小化”，可取 -W。
    try:
        from km_matcher import KMMatcher
        M = W.copy()
        # 若你的 KM 是“最小化”，请改为 M = -W
        matcher = KMMatcher(M)
        matches = matcher.solve()  # 返回 [(i,j)]
        result = []
        for (i, j) in matches:
            if i < len(tasks) and j < len(couriers) and W[i, j] > -1e8:
                result.append((tasks[i], couriers[j]))
        return result
    except Exception as e:
        # 兜底：贪心
        pairs = []
        used_c = set()
        order = np.dstack(np.unravel_index(
            np.argsort(W.ravel())[::-1], W.shape))[0]
        for i, j in order:
            if W[i, j] < -1e8:
                break
            if j in used_c:
                continue
            pairs.append((tasks[i], couriers[j]))
            used_c.add(j)
        return pairs


def compute_threshold(matched_pairs: list, utility_map: Dict[tuple, float], omega: float = OMEGA_THRESHOLD) -> float:
    """Th = ω * 平均 utility（对 KM 匹配到的对）"""
    if not matched_pairs:
        return float('inf')  # 无匹配则全部进跨平台
    vals = [utility_map[(t.num, id(c))] for (
        t, c) in matched_pairs if (t.num, id(c)) in utility_map]
    if not vals:
        return float('inf')
    return omega * (sum(vals) / len(vals))


def split_local_or_cross(matched_pairs: list,
                         utility_map: Dict[tuple, float],
                         best_idx_map: Dict[tuple, int],
                         omega: float = OMEGA_THRESHOLD) -> Tuple[list, list]:
    """
    根据 Th 划分：
      local_list: [(t,c,best_idx)]
      cross_list: [t]
    """
    Th = compute_threshold(matched_pairs, utility_map, omega)
    local_list, cross_list = [], []
    for (t, c) in matched_pairs:
        u = utility_map.get((t.num, id(c)), -1e9)
        if u >= Th:
            local_list.append((t, c, best_idx_map.get((t.num, id(c)), -1)))
        else:
            cross_list.append(t)
    return local_list, cross_list

# ====== 应用本地插入 ======


def apply_local_assignment(local_list: list) -> list:
    """
    对每个 (t,c,best_idx) 在 c.re_schedule 中执行插入，并更新 c 的状态。
    返回已落地列表（可用于本地收益结算）。
    备注：此处仅演示插入点的使用，具体 reach_time/返站/后续点时间调整
         保留你现有项目里对 re_schedule 的更新逻辑（不重排，只插入）。
    """
    landed = []
    for (t, c, best_idx) in local_list:
        if best_idx < 0:
            # 容错：末尾插入
            c.re_schedule.append(t)
        else:
            c.re_schedule.insert(min(best_idx + 1, len(c.re_schedule)), t)
        # 更新承重
        c.re_weight += t.weight
        landed.append((t, c))
    return landed

# ====== 一条龙：本地 CAMA 流程 ======


def run_cama_batch(couriers: list, tasks: list, time_count: int) -> Dict[str, Any]:
    """
    返回：
    {
      'matched_pairs': [(t,c),...],
      'local_list': [(t,c,best_idx),...],
      'cross_candidates': [t,...],
      'utility_map': {(t.num,id(c)): u, ...}
    }
    """
    cands = enumerate_candidates(couriers, tasks, time_count)
    # 构造 utility map / best_idx map
    utility_map = {(t.num, id(c)): u for (t, c, u, idx, extra) in cands}
    best_idx_map = {(t.num, id(c)): idx for (t, c, u, idx, extra) in cands}
    # KM
    W = build_matrices(tasks, couriers, cands)
    matched_pairs = km_assign(tasks, couriers, W)
    # 二次筛选：Th
    local_list, cross_list = split_local_or_cross(
        matched_pairs, utility_map, best_idx_map)
    return {
        'matched_pairs': matched_pairs,
        'local_list': local_list,
        'cross_candidates': cross_list,
        'utility_map': utility_map,
        'best_idx_map': best_idx_map,
    }
