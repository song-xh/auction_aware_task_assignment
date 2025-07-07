from MethodUtils_ChengDu import *
from Tasks_ChengDu import *
import sys  # 导入sys模块
import random
import time
import copy
import datetime
from decimal import *

# 总时间
# 将默认的递归深度修改为3000
# sys.setrecursionlimit(10000000)
fw_sum_time = 0

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


    def judge_in_station(self, task: Task):
        if self.station_range[0] <= float(task.l_lng) \
                < self.station_range[1] and self.station_range[2] \
                <= float(task.l_lat) < self.station_range[3]:
            self.station_task_set.append(task)
            return True

    def judge_pick_task(self, task):
        if self.station_range[0] <= float(task.l_lng) \
                < self.station_range[1] and self.station_range[2] \
                <= float(task.l_lat) < self.station_range[3]:
            self.f_pick_task_set.append(task)
            fw_ff_pick_task_set1.append(task)
            return True


class GenerateStation:
    def __init__(self, g_filepath: str, d_filepath: str, parts_num: int):
        """
        # "Data/order_20161101_deal"
        :param g_filepath: 地图路径
        :param d_filepath: 订单数据
        :param parts_num: 划分多少个中转站
        """

        self.g_filepath = g_filepath
        self.d_filepath = d_filepath
        self.parts_num = parts_num
        self.range_lng = 0
        self.range_lat = 0

    def get_station(self):
        fw_station_set1 = []
        # station的经纬度edge_station
        self.range_lng = self.edge_station()[0]
        self.range_lat = self.edge_station()[1]
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
                    temp_station.judge_in_station(t)

                count_pick_task_num = 0
                # 为每个station找到自己的pick_tasks
                for t1 in pick_task_set:
                    # 调参：递送任务个数
                    if count_pick_task_num < parameter_task_num:
                        temp_station.judge_pick_task(t1)
                        count_pick_task_num += 1
                fw_station_set1.append(temp_station)

        return fw_station_set1

    def edge_station(self):
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

# 为每个station 形成一个task_schedule
def GenerateOriginSchedule(fw_station_set, preference):
    global fw_sum_time
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
            task_schedule_set, fw_sum_time = TaskSchedule(task, station.station_task_set,
                                                          0, task.weight, 1, temp_task_schedule, station)
            station.station_task_schedule.append(task_schedule_set)
            num += 1

            sum_task_weight = 0
            for t in task_schedule_set:
                sum_task_weight += t.weight
            courier = Courier(num, station.l_node, task_schedule_set, round(sum_task_weight, 2), station.num, preference)
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
def TaskSchedule(task, task_set, temp_cost, temp_weight, temp_task_num, task_schedule, station):
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
        # 这里写的位置不对吧，应该放到下面if判断的里面，因为只有符号条件才能成功插入任务
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
                         temp_weight, temp_task_num, task_schedule, station)
    return task_schedule, fw_sum_time


# 令快递员移动，也就是修改相关变量
def WalkAlongRoute(courier, time, c_location, a_lengt, time_cost, real_time, courier_set1, station_set):
    """

    :param courier_set1:
    :param real_time:
    :param courier: 快递员
    :param time: 每次执行快递员移动的总时间
    :param c_location:快递员位置
    :param a_lengt: 在时间内移动的总距离
    :param time_cost:花费时间
    :return:
    """
    if len(courier.re_schedule) != 0:
        start_node = NodeModel()
        start_node.nodeId = c_location
        end_node = NodeModel()
        end_node.nodeId = courier.re_schedule[0].l_node
        paths = g.getShortPath(start_node, end_node, s)
        # 每轮循环内的移动距离长度
        lengt = 0
        for p in paths:
            lengt += p.length
        time_cost += lengt / (VELOCITY * 1000)
        # 总移动距离长度
        lengt += a_lengt
        if (VELOCITY * 1000) * time >= lengt:
            courier.re_weight -= courier.re_schedule[0].weight
            courier.location = courier.re_schedule[0].l_node
            del courier.re_schedule[0]
            WalkAlongRoute(courier, time, courier.location, lengt, time_cost, real_time, courier_set1, station_set)
        else:
            courier.temp_lengt += (VELOCITY * 1000) * time
            if courier.temp_lengt >= lengt:
                courier.location = courier.re_schedule[0].l_node
                courier.temp_location = courier.re_schedule[0].l_node
                courier.re_weight -= courier.re_schedule[0].weight

                del courier.re_schedule[0]
                courier.temp_lengt = courier.temp_lengt - lengt

    else:
        for station in station_set:
            if station.num == courier.station_num:
                start_node = NodeModel()
                start_node.nodeId = c_location
                end_node = NodeModel()
                end_node.nodeId = station.l_node
                paths = g.getShortPath(start_node, end_node, s)
                lengt = 0
                for p in paths:
                    lengt += p.length
                time_cost += lengt / (VELOCITY * 1000)
                # 总移动距离长度
                lengt += a_lengt

                courier_set1.remove(courier)


def Greedy(station_set, f_courier_set, ff_pick_task_set, time_window, u, realtime):
    # print("Greedy开始")
    starttime = time.time()
    # 时间计数器
    time_count = 0
    # 临时缓冲池
    sucess_num = 0
    failed_num = 0
    sum_time_count = 0
    sum_bidding = 0
    avg_bidding = 0
    pass_num = 0
    for i1 in range(int(14400 / realtime)):
        for station in station_set:
            for t in station.f_pick_task_set:
                if int(t.s_time) == time_count:
                    can_do_courier_set = []
                    start_time = time.time()
                    best_courier = ""
                    result_pre = "a"
                    f_result_pre = ""
                    f_result_bid = 0
                    f_result_extime = 0
                    # 选取所有能够到达的快递员
                    for c in station.courier_set:
                        if c in f_courier_set:
                            start = NodeModel()
                            start.nodeId = c.location
                            end = NodeModel()
                            end.nodeId = t.l_node
                            paths = g.getShortPath(start, end, s)
                            lengt = 0
                            for p in paths:
                                lengt += p.length
                            if lengt <= (int(t.d_time) - time_count) * (VELOCITY * 1000) \
                                    and (c.max_weight - c.re_weight) > t.weight:
                                can_do_courier_set.append(c)
                    if len(can_do_courier_set) == 0:
                        failed_num += 1
                    else:
                        if len(can_do_courier_set) != 1:
                            min_bidding = 100000
                            for c in can_do_courier_set:
                                result_pre, result_bid, result_extime = FBP_GA(c, t, u, time_count)
                                if result_pre == "a":
                                    pass_num += 1
                                    if pass_num % 3 == 0:
                                        break
                                    else:
                                        continue
                                else:
                                    if avg_bidding == 0:
                                        f_result_pre = result_pre
                                        f_result_bid = result_bid
                                        f_result_extime = result_extime
                                        best_courier = c
                                        break
                                    else:
                                        if result_bid < min_bidding:
                                            min_bidding = result_bid
                                            f_result_pre = result_pre
                                            f_result_bid = result_bid
                                            f_result_extime = result_extime
                                            best_courier = c
                                            if result_bid <= avg_bidding / sucess_num:
                                                break
                            if result_pre == "a":
                                failed_num += 1
                            else:
                                insert_index = best_courier.re_schedule.index(f_result_pre)
                                best_courier.re_schedule.insert(insert_index + 1, t)
                                best_courier.sum_useful_time -= f_result_extime
                                size_reschedule = len(best_courier.re_schedule)
                                for i in range((insert_index + 2), size_reschedule):
                                    best_courier.re_schedule[i].reach_time += f_result_extime
                                best_courier.re_weight += t.weight
                                best_courier.max_weight -= t.weight
                                avg_bidding += f_result_bid
                                sucess_num += 1
                                sum_bidding += f_result_bid
                        else:
                            best_courier = can_do_courier_set[0]
                            result_pre, result_bid, result_extime = FBP_GA1(best_courier, t, u,
                                                                            time_count)
                            if result_pre == "a":
                                failed_num += 1
                            else:
                                insert_index = best_courier.re_schedule.index(result_pre)
                                best_courier.re_schedule.insert(insert_index + 1, t)
                                best_courier.sum_useful_time -= result_extime
                                size_reschedule = len(best_courier.re_schedule)
                                for i in range((insert_index + 2), size_reschedule):
                                    best_courier.re_schedule[i].reach_time += result_extime
                                best_courier.re_weight += t.weight
                                best_courier.max_weight -= t.weight
                                avg_bidding += result_bid
                                sucess_num += 1
                                sum_bidding += result_bid
                    end_time = time.time()
                    sum_time_count += (end_time - start_time)
        time_count += realtime
        percent = round(float(1.0 * i1 / 14400 * 100), 4)
        sys.stdout.write("\r rate of Greedy progress: %0.2f %%, %d" % (percent, sucess_num))
        sys.stdout.flush()
        time.sleep(0.0001)
        if len(f_courier_set) == 0:
            break
        for courier in f_courier_set:
            WalkAlongRoute(courier, realtime, courier.location, 0, 0, time_count, f_courier_set, station_set)
    endtime = time.time()
    avg_time = Decimal((sum_time_count / len(ff_pick_task_set)) * 1000).quantize(Decimal('0.00'))
    avg_time1 = Decimal((sum_time_count / sucess_num) * 1000).quantize(Decimal('0.00'))
    sum_time1 = Decimal(sum_time_count * 1000).quantize(Decimal('0.00'))
    sum_time2 = Decimal(sum_time_count / (14400 / time_window) * 1000).quantize(Decimal('0.00'))
    sucess_rate = Decimal((sucess_num / len(ff_pick_task_set)) * 100).quantize(Decimal('0.00'))
    time_cost = Decimal((endtime - starttime)).quantize(Decimal('0.00'))
    f_sum_bidding = Decimal(sum_bidding).quantize(Decimal('0.00'))
    each_bidding = Decimal((sum_bidding / sucess_num)).quantize(Decimal('0.00'))
    print("\rGreedy Result:-------------------------")
    print("程序总耗时:%-10s,完成任务个数:%-5s,总失败个数:%-5s,任务完成率:%-5s%%,"
          "所有均耗时:%-8sms,成功均耗时:%-8sms,所有总耗时:%-10sms,批处理耗时:%-8sms,"
          "任务均报价:%-5s,平台总报价:%-10s,平台总收益:%-10s" %
          (time_cost, sucess_num, failed_num, sucess_rate,
           avg_time, avg_time1, sum_time1, sum_time2, each_bidding, f_sum_bidding, (8 * sucess_num - f_sum_bidding)))


if __name__ == "__main__":
    print("Divide执行了")
    generate_station = GenerateStation("Data/map_ChengDu", "Data/order_20161101_deal", 11)
    print("finish")

    rounds = [
        # LNS 参数
        # [5000, 100, 75, 15, 0.5, 0.01, 75],
        # [5000, 200, 75, 15, 0.5, 0.01, 75],
        # [5000, 300, 75, 15, 0.5, 0.01, 75],
        # [5000, 400, 75, 15, 0.5, 0.01, 75],
        # [5000, 500, 75, 15, 0.5, 0.01, 75],
        #
        # [1250, 300, 75, 15, 0.5, 0.01, 75],
        # [2500, 300, 75, 15, 0.5, 0.01, 75],
        # [5000, 300, 75, 15, 0.5, 0.01, 75],
        # [10000, 300, 75, 15, 0.5, 0.01, 75],
        # [20000, 300, 75, 15, 0.5, 0.01, 75],
        #
        # [5000, 300, 75, 5, 0.5, 0.01, 75],
        # [5000, 300, 75, 10, 0.5, 0.01, 75],
        # 10.11补充实验
        # [5000, 300, 75, 15, 0.1, 0.01, 75],
        # [5000, 300, 75, 15, 0.3, 0.01, 75],
        # [5000, 300, 75, 15, 0.5, 0.01, 75],
        # [5000, 300, 75, 15, 0.7, 0.01, 75],
        # [5000, 300, 75, 15, 0.9, 0.01, 75],
        [50000, 3000, 75, 15, 0.1, 0.01, 75],
        [50000, 3000, 75, 15, 0.3, 0.01, 75],
        [50000, 3000, 75, 15, 0.5, 0.01, 75],
        [50000, 3000, 75, 15, 0.7, 0.01, 75],
        [50000, 3000, 75, 15, 0.9, 0.01, 75],
        # [5000, 300, 75, 20, 0.5, 0.01, 75],
        # [5000, 300, 75, 30, 0.5, 0.01, 75],
        #
        # [5000, 300, 25, 15, 0.5, 0.01, 25],
        # [5000, 300, 50, 15, 0.5, 0.01, 50],
        # [5000, 300, 75, 15, 0.5, 0.01, 75],
        # [5000, 300, 75, 15, 0.5, 0.01, 100],
        # [5000, 300, 75, 15, 0.5, 0.01, 125],
        #
        # ########################
        #
        # [50000, 1000, 75, 15, 0.5, 0.01, 75],
        # [50000, 2000, 75, 15, 0.5, 0.01, 75],
        # [50000, 3000, 75, 15, 0.5, 0.01, 75],
        # [50000, 4000, 75, 15, 0.5, 0.01, 75],
        # [50000, 5000, 75, 15, 0.5, 0.01, 75],
        #
        # [12500, 2000, 75, 15, 0.5, 0.01, 75],
        # [25000, 2000, 75, 15, 0.5, 0.01, 75],
        # [50000, 2000, 75, 15, 0.5, 0.01, 75],
        # [100000, 2000, 75, 15, 0.5, 0.01, 75],
        # [200000, 2000, 75, 15, 0.5, 0.01, 75],
        #
        # [50000, 2000, 75, 5, 0.5, 0.01, 75],
        # [50000, 2000, 75, 10, 0.5, 0.01, 75],
        # [50000, 2000, 75, 15, 0.5, 0.01, 75],
        # [50000, 2000, 75, 20, 0.5, 0.01, 75],
        # [50000, 2000, 75, 30, 0.5, 0.01, 75],
        #
        # [50000, 2000, 25, 15, 0.5, 0.01, 25],
        # [50000, 2000, 50, 15, 0.5, 0.01, 50],
        # [50000, 2000, 75, 15, 0.5, 0.01, 75],
        # [50000, 2000, 75, 15, 0.5, 0.01, 100],
        # [50000, 2000, 75, 15, 0.5, 0.01, 125],


        # [2500, 600, 75, 15, 0.5, 0.01, 75],
        # [5000, 600, 75, 15, 0.5, 0.01, 75],
        # [10000, 600, 75, 15, 0.5, 0.01, 75],
        # [20000, 600, 75, 15, 0.5, 0.01, 75],
        # [40000, 600, 75, 15, 0.5, 0.01, 75],

        # [10000, 200, 75, 15, 0.5, 0.01, 75],
        # [10000, 400, 75, 15, 0.5, 0.01, 75],
        # [10000, 800, 75, 15, 0.5, 0.01, 75],
        # [10000, 1000, 75, 15, 0.5, 0.01, 75],

        # [10000, 600, 25, 15, 0.5, 0.01, 25],
        # [10000, 600, 50, 15, 0.5, 0.01, 50],
        # [10000, 600, 75, 15, 0.5, 0.01, 100],
        # [10000, 600, 75, 15, 0.5, 0.01, 125],

        # [1000, 60, 75, 45, 0.5, 0.01, 75],
        # [10000, 600, 75, 60, 0.5, 0.01, 75],
        # [10000, 600, 75, 120, 0.5, 0.01, 75],
        # [10000, 600, 75, 180, 0.5, 0.01, 75],
        # [10000, 600, 75, 240, 0.5, 0.01, 75],
        # [10000, 600, 75, 300, 0.5, 0.01, 75],

        # [10000, 600, 75, 15, 0.5, 0.1, 75],
        # [10000, 600, 75, 15, 0.5, 0.3, 75],
        # [10000, 600, 75, 15, 0.5, 0.5, 75],
        # [10000, 600, 75, 15, 0.5, 0.9, 75],
    ]

    # rounds = [
    #           [12500, 3000, 75, 15, 0.5, 0.01, 75],
    #           [25000, 3000, 75, 15, 0.5, 0.01, 75],
    #           [50000, 3000, 75, 15, 0.5, 0.01, 75],
    #           [100000, 3000, 75, 15, 0.5, 0.01, 75],
    #           [200000, 3000, 75, 15, 0.5, 0.01, 75],
    #
    #           [50000, 1000, 75, 15, 0.5, 0.01, 75],
    #           [50000, 2000, 75, 15, 0.5, 0.01, 75],
    #           [50000, 4000, 75, 15, 0.5, 0.01, 75],
    #           [50000, 5000, 75, 15, 0.5, 0.01, 75],
    #
    #           [50000, 3000, 25, 15, 0.5, 0.01, 25],
    #           [50000, 3000, 50, 15, 0.5, 0.01, 50],
    #           [50000, 3000, 75, 15, 0.5, 0.01, 100],
    #           [50000, 3000, 75, 15, 0.5, 0.01, 125],
    #
    #           [50000, 3000, 75, 5, 0.5, 0.01, 75],
    #           [50000, 3000, 75, 10, 0.5, 0.01, 75],
    #           [50000, 3000, 75, 20, 0.5, 0.01, 75],
    #           [50000, 3000, 75, 30, 0.5, 0.01, 75],
    #
    #           [50000, 3000, 75, 15, 0.9, 0.01, 75],
    #           [50000, 3000, 75, 15, 0.7, 0.01, 75],
    #           [50000, 3000, 75, 15, 0.3, 0.01, 75],
    #           [50000, 3000, 75, 15, 0.1, 0.01, 75]
    # ]

    for r in rounds:
        pick_task_set, delivery_task_set = readTask()
        # 最终的收取任务集合, 所有站点的taskset之和
        fw_ff_pick_task_set1 = []

        parameter_task_num = r[0]
        parameter_courier_num = r[1]
        parameter_capacity = r[2]
        time_window = r[3]
        parameter_bidding_w = r[4]
        p = r[5]
        parameter_capacity_c = r[6]
        u = 0.5

        print("generate st")
        # 下面的步骤太慢了，跑不出来
        ##FIXME检查为什么这里会慢
        a = datetime.datetime.now()
        # 这里之所以要分成五个set，因为下面要跑五个算法
        fw_station_set1 = generate_station.get_station()
        fw_f_courier_set1 = GenerateOriginSchedule(fw_station_set1, parameter_bidding_w)

        print("generate")
        realtime = 1
        if p == 0.01:
            print("************************************************************************* Round start ", r)
            b = datetime.datetime.now()
            print("当前轮次预处理时间为：", (b - a))
            print("开始时间为为：", b)
            c = datetime.datetime.now()
            Greedy(fw_station_set1, fw_f_courier_set1, fw_ff_pick_task_set1, time_window, u, realtime)
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
