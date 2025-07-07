import copy

'''
定义Task、Station、快递员实体
'''
class Task:
    """
    所在地，发出时间，截止时间，任务质量，费用
    """
    def __init__(self, num: int, l_lng: float, l_lat: float,
                 l_node: str, s_time: int, d_time: int, weight: float, fare: float):
        self.num: int = num
        self.l_lng: float = l_lng
        self.l_lat: float = l_lat
        # 因为graph util里的nodeid是str类型，所以这里也用str
        self.l_node: str  = l_node
        self.s_time: int  = s_time
        self.d_time: int  = d_time
        self.weight: float = weight
        self.fare: float = fare

        self.temp_courier_set: list[Courier] = []
        self.temp_greedy_courier_set: list[Courier] = []
        self.reach_time: int = 0
        self.temp_bidding_set = []
        self.task_num: int = 1
        self.dis_next_point: float = 0.
        self.nodes = []
        self.extime: float = 0.


class Courier:
    def __init__(self, num: int, location: int, schedule: list[Task], weight: float,
                 station_num: int, preferences: float, parameter_capacity_c: float):
        """
        :param num: 编号
        :param location: 位置 所在node的id
        :param schedule: 时间表
        """
        # 快递员编号
        self.num: int = num
        # 快递员当前位置
        self.location: int = location
        # 快递员虚拟位置（计算快递员到达某个节点的时间时使用）
        self.temp_location = self.location
        # 快递员最大容量
        # 调参：快递员背包容量
        self.max_weight: float = parameter_capacity_c
        # 快递员实际负载
        self.re_weight: float = weight
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
        self.w: float = preferences
        self.c: float = 1 - preferences


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
        self.f_pick_task_set: list[Task] = []
        self.pick_task_pool = []
        self.combin_pick_task_pool = []
        self.temp_courier_pool = []


    # 这个函数的功能我进行了修改，在函数内部版只判断任务是否为deliver task
    def judge_in_station(self, task: Task):
        if self.station_range[0] <= float(task.l_lng) \
                < self.station_range[1] and self.station_range[2] \
                <= float(task.l_lat) < self.station_range[3]:
            return True
        return False

    # 判断该任务是否是该站点的pick task，同上进行了修改
    def judge_pick_task(self, task: Task):
        if self.station_range[0] <= float(task.l_lng) \
                < self.station_range[1] and self.station_range[2] \
                <= float(task.l_lat) < self.station_range[3]:
            return True
        return False

