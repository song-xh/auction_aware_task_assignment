from entity import *
from data import *
from algorithm import Greedy, CombinKM
from graph import *
import sys  # 导入sys模块
import random
import time
import copy
import datetime
from decimal import *
'''
实验流程的框架，在本文件运行实验
main函数流程的代码我做了一些修改，把全局变量改为参数传递
'''


# 为每个Station形成一个task_schedule， 然后生成Courier
def GenerateOriginSchedule(fw_station_set: list[Station], preference: float, parameter_courier_num: int,
                           parameter_capacity: float, parameter_capacity_c: float) -> list[Courier]:

    fw_courier_set = []
    # 对于每一个快递站
    count = 0
    num = 0
    for station in fw_station_set:
        count_in_one = 0
        # 快递站内的所有递送任务delivery task
        for task in station.station_task_set:
            # 中转站时间表temp_task_schedule
            temp_task_schedule = []
            # 递送任务随机成组，并判断是否满足约束，若满足则成组,
            # zgl：随机的形式为每个task找到其满足时间和重量约束的任务组，且以此找到的这个任务组作为先后执行的deliverytask顺序。
            task_schedule_set, fw_sum_time = TaskSchedule(task, station.station_task_set, 0, task.weight,
                                                          1, temp_task_schedule, station, parameter_capacity)
            station.station_task_schedule.append(task_schedule_set)
            num += 1

            sum_task_weight = 0
            for t in task_schedule_set:
                sum_task_weight += t.weight
            courier = Courier(num, station.l_node, task_schedule_set, round(sum_task_weight, 2), station.num, preference, parameter_capacity_c)
            courier.sum_useful_time = 14400 - fw_sum_time
            fw_sum_time = 0

            station.courier_set.append(courier)
            fw_courier_set.append(courier)

            count_in_one += 1

        count += count_in_one

    # 调参：快递员数量
    a = random.Random()
    # # 指定相同的随机种子，共享随机状态
    a.seed(1)
    fw_f_courier_set = a.sample(fw_courier_set, parameter_courier_num)

    return fw_f_courier_set


# 往task和station直接插入若干个task，形成一个多task组成的task_schedule
def TaskSchedule(task: Task, task_set: list[Task], temp_cost: float, temp_weight: float,
                 temp_task_num: int, task_schedule: list[Task], station: Station, parameter_capacity: float):
    '''
    param task: 起始task
    param task_set: 备选任务集，我们从其中随机选择任务集并插入
    param temp_cost: 记录schedule中任务总花费，从schedule第一个任务出发，到最后一个任务的总花费
    param temp_weight: 随机选择的任务的weight
    param temp_task_num: scedule中任务数量
    param task_schedule: task列表
    param station: 终点站
    returns: task列表task_schedule，从第一个任务开始到station的总花费时间fw_sum_time
    '''
    global fw_sum_time
    # 如果不为空
    if task_set:
        # 从备选任务集里随机选一个task
        temp_random_task = random.choice(task_set)

        # 根据task、station内的信息，获取node节点
        start_node = NodeModel()
        start_node.nodeId = task.l_node

        end_node = NodeModel()
        end_node.nodeId = temp_random_task.l_node

        # task到temp_task的路径
        temp_paths = g.getShortPath(start_node, end_node, s)

        last_node = NodeModel()
        last_node.nodeId = station.l_node

        # temp_task到station的路径
        temp_last_paths = g.getShortPath(end_node, last_node, s)

        lengt1 = 0
        lengt2 = 0

        # paths由多个边组成， 计算task到task到temp_task的距离和temp_task到station的距离
        for p in temp_paths:
            lengt1 += p.length
        for p1 in temp_last_paths:
            lengt2 += p1.length

        # 计算花费
        temp_cost += lengt1 / (VELOCITY * 1000)
        temp_last_cost = lengt2 / (VELOCITY * 1000)

        # 根据新插入的temp_task，更新weiht和任务数量
        # 这里写的位置不对吧，应该放到下面if判断的里面，因为只有符合条件才能成功插入任务
        temp_weight += temp_random_task.weight
        temp_task_num += 1
        # and temp_task_num <= 51 parameter_capacity调参：快递员背包容量
        if temp_cost + temp_last_cost <= 14400 and temp_weight <= parameter_capacity:
            temp_random_task.reach_time = temp_cost
            # 给每个任务加上预计可达时间的属性
            task.dis_next_point = lengt1
            task_schedule.append(temp_random_task)
            task_set.remove(temp_random_task)
            fw_sum_time = temp_cost + temp_last_cost

            # 递归调用该函数，插入新的任务
            # 其实这里return掉也没关系， 返回值只返回一个fw_sum_time即可，task_schedule作为引用参数会被修改
            TaskSchedule(temp_random_task, task_set, temp_cost,
                         temp_weight, temp_task_num, task_schedule, station, parameter_capacity)
    return task_schedule, fw_sum_time





if __name__ == '__main__':

    # 每一轮的超参数
    rounds = [
        # 第一轮数据弄小一点，方便查看结果
        [50, 3, 75, 15, 0.1, 0.01, 75],
        [50000, 3000, 75, 15, 0.3, 0.01, 75],
        [50000, 3000, 75, 15, 0.5, 0.01, 75],
        [50000, 3000, 75, 15, 0.7, 0.01, 75],
        [50000, 3000, 75, 15, 0.9, 0.01, 75],
    ]
    for r in rounds:

        print("\nround %d \n" % rounds.index(r))

        # 读取超参数
        parameter_task_num = r[0]
        parameter_courier_num = r[1]
        parameter_capacity = r[2]
        time_window = r[3]
        parameter_bidding_w = r[4]
        p = r[5]
        parameter_capacity_c = r[6]
        u = 0.5

        # 记录时间
        a = datetime.datetime.now()

        # 生成task
        print("generate Task...")
        gt = GenerateTask("../Data")
        pick_task_set, delivery_task_set = gt.readTask()

        # 生成station
        print("generate Station...")
        gs = GenerateStation("../Data/map_ChengDu", "../Data/order_20161101_deal", 11)
        fw_station_set1  = gs.get_station(pick_task_set,  delivery_task_set, parameter_task_num)
        fw_station_set2 = gs.get_station(pick_task_set,  delivery_task_set, parameter_task_num)

        # 所有station的pick任务之和
        fw_ff_pick_task_set1: list[Task] = []
        for st in fw_station_set1:
            fw_ff_pick_task_set1.extend(st.f_pick_task_set)

        # 所有station的pick任务之和
        fw_ff_pick_task_set2: list[Task] = []
        for st in fw_station_set2:
            fw_ff_pick_task_set2.extend(st.f_pick_task_set)

        # 为每个Station形成一个task_schedule， 然后生成Courier
        print("generate OriginSchedule...")
        fw_f_courier_set1 = GenerateOriginSchedule(fw_station_set1, parameter_bidding_w, parameter_courier_num, parameter_capacity, parameter_capacity_c)
        fw_f_courier_set2 = GenerateOriginSchedule(fw_station_set2, parameter_bidding_w, parameter_courier_num, parameter_capacity, parameter_capacity_c)

        # batch size ？
        realtime = 1
        if p == 0.01:
            print("************************************************************************* Round start ", r)
            b = datetime.datetime.now()
            print("当前轮次预处理时间为：", (b - a))
            print("开始时间为为：", b)
            c = datetime.datetime.now()

            # 运行两种算法
            print("Greedy Run")
            Greedy(fw_station_set1, fw_f_courier_set1, fw_ff_pick_task_set1, time_window, u, realtime)
            print("CombinKM Run")
            CombinKM(fw_station_set2, fw_f_courier_set2, fw_ff_pick_task_set2, time_window, u, p, realtime)

            d = datetime.datetime.now()
            print("当前轮次算法处理时间为：", (d - c))
            print("结束时间为为：", d)
            print("************************************************************************* Round end")
        else:
            print("************************************************************************* Round start ", r)
            b = datetime.datetime.now()
            print("当前轮次预处理时间为：", (b - a))
            print("开始时间为为：", b)
            c = datetime.datetime.now()
            d = datetime.datetime.now()
            print("当前轮次算法处理时间为：", (d - c))
            print("结束时间为为：", d)
            print("************************************************************************* Round end")
    print("All rounds are over!!!")

'''
运行输出
-------------Start parsing-------------
end parsing with: nodes : 290517  |   edges: 20343
before DFS nodeNumber: 37027  edgeNumber: 51824
After DFS nodeNumber: 36630  |  edgeNumber:50786
end of graph processing

round 0 

generate Task...
generate Station...
generate OriginSchedule...
************************************************************************* Round start  [50, 3, 75, 15, 0.1, 0.01, 75]
当前轮次预处理时间为： 0:09:37.411372
开始时间为为： 2024-01-05 16:25:07.328746
Greedy Run
Greedy Result:-------------------------
程序总耗时:144.15    ,完成任务个数:88   ,总失败个数:4826 ,任务完成率:1.76 %,所有均耗时:0.44    ms,成功均耗时:25.07   ms,所有总耗时:2206.09   ms,批处理耗时:2.30    ms,任务均报价:6.28 ,平台总报价:552.77    ,平台总收益:151.23    
CombinKM Run
CombinKM Result:-----------------------
程序总耗时:103.73    ,完成任务个数:60   ,总失败个数:4927 ,任务完成率:1.20 %,所有均耗时:0.06    ms,成功均耗时:4.77    ms,所有总耗时:286.00    ms,批处理耗时:0.30    ms,任务均报价:2.35 ,平台总报价:140.81    ,平台总收益:339.19    
当前轮次算法处理时间为： 0:04:07.902656
结束时间为为： 2024-01-05 16:29:15.231402
************************************************************************* Round end
'''