# 距离计算类
import math

# 地球半径
EARTH_RADIUS = 6378.137


class DistanceUtils(object):

    def rad(self, d):
        '''
        计算弧度
        :param d: 经纬度值
        :return:
        '''
        r = 0
        d = float(d)

        r = d * math.pi / 180.0

        return r

    def getNodeDistance(self, lat1Str, lng1Str, lat2Str, lng2Str):
        '''
        计算两点间距离
        :param lat1Str:起点经度
        :param lng1Str: 起点纬度
        :param lat2Str:终点经度
        :param lng2Str:终点纬度
        :return: 距离
        '''

        # 纬度弧度
        radLat1 = self.rad(lat1Str)
        radLat2 = self.rad(lat2Str)

        # 起点，终点弧度差异
        difference = radLat1 - radLat2
        mdifference = self.rad(lng1Str) - self.rad(lng2Str)

        distance = 2 * math.asin(math.sqrt(math.pow(math.sin(difference / 2), 2)
                                           + math.cos(radLat1) * math.cos(radLat2)
                                           * math.pow(math.sin(mdifference / 2), 2)))

        distance = distance * EARTH_RADIUS
        # round为四舍五入
        distance = round(distance * 10000) * 1000 / 100000

        return distance

    def getDistance(self, start, end):
        '''
        计算起点和终点的距离
        :param start: Node对象
        :param end: Node对象
        :return:
        '''

        return self.getNodeDistance(start.lat, start.lng, end.lat, end.lng)


if __name__ == "__main__":
    dis = DistanceUtils()
    print(dis.getNodeDistance(10, 21, 20, 20))
