class Courier:
    def __init__(self, num: int, location, schedule, weight, station_num, preferences):
        """

        :param num: 编号
        :param location: 位置
        :param schedule: 时间表
        """
        # 快递员编号
        self.num = num
        # 快递员当前位置
        self.location = location
        # 快递员虚拟位置（计算快递员到达某个节点的时间时使用）
        self.temp_location = self.location
        # 快递员最大容量
        # 调参：快递员背包容量
        self.max_weight = parameter_capacity_c
        # 快递员实际负载
        self.re_weight = weight
        # 快递员初始队列
        self.o_schedule = copy.deepcopy(schedule)
        # 快递员剩余队列
        self.re_schedule = schedule
        # 快递员属于哪个中转站
        self.station_num = station_num
        # 每个快递员在time时间内的临时纪录距离变量
        self.temp_lengt = 0
        # 快递员剩余总可用时间
        self.sum_useful_time = 0
        # 调参：快递员报价参数
        # w is weight
        # self.w = random.uniform(0, 1)
        # self.c = 1 - self.w
        self.w = preferences
        self.c = 1 - preferences


class Station:
    def __init__(self, num: int, l_lng: float, l_lat: float, l_node, station_range):
        self.num = num
        self.l_lng = l_lng
        self.l_lat = l_lat
        self.l_node = l_node
        self.station_range = station_range
        # drop-off task的任务集合
        self.station_task_set = []
        self.station_task_schedule = []
        self.courier_set = []
        # pick-up的任务集合
        self.f_pick_task_set = []
        self.pick_task_pool = []
        self.combin_pick_task_pool = []
        self.temp_courier_pool = []

class Platform:
    def __init__(self, platform_id: int, station_set, courier_set, is_cross_platform: bool):
        self.platform_id = platform_id
        self.station_set = station_set
        self.courier_set = courier_set
        self.is_cross_platform = is_cross_platform