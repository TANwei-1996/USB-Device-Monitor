"""
USB设备数据结构
作者：TANYI
日期：2026-07-02
"""

from utils import device_type
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict


@dataclass(slots=True) # 开启slots  优化内存占用
class USBDeviceInfo:
    """单个USB设备的信息"""
    friendly_name: str
    instance_id: str
    vid: str
    pid: str
    status: str
    device_type: Optional[str] = None
    audio_children: Optional[List[Dict]] = None

    def __post_init__(self):
        # 必填文本字段：不能为空 / None
        for name in ("friendly_name", "instance_id"):
            value = getattr(self, name)
            if value is None or not str(value).strip():
                raise ValueError(f"USBDeviceInfo.{name} 不能为空或 None")

        # VID/PID 允许"None：未知"，不允许 None / 空串
        for name in ("vid", "pid"):
            value = getattr(self, name)
            if value is None or not str(value).strip():
                raise ValueError(f"USBDeviceInfo.{name} 不能为 None 或空字符串")

        # 音频子设备必须是列表，防止传 dict/str 导致下游遍历出错
        if self.audio_children is not None and not isinstance(self.audio_children, list):
            raise TypeError(
                f"USBDeviceInfo.audio_children 必须是 list 或 None"
                f"实际类型 {type(self.audio_children).__name__}"
            )

    def to_dict(self) -> Dict:
        return asdict(self)


class DeviceList:
    """设备封装"""
    # 实例化对象devices
    def __init__(self, devices: List[USBDeviceInfo] = None):
        self.devices = devices or []

    def __len__(self) -> int:
        return len(self.devices)

