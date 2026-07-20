"""
USB设备监控器 - 核心包
作者：TANYI
日期：2026-07-02
"""

from .usb_search import (
    scan_usb_devices,
    split_vid_pid,
    scan_audio_devices,
    check_audio_dir,
)

from .audio_stream import (
    audio_dev_list,
    find_mic_by_name,
    select_input_device,
    get_samplerate,
    test_mic,
    monitor_realtime,
)

__all__ = [
    "scan_usb_devices",
    "split_vid_pid",
    "scan_audio_devices",
    "check_audio_dir",
    "audio_dev_list",
    "find_mic_by_name",
    "select_input_device",
    "get_samplerate",
    "test_mic",
    "monitor_realtime",
]
