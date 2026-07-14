"""
实时音频采集
作者：TANYI
2026-07-13
"""
import time
import numpy as np
import sounddevice as sd
from utils import setup_logger

logger = setup_logger(__name__)

# 全局变量
VOICE_DB_THRESHOLD = -30  # 语音阈值
VOICE_DB_MIN = -60  # 最低分贝
BAR_WIDTH = 50  # 音量条最大宽度
RMS_SILENCE = 0.0001  # 静音阈值默认判定值


def audio_dev_list():
    """
    所有的音频设备
    :return:
    """
    print("=" * 30 + "可用音频设备" + "=" * 30, end="\n")

    dev_audio = sd.query_devices()
    for i, dev in enumerate(dev_audio):
        # 最大输入声道数
        if dev['max_input_channels'] > 0:
            kind = "输入"
        else:
            kind = "输出"
        ch = dev['max_input_channels'] or dev['max_output_channels']
        print(f"[{i}] {dev['name']} ({kind}, ch={ch})", flush=True)
    return dev_audio


def find_mic_by_name(keyword="麦克风") -> tuple:
    """
    按关键字找输入设备
    :param keyword: 设备名关键字
    :return: (index, name) 或 (None, None)
    """
    dev_audio = sd.query_devices()
    for i, dev in enumerate(dev_audio):
        if (dev['max_input_channels'] > 0) and (keyword in dev['name']):
            return i, dev['name']
    return None, None


def select_input_device() -> int:
    """
    列出所有输入设备，手动选择
    :return: 选中的设备 index
    """
    dev_audio = sd.query_devices()
    input_list = []  # 存所有输入设备 (index, name)

    print("\n=== 可用输入设备 ===")
    for i, dev in enumerate(dev_audio):
        if dev['max_input_channels'] > 0:
            input_list.append((i, dev['name']))
            print(f" [{i}] {dev['name']}", flush=True)

    if not input_list:
        raise RuntimeError("没有可用的输入设备")

    # 只有一个输入设备，直接用
    if len(input_list) == 1:
        idx, name = input_list[0]
        print(f"\n只有一个输入设备，自动选择: [{idx}] {name}")
        return idx

    # 多设备手动选择
    print()
    while True:
        try:
            num = input("选择输入设备序号（直接回车选第一个）: ").strip()
            # 无输入时，默认选择第一个
            if not num:
                idx, name = input_list[0]
                print(f" -> 自动选择: [{idx}] {name}")
                return idx
            # 数字输入 → 校验
            choice = int(num)
            for i, name in input_list:
                if i == choice:
                    return choice
            print(f" [{choice}] 非已有输入设备，重新选择")
        except ValueError:
            print(" 请输入设备序号（数字）")


def get_samplerate(device_idx: int, default: int = 44100) -> int:
    """
    获取相关采用的设备默认采样率
    :param device_idx: 设备 index
    :param default: 默认值
    :return: 采样率
    """
    try:
        info = sd.query_devices(device_idx)
    except Exception:
        return default

    # 蓝牙耳机常见采样率优先（8000/16000 通话用）
    candidates = [
        int(info['default_samplerate']),
        16000, 8000, 48000, 44100, 32000, 22050, 11025
    ]

    for sr in candidates:
        if sr <= 0:
            continue
        try:
            sd.check_input_settings(device=device_idx, samplerate=sr)
            return sr
        except Exception:
            continue
    return default


def test_mic(duration: int = 10, samplerate: int = 44100, device_ind=None):
    """
    mic测试
    :param duration: 录制时间：10S
    :param samplerate: 采样率：44.1 Khz
    :param device_ind: 设备 index，None 则让用户选
    :return:
    """

    if device_ind is None:
        device_ind = select_input_device()

    # 获取设备支持的采样率大小
    samplerate = get_samplerate(device_ind, samplerate)
    dev = sd.query_devices(device_ind)
    print(f"使用设备 [{device_ind}] {dev['name']} @ {samplerate} Hz")

    print(f"\n ... 开始录音 {duration} 秒 ...")
    try:
        recording = sd.rec(
            int(duration * samplerate),  # 计算总样本点数
            samplerate=samplerate,
            channels=1,
            dtype='float32',
            device=device_ind
        )
    except sd.PortAudioError as e:
        logger.error(f"录音启动失败: {e}")
        print(f" 录音启动失败: {e}")
        return None

    # 等待音频录制结束
    try:
        sd.wait()
    except sd.PortAudioError as e:
        logger.error(f"录音过程中出错: {e}")
        print(f"录音中断: {e}")
        return None

    if recording is None or recording.size == 0:
        print(" 录音数据为空")
        return None

    # 音量大小
    rms = float(np.sqrt(np.mean(recording ** 2)))
    # 峰值大小
    peak = float(np.max(np.abs(recording)))
    # 分贝：db
    db = 20 * np.log10(rms + 1e-10)

    print("\n 录音完成：", flush=True)
    print(f" RMS 音量: {rms:.6f}", flush=True)
    print(f" 峰值振幅: {peak:.6f}", flush=True)
    print(f" 分贝值: {db:.2f} dB", flush=True)

    if rms < RMS_SILENCE:
        print(" 音量极低，检查麦克风是否启用 / 静音")
    return recording


def monitor_realtime(duration: int = 10, samplerate: int = 44100,
                     blocksize: int = 2048, device_ind=None):
    """
    实现：分贝\底噪\削波\短时能量\过零概率
    :param duration: 检测总时长
    :param samplerate: 采样率
    :param blocksize: 每次处理的样本块大小
    :param device_ind: 设备 index，None 则让用户选
    """
    VALUE = 1e-10
    # 手动选择输入设备
    if device_ind is None:
        device_ind = select_input_device()

    # 检测输入设备如果小于0个
    if device_ind < 0:
        logger.info("无设备输入....")
        return

    # 获取设备支持的采样率大小
    samplerate = get_samplerate(device_ind, samplerate)
    dev = sd.query_devices(device_ind)
    mic_name = dev['name']
    logger.info(f"输入音频设备：[{device_ind}] {mic_name} @ {samplerate} Hz")

    # 背景噪声
    # 安静环境下的音量值
    noise_sampler = []  # 定义存储安静环境下的音量RMS
    noise_db_sampler = None  # 底噪

    # 定义全局变量：初始默认值
    noise_rms_sampler = 0.005  # 定义安静判定值大小：如rms＜0.005：安静
    noise_count = 10  # 默认帧数设置：10
    consecutive_frames = 0  # 连续安静环境下的帧数计算初始值：0

    print(f"\n === 实时声音检测（{duration} 秒）===")
    print(f"采样率: {samplerate} Hz | 设备: [{device_ind}] {mic_name}")
    print("声音检测中...., ctrl+c提前结束\n")
    print("-" * 60, flush=True)
    print(f" {'dB':>8} | {'RMS':>10} | {'峰值':>8} | {'短时能量':>9} | {'过零率':>8} | {'底噪':>8} | {'削波':>5} |", flush=True)
    print("-" * 60, flush=True)

    start_time = time.time()
    count = 5  # 循环最大次数
    count_1 = 0
    try:
        while (time.time() - start_time) < duration:
            try:
                block = sd.rec(
                    blocksize,
                    samplerate=samplerate,
                    channels=1,
                    dtype='float32',
                    device=device_ind
                )
                sd.wait()
            except sd.PortAudioError as e:
                logger.error(f"声音采集失败: {e}")
                print(f"录音失败: {e}，0.5s 后重试", flush=True)
                time.sleep(0.5)
                count_1 += 1
                if count_1 >= count:
                    break
                continue

            # 空数据保护
            if block is None or block.size == 0:
                continue

            # 分贝值计算
            rms = float(np.sqrt(np.mean(block ** 2)))
            voice_db = 20 * np.log10(rms + VALUE)

            # 音频数据峰值幅度
            peak = float(np.max(np.abs(block)))

            # 短时能量值
            short_time_val = rms

            # 过零率
            # 统计数据变化标志的数量
            signs = np.sign(block.flatten())
            zero_crossings = int(np.sum(np.diff(signs) != 0))
            # 计算过零率
            crossings_val = blocksize / samplerate
            zcr = zero_crossings / crossings_val  # 次/秒

            # 统计底噪数量值-概率值（非具体）
            if rms < noise_rms_sampler:
                consecutive_frames += 1
            else:
                consecutive_frames = 0  # 有声音，清零

            if consecutive_frames >= noise_count:
                noise_sampler.append(rms)

            if len(noise_sampler) > 0:
                recent = noise_sampler[-30:]
                noise_db_sampler = 20 * np.log10(np.mean(recent) + VALUE)
            else:
                noise_db_sampler = None

            # 削波：以频谱上下±1归一化振幅区间统计，超出该区间判定为能量过大导致声音削波
            # 说明解释：数字音频标准：+1.0 和 -1.0 就是 0dBFS（满量程），超过 ±1 就会削波失真；0 代表静音
            # 设置极限非削波值大小
            WAVE_CUTTING_RANGE = 0.99
            clipped = int(np.sum(np.abs(block) >= WAVE_CUTTING_RANGE))
            if clipped > 0:
                voice_clip_flag = "削波"
            else:
                voice_clip_flag = ""

            # 声音波动标识
            # 输入声音能量大于阈值，添加标识，否则不添加，为空标识
            if voice_db > VOICE_DB_THRESHOLD:
                voice_flag = "🔊"
            else:
                voice_flag = " "

            if noise_db_sampler is not None:
                noise_str = f"{noise_db_sampler:8.2f}"
            else:
                noise_str = f"{'--':>8}"
            # 格式化指标输出打印
            print(f" {voice_db:8.2f} | {rms:10.6f} | {peak:8.4f} | {short_time_val:9.6f} | "
                  f"{zcr:8.1f} | {noise_str} | {voice_clip_flag:<6} | {voice_flag}", flush=True)


    except KeyboardInterrupt:
        print("\n 已停止检测", flush=True)

    print("-" * 25 + " 检测结束 " + "-" * 25, flush=True)

    # 数据最终打印结果
    print("\n========== 本次监测报告 ==========\n")
    if len(noise_sampler) > 0:
        final_noise = np.mean(noise_sampler[-30:])
        final_noise_db = 20 * np.log10(final_noise + VALUE)
        print(f" 底噪水平:   {final_noise_db:8.2f} dB")
    else:
        print(f" 底噪水平:   未检测到安静片段:持续有声音")

    if voice_db > VOICE_DB_THRESHOLD:
        print(f" 语音活动:   有声")
    else:
        print(f" 语音活动:   无声音：安静")
    print(f" 检测结束", flush=True)


if __name__ == '__main__':
    audio_dev_list()
    print()
    monitor_realtime(duration=10)  # 实时监测 10 秒，5 项指标
    # monitor_realtime(duration=30)    # 监测 30 秒
    # test_mic()                       # 一次性录音
