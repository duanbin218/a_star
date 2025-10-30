import kmNet
import random
import win32api
import time
import keyboard
import threading
import os
import ctypes
import math
import itertools
import queue
from dataclasses import dataclass, field
from typing import Callable, Optional, Tuple, Any


kmNet.init("192.168.2.188","1538","86C2E466")


# 全局退出标志
exit_flag = False

# 定义必要的Windows API,监听键盘按键
user32 = ctypes.WinDLL('user32', use_last_error=True)

# 键盘监听函数方式二 : 在游戏窗口能监听键盘,使用更底层的输入监控,需要导入ctypes库
def keyboard_listener():
    global exit_flag
    while not exit_flag:
        # 直接检查F3物理键状态（不依赖窗口消息）
        if user32.GetAsyncKeyState(0x2C) & 0x8000:  # 0x2C是Print Screen的虚拟(VK)键码
            exit_flag = True
            print("检测到F12按键，程序将退出")
            return
        time.sleep(0.05)  # 降低CPU使用率

# 键盘监听函数方式一 : 在游戏窗口不能监听键盘,因为游戏有反外挂,会阻止键盘钩子,导致keyboard库无法捕获游戏窗口中的按键事件
# def keyboard_listener():
#     global exit_flag
#     keyboard.wait('f3')  # 阻塞等待F3键按下
#     exit_flag = True
#     print("检测到F3按键，程序将退出")

# 启动键盘监听线程（守护线程）
threading.Thread(target=keyboard_listener, daemon=True).start()

def 延时(毫秒):
    """高精度延时函数，每100ms检查一次退出标志"""
    global exit_flag
    start = time.perf_counter()
    target_ms = 毫秒  # 目标毫秒数

    while True:
        if exit_flag:
            # 退出前把鼠标左右键释放,防止左右键处于按下状态退出
            kmNet.enc_right(0)
            kmNet.enc_left(0)
            os._exit(0)  # 强制退出整个程序

        elapsed_ms = (time.perf_counter() - start) * 1000
        if elapsed_ms >= target_ms:
            break

        remaining_ms = target_ms - elapsed_ms
        sleep_time = min(0.1, remaining_ms / 1000)
        time.sleep(sleep_time)


@dataclass(order=True)
class _InputTask:
    """内部任务模型：PriorityQueue 会使用 (优先级, 序号, 任务)."""

    priority: int
    sequence: int
    action: Callable = field(compare=False)
    args: Tuple[Any, ...] = field(default_factory=tuple, compare=False)
    kwargs: dict = field(default_factory=dict, compare=False)
    name: str = field(default="", compare=False)
    done: threading.Event = field(default_factory=threading.Event, compare=False)
    error: Optional[BaseException] = field(default=None, compare=False)


class InputBroker:
    """串行化 my_con 调用的单工人线程调度器（方案B）。

    - 采用 PriorityQueue 实现：数值越小优先级越高，紧急任务先执行。
    - worker 线程唯一持有 my_con 的控制权，避免多线程抢占导致死锁、按键卡死。
    - submit() 默认阻塞直到任务完成，可传 block=False 变为异步。

    风险与对策：
        * 如果任务内部包含长时间循环，应拆分为更小的任务，或提交时使用 block=False
          让调用线程自行等待/轮询，从而避免阻塞 worker。
        * 若优先级设置错误导致紧急任务被排队，可通过更小的 priority 值提交，例如 0 表示立即抢占。
    """

    def __init__(self, controller: "MyController", name: str = "InputWorker"):
        self._controller = controller
        self._name = name
        self._queue: "queue.PriorityQueue[_InputTask]" = queue.PriorityQueue()
        self._sequence = itertools.count()
        self._stop_event = threading.Event()
        self._worker = threading.Thread(target=self._run, name=name, daemon=True)
        self._worker.start()

    @property
    def controller(self) -> "MyController":
        """暴露底层控制器实例，仅供调试或组合使用。"""

        return self._controller

    def submit(
        self,
        action: Callable,
        *args,
        priority: int = 100,
        name: str = "",
        block: bool = True,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> _InputTask:
        """提交一个键鼠任务。

        Args:
            action: 实际执行的回调函数，通常为 my_con 的方法。
            *args/**kwargs: 传递给回调的参数。
            priority: 数字越小优先级越高，例如 0 为抢占级。
            name: 任务调试名称。
            block: True 时等待任务执行完成，保持旧逻辑的一致性。
            timeout: 等待完成的超时时间（秒）。

        Returns:
            _InputTask: 任务对象，可用于等待或检查错误。
        """

        if self._stop_event.is_set():
            raise RuntimeError("InputBroker 已停止，不能再提交任务")

        task = _InputTask(
            priority=priority,
            sequence=next(self._sequence),
            action=action,
            args=args,
            kwargs=kwargs,
            name=name,
        )
        self._queue.put(task)

        if block:
            finished = task.done.wait(timeout)
            if not finished:
                raise TimeoutError(f"等待任务 {task.name or action.__name__} 超时")
            if task.error:
                raise task.error

        return task

    def stop(self) -> None:
        """停止 worker 线程，通常在程序退出时调用。"""

        self._stop_event.set()
        # Sentinel：priority=100000 确保排队尾部，但不影响已有任务执行。
        self._queue.put(
            _InputTask(
                priority=100000,
                sequence=next(self._sequence),
                action=lambda: None,
                name="broker-stop",
            )
        )
        self._worker.join(timeout=1)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                task: _InputTask = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                task.action(*task.args, **task.kwargs)
            except BaseException as exc:  # noqa: BLE001 - 记录并传播所有异常
                task.error = exc
                print(f"[InputBroker] 任务 {task.name or task.action.__name__} 执行失败: {exc}")
            finally:
                task.done.set()


# 方案A：最小改动的互斥锁封装，供极端情况下退回旧逻辑
my_con_lock = threading.RLock()
cooperative_preempt = threading.Event()


def safe_keypress(controller: "MyController", hid_value: int, 延时a: int = 70, 延时b: int = 200) -> None:
    """方案A：带协作抢占检查的安全按键调用。

    - 当 cooperative_preempt 被 set() 时，调用方应提前释放锁并重试，避免长时间持锁。
    - 推荐仅在 InputBroker 不可用时使用。
    """

    while True:
        acquired = my_con_lock.acquire(timeout=0.2)
        if not acquired:
            # 锁被长时间占用，主动检查是否有抢占请求
            if cooperative_preempt.is_set():
                time.sleep(0.05)
            continue

        try:
            if cooperative_preempt.is_set():
                # 有抢占请求时释放控制权，让高优先级逻辑先执行
                time.sleep(0.01)
                continue
            controller.键盘点击(hid_value, 延时a, 延时b)
            break
        finally:
            my_con_lock.release()

class 游戏坐标系统():
    def __init__(self,MouseController=None):
        self.八方位点击坐标 = self.八方位点击坐标计算(966, 463, 170)
        self.mouse = MouseController if MouseController else MouseController()

    @staticmethod
    def 八方位点击坐标计算(圆心x, 圆心y, 半径r):
        八方位点击坐标 = []
        for i in range(8):
            # 0 * 45度是正东,1 * 45度是东北,逆时针增加角度,依次类推
            角度 = i * 45
            弧度 = math.radians(角度)
            x = 圆心x + 半径r * math.cos(弧度)
            y = 圆心y - 半径r * math.sin(弧度)
            八方位点击坐标.append((int(x), int(y)))
        return 八方位点击坐标

    @staticmethod
    def 判断方位(目的地x, 目的地y, 中心点x, 中心点y):
        """
        求目的地坐标位于中心点坐标的什么方位
        :param 目的地x:输入你要寻往的目的地x坐标
        :param 目的地y:输入你要寻往的目的地y坐标
        :param 中心点x:输入你现在人物的x坐标
        :param 中心点y:输入你现在人物的y坐标
        :return:返回目的地坐标位于中心点坐标的8个方位
        """
        if 目的地x > 中心点x and 目的地y == 中心点y:
            return '正东'
        elif 目的地x > 中心点x and 目的地y < 中心点y:
            return '东北'
        elif 目的地x == 中心点x and 目的地y < 中心点y:
            return '正北'
        elif 目的地x < 中心点x and 目的地y < 中心点y:
            return '西北'
        elif 目的地x < 中心点x and 目的地y == 中心点y:
            return '正西'
        elif 目的地x < 中心点x and 目的地y > 中心点y:
            return '西南'
        elif 目的地x == 中心点x and 目的地y > 中心点y:
            return '正南'
        elif 目的地x > 中心点x and 目的地y > 中心点y:
            return '东南'

    def 方位取反(self,目的地x, 目的地y, 中心点x, 中心点y):
        目标方位 = self.判断方位(目的地x, 目的地y, 中心点x, 中心点y)
        if 目标方位 == '正东':
            return '正西'
        elif 目标方位 == '东北':
            return '西南'
        elif 目标方位 == '正北':
            return '正南'
        elif 目标方位 == '西北':
            return '东南'
        elif 目标方位 == '正西':
            return '正东'
        elif 目标方位 == '西南':
            return '东北'
        elif 目标方位 == '正南':
            return '正北'
        elif 目标方位 == '东南':
            return '西北'

    @staticmethod
    def 屏幕坐标转游戏坐标(人物游戏x, 人物游戏y, 目标屏幕x, 目标屏幕y, 偏移量y=0):
        # 所有怪物和人物名字的图片宽度以血条的宽度为标准,找怪物以950,430为标准计算偏移量,964,464是人物中心坐标
        # 物品名字和人名名字不是一样高,要向y轴增加9个屏幕坐标,找物品就要以950,439为标准计算偏移量
        屏幕坐标x偏移量 = 964 - 目标屏幕x
        屏幕坐标y偏移量 = 464 + 偏移量y - 目标屏幕y
        # 屏幕坐标x到游戏坐标x的比例系数48,y的比例系数32,屏幕坐标移动48,游戏坐标变动1
        游戏坐标x偏移量 = 屏幕坐标x偏移量 / 48
        游戏坐标y偏移量 = 屏幕坐标y偏移量 / 32
        # print("屏幕坐标转游戏坐标转换系数:", 游戏坐标x偏移量)
        整数x偏移量 = 游戏坐标系统.round_away_from_zero(游戏坐标x偏移量)
        整数y偏移量 = 游戏坐标系统.round_away_from_zero(游戏坐标y偏移量)
        游戏坐标x = int(人物游戏x) - int(整数x偏移量)
        游戏坐标y = int(人物游戏y) - int(整数y偏移量)
        return 游戏坐标x, 游戏坐标y

    @staticmethod
    def round_away_from_zero(x):
        # "向远离零的方向取整"（即正数向上取整，负数向下取整）10.31取整变成11 , -1.91取整变成-2
        if x >= 0:
            return math.ceil(x)
        else:
            return math.floor(x)

    def 移动方位不点击(self, 目标方位):
        随机数_90度_min = random.randint(-4,4)
        随机数_90度_max = random.randint(-100,100)
        随机数_45度 = random.randint(-36,36)
        if 目标方位 == "正东":
            self.mouse.simple_move_without_click(self.八方位点击坐标[0][0]+随机数_90度_max, self.八方位点击坐标[0][1]+随机数_90度_min)
        elif 目标方位 == "东北":
            self.mouse.simple_move_without_click(self.八方位点击坐标[1][0]+随机数_45度, self.八方位点击坐标[1][1]+随机数_45度)
        elif 目标方位 == "正北":
            self.mouse.simple_move_without_click(self.八方位点击坐标[2][0]+随机数_90度_min, self.八方位点击坐标[2][1]+随机数_90度_max)
        elif 目标方位 == "西北":
            self.mouse.simple_move_without_click(self.八方位点击坐标[3][0]+随机数_45度, self.八方位点击坐标[3][1]+随机数_45度)
        elif 目标方位 == "正西":
            self.mouse.simple_move_without_click(self.八方位点击坐标[4][0]+随机数_90度_max, self.八方位点击坐标[4][1]+随机数_90度_min)
        elif 目标方位 == "西南":
            self.mouse.simple_move_without_click(self.八方位点击坐标[5][0]+随机数_45度, self.八方位点击坐标[5][1]+随机数_45度)
        elif 目标方位 == "正南":
            self.mouse.simple_move_without_click(self.八方位点击坐标[6][0]+随机数_90度_min, self.八方位点击坐标[6][1]+随机数_90度_max)
        elif 目标方位 == "东南":
            self.mouse.simple_move_without_click(self.八方位点击坐标[7][0]+随机数_45度, self.八方位点击坐标[7][1]+随机数_45度)

    def 左键点击方位_走路(self, 目标方位,延时a=100, 延时b=200):
        随机数_90度_min = random.randint(-4, 4)
        随机数_90度_max = random.randint(-100, 100)
        随机数_45度 = random.randint(-36, 36)
        if 目标方位 == "正东":
            self.mouse.simple_move_with_left_click(self.八方位点击坐标[0][0] + 随机数_90度_max,
                                        self.八方位点击坐标[0][1] + 随机数_90度_min, 延时a, 延时b)
        elif 目标方位 == "东北":
            self.mouse.simple_move_with_left_click(self.八方位点击坐标[1][0] + 随机数_45度,
                                        self.八方位点击坐标[1][1] + 随机数_45度, 延时a, 延时b)
        elif 目标方位 == "正北":
            self.mouse.simple_move_with_left_click(self.八方位点击坐标[2][0] + 随机数_90度_min,
                                        self.八方位点击坐标[2][1] + 随机数_90度_max, 延时a, 延时b)
        elif 目标方位 == "西北":
            self.mouse.simple_move_with_left_click(self.八方位点击坐标[3][0] + 随机数_45度,
                                        self.八方位点击坐标[3][1] + 随机数_45度, 延时a, 延时b)
        elif 目标方位 == "正西":
            self.mouse.simple_move_with_left_click(self.八方位点击坐标[4][0] + 随机数_90度_max,
                                        self.八方位点击坐标[4][1] + 随机数_90度_min, 延时a, 延时b)
        elif 目标方位 == "西南":
            self.mouse.simple_move_with_left_click(self.八方位点击坐标[5][0] + 随机数_45度,
                                        self.八方位点击坐标[5][1] + 随机数_45度, 延时a, 延时b)
        elif 目标方位 == "正南":
            self.mouse.simple_move_with_left_click(self.八方位点击坐标[6][0] + 随机数_90度_min,
                                        self.八方位点击坐标[6][1] + 随机数_90度_max, 延时a, 延时b)
        elif 目标方位 == "东南":
            self.mouse.simple_move_with_left_click(self.八方位点击坐标[7][0] + 随机数_45度,
                                        self.八方位点击坐标[7][1] + 随机数_45度, 延时a, 延时b)

    def 右键点击方位_跑步(self, 目标方位, 延时a=100, 延时b=200):
        随机数_90度_min = random.randint(-1, 1)
        随机数_90度_max = random.randint(-50, 50)
        随机数_45度 = random.randint(-50, 50)
        if 目标方位 == "正东":
            self.mouse.simple_move_with_right_click(self.八方位点击坐标[0][0] + 随机数_90度_max,
                                        self.八方位点击坐标[0][1] + 随机数_90度_min, 延时a, 延时b)
        elif 目标方位 == "东北":
            self.mouse.simple_move_with_right_click(self.八方位点击坐标[1][0] + 随机数_45度,
                                        self.八方位点击坐标[1][1] + 随机数_45度, 延时a, 延时b)
        elif 目标方位 == "正北":
            self.mouse.simple_move_with_right_click(self.八方位点击坐标[2][0] + 随机数_90度_min,
                                        self.八方位点击坐标[2][1] + 随机数_90度_max, 延时a, 延时b)
        elif 目标方位 == "西北":
            self.mouse.simple_move_with_right_click(self.八方位点击坐标[3][0] + 随机数_45度,
                                        self.八方位点击坐标[3][1] + 随机数_45度, 延时a, 延时b)
        elif 目标方位 == "正西":
            self.mouse.simple_move_with_right_click(self.八方位点击坐标[4][0] + 随机数_90度_max,
                                        self.八方位点击坐标[4][1] + 随机数_90度_min, 延时a, 延时b)
        elif 目标方位 == "西南":
            self.mouse.simple_move_with_right_click(self.八方位点击坐标[5][0] + 随机数_45度,
                                        self.八方位点击坐标[5][1] + 随机数_45度, 延时a, 延时b)
        elif 目标方位 == "正南":
            self.mouse.simple_move_with_right_click(self.八方位点击坐标[6][0] + 随机数_90度_min,
                                        self.八方位点击坐标[6][1] + 随机数_90度_max, 延时a, 延时b)
        elif 目标方位 == "东南":
            self.mouse.simple_move_with_right_click(self.八方位点击坐标[7][0] + 随机数_45度,
                                        self.八方位点击坐标[7][1] + 随机数_45度, 延时a, 延时b)


class MyController():
    def __init__(self,kmNet=kmNet):
        self.kmNet = kmNet

    def move_without_click(self,目标x, 目标y, 最小x偏移=0, 最大x偏移=0, 最小y偏移=0, 最大y偏移=0,延时a=100,延时b=200):
        """
        从当前位置相对移动到目标坐标，带有随机偏移和延时，然后左键单击

        参数:
            目标x, 目标y: 目标坐标
            延时a, 延时b: 移动延时的随机范围(毫秒)
            最小x偏移, 最大x偏移: x轴随机偏移范围
            最小y偏移, 最大y偏移: y轴随机偏移范围
        """
        # 获取当前鼠标位置
        当前x, 当前y = win32api.GetCursorPos()
        print(f"\n起始位置: x={当前x}, y={当前y}")

        # 计算相对移动距离
        x移动 = 目标x - 当前x
        y移动 = 目标y - 当前y

        # 添加随机偏移
        x随机偏移 = random.randint(最小x偏移, 最大x偏移)
        y随机偏移 = random.randint(最小y偏移, 最大y偏移)
        总x移动 = x移动 + x随机偏移
        总y移动 = y移动 + y随机偏移

        # 执行移动
        self.kmNet.enc_move_auto(int(总x移动), int(总y移动), 2000)

        for i in range(5):
            当前x, 当前y = win32api.GetCursorPos()
            x移动 = 目标x - 当前x
            y移动 = 目标y - 当前y
            if abs(x移动) < 2 and abs(y移动) < 2:
                print("位置正确")
                break
            x随机偏移 = random.randint(最小x偏移, 最大x偏移)
            y随机偏移 = random.randint(最小y偏移, 最大y偏移)
            总x移动 = x移动 + x随机偏移
            总y移动 = y移动 + y随机偏移
            # enc_move_auto的参数3延时时间,不是按设置的2000需要这么久,实际耗时是达到目的地的时间,所以参数3可以设置多一点
            self.kmNet.enc_move_auto(int(总x移动), int(总y移动), 2000)
            随机延时 = random.randint(10, 50)
            延时(随机延时)

        随机延时 = random.randint(延时a, 延时b)
        延时(随机延时)

        # 当前x, 当前y = win32api.GetCursorPos()
        # print(f"\n结束位置: x={当前x}, y={当前y}")

    def move_with_left_click(self,目标x, 目标y, 最小x偏移=0, 最大x偏移=0, 最小y偏移=0, 最大y偏移=0,延时a=100,延时b=200):
        self.move_without_click(目标x, 目标y, 最小x偏移, 最大x偏移, 最小y偏移, 最大y偏移,延时a,延时b)
        self.left_click()

    def simple_move_without_click(self,目标x, 目标y,延时a=100,延时b=200):
        # 获取当前鼠标位置
        当前x, 当前y = win32api.GetCursorPos()

        # 计算相对移动距离
        x移动 = 目标x - 当前x
        y移动 = 目标y - 当前y

        # 执行移动
        self.kmNet.enc_move_auto(int(x移动), int(y移动), 2000)

        随机延时 = random.randint(延时a, 延时b)
        延时(随机延时)

        # 当前x, 当前y = win32api.GetCursorPos()
        # print(f"\n结束位置: x={当前x}, y={当前y}")

    def left_click(self):
        self.kmNet.enc_left(1)  # 按下左键
        点击按下延时 = random.randint(70, 200)
        延时(点击按下延时)
        self.kmNet.enc_left(0)  # 释放左键

    def right_click(self):
        self.kmNet.enc_right(1) # 按下右键
        点击按下延时 = random.randint(70, 200)
        延时(点击按下延时)
        self.kmNet.enc_right(0)  # 释放右键

    def simple_move_with_left_click(self,目标x, 目标y, 延时a=100,延时b=200):
        self.simple_move_without_click(目标x, 目标y,延时a,延时b)
        self.left_click()

    def simple_move_with_right_click(self,目标x, 目标y, 延时a=100,延时b=200):
        self.simple_move_without_click(目标x, 目标y,延时a,延时b)
        self.right_click()

    def 键盘点击(self,HID值, 延时a=70, 延时b=200):
        self.kmNet.enc_keydown(HID值)
        随机延时 = random.randint(延时a, 延时b)
        延时(随机延时)
        self.kmNet.enc_keyup(HID值)
        随机延时 = random.randint(延时a, 延时b)
        延时(随机延时)


# 测试鼠标每次移动的坐标是不是我们指定的坐标
def test():
    my_mouse = MouseController()
    my_mouse.move_without_click(500, 500)

# 测试鼠标每次移动的相对坐标是不是100,100
def test1():
    kmNet.enc_move_auto(100, 100, 300)
    当前x, 当前y = win32api.GetCursorPos()
    print(f"结束位置: x={当前x}, y={当前y}")

# 按F3执行哪个程序
def on_f3_press(event):
    test1()

if __name__ =="__main__":

    keyboard.on_press_key('F3', on_f3_press)
    print("\n按下 F3 测试（按 ESC 退出）...")
    keyboard.wait('esc')
