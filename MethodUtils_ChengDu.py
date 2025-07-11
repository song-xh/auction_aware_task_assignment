from GraphUtils_ChengDu import *
from MyMethod.km_matcher import KMMatcher

def check_threshold(courier, task, u, time_count):
    start = NodeModel()
    start.nodeId = courier.location
    end = NodeModel()
    end.nodeId = task.l_node
    paths = g.getShortPath(start, end, s)
    lengt = 0
    for p in paths:
        lengt += p.length
    temp_cost_time = courier.re_schedule[0].reach_time
    if lengt / (VELOCITY * 1000) <= 0.5 * courier.sum_useful_time and \
            lengt / (VELOCITY * 1000) <= float(task.d_time) - time_count - float(temp_cost_time):
        return True
    else:
        return False

# FBP_BaseC函数是基础的快递员任务匹配函数，使用了简单的路径计算和报价计算。
def FBP_BaseC(courier, task, u, time_count):
    temp_task_set = []
    # start_time2 = time.time()
    best_insert_prepoint = ""
    min_bidding = 10000
    # start_time3 = time.time()
    cost_extime = 0

    for t in courier.re_schedule:
        start = NodeModel()
        start.nodeId = t.l_node
        end = NodeModel()
        end.nodeId = task.l_node
        paths = g.getShortPath(start, end, s)
        lengt = 0
        for p in paths:
            lengt += p.length
        temp_cost_time = t.reach_time
        courier.temp_location = courier.location
        if lengt / (VELOCITY * 1000) <= 0.5 * courier.sum_useful_time and \
                lengt / (VELOCITY * 1000) <= float(task.d_time) - time_count - float(temp_cost_time):

            task_index = courier.re_schedule.index(t)
            # print(task_index)
            courier.re_schedule.insert(task_index + 1, task)

            # task_index1 = courier.re_schedule.index(task)
            # print(task_index1)
            # print(len(courier.re_schedule))

            last = NodeModel()
            if len(courier.re_schedule) <= task_index + 1:
                last.nodeId = courier.re_schedule[task_index + 2].l_node
            else:
                last.nodeId = t.l_node
            courier.re_schedule.remove(task)
            paths1 = g.getShortPath(start, last, s)
            lengt_before = 0
            for p in paths1:
                lengt_before += p.length
            paths2 = g.getShortPath(start, end, s)
            lengt_after = 0
            for p in paths2:
                lengt_after += p.length
            paths3 = g.getShortPath(end, last, s)
            for p in paths3:
                lengt_after += p.length
            if lengt_before == 0:
                detour_rate = 0
            else:
                detour_rate = lengt_after / lengt_before
            temp_bidding = 2 + (courier.w * (task.weight / (courier.max_weight - courier.re_weight)) +
                                courier.c * detour_rate) * u * task.fare
            if temp_bidding > 2 + u * task.fare:
                temp_bidding = 2 + u * task.fare
            if temp_bidding < min_bidding:
                min_bidding = temp_bidding
                best_insert_prepoint = t
                cost_extime = (lengt_after - lengt_before) / (VELOCITY * 1000)
    if best_insert_prepoint == "":
        return "a", "b", "c"
    return best_insert_prepoint, round(min_bidding, 4), cost_extime


def FBP_BaseC1(courier, task, u, time_count):
    temp_task_set = []
    # start_time2 = time.time()
    best_insert_prepoint = ""
    min_bidding = 10000
    # start_time3 = time.time()
    cost_extime = 0
    min_detour_rate = 100

    for t in courier.re_schedule:
        start = NodeModel()
        start.nodeId = t.l_node
        end = NodeModel()
        end.nodeId = task.l_node
        paths = g.getShortPath(start, end, s)
        lengt = 0
        for p in paths:
            lengt += p.length
        temp_cost_time = t.reach_time
        courier.temp_location = courier.location
        if lengt / (VELOCITY * 1000) <= 0.5 * courier.sum_useful_time and \
                lengt / (VELOCITY * 1000) <= float(task.d_time) - time_count - float(temp_cost_time):

            task_index = courier.re_schedule.index(t)
            # print(task_index)
            courier.re_schedule.insert(task_index + 1, task)

            # task_index1 = courier.re_schedule.index(task)
            # print(task_index1)
            # print(len(courier.re_schedule))

            last = NodeModel()
            if len(courier.re_schedule) <= task_index + 1:
                last.nodeId = courier.re_schedule[task_index + 2].l_node
            else:
                last.nodeId = t.l_node
            courier.re_schedule.remove(task)
            paths1 = g.getShortPath(start, last, s)
            lengt_before = 0
            for p in paths1:
                lengt_before += p.length
            paths2 = g.getShortPath(start, end, s)
            lengt_after = 0
            for p in paths2:
                lengt_after += p.length
            paths3 = g.getShortPath(end, last, s)
            for p in paths3:
                lengt_after += p.length
            if lengt_before == 0:
                detour_rate = 0
            else:
                detour_rate = lengt_after / lengt_before
            temp_bidding = 2 + u * task.fare
            if detour_rate < min_detour_rate:
                min_detour_rate = detour_rate
                min_bidding = temp_bidding
                best_insert_prepoint = t
    if best_insert_prepoint == "":
        return "a", "b", "c"
    return best_insert_prepoint, min_bidding, cost_extime


def list_of_groups(init_list, children_list_len):
    list_of_groups = zip(*(iter(init_list),) *children_list_len)
    end_list = [list(i) for i in list_of_groups]
    count = len(init_list) % children_list_len
    end_list.append(init_list[-count:]) if count !=0 else end_list
    return end_list


def FBP_cKMB(courier, task, u, time_count):
    temp_task_set = []
    # start_time2 = time.time()
    best_insert_prepoint = ""
    min_bidding = 10000
    # start_time3 = time.time()
    cost_extime = 0
    min_detour_rate = 100000

    for t in courier.re_schedule:
        flag = True
        start = NodeModel()
        start.nodeId = t.l_node
        end = NodeModel()
        end.nodeId = task.l_node
        paths = g.getShortPath(start, end, s)
        lengt = 0
        for p in paths:
            lengt += p.length
        temp_cost_time = t.reach_time
        courier.temp_location = courier.location
        if lengt / (VELOCITY * 1000) + task.extime <= 0.5 * courier.sum_useful_time and \
                lengt / (VELOCITY * 1000) <= float(task.d_time) - time_count - float(temp_cost_time):
            if lengt < t.dis_next_point:
                if min_detour_rate <= 1:
                    flag = False
            else:
                if t.dis_next_point != 0 and min_detour_rate < (2 * lengt / t.dis_next_point) - 1:
                        flag = False

        if flag:
            task_index = courier.re_schedule.index(t)
            # print(task_index)
            courier.re_schedule.insert(task_index + 1, task)

            # task_index1 = courier.re_schedule.index(task)
            # print(task_index1)
            # print(len(courier.re_schedule))

            last = NodeModel()
            if len(courier.re_schedule) <= task_index + 1:
                last.nodeId = courier.re_schedule[task_index + 2].l_node
            else:
                last.nodeId = t.l_node
            courier.re_schedule.remove(task)

            lengt_before = t.dis_next_point

            lengt_after = lengt
            paths3 = g.getShortPath(end, last, s)
            for p in paths3:
                lengt_after += p.length

            if lengt_before == 0:
                detour_rate = 0
            else:
                detour_rate = lengt_after / lengt_before
            temp_bidding = 2 * task.task_num + (courier.w * (task.weight / (courier.max_weight - courier.re_weight)) +
                                courier.c * detour_rate) * u * task.fare
            if temp_bidding > 2 * task.task_num + u * task.fare:
                temp_bidding = 2 * task.task_num + u * task.fare
            if temp_bidding < min_bidding:
                min_bidding = temp_bidding
                min_detour_rate = detour_rate
                best_insert_prepoint = t
                cost_extime = (lengt_after - lengt_before) / (VELOCITY * 1000) + task.extime
    if best_insert_prepoint == "":
        return "a", "b", "c"
    return best_insert_prepoint, round(min_bidding, 4), cost_extime

# Batch Matching
# 该函数是批量匹配的核心函数，使用了KM算法来进行任务和快递员的匹配。
def BM_cKMB(temp_courier_pool, pick_task_pool, time_count, u):
    count_bidding_num = 0
    count_task_num = 0
    sum_bidding1 = 0
    sum_route_cost = 0
    bidding_matrix = []
    # start = time.time()
    match_list = []
    match_pair = {"t.num": 0, "c.num": 0, "result_pre": "", "result_bid": 0, "ex_time": 0}
    # print("任务池长度为%s，快递员池长度为%s" % (len(pick_task_pool), len(temp_courier_pool)))
    for t in pick_task_pool:
        count_task_num += t.task_num
        t.temp_bidding_set = []
        for c in temp_courier_pool:
            if (c.max_weight - c.re_weight) > t.weight:
                result_pre, result_bid, result_extime = FBP_cKMB(c, t, u, time_count)
                if result_pre != "a":
                    match_pair["t.num"] = t.num
                    match_pair["c.num"] = c.num
                    match_pair["result_pre"] = result_pre
                    match_pair["result_bid"] = result_bid
                    match_pair["ex_time"] = result_extime
                    # print("快递员编号%s,任务编号%s,插入任务点%s,报价%s,额外时间%s" %
                    #       (match_pair["c.num"], match_pair["t.num"], match_pair["result_pre"],
                    #        match_pair["result_bid"], match_pair["ex_time"]))
                    match_list.append(match_pair.copy())
                    t.temp_bidding_set.append((1/result_bid))
                else:
                    t.temp_bidding_set.append(0)
            else:
                t.temp_bidding_set.append(0)
        sum = 0
        for i in t.temp_bidding_set:
            sum += i
        if sum != 0:
            bidding_matrix.append(t.temp_bidding_set)
        # for x in bidding_matrix:
        #     for y in x:
        #         print('%s' % y, end=' ')
        #     print()
    # end = time.time()
    # print("生成矩阵时间", (end - start))
    # start = time.time()
    # print(np.shape(bidding_matrix))
    # print(bidding_matrix)
    if len(bidding_matrix) != 0:
        matcher = KMMatcher(bidding_matrix)
        sum, temp_match_pair = matcher.solve(verbose=True)
    # pick_task_pool[x[0] - i_count]就是任务
    # temp_courier_pool[x[1]]就是快递员
    #     print(f'匹配对是{temp_match_pair}')
        # print(match_list)
        i_count = 0
        for x in temp_match_pair:
            for m_p in match_list:
                # print(x[0], x[1])
                # print(pick_task_pool[x[0] - i_count])
                # print(temp_courier_pool[x[1]])
                # print(f'长度是{len(pick_task_pool)}')
                if pick_task_pool[x[0] - i_count].num == m_p["t.num"] and temp_courier_pool[x[1]].num == m_p["c.num"]:
                    insert_index = temp_courier_pool[x[1]].re_schedule.index(m_p["result_pre"])
                    temp_courier_pool[x[1]].re_schedule.insert(insert_index + 1, pick_task_pool[x[0] - i_count])
                    temp_courier_pool[x[1]].sum_useful_time -= m_p["ex_time"]
                    size_reschedule = len(temp_courier_pool[x[1]].re_schedule)
                    for i in range((insert_index + 2), size_reschedule):
                        temp_courier_pool[x[1]].re_schedule[i].reach_time += m_p["ex_time"]
                    temp_courier_pool[x[1]].re_weight += pick_task_pool[x[0] - i_count].weight
                    temp_courier_pool[x[1]].max_weight -= pick_task_pool[x[0] - i_count].weight
                    # print("%s分配给了%s" % (pick_task_pool[x[0] - i_count].num, temp_courier_pool[x[1]].num))
                    count_bidding_num += pick_task_pool[x[0] - i_count].task_num
                    sum_bidding1 += m_p["result_bid"]
                    sum_route_cost += m_p["ex_time"]
                    pick_task_pool.remove(pick_task_pool[x[0] - i_count])
                    i_count += 1
                    # print(f'i的值是{i_count}')
                    # print(f'删除后长度是{len(pick_task_pool)}')
                    break
    # print(f'完成任务个数{count_bidding_num}')
    # print(f'完成任务个数1{len(compeleted_task1)}')
    # end = time.time()
    # print("匹配时间", (end - start))
    # print("应该返回的报价", sum_bidding1)
    return sum_bidding1, sum_route_cost, count_bidding_num, count_task_num


def Combin(task_set, w_th, pl):
    flag = 0
    for t in task_set:
        for t1 in task_set:
            if t.num != t1.num:
                Qcorr = min(abs(t.weight + t1.weight), abs(t.weight + t1.weight - w_th))
                start = NodeModel()
                start.nodeId = t.l_node
                end = NodeModel()
                end.nodeId = t1.l_node
                paths = g.getShortPath(start, end, s)
                lengt = 0
                for p in paths:
                    lengt += p.length
                Pcorr = abs(lengt)
                Dcorr = abs(int(t.d_time) - int(t1.d_time)) / 3600
                # print(Qcorr, Pcorr, Dcorr)
                com = 1 / (1 + math.sqrt(Qcorr + Pcorr + Dcorr))
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


def FBP_GA(courier, task, u, time_count):
    temp_task_set = []
    # start_time2 = time.time()
    best_insert_prepoint = ""
    min_bidding = 10000
    # start_time3 = time.time()
    cost_extime = 0

    for t in courier.re_schedule:
        start = NodeModel()
        start.nodeId = t.l_node
        end = NodeModel()
        end.nodeId = task.l_node
        paths = g.getShortPath(start, end, s)
        lengt = 0
        for p in paths:
            lengt += p.length
        temp_cost_time = t.reach_time
        courier.temp_location = courier.location

        # 一些基本的判定条件来判断某个快递员事都能完成这个任务
        if lengt / (VELOCITY * 1000) <= 0.5 * courier.sum_useful_time and \
                lengt / (VELOCITY * 1000) <= float(task.d_time) - time_count - float(temp_cost_time):

            task_index = courier.re_schedule.index(t)
            # print(task_index)
            courier.re_schedule.insert(task_index + 1, task)

            # task_index1 = courier.re_schedule.index(task)
            # print(task_index1)
            # print(len(courier.re_schedule))

            last = NodeModel()
            if len(courier.re_schedule) <= task_index + 1:
                last.nodeId = courier.re_schedule[task_index + 2].l_node
            else:
                last.nodeId = t.l_node
            courier.re_schedule.remove(task)
            paths1 = g.getShortPath(start, last, s)
            lengt_before = 0
            for p in paths1:
                lengt_before += p.length
            paths2 = g.getShortPath(start, end, s)
            lengt_after = 0
            for p in paths2:
                lengt_after += p.length
            paths3 = g.getShortPath(end, start, s)
            for p in paths3:
                lengt_after += p.length
            if lengt_before == 0:
                detour_rate = 0
            else:
                detour_rate = lengt_after / lengt_before
            temp_bidding = 2 + (courier.w * (task.weight / (courier.max_weight - courier.re_weight)) +
                                courier.c * detour_rate) * u * task.fare
            if temp_bidding < min_bidding:
                min_bidding = temp_bidding
                best_insert_prepoint = t
                cost_extime = (lengt_after - lengt_before) / (VELOCITY * 1000)
    if best_insert_prepoint == "":
        return "a", "b", "c"
    return best_insert_prepoint, round(min_bidding, 4), cost_extime


def FBP_GA1(courier, task, u, time_count):
    temp_task_set = []
    # start_time2 = time.time()
    best_insert_prepoint = ""
    min_bidding = 10000
    # start_time3 = time.time()
    cost_extime = 0
    min_detour_rate = 100

    for t in courier.re_schedule:
        start = NodeModel()
        start.nodeId = t.l_node
        end = NodeModel()
        end.nodeId = task.l_node
        paths = g.getShortPath(start, end, s)
        lengt = 0
        for p in paths:
            lengt += p.length
        temp_cost_time = t.reach_time
        courier.temp_location = courier.location
        if lengt / (VELOCITY * 1000) <= 0.5 * courier.sum_useful_time and \
                lengt / (VELOCITY * 1000) <= float(task.d_time) - time_count - float(temp_cost_time):

            task_index = courier.re_schedule.index(t)
            # print(task_index)
            courier.re_schedule.insert(task_index + 1, task)

            # task_index1 = courier.re_schedule.index(task)
            # print(task_index1)
            # print(len(courier.re_schedule))

            last = NodeModel()
            if len(courier.re_schedule) <= task_index + 1:
                last.nodeId = courier.re_schedule[task_index + 2].l_node
            else:
                last.nodeId = t.l_node
            courier.re_schedule.remove(task)
            paths1 = g.getShortPath(start, last, s)
            lengt_before = 0
            for p in paths1:
                lengt_before += p.length
            paths2 = g.getShortPath(start, end, s)
            lengt_after = 0
            for p in paths2:
                lengt_after += p.length
            paths3 = g.getShortPath(end, last, s)
            for p in paths3:
                lengt_after += p.length
            if lengt_before == 0:
                detour_rate = 0
            else:
                detour_rate = lengt_after / lengt_before
            temp_bidding = 2 + u * task.fare
            if detour_rate < min_detour_rate:
                min_detour_rate = detour_rate
                min_bidding = temp_bidding
                best_insert_prepoint = t
    if best_insert_prepoint == "":
        return "a", "b", "c"
    return best_insert_prepoint, min_bidding, cost_extime


def FBP_KM(courier, task, u, time_count):
    temp_task_set = []
    # start_time2 = time.time()
    best_insert_prepoint = ""
    min_bidding = 10000
    # start_time3 = time.time()
    cost_extime = 0
    min_detour_rate = 100000

    for t in courier.re_schedule:
        flag = True
        start = NodeModel()
        start.nodeId = t.l_node
        end = NodeModel()
        end.nodeId = task.l_node
        paths = g.getShortPath(start, end, s)
        lengt = 0
        for p in paths:
            lengt += p.length
        temp_cost_time = t.reach_time
        courier.temp_location = courier.location
        if lengt / (VELOCITY * 1000) <= 0.5 * courier.sum_useful_time and \
                lengt / (VELOCITY * 1000) <= float(task.d_time) - time_count - float(temp_cost_time):
            if lengt < t.dis_next_point:
                if min_detour_rate <= 1:
                    flag = False
            else:
                if t.dis_next_point != 0 and min_detour_rate < (2 * lengt / t.dis_next_point) - 1:
                    flag = False

        if flag:
            task_index = courier.re_schedule.index(t)
            # print(task_index)
            courier.re_schedule.insert(task_index + 1, task)

            # task_index1 = courier.re_schedule.index(task)
            # print(task_index1)
            # print(len(courier.re_schedule))

            last = NodeModel()
            if len(courier.re_schedule) <= task_index + 1:
                last.nodeId = courier.re_schedule[task_index + 2].l_node
            else:
                last.nodeId = t.l_node
            courier.re_schedule.remove(task)

            lengt_before = t.dis_next_point

            lengt_after = lengt
            paths3 = g.getShortPath(end, last, s)
            for p in paths3:
                lengt_after += p.length

            if lengt_before == 0:
                detour_rate = 0
            else:
                detour_rate = lengt_after / lengt_before
            temp_bidding = 2 + (courier.w * (task.weight / (courier.max_weight - courier.re_weight)) +
                                courier.c * detour_rate) * u * task.fare
            if temp_bidding > 2 + u * task.fare:
                temp_bidding = 2 + u * task.fare
            if temp_bidding < min_bidding:
                min_bidding = temp_bidding
                min_detour_rate = detour_rate
                best_insert_prepoint = t
                cost_extime = (lengt_after - lengt_before) / (VELOCITY * 1000)
    if best_insert_prepoint == "":
        return "a", "b", "c"
    return best_insert_prepoint, round(min_bidding, 4), cost_extime


def BM_KM(temp_courier_pool, pick_task_pool, time_count, u):
    count_bidding_num = 0
    sum_bidding1 = 0
    sum_route_cost = 0
    bidding_matrix = []
    # start = time.time()
    match_list = []
    match_pair = {"t.num": 0, "c.num": 0, "result_pre": "", "result_bid": 0, "ex_time": 0}
    # print("任务池长度为%s，快递员池长度为%s" % (len(pick_task_pool), len(temp_courier_pool)))
    for t in pick_task_pool:
        t.temp_bidding_set = []
        for c in temp_courier_pool:
            if (c.max_weight - c.re_weight) > t.weight:
                result_pre, result_bid, result_extime = FBP_KM(c, t, u, time_count)
                if result_pre != "a":
                    match_pair["t.num"] = t.num
                    match_pair["c.num"] = c.num
                    match_pair["result_pre"] = result_pre
                    match_pair["result_bid"] = result_bid
                    match_pair["ex_time"] = result_extime
                    # print("快递员编号%s,任务编号%s,插入任务点%s,报价%s,额外时间%s" %
                    #       (match_pair["c.num"], match_pair["t.num"], match_pair["result_pre"],
                    #        match_pair["result_bid"], match_pair["ex_time"]))
                    match_list.append(match_pair.copy())
                    t.temp_bidding_set.append((1/result_bid))
                else:
                    t.temp_bidding_set.append(0)
            else:
                t.temp_bidding_set.append(0)
        sum = 0
        for i in t.temp_bidding_set:
            sum += i
        if sum != 0:
            bidding_matrix.append(t.temp_bidding_set)
        # for x in bidding_matrix:
        #     for y in x:
        #         print('%s' % y, end=' ')
        #     print()
    # end = time.time()
    # print("生成矩阵时间", (end - start))
    # start = time.time()
    # print(np.shape(bidding_matrix))
    # print(bidding_matrix)
    if len(bidding_matrix) != 0:
        matcher = KMMatcher(bidding_matrix)
        sum, temp_match_pair = matcher.solve(verbose=True)
    # pick_task_pool[x[0] - i_count]就是任务
    # temp_courier_pool[x[1]]就是快递员
    #     print(f'匹配对是{temp_match_pair}')
        # print(match_list)
        i_count = 0
        for x in temp_match_pair:
            for m_p in match_list:
                # print(x[0], x[1])
                # print(pick_task_pool[x[0] - i_count])
                # print(temp_courier_pool[x[1]])
                # print(f'长度是{len(pick_task_pool)}')
                if pick_task_pool[x[0] - i_count].num == m_p["t.num"] and temp_courier_pool[x[1]].num == m_p["c.num"]:
                    insert_index = temp_courier_pool[x[1]].re_schedule.index(m_p["result_pre"])
                    temp_courier_pool[x[1]].re_schedule.insert(insert_index + 1, pick_task_pool[x[0] - i_count])
                    temp_courier_pool[x[1]].sum_useful_time -= m_p["ex_time"]
                    size_reschedule = len(temp_courier_pool[x[1]].re_schedule)
                    for i in range((insert_index + 2), size_reschedule):
                        temp_courier_pool[x[1]].re_schedule[i].reach_time += m_p["ex_time"]
                    temp_courier_pool[x[1]].re_weight += pick_task_pool[x[0] - i_count].weight
                    temp_courier_pool[x[1]].max_weight -= pick_task_pool[x[0] - i_count].weight
                    # print("%s分配给了%s" % (pick_task_pool[x[0] - i_count].num, temp_courier_pool[x[1]].num))
                    count_bidding_num += 1
                    sum_bidding1 += m_p["result_bid"]
                    sum_route_cost += m_p["ex_time"]
                    pick_task_pool.remove(pick_task_pool[x[0] - i_count])
                    i_count += 1
                    # print(f'i的值是{i_count}')
                    # print(f'删除后长度是{len(pick_task_pool)}')
                    break
    # print(f'完成任务个数{count_bidding_num}')
    # print(f'完成任务个数1{len(compeleted_task1)}')
    # end = time.time()
    # print("匹配时间", (end - start))
    # print("应该返回的报价", sum_bidding1)
    return sum_bidding1, sum_route_cost, count_bidding_num


def FBP_Com(courier, task, u, time_count):
    temp_task_set = []
    # start_time2 = time.time()
    best_insert_prepoint = ""
    min_bidding = 10000
    min_lengt = 10000
    # start_time3 = time.time()
    cost_extime = 0
    cost_lengt = 0

    for t in courier.re_schedule:
        start = NodeModel()
        start.nodeId = t.l_node
        end = NodeModel()
        end.nodeId = task.l_node
        paths = g.getShortPath(start, end, s)
        lengt = 0
        for p in paths:
            lengt += p.length
        temp_cost_time = t.reach_time
        courier.temp_location = courier.location
        if lengt / (VELOCITY * 1000) <= 0.5 * courier.sum_useful_time and \
                lengt / (VELOCITY * 1000) <= float(task.d_time) - time_count - float(temp_cost_time):

            task_index = courier.re_schedule.index(t)
            # print(task_index)
            courier.re_schedule.insert(task_index + 1, task)

            # task_index1 = courier.re_schedule.index(task)
            # print(task_index1)
            # print(len(courier.re_schedule))

            last = NodeModel()
            if len(courier.re_schedule) <= task_index + 1:
                last.nodeId = courier.re_schedule[task_index + 2].l_node
            else:
                last.nodeId = t.l_node
            courier.re_schedule.remove(task)
            paths1 = g.getShortPath(start, last, s)
            lengt_before = 0
            for p in paths1:
                lengt_before += p.length
            paths2 = g.getShortPath(start, end, s)
            lengt_after = 0
            for p in paths2:
                lengt_after += p.length
            paths3 = g.getShortPath(end, last, s)
            for p in paths3:
                lengt_after += p.length
            if lengt_before == 0:
                detour_rate = 0
            else:
                detour_rate = lengt_after / lengt_before
            cost_lengt = lengt_after - lengt_before
            temp_bidding = 2 + (courier.w * (task.weight / (courier.max_weight - courier.re_weight)) +
                                courier.c * detour_rate) * u * task.fare
            if temp_bidding > 2 + u * task.fare:
                temp_bidding = 2 + u * task.fare
            if cost_lengt < min_lengt:
                min_lengt = cost_lengt
                min_bidding = temp_bidding
                best_insert_prepoint = t
                cost_extime = (lengt_after - lengt_before) / (VELOCITY * 1000)
    if best_insert_prepoint == "":
        return "a", "b", "c"
    return best_insert_prepoint, min_bidding, cost_extime
