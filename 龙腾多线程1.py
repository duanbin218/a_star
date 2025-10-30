import cv2
from 新大漠插件 import *
import sys
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QEvent
from kmNet类封装 import InputBroker, MyController, 延时, 游戏坐标系统


import heapq
import numpy as np
import time

# 方案B（默认）：单工人线程 + 优先级队列串行所有键鼠操作。
# - 优先级越小越紧急（0 = 抢占级，如紧急逃跑或加血）。
# - 正常打怪逻辑使用默认优先级 100，保持顺序执行。
# - 通过 input_broker.create_proxy() 获得 my_con_via_broker，直接调用其鼠标/键盘方法即可自动排队。
#   如需调整行为，可在调用时增加 input_priority/input_name/input_block/input_timeout 关键字参数。
# 如需添加新的高优先级命令，调用 input_broker.submit(action, priority=0, name="紧急逃跑")。
# 方案A：在 kmNet类封装.safe_keypress 中提供最小改动的互斥锁版本，必要时可退回。
#
# 本地验证（Windows）：
# 1. 在安装了大漠插件（DM）和 pywin32 的环境运行 GUI，启动“打怪”“血量”线程。
#    观察日志，低血量时抢占触发，键鼠操作串行无冲突。
# 2. 若缺少 DM 或 pywin32：
#    - DM 不存在时，相关 API 会抛异常；InputBroker 仍可单独测试，使用 my_con 模拟。
#    - 无 pywin32 时，需安装或将 MyController 相关调用替换为 mock；Broker 不依赖额外三方库。

my_con = MyController()
input_broker = InputBroker(my_con)
my_con_via_broker = input_broker.create_proxy()
游戏坐标方位 = 游戏坐标系统(my_con_via_broker)


def 提交输入任务(action, *args, priority: int = 100, name: str = "", block: bool = True, **kwargs):
    """封装 Broker 提交，避免每次重复填写参数。"""

    return input_broker.submit(action, *args, priority=priority, name=name, block=block, **kwargs)

def 随机延时(最小延时,最大延时):
    随机时间 = random.randint(最小延时,最大延时)
    # print(f"随机延时时间:{随机时间}毫秒")
    延时(随机时间)

with open(r"./pic/wupin/wupin.txt",'r',encoding='ANSI') as f:
    物品图片路径 = f.read()
    物品图片路径 = 物品图片路径.replace('\n','|')
    物品路径列表 = 物品图片路径.split('|')
    print(物品路径列表)

with open(r"./pic/guaiwu/guaiwu.txt",'r',encoding='UTF-8') as f:
    怪物图片路径 = f.read()
    怪物图片路径 = 怪物图片路径.replace('\n','|')
    怪物路径列表 = 怪物图片路径.split('|')
    print(怪物路径列表)

def 识别人物当前坐标():
    识别结果 = dms[0].Ocr(48, 1057, 108, 1078, "#255-50|#253-50", 1)
    if 识别结果 != '':
        识别结果 = 识别结果.strip(":")
        分割结果 = 识别结果.split(':')
        人物游戏x = int(分割结果[0])
        人物游戏y = int(分割结果[1])
        return 人物游戏x,人物游戏y
    return 0




class WorkerThread(QThread):

    caozuo = pyqtSignal(str)
    jiankong = pyqtSignal(str)

    def __init__(self,大漠对象,句柄,线程名):
        super().__init__()
        self.大漠对象 = 大漠对象
        self.大漠对象.SetDict(0, r"./字库/数字.txt")
        self.句柄 = 句柄
        self.线程名 = 线程名


    def run(self):
        窗口标题 = self.大漠对象.GetWindowTitle(self.句柄)

        if self.线程名 == '打怪':
            self.caozuo.emit(f"线程名:{self.线程名}|{窗口标题}|线程启动成功")
            self.打怪()
            # self.押镖()
        elif self.线程名 == '血量':
            self.jiankong.emit(f"线程名:{self.线程名}|{窗口标题}|线程启动成功")
            self.监控血量()

        # self.找怪()
        # self.caozuo.emit("开启线程成功")
        # self.测试()

        # 大范围找怪 : 5, 28, 1916, 823

    def 找最近怪(self,x1,y1,x2,y2):
        返回_找图AIEx = self.大漠对象.AiFindPicEx(x1,y1,x2,y2, fr"./{怪物图片路径}", 0.82, 0)
        if 返回_找图AIEx != "":
            返回_最近怪物 = self.大漠对象.FindNearestPos(返回_找图AIEx, 0, 966, 463)
            分割结果 = 返回_最近怪物.split(',')
            序号 = int(分割结果[0])
            # 获取怪物名字屏幕坐标
            怪物屏幕x = int(分割结果[1])
            怪物屏幕y = int(分割结果[2])
            return 怪物屏幕x,怪物屏幕y
        return -1,-1

    def 监控血量(self):
        try:
            while True:
                识别结果 = self.大漠对象.Ocr(21,1042,81,1055, "#255-50|#253-50", 1)
                if 识别结果 != '':
                    识别结果 = 识别结果.strip(":")
                    分割结果 = 识别结果.split('/')
                    当前血量 = int(分割结果[0])
                    最大血量 = int(分割结果[1])
                    self.jiankong.emit(f"当前血量:{当前血量}|最大血量:{最大血量}")
                    if 0 < 当前血量/最大血量 < 0.9:
                        self.jiankong.emit("要加血了,按F1加血")
                        提交输入任务(
                            my_con.键盘点击,
                            58,
                            priority=0,
                            name="紧急加血",
                            block=False,
                        )
                        随机延时(500, 1000)

                    elif 当前血量 == 0:
                        self.jiankong.emit("人物已死亡,需要重新登录游戏")
                time.sleep(1)
        except Exception as e:
            print(e)

    def 捡取物品(self):
        try:
            z, x, y = self.大漠对象.AiFindPic(6, 29, 1916, 822, fr"./{物品图片路径}", 0.5, 0)
            if z != -1:
                # 求出物品的中心屏幕坐标
                中心x,中心y = x+12,y+23
                print(f"中心x{中心x},中心y{中心y}")
                识别结果 = self.大漠对象.Ocr(48, 1057, 108, 1078, "#255-50|#253-50", 1)
                if 识别结果 != '':
                    分割结果 = 识别结果.split(':')
                    人物x = int(分割结果[0])
                    人物y = int(分割结果[1])
                    print(f"人物x{人物x},人物y{人物y}")
                    # 求物品游戏坐标方位
                    物品x,物品y = 屏幕坐标转游戏坐标方位(人物x,人物y,中心x,中心y)
                    print(f"物品x{物品x},物品y{物品y}")
                    print("------------------------------------------------------------------------------")
            else:
                print("未找到图片")
                return

            for i in range(100):
                识别结果 = self.大漠对象.Ocr(48, 1057, 108, 1078, "#255-50|#253-50", 1)
                if 识别结果 != '':
                    分割结果 = 识别结果.split(':')
                    人物x = int(分割结果[0])
                    人物y = int(分割结果[1])
                    print(f"人物:{人物x},{人物y}")
                    目标方位 = 游戏坐标方位.判断方位(物品x, 物品y, 人物x, 人物y)
                    if abs(物品x - 人物x) == 1 or abs(物品y - 人物y) == 1:
                        提交输入任务(
                            游戏坐标方位.左键点击方位_走路,
                            目标方位,
                            100,
                            300,
                            name="捡取物品-走路",
                        )
                    else:
                        提交输入任务(
                            游戏坐标方位.右键点击方位_跑步,
                            目标方位,
                            100,
                            300,
                            name="捡取物品-跑步",
                        )

                    if 物品x == 人物x and 物品y == 人物y:
                        print(f"到达{物品x},{物品y}")
                        break
                else:
                    continue
                随机延时(30,90)
        except Exception as e:
            print(str(e))

    def 八方a星寻路(self, start_x, start_y, end_x, end_y, map_img,distance=0,enb_deviation=0):
        """
        八方向A*寻路（实时安全版）- 增加终点容差和避障距离
        """
        h, w = map_img.shape[:2]
        if not (0 <= start_x < w and 0 <= start_y < h and 0 <= end_x < w and 0 <= end_y < h):
            print("坐标越界，终止寻路")
            return []

        directions = [
            (-1, 0), (1, 0), (0, -1), (0, 1),
            (-1, -1), (-1, 1), (1, -1), (1, 1)
        ]

        def heuristic(x1, y1, x2, y2):
            dx = abs(x1 - x2)
            dy = abs(y1 - y2)
            return (dx + dy) + (np.sqrt(2) - 2) * min(dx, dy)

        def is_near_obstacle(x, y, map_img, safe_distance=0):
            """检查坐标是否靠近障碍物"""
            for dx in range(-safe_distance, safe_distance + 1):
                for dy in range(-safe_distance, safe_distance + 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        if np.all(map_img[ny, nx] == [0, 0, 0]):  # 黑色 = 障碍
                            return True
            return False

        def is_reachable(x, y, map_img):
            """检查坐标是否可达（不是障碍物且不靠近障碍物）"""
            if not (0 <= x < w and 0 <= y < h):
                return False
            if np.all(map_img[y, x] == [0, 0, 0]):  # 黑色 = 障碍
                return False
            # 检查是否靠近障碍物
            if is_near_obstacle(x, y, map_img):
                return False
            return True

        open_list = []
        closed_set = set()
        came_from = {}

        start_node = (heuristic(start_x, start_y, end_x, end_y), 0, (start_x, start_y), None)
        heapq.heappush(open_list, start_node)

        while open_list:
            f, g, (x, y), parent = heapq.heappop(open_list)
            if (x, y) in closed_set:
                continue

            closed_set.add((x, y))
            came_from[(x, y)] = parent

            # 修改1: 增加终点容差，距离1个像素内就算到达
            if abs(x - end_x) <= enb_deviation and abs(y - end_y) <= enb_deviation:
                path = []
                current = (x, y)
                while current is not None:
                    path.append(current)
                    current = came_from.get(current)
                path.reverse()
                return path

            for dx, dy in directions:
                nx, ny = x + dx, y + dy

                # 修改2: 使用新的可达性检查，避免贴边和贴障碍物
                if not is_reachable(nx, ny, map_img):
                    continue

                if (nx, ny) in closed_set:
                    continue

                # 对角移动成本更高，鼓励走直线
                cost = np.sqrt(2) if dx != 0 and dy != 0 else 1

                # 额外惩罚：如果靠近障碍物但还在可达范围内，增加成本
                penalty = 0
                if is_near_obstacle(nx, ny, map_img, safe_distance=distance):
                    penalty = 0.5  # 轻微惩罚靠近障碍物的路径

                new_g = g + cost + penalty
                new_f = new_g + heuristic(nx, ny, end_x, end_y)
                heapq.heappush(open_list, (new_f, new_g, (nx, ny), (x, y)))

        return []

    def 识别怪物坐标(self,x1,y1,x2,y2):
        """
        找图找到范围内所有怪物的屏幕坐标,转换成游戏坐标
        """
        人物坐标x, 人物坐标y = 识别人物当前坐标()
        返回_找图AIEx = self.大漠对象.AiFindPicEx(x1,y1,x2,y2, fr"./{怪物图片路径}", 0.85, 0)
        if 返回_找图AIEx != '':
            返回_找图AIEx_list = 返回_找图AIEx.split('|')
            怪物坐标列表 = []
            for i in 返回_找图AIEx_list:
                i_list = i.split(',')
                # 以血量为标准做怪物名字图,找到的坐标x+14,y+34偏移后,就是怪物的中心位置
                怪物屏幕x = int(i_list[1]) + 14
                怪物屏幕y = int(i_list[2]) + 34
                游戏坐标x, 游戏坐标y = 游戏坐标方位.屏幕坐标转游戏坐标(人物坐标x, 人物坐标y, 怪物屏幕x, 怪物屏幕y)
                怪物坐标 = (游戏坐标x, 游戏坐标y)
                怪物坐标列表.append(怪物坐标)
            return 怪物坐标列表
        else:
            return []

    # ==============================
    # 实时主循环
    # ==============================
    def 打怪(self):
        try:
            map_img = cv2.imread("chuanqi2.bmp")

            if map_img is None:
                print("未找到 chuanqi2.bmp")
                return

            while True:
                frame = map_img.copy()
                人物x, 人物y = 识别人物当前坐标()
                怪物列表 = self.识别怪物坐标(5, 28, 1916, 823)
                # 画人物位置（蓝点）
                # cv2.circle(frame, (人物x, 人物y), 1, (255, 0, 0), -1)

                if 怪物列表:
                    print('怪物列表',怪物列表)
                    # 绘制怪物点（红色）
                    # for (mx, my) in 怪物列表:
                    #     cv2.circle(frame, (mx, my), 1, (0, 0, 255), -1)

                    # 寻找最近怪物
                    怪物距离 = [np.hypot(mx - 人物x, my - 人物y) for (mx, my) in 怪物列表]
                    最近怪物 = 怪物列表[np.argmin(怪物距离)]
                    最近x, 最近y = 最近怪物

                    # A星寻路
                    path = self.八方a星寻路(人物x, 人物y, 最近x, 最近y, map_img,0,0)
                    print('寻路路径',path)
                    # 画出路径
                    # for (px, py) in path:
                    #     if 0 <= px < frame.shape[1] and 0 <= py < frame.shape[0]:
                    #         frame[py, px] = [0, 255, 0]  # 绿色路径

                    # 跑向怪物
                    length = len(path)
                    for i in range(length):
                        人物x, 人物y = 识别人物当前坐标()
                        if abs(人物x-path[length-1][0])<3 and abs(人物y-path[length-1][1])<3:
                            print("到达最终目的地")
                            break
                        if abs(人物x - path[i][0]) < 2 and abs(人物y - path[i][1]) < 2:
                            print('到达路径点')
                        while abs(人物x - path[i][0]) >= 2 or abs(人物y - path[i][1]) >= 2:
                            print('寻路中')
                            目标方位 = 游戏坐标方位.判断方位(path[i][0],path[i][1],人物x,人物y)
                            提交输入任务(
                                游戏坐标方位.右键点击方位_跑步,
                                目标方位,
                                name="寻路-跑步",
                            )
                            人物x, 人物y = 识别人物当前坐标()
                    # F3隐身,让怪物不要攻击自己
                    提交输入任务(my_con.键盘点击, 60, name="F3隐身")
                    随机延时(1400, 1600)
                    提交输入任务(my_con.键盘点击, 65, name="F8召唤")
                    # F8召唤宝宝技能释放时间大概1200 - 1300
                    self.fighting()

                # 显示
                # cv2.imshow("show", frame)
                #
                # key = cv2.waitKey(1)
                # if key == ord('q'):
                #     break

            # cv2.destroyAllWindows()
        except Exception as e:
            print(e)
    # 判断是否在战斗中
    def fighting(self):
        查找宝宝计次 = 0
        宝宝打怪计次 = 0
        for i in range(5000):
            宝宝列表 = list()
            宝宝 = list()
            宝宝攻击范围 = [None, None, None, None]  # 0,1是左上角坐标.2,3是右下角坐标

            返回_找图AIEx = self.大漠对象.AiFindPicEx(627, 106, 1300, 712, r"./pic/guaiwu/宝宝.bmp", 0.6, 0)
            if 返回_找图AIEx != "":
                查找宝宝计次 = 0
                返回_列表 = 返回_找图AIEx.split('|')
                if len(返回_列表) > 1:
                    for i in 返回_列表:
                        分隔结果 = i.split(',')
                        分隔结果 = [int(j) for j in 分隔结果]
                        宝宝列表.append(分隔结果)  # 有多个宝宝时,二维列表存储坐标位置
                else:
                    分隔结果 = 返回_列表[0].split(',')
                    宝宝 = [int(i) for i in 分隔结果]  # 只有一个宝宝时,存储坐标位置
            else:
                查找宝宝计次 += 1
                print('宝宝未找到计次', 查找宝宝计次)
                if 查找宝宝计次 > 10:
                    break
            # 判断是否是空列表
            if 宝宝列表:
                pass
            if 宝宝:
                # 0,1是左上角坐标.2,3是右下角坐标
                宝宝攻击范围 = [宝宝[1] - 70, 宝宝[2] - 39, 宝宝[1] + 121, 宝宝[2] + 58]

                返回_找图AIEx = self.大漠对象.AiFindPicEx(宝宝攻击范围[0], 宝宝攻击范围[1], 宝宝攻击范围[2],
                                                   宝宝攻击范围[3], fr"./{怪物图片路径}", 0.85, 0)
                if 返回_找图AIEx != '':
                    宝宝打怪计次 = 0
                    print("正在打怪中")
                    print(返回_找图AIEx)
                else:
                    宝宝打怪计次 += 1
                    print('怪物死亡计次', 宝宝打怪计次)
                    if 宝宝打怪计次 > 10:
                        print("怪物已死亡")
                        break
            随机延时(200, 300)

    def 押镖(self):
        try:
            for i in range(30):
                # 走到可以接镖车的位置
                while True:
                    识别结果 = self.大漠对象.Ocr(48, 1057, 108, 1078, "#255-50|#253-50", 1)
                    if 识别结果 != '':
                        分割结果 = 识别结果.split(':')
                        人物x = int(分割结果[0])
                        人物y = int(分割结果[1])
                        目标方位 = 游戏坐标方位.判断方位(352, 348, 人物x, 人物y)
                        if abs(352 - 人物x) == 1 or abs(348 - 人物y) == 1:
                            提交输入任务(
                                游戏坐标方位.左键点击方位_走路,
                                目标方位,
                                100,
                                300,
                                name="押镖-接镖走路",
                            )
                        else:
                            提交输入任务(
                                游戏坐标方位.右键点击方位_跑步,
                                目标方位,
                                100,
                                300,
                                name="押镖-接镖跑步",
                            )
                        if abs(352 - 人物x)<=2 and abs(348 - 人物y)<=2:
                            self.caozuo.emit("到达接镖位置")
                            break
                    else:
                        self.caozuo.emit("未识别到人物坐标")
                    随机延时(200, 400)
                # 点击NPC接镖
                for i in range(30):
                    z, x, y = self.大漠对象.AiFindPic(5, 28, 1916, 823, r"./pic/镖局.bmp", 0.8, 0)
                    if z != -1:
                        提交输入任务(
                            my_con.move_with_left_click,
                            x + 25,
                            y - 34,
                            -1,
                            1,
                            0,
                            10,
                            name="点击镖师",
                        )
                        随机延时(200, 500)
                    z, x, y = self.大漠对象.AiFindPic(8, 9, 390, 164, r"./pic/开始押镖.bmp", 0.8, 0)
                    if z != -1 :
                        提交输入任务(
                            my_con.move_with_left_click,
                            x,
                            y,
                            0,
                            20,
                            0,
                            8,
                            name="开始押镖",
                        )
                        随机延时(200, 500)
                    z, x, y = self.大漠对象.AiFindPic(8, 9, 390, 164, r"./pic/接受护送.bmp", 0.8, 0)
                    if z != -1 :
                        提交输入任务(
                            my_con.move_with_left_click,
                            x,
                            y,
                            0,
                            20,
                            0,
                            7,
                            name="接受护送",
                        )
                        随机延时(200, 500)
                    z, x, y = self.大漠对象.AiFindPic(700, 428, 1223, 657, r"./pic/镖车确定.bmp", 0.8,0)
                    if z != -1:
                        提交输入任务(
                            my_con.move_with_left_click,
                            x,
                            y,
                            0,
                            30,
                            0,
                            10,
                            name="确认镖车",
                        )
                        随机延时(200, 500)
                        # 有时候找图找的坐标不准确,没有"镖车确定"的图片,就是接到镖车了
                        z, x, y = self.大漠对象.AiFindPic(700, 428, 1223, 657, r"./pic/镖车确定.bmp", 0.8, 0)
                        if z == -1:
                            self.caozuo.emit("接到镖车")
                            break
                        continue
                    随机延时(50, 100)
                # 接到镖车走到交镖车位置
                while True:
                    识别结果 = self.大漠对象.Ocr(48, 1057, 108, 1078, "#255-50|#253-50", 1)
                    if 识别结果 != '':
                        分割结果 = 识别结果.split(':')
                        人物x = int(分割结果[0])
                        人物y = int(分割结果[1])
                        目标方位 = 游戏坐标方位.判断方位(382, 341, 人物x, 人物y)
                        if abs(382 - 人物x) == 1 or abs(341 - 人物y) == 1:
                            提交输入任务(
                                游戏坐标方位.左键点击方位_走路,
                                目标方位,
                                100,
                                300,
                                name="押镖-交镖走路",
                            )
                        else:
                            提交输入任务(
                                游戏坐标方位.右键点击方位_跑步,
                                目标方位,
                                100,
                                300,
                                name="押镖-交镖跑步",
                            )
                        # 镖车走的慢,要等镖车
                        随机延时(2000, 2500)
                        self.caozuo.emit(f"{人物x},{人物y}")
                        if abs(382 - 人物x)<=2 and abs(341 - 人物y)<=2:
                            self.caozuo.emit("到达交镖车位置")
                            break
                    随机延时(200, 400)
                # 点击NPC交镖车
                for i in range(30):
                    z, x, y = self.大漠对象.AiFindPic(11, 55, 1915, 718, r"./pic/镖局总管.bmp", 0.8,0)
                    if z != -1:
                        提交输入任务(
                            my_con.move_with_left_click,
                            x,
                            y,
                            0,
                            23,
                            0,
                            10,
                            name="交镖-点击总管",
                        )
                        随机延时(200, 500)
                    z, x, y = self.大漠对象.AiFindPic(11, 20, 389, 161, r"./pic/完成任务.bmp", 0.8, 0)
                    if z != -1:
                        提交输入任务(
                            my_con.move_with_left_click,
                            x,
                            y,
                            0,
                            15,
                            0,
                            8,
                            name="交镖-完成任务",
                        )
                        随机延时(1000, 1500)
                        # 没找到完成任务,就是已经交任务了
                        z, x, y = self.大漠对象.AiFindPic(11, 20, 389, 161, r"./pic/完成任务.bmp", 0.8, 0)
                        if z == -1:
                            self.caozuo.emit("镖车交接完成")
                            # 按1键回城（示例，使用高优先级抢占输入）
                            # 提交输入任务(my_con.键盘点击, 30, priority=10, name="回城", block=False)
                            break
                        continue
                    随机延时(50, 100)
                随机延时(50, 100)
        except Exception as e:
            print(str(e))

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 直接加载.ui文件（无需提前转换成.py）
        uic.loadUi('./gui/longteng.ui', self)  # 参数1: .ui文件路径，参数2: 要附加到的窗口
        self.pushButton_kaishi.clicked.connect(self.kaishi)
        self.pushButton_yidong.clicked.connect(self.yidong)
        self.pushButton_ceshi.clicked.connect(self.ceshi)
        self.pushButton_zhaowupin.clicked.connect(self.zhaowupin)
        self.pushButton_bangding.clicked.connect(self.bangding)
        self.pushButton_jiebang.clicked.connect(self.jiebang)
        self.pushButton_ceshi2.clicked.connect(self.ceshi2)
        self.句柄_列表 = []
        self.A组线程对象列表 = []
        self.B组线程对象列表 = []
        大漠初始化("lumiku2fdc744d96597f65888674a63fb3489a",'yk1226497128')
        dms[0].SetDict(0, r"./字库/数字.txt")
        # 返回_句柄 = dms[0].EnumWindowByProcess("画面采集1920.exe","","HALCON",2+16)
        返回_句柄 = dms[0].EnumWindowByProcess("557ltss20251027.exe","开放","",1+16)
        if 返回_句柄 != '':
            self.句柄_列表 = 返回_句柄.split(',')
            self.句柄_列表 = [int(i) for i in self.句柄_列表]
            for A大漠对象,B大漠对象,句柄 in zip(dms,血量监控,self.句柄_列表):
                窗口标题 = A大漠对象.GetWindowTitle(句柄)
                返回_绑定 = A大漠对象.BindWindowEx(句柄, "gdi", "windows", "windows", "", 0)
                if 返回_绑定 == 1:
                    self.plainTextEdit.appendPlainText(f"A大漠对象|{窗口标题}|绑定成功")
                    随机延时(100,300)
                    A大漠对象.MoveWindow(句柄, -3, -26)
                    self.A组线程对象列表.append(None)
                else:
                    self.plainTextEdit.appendPlainText(f"A大漠对象{窗口标题}|绑定失败")
                返回_绑定 = B大漠对象.BindWindowEx(句柄, "gdi", "windows", "windows", "", 0)
                if 返回_绑定 == 1:
                    self.plainTextEdit.appendPlainText(f"B大漠对象|{窗口标题}|绑定成功")
                    self.B组线程对象列表.append(None)
                else:
                    self.plainTextEdit.appendPlainText(f"B大漠对象{窗口标题}|绑定失败")
        else:
            self.plainTextEdit.appendPlainText('未找到窗口句柄')

        # 鼠标按下和释放事件
        self.pushButton = self.findChild(QPushButton, "self.pushButton_qujubing")

        if self.pushButton_qujubing:  # 如果成功找到按钮对象
            # 给按钮安装事件过滤器（让窗口可以监听按钮的事件）
            self.pushButton_qujubing.installEventFilter(self)
        else:
            print("未找到按钮对象，请检查objectName")  # 调试提示

    def eventFilter(self, obj, event):
        """
        事件过滤器函数（监听所有安装过过滤器的对象）
        参数:
            obj: 触发事件的对象（这里是按钮）
            event: 事件对象（包含事件类型、坐标等信息）
        返回:
            bool: 是否继续传递事件（必须调用父类方法保持默认事件链）
        """
        # ---- 鼠标按下事件处理 ----
        if (obj == self.pushButton_qujubing and  # 确保是目标按钮
                event.type() == QEvent.MouseButtonPress):  # 鼠标按下事件

            if event.button() == Qt.LeftButton:  # 检查是否是左键
                # 将按钮局部坐标转换为窗口坐标（mapTo方法）
                window_pos = obj.mapTo(self, event.pos())
                # 打印调试信息（f-string格式化）
                self.lineEdit_jubing.setText('')

        # ---- 鼠标释放事件处理 ----
        elif (obj == self.pushButton_qujubing and  # 确保是目标按钮
              event.type() == QEvent.MouseButtonRelease):  # 鼠标释放事件

            if event.button() == Qt.LeftButton:  # 检查是否是左键
                句柄 = dms[0].GetMousePointWindow()
                self.lineEdit_jubing.setText(str(句柄))
                # 这里可以添加按钮释放后的业务逻辑

        # 必须调用父类方法，保证未处理的事件能继续传递
        return super().eventFilter(obj, event)

    def bangding(self):
        dms[0].UnBindWindow()
        句柄 = int(self.lineEdit_jubing.text())
        窗口标题 = dms[0].GetWindowTitle(句柄)
        返回_绑定 = dms[0].BindWindowEx(句柄, "gdi", "windows", "windows", "", 0)
        if 返回_绑定 == 1:
            self.plainTextEdit.appendPlainText(f"{窗口标题}|绑定成功")

    def jiebang(self):
        dms[0].UnBindWindow()
        self.plainTextEdit.appendPlainText("解除绑定")

    def ceshi2(self):
        pass

    def ceshi(self):
        self.实时寻路()


    def kaishi(self):
        try:
            if self.A组线程对象列表 :
                for 序号,(A大漠对象,B大漠对象,句柄) in enumerate(zip(dms,血量监控,self.句柄_列表)):
                    if self.A组线程对象列表[序号] == None:
                        self.A组线程对象列表[序号] = WorkerThread(A大漠对象,句柄,'打怪')
                        self.A组线程对象列表[序号].caozuo.connect(self.caozuo)
                        self.A组线程对象列表[序号].start()
                        self.B组线程对象列表[序号] = WorkerThread(B大漠对象,句柄,'血量')
                        self.B组线程对象列表[序号].jiankong.connect(self.jiankong)
                        self.B组线程对象列表[序号].start()
            else:
                self.plainTextEdit.appendPlainText("请先绑定游戏后再开启线程")
        except Exception as e:
            print(e)

    def caozuo(self,str):
        self.plainTextEdit.appendPlainText(str)

    def jiankong(self,str):
        self.plainTextEdit_jiankong.appendPlainText(str)

    def zhaowupin(self):
        dms[0].Delay(2000)
        文本 = self.lineEdit_xiangsidu.text()
        if 文本 != '':
            相似度 = float(文本)
        else:
            相似度 = 0.7
        z, x, y = dms[0].AiFindPic(4, 72, 1914, 821, r"./pic/333333.bmp", 相似度, 0)
        if z != -1:
            识别结果 = dms[0].Ocr(48, 1057, 108, 1078, "#255-50|#253-50", 1)
            if 识别结果 != '':
                识别结果 = 识别结果.strip(":")
                分割结果 = 识别结果.split(':')
                人物游戏x = int(分割结果[0])
                人物游戏y = int(分割结果[1])
                物品x, 物品y = 屏幕坐标转游戏坐标方位(人物游戏x, 人物游戏y, x, y, 9)
                print(f'怪物坐标:{物品x}|{物品y}')

    def yidong(self):
        文本 = self.lineEdit.text()
        if ',' in 文本 and 文本 != '':
            分割结果 = 文本.split(',')
            x = int(分割结果[0])
            y = int(分割结果[1])
            dms[0].MoveWindow(self.句柄_列表[0], x, y)
        else:
            self.plainTextEdit.appendPlainText("请输入正确的数值,如 : 0,-25")

    def closeEvent(self, event):
        # pyqt_ui窗口关闭时触发的事件
        dms[0].UnBindWindow()
        del dms[0]
        event.accept()  # 允许关闭
        print("关闭")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec_())