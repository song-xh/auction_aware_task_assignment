from typing import List, Tuple, Dict, Any, Optional
from config import COOP_QUALITY
import random

class Station:
    def __init__(self, num: int, l_node: int):
        self.num = num
        self.l_node = l_node
        self.courier_set: List['Courier'] = []


class Courier:
    def __init__(self, num: int, location_node: int, max_weight: float, station: Station):
        self.num = num
        self.location = location_node
        self.station = station
        self.station_num = station.num
        self.max_weight = max_weight
        self.schedule = []
        self.re_schedule = []
        self.re_weight = 0.0
        self.reach_time = 0.0
        self.sum_useful_time = 7200.0
        self.w = random.uniform(0.3, 0.7)
        self.c = random.uniform(0.3, 0.7)
        self.service_score = random.uniform(0.5, 1.0)
        self.batch_take = 0
        # NEW: 路径缓存（逐节点推进）
        self._path_nodes: Optional[List[int]] = None
        self._path_idx: int = 0


class InnerCourier:
    def __init__(self, ref): self.ref = ref
    def __getattr__(self, k): return getattr(self.ref, k)


class CrossPlatformCourier:
    def __init__(self, ref): self.ref = ref
    def __getattr__(self, k): return getattr(self.ref, k)


class Platform:
    def __init__(self, platform_id: int, is_local: bool, couriers: List[Any], station=None):
        self.platform_id = platform_id
        self.is_local = is_local
        self.couriers = couriers
        self.station = station
        self.cross_task_pool = []

    def clear_cross_pool(self): self.cross_task_pool = []


class LocalPlatform(Platform):
    def __init__(self, platform_id: int, couriers: List[Any], station=None):
        super().__init__(platform_id, True, couriers, station)


class PartnerPlatform(Platform):
    def __init__(self, platform_id: int, couriers: List[Any], station=None):
        super().__init__(platform_id, False, couriers, station)


class PlatformRegistry:
    def __init__(self, local: LocalPlatform, partners: List[PartnerPlatform]):
        self.local = local
        self.partners = partners
        self.coop_quality = COOP_QUALITY.copy()

    def broadcast_cross_tasks(self, tasks):
        for p in self.partners:
            p.cross_task_pool = list(tasks)

    def quality_of(
        self, pid: int) -> float: return float(self.coop_quality.get(pid, 1.0))
