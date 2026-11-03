"""
USB设备监控器
作者：TANYI
日期：2026-07-02
修改记录：
    2026-11-03：v0.1.2 (fix/v0.1.2-core-scan) - 修改逻辑，一次性搜索出所有USB设备，包括音频设备
"""

from .usb_search import scan_usb_devices, split_vid_pid, check_audio_dir

__all__ = ["scan_usb_devices", "split_vid_pid", "check_audio_dir"]
