import copy
import json
import os.path
from graph import g, s
from entity import Task, Courier, Station
import numpy as np

'''
从data目录中读取任务信息和station信息
'''

class GenerateTask:
    def __init__(self, dataFolderPath: str):
        # data文件夹路径
        self.dataFolderPath: str = dataFolderPath

    # 从文件中读取任务信息
    def readTask(self) -> tuple[list[Task], list[Task]]:
        pick_task_set = []
        delivery_task_set = []
        for i in range(1, 5):
            with open(os.path.join(self.dataFolderPath, "order_20161101_deal%d"%i)) as f:
                count = 0
                for line in f:
                    line = line.split(",")
                    temp_task = Task(
                        # 一行有八个数，分别如下
                        # 0,30.63833,104.04436,3582961906,
                        # 0,5778,1.35,0.00
                        num=int(line[0]),
                        l_lng=float(line[1]),
                        l_lat=float(line[2]),
                        l_node=line[3],
                        s_time=int(line[4]),
                        d_time=int(line[5]),
                        weight=np.round(float(line[6]), 2),
                        fare=np.round(float(line[7]), 2)
                    )
                    count += 1
                    if temp_task.fare != 0:
                        pick_task_set.append(temp_task)
                    else:
                        delivery_task_set.append(temp_task)
        return pick_task_set, delivery_task_set
class GenerateStation:
    # 从文件中读取station信息
    def __init__(self, g_filepath: str, d_filepath: str, parts_num: int):
        """

        # "Data/order_20161101_deal"
        :param g_filepath: 地图路径
        :param d_filepath: 数据路径
        :param parts_num: 划分多少个中转站
        """
        self.g_filepath: str = g_filepath
        self.d_filepath: str = d_filepath
        self.parts_num: int = parts_num
        self.range_lng: float = 0.
        self.range_lat: float = 0.
        self.fw_station_set: list[Station] = []

    def get_station(self, pick_task_set: list[Task], delivery_task_set: list[Task], parameter_task_num: int) -> list[Station]:

        '''
        函数功能为读取文件，创建station对象，为每个station对象添加配送和取件包裹，返回stationset
        '''
        # 考虑到可能重复获取多次station set，这样写可以节省时间消耗
        if len(self.fw_station_set) > 0:
            return  copy.deepcopy(self.fw_station_set)

        fw_station_set: list[Station] = []

        self.range_lng, self.range_lat = self.edge_station()

        count = 0
        for i in range(self.parts_num - 1):
            for j in range(self.parts_num - 1):
                count += 1
                l_lng = (self.range_lng[i] + self.range_lng[i + 1]) / 2
                l_lat = (self.range_lat[j] + self.range_lat[j + 1]) / 2
                l_node = g.findNode(l_lng, l_lat, s)
                # 为每个station确定经纬度坐标
                temp_station = Station(count, l_lng, l_lat, l_node,
                                       [self.range_lng[i], self.range_lng[i + 1],
                                        self.range_lat[j], self.range_lat[j + 1]])

                # 为每个station找到自己的delivery_tasks
                for t in delivery_task_set:
                    if temp_station.judge_in_station(t):
                        temp_station.station_task_set.append(t)

                count_pick_task_num = 0
                # 为每个station找到自己的pick_tasks
                for t1 in pick_task_set:
                    # 调参：递送任务个数
                    if count_pick_task_num < parameter_task_num:
                        if temp_station.judge_pick_task(t1):
                            temp_station.f_pick_task_set.append(t1)
                            count_pick_task_num += 1
                fw_station_set.append(temp_station)

        self.fw_station_set = copy.deepcopy(fw_station_set)

        return fw_station_set

    def edge_station(self) -> np.ndarray[float]:
        with open(self.d_filepath) as f:
            line_lng_min = 150
            line_lat_min = 150
            line_lng_max = 0
            line_lat_max = 0
            # 找到实际数据中的最大和最小经纬度
            for line in f:
                line = line.split(",")
                if float(line[4]) > line_lng_max:
                    line_lng_max = float(line[4])
                elif float(line[4]) < line_lng_min:
                    line_lng_min = float(line[4])

                if float(line[3]) > line_lat_max:
                    line_lat_max = float(line[3])
                elif float(line[3]) < line_lat_min:
                    line_lat_min = float(line[3])

            # 划分region，找到最大和最小经纬度后，划分范围
            # arr = np.linspace(0, 1, 5)----->输出: [0.   0.25 0.5  0.75 1.  ]
            range_length = np.linspace(line_lng_min + (line_lng_max - line_lng_min) * 0.415,
                                       line_lng_max - (line_lng_max - line_lng_min) * 0.415, self.parts_num)
            range_width = np.linspace(line_lat_min + (line_lat_max - line_lat_min) * 0.415,
                                      line_lat_max - (line_lat_max - line_lat_min) * 0.415, self.parts_num)
        return [range_length, range_width]




import unittest

class TestMyCode(unittest.TestCase):

    def test_(self):
        gt = GenerateTask("../Data")
        pick, deliver = gt.readTask()

        gs = GenerateStation("../Data/map_ChengDu", "../Data/order_20161101_deal", 11)
        stations = gs.get_station(pick, deliver, 50000)
        for i in range(100):
            print(len(stations[i].station_task_set), len(stations[i].f_pick_task_set))

'''
测试输出
============================= test session starts =============================
collecting ... collected 1 item

data.py::TestMyCode::test_ 

======================== 1 passed in 88.87s (0:01:28) =========================
PASSED                                        [100%]
PASSED                           [100%]
174 57
151 44
156 52
500 179
1743 589
2456 789
'''