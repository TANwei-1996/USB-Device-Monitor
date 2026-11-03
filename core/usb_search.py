"""
USB设备扫描核心逻辑
作者：TANYI
日期：2026-07-02
修改记录：
    2026-07-02：v0.1.2 (fix/v0.1.2-core-scan) ：
    - 一次提取父链层的VID/PID信息, 无需递归查询子设备 - 规避检索全为null的问题
"""

import re
import json
import subprocess
from utils import setup_logger
from typing import List, Dict, Tuple
from .search_audio import check_audio_dir

# 调用函数setup_logger初始化日志模块
log = setup_logger(__name__)

# 判断USB设备节点
USB_VID_PATTERN = re.compile(r'VID_[0-9A-Fa-f]{4}', re.I)


def split_vid_pid(device_id: str) -> Tuple[str, str]:
    """
    获取设备VIP PID信息
    :param device_id: 设备id信息
    :return:
    """
    if not device_id:
        return "None：未知", "None：未知"

    vid = "None：未知"
    pid = "None：未知"
    # 正则匹配VID_后四位
    m_vid = re.search(r'VID_([0-9A-Fa-f]{4})', device_id, re.I)
    if m_vid:
        vid = m_vid.group(1).upper()

    # 正则匹配PID_后四位
    m_pid = re.search(r'PID_([0-9A-Fa-f]{4})', device_id, re.I)
    if m_pid:
        pid = m_pid.group(1).upper()

    return vid, pid


def check_audio_endpoint() -> List[Dict]:
    """
      确认音频设备端点（包含父链层）
      :param:
      :return: [{"name": 端点名, "endpoint": 端点ID, "status": 状态, "chain": [L0, L1, ..., L4]}]
    """
    power_shell_script_01 = (
        "Get-PnpDevice -Class AudioEndpoint -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Status -eq 'OK' } | "
        "ForEach-Object { "
        "$name = $_.FriendlyName; $ep = $_.InstanceId; $st = $_.Status; "
        "$id = $ep; $lvl = 0; $chain = @(); "
        "while ($id -and $lvl -lt 5) { "
        "$chain += $id; "
        "$id = (Get-PnpDeviceProperty -InstanceId $id "
        "-KeyName 'DEVPKEY_Device_Parent' -ErrorAction SilentlyContinue).Data; "
        "$lvl++ }; "
        "[PSCustomObject]@{ name = $name; endpoint = $ep; status = $st; chain = $chain } } | "
        "ConvertTo-Json -Compress -Depth 3"
    )
    res = subprocess.run(
        ["powershell", "-NoProfile", "-Command", power_shell_script_01],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=20,
    )
    output = (res.stdout or "").strip()
    if not output:
        return []
    
    data = json.loads(output)
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return []
    

    for item in data:
        # 获取节点VID/PID信息
        chain = item.get('chain', [])
        if isinstance(chain, str):
            item['chain'] = [chain]
        elif not isinstance(chain, list):
            item['chain'] = []
    return data

def seach_usb_chaindevice(chain: List[str]):
    """
    搜索USB设备父链层VID/PID信息
    :param chain: 父层端点信息
    :return:USB设备信息(InstanceId)
    """
    for c in chain:
        if not c:
            continue
        if c.upper().startswith("USB\\") and USB_VID_PATTERN.search(c):
            return c
    return None

def scan_usb_devices(connected_audio=False) -> List[Dict]:
    """
    扫描USB设备
    返回设备字典列表
    :param connected_audio: 是否关联音频子设备
    :return: USB字典列表 -  FriendlyName / InstanceId / Status / VID / PID / audio_children
    """
    log.info("搜索USB设备...")
    try:
        # 尝试运行父层检索
        items = check_audio_endpoint()
        if not items:
            return []
    # 处理异常：针对超时、JSON解析错误、其他异常，并实施打印日志
    except subprocess.TimeoutExpired:
        log.error(f" --- 搜索超时，执行超时 ---")
        return []
    except json.JSONDecodeError:
        log.error(f" --- JSON解析错误 ---")
        return []
    except Exception as e:
        log.error(f"搜索异常：{e} ---")
        return []
    if not items:
        return []

    # 分层级逐步打印记录端点信息
    if not connected_audio:
        # 创建空列表，用来存放设备信息
        devices = []
        for item in items:
            # 获取不到endpoint，直接返回“ ”
            point = item.get('endpoint', " ")
            vid, pid = split_vid_pid(point)
            devices.append({
                # 设备名
                'FriendlyName': item.get('name'),
                # 设备ID
                'InstanceId': point,
                # 设备状态
                'Status': item.get('status') or 'None',
                # 设备vid、pid
                'VID': vid,
                'PID': pid,
            })
        # 返回列表设备信息
        return devices
    # 按照 USB 根节点下的设备整合音频子设备
    grouped: Dict[str, Dict] = {}   # 主条目
    loose: List[Dict] = []          # 上溯不到 USB 根的端点（板载/显示器音频）
    for item in items:
        name = item.get('name') or '未知'
        point = item.get('endpoint') or ""
        status = item.get('status') or 'None'
        chain = item.get('chain') or []

        # 将某个端点作为一个功能
        child = {
            "name": name,
            "direction": check_audio_dir(name),
            "status": status,
        }
        # 搜索USB设备父链层VID/PID信息
        usb_root = seach_usb_chaindevice(chain)
        # 非usb设备，直接加入loose
        if not usb_root:
            loose.append({
                'FriendlyName': name,
                'InstanceId': point,
                'Status': status,
                'VID': "None：未知",
                'PID': "None：未知",
                'audio_children': [child],
            })
            continue

        # 作为首次遇到该 USB 设备的处理方式
        if usb_root not in grouped:
            vid, pid = split_vid_pid(usb_root)
            grouped[usb_root] = {
                'FriendlyName': name,
                'InstanceId': usb_root,
                'Status': status,
                'VID': vid,
                'PID': pid,
                'audio_children': [],
            }
        # 添加grouped中
        grouped[usb_root]['audio_children'].append(child)

    devices = list(grouped.values()) + loose
    log.info(f"扫描完成，搜索出 {len(devices)} 个设备")
    return devices

if __name__ == '__main__':
    devs = scan_usb_devices(connected_audio=True)
    for d in devs:
        name = d.get('FriendlyName') or '未知'
        print(f"{name} | VID:{d['VID']} PID:{d['PID']}")
        for c in d.get('audio_children') or []:
            print(f"======》 [{c['direction']}] {c['name']}")
