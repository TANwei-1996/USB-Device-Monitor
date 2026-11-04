"""
音频设备具体到麦克风和扬声器
作者：TANYI
日期：2026-07-02
修改记录：
    2026-11-03：v0.1.2 (fix/v0.1.2-core-scan) ：
    - 修复GBK硬编码乱码；
    - 删除scan_audio_devices(数据源)，端点枚举改由usb_search父链查询实现一致性；
    2026-11-04：v0.1.3 (fix/v0.1.3) - 优化日志打印类型为error
    
"""
from utils import setup_logger

# 日志模块初始化
log = setup_logger(__name__)

def check_audio_dir(name:str) -> str:
    """
    确认设备是输入还是输出
    :param name: 设备名称
    :return: 音频输入、音频输出、音频设备
    """

    if not name:
        return "None"

    n = name.lower()

    try:
        # 输入名称检索
        if ('microphone' in n) or ('mic' in n) or ('麦克风' in name):
            return "音频输入"

        # 输出名称检索
        if ('speaker' in n) or ('headphone' in n) or ('耳机' in name) or ('扬声器' in name):
            return "音频输出"

        return "音频设备"
    except Exception as e:
        log.error(f"输入输出设备检索异常：{e}")
        return "音频设备"