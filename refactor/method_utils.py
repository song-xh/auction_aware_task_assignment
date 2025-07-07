from graph import *
import numpy as np

'''
匹配算法会用到的一些工具方法
这里的内容我还没有细看，所以只做整理，没有修改实现代码
'''


#max weight assignment
class KMMatcher:

    ## weights : nxm weight matrix (numpy , float), n <= m
    def __init__(self, weights):
        weights = np.array(weights).astype(np.float32)
        self.weights = weights
        self.n, self.m = weights.shape
        assert self.n <= self.m
        # init label
        self.label_x = np.max(weights, axis=1)
        self.label_y = np.zeros((self.m, ), dtype=np.float32)

        self.max_match = 0
        self.xy = -np.ones((self.n,), dtype=np.int_)
        self.yx = -np.ones((self.m,), dtype=np.int_)

    def do_augment(self, x, y):
        self.max_match += 1
        while x != -2:
            self.yx[y] = x
            ty = self.xy[x]
            self.xy[x] = y
            x, y = self.prev[x], ty

    def find_augment_path(self):
        self.S = np.zeros((self.n,), np.bool_)
        self.T = np.zeros((self.m,), np.bool_)

        self.slack = np.zeros((self.m,), dtype=np.float32)
        self.slackyx = -np.ones((self.m,), dtype=np.int_)  # l[slackyx[y]] + l[y] - w[slackx[y], y] == slack[y]

        self.prev = -np.ones((self.n,), np.int_)

        queue, st = [], 0
        root = -1

        for x in range(self.n):
            if self.xy[x] == -1:
                queue.append(x)
                root = x
                self.prev[x] = -2
                self.S[x] = True
                break

        self.slack = self.label_y + self.label_x[root] - self.weights[root]
        self.slackyx[:] = root

        while True:
            while st < len(queue):
                x = queue[st]; st+= 1

                is_in_graph = np.isclose(self.weights[x], self.label_x[x] + self.label_y)
                nonzero_inds = np.nonzero(np.logical_and(is_in_graph, np.logical_not(self.T)))[0]

                for y in nonzero_inds:
                    if self.yx[y] == -1:
                        return x, y
                    self.T[y] = True
                    queue.append(self.yx[y])
                    self.add_to_tree(self.yx[y], x)

            self.update_labels()
            queue, st = [], 0
            is_in_graph = np.isclose(self.slack, 0)
            nonzero_inds = np.nonzero(np.logical_and(is_in_graph, np.logical_not(self.T)))[0]

            for y in nonzero_inds:
                x = self.slackyx[y]
                if self.yx[y] == -1:
                    return x, y
                self.T[y] = True
                if not self.S[self.yx[y]]:
                    queue.append(x)
                    self.add_to_tree(self.yx[y], x)

    def solve(self, verbose = False):
        while self.max_match < self.n:
            x, y = self.find_augment_path()
            self.do_augment(x, y)

        sum = 0.
        match_pair = []
        for x in range(self.n):
            if verbose:
                # print('match {} to {}, weight {:.4f}'.format(x, self.xy[x], self.weights[x, self.xy[x]]))
                match_pair.append((x, self.xy[x]))
            sum += self.weights[x, self.xy[x]]
        self.best = sum
        # if verbose:
        #     print('ans: {:.4f}'.format(sum))
        return sum, match_pair


    def add_to_tree(self, x, prevx):
        self.S[x] = True
        self.prev[x] = prevx

        better_slack_idx = self.label_x[x] + self.label_y - self.weights[x] < self.slack
        self.slack[better_slack_idx] = self.label_x[x] + self.label_y[better_slack_idx] - self.weights[x, better_slack_idx]
        self.slackyx[better_slack_idx] = x

    def update_labels(self):
        delta = self.slack[np.logical_not(self.T)].min()
        self.label_x[self.S] -= delta
        self.label_y[self.T] += delta
        self.slack[np.logical_not(self.T)] -= delta



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





# 快递员移动，修改相关变量值
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

