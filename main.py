"""
USB设备监控器 - 主程序
作者：TANYI
2026-07-02
"""

import sys
from pathlib import Path
from core.usb_search import scan_usb_devices
from utils import (
    setup_logger,
    print_device_list,
    # guess_vendor,
    device_type,
    safe_str,
)
from models.usb_devices_info import USBDeviceInfo, DeviceList

PROJECT_PATH = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_PATH))

# 调用日志模块
log = setup_logger("main")


def build_devices(raw_list):
    """把扫描出来的原始数据转成对象"""
    result = []
    for d in raw_list:
        name = safe_str(d.get('FriendlyName') or d.get('friendlyName'))
        iid = safe_str(d.get('InstanceId') or d.get('instanceId'))
        status = safe_str(d.get('Status'))
        vid = safe_str(d.get('VID'))
        pid = safe_str(d.get('PID'))

        result.append(USBDeviceInfo(
            friendly_name=name,
            instance_id=iid,
            vid=vid,
            pid=pid,
            status=status,
            device_type=device_type(name),
            # vendor_name=guess_vendor(vid),
        ))
    return DeviceList(devices=result)


def show_details(d_list):
    """
    输出设备信息 --- 到子设备列表中
    """
    print("=" * 30 +  " 设备信息 "  + "=" * 30)


    # 设备列表
    for i, d in enumerate(d_list.devices, 1):
        print(f"\n[{i}] {d.friendly_name}")
        # print(f"    类型: {d.device_type}")
        # print(f"    厂商: {d.vendor_name}")
        print(f"    VID:  {d.vid}")
        print(f"    PID:  {d.pid}")
        #显示分支下的音频设备
        if hasattr(d, 'audio_children') and d.audio_children:
            print(f"    音频功能:")
            for audio in d.audio_children:
                print(f"      - [{audio['direction']}] {audio['name']}")

        print(f"    状态: {d.status}")

def main():
    print("=" * 70)
    print("  USB设备监控器  v0.1.0")
    print("=" * 70)
    print()

    try:
        print("正在搜索USB设备...")
        devices = scan_usb_devices()

        if not devices:
            print("无USB设备接入")
            return 0

        print(f"找到 {len(devices)} 个设备")
        print_device_list(devices)

        dev_list = build_devices(devices)
        show_details(dev_list)

        log.info("运行结束")
        return 0
    except KeyboardInterrupt:
        print("\n已取消")
        return 0
    except Exception as e:
        log.exception(f"程序运行异常：{e}")
        return 1


if __name__ == '__main__':
    devices = scan_usb_devices(connected_audio=True)
    sys.exit(main())
