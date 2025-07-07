import numpy as np
import random
from GraphUtils_ChengDu import *
from itertools import islice

# pick_task_set = []
# delivery_task_set = []
class Task:
    """
    所在地，发出时间，截止时间，任务质量，费用
    """
    def __init__(self, num: int, l_lng: float, l_lat: float,
                 l_node: int, s_time: int, d_time: int, weight: float, fare: float):
        self.num = num
        self.l_lng = l_lng
        self.l_lat = l_lat
        self.s_time = s_time
        self.d_time = d_time
        self.weight = weight
        self.l_node = l_node
        # 运行时取消注释
        self.fare = fare
        self.temp_courier_set = []
        self.temp_greedy_courier_set = []
        self.reach_time = 0
        self.temp_bidding_set = []
        self.task_num = 1
        self.dis_next_point = 0
        self.nodes = []
        self.extime = 0

# 平时运行开启
def readTask():
    pick_task_set = []
    delivery_task_set = []
    with open("Data/order_20161101_deal1") as f:
        count = 0
        for line in f:
            line = line.split(",")
            temp_task = Task(line[0], line[1], line[2], line[3],
                             line[4], line[5], np.round(float(line[6]), 2), np.round(float(line[7]), 2))

            count += 1
            if temp_task.fare != 0:
                pick_task_set.append(temp_task)
            else:
                delivery_task_set.append(temp_task)
    with open("Data/order_20161101_deal2") as f:
        count = 0
        for line in f:
            line = line.split(",")
            temp_task = Task(line[0], line[1], line[2], line[3],
                             line[4], line[5], np.round(float(line[6]), 2), np.round(float(line[7]), 2))

            count += 1
            if temp_task.fare != 0:
                pick_task_set.append(temp_task)
            else:
                delivery_task_set.append(temp_task)
    with open("Data/order_20161101_deal3") as f:
        count = 0
        for line in f:
            line = line.split(",")
            temp_task = Task(line[0], line[1], line[2], line[3],
                             line[4], line[5], np.round(float(line[6]), 2), np.round(float(line[7]), 2))
        count += 1
        if temp_task.fare != 0:
            pick_task_set.append(temp_task)
            # print("picpup+1, 总数为%s" % count)
        else:
            delivery_task_set.append(temp_task)
            # print(f"delivery+1, 总数为{count}")
    with open("Data/order_20161101_deal4") as f:
        count = 0
        for line in f:
            line = line.split(",")
            temp_task = Task(line[0], line[1], line[2], line[3],
                             line[4], line[5], np.round(float(line[6]), 2), np.round(float(line[7]), 2))

            count += 1
            if temp_task.fare != 0:
                pick_task_set.append(temp_task)
                # print("picpup+1, 总数为%s" % count)
            else:
                delivery_task_set.append(temp_task)
                # print(f"delivery+1, 总数为{count}")
    return pick_task_set, delivery_task_set


# 打包策略,pl是打包阈值
'''这个是做什么事情？'''
def Combin(task_set, w_th, pl):
    flag = 0
    for t in task_set:
        for t1 in task_set:
            if t.num != t1.num:
                start = NodeModel()
                start.nodeId = t.l_node
                end = NodeModel()
                end.nodeId = t1.l_node
                paths = g.getShortPath(start, end, s)
                lengt = 0
                for p in paths:
                    lengt += p.length
                # 打包不但和距离相关
                Pcorr = abs(lengt)
                # 还deadline时间有关
                Dcorr = abs(int(t.d_time) - int(t1.d_time)) / 3600

                com = 1 / (1 + math.sqrt( Pcorr + Dcorr))
                if com > pl:
                    if t.d_time < t1.d_time:
                        t.weight += t1.weight
                        t.fare += t1.fare
                        t.task_num += 1
                        task_set.remove(t1)
                        flag += 1
                        break
                    else:
                        t1.weight += t.weight
                        t1.fare += t.fare
                        t1.task_num += 1
                        task_set.remove(t)
                        flag += 1
                        break
    return flag

if __name__ == "__main__":
    print("kaishi")
    pick_count = 0
    delivery_count = 0
    pick_task_set, delivery_task_set = readTask()
    for i in pick_task_set:
        pick_count += 1
    for i in delivery_task_set:
        delivery_count += 1
    print(f"jieshu, {pick_count}个收取请求， {delivery_count}个递送请求")
    print(f'{len(pick_task_set),len(delivery_task_set)}')
    a = random.Random()
    # # 指定相同的随机种子，共享随机状态
    a.seed(1)
    pick_task_set = a.sample(pick_task_set, 50)
    print(f'zuheqian',{len(pick_task_set)})
    flag = 1
    num = 1
    while flag != 0:
        num += 1
        print(num)
        flag = Combin(pick_task_set, 10, 0.15)
    print(f'zuhehou',{len(pick_task_set)})
    for i in pick_task_set:
        print(i.weight)

