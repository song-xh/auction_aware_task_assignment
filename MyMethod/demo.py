import random
import math

# ---------- 1. 定义核心数据结构 ----------


class Courier:
    def __init__(self, courier_id, lat, lng, radius, quality, efficiency, customer_score):
        self.courier_id = courier_id
        self.lat = lat
        self.lng = lng
        self.radius = radius
        self.quality = quality
        self.efficiency = efficiency
        self.customer_score = customer_score


class Task:
    def __init__(self, task_id, lat, lng, weight, fare, source_platform_id):
        self.task_id = task_id
        self.lat = lat
        self.lng = lng
        self.weight = weight
        self.fare = fare
        self.source_platform_id = source_platform_id


class Platform:
    def __init__(self, platform_id, courier_set, base_price=2, beta=0.5):
        self.platform_id = platform_id
        self.courier_set = courier_set
        self.base_price = base_price
        self.beta = beta


def calculate_distance(courier, task):
    return math.sqrt((courier.lat - task.lat) ** 2 + (courier.lng - task.lng) ** 2)

# ---------- 2. 本地分配 CAMA ----------


def batch_match_cama(platform, task_pool, gamma=0.5, omega=0.5):
    assignments = []
    lcr_pool = []
    util_list = []
    utility_matrix = []

    # 计算所有快递员-任务效用
    for t in task_pool:
        row = []
        for c in platform.courier_set:
            if c.radius >= calculate_distance(c, t):
                # 效用函数：γ * 剩余质量 + (1-γ) * 服务评分
                delta_w = 1 - t.weight / 5  # 假设快递员最大负重5
                delta_perf = (c.quality + c.efficiency + c.customer_score) / 3
                utility = gamma * delta_w + (1 - gamma) * delta_perf
                row.append(utility)
            else:
                row.append(0)
        utility_matrix.append(row)
        util_list.extend([u for u in row if u > 0])

    # 计算动态阈值
    threshold = omega * (sum(util_list) / len(util_list)) if util_list else 0

    # 贪心本地分配（可换成KM，演示重点是阈值控制）
    for ti, t in enumerate(task_pool):
        best_u = max(utility_matrix[ti]) if utility_matrix[ti] else 0
        if best_u >= threshold and best_u > 0:
            ci = utility_matrix[ti].index(best_u)
            c = platform.courier_set[ci]
            assignments.append((t, c, best_u))
        else:
            lcr_pool.append(t)
    print(f"[CAMA] 平台{platform.platform_id}本地动态阈值: {threshold:.3f}")
    return assignments, lcr_pool, threshold

# ---------- 3. 跨平台分配 DAPA ----------


def first_price_bidding(platform, task):
    best_courier = None
    best_bid = float('inf')
    for courier in platform.courier_set:
        if courier.radius >= calculate_distance(courier, task):
            performance = (courier.quality + courier.efficiency +
                           courier.customer_score) / 3
            bid = platform.base_price + platform.beta * performance * platform.base_price
            if bid < best_bid:
                best_bid = bid
                best_courier = courier
    return best_courier, best_bid


def second_layer_auction(platform_list, task, cooperation_freq_matrix):
    platform_bids = []
    for plat in platform_list:
        courier, bid = first_price_bidding(plat, task)
        if courier is not None:
            freq = cooperation_freq_matrix.get(
                (plat.platform_id, task.source_platform_id), 1.0)
            final_bid = bid + (1 / freq if freq > 0 else 0)
            platform_bids.append((plat, final_bid, courier))
    if not platform_bids:
        return None, None, None, None
    platform_bids.sort(key=lambda x: x[1])
    winner_platform, winner_bid, winner_courier = platform_bids[0]
    second_price = platform_bids[1][1] if len(
        platform_bids) > 1 else winner_bid
    return winner_platform, winner_courier, second_price, platform_bids

# ---------- 4. 主流程 ----------


def main_cama_dapa(platform_list, all_task_pools, cooperation_freq_matrix, gamma=0.5, omega=0.5):
    print("\n=== 本地CAMA分配阶段 ===")
    all_local_assignments = {}
    all_Lcr = []
    for i, platform in enumerate(platform_list):
        assignments, lcr_pool, threshold = batch_match_cama(
            platform, all_task_pools[i], gamma, omega)
        all_local_assignments[platform.platform_id] = assignments
        all_Lcr.extend(lcr_pool)
        for t, c, u in assignments:
            print(
                f"[CAMA] 平台{platform.platform_id}任务{t.task_id}→快递员{c.courier_id}，效用={u:.3f}")
        print(
            f"[CAMA] 平台{platform.platform_id}本地未分配任务：{[t.task_id for t in lcr_pool]}")
    print("\n=== 跨平台DAPA拍卖阶段 ===")
    cross_assignments = []
    for task in all_Lcr:
        winner_platform, winner_courier, final_price, platform_bids = second_layer_auction(
            platform_list, task, cooperation_freq_matrix)
        print(f"[DAPA] 任务{task.task_id} 各平台报价：")
        for plat, bid, courier in platform_bids or []:
            print(
                f"    平台{plat.platform_id}（快递员{courier.courier_id}）报价：{bid:.2f}")
        if winner_platform:
            print(
                f"★[DAPA] 任务{task.task_id}由平台{winner_platform.platform_id}的快递员{winner_courier.courier_id}中标，成交价（第二价）={final_price:.2f}\n")
            cross_assignments.append(
                (task, winner_platform, winner_courier, final_price))
        else:
            print(f"×[DAPA] 任务{task.task_id}无人接单\n")
    # 结果统计
    print("\n=== 调度结果统计 ===")
    for pid, assigns in all_local_assignments.items():
        print(f"平台{pid} 本地完成任务: {[t.task_id for t, _, _ in assigns]}")
    print(f"跨平台DAPA分配完成任务: {[t.task_id for t, _, _, _ in cross_assignments]}")
    print(f"总任务数: {sum(len(tasks) for tasks in all_task_pools)}，"
          f"本地完成: {sum(len(a) for a in all_local_assignments.values())}，"
          f"跨平台完成: {len(cross_assignments)}\n")
    return all_local_assignments, cross_assignments


# ========== 5. 构造复杂测试数据 ==========
if __name__ == "__main__":
    random.seed(12345)
    # 构造3个平台，每个平台10个快递员，特征异构
    platform_list = []
    for p_id in range(3):
        courier_set = []
        for c_id in range(10):
            courier = Courier(
                courier_id=f"{p_id}-{c_id}",
                lat=100 + random.uniform(-0.5, 0.5) + p_id * 0.6,   # 平台有空间偏移
                lng=30 + random.uniform(-0.5, 0.5) + p_id * 0.6,
                radius=5 + random.uniform(-1, 1),
                quality=random.uniform(0.6, 1),
                efficiency=random.uniform(0.5, 1),
                customer_score=random.uniform(0.7, 1),
            )
            courier_set.append(courier)
        platform_list.append(
            Platform(platform_id=p_id, courier_set=courier_set))

    # 每个平台10个任务，源平台随机
    all_task_pools = []
    for p_id in range(3):
        task_pool = []
        for t_id in range(10):
            # 让每个平台的任务可能来自其他平台
            source_platform = random.choice([0, 1, 2])
            task = Task(
                task_id=f"{p_id}-{t_id}",
                lat=100 + random.uniform(-1, 1) + source_platform * 0.5,
                lng=30 + random.uniform(-1, 1) + source_platform * 0.5,
                weight=random.uniform(0.3, 4.5),
                fare=random.uniform(8, 25),
                source_platform_id=source_platform
            )
            task_pool.append(task)
        all_task_pools.append(task_pool)

    # 合作频率矩阵
    cooperation_freq_matrix = {(i, j): random.uniform(
        0.25, 1.0) if i != j else 1.0 for i in range(3) for j in range(3)}

    # 调度主程序
    main_cama_dapa(platform_list, all_task_pools,
                   cooperation_freq_matrix, gamma=0.55, omega=0.6)
