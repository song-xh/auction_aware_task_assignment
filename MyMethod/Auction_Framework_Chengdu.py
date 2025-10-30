import sys
import time
import random
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
from decimal import Decimal

import numpy as np
import matplotlib.pyplot as plt
from functools import lru_cache

from GraphUtils_ChengDu import g, s, NodeModel, VELOCITY
from Tasks_ChengDu import readTask
from MyMethod.km_matcher import KMMatcher
from DistanceUtils import DistanceUtils
from config import *
from classDefine import *


# ============ 打印
def _progress_line(prefix: str, i: int, total: int, count: int = 0):
    if total <= 0:
        return
    percent = round(float(i) / float(total) * 100.0, 2)
    sys.stdout.write(
        f"\r rate of {prefix} progress: {percent:0.2f} %%, {count}")
    sys.stdout.flush()
    time.sleep(0.0001)


def _progress_endline():
    sys.stdout.write("\n")
    sys.stdout.flush()


def _fmt_ms(x: float) -> str:
    return str(Decimal(x * 1000).quantize(Decimal('0.00')))

# ===================== LCC 计算
# 先做连通分量分析，取最大连通分量（LCC），避免不可达和无效路径

def _compute_cc(s):
    visited, comps = set(), []
    for nid in s.nMap.keys():
        if nid in visited:
            continue
        q = [nid]
        comp = {nid}
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


print(f"[GRAPH] nodes={len(s.nMap)}" + (
    f" edges={getattr(s, 'edgeNumber', 'N/A')}" if hasattr(s, 'edgeNumber') else ""))
print("[INIT] Computing connected components...")
CCS = _compute_cc(s)
if not CCS:
    raise RuntimeError("Road graph empty. 请检查 GraphUtils_ChengDu 是否已正确加载地图。")
LCC_SET = set(CCS[0])
print(f"[INIT] Components: {len(CCS)} | LCC size: {len(LCC_SET)}")

_REACH_CACHE = {}
_NODE_LATLNG_CACHE: Dict[int, Tuple[float, float]] = {}
_dist_util = DistanceUtils()


def node_latlng(nid: int) -> Tuple[float, float]:
    v = _NODE_LATLNG_CACHE.get(nid)
    if v is None:
        node = s.nMap[nid]
        v = (float(node.lat), float(node.lng))
        _NODE_LATLNG_CACHE[nid] = v
    return v


def is_reachable(a: int, b: int) -> bool:
    k = (a, b)
    if k in _REACH_CACHE:
        return _REACH_CACHE[k]
    ok = (a in LCC_SET) and (b in LCC_SET)
    _REACH_CACHE[k] = ok
    return ok


@lru_cache(maxsize=LRU_DIST_CACHE_SIZE)
def _shortest_path_len_cached(a: int, b: int) -> float:
    if a == b:
        return 0.0
    A = NodeModel()
    A.nodeId = a
    B = NodeModel()
    B.nodeId = b
    eds = g.getShortPath(A, B, s)
    if not eds:
        return -1.0
    return float(sum(e.length for e in eds))


def safe_path_len(a: int, b: int) -> Optional[float]:
    if a == b:
        return 0.0
    if not is_reachable(a, b):
        return None
    d = _shortest_path_len_cached(a, b)
    return None if d < 0 else d


def remap_task_to_LCC(task) -> bool:
    if getattr(task, 'l_node', None) in LCC_SET:
        return False
    lat = getattr(task, 'l_lat', None)
    lng = getattr(task, 'l_lng', None)
    if (lat is None or lng is None) and getattr(task, 'l_node', None) in s.nMap:
        lat, lng = node_latlng(task.l_node)
    if lat is None or lng is None:
        return False
    best, bd = None, 1e18
    SAMPLE = min(5000, len(LCC_SET))
    for nid in random.sample(tuple(LCC_SET), SAMPLE):
        nl, ng = node_latlng(nid)
        d = _dist_util.getNodeDistance(lat, lng, nl, ng)
        if d < bd:
            bd, best = d, nid
    if best is not None:
        task.l_node = best
        return True
    return False

# =================== 可行性 

def time_lower_bound_seconds(a: int, b: int) -> float:
    la, lo = node_latlng(a)
    lb, lg = node_latlng(b)
    d_m = _dist_util.getNodeDistance(la, lo, lb, lg)
    # VELOCITY（km/s）*1000 = m/s
    return d_m / max(1e-6, VELOCITY*1000.0)


def compute_best_insert_and_detour(courier, task) -> Tuple[float, int, Optional[float]]:
    """返回：delta_d, best_insert_index, extra_distance；其中 best_insert_index 的语义是：
       将任务插入到 re_schedule 中的 index 位置（即“插在 seq[index] 之前”；index==len(seq) 等价 append）。"""
    best_delta, best_idx, best_extra = -1.0, -1, None
    seq = courier.re_schedule
    if not is_reachable(courier.location, courier.station.l_node):
        return -1.0, -1, None
    if not seq:
        base = safe_path_len(courier.location, courier.station.l_node)
        a = safe_path_len(courier.location, task.l_node)
        b = safe_path_len(task.l_node, courier.station.l_node)
        if None in (base, a, b):
            return -1.0, -1, None
        denom = max(1e-6, a+b)
        return base/denom, 0, (a+b)-base
    for i in range(len(seq)):
        prev = courier.location if i == 0 else seq[i-1].l_node
        nxt = seq[i].l_node
        base = safe_path_len(prev, nxt)
        a = safe_path_len(prev, task.l_node)
        b = safe_path_len(task.l_node, nxt)
        if None in (base, a, b):
            continue
        denom = max(1e-6, a+b)
        delta = base/denom
        extra = (a+b)-base
        if delta > best_delta:
            best_delta, best_idx, best_extra = delta, i, extra
    last = seq[-1].l_node if seq else courier.location
    base = safe_path_len(last, courier.station.l_node)
    a = safe_path_len(last, task.l_node)
    b = safe_path_len(task.l_node, courier.station.l_node)
    if None not in (base, a, b):
        denom = max(1e-6, a+b)
        delta = base/denom
        extra = (a+b)-base
        if delta > best_delta:
            best_delta, best_idx, best_extra = delta, len(seq), extra
    return best_delta, best_idx, best_extra


def compute_delta_weight(courier, task) -> float:
    denom = max(1e-6, courier.max_weight)
    val = 1.0-(courier.re_weight+task.weight)/denom
    return max(-10.0, min(10.0, val))

# 计算效用
def compute_utility(courier, task, gamma=GAMMA_UTILITY):
    delta_d, best_idx, extra = compute_best_insert_and_detour(courier, task)
    if delta_d < 0 or extra is None:
        return -1e9, -1, None, -1e9, -1e9
    delta_w = compute_delta_weight(courier, task)
    u = gamma*delta_w + (1.0-gamma)*delta_d
    return float(u), best_idx, float(extra), float(delta_d), float(delta_w)


def topk_couriers_for_task(task, couriers, k):
    tlat, tlng = node_latlng(task.l_node)
    pairs = []
    for c in couriers:
        if getattr(c, 'batch_take', 0) >= MAX_TASKS_PER_COURIER_PER_BATCH:
            continue
        clat, clng = node_latlng(c.location)
        d = _dist_util.getNodeDistance(tlat, tlng, clat, clng)
        pairs.append((d, c))
    pairs.sort(key=lambda x: x[0])
    return [c for _, c in pairs[:min(k, len(pairs))]]

# candidate（CAND） 枚举
def enumerate_candidates(couriers, tasks, time_count: int):
    cands = []
    total = len(tasks)
    start = time.time()
    last_print_t = start
    for idx, t in enumerate(tasks, 1):
        cand_cs = topk_couriers_for_task(t, couriers, K_NEAREST_COURIERS)
        for c in cand_cs:
            if c.re_weight + t.weight > c.max_weight:
                continue
            tlb = time_lower_bound_seconds(c.location, t.l_node)
            if time_count + tlb > float(t.d_time):
                continue
            u, ins, extra, dd, dw = compute_utility(c, t)
            if u < -1e8 or extra is None:
                continue
            extra_time = extra / max(1e-6, VELOCITY*1000.0)
            if time_count + extra_time <= float(t.d_time):
                cands.append((t, c, u, ins, extra, dd, dw))
        if (idx % PRINT_HEARTBEAT_N == 0) or (time.time()-last_print_t >= PRINT_HEARTBEAT_SEC):
            _progress_line("CAND", idx, total, len(cands))
            last_print_t = time.time()
    _progress_line("CAND", total, total, len(cands))
    _progress_endline()
    return cands, (time.time()-start)

# ========== KM 矩阵 ==========


def build_mats(tasks, couriers, cands):
    n, m = len(tasks), len(couriers)
    W = np.full((n, m), -1e9, dtype=float)
    ti = {id(t): i for i, t in enumerate(tasks)}
    ci = {id(c): j for j, c in enumerate(couriers)}
    last_print_t = time.time()
    for k, (t, c, u, ins, extra, dd, dw) in enumerate(cands, 1):
        W[ti[id(t)], ci[id(c)]] = float(u)
        if (k % (PRINT_HEARTBEAT_N*2) == 0) or (time.time()-last_print_t >= PRINT_HEARTBEAT_SEC):
            _progress_line("KM-MAT", k, len(cands), k)
            last_print_t = time.time()
    if len(cands) > 0:
        _progress_line("KM-MAT", len(cands), len(cands), len(cands))
        _progress_endline()
    return W

# ========== KM/贪心 指派 ==========


def km_assign(tasks, couriers, W):
    try:
        print("[STEP] KM 求解（最大权匹配）...")
        matcher = KMMatcher(W.copy())
        matches = matcher.solve()
        pairs = []
        for (i, j) in matches:
            if 0 <= i < len(tasks) and 0 <= j < len(couriers) and W[i, j] > -1e8:
                pairs.append((tasks[i], couriers[j]))
        print(f"[OK] KM 完成，匹配对数={len(pairs)}")
        return pairs
    except Exception:
        print("[WARN] KM 退化为贪心排序匹配（打印进度）")
        order = np.dstack(np.unravel_index(
            np.argsort(W.ravel())[::-1], W.shape))[0]
        used_rows = set()
        used_cols = set()
        pairs = []
        last_print_t = time.time()
        total = len(order)
        for k, (i, j) in enumerate(order, 1):
            if W[i, j] < -1e8:
                break
            if (i in used_rows) or (j in used_cols):
                continue
            used_rows.add(i)
            used_cols.add(j)
            pairs.append((tasks[i], couriers[j]))
            if (k % (PRINT_HEARTBEAT_N*10) == 0) or (time.time()-last_print_t >= PRINT_HEARTBEAT_SEC):
                _progress_line("KM-GREEDY", k, total, len(pairs))
                last_print_t = time.time()
        _progress_line("KM-GREEDY", total, total, len(pairs))
        _progress_endline()
        return pairs


def greedy_assign_from_candidates(tasks, couriers, cands):
    cands_sorted = sorted(cands, key=lambda x: x[2], reverse=True)
    used_task = set()
    used_courier = set()
    pairs = []
    last_print_t = time.time()
    total = len(cands_sorted)
    for k, (t, c, u, ins, extra, dd, dw) in enumerate(cands_sorted, 1):
        if id(t) in used_task or id(c) in used_courier:
            continue
        used_task.add(id(t))
        used_courier.add(id(c))
        pairs.append((t, c))
        if (k % (PRINT_HEARTBEAT_N*5) == 0) or (time.time()-last_print_t >= PRINT_HEARTBEAT_SEC):
            _progress_line("GREEDY", k, total, len(pairs))
            last_print_t = time.time()
    if total > 0:
        _progress_line("GREEDY", total, total, len(pairs))
        _progress_endline()
    return pairs

# ========== 落地 ==========

# 计算阈值
def compute_threshold(matched_pairs, utility_map, omega=OMEGA_THRESHOLD):
    if not matched_pairs:
        return float('inf')
    vs = [utility_map[(id(t), id(c))]
          for (t, c) in matched_pairs if (id(t), id(c)) in utility_map]
    if not vs:
        return float('inf')
    return omega * (sum(vs)/len(vs))


def split_local_or_cross(matched_pairs, utility_map, best_idx_map, omega=OMEGA_THRESHOLD):
    Th = compute_threshold(matched_pairs, utility_map, omega)
    local_list, cross_list = [], []
    for (t, c) in matched_pairs:
        u = utility_map.get((id(t), id(c)), -1e9)
        if u >= Th:
            local_list.append((t, c, best_idx_map.get((id(t), id(c)), -1)))
        else:
            cross_list.append(t)
    return local_list, cross_list, Th


def apply_local_assignment(local_list):
    """[FIX] 插入语义：best_idx = 插入到 seq[best_idx] 之前；best_idx==len(seq) 等价 append。"""
    landed = []
    for (t, c, idx) in local_list:
        if idx is None or idx < 0 or idx > len(c.re_schedule):
            c.re_schedule.append(t)
        else:
            # FIX: 去掉原来的 +1，实现“可插在第一位”
            c.re_schedule.insert(idx, t)   # <-- 关键修复
        c.re_weight += t.weight
        c.batch_take = getattr(c, 'batch_take', 0) + 1
        landed.append((t, c))
    return landed


def _kmeans_ll(points: np.ndarray, k: int, max_iters: int = 15) -> np.ndarray:
    N = points.shape[0]
    if N == 0:
        return np.zeros((k, 2), dtype=float)
    idx = np.random.choice(N, size=min(k, N), replace=False)
    centers = points[idx].copy()
    for _ in range(max_iters):
        dists = np.square(points[:, None, :] - centers[None, :, :]).sum(axis=2)
        lab = np.argmin(dists, axis=1)
        new = []
        for j in range(centers.shape[0]):
            grp = points[lab == j]
            new.append(grp.mean(axis=0) if len(grp) > 0 else centers[j])
        new = np.stack(new, axis=0)
        if np.allclose(new, centers):
            break
        centers = new
    return centers


def _nearest_LCC_node(lat: float, lng: float) -> int:
    best = None
    bd = 1e18
    SAMPLE = min(10000, len(LCC_SET))
    for nid in random.sample(tuple(LCC_SET), SAMPLE):
        nl, ng = node_latlng(nid)
        d = _dist_util.getNodeDistance(lat, lng, nl, ng)
        if d < bd:
            bd, best = d, nid
    return best if best is not None else random.choice(tuple(LCC_SET))


def _extract_points(tasks: List[Any]) -> np.ndarray:
    pts = []
    for t in tasks:
        if getattr(t, 'l_node', None) in s.nMap:
            lat, lng = node_latlng(t.l_node)
            pts.append((lat, lng))
    return np.array(pts, dtype=float) if pts else np.zeros((0, 2), dtype=float)


def build_local_platform_from_data(tasks_for_seeding: List[Any],
                                   num_stations: int,
                                   couriers_per_station: int) -> Tuple[LocalPlatform, List[Station]]:
    pts = _extract_points(tasks_for_seeding)
    if len(pts) == 0:
        stations = []
        inner = []
        for i in range(num_stations):
            nid = random.choice(tuple(LCC_SET))
            st = Station(i, nid)
            stations.append(st)
            for j in range(couriers_per_station):
                node = random.choice(tuple(LCC_SET))
                c = Courier(i*1000+j, node, 50.0, st)
                st.courier_set.append(c)
                inner.append(InnerCourier(c))
        return LocalPlatform(1, inner), stations
    centers = _kmeans_ll(pts, num_stations, KMEANS_MAX_ITERS)
    stations = []
    inner = []
    for i, (lat, lng) in enumerate(centers):
        nid = _nearest_LCC_node(lat, lng)
        st = Station(i, nid)
        stations.append(st)
        for j in range(couriers_per_station):
            node = _nearest_LCC_node(
                lat+(random.random()-0.5)*0.002, lng+(random.random()-0.5)*0.002)
            c = Courier(i*1000+j, node, 50.0, st)
            st.courier_set.append(c)
            inner.append(InnerCourier(c))
    return LocalPlatform(1, inner), stations


def build_partner_platforms_from_data(tasks_for_seeding: List[Any],
                                      platform_ids: List[int],
                                      couriers_per_platform: int) -> List[PartnerPlatform]:
    pts = _extract_points(tasks_for_seeding)
    partners = []
    if len(pts) == 0:
        for pid in platform_ids:
            lst = []
            for j in range(couriers_per_platform):
                node = random.choice(tuple(LCC_SET))
                st = Station(pid, node)
                c = Courier(pid*10000+j, node, 50.0, st)
                lst.append(CrossPlatformCourier(c))
            partners.append(PartnerPlatform(pid, lst))
        return partners
    centers = _kmeans_ll(pts, len(platform_ids)*2, KMEANS_MAX_ITERS)
    ci = 0
    for pid in platform_ids:
        cwrap = []
        for _ in range(2):
            if ci >= len(centers):
                break
            lat, lng = centers[ci]
            ci += 1
            for j in range(couriers_per_platform//2):
                node = _nearest_LCC_node(
                    lat+(random.random()-0.5)*0.003, lng+(random.random()-0.5)*0.003)
                st = Station(pid, node)
                c = Courier(pid*10000+j, node, 50.0, st)
                cwrap.append(CrossPlatformCourier(c))
        partners.append(PartnerPlatform(pid, cwrap))
    return partners

# ========== 拍卖（FPSA & RVA） ==========


def _courier_bid_fpsa(courier, task) -> float:
    p_visible = MU_1 * float(task.fare)
    delta_d, ins, extra = compute_best_insert_and_detour(courier, task)
    if delta_d < 0 or extra is None:
        return 0.0
    extra_time = extra / max(1e-6, VELOCITY*1000.0)
    cost = LAMBDA_D * extra + LAMBDA_T * extra_time
    g_score = getattr(courier, 'service_score', 0.5)
    raw = THETA_BID * p_visible * (0.5 + 0.5*g_score) - cost
    bid = max(0.0, min(p_visible, raw))
    return bid


def internal_fpsa_for_platform(platform, tasks) -> Dict[int, Dict[str, Any]]:
    out = {}
    total = len(tasks)
    wins = 0
    last_print_t = time.time()
    for i, t in enumerate(tasks, 1):
        best = None
        best_price = -1.0
        for cwrap in platform.couriers:
            c = getattr(cwrap, 'ref', cwrap)
            price = _courier_bid_fpsa(c, t)
            if price > best_price:
                best, best_price = c, price
        if best is not None and best_price > 0:
            out[t.num] = {'courier': best, 'p_prime': best_price}
            wins += 1
        if (i % PRINT_HEARTBEAT_N == 0) or (time.time()-last_print_t >= PRINT_HEARTBEAT_SEC):
            _progress_line(f"FPSA P{platform.platform_id}", i, total, wins)
            last_print_t = time.time()
    _progress_line(f"FPSA P{platform.platform_id}", total, total, wins)
    _progress_endline()
    return out


def platform_bid_rva(all_platform_bids: Dict[int, Dict[int, Dict[str, Any]]], task):
    bucket = []
    for pid, d in all_platform_bids.items():
        if task.num in d:
            bucket.append((pid, d[task.num]['p_prime']))
    if not bucket:
        return -1, 0.0, []
    bids = []
    multi = len(bucket) >= 2
    for pid, p_prime in bucket:
        BR = p_prime + MU_2 * \
            float(task.fare) * \
            (float(COOP_QUALITY.get(pid, 1.0)) if multi else 1.0)
        bids.append((pid, BR))
    bids.sort(key=lambda x: x[1])
    winner_pid, winner_bid = bids[0]
    pay_price = bids[1][1] if len(bids) >= 2 else bids[0][1]
    return winner_pid, float(pay_price), bids


def settle_cross_platform(ledger, winner_pid: int, winner_record: Dict[str, Any], pay_price: float, task):
    p_tau = float(task.fare)
    p_prime = float(winner_record['p_prime'])
    local_gain = max(0.0, p_tau - MU_1*p_tau)
    partner_gain = max(0.0, pay_price - p_prime)
    courier_gain = p_prime
    ledger['local_revenue'] = ledger.get('local_revenue', 0.0)+local_gain
    ledger['partner_revenue'] = ledger.get('partner_revenue', 0.0)+partner_gain
    ledger['courier_revenue'] = ledger.get('courier_revenue', 0.0)+courier_gain

# ========== 数据/批组织 ==========


def load_pick_tasks() -> List[Any]:
    pick_set, _ = readTask()
    if not pick_set:
        raise RuntimeError("未读到任何任务。请检查 Tasks_ChengDu 是否已正确读取订单目录。")
    if REMAP_TASKS_TO_LCC:
        remap_cnt = 0
        for t in pick_set:
            if getattr(t, 'l_node', None) not in LCC_SET:
                if remap_task_to_LCC(t):
                    remap_cnt += 1
        print(f"[FIX] remapped {remap_cnt}/{len(pick_set)} tasks to LCC")
    print(f"[OK] tasks={len(pick_set)}")
    return pick_set


def make_batches_by_time(tasks: List[Any], batch_seconds: int) -> List[List[Any]]:
    tasks_sorted = sorted(
        tasks, key=lambda t: float(getattr(t, "s_time", 0.0)))
    start = float(getattr(tasks_sorted[0], "s_time", 0.0))
    buckets = defaultdict(list)
    for t in tasks_sorted:
        st = float(getattr(t, "s_time", 0.0))
        idx = int((st-start)//batch_seconds)
        buckets[idx].append(t)
    batches = [buckets[i] for i in sorted(buckets.keys())]
    print(f"[OK] batches={len(batches)} (batch_sec={batch_seconds})")
    return batches

# ========== 本地阶段（每小步多轮；KM/贪心二选一） 


def _local_phase_step(tasks_arrived, couriers_local, time_count, max_rounds: int):
    landed_all = []
    remaining_tasks = list(tasks_arrived)
    Th_last = None
    for r in range(1, max_rounds+1):
        if not remaining_tasks:
            break
        print(
            f"[STEP] Local | step-round {r} | arrived={len(remaining_tasks)}")
        cands, _ = enumerate_candidates(
            couriers_local, remaining_tasks, time_count)
        if not cands:
            print("[INFO] Local | 无候选，可行性约束导致终止本小步。")
            break

        U = {(id(t), id(c)): u for (t, c, u, ins, extra, dd, dw) in cands}
        best_idx_map = {(id(t), id(c)): ins for (
            t, c, u, ins, extra, dd, dw) in cands}

        if USE_KM_FOR_LOCAL:
            W = build_mats(remaining_tasks, couriers_local, cands)
            pairs = km_assign(remaining_tasks, couriers_local, W)
        else:
            pairs = greedy_assign_from_candidates(
                remaining_tasks, couriers_local, cands)

        local_list, cross_list_tmp, Th = split_local_or_cross(
            pairs, U, best_idx_map)
        Th_last = Th
        landed_local = apply_local_assignment(local_list)
        landed_all.extend(landed_local)

        assigned_set = set(id(t) for (t, _) in landed_local)
        remaining_tasks = [
            t for t in remaining_tasks if id(t) not in assigned_set]
        print(
            f"[ROUND] Local landed={len(landed_local)} | remain_after_local={len(remaining_tasks)}")

        if len(landed_local) == 0:
            print("[INFO] Local | 本轮无增量，结束本小步局部轮。")
            break
    return landed_all, remaining_tasks, Th_last

# ========== 跨平台阶段（每小步对剩余进行 FPSA+RVA）


def _cross_phase_step(remaining_tasks, partners, time_count, ledger):
    reg = PlatformRegistry(None, partners)
    reg.broadcast_cross_tasks(remaining_tasks)
    all_fpsa = {}
    for p in partners:
        all_fpsa[p.platform_id] = internal_fpsa_for_platform(
            p, p.cross_task_pool)
    landed_cross = 0
    fpsa_win = []
    rva_pay = []
    assigned_tasks = []
    total = len(remaining_tasks)
    last_print_t = time.time()
    for i, t in enumerate(remaining_tasks, 1):
        winner_pid, pay_price, bids_sorted = platform_bid_rva(all_fpsa, t)
        if winner_pid >= 0:
            rec = all_fpsa[winner_pid][t.num]
            win_courier = rec['courier']
            settle_cross_platform(ledger, winner_pid, rec, pay_price, t)
            fpsa_win.append(float(rec['p_prime']))
            rva_pay.append(float(pay_price))
            _, idx, _ = compute_best_insert_and_detour(win_courier, t)
            # FIX: 插入语义一致，直接 insert(idx, t)
            if idx is None or idx < 0 or idx > len(win_courier.re_schedule):
                win_courier.re_schedule.append(t)
            else:
                win_courier.re_schedule.insert(idx, t)   # <-- 关键修复
            win_courier.re_weight += t.weight
            win_courier.batch_take = getattr(win_courier, 'batch_take', 0)+1
            landed_cross += 1
            assigned_tasks.append(t)
        if (i % PRINT_HEARTBEAT_N == 0) or (time.time()-last_print_t >= PRINT_HEARTBEAT_SEC):
            _progress_line("RVA", i, total, landed_cross)
            last_print_t = time.time()
    if total > 0:
        _progress_line("RVA", total, total, landed_cross)
        _progress_endline()
    return landed_cross, fpsa_win, rva_pay, assigned_tasks

# ========== 位置推进


def _ensure_path_to_target(courier: 'Courier', target_node: int):
    """若当前缓存不存在或目标变了，则用 getShortPath 重建“节点序列”缓存。"""
    if getattr(courier, '_path_nodes', None):
        if courier._path_nodes and courier._path_nodes[-1] == target_node:
            return
    A = NodeModel()
    A.nodeId = courier.location
    B = NodeModel()
    B.nodeId = target_node
    eds = g.getShortPath(A, B, s)
    if not eds:
        courier._path_nodes = [courier.location, target_node]
    else:
        nodes = [courier.location]
        for e in eds:
            # 尝试获取终点节点 ID；如你的 Edge 模型字段不同，请按实际替换
            v = getattr(e, 'eNodeId', None)
            if v is None:
                v = getattr(e, 'toId', None)
            if v is None:
                v = target_node
            nodes.append(v)
        if nodes[-1] != target_node:
            nodes.append(target_node)
        courier._path_nodes = nodes
    courier._path_idx = 1  # 下一目标是 path_nodes[1]


def _advance_one_target(courier: 'Courier', target_node: int, move_dist: float) -> Tuple[int, float, bool]:
    """基于“节点序列”推进：从 courier.location 沿 path_nodes 逐节点前进。
       返回：(new_location, used_distance, reached_target)"""
    _ensure_path_to_target(courier, target_node)
    if courier.location == target_node:
        return courier.location, 0.0, True
    used = 0.0
    while move_dist - used > 1e-6 and courier._path_idx < len(courier._path_nodes):
        u = courier.location
        v = courier._path_nodes[courier._path_idx]
        seg = safe_path_len(u, v)
        if seg is None or seg <= 0:
            # 防御：跳到 v
            courier.location = v
            courier._path_idx += 1
            continue
        if used + seg <= move_dist + 1e-6:
            # 可以整段走完，跳到 v
            used += seg
            courier.location = v
            courier._path_idx += 1
            if v == target_node:
                return courier.location, used, True
        else:
            # 不足以走完整段：保守近似，直接跳到 v（避免引入边几何）
            courier.location = v
            used = move_dist
            break
    return courier.location, used, (courier.location == target_node)


def advance_couriers(couriers: List['Courier'], step_seconds: int):
    """
    在每小步结束时推进骑手：
      - 目标为 re_schedule[0].l_node；若空则目标为 station.l_node；
      - 达到目标即弹出任务并继续向下一个目标推进；
      - reach_time 累计行驶时间（s）。
    """
    speed_mps = VELOCITY * 1000.0  # m/s
    move_dist_total = max(0.0, speed_mps * step_seconds)
    for c in couriers:
        remain = move_dist_total
        if not hasattr(c, 'station') or c.station is None:
            c.reach_time += step_seconds
            continue
        while remain > 1e-6:
            if len(c.re_schedule) > 0:
                target_node = c.re_schedule[0].l_node
                is_task_target = True
            else:
                target_node = c.station.l_node
                is_task_target = False

            if c.location == target_node:
                if is_task_target:
                    c.re_schedule.pop(0)
                    c._path_nodes = None  # 目标完成，路径失效
                else:
                    break
                continue

            new_loc, used, reached = _advance_one_target(
                c, target_node, remain)
            time_used = used / max(1e-6, speed_mps)
            c.reach_time += time_used
            remain -= used

            if reached and is_task_target:
                c.re_schedule.pop(0)
                c._path_nodes = None
            if reached and not is_task_target:
                break

        if remain > 1e-6:
            c.reach_time += remain / max(1e-6, speed_mps)

# =================== Baseline（仅本地，小步推进 + 位置推进）


def run_baseline_local_time_stepped(batch_idx: int, batch_tasks, local_platform, base_time: float, sink: Dict[str, list]):
    start = time.time()
    couriers_local = [ic.ref for ic in local_platform.couriers]
    for c in couriers_local:
        c.batch_take = 0

    t0 = min(float(getattr(t, "s_time", 0.0))
             for t in batch_tasks) if batch_tasks else base_time
    t_end = t0 + BATCH_SECONDS
    unassigned = list(batch_tasks)
    assigned_local_cnt = 0

    step_no = 0
    while t0 < t_end and unassigned:
        step_no += 1
        arrived = [t for t in unassigned if float(
            getattr(t, "s_time", 0.0)) <= t0]
        if len(arrived) > MAX_TASKS_PER_STEP:
            arrived = arrived[:MAX_TASKS_PER_STEP]
        if not arrived:
            advance_couriers(couriers_local, STEP_SECONDS)
            t0 += STEP_SECONDS
            continue

        print(
            f"[STEP][Baseline] batch={batch_idx} step={step_no} t={int(t0)}s | arrived={len(arrived)} | unassigned={len(unassigned)}")

        landed_local, remaining_after_local, _ = _local_phase_step(
            arrived, couriers_local, time_count=t0, max_rounds=MAX_ASSIGN_ROUNDS_PER_STEP)

        assigned_set = set(id(t) for (t, _) in landed_local)
        unassigned = [t for t in unassigned if id(t) not in assigned_set]
        assigned_local_cnt += len(landed_local)

        advance_couriers(couriers_local, STEP_SECONDS)
        t0 += STEP_SECONDS

    local_revenue = 0.0
    for c in couriers_local:
        for t in c.re_schedule:
            pay = ZETA_LOCAL_PAYMENT_RATIO * float(t.fare)
            local_revenue += max(0.0, float(t.fare)-pay)

    elapsed = time.time()-start
    sucess_num = assigned_local_cnt
    failed_num = len(batch_tasks)-sucess_num
    sucess_rate = Decimal(
        (sucess_num / max(1, len(batch_tasks)))*100).quantize(Decimal('0.00'))
    print("Baseline Result: 完成:%-5s 未分配:%-5s 完成率:%-5s%% 本地收益:%-10.2f 耗时(ms):%-8s"
          % (sucess_num, failed_num, sucess_rate, local_revenue, _fmt_ms(elapsed)))

    sink['bl_local_cnt'].append(sucess_num)
    sink['bl_unassigned_cnt'].append(failed_num)
    sink['bl_local_rev'].append(local_revenue)

# =================== Multi-Platform（本地+跨平台，小步推进 + 位置推进） 


def run_multiplatform_time_stepped(batch_idx: int, batch_tasks, local_platform, partners, base_time: float, sink: Dict[str, list]):
    start = time.time()
    couriers_local = [ic.ref for ic in local_platform.couriers]
    for c in couriers_local:
        c.batch_take = 0
    for p in partners:
        for cw in p.couriers:
            ref = getattr(cw, 'ref', cw)
            ref.batch_take = 0

    ledger = {'local_revenue': 0.0,
              'partner_revenue': 0.0, 'courier_revenue': 0.0}

    t0 = min(float(getattr(t, "s_time", 0.0))
             for t in batch_tasks) if batch_tasks else base_time
    t_end = t0 + BATCH_SECONDS
    unassigned = list(batch_tasks)

    assigned_local_cnt = 0
    assigned_cross_cnt = 0
    fpsa_win_all = []
    rva_pay_all = []

    step_no = 0
    while t0 < t_end and unassigned:
        step_no += 1
        arrived = [t for t in unassigned if float(
            getattr(t, "s_time", 0.0)) <= t0]
        if len(arrived) > MAX_TASKS_PER_STEP:
            arrived = arrived[:MAX_TASKS_PER_STEP]
        if not arrived:
            advance_couriers(couriers_local, STEP_SECONDS)
            for p in partners:
                advance_couriers([cw.ref for cw in p.couriers], STEP_SECONDS)
            t0 += STEP_SECONDS
            continue

        print(
            f"[STEP][CAMA] batch={batch_idx} step={step_no} t={int(t0)}s | arrived={len(arrived)} | unassigned={len(unassigned)}")

        # 1) 本地阶段：小步内多轮 KM/贪心
        landed_local, remaining_after_local, Th = _local_phase_step(
            arrived, couriers_local, time_count=t0, max_rounds=MAX_ASSIGN_ROUNDS_PER_STEP)
        assigned_local_cnt += len(landed_local)

        local_assigned_set = set(id(t) for (t, _) in landed_local)
        unassigned = [t for t in unassigned if id(t) not in local_assigned_set]

        cross_candidates = [t for t in remaining_after_local if id(
            t) not in local_assigned_set]

        # 2) 跨平台阶段：FPSA + RVA（仅对本小步的剩余）
        if cross_candidates:
            landed_cross, fpsa_win, rva_pay, assigned_tasks = _cross_phase_step(
                cross_candidates, partners, time_count=t0, ledger=ledger)
            assigned_cross_cnt += landed_cross
            fpsa_win_all.extend(fpsa_win)
            rva_pay_all.extend(rva_pay)
            if assigned_tasks:
                remove_ids = set(id(x) for x in assigned_tasks)
                unassigned = [t for t in unassigned if id(t) not in remove_ids]

        # 3) 本小步结束：推进位置（本地与合作平台骑手）
        advance_couriers(couriers_local, STEP_SECONDS)
        for p in partners:
            advance_couriers([cw.ref for cw in p.couriers], STEP_SECONDS)

        t0 += STEP_SECONDS

    # 4) 批末收益：把“本地内完成”的也累到账本（跨平台在 settle 中已加过）
    for c in couriers_local:
        for t in c.re_schedule:
            pay = ZETA_LOCAL_PAYMENT_RATIO * float(t.fare)
            ledger['local_revenue'] += max(0.0, float(t.fare)-pay)
            ledger['courier_revenue'] += pay

    elapsed = time.time()-start
    sucess_num = assigned_local_cnt + assigned_cross_cnt
    failed_num = len(batch_tasks)-sucess_num
    sucess_rate = Decimal(
        (sucess_num / max(1, len(batch_tasks)))*100).quantize(Decimal('0.00'))
    avg_time_all = Decimal(
        (elapsed / max(1, len(batch_tasks)))*1000).quantize(Decimal('0.00'))
    avg_time_succ = Decimal((elapsed / max(1, sucess_num))
                            * 1000).quantize(Decimal('0.00'))
    sum_time_ms = Decimal(elapsed*1000).quantize(Decimal('0.00'))
    f_sum_bidding = Decimal(sum(fpsa_win_all)).quantize(Decimal('0.00'))
    each_bidding = Decimal((sum(fpsa_win_all)/max(1, assigned_cross_cnt))).quantize(
        Decimal('0.00')) if assigned_cross_cnt > 0 else Decimal('0.00')

    print("\nCAMA+Auction Result:-------------------------")
    print("程序总耗时:%-10s,完成任务个数:%-5s,总失败个数:%-5s,任务完成率:%-5s%%,"
          "所有均耗时:%-8sms,成功均耗时:%-8sms,所有总耗时:%-10sms,批处理耗时:%-8sms,"
          "任务均报价:%-5s,平台总报价:%-10s,平台总收益:%-10s" %
          (sum_time_ms, sucess_num, failed_num, sucess_rate,
           avg_time_all, avg_time_succ, sum_time_ms, sum_time_ms,
           each_bidding, f_sum_bidding, Decimal(ledger['local_revenue']).quantize(Decimal('0.00'))))

    sink['mp_local_cnt'].append(assigned_local_cnt)
    sink['mp_cross_cnt'].append(assigned_cross_cnt)
    sink['mp_unassigned_cnt'].append(max(0, len(batch_tasks)-sucess_num))
    sink['mp_local_rev'].append(ledger['local_revenue'])
    sink['mp_partner_rev'].append(ledger['partner_revenue'])
    sink['mp_courier_rev'].append(ledger['courier_revenue'])

# =================== 结果与图表 ===================


def finalize_and_plot(total_tasks: int, sink: Dict[str, list], run_baseline: bool):
    print("\n========== FINAL SUMMARY ==========")
    if run_baseline:
        print(f"[Baseline-LocalOnly] tasks={total_tasks} "
              f"| local={sum(sink['bl_local_cnt'])} "
              f"| unassigned={sum(sink['bl_unassigned_cnt'])} "
              f"| local_revenue={sum(sink['bl_local_rev']):.2f}")
    print(f"[Multi-Platform] tasks={total_tasks} "
          f"| local={sum(sink['mp_local_cnt'])} "
          f"| cross={sum(sink['mp_cross_cnt'])} "
          f"| unassigned={sum(sink['mp_unassigned_cnt'])} "
          f"| local_revenue={sum(sink['mp_local_rev']):.2f} "
          f"| partner_revenue={sum(sink['mp_partner_rev']):.2f} "
          f"| courier_revenue={sum(sink['mp_courier_rev']):.2f}")
    if run_baseline:
        gain = sum(sink['mp_local_rev']) - sum(sink['bl_local_rev'])
        print(f"===> Δ Local Revenue (MP - Baseline) = {gain:.2f}")

    plt.figure()
    plt.bar(['Local', 'Cross', 'Unassigned'],
            [sum(sink['mp_local_cnt']), sum(sink['mp_cross_cnt']), sum(sink['mp_unassigned_cnt'])])
    plt.title('Assignments Count')
    plt.ylabel('Count')
    plt.tight_layout()
    plt.savefig('fig_counts.png', dpi=150)

    x = np.arange(max(len(sink['mp_local_rev']), 1))
    plt.figure()
    if run_baseline and len(sink['bl_local_rev']) > 0:
        xb = np.arange(len(sink['bl_local_rev']))
        plt.plot(xb, np.cumsum(sink['bl_local_rev']),
                 label='Baseline Local (cum)')
    if len(sink['mp_local_rev']) > 0:
        plt.plot(np.arange(len(sink['mp_local_rev'])), np.cumsum(
            sink['mp_local_rev']), label='MP Local (cum)')
        plt.plot(np.arange(len(sink['mp_partner_rev'])), np.cumsum(
            sink['mp_partner_rev']), label='MP Partner (cum)')
        plt.plot(np.arange(len(sink['mp_courier_rev'])), np.cumsum(
            sink['mp_courier_rev']), label='MP Courier (cum)')
    plt.legend()
    plt.title('Cumulative Revenue')
    plt.xlabel('Batch')
    plt.ylabel('Revenue')
    plt.tight_layout()
    plt.savefig('revenue_over_batches.png', dpi=150)
    print("Saved: fig_counts.png, revenue_over_batches.png")

# =================== main ===================


def main():
    print("Divide执行了")
    if not getattr(s, 'nMap', None) or len(s.nMap) == 0:
        raise RuntimeError("路网为空，请检查 GraphUtils_ChengDu 是否已正确加载地图数据。")
    print("finish")

    print("[STEP] 读取任务集...")
    all_tasks = load_pick_tasks()
    print("[STEP] 任务按时间分批 ...")
    batches = make_batches_by_time(all_tasks, BATCH_SECONDS)

    warmup = [t for bi, b in enumerate(
        batches) if bi < WARMUP_BATCHES_FOR_SEEDING for t in b]
    local_platform, stations = build_local_platform_from_data(
        warmup, NUM_STATIONS_LOCAL, COURIERS_PER_STATION)
    partner_ids = [i for i in range(2, 2+NUM_PARTNER_PLATFORMS)]
    partners = build_partner_platforms_from_data(
        warmup, partner_ids, PARTNER_COURIERS_PER_PLATFORM)

    sink = {
        'mp_local_cnt': [], 'mp_cross_cnt': [], 'mp_unassigned_cnt': [],
        'mp_local_rev': [], 'mp_partner_rev': [], 'mp_courier_rev': [],
        'bl_local_cnt': [], 'bl_unassigned_cnt': [], 'bl_local_rev': [],
    }

    batches_n = len(batches)
    for bi, batch in enumerate(batches, 1):
        print(f"\n[Batch {bi}/{batches_n}] size={len(batch)}")
        # Baseline：仅本地，小步推进 + 位置推进
        if RUN_BASELINE_LOCAL_ONLY:
            run_baseline_local_time_stepped(
                bi, batch, local_platform, base_time=0.0, sink=sink)
        # Multi-Platform：本地+跨平台，小步推进 + 位置推进
        run_multiplatform_time_stepped(
            bi, batch, local_platform, partners, base_time=0.0, sink=sink)

    finalize_and_plot(len(all_tasks), sink, RUN_BASELINE_LOCAL_ONLY)
    print("All rounds are over!!!")


if __name__ == "__main__":
    main()
