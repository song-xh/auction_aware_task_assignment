from GraphUtils_ChengDu import *
from km_matcher import KMMatcher


# 本地匹配算法
# 计算路径和报价
# 对于本地平台无法满足或者大于阈值的任务，进入跨平台匹配集合，进入下一阶段的匹配
# 其他快递员的任务，直接进行本地匹配

def list_of_groups(init_list, children_list_len):
    list_of_groups = zip(*(iter(init_list),) * children_list_len)
    end_list = [list(i) for i in list_of_groups]
    count = len(init_list) % children_list_len
    end_list.append(init_list[-count:]) if count != 0 else end_list
    return end_list


def compute_utility(courier, task, detour_rate, gamma):
    '''
    计算效用函数
    '''
    if courier.max_weight > 0:
        delta_weight = 1-(task.weight / courier.max_weight)
    else:
        delta_weight = 0
    utility = gamma*delta_weight+(1-gamma)*(1-detour_rate)
    return utility


def find_best_insert(courier, task, u, time_count):
    """
    返回: 最优插入点, 最小报价, 额外时间, 效用
    """
    best_insert_prepoint = ""
    min_bidding = float('inf')
    cost_extime = 0
    min_detour_rate = float('inf')
    best_utility = -float('inf')

    for t in courier.re_schedule:
        flag = True
        start = NodeModel()
        start.nodeId = t.l_node
        end = NodeModel()
        end.nodeId = task.l_node
        paths = g.getShortPath(start, end, s)
        lengt = sum(p.length for p in paths)
        temp_cost_time = t.reach_time
        courier.temp_location = courier.location

        # 可行性判定
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
            courier.re_schedule.insert(task_index + 1, task)
            last = NodeModel()
            if len(courier.re_schedule) <= task_index + 1:
                last.nodeId = courier.re_schedule[task_index + 2].l_node
            else:
                last.nodeId = t.l_node
            courier.re_schedule.remove(task)

            lengt_before = t.dis_next_point
            lengt_after = lengt
            for p in g.getShortPath(end, last, s):
                lengt_after += p.length

            detour_rate = lengt_after / lengt_before if lengt_before != 0 else 0
            temp_bidding = 2 * task.task_num + (courier.w * (task.weight / max(1e-5, (courier.max_weight - courier.re_weight))) +
                                                courier.c * detour_rate) * u * task.fare
            if temp_bidding > 2 * task.task_num + u * task.fare:
                temp_bidding = 2 * task.task_num + u * task.fare

            # 效用（可根据实际设计）
            if (courier.max_weight - courier.re_weight) > 0:
                utility = (task.weight / (courier.max_weight -
                           courier.re_weight)) - detour_rate
            else:
                utility = -detour_rate

            if temp_bidding < min_bidding:
                min_bidding = temp_bidding
                min_detour_rate = detour_rate
                best_insert_prepoint = t
                cost_extime = (lengt_after - lengt_before) / \
                    (VELOCITY * 1000) + task.extime
                best_utility = utility

    if best_insert_prepoint == "":
        return None, None, None, None
    return best_insert_prepoint, round(min_bidding, 4), cost_extime, best_utility

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
    match_pair = {"t.num": 0, "c.num": 0,
                  "result_pre": "", "result_bid": 0, "ex_time": 0}
    # print("任务池长度为%s，快递员池长度为%s" % (len(pick_task_pool), len(temp_courier_pool)))
    for t in pick_task_pool:
        count_task_num += t.task_num
        t.temp_bidding_set = []
        for c in temp_courier_pool:
            if (c.max_weight - c.re_weight) > t.weight:
                result_pre, result_bid, result_extime = FBP_cKMB(
                    c, t, u, time_count)
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
                    insert_index = temp_courier_pool[x[1]].re_schedule.index(
                        m_p["result_pre"])
                    temp_courier_pool[x[1]].re_schedule.insert(
                        insert_index + 1, pick_task_pool[x[0] - i_count])
                    temp_courier_pool[x[1]].sum_useful_time -= m_p["ex_time"]
                    size_reschedule = len(temp_courier_pool[x[1]].re_schedule)
                    for i in range((insert_index + 2), size_reschedule):
                        temp_courier_pool[x[1]
                                          ].re_schedule[i].reach_time += m_p["ex_time"]
                    temp_courier_pool[x[1]
                                      ].re_weight += pick_task_pool[x[0] - i_count].weight
                    temp_courier_pool[x[1]
                                      ].max_weight -= pick_task_pool[x[0] - i_count].weight
                    # print("%s分配给了%s" % (pick_task_pool[x[0] - i_count].num, temp_courier_pool[x[1]].num))
                    count_bidding_num += pick_task_pool[x[0] -
                                                        i_count].task_num
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
                Qcorr = min(abs(t.weight + t1.weight),
                            abs(t.weight + t1.weight - w_th))
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
