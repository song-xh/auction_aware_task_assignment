# 地图工具类
import numpy as np
# from v1.utils.DistanceUtils import *
from DistanceUtils import *
import xml.sax
import uuid

# import DistanceUtils

# 定义一些常数

# 物理速度  40km/h = 11.11m/s
VELOCITY = 0.0011
# VELOCITY = 0.0050
# 最大索引数
MAX_INDEX_NUM = 196591
# 最大经度
MAX_LNG = -73.7
# 最小经度
MIN_LNG = -74.8559
# 最大纬度
MAX_LAT = 40.9286
# 最小纬度
MIN_LAT = 40.4982
# 创建距离工具类
distanceUtils = DistanceUtils()
# 水平长度
HORIZONTAL_LENGTH = distanceUtils.getNodeDistance(MIN_LAT, MAX_LNG, MIN_LAT, MIN_LNG)
# 垂直长度
VERTICAL_LENGTH = distanceUtils.getNodeDistance(MAX_LAT, MIN_LNG, MIN_LAT, MIN_LNG)
# 总网格 100*100
GRID_SIZE = 100
# X轴最多网格数
GRID_XNUM = int(VERTICAL_LENGTH / GRID_SIZE) + 1
# Y轴最多网格数
GRID_YNUM = int(HORIZONTAL_LENGTH / GRID_SIZE) + 1


# 节点
class NodeModel(object):
    def __init__(self):
        # id
        self.nodeId = None
        # 虚拟id
        self.vnodeId = None
        # 经度
        self.lat = 0.0
        # 纬度
        self.lng = 0.0
        # 计数器
        self.counter = 0
        # 邻居list
        self.neighbors = []
        # 边映射map
        self.nEdge = {}


# 边
class EdgeModel(object):
    def __init__(self):
        # id
        self.edgeId = None
        # 起点
        self.startNode = None
        # 终点
        self.endNode = None
        # 中间点list
        self.nodeList = []
        # 长度
        self.length = 0
        # 边上已有的快递员的列表
        self.Lc = []


# 网格边缘
class GridEdgeItem(object):
    def __init__(self, e, x, y):
        # 边
        self.edge = e
        # x
        self.gx = x
        # y
        self.gy = y


# 网格
class GridModel(object):
    def __init__(self, index):
        # 网格编号
        self.index = index
        # 点list
        self.Tnode = []
        # GridEdgeItem list
        self.Tedge = []

        # String类型的边list
        self.edgeList = []
        # String类型的点list
        self.nodeList = []

        # String类型的边集合
        self.edgeSet = set()


# 地图内容
class ServletContext(object):
    def __init__(self):
        # 边映射
        self.eMap = {}
        # 点映射
        self.nMap = {}
        # 边list
        self.eList = []
        # 点list
        self.nList = []
        # 快递员list
        self.courierList = []
        # 任务list
        self.taskList = []
        # 网格
        self.grids = []
        temp = []
        for i in range(GRID_XNUM):
            for j in range(GRID_YNUM):
                temp.append(GridModel("(%s,%s)" % (i, j)))

            self.grids.append(temp)
            temp = []


# 地图xml文件Handler
class NewGraphHandler(xml.sax.ContentHandler):
    def __init__(self, nMap, eList):
        '''
        :param nMap: 节点map
        :param eList: 边list
        '''
        self.isNode = False
        self.isEdge = False
        self.isNd = False
        self.isTag = False
        self.nMap = nMap
        self.eList = eList
        self.edge = None

    # 元素开始事件处理
    def startElement(self, tag, attributes):

        if tag == "node":
            self.isNode = True
            node = NodeModel()
            id = attributes["id"]
            node.nodeId = id
            node.lat = attributes["lat"]
            node.lng = attributes["lon"]
            self.nMap[id] = node
        elif tag == "way":
            self.isEdge = True
            self.edge = EdgeModel()
            self.edge.edgeId = attributes["id"]
        elif self.isEdge and tag == "nd":
            self.isNd = True
            ref = attributes["ref"]
            n = self.nMap[ref]
            n.counter += 1
            self.nMap[n.nodeId] = n
            self.edge.nodeList.append(ref)
        elif self.isEdge and tag == "tag":
            self.isTag = True
            k = attributes["k"]
            if k == "highway":
                v = attributes["v"]
                if v == "footway":
                    return
                if v == "bridelway":
                    return
                if v == "steps":
                    return
                if v == "path":
                    return
                if v == "cycleway":
                    return
                if v == "proposed":
                    return
                if v == "construction":
                    return
                if v == "pedestrian":
                    return
                if v == "bus_stop":
                    return
                if v == "crossing":
                    return
                if v == "elevator":
                    return
                self.eList.append(self.edge)

    # 元素结束事件处理
    def endElement(self, tag):
        if tag == "node":
            self.isNode = False
        elif tag == "way":
            self.isEdge = False
        elif tag == "tag":
            self.isTag = False
        elif tag == "nd":
            self.isNd = False


class GraphUtils(object):
    def __init__(self):
        pass

    def saxBigGraphImport(self, filePath, sContext):
        '''
        地图数据导入
        # :param file_path: 地图路径
        :param sContext:
        :return:
        '''
        # 打开地图文件
        file = open(filePath)
        # 节点map
        nMap = {}
        # 边map
        eMap = {}
        # 边list
        eList = []
        # 节点集合
        nSet = set()

        try:
            # 创建xml解析器
            parser = xml.sax.make_parser()
            # turn off namepsaces
            parser.setFeature(xml.sax.handler.feature_namespaces, 0)
            # 重写ContextHandler
            Handler = NewGraphHandler(nMap, eList)
            print("-------------Start parsing-------------")
            parser.setContentHandler(Handler)
            # 开始解析地图文件
            parser.parse(filePath)
            print("end parsing with: nodes : %s  |   edges: %s" % (len(nMap), len(eList)))

            for i in range(len(eList)):
                # 依次对每个边进行处理
                eModel = eList[i]
                # 获取边的起点
                start = eModel.nodeList[0]
                # 获取终点
                end = eModel.nodeList[len(eModel.nodeList) - 1]
                # 从nodemap映射关系里里获得startnode点
                nStart = nMap[start]
                # 从nodemap映射关系里获得边的终点的endnode点
                nEnd = nMap[end]
                # 临时长度
                tentativeLength = 0.0
                # 该边的起点
                pointer = nStart
                # 某一条边上有很多点，这个循环可以依次遍历这条边上从起点到终点所有的点
                for k in range(1, len(eModel.nodeList) - 1):
                    # 依次取边上的内部包含的每个点
                    internNode = nMap[eModel.nodeList[k]]
                    # 计算pointer和interNode之间的距离
                    tentativeLength += distanceUtils.getDistance(pointer, internNode)
                    if internNode.counter > 1:
                        # 初始化一条新边
                        newEdge = EdgeModel()
                        # 边id随机，获得对象的字段的值，然后转成string类型，并且去掉前后空白
                        newEdge.edgeId = str(uuid.uuid1()).replace("-", "").strip()
                        newEdge.startNode = nStart
                        newEdge.endNode = internNode
                        # 新的边的点列表NodeList增加上起点和终点的nodeID
                        newEdge.nodeList.append(nStart.nodeId)
                        newEdge.nodeList.append(internNode.nodeId)
                        newEdge.length = tentativeLength
                        # 如果nSet中不包含nStart，nSet就增加nStart，【把边两端的点（起点）加入了nset】
                        if nStart not in nSet:
                            nSet.add(nStart)

                        if internNode not in nSet:
                            nSet.add(internNode)
                        # nStart的neighbor不包含internNode时增加internNode.nodeid【给nStart增加internode（内部的点）作为新的邻居节点】
                        if internNode.nodeId not in nStart.neighbors:
                            nStart.neighbors.append(internNode.nodeId)
                            # 更新nstart的所连得边的list
                            nStart.nEdge[internNode.nodeId] = newEdge.edgeId
                            nMap[nStart.nodeId] = nStart

                        if nStart.nodeId not in internNode.neighbors:
                            internNode.neighbors.append(nStart.nodeId)
                            internNode.nEdge[nStart.nodeId] = newEdge.edgeId
                            nMap[internNode.nodeId] = internNode
                        eMap[newEdge.edgeId] = newEdge
                        tentativeLength = 0.0
                        nStart = internNode
                        pointer = nStart
                    else:
                        pointer = internNode
                # 获取pointer和nEnd的距离，并且累加到tentativelength
                tentativeLength += distanceUtils.getDistance(pointer, nEnd)
                finalEdge = EdgeModel()
                finalEdge.edgeId = str(uuid.uuid1()).replace("-", "").strip()
                finalEdge.length = tentativeLength
                finalEdge.startNode = nStart
                finalEdge.endNode = nEnd
                finalEdge.nodeList.append(nStart.nodeId)
                finalEdge.nodeList.append(nEnd.nodeId)

                if nStart not in nSet:
                    nSet.add(nStart)

                if nEnd not in nSet:
                    nSet.add(nEnd)

                # 如果起点和终点不包含相邻关系，就把相邻关系加入
                if nEnd.nodeId not in nStart.neighbors:
                    nStart.neighbors.append(nEnd.nodeId)
                    nStart.nEdge[nEnd.nodeId] = finalEdge.edgeId
                    nMap[nStart.nodeId] = nStart

                if nStart.nodeId not in nEnd.neighbors:
                    nEnd.neighbors.append(nStart.nodeId)
                    nEnd.nEdge[nStart.nodeId] = finalEdge.edgeId
                    nMap[nEnd.nodeId] = nEnd

                # 把最终的边的关系放在eMap中，保存边的id和对应的边
                eMap[finalEdge.edgeId] = finalEdge
            # 深度优先搜索之前的结点个数
            print("before DFS nodeNumber: %s  edgeNumber: %s" % (len(nSet), len(eMap)))

            # 将set转为list
            nList = list(nSet)
            # 深度优先搜索后的边的列表
            edList = self.DFSSearch(nMap, eMap, nList[0], sContext)
            # 依次遍历深度优先搜索后的边的列表中的每一条边
            num = 0
            for i in range(len(edList)):
                e = edList[i]
                # 获取边的起点和终点
                nStart = e.startNode
                nEnd = e.endNode

                # 输入四个经纬度后计算距离 / GRID_size得到网格坐标

                # 起点x
                xIndex = int(distanceUtils.getNodeDistance(nStart.lat, nStart.lng, MAX_LAT, nStart.lng)
                             / GRID_SIZE)
                # 起点y
                yIndex = int(distanceUtils.getNodeDistance(nStart.lat, nStart.lng, nStart.lat, MIN_LNG)
                             / GRID_SIZE)
                # 终点x
                xeIndex = int(distanceUtils.getNodeDistance(nEnd.lat, nEnd.lng, MAX_LAT, nEnd.lng)
                              / GRID_SIZE)
                # 终点y
                yeIndex = int(distanceUtils.getNodeDistance(nEnd.lat, nEnd.lng, nEnd.lat, MIN_LNG)
                              / GRID_SIZE)

                # 输出起点的经度，纬度
                # print("start:(%s , %s)" % (nStart.lng, nStart.lat))
                # 输出起点的x坐标，起点的y坐标，网格中的x的个数，网格中的Y的个数
                # print("输出起点的坐标:( %s, %s )，网格中的x的个数:%s ，网格中的Y的个数:%s " % (xIndex, yIndex, GRID_XNUM, GRID_YNUM))

                # 在这种最大情况下（边界情况下，设置Yindex和Yindex）
                if xIndex > GRID_XNUM - 1:
                    xIndex = GRID_XNUM - 1
                if yIndex > GRID_YNUM - 1:
                    yIndex = GRID_YNUM - 1

                # 更新网格的索引信息中的edge边列表

                if e.edgeId not in sContext.grids[xIndex][yIndex].edgeSet:
                    sContext.grids[xIndex][yIndex].edgeList.append(e.edgeId)
                    sContext.grids[xIndex][yIndex].edgeSet.add(e.edgeId)

                # 输出边的终点的经度，和纬度
                # print("end:( %s, %s )" % (nEnd.lng, nEnd.lat))
                # print("边的终点的x索引: %s 和y索引: %s " % (xeIndex, yeIndex))
                num += 1

                if xeIndex > GRID_XNUM - 1:
                    xeIndex = GRID_XNUM - 1
                if yeIndex > GRID_YNUM - 1:
                    yeIndex = GRID_YNUM - 1

                # 更新网格的索引信息中的edge边列表
                if e.edgeId not in sContext.grids[xeIndex][yeIndex].edgeSet:
                    sContext.grids[xeIndex][yeIndex].edgeList.append(e.edgeId)
                    sContext.grids[xeIndex][yeIndex].edgeSet.add(e.edgeId)

            # for i in range(len(edList)):
                # print("")
            # 把所有的边的两端node节点经纬度，x，y输出一遍后，图处理结束
            print("end of graph processing")
            # print(f'共有{num}条边')

        except IOError:
            print("************")

    def DFSSearch(self, nMap, eMap, start, context):
        '''
        深度优先搜索
        :param nMap:节点
        :param eMap: 边
        :param start: 开始点
        :param context:
        :return:
        '''
        # 节点list
        stack = []
        closeList = []
        edgeList = []

        closeSet = set()
        edgeSet = set()

        stack.append(start)
        count = 0
        iteration = 0
        while len(stack) != 0:
            cur = stack[len(stack) - 1]

            stack.remove(stack[len(stack) - 1])

            if cur.nodeId not in closeSet:
                count += 1
                closeList.append(cur)
                closeSet.add(cur.nodeId)
                for i in range(len(cur.neighbors)):
                    neighbor = nMap[cur.neighbors[i]]
                    stack.append(neighbor)
                    edgePattern = cur.nEdge[neighbor.nodeId]
                    e = eMap[edgePattern]
                    if e.edgeId not in edgeSet:
                        edgeList.append(eMap[edgePattern])
                        edgeSet.add(e.edgeId)

        context.nMap = nMap
        context.eMap = eMap
        context.nList = closeList
        context.eList = edgeList
        print("After DFS nodeNumber: %s  |  edgeNumber:%s" % (len(closeList), len(edgeList)))
        return edgeList

    def heuristic_cost(self, cur, end):

        """时间成本

        :param cur:当前节点
        :param end: 终节点
        :return:

        """
        cost = 0.0
        cost = distanceUtils.getNodeDistance(cur.lat, cur.lng, end.lat, end.lng) / VELOCITY
        return cost

    def reconstructPaths(self, startPattern, trace, nMap, eMap):
        '''
        重建路径
        :param startPattern:
        :param trace:轨迹
        :param nMap:点集合
        :param eMap:边集合
        :return:
        '''
        paths = []
        current = startPattern
        while current in trace.keys():
            pre = current
            current = trace[current]
            node = nMap[current]
            edgePattern = node.nEdge[pre]
            edge = eMap[edgePattern]
            # 将边插入list的最前边
            paths.insert(0, edge)

        return paths

    def getShortPath(self, start, end, context):
        '''
        使用迪杰特斯拉算法获得最短路径,求在ServletContext中从start到 end的最短路径
        :param start:开始点
        :param end:结束点
        :param context:地图
        :return:边的列表edlist
        '''
        # 定义了边的列表作为path
        paths = []
        # 得分map
        gScore = {}
        # final得分map
        fScore = {}
        # 存放许多点list
        openList = []
        closeSet = set()
        # 存放字符串
        openSet = set()
        # 轨迹map
        track = {}
        nMap = context.nMap
        eMap = context.eMap

        # 起点node
        start = nMap[start.nodeId]
        start.nodeId = start.nodeId
        # 终点
        end = nMap[end.nodeId]
        end.nodeId = end.nodeId

        # 把起点加进去（节点node）
        openList.append(start)
        # 把起点的vnodeId加进去（字符）
        openSet.add(start.nodeId)
        gScore[start.nodeId] = 0.0
        # 把start.nodeid和从“起点 - 终点”的时间的映射关系放进去
        fScore[start.nodeId] = self.heuristic_cost(start, end)
        # 当节点非空时
        while len(openList) != 0:
            # 定义当前点
            cur = NodeModel()
            pos = 0
            min = fScore[openList[0].nodeId]
            for i in range(len(openList)):
                if fScore[openList[i].nodeId] < min:
                    min = fScore[openList[i].nodeId]
                    pos = i

            cur = openList[pos]
            if cur.nodeId == end.nodeId:
                return self.reconstructPaths(cur.nodeId, track, nMap, eMap)

            openList.remove(cur)
            openSet.remove(cur.nodeId)
            closeSet.add(cur.nodeId)

            for i in range(len(cur.neighbors)):
                neighbor = nMap[cur.neighbors[i]]
                if neighbor.nodeId in closeSet:
                    continue
                eid = cur.nEdge[neighbor.nodeId]
                e = eMap[eid]
                tentative_score = gScore[cur.nodeId] + e.length / VELOCITY

                if neighbor.nodeId not in openSet:
                    openSet.add(neighbor.nodeId)
                    openList.append(neighbor)
                    gScore[neighbor.nodeId] = float('inf')
                    fScore[neighbor.nodeId] = float('inf')
                elif tentative_score >= gScore[neighbor.nodeId]:
                    continue

                track[neighbor.nodeId] = cur.nodeId
                gScore[neighbor.nodeId] = tentative_score
                fScore[neighbor.nodeId] = tentative_score + self.heuristic_cost(neighbor, end)

        print("no paths suitable.")

        return paths

    def findNode(self, lat, lng, sContext):
        '''
        查找经纬度在地图路网上所对应的节点
        :param lat: 经度
        :param lng: 纬度
        :param sContext:地图内容
        :return: 节点id
        '''
        # 节点list
        nodeList = sContext.nList
        nodeId = None
        # 水平距离
        distance = HORIZONTAL_LENGTH
        for i in range(len(nodeList)):
            node = nodeList[i]
            temp = distanceUtils.getNodeDistance(lat, lng, node.lat, node.lng)
            # 若此经纬度恰好对应某个节点，就返回此节点
            if temp == 0:
                nodeId = node.nodeId
                break
            # 若此经纬度不是地图中的一个节点，就返回离它最近的节点
            elif temp < distance:
                distance = temp
                nodeId = node.nodeId

        return nodeId


s = ServletContext()
g = GraphUtils()
g.saxBigGraphImport("Data/map_ChengDu", s)


if __name__ == "__main__":
    s = ServletContext()
    g = GraphUtils()
    g.saxBigGraphImport("Data/map_ChengDu", s)

    # start = NodeModel()
    # start.nodeId = "1919585115"
    # end = NodeModel()
    # end.nodeId = "1919585130"
    start = NodeModel()
    start.nodeId = "1964427886"
    end = NodeModel()
    end.nodeId = "3582961906"
    paths = g.getShortPath(start, end, s)
    lenght = 0
    print("Shortest path:")
    for p in paths:
        print("%s---->%s" % (p.startNode.nodeId, p.endNode.nodeId))
        lenght += p.length
        # print(np.round(p.length / (VELOCITY * 1000), 2))
    print("Shortest distance:", lenght)

    print("经纬度（30.7068375，104.0432570）所对应的节点Id为：", g.findNode("30.66967", "104.10345", s))

    print("3541427561 节点所对应经纬度为（%s,%s）" % (s.nMap["3541427561"].lat, s.nMap["3541427561"].lng))
