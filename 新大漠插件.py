# -*- coding: utf-8 -*-
import ctypes
import win32com.client
import os
import win32api
import base64

import cv2
import numpy as np
from typing import List, Tuple, Optional

import math#求最近坐标 自己封装

import requests
import base64
import json
import time

import random
#全局大漠cmd

dms = []
血量监控 = []

def 调试输出(内容):
    print(内容)

def 弹窗提醒(内容):
    win32api.MessageBox(0, 内容, "提示", 0x40)

def 检测文件是否存在():
    """检测当前目录下是否存在三个关键文件"""
    target_files = ["DmReg.dll", "康晓.dll", "ai.module"]
    missing_files = []

    for filename in target_files:
        if not os.path.isfile(filename):
            missing_files.append(filename)

    if missing_files:
        for file in missing_files:
            弹窗提醒(f"根目录必须提供此文件： - {file}")
            return
    else:
        pass


def 大漠初始化(注册码,附加码,多开数量 = None):
    global dms
    global 血量监控

    # 要求:根目录下提供:"DmReg.dll"、"康晓.dll"、"ai.module"三个文件，否则失败！

    检测文件是否存在()

    # 核心代码 ----------------

    current_dir = os.path.abspath(os.getcwd())
    dmreg = ctypes.WinDLL(os.path.join(current_dir, "DmReg.dll"))
    dm_path = os.path.normpath(os.path.join(current_dir, "康晓.dll"))
    dmreg.SetDllPathW(ctypes.c_wchar_p(dm_path), 0)

    # 3. 创建初始COM对象
    dm = win32com.client.Dispatch("dm.dmsoft")
    注册结果 = dm.reg(注册码,附加码)

    if 注册结果 == 1:
        调试输出("注册大漠VIP成功")
        # AI模块加载

        ai_模块加载 = dm.LoadAi(r'.\ai.module')
        if ai_模块加载 == 1:
            调试输出('AI模块加载成功!')
            ai_版本号 = dm.AiYoloSetVersion("v5-7.0")
            if ai_版本号 == 1:
                调试输出('AI版本号(v5-7.0), 设置成功!')
            else:
                调试输出('AI版本号设置失败!')

        else:
            弹窗提醒('AI模块加载失败!')

        # 5. 创建实例（仅添加CoInitializeEx调用）

        if 多开数量 is None:

            for i in range(2):

                ctypes.windll.ole32.CoInitializeEx(0, 0)  # 严格等效易语言调用‌:ml-citation{ref="2" data="citationList"}
                instance = win32com.client.Dispatch("dm.dmsoft")
                if i == 0:
                    dms.append(instance)
                    调试输出(f"共创建1个dms的大漠对象,版本：{instance.Ver()}")
                elif i == 1:
                    # return
                    血量监控.append(instance)
                    调试输出(f"共创建1个血量监控的大漠对象,版本：{instance.Ver()}")

        else:
            for a in range(2):

                for i in range(多开数量):
                    ctypes.windll.ole32.CoInitializeEx(0, 0)  # 严格等效易语言调用‌:ml-citation{ref="2" data="citationList"}
                    instance = win32com.client.Dispatch("dm.dmsoft")
                    if a == 0:
                        dms.append(instance)
                        if i == 多开数量-1:
                            调试输出(f" 共创建了{i+1}个dms的大漠对象，版本：{instance.Ver()}")
                    elif a == 1:
                        # return
                        血量监控.append(instance)
                        if i == 多开数量 - 1:
                            调试输出(f" 共创建了{i+1}个血量监控的大漠对象，版本：{instance.Ver()}")

    else:
        弹窗提醒(f"注册失败，错误码：{注册结果}")
        return


def 计算八个方向坐标(圆心_x, 圆心_y, 半径):
    """
    根据屏幕坐标系计算圆上八个方向的坐标并格式化输出
    :param 圆心_x: 圆心的X坐标（非负数）
    :param 圆心_y: 圆心的Y坐标（非负数）
    :param 半径:   圆的半径（正数）
    :return: 格式化后的方向坐标字符串，例如 "东：656，307\n东南：619，395\n..."
    """
    方向表 = {
        '东': 0,
        '东南': 45,
        '南': 90,
        '西南': 135,
        '西': 180,
        '西北': 225,
        '北': 270,
        '东北': 315
    }

    输出结果 = []

    for 方向, 角度 in 方向表.items():
        弧度 = math.radians(角度)
        x坐标 = 圆心_x + 半径 * math.cos(弧度)
        y坐标 = 圆心_y + 半径 * math.sin(弧度)
        输出结果.append(f"{方向}：{int(round(x坐标))}，{int(round(y坐标))}")

    return "\n".join(输出结果)


def 取图片中心位置(大漠对象, 图片地址, 图片x坐标, 图片y坐标):
    # 取图片中心位置,这个位置结果是求整的结果(会自动无视小数部分)

    图片信息 = 图色_取图片尺寸(大漠对象, 图片地址)
    返回_图片信息 = 图片信息.split(",")

    图片长 = int(返回_图片信息[0]) / 2
    图片宽 = int(返回_图片信息[1]) / 2

    中心点x = int(图片x坐标 + 图片长)
    中心点y = int(图片y坐标 + 图片宽)

    return 中心点x, 中心点y

#命令封装
def 查找最近坐标(坐标列表, 中心坐标):

    最短距离 = float('inf')  # 初始化为无穷大
    最近坐标 = None

    # 遍历所有坐标
    for 当前坐标 in 坐标列表:
        # 计算两点间距（使用勾股定理）
        横向差 = 当前坐标[0] - 中心坐标[0]
        纵向差 = 当前坐标[1] - 中心坐标[1]
        当前距离 = math.hypot(横向差, 纵向差)  # 等效于√(横向差² + 纵向差²)

        # 比较并更新最近坐标
        if 当前距离 < 最短距离:
            最短距离 = 当前距离
            最近坐标 = 当前坐标

    x,y = 最近坐标

    return  x,y

#openvc 封装开始
class OpenCv:
    def __init__(self, method: int = cv2.TM_CCOEFF_NORMED):
        self.method = method

    def _load_imgs(self, big_path: str, small_path: str) -> Tuple[np.ndarray, np.ndarray]:
        """图像加载 (严格校验版本)"""
        big = cv2.imread(big_path, cv2.IMREAD_GRAYSCALE)
        small = cv2.imread(small_path, cv2.IMREAD_GRAYSCALE)

        if big is None or small is None:
            raise ValueError(f"图片加载失败: 大图[{big_path}] 小图[{small_path}]")
        if small.shape > big.shape or small.shape > big.shape:
            raise ValueError(f"小图尺寸{small.shape}超过大图{big.shape}")
        return big, small

    def ocv找图(self, big_path: str, small_path: str, th: float) -> Optional[Tuple[int, int]]:
        """
        严格三参数单目标匹配
        :param th: 相似度阈值 [0-1]
        """
        big, small = self._load_imgs(big_path, small_path)
        res = cv2.matchTemplate(big, small, self.method)
        _, confidence, _, max_loc = cv2.minMaxLoc(res)
        return max_loc if confidence >= th else None

    def ocv找图Ex(self, big_path: str, small_path: str, th: float) -> List[Tuple[int, int]]:
        """
        严格三参数多目标匹配
        :param th: 相似度阈值 [0-1]
        """
        big, small = self._load_imgs(big_path, small_path)
        h, w = small.shape

        res = cv2.matchTemplate(big, small, self.method)
        y_locs, x_locs = np.where(res >= th)
        points = list(zip(x_locs, y_locs))

        if not points:
            return []

        # NMS处理
        scores = res[y_locs, x_locs].flatten().tolist()
        boxes = [[x, y, w, h] for (x, y) in points]
        indices = cv2.dnn.NMSBoxes(boxes, scores, th, 0.3)

        return [points[i] for i in indices.flatten()] if indices.size > 0 else []


#opencv 封装结束
#飞桨识图开始
class FeiJiang:
    """飞桨OCR API封装类"""

    def __init__(self):
        self.api_url = "https://www.paddlepaddle.org.cn/paddlehub-api/image_classification/chinese_ocr_db_crnn_mobile"
        self.headers = {
            "Host": "www.paddlepaddle.org.cn",
            "Connection": "keep-alive",
            "Origin": "https://www.paddlepaddle.org.cn",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.25 Safari/537.36 Core/1.70.3870.400 QQBrowser/10.8.4405.400",
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Referer": "https://www.paddlepaddle.org.cn/hub/scene/ocr",
            "Accept-Language": "zh-CN,zh;q=0.9"
        }

    def 识图上文字(self, image_path, include_position=False):
        """
        识别图片文字
        :param image_path: 图片路径
        :param include_position: 是否返回位置信息
        :return: 纯文本或带位置信息的字典
        """
        start_time = time.time()

        try:
            # 读取并编码图片
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # 发送请求
            response = requests.post(
                self.api_url,
                json={"image": image_data},
                headers=self.headers
            )

            if response.status_code != 200:
                raise Exception(f"API请求失败，状态码: {response.status_code}")

            data = response.json()
            result = self._parse_response(data, include_position)

            print(f"识别耗时: {time.time() - start_time:.2f}秒")
            return result

        except Exception as e:
            print(f"识别出错: {str(e)}")
            return None

    def _parse_response(self, data, include_position):
        """解析API返回数据"""
        if include_position:
            results = []
            for item in data.get("result", [{}])[0].get("data", []):
                results.append({
                    "text": item.get("text", ""),
                    "confidence": item.get("confidence", 0),
                    "position": item.get("text_box_position", [])
                })
            return results
        else:
            return "\n".join([
                item.get("text", "")
                for item in data.get("result", [{}])[0].get("data", [])
            ])


#飞桨识图结束
def 计算转换比例(游戏点1, 地图点1, 游戏点2, 地图点2):
    x比例 = (游戏点2[0] - 游戏点1[0]) / (地图点2[0] - 地图点1[0])
    x偏移量 = 游戏点1[0] - 地图点1[0] * x比例

    # 计算y轴比例和偏移量
    y比例 = (游戏点2[1] - 游戏点1[1]) / (地图点2[1] - 地图点1[1])
    y偏移量 = 游戏点1[1] - 地图点1[1] * y比例

    return x比例, y比例, x偏移量, y偏移量


def 游戏转小地图屏幕坐标(游戏x, 游戏y, 转换参数):
    x比例, y比例, x偏移量, y偏移量 = 转换参数
    地图x = (游戏x - x偏移量) / x比例
    地图y = (游戏y - y偏移量) / y比例
    return int(round(地图x)), int(round(地图y))

def 小地图屏幕转游戏坐标(地图x, 地图y, 转换参数):
    x比例, y比例, x偏移量, y偏移量 = 转换参数
    游戏x = 地图x * x比例 + x偏移量
    游戏y = 地图y * y比例 + y偏移量
    return int(round(游戏x)), int(round(游戏y))


# 游x1,游y1 = 328,378
# 图x1,图y1 = 434,195
#
# 游x2,游y2 = 383,359
# 图x2,图y2 = 461,187


# 转换参数 = 计算转换比例((游x1, 游y1), (图x1, 图y1), (游x2, 游y2), (图x2, 图y2))
#
#     # 测试转换
#
# x,y = 339,338
#
# 测试游戏坐标 = (x, y)
# 地图坐标 = 游戏转地图坐标(*测试游戏坐标, 转换参数)
#
# print(f"游戏坐标{测试游戏坐标} -> 地图坐标{地图坐标}")


def 鼠标移动点击(大漠对象,x,y,延迟时间):
    系统_延时(大漠对象, 延迟时间)
    鼠标_移动E(大漠对象,x,y)
    系统_延时(大漠对象,延迟时间)
    鼠标_单击左键(大漠对象)
    系统_延时(大漠对象, 延迟时间)

def 鼠标移动点击E(大漠对象,x,y,w,h,开始时间,结束时间):
    鼠标_移动Ex(大漠对象,x,y,w,h)
    系统_延时Ex(大漠对象,开始时间,结束时间)
    鼠标_单击左键(大漠对象)

def 鼠标移动右键(大漠对象,x,y,延迟时间):
    系统_延时(大漠对象, 延迟时间)
    鼠标_移动E(大漠对象, x, y)
    系统_延时(大漠对象, 延迟时间)
    鼠标_单击右键(大漠对象)
    系统_延时(大漠对象, 延迟时间)


def 坐标转换_游戏转小地图屏幕坐标(x,y,游x1,游y1,图x1,图y1,游x2,游y2,图x2,图y2):
    转换参数 = 计算转换比例((游x1, 游y1), (图x1, 图y1), (游x2, 游y2), (图x2, 图y2))
    游戏坐标 = (x, y)
    地图坐标 = 游戏转小地图屏幕坐标(*游戏坐标, 转换参数)
    return 地图坐标

def 坐标转换_小地图屏幕转游戏坐标(x,y,游x1,游y1,图x1,图y1,游x2,游y2,图x2,图y2):
    转换参数 = 计算转换比例((游x1, 游y1), (图x1, 图y1), (游x2, 游y2), (图x2, 图y2))
    游戏x,游戏y = 小地图屏幕转游戏坐标(x, y, 转换参数)
    return 游戏x,游戏y

def 取指定坐标方位(x,y,中心x,中心y):

    if x<0 or y<0 or 中心x<0 or 中心y<0:
        弹窗提醒("传入的数据不能为负数！")
        return

    if x < 中心x and y < 中心y:   #西北:
            return "西北"
    elif x < 中心x and y > 中心y:
        return "西南"
    elif x > 中心x and y < 中心y:
        return "东北"
    elif x > 中心x and y > 中心y:
        return "东南"
    elif x < 中心x and y == 中心y:
        return "正西"
    elif x == 中心x and y < 中心y:
        return "正北"
    elif x > 中心x and y == 中心y:
        return "正东"
    elif x == 中心x and y > 中心y:
        return "正南"

    return None

def 鼠标按住右键(大漠对象,x,y,延迟时间):
    鼠标_移动E(大漠对象, x, y)
    鼠标_按住右键(大漠对象)

    系统_延时(大漠对象,延迟时间)
    鼠标_弹起右键(大漠对象)

def Ai_找图(大漠对象,x1, y1, x2, y2, pic_name, sim, dir) :
    return 大漠对象.AiFindPic(x1, y1, x2, y2, pic_name, sim, dir)

def Ai_找图Ex(大漠对象,x1,y1,x2,y2,pic_name,sim,dir) :
    return 大漠对象.AiFindPicEx(x1,y1,x2,y2,pic_name,sim,dir)

def Ai_找图Mem(大漠对象,x1,y1,x2,y2,pic_info,sim,dir) :
    return 大漠对象.AiFindPicMem(x1,y1,x2,y2,pic_info,sim,dir)

def Ai_找图MemEx(大漠对象,x1,y1,x2,y2,pic_info,sim,dir) :
    return 大漠对象.AiFindPicMemEx(x1,y1,x2,y2,pic_info,sim,dir)

def Ai_是否弹出找图窗口(大漠对象,enable) :
    return 大漠对象.AiEnableFindPicWindow(enable)

def Ai_模块_内存加载(大漠对象,addr,size) :
    return 大漠对象.LoadAiMemory(addr,size)

def Ai_模块_加载(大漠对象,file_name) :
    return 大漠对象.LoadAi(file_name)

def Ai_模型_内存加载(大漠对象,index,addr,size,pwd) :
    return 大漠对象.AiYoloSetModelMemory(index,addr,size,pwd)

def Ai_模型_切换(大漠对象,index) :
    return 大漠对象.AiYoloUseModel(index)

def Ai_模型_加载(大漠对象,index,file_name,pwd) :
    return 大漠对象.AiYoloSetModel(index,file_name,pwd)

def Ai_模型_卸载(大漠对象,index) :
    return 大漠对象.AiYoloFreeModel(index)

def Ai_置版本(大漠对象,Ver) :
    return 大漠对象.AiYoloSetVersion(Ver)

def Ai_识别(大漠对象,x1,y1,x2,y2,prob,iou) :
    return 大漠对象.AiYoloDetectObjects(x1,y1,x2,y2,prob,iou)

def Ai_识别_返回图片(大漠对象,x1,y1,x2,y2,prob,iou,file_name,mode) :
    return 大漠对象.AiYoloDetectObjectsToFile(x1,y1,x2,y2,prob,iou,file_name,mode)

def Ai_识别_返回指针(大漠对象,x1,y1,x2,y2,prob,iou,mode) :
    return 大漠对象.AiYoloDetectObjectsToDataBmp(x1,y1,x2,y2,prob,iou,mode)

def Ai_识别结果排序(大漠对象,objects,height) :
    return 大漠对象.AiYoloSortsObjects(objects,height)

def Ai_识别结果输出(大漠对象,objects) :
    return 大漠对象.AiYoloObjectsToString(objects)

def 内存_优化(大漠对象,hwnd) :
    return 大漠对象.FreeProcessMemory(hwnd)

def 内存_写二进制(大漠对象,hwnd,addr,data) :
    return 大漠对象.WriteData(hwnd,addr,data)

def 内存_写二进制A(大漠对象,hwnd,addr,data) :
    return 大漠对象.WriteDataAddr(hwnd,addr,data)

def 内存_写二进制指针(大漠对象,hwnd,addr,data,length) :
    return 大漠对象.WriteDataFromBin(hwnd,addr,data,length)

def 内存_写二进制指针A(大漠对象,hwnd,addr,data,length) :
    return 大漠对象.WriteDataAddrFromBin(hwnd,addr,data,length)

def 内存_写二进制指针A字节集(大漠对象,hwnd,addr,datazjj) :
    return 大漠对象.WriteDataAddrZjj(hwnd,addr,datazjj)

def 内存_写二进制指针字节集(大漠对象,hwnd,addr,datazjj) :
    return 大漠对象.WriteDataZjj(hwnd,addr,datazjj)

def 内存_写单精浮点(大漠对象,hwnd,addr,v) :
    return 大漠对象.WriteFloat(hwnd,addr,v)
def 内存_写单精浮点A(大漠对象,hwnd,addr,v) :
    return 大漠对象.WriteFloatAddr(hwnd,addr,v)

def 内存_写双精浮点(大漠对象,hwnd,addr,v) :
    return 大漠对象.WriteDouble(hwnd,addr,v)

def 内存_写双精浮点A(大漠对象,hwnd,addr,v) :
    return 大漠对象.WriteDoubleAddr(hwnd,addr,v)

def 内存_写字符串(大漠对象,hwnd,addr,tpe,v) :
    return 大漠对象.WriteString(hwnd,addr,tpe,v)

def 内存_写字符串A(大漠对象,hwnd,addr,tpe,v) :
    return 大漠对象.WriteStringAddr(hwnd,addr,tpe,v)

def 内存_写整数(大漠对象,hwnd,addr,tpe,v) :
    return 大漠对象.WriteInt(hwnd,addr,tpe,v)

def 内存_写整数A(大漠对象,hwnd,addr,tpe,v) :
    return 大漠对象.WriteIntAddr(hwnd,addr,tpe,v)

def 内存_分配(大漠对象,hwnd,addr,size,tpe) :
    return 大漠对象.VirtualAllocEx(hwnd,addr,size,tpe)

def 内存_单精浮点转二进制(大漠对象,float_value) :
    return 大漠对象.FloatToData(float_value)

def 内存_双精度浮点数转二进制(大漠对象,double_value) :
    return 大漠对象.DoubleToData(double_value)

def 内存_取函数地址(大漠对象,hwnd,base_addr,fun_name) :
    return 大漠对象.GetRemoteApiAddress(hwnd,base_addr,fun_name)

def 内存_取命令行(大漠对象,hwnd) :
    return 大漠对象.GetCommandLine(hwnd)

def 内存_取字节集地址(大漠对象,param) :
    return 大漠对象.GetZjjAddr(param)

def 内存_取属性(大漠对象,hwnd,addr,pmbi) :
    return 大漠对象.VirtualQueryEx(hwnd,addr,pmbi)

def 内存_取模块基址(大漠对象,hwnd,module_name) :
    return 大漠对象.GetModuleBaseAddr(hwnd,module_name)

def 内存_取模块大小(大漠对象,hwnd,module_name) :
    return 大漠对象.GetModuleSize(hwnd,module_name)

def 内存_句柄转pid(大漠对象,en) :
    return 大漠对象.SetMemoryHwndAsProcessId(en)

def 内存_字符串转二进制(大漠对象,string_value,tpe) :
    return 大漠对象.StringToData(string_value,tpe)

def 内存_强制结束进程(大漠对象,pid) :
    return 大漠对象.TerminateProcess(pid)

def 内存_打开进程(大漠对象,pid) :
    return 大漠对象.OpenProcess(pid)

def 内存_搜索二进制(大漠对象,hwnd,addr_range,data) :
    return 大漠对象.FindData(hwnd,addr_range,data)

def 内存_搜索二进制Ex(大漠对象,hwnd,addr_range,data,steps,multi_thread,mode) :
    return 大漠对象.FindDataEx(hwnd,addr_range,data,steps,multi_thread,mode)

def 内存_搜索单精浮点(大漠对象,hwnd,addr_range,float_value_min,float_value_max) :
    return 大漠对象.FindFloat(hwnd,addr_range,float_value_min,float_value_max)

def 内存_搜索单精浮点Ex(大漠对象,hwnd,addr_range,float_value_min,float_value_max,steps,multi_thread,mode) :
    return 大漠对象.FindFloatEx(hwnd,addr_range,float_value_min,float_value_max,steps,multi_thread,mode)

def 内存_搜索双精浮点(大漠对象,hwnd,addr_range,double_value_min,double_value_max) :
    return 大漠对象.FindDouble(hwnd,addr_range,double_value_min,double_value_max)

def 内存_搜索双精浮点Ex(大漠对象,hwnd,addr_range,double_value_min,double_value_max,steps,multi_thread,mode) :
    return 大漠对象.FindDoubleEx(hwnd,addr_range,double_value_min,double_value_max,steps,multi_thread,mode)

def 内存_搜索字符串(大漠对象,hwnd,addr_range,string_value,tpe) :
    return 大漠对象.FindString(hwnd,addr_range,string_value,tpe)

def 内存_搜索字符串Ex(大漠对象,hwnd,addr_range,string_value,tpe,steps,multi_thread,mode) :
    return 大漠对象.FindStringEx(hwnd,addr_range,string_value,tpe,steps,multi_thread,mode)

def 内存_搜索整数(大漠对象,hwnd,addr_range,int_value_min,int_value_max,tpe) :
    return 大漠对象.FindInt(hwnd,addr_range,int_value_min,int_value_max,tpe)

def 内存_搜索整数Ex(大漠对象,hwnd,addr_range,int_value_min,int_value_max,tpe,steps,multi_thread,mode) :
    return 大漠对象.FindIntEx(hwnd,addr_range,int_value_min,int_value_max,tpe,steps,multi_thread,mode)

def 内存_搜索结果保存(大漠对象,file_name) :
    return 大漠对象.SetMemoryFindResultToFile(file_name)

def 内存_整数转二进制(大漠对象,int_value,tpe) :
    return 大漠对象.IntToData(int_value,tpe)

def 内存_置读写(大漠对象,hwnd,addr,size,tpe,old_protect) :
    return 大漠对象.VirtualProtectEx(hwnd,addr,size,tpe,old_protect)

def 内存_读二进制(大漠对象,hwnd,addr,length) :
    return 大漠对象.ReadData(hwnd,addr,length)

def 内存_读二进制A(大漠对象,hwnd,addr,length) :
    return 大漠对象.ReadDataAddr(hwnd,addr,length)

def 内存_读二进制A字节集(大漠对象,hwnd,addr,size) :
    return 大漠对象.ReadDataAddrZjj(hwnd,addr,size)

def 内存_读二进制地址(大漠对象,hwnd,addr,length) :
    return 大漠对象.ReadDataToBin(hwnd,addr,length)

def 内存_读二进制地址A(大漠对象,hwnd,addr,length) :
    return 大漠对象.ReadDataAddrToBin(hwnd,addr,length)

def 内存_读二进制地址字节集(大漠对象,hwnd,addr,size) :
    return 大漠对象.ReadDataZjj(hwnd,addr,size)

def 内存_读单精浮点(大漠对象,hwnd,addr) :
    return 大漠对象.ReadFloat(hwnd,addr)

def 内存_读单精浮点A(大漠对象,hwnd,addr) :
    return 大漠对象.ReadFloatAddr(hwnd,addr)

def 内存_读双精浮点(大漠对象,hwnd,addr) :
    return 大漠对象.ReadDouble(hwnd,addr)

def 内存_读双精浮点A(大漠对象,hwnd,addr) :
    return 大漠对象.ReadDoubleAddr(hwnd,addr)

def 内存_读字符串(大漠对象,hwnd,addr,tpe,length) :
    return 大漠对象.ReadString(hwnd,addr,tpe,length)

def 内存_读字符串A(大漠对象,hwnd,addr,tpe,length) :
    return 大漠对象.ReadStringAddr(hwnd,addr,tpe,length)

def 内存_读整数(大漠对象,hwnd,addr,tpe) :
    return 大漠对象.ReadInt(hwnd,addr,tpe)

def 内存_读整数A(大漠对象,hwnd,addr,tpe) :
    return 大漠对象.ReadIntAddr(hwnd,addr,tpe)

def 内存_追加图片(大漠对象,pic_info,pic) :
    return 大漠对象.AppendPicAddrZjj(pic_info,pic)

def 内存_释放(大漠对象,hwnd,addr) :
    return 大漠对象.VirtualFreeEx(hwnd,addr)

def 内存_长整数到指针(大漠对象) :
    return 大漠对象.SetParam64ToPointer()

def 内部_DelEnv(大漠对象,index,name) :
    return 大漠对象.DelEnv(index,name)

def 内部_FaqRelease(大漠对象,handle) :
    return 大漠对象.FaqRelease(handle)

def 内部_FreeScreenData(大漠对象,handle) :
    return 大漠对象.FreeScreenData(handle)

def 内部_GetEnv(大漠对象,index,name) :
    return 大漠对象.GetEnv (index,name)

def 内部_GetMac(大漠对象) :
    return 大漠对象.GetMac()

def 内部_Hex32(大漠对象,v) :
    return 大漠对象.Hex32(v)

def 内部_Hex64(大漠对象,v) :
    return 大漠对象.Hex64(v)

def 内部_Log(大漠对象,info) :
    return 大漠对象.Log (info)

def 内部_Md5(大漠对象,str) :
    return 大漠对象.Md5(str)

def 内部_MoveDD(大漠对象,dx,dy) :
    return 大漠对象.MoveDD(dx,dy)

def 内部_ReadFileData(大漠对象,file_name,start_pos,end_pos) :
    return 大漠对象.ReadFileData(file_name,start_pos,end_pos)

def 内部_SendCommand(大漠对象,cmd) :
    return 大漠对象.SendCommand(cmd)

def 内部_SetEnv(大漠对象,index,name,value) :
    return 大漠对象.SetEnv (index,name,value)

def 内部_SetExportDict(大漠对象,index,dict_name) :
    return 大漠对象.SetExportDict(index,dict_name)

def 内部_ShowScrMsg(大漠对象,x1,y1,x2,y2,msg,color) :
    return 大漠对象.ShowScrMsg(x1,y1,x2,y2,msg,color)

def 内部_StrStr(大漠对象,s,str) :
    return 大漠对象.StrStr (s,str)

def 创建dm(大漠对象) :
    return 大漠对象.创建()

def 后台_切换绑定(大漠对象,hwnd) :
    return 大漠对象.SwitchBindWindow(hwnd)

def 后台_取FPS(大漠对象) :
    return 大漠对象.GetFps()

def 后台_取绑定句柄(大漠对象) :
    return 大漠对象.GetBindWindow()

def 后台_取绑定状态(大漠对象,hwnd) :
    return 大漠对象.IsBind(hwnd)

def 后台_绑定窗口(大漠对象,hwnd,display,mouse,keypad,mode) :
    return 大漠对象.BindWindow(hwnd,display,mouse,keypad,mode)


def 后台_绑定窗口Ex(大漠对象,hwnd,display,mouse,keypad,public_desc,mode) :
    return 大漠对象.BindWindowEx(hwnd,display,mouse,keypad,public_desc,mode)

def 后台_置Aero(大漠对象,en) :
    return 大漠对象.SetAero(en)

def 后台_置CPU占用(大漠对象,tpe,rate) :
    return 大漠对象.DownCpu(tpe,rate)

def 后台_置opengl截图延迟(大漠对象,t) :
    return 大漠对象.SetDisplayRefreshDelay(t)

def 后台_置假激活(大漠对象,en) :
    return 大漠对象.EnableFakeActive(en)

def 后台_置加速(大漠对象,rate) :
    return 大漠对象.HackSpeed(rate)

def 后台_置截图延迟(大漠对象,t) :
    return 大漠对象.SetDisplayDelay(t)

def 后台_置控制(大漠对象,en) :
    return 大漠对象.EnableBind(en)

def 后台_置真实键盘(大漠对象,en) :
    return 大漠对象.EnableRealKeypad(en)

def 后台_置真实鼠标(大漠对象,en,mousedelay,mousestep) :
    return 大漠对象.EnableRealMouse(en,mousedelay,mousestep)

def 后台_置输入对象(大漠对象,input_dm,rx,ry) :
    return 大漠对象.SetInputDm(input_dm,rx,ry)

def 后台_置输入法(大漠对象,en) :
    return 大漠对象.EnableIme(en)

def 后台_置键盘同步(大漠对象,en,time_out) :
    return 大漠对象.EnableKeypadSync(en,time_out)

def 后台_置键盘消息(大漠对象,en) :
    return 大漠对象.EnableKeypadMsg(en)

def 后台_置键盘补丁(大漠对象,en) :
    return 大漠对象.EnableKeypadPatch(en)

def 后台_置高速Dx键鼠(大漠对象,en) :
    return 大漠对象.EnableSpeedDx(en)

def 后台_置鼠标同步(大漠对象,en,time_out) :
    return 大漠对象.EnableMouseSync(en,time_out)

def 后台_置鼠标消息(大漠对象,en) :
    return 大漠对象.EnableMouseMsg(en)

def 后台_解绑窗口(大漠对象) :
    return 大漠对象.UnBindWindow()

def 后台_解绑窗口_强制(大漠对象,hwnd) :
    return 大漠对象.ForceUnBindWindow(hwnd)

def 后台_锁定图色(大漠对象,locks) :
    return 大漠对象.LockDisplay(locks)

def 后台_锁定输入(大漠对象,locks) :
    return 大漠对象.LockInput(locks)

def 后台_锁定鼠标范围(大漠对象,x1,y1,x2,y2) :
    return 大漠对象.LockMouseRect(x1,y1,x2,y2)

def 图色_RGB转BGR(大漠对象,rgb_color) :
    return 大漠对象.RGB2BGR(rgb_color)

def 图色_内存找图(大漠对象,x1,y1,x2,y2,pic_info,delta_color,sim,dir) :
    return 大漠对象.FindPicMem(x1,y1,x2,y2,pic_info,delta_color,sim,dir)

def 图色_内存找图E(大漠对象,x1,y1,x2,y2,pic_info,delta_color,sim,dir) :
    return 大漠对象.FindPicMemE(x1,y1,x2,y2,pic_info,delta_color,sim,dir)

def 图色_内存找图Ex(大漠对象,x1,y1,x2,y2,pic_info,delta_color,sim,dir) :
    return 大漠对象.FindPicMemEx(x1,y1,x2,y2,pic_info,delta_color,sim,dir)

def 图色_内存找图Sim(大漠对象,x1,y1,x2,y2,pic_info,delta_color,sim,dir) :
    return 大漠对象.FindPicSimMem(x1,y1,x2,y2,pic_info,delta_color,sim,dir)

def 图色_内存找图SimE(大漠对象,x1,y1,x2,y2,pic_info,delta_color,sim,dir) :
    return 大漠对象.FindPicSimMemE(x1,y1,x2,y2,pic_info,delta_color,sim,dir)

def 图色_内存找图SimEx(大漠对象,x1,y1,x2,y2,pic_info,delta_color,sim,dir) :
    return 大漠对象.FindPicSimMemEx(x1,y1,x2,y2,pic_info,delta_color,sim,dir)

def 图色_内存找图字节集(大漠对象,x1,y1,x2,y2,pic_info,delta_color,sim,dir) :
    return 大漠对象.FindPicMemZjj(x1,y1,x2,y2,pic_info,delta_color,sim,dir)

def 图色_内存找图字节集E(大漠对象,x1,y1,x2,y2,pic_info,delta_color,sim,dir) :
    return 大漠对象.FindPicMemEZjj(x1,y1,x2,y2,pic_info,delta_color,sim,dir)

def 图色_内存找图字节集Ex(大漠对象,x1,y1,x2,y2,pic_info,delta_color,sim,dir) :
    return 大漠对象.FindPicMemExZjj(x1,y1,x2,y2,pic_info,delta_color,sim,dir)

def 图色_加载内存图片(大漠对象,addr,size,name) :
    return 大漠对象.LoadPicByte(addr,size,name)

def 图色_加载文件图片(大漠对象,pic_name) :
    return 大漠对象.LoadPic(pic_name)

def 图色_取图片尺寸(大漠对象,pic_name) :
    return 大漠对象.GetPicSize(pic_name)

def 图色_取均值HSV(大漠对象,x1,y1,x2,y2) :
    return 大漠对象.GetAveHSV(x1,y1,x2,y2)

def 图色_取均值RGB(大漠对象,x1,y1,x2,y2) :
    return 大漠对象.GetAveRGB(x1,y1,x2,y2)

def 图色_取数据地址(大漠对象,x1,y1,x2,y2) :
    return 大漠对象.GetScreenData(x1,y1,x2,y2)

def 图色_取数据指针(大漠对象,x1,y1,x2,y2) :
    return 大漠对象.GetScreenDataBmp(x1,y1,x2,y2)

def 图色_取色(大漠对象,x,y) :
    return 大漠对象.GetColor(x,y)

def 图色_取色BGR(大漠对象,x,y) :
    return 大漠对象.GetColorBGR(x,y)

def 图色_取色HSV(大漠对象,x,y) :
    return 大漠对象.GetColorHSV(x,y)

def 图色_取颜色数(大漠对象,x1,y1,x2,y2,color,sim) :
    return 大漠对象.GetColorNum(x1,y1,x2,y2,color,sim)

def 图色_图片转bmp(大漠对象,pic_name,bmp_name) :
    return 大漠对象.ImageToBmp (pic_name,bmp_name)

def 图色_多点找色(大漠对象,x1,y1,x2,y2,first_color,offset_color,sim,dir) :
    return 大漠对象.FindMultiColor(x1,y1,x2,y2,first_color,offset_color,sim,dir)

def 图色_多点找色E(大漠对象,x1,y1,x2,y2,first_color,offset_color,sim,dir) :
    return 大漠对象.FindMultiColorE(x1,y1,x2,y2,first_color,offset_color,sim,dir)

def 图色_多点找色Ex(大漠对象,x1,y1,x2,y2,first_color,offset_color,sim,dir) :
    return 大漠对象.FindMultiColorEx(x1,y1,x2,y2,first_color,offset_color,sim,dir)

def 图色_截取gif(大漠对象,x1,y1,x2,y2,file_name,delay,time) :
    return 大漠对象.CaptureGif(x1,y1,x2,y2,file_name,delay,time)

def 图色_截取jpg(大漠对象,x1,y1,x2,y2,file_name,quality) :
    return 大漠对象.CaptureJpg(x1,y1,x2,y2,file_name,quality)

def 图色_截取png(大漠对象,x1,y1,x2,y2,file_name) :
    return 大漠对象.CapturePng(x1,y1,x2,y2,file_name)

def 图色_截取上次区域bmp(大漠对象,file_name) :
    return 大漠对象.CapturePre(file_name)

def 图色_截取保存bmp(大漠对象,x1,y1,x2,y2,file_name) :
    return 大漠对象.Capture(x1,y1,x2,y2,file_name)

def 图色_截图取色(大漠对象,en) :
    return 大漠对象.EnableGetColorByCapture(en)

def 图色_找图(大漠对象,x1,y1,x2,y2,pic_name,delta_color,sim,dir) :
    return 大漠对象.FindPic(x1,y1,x2,y2,pic_name,delta_color,sim,dir)

def 图色_找图E(大漠对象,x1,y1,x2,y2,pic_name,delta_color,sim,dir) :
    return 大漠对象.FindPicE(x1,y1,x2,y2,pic_name,delta_color,sim,dir)

def 图色_找图Ex(大漠对象,x1,y1,x2,y2,pic_name,delta_color,sim,dir) :
    return 大漠对象.FindPicEx(x1,y1,x2,y2,pic_name,delta_color,sim,dir)

def 图色_找图ExS(大漠对象,x1,y1,x2,y2,pic_name,delta_color,sim,dir) :
    return 大漠对象.FindPicExS(x1,y1,x2,y2,pic_name,delta_color,sim,dir)

def 图色_找图S(大漠对象,x1,y1,x2,y2,pic_name,delta_color,sim,dir) :
    return 大漠对象.FindPicS(x1,y1,x2,y2,pic_name,delta_color,sim,dir)

def 图色_找图Sim(大漠对象,x1,y1,x2,y2,pic_name,delta_color,sim,dir) :
    return 大漠对象.FindPicSim(x1,y1,x2,y2,pic_name,delta_color,sim,dir)

def 图色_找图SimE(大漠对象,x1,y1,x2,y2,pic_name,delta_color,sim,dir) :
    return 大漠对象.FindPicSimE(x1,y1,x2,y2,pic_name,delta_color,sim,dir)

def 图色_找图SimEx(大漠对象,x1,y1,x2,y2,pic_name,delta_color,sim,dir) :
    return 大漠对象.FindPicSimEx(x1,y1,x2,y2,pic_name,delta_color,sim,dir)

def 图色_找多色(大漠对象,x1,y1,x2,y2,color,sim) :
    return 大漠对象.FindMulColor(x1,y1,x2,y2,color,sim)

def 图色_找形状(大漠对象,x1,y1,x2,y2,offset_color,sim,dir) :
    return 大漠对象.FindShape(x1,y1,x2,y2,offset_color,sim,dir)

def 图色_找形状E(大漠对象,x1,y1,x2,y2,offset_color,sim,dir) :
    return 大漠对象.FindShapeE(x1,y1,x2,y2,offset_color,sim,dir)

def 图色_找形状Ex(大漠对象,x1,y1,x2,y2,offset_color,sim,dir) :
    return 大漠对象.FindShapeEx(x1,y1,x2,y2,offset_color,sim,dir)

def 图色_找色(大漠对象,x1,y1,x2,y2,color,sim,dir) :
    return 大漠对象.FindColor(x1,y1,x2,y2,color,sim,dir)

def 图色_找色E(大漠对象,x1,y1,x2,y2,color,sim,dir) :
    return 大漠对象.FindColorE(x1,y1,x2,y2,color,sim,dir)

def 图色_找色Ex(大漠对象,x1,y1,x2,y2,color,sim,dir) :
    return 大漠对象.FindColorEx(x1,y1,x2,y2,color,sim,dir)

def 图色_找色块(大漠对象,x1,y1,x2,y2,color,sim,count,width,height) :
    return 大漠对象.FindColorBlock(x1,y1,x2,y2,color,sim,count,width,height)

def 图色_找色块Ex(大漠对象,x1,y1,x2,y2,color,sim,count,width,height) :
    return 大漠对象.FindColorBlockEx(x1,y1,x2,y2,color,sim,count,width,height)

def 图色_排除区域(大漠对象,tpe,info) :
    return 大漠对象.SetExcludeRegion(tpe,info)

def 图色_是否卡屏(大漠对象,x1,y1,x2,y2,t) :
    return 大漠对象.IsDisplayDead (x1,y1,x2,y2,t)

def 图色_枚举图片(大漠对象,pic_name) :
    return 大漠对象.MatchPicName(pic_name)

def 图色_比较颜色(大漠对象,x,y,color,sim) :
    return 大漠对象.CmpColor(x,y,color,sim)

def 图色_线程找图(大漠对象,en) :
    return 大漠对象.EnableFindPicMultithread(en)

def 图色_线程控制(大漠对象,count) :
    return 大漠对象.SetFindPicMultithreadCount(count)

def 图色_线程限制(大漠对象,limit) :
    return 大漠对象.SetFindPicMultithreadLimit(limit)

def 图色_置图片密码(大漠对象,pwd) :
    return 大漠对象.SetPicPwd(pwd)

def 图色_调试(大漠对象,enable_debug) :
    return 大漠对象.EnableDisplayDebug(enable_debug)

def 图色_追加图片(大漠对象,pic_info,addr,size) :
    return 大漠对象.AppendPicAddr(pic_info,addr,size)

def 图色_释放图片(大漠对象,pic_name) :
    return 大漠对象.FreePic(pic_name)

def 基本_取全局路径(大漠对象) :
    return 大漠对象.GetPath()

def 基本_取大漠版本号(大漠对象) :
    return 大漠对象.Ver()

def 基本_取对象ID(大漠对象) :
    return 大漠对象.GetID()

def 基本_取对象数量(大漠对象) :
    return 大漠对象.GetDmCount()

def 基本_取插件路径(大漠对象) :
    return 大漠对象.GetBasePath()

def 基本_取最后错误(大漠对象) :
    return 大漠对象.GetLastError()

def 基本_注册VIP(大漠对象,code,Ver) :
    return 大漠对象.Reg(code,Ver)

def 基本_注册VIPEx(大漠对象,code,Ver,ip) :
    return 大漠对象.RegEx(code,Ver,ip)

def 基本_注册VIPEx_无mac(大漠对象,code,Ver,ip) :
    return 大漠对象.RegExNoMac(code,Ver,ip)

def 基本_注册VIP_无mac(大漠对象,code,Ver) :
    return 大漠对象.RegNoMac(code,Ver)

def 基本_置全局路径(大漠对象,path) :
    return 大漠对象.SetPath(path)

def 基本_置前台图色加速(大漠对象,en) :
    return 大漠对象.SpeedNormalGraphic(en)

def 基本_置图片缓存(大漠对象,en) :
    return 大漠对象.EnablePicCache(en)

def 基本_置图色模式(大漠对象,mode) :
    return 大漠对象.SetDisplayInput(mode)

def 基本_置枚举延迟(大漠对象,delay) :
    return 大漠对象.SetEnumWindowDelay(delay)

def 基本_置错误提示(大漠对象,show) :
    return 大漠对象.SetShowErrorMsg(show)

def 护盾_开关(大漠对象,en,tpe) :
    return 大漠对象.DmGuard(en,tpe)

def 护盾_控制(大漠对象,cmd,sub_cmd,param) :
    return 大漠对象.DmGuardParams(cmd,sub_cmd,param)

def 护盾_驱动加载(大漠对象,tpe,path) :
    return 大漠对象.DmGuardLoadCustom(tpe,path)

def 护盾_驱动卸载(大漠对象) :
    return 大漠对象.UnLoadDriver()

def 护盾_驱动释放(大漠对象,tpe,path) :
    return 大漠对象.DmGuardExtract(tpe,path)

def 文件_下载dm(大漠对象,url,save_file,timeout) :
    return 大漠对象.DownloadFile(url,save_file,timeout)

def 文件_写入(大漠对象,file_name,content) :
    return 大漠对象.WriteFile(file_name,content)

def 文件_写配置项(大漠对象,section,key,v,file_name) :
    return 大漠对象.WriteIni(section,key,v,file_name)

def 文件_写配置项Ex(大漠对象,section,key,v,file_name,pwd) :
    return 大漠对象.WriteIniPwd(section,key,v,file_name,pwd)

def 文件_创建目录(大漠对象,folder_name) :
    return 大漠对象.CreateFolder(folder_name)

def 文件_删除dm(大漠对象,file_name) :
    return 大漠对象.DeleteFile(file_name)

def 文件_删除目录(大漠对象,folder_name) :
    return 大漠对象.DeleteFolder(folder_name)

def 文件_删除配置(大漠对象,section,key,file_name) :
    return 大漠对象.DeleteIni(section,key,file_name)

def 文件_删除配置Ex(大漠对象,section,key,file_name,pwd) :
    return 大漠对象.DeleteIniPwd(section,key,file_name,pwd)

def 文件_加密(大漠对象,file_name,pwd) :
    return 大漠对象.EncodeFile(file_name,pwd)

def 文件_取真实路径(大漠对象,path) :
    return 大漠对象.GetRealPath(path)

def 文件_取长度(大漠对象,file_name) :
    return 大漠对象.GetFileLength(file_name)

def 文件_拷贝(大漠对象,src_file,dst_file,over) :
    return 大漠对象.CopyFile(src_file,dst_file,over)

def 文件_是否存在dm(大漠对象,file_name) :
    return 大漠对象.IsFileExist(file_name)

def 文件_枚举节名(大漠对象,file_name) :
    return 大漠对象.EnumIniSection(file_name)

def 文件_枚举节名Ex(大漠对象,file_name,pwd) :
    return 大漠对象.EnumIniSectionPwd(file_name,pwd)

def 文件_枚举键名(大漠对象,section,file_name) :
    return 大漠对象.EnumIniKey(section,file_name)

def 文件_枚举键名Ex(大漠对象,section,file_name,pwd) :
    return 大漠对象.EnumIniKeyPwd(section,file_name,pwd)

def 文件_目录是否存在(大漠对象,folder) :
    return 大漠对象.IsFolderExist(folder)

def 文件_移动dm(大漠对象,src_file,dst_file) :
    return 大漠对象.MoveFile(src_file,dst_file)

def 文件_解密(大漠对象,file_name,pwd) :
    return 大漠对象.DecodeFile(file_name,pwd)

def 文件_读取(大漠对象,file_name) :
    return 大漠对象.ReadFile(file_name)

def 文件_读配置项(大漠对象,section,key,file_name) :
    return 大漠对象.ReadIni(section,key,file_name)

def 文件_读配置项Ex(大漠对象,section,key,file_name,pwd) :
    return 大漠对象.ReadIniPwd(section,key,file_name,pwd)

def 文件_选择文件(大漠对象) :
    return 大漠对象.SelectFile()

def 文件_选择目录(大漠对象) :
    return 大漠对象.SelectDirectory()

def 文字_取坐标数量(大漠对象,str) :
    return 大漠对象.GetResultCount(str)

def 文字_取指定坐标(大漠对象,str,index) :
    return 大漠对象.GetResultPos(str,index)

def 文字_取词组内容(大漠对象,str,index) :
    return 大漠对象.GetWordResultStr(str,index)

def 文字_取词组坐标(大漠对象,str,index) :
    return 大漠对象.GetWordResultPos(str,index)

def 文字_取词组数量(大漠对象,str) :
    return 大漠对象.GetWordResultCount(str)

def 文字_字库保存(大漠对象,index,file_name) :
    return 大漠对象.SaveDict(index,file_name)

def 文字_字库全局(大漠对象,en) :
    return 大漠对象.EnableShareDict(en)

def 文字_字库切换(大漠对象,index) :
    return 大漠对象.UseDict(index)

def 文字_字库取字符数(大漠对象,index) :
    return 大漠对象.GetDictCount(index)

def 文字_字库取大漠对象(大漠对象) :
    return 大漠对象.GetNowDict()

def 文字_字库取描述(大漠对象,str,font_name,font_size,flag) :
    return 大漠对象.GetDictInfo(str,font_name,font_size,flag)

def 文字_字库取条目(大漠对象,index,font_index) :
    return 大漠对象.GetDict(index,font_index)

def 文字_字库添加(大漠对象,index,dict_info) :
    return 大漠对象.AddDict(index,dict_info)

def 文字_字库清空(大漠对象,index) :
    return 大漠对象.ClearDict(index)

def 文字_找字(大漠对象,x1,y1,x2,y2,str,color,sim) :
    return 大漠对象.FindStr(x1,y1,x2,y2,str,color,sim)

def 文字_找字E(大漠对象,x1,y1,x2,y2,str,color,sim) :
    return 大漠对象.FindStrE(x1,y1,x2,y2,str,color,sim)

def 文字_找字Ex(大漠对象,x1,y1,x2,y2,str,color,sim) :
    return 大漠对象.FindStrEx(x1,y1,x2,y2,str,color,sim)

def 文字_找字ExS(大漠对象,x1,y1,x2,y2,str,color,sim) :
    return 大漠对象.FindStrExS(x1,y1,x2,y2,str,color,sim)

def 文字_找字S(大漠对象,x1,y1,x2,y2,str,color,sim) :
    return 大漠对象.FindStrS(x1,y1,x2,y2,str,color,sim)

def 文字_找字_快速(大漠对象,x1,y1,x2,y2,str,color,sim) :
    return 大漠对象.FindStrFast(x1,y1,x2,y2,str,color,sim)

def 文字_找字_快速E(大漠对象,x1,y1,x2,y2,str,color,sim) :
    return 大漠对象.FindStrFastE(x1,y1,x2,y2,str,color,sim)

def 文字_找字_快速Ex(大漠对象,x1,y1,x2,y2,str,color,sim) :
    return 大漠对象.FindStrFastEx(x1,y1,x2,y2,str,color,sim)

def 文字_找字_快速ExS(大漠对象,x1,y1,x2,y2,str,color,sim) :
    return 大漠对象.FindStrFastExS(x1,y1,x2,y2,str,color,sim)

def 文字_找字_快速S(大漠对象,x1,y1,x2,y2,str,color,sim) :
    return 大漠对象.FindStrFastS(x1,y1,x2,y2,str,color,sim)

def 文字_找字_系统(大漠对象,x1,y1,x2,y2,str,color,sim,font_name,font_size,flag) :
    return 大漠对象.FindStrWithFont(x1,y1,x2,y2,str,color,sim,font_name,font_size,flag)

def 文字_找字_系统E(大漠对象,x1,y1,x2,y2,str,color,sim,font_name,font_size,flag) :
    return 大漠对象.FindStrWithFontE(x1,y1,x2,y2,str,color,sim,font_name,font_size,flag)

def 文字_找字_系统Ex(大漠对象,x1,y1,x2,y2,str,color,sim,font_name,font_size,flag) :
    return 大漠对象.FindStrWithFontEx(x1,y1,x2,y2,str,color,sim,font_name,font_size,flag)

def 文字_文字_词组模糊识别(大漠对象,x1,y1,x2,y2,color) :
    return 大漠对象.GetWordsNoDict(x1,y1,x2,y2,color)

def 文字_点阵提取(大漠对象,x1,y1,x2,y2,color,word) :
    return 大漠对象.FetchWord(x1,y1,x2,y2,color,word)

def 文字_置内存字库(大漠对象,index,addr,size) :
    return 大漠对象.SetDictMem(index,addr,size)

def 文字_置内存字库字节集(大漠对象,index,dict) :
    return 大漠对象.SetDictMemZjj(index,dict)

def 文字_置列距(大漠对象,col_gap) :
    return 大漠对象.SetMinColGap(col_gap)

def 文字_置字库(大漠对象,index,dict_name) :
    return 大漠对象.SetDict(index,dict_name)

def 文字_置字库密码(大漠对象,pwd) :
    return 大漠对象.SetDictPwd(pwd)

def 文字_置精准(大漠对象,exact_ocr) :
    return 大漠对象.SetExactOcr(exact_ocr)

def 文字_置行距(大漠对象,row_gap) :
    return 大漠对象.SetMinRowGap(row_gap)

def 文字_置词组列距_无库(大漠对象,col_gap) :
    return 大漠对象.SetColGapNoDict(col_gap)

def 文字_置词组行距_无库(大漠对象,row_gap) :
    return 大漠对象.SetRowGapNoDict(row_gap)

def 文字_置词组行高(大漠对象,line_height) :
    return 大漠对象.SetWordLineHeight(line_height)

def 文字_置词组行高_无库(大漠对象,line_height) :
    return 大漠对象.SetWordLineHeightNoDict(line_height)

def 文字_置词组间隔(大漠对象,word_gap) :
    return 大漠对象.SetWordGap(word_gap)

def 文字_置词组间隔_无库(大漠对象,word_gap) :
    return 大漠对象.SetWordGapNoDict(word_gap)

def 文字_识别(大漠对象,x1,y1,x2,y2,color,sim) :
    return 大漠对象.Ocr(x1,y1,x2,y2,color,sim)

def 文字_识别bmp(大漠对象,x1,y1,x2,y2,pic_name,color,sim) :
    return 大漠对象.OcrInFile(x1,y1,x2,y2,pic_name,color,sim)

def 文字_识别Ex(大漠对象,x1,y1,x2,y2,color,sim) :
    return 大漠对象.OcrEx(x1,y1,x2,y2,color,sim)

def 文字_识别Ex1(大漠对象,x1,y1,x2,y2,color,sim) :
    return 大漠对象.OcrExOne(x1,y1,x2,y2,color,sim)

def 文字_词组识别(大漠对象,x1,y1,x2,y2,color,sim) :
    return 大漠对象.GetWords(x1,y1,x2,y2,color,sim)

def 杂项_Cmd指令(大漠对象,cmd,current_dir,time_out) :
    return 大漠对象.ExecuteCmd(cmd,current_dir,time_out)

def 杂项_临界区_初始化(大漠对象) :
    return 大漠对象.InitCri()

def 杂项_临界区进入(大漠对象) :
    return 大漠对象.EnterCri()

def 杂项_临界区退出(大漠对象) :
    return 大漠对象.LeaveCri()

def 杂项_线程退出(大漠对象,mode) :
    return 大漠对象.SetExitThread(mode)

def 杂项_输入法是否开启(大漠对象,hwnd,id) :
    return 大漠对象.CheckInputMethod(hwnd,id)

def 杂项_输入法检测(大漠对象,id) :
    return 大漠对象.FindInputMethod(id)

def 杂项_输入法激活(大漠对象,hwnd,id) :
    return 大漠对象.ActiveInputMethod(hwnd,id)

def 杂项_降低引用(大漠对象) :
    return 大漠对象.ReleaseRef()

def 汇编_执行(大漠对象,hwnd,mode) :
    return 大漠对象.AsmCall(hwnd,mode)

def 汇编_执行Ex(大漠对象,hwnd,mode,base_addr) :
    return 大漠对象.AsmCallEx(hwnd,mode,base_addr)

def 汇编_指令转机器码(大漠对象,base_addr,is_64bit) :
    return 大漠对象.Assemble(base_addr,is_64bit)

def 汇编_机器码转指令(大漠对象,asm_code,base_addr,is_64bit) :
    return 大漠对象.DisAssemble(asm_code,base_addr,is_64bit)

def 汇编_添加(大漠对象,asm_ins) :
    return 大漠对象.AsmAdd(asm_ins)

def 汇编_清除(大漠对象) :
    return 大漠对象.AsmClear()

def 汇编_置句柄转进程ID(大漠对象,en) :
    return 大漠对象.SetAsmHwndAsProcessId(en)

def 汇编_置延迟(大漠对象,time_out,param) :
    return 大漠对象.AsmSetTimeout(time_out,param)

def 汇编_置错误提示(大漠对象,show) :
    return 大漠对象.SetShowAsmErrorMsg(show)

def 窗口_发送文本(大漠对象,hwnd,str) :
    return 大漠对象.SendString(hwnd,str)

def 窗口_发送文本2(大漠对象,hwnd,str) :
    return 大漠对象.SendString2(hwnd,str)

def 窗口_发送文本ime(大漠对象,str) :
    return 大漠对象.SendStringIme(str)

def 窗口_发送文本ime2(大漠对象,hwnd,str,mode) :
    return 大漠对象.SendStringIme2(hwnd,str,mode)

def 窗口_发送粘贴(大漠对象,hwnd) :
    return 大漠对象.SendPaste(hwnd)

def 窗口_取位置(大漠对象,hwnd) :
    return 大漠对象.GetWindowRect(hwnd)

def 窗口_取坐标处句柄(大漠对象,x,y) :
    return 大漠对象.GetPointWindow(x,y)

def 窗口_取客户区坐标(大漠对象,hwnd) :
    return 大漠对象.GetClientRect(hwnd)

def 窗口_取客户区大小(大漠对象,hwnd) :
    return 大漠对象.GetClientSize(hwnd)

def 窗口_取标题(大漠对象,hwnd) :
    return 大漠对象.GetWindowTitle(hwnd)

def 窗口_取特殊句柄(大漠对象,flag) :
    return 大漠对象.GetSpecialWindow(flag)

def 窗口_取状态(大漠对象,hwnd,flag) :
    return 大漠对象.GetWindowState(hwnd,flag)

def 窗口_取相关句柄(大漠对象,hwnd,flag) :
    return 大漠对象.GetWindow(hwnd,flag)

def 窗口_取类名(大漠对象,hwnd) :
    return 大漠对象.GetWindowClass(hwnd)

def 窗口_取线程ID(大漠对象,hwnd) :
    return 大漠对象.GetWindowThreadId(hwnd)

def 窗口_取进程ID(大漠对象,hwnd) :
    return 大漠对象.GetWindowProcessId(hwnd)

def 窗口_取进程信息(大漠对象,pid) :
    return 大漠对象.GetProcessInfo(pid)

def 窗口_取进程路径(大漠对象,hwnd) :
    return 大漠对象.GetWindowProcessPath(hwnd)

def 窗口_取顶层活动句柄(大漠对象) :
    return 大漠对象.GetForegroundWindow()

def 窗口_取顶层焦点句柄(大漠对象) :
    return 大漠对象.GetForegroundFocus()

def 窗口_取鼠标指向句柄(大漠对象) :
    return 大漠对象.GetMousePointWindow()

def 窗口_屏幕转窗口坐标(大漠对象,hwnd,x,y) :
    return 大漠对象.ScreenToClient(hwnd,x,y)

def 窗口_枚举句柄(大漠对象,parent,title,class_name,filter) :
    return 大漠对象.EnumWindow(parent,title,class_name,filter)

def 窗口_枚举句柄P(大漠对象,pid,title,class_name,filter) :
    return 大漠对象.EnumWindowByProcessId(pid,title,class_name,filter)

def 窗口_枚举句柄PN(大漠对象,process_name,title,class_name,filter) :
    return 大漠对象.EnumWindowByProcess(process_name,title,class_name,filter)

def 窗口_枚举句柄S(大漠对象,spec1,flag1,type1,spec2,flag2,type2,sort) :
    return 大漠对象.EnumWindowSuper(spec1,flag1,type1,spec2,flag2,type2,sort)

def 窗口_枚举进程ID(大漠对象,name) :
    return 大漠对象.EnumProcess(name)

def 窗口_查找句柄(大漠对象,class_name,title_name) :
    return 大漠对象.FindWindow(class_name,title_name)

def 窗口_查找句柄Ex(大漠对象,parent,class_name,title_name) :
    return 大漠对象.FindWindowEx(parent,class_name,title_name)

def 窗口_查找句柄P(大漠对象,process_id,class_name,title_name) :
    return 大漠对象.FindWindowByProcessId(process_id,class_name,title_name)

def 窗口_查找句柄PN(大漠对象,process_name,class_name,title_name) :
    return 大漠对象.FindWindowByProcess(process_name,class_name,title_name)

def 窗口_查找句柄S(大漠对象,spec1,flag1,type1,spec2,flag2,type2) :
    return 大漠对象.FindWindowSuper(spec1,flag1,type1,spec2,flag2,type2)

def 窗口_移动(大漠对象,hwnd,x,y) :
    return 大漠对象.MoveWindow(hwnd,x,y)

def 窗口_窗口转屏幕坐标(大漠对象,hwnd,x,y) :
    return 大漠对象.ClientToScreen(hwnd,x,y)

def 窗口_置大小(大漠对象,hwnd,width,height) :
    return 大漠对象.SetWindowSize(hwnd,width,height)

def 窗口_置客户区大小(大漠对象,hwnd,width,height) :
    return 大漠对象.SetClientSize(hwnd,width,height)

def 窗口_置标题(大漠对象,hwnd,text) :
    return 大漠对象.SetWindowText(hwnd,text)

def 窗口_置状态(大漠对象,hwnd,flag) :
    return 大漠对象.SetWindowState(hwnd,flag)

def 窗口_置透明(大漠对象,hwnd,v) :
    return 大漠对象.SetWindowTransparent(hwnd,v)

def 窗口_设置发送间隔(大漠对象,delay) :
    return 大漠对象.SetSendStringDelay(delay)

def 答题_取回答案(大漠对象) :
    return 大漠对象.FaqFetch()

def 答题_取数据大小(大漠对象,handle) :
    return 大漠对象.FaqGetSize(handle)

def 答题_取消发送(大漠对象) :
    return 大漠对象.FaqCancel()

def 答题_同步发送(大漠对象,server,handle,request_type,time_out) :
    return 大漠对象.FaqSend(server,handle,request_type,time_out)

def 答题_图像类型(大漠对象,x1,y1,x2,y2,quality,delay,time) :
    return 大漠对象.FaqCapture(x1,y1,x2,y2,quality,delay,time)

def 答题_异步发送(大漠对象,server,handle,request_type,time_out) :
    return 大漠对象.FaqPost(server,handle,request_type,time_out)

def 答题_文件截图(大漠对象,x1,y1,x2,y2,file_name,quality) :
    return 大漠对象.FaqCaptureFromFile(x1,y1,x2,y2,file_name,quality)

def 答题_文字类型(大漠对象,str) :
    return 大漠对象.FaqCaptureString(str)

def 答题_是否发送(大漠对象) :
    return 大漠对象.FaqIsPosted()

def 算法_取最近坐标(大漠对象,all_pos,tpe,x,y) :
    return 大漠对象.FindNearestPos(all_pos,tpe,x,y)

def 算法_排序坐标(大漠对象,all_pos,tpe,x,y) :
    return 大漠对象.SortPosDistance(all_pos,tpe,x,y)

def 算法_排除区域(大漠对象,all_pos,tpe,x1,y1,x2,y2) :
    return 大漠对象.ExcludePos(all_pos,tpe,x1,y1,x2,y2)

def 系统_关闭休眠(大漠对象) :
    return 大漠对象.DisablePowerSave()

def 系统_关闭屏护(大漠对象) :
    return 大漠对象.DisableScreenSave()

def 系统_取CPU使用率(大漠对象) :
    return 大漠对象.GetCpuUsage()

def 系统_取CPU类型(大漠对象) :
    return 大漠对象.GetCpuType()

def 系统_取DPI(大漠对象) :
    return 大漠对象.GetDPI()

def 系统_取UAC(大漠对象) :
    return 大漠对象.CheckUAC()

def 系统_取vt状态(大漠对象) :
    return 大漠对象.IsSurrpotVt()

def 系统_取位数(大漠对象) :
    return 大漠对象.Is64Bit()

def 系统_取内存使用率(大漠对象) :
    return 大漠对象.GetMemoryUsage()

def 系统_取剪辑板内容(大漠对象) :
    return 大漠对象.GetClipboard()

def 系统_取北京时间(大漠对象) :
    return 大漠对象.GetNetTime()

def 系统_取北京时间Ex(大漠对象,ip) :
    return 大漠对象.GetNetTimeByIp(ip)

def 系统_取北京时间S(大漠对象) :
    return 大漠对象.GetNetTimeSafe()

def 系统_取字体平滑(大漠对象) :
    return 大漠对象.CheckFontSmooth()

def 系统_取屏幕宽度(大漠对象) :
    return 大漠对象.GetScreenWidth()

def 系统_取屏幕高度(大漠对象) :
    return 大漠对象.GetScreenHeight()

def 系统_取显卡信息(大漠对象) :
    return 大漠对象.GetDisplayInfo()

def 系统_取机器码(大漠对象) :
    return 大漠对象.GetMachineCode()

def 系统_取机器码_无mac(大漠对象) :
    return 大漠对象.GetMachineCodeNoMac()

def 系统_取版本号(大漠对象) :
    return 大漠对象.GetOsBuildNumber()

def 系统_取硬盘修正版本(大漠对象,index) :
    return 大漠对象.GetDiskReversion(index)

def 系统_取硬盘厂商(大漠对象,index) :
    return 大漠对象.GetDiskModel(index)

def 系统_取硬盘序列号(大漠对象,index) :
    return 大漠对象.GetDiskSerial(index)

def 系统_取类型(大漠对象) :
    return 大漠对象.GetOsType()

def 系统_取系统信息(大漠对象,tpe,method) :
    return 大漠对象.GetSystemInfo(tpe,method)

def 系统_取系统路径(大漠对象,tpe) :
    return 大漠对象.GetDir(tpe)

def 系统_取编码(大漠对象) :
    return 大漠对象.GetLocale()

def 系统_取色深(大漠对象) :
    return 大漠对象.GetScreenDepth()

def 系统_取运行时间(大漠对象) :
    return 大漠对象.GetTime()

def 系统_字体平滑关闭(大漠对象) :
    return 大漠对象.DisableFontSmooth()

def 系统_字体平滑开启(大漠对象) :
    return 大漠对象.EnableFontSmooth()

def 系统_延时(大漠对象,mis) :
    return 大漠对象.Delay(mis)

def 系统_延时Ex(大漠对象,min_s,max_s) :
    return 大漠对象.Delays(min_s,max_s)

def 系统_整数64转32(大漠对象,v) :
    return 大漠对象.Int64ToInt32(v)

def 系统_电源设置(大漠对象) :
    return 大漠对象.DisableCloseDisplayAndSleep()

def 系统_置UAC(大漠对象,uac) :
    return 大漠对象.SetUAC(uac)

def 系统_置任务栏(大漠对象,hwnd,is_show) :
    return 大漠对象.ShowTaskBarIcon(hwnd,is_show)

def 系统_置剪辑板文本(大漠对象,data) :
    return 大漠对象.SetClipboard(data)

def 系统_置屏幕(大漠对象,width,height,depth) :
    return 大漠对象.SetScreen(width,height,depth)

def 系统_置硬件加速(大漠对象,level) :
    return 大漠对象.SetDisplayAcceler(level)

def 系统_置编码(大漠对象) :
    return 大漠对象.SetLocale()

def 系统_置警报(大漠对象,fre,delay) :
    return 大漠对象.Beep(fre,delay)

def 系统_运行应用(大漠对象,path,mode) :
    return 大漠对象.RunApp(path,mode)

def 系统_退出(大漠对象,tpe) :
    return 大漠对象.ExitOs(tpe)

def 系统_音乐停止(大漠对象,id) :
    return 大漠对象.Stop(id)

def 系统_音乐播放(大漠对象,file_name) :
    return 大漠对象.Play(file_name)

def 绘制_gif(大漠对象,hwnd,x,y,pic_name,repeat_limit,delay) :
    return 大漠对象.FoobarStartGif(hwnd,x,y,pic_name,repeat_limit,delay)

def 绘制_gif停止(大漠对象,hwnd,x,y,pic_name) :
    return 大漠对象.FoobarStopGif(hwnd,x,y,pic_name)

def 绘制_关闭(大漠对象,hwnd) :
    return 大漠对象.FoobarClose(hwnd)

def 绘制_刷新(大漠对象,hwnd) :
    return 大漠对象.FoobarUpdate(hwnd)

def 绘制_图像(大漠对象,hwnd,x,y,pic,trans_color) :
    return 大漠对象.FoobarDrawPic(hwnd,x,y,pic,trans_color)

def 绘制_圆角矩形(大漠对象,hwnd,x,y,w,h,rw,rh) :
    return 大漠对象.CreateFoobarRoundRect(hwnd,x,y,w,h,rw,rh)

def 绘制_填充矩形(大漠对象,hwnd,x1,y1,x2,y2,color) :
    return 大漠对象.FoobarFillRect(hwnd,x1,y1,x2,y2,color)

def 绘制_文字(大漠对象,hwnd,x,y,w,h,text,color,align) :
    return 大漠对象.FoobarDrawText(hwnd,x,y,w,h,text,color,align)

def 绘制_文本(大漠对象,hwnd,text,color) :
    return 大漠对象.FoobarPrintText(hwnd,text,color)

def 绘制_椭圆(大漠对象,hwnd,x,y,w,h) :
    return 大漠对象.CreateFoobarEllipse(hwnd,x,y,w,h)

def 绘制_清除文本(大漠对象,hwnd) :
    return 大漠对象.FoobarClearText(hwnd)

def 绘制_矩形(大漠对象,hwnd,x,y,w,h) :
    return 大漠对象.CreateFoobarRect(hwnd,x,y,w,h)

def 绘制_线条(大漠对象,hwnd,x1,y1,x2,y2,color,style,width) :
    return 大漠对象.FoobarDrawLine(hwnd,x1,y1,x2,y2,color,style,width)

def 绘制_置保存(大漠对象,hwnd,file_name,en,header) :
    return 大漠对象.FoobarSetSave(hwnd,file_name,en,header)

def 绘制_置字体(大漠对象,hwnd,font_name,size,flag) :
    return 大漠对象.FoobarSetFont(hwnd,font_name,size,flag)

def 绘制_置文本范围(大漠对象,hwnd,x,y,w,h) :
    return 大漠对象.FoobarTextRect(hwnd,x,y,w,h)

def 绘制_置文本行距(大漠对象,hwnd,gap) :
    return 大漠对象.FoobarTextLineGap(hwnd,gap)

def 绘制_置文本输出方向(大漠对象,hwnd,dir) :
    return 大漠对象.FoobarTextPrintDir(hwnd,dir)

def 绘制_置透明(大漠对象,hwnd,trans,color,sim) :
    return 大漠对象.FoobarSetTrans(hwnd,trans,color,sim)

def 绘制_自定义(大漠对象,hwnd,x,y,pic,trans_color,sim) :
    return 大漠对象.CreateFoobarCustom(hwnd,x,y,pic,trans_color,sim)

def 绘制_鼠标解锁(大漠对象,hwnd) :
    return 大漠对象.FoobarUnlock(hwnd)

def 绘制_鼠标锁定(大漠对象,hwnd) :
    return 大漠对象.FoobarLock(hwnd)

def 释放dm(大漠对象) :
    return 大漠对象.释放()

def 键盘_单击(大漠对象,vk) :
    return 大漠对象.KeyPress(vk)

def 键盘_单击Char(大漠对象,key_str) :
    return 大漠对象.KeyPressChar(key_str)

def 键盘_单击Str(大漠对象,key_str,delay) :
    return 大漠对象.KeyPressStr(key_str,delay)

def 键盘_取状态(大漠对象,vk) :
    return 大漠对象.GetKeyState(vk)

def 键盘_弹起(大漠对象,vk) :
    return 大漠对象.KeyUp(vk)

def 键盘_弹起Char(大漠对象,key_str) :
    return 大漠对象.KeyUpChar(key_str)

def 键盘_按住(大漠对象,vk) :
    return 大漠对象.KeyDown(vk)

def 键盘_按住Char(大漠对象,key_str) :
    return 大漠对象.KeyDownChar(key_str)

def 键盘_等待按键(大漠对象,key_code,time_out) :
    return 大漠对象.WaitKey(key_code,time_out)

def 键盘_置延时(大漠对象,tpe,delay) :
    return 大漠对象.SetKeypadDelay(tpe,delay)

def 鼠标_单击中键(大漠对象) :
    return 大漠对象.MiddleClick()

def 鼠标_单击右键(大漠对象) :
    return 大漠对象.RightClick()

def 鼠标_单击左键(大漠对象) :
    return 大漠对象.LeftClick()

def 鼠标_双击左键(大漠对象) :
    return 大漠对象.LeftDoubleClick()

def 鼠标_取位置(大漠对象) :
    return 大漠对象.GetCursorPos()

def 鼠标_取热点坐标(大漠对象) :
    return 大漠对象.GetCursorSpot()

def 鼠标_取特征码(大漠对象) :
    return 大漠对象.GetCursorShape()

def 鼠标_取特征码Ex(大漠对象,tpe) :
    return 大漠对象.GetCursorShapeEx(tpe)

def 鼠标_取速度(大漠对象) :
    return 大漠对象.GetMouseSpeed()

def 鼠标_弹起中键(大漠对象) :
    return 大漠对象.MiddleUp()

def 鼠标_弹起右键(大漠对象) :
    return 大漠对象.RightUp()

def 鼠标_弹起左键(大漠对象) :
    return 大漠对象.LeftUp()

def 鼠标_按住中键(大漠对象) :
    return 大漠对象.MiddleDown()

def 鼠标_按住右键(大漠对象) :
    return 大漠对象.RightDown()

def 鼠标_按住左键(大漠对象) :
    return 大漠对象.LeftDown()

def 鼠标_滚轮上滚(大漠对象) :
    return 大漠对象.WheelUp()

def 鼠标_滚轮下滚(大漠对象) :
    return 大漠对象.WheelDown()

def 鼠标_相对移动(大漠对象,rx,ry) :
    return 大漠对象.MoveR(rx,ry)

def 鼠标_移动E(大漠对象,x,y) :
    return 大漠对象.MoveTo(x,y)

def 鼠标_移动Ex(大漠对象,x,y,w,h) :
    return 大漠对象.MoveToEx(x,y,w,h)

def 鼠标_置延时(大漠对象,tpe,delay) :
    return 大漠对象.SetMouseDelay(tpe,delay)

def 鼠标_置模式(大漠对象,mode) :
    return 大漠对象.SetSimMode(mode)

def 鼠标_置精确度(大漠对象,en) :
    return 大漠对象.EnableMouseAccuracy(en)

def 鼠标_置速度(大漠对象,speed) :
    return 大漠对象.SetMouseSpeed(speed)