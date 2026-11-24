"""
音频流采集
作者: TANYI
日期: 2026-11-23
修改记录：
    2026-11-23: 实现设备索引匹配 + InputStream 回调骨架
    2026-11-23: 整理设备索引匹配逻辑，修复设备属性读取及重复代码问题
"""

import re
import sys
from pathlib import Path
from typing import Optional
from types import ModuleType
import numpy as np

# 获取项目根目录
PROJECT_PATH = Path(__file__).resolve().parent.parent
if str(PROJECT_PATH) not in sys.path:
    sys.path.insert(0, str(PROJECT_PATH))

from utils import setup_logger
from models import AllExceptionError

# 实例化 logger 对象
logger = setup_logger(__name__)

# 封装懒加载sounddevice模块，避免在导入时抛出异常
def _req_sounddevice() -> ModuleType:
    """懒加载 sounddevice 模块，若失败则抛出运行时异常。"""

    try:
        import sounddevice as sd

    except ImportError as e:
        raise AllExceptionError(
            "sounddevice模块未安装"
        ) from e

    return sd

def _get(dev, key, default=0):
    """
    获取音频设备的sounddevice索引,规避isinstance判断异常
    :param dev: 音频设备对象
    :param key: 音频设备属性"name"或"type"
    :param default: 默认值, 若未找到则返回default
    :return: 音频设备属性值; 若未找到则返回default
    """
    # 判定是否为字典类型，若不是则通过属性方式获取
    if isinstance(dev, dict):
        return dev.get(key, default)

    return getattr(dev, key, default)


def _strip_detail(name: str) -> str:
    """去掉设备名称最后一对括号及其内容。"""

    # 去掉最后一对括号及其内容："麦克风 (Realtek)" → "麦克风"
    return re.sub(r"\s*\([^()]*\)\s*$", "", str(name)).strip()


def _strip_name(name: str) -> str:
    """
    做模糊匹配，去除音频设备名称中的空格和特殊字符
    :param name: 音频设备名称
    :return: 去除空格和特殊字符后的音频设备名称
    """
    return re.sub(
        r"[^\w]",
        "",
        str(name).strip(),
        flags=re.UNICODE
    )


def _query_audio_devices():
    """懒加载 sounddevice 并枚举系统音频设备。"""

    # 调用懒加载sounddevice模块，若失败则抛出运行时异常
    sd = _req_sounddevice()

    # 调用上层模块，获取所有音频设备(all_devices)信息列表
    # 做双层异常捕获，避免直接抛出PortAudioError异常
    try:
        all_devices = sd.query_devices()

    except sd.PortAudioError as e:
        raise AllExceptionError(
            "sounddevice 初始化失败,PortAudio/音频驱动异常"
        ) from e

    except Exception as e:
        raise AllExceptionError(
            f"sounddevice查询设备未知异常:{e}"
        ) from e

    # 判定是否查询到音频设备
    if not all_devices:
        return sd, []

    return sd, all_devices


def _resolve_device_index(friendly_name: str, direction: str, raise_if_empty: bool = False) -> Optional[int]:

    """统一执行设备方向过滤、名称匹配和系统默认设备兜底。"""

    sd, all_devices = _query_audio_devices()

    if not all_devices:

        if raise_if_empty:
            raise AllExceptionError(
                "sounddevice 查询失败,未找到音频设备"
            )

        logger.warning("sounddevice 枚举到 0 个音频设备")       
        return None

    # 按 direction 先过滤通道方向
    want_input = direction in ("音频输入", "input")

    if direction not in ("音频输入","音频输出","input","output"):
        raise ValueError(
            "direction 必须是 '音频输入'、'音频输出'、'input' 或 'output'"
        )

    candidates = []
    audio_candidate = candidates

    for dev in all_devices:

        # 通过对输入输出通道数量是否大于0，判定是否为音频设备
        inp_channels = _get(
            dev,
            "max_input_channels",
            0
        )

        out_channels = _get(
            dev,
            "max_output_channels",
            0
        )

        if want_input and inp_channels > 0:
            audio_candidate.append(dev)

        elif not want_input and out_channels > 0:
            audio_candidate.append(dev)

    if not audio_candidate:

        logger.warning(
            f"direction={direction} 在 sounddevice 中没有候选设备"
        )

        if raise_if_empty:
            raise AllExceptionError(                
                f"未找到{direction}音频输入或输出通道的设备"
            )

        return None

    # 模糊匹配

    clean_key = str(friendly_name or "").strip()

    clean_key_no_detail = _strip_detail(
        clean_key
    )

    clean_key_normalized = _strip_name(
        clean_key
    ).casefold()

    for dev in audio_candidate:

        dev_name = str(
            _get(dev, "name", "") or ""
        ).strip()

        dev_index = _get(
            dev,
            "index",
            -1
        )

        dev_idx = dev_index

        dev_name_normalized = _strip_name(
            dev_name
        ).casefold()

        # 三层匹配：
        # a) 完整名子串包含  → 命中就返回
        # b) 去括号版本子串包含
        # c) 反过来 sd 名字在 friendly_name 里 (sd 名字可能更短)

        if clean_key and clean_key.casefold() in dev_name.casefold():

            logger.info(
                f"名称匹配 (完整): '{friendly_name}' "      
                f"→ index={dev_idx} '{dev_name}'"
            )

            return dev_idx

        if (
            clean_key_no_detail
            and clean_key_no_detail.casefold() in dev_name.casefold()
        ):

            logger.info(
                f"名称匹配 (去括号): '{clean_key_no_detail}' "
                f"→ index={dev_idx} '{dev_name}'"
            )

            return dev_idx

        if (
            dev_name
            and dev_name.casefold() in clean_key.casefold()
        ):

            logger.info(
                f"名称匹配 (反转): '{dev_name}' "
                f"在 '{friendly_name}' 里 → index={dev_idx}"
            )

            return dev_idx

        # 去除空格和特殊字符后的匹配，兼容不同系统的设备名称格式

        if (
            clean_key_normalized
            and clean_key_normalized == dev_name_normalized
        ):
            logger.info(
                f"名称匹配 (标准化): '{friendly_name}' "
                f"→ index={dev_idx} '{dev_name}'"
            )

            return dev_idx

        # 名字都没匹配到，返回系统默认设备

    try:

        default_in, default_out = sd.default.device

        fallback_idx = (
            default_in if want_input else default_out           
        )
    
    except Exception as e:
        logger.warning(
            f"读取系统默认音频设备失败: {e}"
        )

        fallback_idx = None

    for dev in audio_candidate:

        dev_idx = _get(
            dev,
            "index",
            -1
        )

        dev_name = _get(
            dev,
            "name",
            ""
        )

        if (
            fallback_idx is not None
            and dev_idx == fallback_idx
        ):
            logger.warning(
                f"名称未匹配，回退到系统默认 {direction}: "
                f"index={dev_idx} '{dev_name}'"
            )

            return dev_idx

    logger.warning(     
        f"所有匹配策略都没匹配到, "
        f"friendly_name='{friendly_name}', "
        f"direction={direction}"
    )

    return None


def collect_audio_sd_id(
    friendly_name: str,
    direction: str
) -> Optional[int]:

    """
    采集音频设备的sounddevice索引

    :param friendly_name: 音频设备名称
    :param direction: 音频设备通道类型，"input"或"output"
    :return: 音频设备的sounddevice索引; 若未找到则返回None
    """

    if direction not in ("input", "output"):

        raise ValueError(
            "direction 必须是 'input' 或 'output'"
        )

    return _resolve_device_index(
        friendly_name=friendly_name,
        direction=direction,
        raise_if_empty=True
    )


# 将搜索到得设备名切换成对应的索引
def resolve_sd_device_index(
    friendly_name: str,
    direction: str
) -> Optional[int]:

    """
    把 Layer 1 的 friendly_name 翻译成 sounddevice 设备索引

    :param friendly_name: Layer 1 扫描得到的设备名 (USBDeviceInfo.friendly_name)
    :param direction:     "音频输入" 或 "音频输出"（search_audio.check_audio_dir 的返回值）
    :return:              sounddevice 设备索引 (int)，找不到返回 None
    :raises RuntimeError: sounddevice 未安装 / 系统设备查询失败
    """

    # 懒加载 sounddevice，没装就抛出异常
    if direction not in ("音频输入", "音频输出"):
        # 检查 direction 参数是否有效
        raise ValueError(
            "direction 必须是 '音频输入' 或 '音频输出'"
        )

    return _resolve_device_index(
        friendly_name=friendly_name,
        direction=direction,
        raise_if_empty=False
    )


# 创建音频输入流数据
def audio_stream_data(
    device_index: int,
    callback: Callable[[np.ndarray], None],
    channels: int = 1,
    samplerate: int = 44100,
    blocksize: int = 1024,
) -> object:
    """
    创建音频输入流数据，返回 sounddevice.InputStream 对象   
    :param device_index: resolve_sd_device_index 按照搜索到的设备名返回索引,整数型
    :param callback:     每 blocksize 个样本触发一次
                            callback(samples: np.ndarray)
                         samples.shape = (blocksize, channels), dtype=float32
    :param channels:     声道数，默认 1，单声道
    :param samplerate:   采样率，默认 44100Hz
    :param blocksize:    每个 chunk 的样本数，默认 1024个
    :return:             sounddevice.InputStream 对象
    :raises AllExceptionError: 索引无效 / 设备被占用 / 参数不支持等
    """

    # 调用懒加载sounddevice模块，若失败则抛出运行时异常
    sd = _req_sounddevice()

    # sounddevice 原始回调签名
    def _sd_callback(indata, frames, time_info, status):
        # status 有值说明底层丢帧/溢出，打 warning 但不中断
        if status:
            logger.warning(f"sounddevice 回调 status: {status}")
        # 只把 indata 传给用户的 callback
        callback(indata)

    # 创建流
    try:
        stream = sd.InputStream(
            device=device_index,
            channels=channels,
            samplerate=samplerate,
            blocksize=blocksize,
            dtype='float32',
            callback=_sd_callback,
        )
        logger.info(
            f"InputStream 创建成功: device={device_index}, "
            f"channels={channels}, sr={samplerate}, blocksize={blocksize}"
        )
        return stream

    except Exception as e:
        # 统一捕获 PortAudioError / 设备被占用 / 参数不支持 等异常
        raise AllExceptionError(
            f"打开音频流失败 (index={device_index}): {e}"
        ) from e



# ---------------------------------------------------------------------------
# 自测：单独跑 `python core/audio_collection.py` 会执行这段
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    print("=" * 50)
    print("  audio_collection.py 自测")
    print("=" * 50)

    import sounddevice as sd

    # 兼容 dict / object 的取值辅助 —— 和 resolve 里的 _get 一样
    def _g(d, k, default=0):
        if isinstance(d, dict):
            return d.get(k, default)
        return getattr(d, k, default)

    # 先列一下 sounddevice 枚举到的所有设备 —— 和 PowerShell 那边对照着看
    devs = sd.query_devices()
    print(f"\n--- sounddevice 枚举到 {len(devs)} 个设备 ---")
    for d in devs:
        idx  = _g(d, 'index', -1)
        name = _g(d, 'name', '')
        ic   = _g(d, 'max_input_channels', 0)
        oc   = _g(d, 'max_output_channels', 0)
        io_tag = "IN " if ic > 0 else "OUT" if oc > 0 else "--"
        print(f"  [{idx:>2}] {io_tag} | {name}")

    # 拿系统默认输入做测试
    default_in_idx, _ = sd.default.device
    print(f"\n系统默认输入索引 = {default_in_idx}")

    default_in_name = _g(sd.query_devices(default_in_idx), 'name', '')
    resolved = resolve_sd_device_index(default_in_name, "音频输入")
    print(f"resolve_sd_device_index('{default_in_name}', '音频输入') → {resolved}")

    if resolved == default_in_idx:
        print("✅ 匹配正确")
    else:
        print(f"⚠️ 匹配不一致，预期 {default_in_idx}，得到 {resolved}")