"""
USB设备数据结构
作者：TANYI
日期：2026-07-02
"""

from dataclasses import dataclass, asdict
from typing import Optional, List, Dict


@dataclass
class USBDeviceInfo:
    """单个USB设备的信息"""
    friendly_name: str
    instance_id: str
    vid: str
    pid: str
    status: str
    device_type: Optional[str] = None
    audio_children: Optional[List[Dict]] = None

    def to_dict(self) -> Dict:
        return asdict(self)


class DeviceList:
    """设备封装"""
    # 实例化对象devices
    def __init__(self, devices: List[USBDeviceInfo] = None):
        self.devices = devices or []

    def __len__(self) -> int:
        return len(self.devices)

