"""
USB设备扫描核心逻辑
作者：TANYI
日期：2026-07-02
"""

import re
import json
import subprocess
from utils import setup_logger
from typing import List, Dict, Tuple
from .search_audio import scan_audio_devices, check_audio_dir

# 调用函数setup_logger
log = setup_logger(__name__)


def split_vid_pid(device_id: str) -> Tuple[str, str]:
    """
    获取设备VIP PID信息
    :param device_id: 设备id信息
    :return:
    """
    if not device_id:
        return "N/A", "N/A"

    # 正则匹配VID_后四位
    m_vid = re.search(r'VID_([0-9A-Fa-f]{4})', device_id, re.I)
    if m_vid:
        vid = m_vid.group(1).upper()
    else:
        vid = "N/A"

    # 正则匹配PID_后四位
    m_pid = re.search(r'PID_([0-9A-Fa-f]{4})', device_id, re.I)
    if m_pid:
        pid = m_pid.group(1).upper()
    else:
        pid = "N/A"

    return vid, pid


def scan_usb_devices(connected_audio=False) -> List[Dict]:
    """
    扫描USB设备
    返回设备字典列表
    :param connected_audio: 是否关联音频子设备
    """
    log.info("搜索USB设备...")

    # 扫描设备管理器：音频输入输出设备相关信息
    cmd = (
        'powershell -NoProfile -Command '
        '"Get-PnpDevice -Class AudioEndpoint -ErrorAction SilentlyContinue | '
        'Where-Object { $_.Status -eq \'OK\' } | '
        'Select-Object FriendlyName, InstanceId, Status | '
        'ConvertTo-Json -Compress"'
    )

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='gbk',
            errors='ignore',
            timeout=10,
        )

        output = (result.stdout or "").strip()
        if not output:
            return []

        data = json.loads(output)

        if isinstance(data, dict):
            devices = [data]
        elif isinstance(data, list):
            devices = data
        else:
            return []

        for out_d in devices:
            dev_out_id = out_d.get('InstanceId') or d.get('instanceId') or ""
            vid, pid = split_vid_pid(dev_out_id)
            d['VID'] = vid
            d['PID'] = pid

        # 判断：不关联时直接返回
        if not connected_audio:
            return devices

        # 创建空字典，用来存放设备信息
        audio_dict = {}
        # 关联设备:定义变量 audio
        audio_dev = scan_audio_devices()
        for a_d in audio_dev:
            parent_dev_id = a_d.get('ParentInstanceId', "")  # 未找到，返回 null
            if parent_dev_id not in audio_dict:
                audio_dict[parent_dev_id] = []

            audio_dict[parent_dev_id].append(
                {
                    "name": a_d.get('FriendlyName', 'None'),
                    "direction": check_audio_dir(a_d.get('FriendlyName', ' ')),
                    "status": a_d.get('Status', 'None'),
                }
            )

        # 添加具体的音频信息到整体devices
        for usb_dev in audio_dev:
            usb_id = usb_dev.get('InstanceId') or usb_dev.get('instanceId') or ""
            # 父类id和分支下的设备id匹配
            match_aud = []
            for parent_dev_id, a_list in audio_dict.items():
                if not parent_dev_id:
                    continue
                if usb_id in parent_dev_id:
                    match_aud.extend(a_list)
            usb_dev['audio_children'] = match_aud

        log.info(f"扫描完成，发现 {len(devices)} 个设备")
        return devices

    except subprocess.TimeoutExpired:
        log.error("PowerShell执行超时")
        return []
    except json.JSONDecodeError:
        log.error("JSON解析失败")
        return []
    except Exception as e:
        log.exception(f"扫描异常:{e}")
        return []


if __name__ == '__main__':
    devs = scan_usb_devices()
    for d in devs:
        name = d.get('FriendlyName') or '未知'
        print(f"{name} | VID:{d['VID']} PID:{d['PID']}")
