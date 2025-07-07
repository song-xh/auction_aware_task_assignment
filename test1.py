import random
# 调参：快递员数量
a = random.Random()
# # 指定相同的随机种子，共享随机状态
a.seed(1)

b = a.sample([1,2,3,4,5],3)
print(b)