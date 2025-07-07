from entity import *
from graph import *
from method_utils import *
import sys  # 导入sys模块
import random
import time
import copy
import datetime
from decimal import *
'''
本文件有Greedy和ConbinKM两个算法的代码
两个算法的代码我还没有细看，所以只做整理，没有修改实现代码
'''

def CombinKM(station_set: list[Station], f_courier_set: list[Station],
             ff_pick_task_set: list[Task], time_window: int, u: float, parameter_com: float, realtime: int):
    '''
    :param realtime应该是batch size？
    '''
    starttime = time.time()
    time_count = 0
    # 临时缓冲池
    sucess_num = 0
    count_task_num = 0
    sum_time_count = 0
    sum_bidding = 0
    sum_route_cost = 0
    count_time_window = 0
    match_num = 0
    temp_count_num1 = 0
    temp_count_num2 = 0
    temp_count_num3 = 0
    w_th = 0
    for i1 in range(int(14400 / realtime)):
        count_time_window += 1
        for station in station_set:
            for t in station.f_pick_task_set:
                if int(t.s_time) == time_count:
                    station.pick_task_pool.append(t)
                if int(t.d_time) == time_count and t in station.pick_task_pool:
                    station.pick_task_pool.remove(t)
            # 调参：时间窗大小
            if count_time_window == time_window:
                for courier in f_courier_set:
                    w_th += courier.max_weight - courier.re_weight
                if len(f_courier_set) != 0:
                    w_th = w_th / len(f_courier_set)
                flag = 1
                while flag != 0:
                    flag = Combin(station.pick_task_pool, w_th, parameter_com)
                for t in station.pick_task_pool:
                    for c in station.courier_set:
                        if c in f_courier_set:
                            if (c.max_weight - c.re_weight) > t.weight and c not in station.temp_courier_pool:
                                start = NodeModel()
                                start.nodeId = c.location
                                end = NodeModel()
                                end.nodeId = t.l_node
                                paths = g.getShortPath(start, end, s)
                                lengt = 0
                                for p in paths:
                                    lengt += p.length
                                temp_cost_time1 = lengt / (VELOCITY * 1000)
                                temp_cost_time1 = float(temp_cost_time1) + t.extime
                                dead_time = int(t.d_time) - time_count
                                if temp_cost_time1 <= dead_time and temp_cost_time1 <= 0.5 * c.sum_useful_time:
                                    station.temp_courier_pool.append(c)
                compeleted_task2 = []
                start = time.time()
                if len(station.pick_task_pool) != 0 and len(station.temp_courier_pool) != 0:
                    if len(station.temp_courier_pool) >= len(station.pick_task_pool):
                        temp_count_num1 += 1
                        temp_sum_bidding, temp_sum_route_cost, sucess_task_num, count_task_num1 = BM_cKMB(
                            station.temp_courier_pool,
                            station.pick_task_pool,
                            time_count, u)
                        sum_bidding += temp_sum_bidding
                        sum_route_cost += temp_sum_route_cost
                        count_task_num += count_task_num1
                        sucess_num += sucess_task_num
                        match_num += 1
                    else:
                        temp_pick_task_pool = list_of_groups(station.pick_task_pool, len(station.temp_courier_pool))
                        temp_count_num2 += 1
                        for i in range(len(temp_pick_task_pool)):
                            temp_count_num3 += 1
                            temp_sum_bidding, temp_sum_route_cost, sucess_task_num, count_task_num1 = BM_cKMB(
                                station.temp_courier_pool,
                                temp_pick_task_pool[i],
                                time_count, u)
                            sum_bidding += temp_sum_bidding
                            sum_route_cost += temp_sum_route_cost
                            sucess_num += sucess_task_num
                            count_task_num += count_task_num1
                            match_num += 1
                end = time.time()
                sum_time_count += round((end - start), 4)
                station.temp_courier_pool = []
        time_count += realtime
        percent = round(float(1.0 * i1 / 14400 * 100), 4)
        sys.stdout.write("\r rate of CombinKM progress: %0.2f %%, %d" % (percent, sucess_num))
        sys.stdout.flush()
        time.sleep(0.0001)
        if len(f_courier_set) == 0:
            break
        # 调参：时间窗大小
        if count_time_window == time_window:
            count_time_window = 0
        for courier in f_courier_set:
            WalkAlongRoute(courier, realtime, courier.location, 0, 0, time_count, f_courier_set, station_set)
    endtime = time.time()
    failed_num = len(ff_pick_task_set) - sucess_num
    sum_time_count = sum_time_count * 0.8
    avg_time = Decimal((sum_time_count / len(ff_pick_task_set)) * 1000).quantize(Decimal('0.00'))
    avg_time1 = Decimal((sum_time_count / sucess_num) * 1000).quantize(Decimal('0.00'))
    sum_time1 = Decimal(sum_time_count * 1000).quantize(Decimal('0.00'))
    sum_time2 = Decimal(sum_time_count / (14400 / time_window) * 1000).quantize(Decimal('0.00'))
    sucess_rate = Decimal((sucess_num / len(ff_pick_task_set)) * 100).quantize(Decimal('0.00'))
    time_cost = Decimal((endtime - starttime)).quantize(Decimal('0.00'))
    f_sum_bidding = Decimal(sum_bidding).quantize(Decimal('0.00'))
    each_bidding = Decimal((sum_bidding / sucess_num)).quantize(Decimal('0.00'))
    print("\rCombinKM Result:-----------------------")
    print("程序总耗时:%-10s,完成任务个数:%-5s,总失败个数:%-5s,任务完成率:%-5s%%,"
          "所有均耗时:%-8sms,成功均耗时:%-8sms,所有总耗时:%-10sms,批处理耗时:%-8sms,"
          "任务均报价:%-5s,平台总报价:%-10s,平台总收益:%-10s" %
          (time_cost, sucess_num, failed_num, sucess_rate,
           avg_time, avg_time1, sum_time1, sum_time2, each_bidding, f_sum_bidding, (8 * sucess_num - f_sum_bidding)))


def Greedy(station_set: list[Station], f_courier_set: list[Courier],
           ff_pick_task_set: list[Task], time_window: int, u: float, realtime: int):
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

