"""
音频设备具体到麦克风和扬声器
作者：TANYI
日期：2026-07-02
"""
import sys
import json
import subprocess
from typing import List, Dict
from utils import setup_logger

# 日志模块初始化
log = setup_logger(__name__)
# 编解码判定
encode = "gbk" if sys.platform == "win32" else "utf-8"
def scan_audio_devices() -> List[Dict]:
    """
    扫描音频输入/输出设备
    返回设备列表
    """
    log.info("="*30 + " 搜索音频设备 " + "="*30)

    # 获取：FriendlyName, InstanceId, ParentInstanceId, Status
    cmd = (
        'powershell -NoProfile -Command '
        '"Get-PnpDevice -Class AudioEndpoint -ErrorAction SilentlyContinue | '
        'Where-Object { $_.Status -eq \'OK\' } | '
        'Select-Object FriendlyName, InstanceId, ParentInstanceId, Status | '
        'ConvertTo-Json -Compress"'
    )

    try:
        res = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
            encoding=encode,
            errors='ignore',
        )
        output = (res.stdout or '').strip()
        if not output:
            return []

        data = json.loads(output)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
        return []
    except Exception as e:
        log.info (f"音频搜索异常：{e}")
        return []

def check_audio_dir(dir_name:str):
    """
    确认设备是输入还是输出
    :param dir_name:
    :return:
    """

    if not dir_name:
        return "None"

    n = dir_name.lower()

    try:
        # 输入名称检索
        if ('microphone' in n) or ('mic' in n) or ('麦克风' in dir_name):
            return "音频输入"

        # 输出名称检索
        if ('speaker' in n) or ('headphone' in n) or ('耳机' in dir_name) or ('扬声器' in dir_name):
            return "音频输出"

        return "音频设备"
    except Exception as e:
        log.info(f"输入输出设备检索异常：{e}")


if __name__ == '__main__':
    d = scan_audio_devices()
    for d in d:
        # 如果未获取到，直接 “None”返回
        name = d.get('FriendlyName', 'None')
        audio_dir = check_audio_dir(name)
        # 总分支设备（父类设备）
        parent = d.get('ParentInstanceId', 'None：无父类设备')
        print(f"[{audio_dir}]{name}")
        print(f"父类设备：{parent}")