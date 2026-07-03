"""
辅助函数
作者：TANYI
日期：2026-07-02
"""

from typing import Any, List, Dict, Optional

def safe_str(value:str, default="None") -> str:
    """防止None报错"""
    if value is None:
        return default
    if isinstance(value, str) and value.strip():
        return value
    if not isinstance(value, str):
        return str(value)
    return default


def print_device_list(devices: List[Dict]) -> None:
    """打印设备列表"""
    if not devices:
        print("无设备")
        return

    print()
    print("-" * 75)
    print(f"{'序号':<5} {'设备名称':<35} {'VID':<8} {'PID':<8} {'状态':<10}")
    print("-" * 75)

    for i, dev in enumerate(devices, 1):
        name = safe_str(dev.get('FriendlyName') or dev.get('friendlyName'))
        vid = safe_str(dev.get('VID'))
        pid = safe_str(dev.get('PID'))
        status = safe_str(dev.get('Status'))

        if len(name) > 33:
            name = name[:30] + "..."

        print(f"{i:<5} {name:<35} {vid:<8} {pid:<8} {status:<10}")

    print("-" * 75)

def device_type(name: Optional[str]) -> str:
    """获取设备类型"""
    if not name:
        return "None"

    n = name.lower()

    if 'audio' in n or 'sound' in n or '声卡' in name:
        return "音频设备"
    if 'camera' in n or 'webcam' in n or '摄像' in name:
        return "视频设备"
    if 'storage' in n or 'disk' in n or '存储' in name:
        return "存储设备"
    if 'hub' in n or '集线器' in name:
        return "USB集线器"
    if 'keyboard' in n or '键盘' in name:
        return "键盘"
    if 'mouse' in n or '鼠标' in name:
        return "鼠标"
    if 'bluetooth' in n or '蓝牙' in name:
        return "蓝牙设备"

    return "其他设备"
