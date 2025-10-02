# Framework_CD_test.py
# 单文件版：CAMA + DLAM（FPSA+RVA），带论文式指标与图表
# 提速补丁：K近邻预筛、LRU缓存、reachability缓存、并行可选、安全最短路封装、下界剪枝
# 依赖：GraphUtils_ChengDu.py, Tasks_ChengDu.py, km_matcher.py, Data/map_ChengDu
# --------------------------------------------------------------------------------

import random
import math
from typing import List, Dict, Any, Tuple
from collections import defaultdict, deque

import numpy as np
import matplotlib.pyplot as plt
from functools import lru_cache
# ADD: 并行支持（按需启用）
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import multiprocessing

# ========= 项目内依赖 =========
from GraphUtils_ChengDu import g, s, NodeModel, VELOCITY
from Tasks_ChengDu import readTask
from MyMethod.km_matcher import KMMatcher
from DistanceUtils import DistanceUtils

# =========================================================
# =============== 1) config（含提速相关开关） ===============
# =========================================================
GAMMA_UTILITY: float = 0.5
OMEGA_THRESHOLD: float = 1.0
KM_USE_UTILITY: bool = True

MU_1: float = 0.8
MU_2: float = 0.1
ALPHA_DETOUR: float = 0.7
BETA_PERF: float = 0.3
COURIER_SHARE_GAMMA: float = 0.8
COURIER_BID_FLOOR: float = 0.0
ZETA_LOCAL_PAYMENT_RATIO: float = 0.7

COOP_QUALITY = {2: 1.0, 3: 0.8, 4: 0.6}

RECOMPUTE_INSERT_AT_PARTNER: bool = True
VERBOSE: bool = True

BATCH_SECONDS: int = 30 * 60
NUM_PARTNER_PLATFORMS = 2
COURIERS_PER_STATION = 10
PARTNER_COURIERS_PER_PLATFORM = 8
NUM_STATIONS_LOCAL = 3

REMAP_TASKS_TO_LCC: bool = True
DEBUG_REACHABILITY_SAMPLE: int = 0

# ADD: 路径算法选择（仅作开关标识；目前底层仍调用 A* 的 getShortPath）
PATH_ALGO: str = "astar"  # 可设为 "dijkstra" 测试，但实现仍用 getShortPath

# ADD: 候选预筛与KM规模控制
K_NEAREST_COURIERS: int = 30      # 每个任务只保留最近K个骑手做候选
MAX_TASKS_PER_BATCH_DEBUG: int = 0  # 调试用，>0 时限制每批任务数

# ADD: 并行设置（谨慎开启；Windows上建议thread或显式spawn）
PARALLEL_MODE: str = "none"  # 可选 "none" | "thread" | "process"
PARALLEL_WORKERS: int = max(1, multiprocessing.cpu_count() // 2)

# ADD: 缓存大小（按内存情况调整）
LRU_DIST_CACHE_SIZE: int = 100_000


# =========================================================
# ============== 2) LCC 与可达性补丁（关键）=================
# =========================================================
def compute_connected_components(s):
    visited = set()
    comps = []
    for nid in s.nMap.keys():
        if nid in visited:
            continue
        q = [nid]
        comp = set([nid])
        visited.add(nid)
        while q:
            u = q.pop()
            neigh = getattr(s.nMap[u], 'neighbors', None) or []
            for v in neigh:
                if v not in visited:
                    visited.add(v)
                    comp.add(v)
                    q.append(v)
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    return comps


print("[INIT] Computing connected components...")
CCS = compute_connected_components(s)
if not CCS:
    raise RuntimeError("Road graph has no connected components.")
LCC_SET = set(CCS[0])
print(f"[INIT] Components: {len(CCS)} | LCC size: {len(LCC_SET)}")

_REACH_CACHE = {}


def is_reachable(nid_a, nid_b) -> bool:
    key = (nid_a, nid_b)
    if key in _REACH_CACHE:
        return _REACH_CACHE[key]
    ok = (nid_a in LCC_SET) and (nid_b in LCC_SET)
    _REACH_CACHE[key] = ok
    return ok


# ADD: Node->(lat,lng) 缓存，减少哈希查找
_NODE_LATLNG_CACHE: Dict[int, Tuple[float, float]] = {}


def node_latlng(nid: int) -> Tuple[float, float]:
    v = _NODE_LATLNG_CACHE.get(nid)
    if v is None:
        node = s.nMap[nid]
        v = (float(node.lat), float(node.lng))
        _NODE_LATLNG_CACHE[nid] = v
    return v

# ADD: LRU缓存的最短路长度（nid对）；注意：依赖路网静态不变


@lru_cache(maxsize=LRU_DIST_CACHE_SIZE)
def _shortest_path_len_cached(nid_a: int, nid_b: int) -> float:
    a = NodeModel()
    a.nodeId = nid_a
    b = NodeModel()
    b.nodeId = nid_b
    # GraphUtils 中实现为 A*；PATH_ALGO='dijkstra' 仅为开关占位
    eds = g.getShortPath(a, b, s)
    if not eds:
        return -1.0
    return float(sum(e.length for e in eds))

# ADD: 安全包装（先判可达，再查缓存）


def safe_path_len(nid_a: int, nid_b: int) -> float | None:
    if not is_reachable(nid_a, nid_b):
        return None
    d = _shortest_path_len_cached(nid_a, nid_b)
    return None if d < 0 else d


# 任务节点就近映射到 LCC
_dist_util = DistanceUtils()


def remap_task_to_LCC(task) -> bool:
    if getattr(task, 'l_node', None) in LCC_SET:
        return False
    lat = getattr(task, 'l_lat', None)
    lng = getattr(task, 'l_lng', None)
    if (lat is None or lng is None) and getattr(task, 'l_node', None) in s.nMap:
        _lat, _lng = node_latlng(task.l_node)
        lat, lng = _lat, _lng
    if lat is None or lng is None:
        return False
    best_nid, best_d = None, 1e18
    # ADD: 采样式最近邻（速度权衡）；全量遍历可更准但更慢
    SAMPLE = 5000 if len(LCC_SET) > 5000 else len(LCC_SET)
    for nid in random.sample(tuple(LCC_SET), SAMPLE):
        nl, ng = node_latlng(nid)
        d = _dist_util.getNodeDistance(lat, lng, nl, ng)
        if d < best_d:
            best_d, best_nid = d, nid
    if best_nid is not None:
        task.l_node = best_nid
        return True
    return False


# =========================================================
# ================= 3) 工具与核心函数 ======================
# =========================================================
def compute_best_insert_and_detour(courier, task) -> Tuple[float, int, float]:
    """
    找 courier.re_schedule 里 Δd 最大的插入点（不重排）
    Δd = base/(a+b)，extra = (a+b) - base
    使用 safe_path_len（含LCC与缓存）
    """
    best_delta_d, best_idx, best_extra = -1.0, -1, 0.0
    seq = courier.re_schedule

    if not is_reachable(courier.location, courier.station.l_node):
        return -1.0, -1, None

    if not seq:
        base = safe_path_len(courier.location, courier.station.l_node)
        a = safe_path_len(courier.location, task.l_node)
        b = safe_path_len(task.l_node, courier.station.l_node)
        if None in (base, a, b):
            return -1.0, -1, None
        delta_d = base / max(1e-6, (a + b))
        extra = a + b - base
        return delta_d, 0, extra

    for i in range(len(seq)):
        prev_node = courier.location if i == 0 else seq[i-1].l_node
        next_node = seq[i].l_node
        base = safe_path_len(prev_node, next_node)
        a = safe_path_len(prev_node, task.l_node)
        b = safe_path_len(task.l_node, next_node)
        if None in (base, a, b):
            continue
        denom = max(1e-6, a + b)
        delta_d = base / denom
        extra = (a + b) - base
        if delta_d > best_delta_d:
            best_delta_d, best_idx, best_extra = delta_d, i, extra

    # 尾部插入
    last_node = seq[-1].l_node if seq else courier.location
    base = safe_path_len(last_node, courier.station.l_node)
    a = safe_path_len(last_node, task.l_node)
    b = safe_path_len(task.l_node, courier.station.l_node)
    if None not in (base, a, b):
        delta_d_tail = base / max(1e-6, (a + b))
        extra_tail = (a + b) - base
        if delta_d_tail > best_delta_d:
            best_delta_d, best_idx, best_extra = delta_d_tail, len(
                seq), extra_tail

    return best_delta_d, best_idx, best_extra


def compute_delta_weight(courier, task) -> float:
    denom = max(1e-6, courier.max_weight)
    val = 1.0 - (courier.re_weight + task.weight) / denom
    return max(-10.0, min(10.0, val))


def compute_utility(courier, task, gamma: float = GAMMA_UTILITY) -> Tuple[float, int, float, float, float]:
    delta_d, best_idx, extra_len = compute_best_insert_and_detour(
        courier, task)
    if delta_d < 0 or extra_len is None:
        return -1e9, -1, None, -1e9, -1e9
    delta_w = compute_delta_weight(courier, task)
    u = gamma * delta_w + (1.0 - gamma) * delta_d
    return float(u), best_idx, float(extra_len), float(delta_d), float(delta_w)

# ADD: 欧氏球面距离下界 -> 时间下界，用于时窗剪枝


def time_lower_bound_seconds(nid_a: int, nid_b: int) -> float:
    lat_a, lng_a = node_latlng(nid_a)
    lat_b, lng_b = node_latlng(nid_b)
    # DistanceUtils 以米为单位（假设）；VELOCITY km/s -> m/s 需乘 1000
    d_m = _dist_util.getNodeDistance(lat_a, lng_a, lat_b, lng_b)
    return d_m / max(1e-6, VELOCITY * 1000.0)

# ADD: 为每个任务做 K近骑手预筛（基于球面距离）


def topk_couriers_for_task(task, couriers: list, k: int) -> List[Any]:
    t_lat, t_lng = node_latlng(task.l_node)
    # 先粗算每个骑手当前位置到任务点的球面距离
    pairs = []
    for c in couriers:
        c_lat, c_lng = node_latlng(c.location)
        d = _dist_util.getNodeDistance(t_lat, t_lng, c_lat, c_lng)
        pairs.append((d, c))
    pairs.sort(key=lambda x: x[0])
    return [c for _, c in pairs[:min(k, len(pairs))]]


def enumerate_candidates(couriers: list, tasks: list, time_count: int) -> list:
    """
    候选过滤：容量/时窗/插入可行（不重排）
    返回：(task, courier, u, best_idx, extra_len, Δd, Δw)
    """
    cands = []
    for t in tasks:
        cand_cs = topk_couriers_for_task(
            t, couriers, K_NEAREST_COURIERS)  # ADD: K近邻预筛
        for c in cand_cs:
            # ADD: 用球面距离的时间下界做时窗快速剪枝
            tlb = time_lower_bound_seconds(c.location, t.l_node)
            if time_count + tlb > float(t.d_time):
                continue
            u, idx, extra, delta_d, delta_w = compute_utility(c, t)
            if u < -1e8 or extra is None:
                continue
            extra_time = extra / max(1e-6, (VELOCITY * 1000.0))
            if time_count + extra_time <= float(t.d_time):
                cands.append((t, c, u, idx, extra, delta_d, delta_w))
    return cands


def build_matrices(tasks: list, couriers: list, candidates: list) -> np.ndarray:
    n, m = len(tasks), len(couriers)
    W = np.full((n, m), -1e9, dtype=float)
    task_index = {t.num: i for i, t in enumerate(tasks)}
    courier_index = {id(c): j for j, c in enumerate(couriers)}
    for (t, c, u, idx, extra, dd, dw) in candidates:
        i = task_index[t.num]
        j = courier_index[id(c)]
        W[i, j] = float(u)
    return W


def km_assign(tasks: list, couriers: list, W: np.ndarray) -> list:
    try:
        M = W.copy()
        # 如果 KMMatcher 是“最小化”，取消注释：
        # M = -W
        matcher = KMMatcher(M)
        matches = matcher.solve()  # [(i,j)]
        result = []
        for (i, j) in matches:
            if 0 <= i < len(tasks) and 0 <= j < len(couriers) and W[i, j] > -1e8:
                result.append((tasks[i], couriers[j]))
        return result
    except Exception:
        order = np.dstack(np.unravel_index(
            np.argsort(W.ravel())[::-1], W.shape))[0]
        used_c, pairs = set(), []
        for i, j in order:
            if W[i, j] < -1e8:
                break
            if j in used_c:
                continue
            pairs.append((tasks[i], couriers[j]))
            used_c.add(j)
        return pairs


def compute_threshold(matched_pairs: list, utility_map: Dict[tuple, float], omega: float = OMEGA_THRESHOLD) -> float:
    if not matched_pairs:
        return float('inf')
    vals = [utility_map[(t.num, id(c))] for (
        t, c) in matched_pairs if (t.num, id(c)) in utility_map]
    if not vals:
        return float('inf')
    return omega * (sum(vals) / len(vals))


def split_local_or_cross(matched_pairs: list,
                         utility_map: Dict[tuple, float],
                         best_idx_map: Dict[tuple, int],
                         omega: float = OMEGA_THRESHOLD) -> Tuple[list, list, float]:
    Th = compute_threshold(matched_pairs, utility_map, omega)
    local_list, cross_list = [], []
    for (t, c) in matched_pairs:
        u = utility_map.get((t.num, id(c)), -1e9)
        if u >= Th:
            local_list.append((t, c, best_idx_map.get((t.num, id(c)), -1)))
        else:
            cross_list.append(t)
    return local_list, cross_list, Th


def apply_local_assignment(local_list: list) -> list:
    landed = []
    for (t, c, best_idx) in local_list:
        if best_idx < 0:
            c.re_schedule.append(t)
        else:
            c.re_schedule.insert(min(best_idx + 1, len(c.re_schedule)), t)
        c.re_weight += t.weight
        landed.append((t, c))
    return landed


def run_cama_batch(couriers: list, tasks: list, time_count: int) -> Dict[str, Any]:
    cands = enumerate_candidates(couriers, tasks, time_count)
    utility_map = {(t.num, id(c)): u for (
        t, c, u, idx, extra, dd, dw) in cands}
    best_idx_map = {(t.num, id(c)): idx for (
        t, c, u, idx, extra, dd, dw) in cands}
    detour_map = {(t.num, id(c)): dd for (
        t, c, u, idx, extra, dd, dw) in cands}
    dweight_map = {(t.num, id(c)): dw for (
        t, c, u, idx, extra, dd, dw) in cands}

    W = build_matrices(tasks, couriers, cands)
    matched_pairs = km_assign(tasks, couriers, W)
    local_list, cross_list, Th = split_local_or_cross(
        matched_pairs, utility_map, best_idx_map)

    return {
        'matched_pairs': matched_pairs,
        'local_list': local_list,
        'cross_candidates': cross_list,
        'utility_map': utility_map,
        'best_idx_map': best_idx_map,
        'detour_map': detour_map,
        'dweight_map': dweight_map,
        'threshold': Th,
    }


# =========================================================
# ============ 4) 平台与工人（含区域划分） =================
# =========================================================
class InnerCourier:
    def __init__(self, ref: Any): self.ref = ref
    def __getattr__(self, item): return getattr(self.ref, item)


class CrossPlatformCourier:
    def __init__(self, ref: Any): self.ref = ref
    def __getattr__(self, item): return getattr(self.ref, item)


class Platform:
    def __init__(self, platform_id: int, is_local: bool, couriers: List[Any], station=None):
        self.platform_id = platform_id
        self.is_local = is_local
        self.couriers = couriers
        self.station = station
        self.cross_task_pool: List[Any] = []

    def clear_cross_pool(self): self.cross_task_pool = []


class LocalPlatform(Platform):
    def __init__(self, platform_id: int, couriers: List[Any], station=None):
        super().__init__(platform_id, True, couriers, station)


class PartnerPlatform(Platform):
    def __init__(self, platform_id: int, couriers: List[Any], station=None):
        super().__init__(platform_id, False, couriers, station)


class PlatformRegistry:
    def __init__(self, local_platform: LocalPlatform, partners: List[PartnerPlatform]):
        self.local = local_platform
        self.partners = partners
        self.coop_quality = COOP_QUALITY.copy()

    def broadcast_cross_tasks(self, tasks: List[Any]) -> None:
        for p in self.partners:
            p.cross_task_pool = list(tasks)

    def quality_of(self, platform_id: int) -> float:
        return float(self.coop_quality.get(platform_id, 1.0))


class Station:
    def __init__(self, num: int, l_node: int):
        self.num = num
        self.l_node = l_node
        self.courier_set: List[Courier] = []


class Courier:
    def __init__(self, num: int, location_node: int, max_weight: float, station: Station):
        self.num = num
        self.location = location_node
        self.schedule: List[Any] = []
        self.re_schedule: List[Any] = []
        self.station_num = station.num
        self.max_weight = max_weight
        self.re_weight = 0.0
        self.reach_time = 0.0
        self.sum_useful_time = 7200.0
        self.w = random.uniform(0.3, 0.7)
        self.c = random.uniform(0.3, 0.7)
        self.service_score = random.uniform(0.5, 1.0)
        self.station: Station = station


def _collect_all_latlng() -> Tuple[List[float], List[float], List[int]]:
    lats, lngs, ids = [], [], []
    for nid, node in s.nMap.items():
        lats.append(float(node.lat))
        lngs.append(float(node.lng))
        ids.append(nid)
    return lats, lngs, ids


def _region_split_by_quartiles(num_partners: int) -> Dict[str, Tuple[float, float, float, float]]:
    lats, lngs, _ = _collect_all_latlng()
    q_lat = np.quantile(lats, [0.25, 0.5, 0.75])
    q_lng = np.quantile(lngs, [0.25, 0.5, 0.75])
    q2_lat, q2_lng = q_lat[1], q_lng[1]
    regions = {}
    regions['local'] = (q2_lat, max(lats), min(lngs), q2_lng)
    candidates = [
        ('p2', q2_lat, max(lats), q2_lng, max(lngs)),
        ('p3', min(lats), q2_lat, q2_lng, max(lngs)),
        ('p4', min(lats), q2_lat, min(lngs), q2_lng),
    ]
    for i, (name, la, lb, lo, hi) in enumerate(candidates[:num_partners], start=2):
        regions[name] = (la, lb, lo, hi)
    return regions


def _sample_node_in_region_from_LCC(lat_min, lat_max, lng_min, lng_max) -> int:
    for _ in range(2000):
        nid = random.choice(tuple(LCC_SET))
        lat, lng = node_latlng(nid)
        if lat_min <= lat <= lat_max and lng_min <= lng <= lng_max:
            return nid
    return random.choice(tuple(LCC_SET))


def build_local_platform_with_regions(num_stations: int, couriers_per_station: int,
                                      region_box: Tuple[float, float, float, float]) -> Tuple[LocalPlatform, List[Station]]:
    lat_min, lat_max, lng_min, lng_max = region_box
    stations: List[Station] = []
    local_couriers_wrapped: List[InnerCourier] = []
    for st_idx in range(num_stations):
        st_node = _sample_node_in_region_from_LCC(
            lat_min, lat_max, lng_min, lng_max)
        st = Station(num=st_idx, l_node=st_node)
        stations.append(st)
        for j in range(couriers_per_station):
            c_node = _sample_node_in_region_from_LCC(
                lat_min, lat_max, lng_min, lng_max)
            c = Courier(num=st_idx * 100 + j, location_node=c_node,
                        max_weight=50.0, station=st)
            st.courier_set.append(c)
            local_couriers_wrapped.append(InnerCourier(c))
    local_platform = LocalPlatform(
        platform_id=1, couriers=local_couriers_wrapped)
    return local_platform, stations


def build_partner_platforms_with_regions(platform_ids: List[int], couriers_per_platform: int,
                                         region_map: Dict[int, Tuple[float, float, float, float]]) -> List[PartnerPlatform]:
    partners: List[PartnerPlatform] = []
    for pid in platform_ids:
        lat_min, lat_max, lng_min, lng_max = region_map[pid]
        c_list: List[CrossPlatformCourier] = []
        for j in range(couriers_per_platform):
            node = _sample_node_in_region_from_LCC(
                lat_min, lat_max, lng_min, lng_max)
            st = Station(num=pid, l_node=node)
            c = Courier(num=pid * 100 + j, location_node=node,
                        max_weight=50.0, station=st)
            c_list.append(CrossPlatformCourier(c))
        partners.append(PartnerPlatform(platform_id=pid, couriers=c_list))
    return partners


# =========================================================
# ================== 5) 拍卖（FPSA & RVA） =================
# =========================================================
def _courier_bid_fpsa(courier, task) -> float:
    p_visible = MU_1 * float(task.fare)
    delta_d, _, _ = compute_best_insert_and_detour(courier, task)
    if delta_d < 0:
        return 0.0
    g_score = getattr(courier, 'service_score', 0.5)
    bid = COURIER_BID_FLOOR + \
        (ALPHA_DETOUR * delta_d + BETA_PERF * g_score) * \
        COURIER_SHARE_GAMMA * p_visible
    return max(0.0, min(p_visible, bid))


def internal_fpsa_for_platform(platform, tasks: List[Any]) -> Dict[int, Dict[str, Any]]:
    result = {}
    for t in tasks:
        best, best_price = None, -1.0
        for cwrap in platform.couriers:
            c = getattr(cwrap, 'ref', cwrap)
            price = _courier_bid_fpsa(c, t)
            if price > best_price:
                best, best_price = c, price
        if best is not None and best_price > 0:
            result[t.num] = {'courier': best, 'p_prime': best_price}
    return result


def platform_bid_rva(all_platform_bids: Dict[int, Dict[int, Dict[str, Any]]], task) -> Tuple[int, float, List[Tuple[int, float]]]:
    bucket = []
    for pid, d in all_platform_bids.items():
        if task.num in d:
            p_prime = d[task.num]['p_prime']
            bucket.append((pid, p_prime))
    if not bucket:
        return -1, 0.0, []

    bids = []
    multi = len(bucket) >= 2
    for pid, p_prime in bucket:
        if multi:
            fP = float(COOP_QUALITY.get(pid, 1.0))
            BR = p_prime + fP * MU_2 * float(task.fare)
        else:
            BR = p_prime + MU_2 * float(task.fare)
        bids.append((pid, BR))

    bids_sorted = sorted(bids, key=lambda x: x[1])
    winner_pid, winner_bid = bids_sorted[0]
    pay_price = bids_sorted[1][1] if len(
        bids_sorted) >= 2 else bids_sorted[0][1]
    if VERBOSE:
        print(
            f"[RVA] task={task.num} winner_platform={winner_pid} winner_bid={winner_bid:.2f} pay(second)={pay_price:.2f}")
    return winner_pid, float(pay_price), bids_sorted


def settle_cross_platform(ledger: dict,
                          winner_platform_id: int,
                          winner_record: Dict[str, Any],
                          pay_price_to_platform: float,
                          task) -> Tuple[float, float, float]:
    p_tau = float(task.fare)
    p_prime = float(winner_record['p_prime'])
    local_gain = max(0.0, p_tau - MU_1 * p_tau)
    partner_gain = max(0.0, pay_price_to_platform - p_prime)
    courier_gain = p_prime

    ledger['local_revenue'] = ledger.get('local_revenue', 0.0) + local_gain
    ledger['partner_revenue'] = ledger.get(
        'partner_revenue', 0.0) + partner_gain
    ledger['courier_revenue'] = ledger.get(
        'courier_revenue', 0.0) + courier_gain
    return local_gain, partner_gain, courier_gain


# =========================================================
# ================== 6) 数据与批次组织 =====================
# =========================================================
def load_pick_tasks() -> List[Any]:
    pick_set, _ = readTask()
    if REMAP_TASKS_TO_LCC:
        remap_cnt = 0
        for t in pick_set:
            if getattr(t, 'l_node', None) not in LCC_SET:
                if remap_task_to_LCC(t):
                    remap_cnt += 1
        if VERBOSE:
            print(f"[FIX] remapped {remap_cnt}/{len(pick_set)} tasks to LCC")
    return pick_set


def make_batches_by_time(tasks: List[Any], batch_seconds: int = BATCH_SECONDS) -> List[List[Any]]:
    if not tasks:
        return []
    tasks_sorted = sorted(
        tasks, key=lambda t: float(getattr(t, "s_time", 0.0)))
    start_t = float(getattr(tasks_sorted[0], "s_time", 0.0))
    buckets = defaultdict(list)
    for t in tasks_sorted:
        st = float(getattr(t, "s_time", 0.0))
        idx = int((st - start_t) // batch_seconds)
        buckets[idx].append(t)
    batches = [buckets[i] for i in sorted(buckets.keys())]
    # ADD: 调试用批量截断（加速调试）
    if MAX_TASKS_PER_BATCH_DEBUG > 0:
        for i in range(len(batches)):
            batches[i] = batches[i][:MAX_TASKS_PER_BATCH_DEBUG]
    return batches


# =========================================================
# ================== 7) 主流程与实验打印 ===================
# =========================================================
def run_once(batch_tasks: List[Any],
             local_platform: LocalPlatform,
             partners: List[PartnerPlatform],
             time_count: int,
             metric_sink: Dict[str, list]) -> Dict[str, Any]:
    couriers_local = [ic.ref for ic in local_platform.couriers]
    result = run_cama_batch(couriers_local, batch_tasks, time_count)
    local_list = result['local_list']
    cross_candidates = result['cross_candidates']
    Th = result['threshold']
    utility_map = result['utility_map']
    detour_map = result['detour_map']
    dweight_map = result['dweight_map']

    u_vals, dd_vals, dw_vals = [], [], []
    for (t, c) in result['matched_pairs']:
        key = (t.num, id(c))
        if key in utility_map:
            u_vals.append(utility_map[key])
            dd_vals.append(detour_map[key])
            dw_vals.append(dweight_map[key])

    ledger = {'local_revenue': 0.0,
              'partner_revenue': 0.0, 'courier_revenue': 0.0}
    landed_local_pairs = apply_local_assignment(local_list)
    for (t, c) in landed_local_pairs:
        pay_courier = ZETA_LOCAL_PAYMENT_RATIO * float(t.fare)
        gain = max(0.0, float(t.fare) - pay_courier)
        ledger['local_revenue'] += gain
        ledger['courier_revenue'] += pay_courier

    registry = PlatformRegistry(local_platform, partners)
    registry.broadcast_cross_tasks(cross_candidates)

    all_fpsa: Dict[int, Dict[int, Dict[str, Any]]] = {}
    for p in partners:
        fpsa_out = internal_fpsa_for_platform(p, p.cross_task_pool)
        all_fpsa[p.platform_id] = fpsa_out

    landed_cross = 0
    fpsa_win_prices, rva_pay_prices, rva_bids_records = [], [], []

    for t in cross_candidates:
        winner_pid, pay_price, bids_sorted = platform_bid_rva(all_fpsa, t)
        if winner_pid < 0:
            continue
        win_rec = all_fpsa[winner_pid][t.num]
        win_courier = win_rec['courier']
        fpsa_win_prices.append(float(win_rec['p_prime']))
        rva_pay_prices.append(float(pay_price))
        rva_bids_records.append((t.num, bids_sorted))
        settle_cross_platform(ledger, winner_pid, win_rec, pay_price, t)

        if RECOMPUTE_INSERT_AT_PARTNER:
            _, best_idx, _ = compute_best_insert_and_detour(win_courier, t)
        else:
            _, best_idx, _ = compute_best_insert_and_detour(win_courier, t)
        if best_idx < 0 or best_idx >= len(win_courier.re_schedule):
            win_courier.re_schedule.append(t)
        else:
            win_courier.re_schedule.insert(best_idx + 1, t)
        win_courier.re_weight += t.weight
        landed_cross += 1

    metric_sink['batch_local_cnt'].append(len(landed_local_pairs))
    metric_sink['batch_cross_cnt'].append(landed_cross)
    metric_sink['batch_unassigned_cnt'].append(
        max(0, len(batch_tasks) - len(landed_local_pairs) - landed_cross))
    metric_sink['batch_local_rev'].append(ledger['local_revenue'])
    metric_sink['batch_partner_rev'].append(ledger['partner_revenue'])
    metric_sink['batch_courier_rev'].append(ledger['courier_revenue'])
    metric_sink['batch_Th'].append(Th if math.isfinite(Th) else 0.0)
    metric_sink['batch_u_mean'].append(
        float(np.mean(u_vals)) if u_vals else 0.0)
    metric_sink['batch_dd_mean'].append(
        float(np.mean(dd_vals)) if dd_vals else 0.0)
    metric_sink['batch_dw_mean'].append(
        float(np.mean(dw_vals)) if dw_vals else 0.0)
    metric_sink['batch_fpsa_win_mean'].append(
        float(np.mean(fpsa_win_prices)) if fpsa_win_prices else 0.0)
    metric_sink['batch_rva_pay_mean'].append(
        float(np.mean(rva_pay_prices)) if rva_pay_prices else 0.0)
    metric_sink['all_u'].extend(u_vals)
    metric_sink['all_dd'].extend(dd_vals)
    metric_sink['all_dw'].extend(dw_vals)
    metric_sink['all_fpsa_win'].extend(fpsa_win_prices)
    metric_sink['all_rva_pay'].extend(rva_pay_prices)

    if VERBOSE:
        print(f"[LOCAL] landed={len(landed_local_pairs)} cross_pool={len(cross_candidates)} "
              f"local_rev≈{ledger['local_revenue']:.2f}")
        print(f"[CROSS] landed_cross={landed_cross} fpsa_win_mean={np.mean(fpsa_win_prices) if fpsa_win_prices else 0:.2f} "
              f"rva_pay_mean={np.mean(rva_pay_prices) if rva_pay_prices else 0:.2f}")
        print(f"[CAMA]  Th={Th:.4f}  u_mean={np.mean(u_vals) if u_vals else 0:.4f}  "
              f"Δd_mean={np.mean(dd_vals) if dd_vals else 0:.4f}  Δw_mean={np.mean(dw_vals) if dw_vals else 0:.4f}")

    return {'landed_local': len(landed_local_pairs), 'landed_cross': landed_cross,
            'ledger': ledger, 'rva_bids_records': rva_bids_records}


def plot_and_print_final_metrics(all_tasks_cnt: int, metric_sink: Dict[str, list]) -> None:
    total_local = sum(metric_sink['batch_local_cnt'])
    total_cross = sum(metric_sink['batch_cross_cnt'])
    total_unassigned = sum(metric_sink['batch_unassigned_cnt'])
    local_rev = sum(metric_sink['batch_local_rev'])
    partner_rev = sum(metric_sink['batch_partner_rev'])
    courier_rev = sum(metric_sink['batch_courier_rev'])

    print("\n========== FINAL SUMMARY (Paper-style) ==========")
    print(
        f"Tasks: total={all_tasks_cnt} | local={total_local} | cross={total_cross} | unassigned={total_unassigned}")
    print(
        f"Revenue: local={local_rev:.2f} | partner={partner_rev:.2f} | couriers={courier_rev:.2f}")
    print(f"Means per-batch: Th={np.mean(metric_sink['batch_Th']):.4f} "
          f"| ū={np.mean(metric_sink['batch_u_mean']):.4f} "
          f"| Δd̄={np.mean(metric_sink['batch_dd_mean']):.4f} "
          f"| Δw̄={np.mean(metric_sink['batch_dw_mean']):.4f} "
          f"| FPSA p'(win)̄={np.mean(metric_sink['batch_fpsa_win_mean']):.2f} "
          f"| RVA pay(second)̄={np.mean(metric_sink['batch_rva_pay_mean']):.2f}")

    fig1 = plt.figure()
    plt.bar(['Local', 'Cross', 'Unassigned'], [
            total_local, total_cross, total_unassigned])
    plt.title('Assignments Count')
    plt.ylabel('Count')
    fig1.tight_layout()
    fig1.savefig('fig_counts.png', dpi=150)

    fig2 = plt.figure()
    x = np.arange(len(metric_sink['batch_local_rev']))
    plt.plot(x, np.cumsum(
        metric_sink['batch_local_rev']), label='Local revenue (cum)')
    plt.plot(x, np.cumsum(
        metric_sink['batch_partner_rev']), label='Partner revenue (cum)')
    plt.plot(x, np.cumsum(
        metric_sink['batch_courier_rev']), label='Courier revenue (cum)')
    plt.legend()
    plt.title('Cumulative Revenue over Batches')
    plt.xlabel('Batch index')
    plt.ylabel('Revenue')
    fig2.tight_layout()
    fig2.savefig('fig_revenue_over_batches.png', dpi=150)

    fig3 = plt.figure()
    plt.hist(metric_sink['all_u'], bins=30, alpha=0.7)
    plt.title('Utility Distribution (u)')
    plt.xlabel('u')
    plt.ylabel('Frequency')
    fig3.tight_layout()
    fig3.savefig('fig_utility_hist.png', dpi=150)

    fig4 = plt.figure()
    data = []
    labels = []
    if metric_sink['all_fpsa_win']:
        data.append(metric_sink['all_fpsa_win'])
        labels.append("FPSA p'(win)")
    if metric_sink['all_rva_pay']:
        data.append(metric_sink['all_rva_pay'])
        labels.append('RVA pay(second)')
    if data:
        plt.boxplot(data, labels=labels, showfliers=False)
        plt.title('Platform Bids and Payments')
    fig4.tight_layout()
    fig4.savefig('fig_bids_box.png', dpi=150)

    print("Saved figures: fig_counts.png, fig_revenue_over_batches.png, fig_utility_hist.png, fig_bids_box.png")


def main():
    random.seed(42)
    np.random.seed(42)

    # ADD: Windows上如需使用进程并行，建议设置 spawn；Linux/Mac 默认 fork 更快
    if PARALLEL_MODE == "process":
        try:
            multiprocessing.set_start_method('fork')
        except Exception:
            pass  # 在Windows会报错，则仍可走spawn，但成本更高

    all_pick_tasks = load_pick_tasks()
    all_tasks_cnt = len(all_pick_tasks)

    regions = _region_split_by_quartiles(NUM_PARTNER_PLATFORMS)
    local_box = regions['local']
    partner_ids = [i for i in range(2, 2 + NUM_PARTNER_PLATFORMS)]
    partner_region_map = {}
    for idx, pid in enumerate(partner_ids, start=2):
        name = f"p{pid}"
        if name not in regions:
            raise RuntimeError("Region split insufficient for partners.")
        lat_min, lat_max, lng_min, lng_max = regions[name]
        partner_region_map[pid] = (lat_min, lat_max, lng_min, lng_max)

    local_platform, stations = build_local_platform_with_regions(
        NUM_STATIONS_LOCAL, COURIERS_PER_STATION, local_box
    )
    partners = build_partner_platforms_with_regions(
        partner_ids, PARTNER_COURIERS_PER_PLATFORM, partner_region_map
    )

    batches = make_batches_by_time(all_pick_tasks, BATCH_SECONDS)
    if VERBOSE:
        print(f"[RUN] total_tasks={all_tasks_cnt} batches={len(batches)} (batch_sec={BATCH_SECONDS}) "
              f"| K_NEAREST_COURIERS={K_NEAREST_COURIERS} | PATH_ALGO={PATH_ALGO} | PARALLEL={PARALLEL_MODE}")

    metric_sink = {
        'batch_local_cnt': [], 'batch_cross_cnt': [], 'batch_unassigned_cnt': [],
        'batch_local_rev': [], 'batch_partner_rev': [], 'batch_courier_rev': [],
        'batch_Th': [], 'batch_u_mean': [], 'batch_dd_mean': [], 'batch_dw_mean': [],
        'batch_fpsa_win_mean': [], 'batch_rva_pay_mean': [],
        'all_u': [], 'all_dd': [], 'all_dw': [], 'all_fpsa_win': [], 'all_rva_pay': [],
    }

    time_cursor = 0.0
    for bi, batch in enumerate(batches):
        if VERBOSE:
            print(
                f"\n[Batch {bi+1}/{len(batches)}] size={len(batch)} t={time_cursor:.0f}s")
        _ = run_once(batch, local_platform, partners,
                     time_count=time_cursor, metric_sink=metric_sink)
        time_cursor += BATCH_SECONDS

    plot_and_print_final_metrics(all_tasks_cnt, metric_sink)


if __name__ == "__main__":
    main()
