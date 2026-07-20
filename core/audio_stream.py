import time
import numpy as np
import sounddevice as sd
from utils import setup_logger

logger = setup_logger(__name__)

# 全局变量
VOICE_DB_THRESHOLD = -30  # 语音阈值
VOICE_DB_MIN = -60  # 最低分贝
BAR_WIDTH = 50  # 音量条宽度
RMS_SILENCE = 0.0001  # 静音阈值默认判定值
NOISE_LONG = 30 # 底噪最大长度
# 设置极限非削波值大小
WAVE_CUTTING_RANGE = 0.99
# 常数：做分母防除零（浮点法）
VALUE = 1e-10


# 整合相关计算
def rms_():
    pass


def audio_dev_list():
    """
    获取音频设备
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
    except Exception as e:
        logger.info(e)
        return default

    # 蓝牙常见采用率：KHz -- 一般16KHz偏多
    candidates = [
        int(info['default_samplerate']),
        16000, 8000, 48000, 44100, 32000, 22050, 11025
    ]

    for sr in candidates:
        # 针对过滤 -1、0这种第一优先检测出来的不合法采样率
        # not in candidates：会将本身合理的却不在candidates过滤掉，不合理
        if sr <= 0:
            continue
        try:
            sd.check_input_settings(device=device_idx, samplerate=sr)
            return sr
        except Exception as e:
            logger.info(f"采样率输入确认不符合:{e}")
            continue
    return default


def voice_act(block, energy_val=0.01, zcr_val=0.3):
    """
    VAD:语音活动检测
    :param block: 单帧音频数据块
    # :param samplerate: 音频采样率
    :param energy_val:  能量阈值（短时能量），默认：0.01
    :param zcr_val: 过零率阈值，默认：0.3
    :return:
    """

    # 计算RMS
    rms_voice = float(np.sqrt(np.mean(block ** 2)))
    if rms_voice < energy_val:
        logger.info("未检测到语音能量活动值：设备判定静音")
        return False
    # 过零计算
    # block.flatten():将音频多维数据拉平成一维采样点序列
    # 输出数组只有 -1 / 0 / 1，只保留波形正负、丢弃振幅大小
    voice_signal = np.sign(block.flatten())
    # voice_signal = np.sign(block.flatten()) *
    # np.log1p(block.flatten() / rms_voice) # np.log1p(block.flatten() / rms_voice)做时域特征提取、语音特征建模、能量加权 ZCR
    cross = int(np.sum(np.diff(voice_signal) != 0))
    # 标准zcr计算公式：阈值0.1-0.5区间
    zcr = cross / (len(voice_signal) -1 )
    if zcr > zcr_val:
        return False
    return True


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
            int(duration * samplerate),
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
    db = 20 * np.log10(rms + VALUE)

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

    # 定义全局变量：初始默认值
    noise_rms_sampler = 0.005  # 定义安静判定值大小：如rms＜0.005：安静
    noise_count = 10  # 默认帧数设置：10
    consecutive_frames = 0  # 连续安静环境下的帧数计算初始值：0

    # 音频能量变化状态
    # 设置初始：None - 无输入能量
    rms_pre = None
    rms_his_l = []  # 创建空列表存放过往RMS记录

    print(f"\n === 实时声音检测（{duration} 秒）===")
    print(f"采样率: {samplerate} Hz | 设备: [{device_ind}] {mic_name}")
    print("声音检测中...., ctrl+c提前结束\n")
    print("-" * 92, flush=True)
    print(f" {'dB':>6} | {'RMS':>6} | {'峰值':>8} | {'波峰因子':>10} | {'信噪比':>14} | {'变化率%':>6} | {'过零率':>8} | {'底噪':>6} | {'削波':<6} |", flush=True)
    print("-" * 92, flush=True)

    # 开始时间
    start_time = time.time()
    count = 5  # 循环最大次数
    count_1 = 0
    try:
        while (time.time() - start_time) < duration:
            snr_str = f"{'--':>14}"
            change_energy_str = f"{'--':>6}"
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

            # 空数据处理
            if block is None or block.size == 0:
                continue

            # 分贝值计算
            rms = float(np.sqrt(np.mean(block ** 2)))
            voice_db = 20 * np.log10(rms + VALUE)

            if voice_db > VOICE_DB_THRESHOLD:
                print(f" 语音活动:   有声")
            else:
                print(f" 语音活动:   无声音：安静")

            # 音频：峰值
            peak = float(np.max(np.abs(block)))

            # 音频波峰因子(crest_factor)
            # 计算公式：CF(dB) = 峰值（peak）/ RMS有效值
            # 正弦波因子：1.141
            # 判断rms分贝
            if rms > 0:
                c_f = peak / (rms + VALUE)
            else:
                c_f = 0
            crest_f = f"{c_f:>10.2f}"

            # 计算音频能量状态：(当前RMS - 上一帧RMS) / 上一帧RMS * 100%
            change_energy = None
            if (rms_pre is not None) and (rms_pre > 0):
                change_energy = ((rms - rms_pre) / rms_pre) * 100
            rms_pre = rms
            rms_his_l.append(rms)

            # 过零率
            # 统计数据变化标志的数量
            signs = np.sign(block.flatten())
            zero_crossings = int(np.sum(np.diff(signs) != 0))

            # 过零率计算
            zcr = zero_crossings / (blocksize - 1)

            # 底噪数量值-概率值（非具体）
            if rms < noise_rms_sampler:
                consecutive_frames += 1
            else:
                consecutive_frames = 0  # 有声音，清零

            if consecutive_frames >= noise_count:
                noise_sampler.append(rms)

            if len(noise_sampler) > 0:
                recent = noise_sampler[-NOISE_LONG:]
                noise_db_sampler = 20 * np.log10(np.mean(recent) + VALUE)
            else:
                noise_db_sampler = None

            # 削波：以频谱上下±1归一化振幅区间统计，超出该区间判定为能量过大导致声音削波
            # 说明解释：数字音频标准：+1.0 和 -1.0 就是 0dBFS（满量程），超过 ±1 就会削波失真；0 代表静音
            clipped = int(np.sum(np.abs(block) >= WAVE_CUTTING_RANGE))
            if clipped > 0:
                voice_clip_flag = "削波"
            else:
                voice_clip_flag = ""

            # VAD
            # 声音波动标识
            # 输入声音能量大于阈值，添加标识，否则不添加，为空标识
            voice_active = voice_act(block)
            if voice_active:
                voice_flag = "有声"
            else:
                voice_flag = "无声"

            if noise_db_sampler is not None:
                noise_str = f"{noise_db_sampler:>6.2f}"
            else:
                noise_str = f"{'--':>6}"

            # 信噪比：Signal‑to‑Noise Ratio
            # 计算公式：snr = 当前信号分贝（voice_db） - 底噪（noise_db_sampler）
            snr_db = None
            if (noise_db_sampler is not None) and rms > 0:
                snr_db = voice_db - noise_db_sampler

            if snr_db is not None:
                snr_str = f"{snr_db:>14.2f}"

            if change_energy is not None:
                change_energy_str = f"{change_energy:>6.2f}"

            print(
                f" {voice_db:>6.2f} | {rms:>6.2f} | {peak:>8.2f} | {crest_f} | {snr_str} | {change_energy_str} | "
                f"{zcr:>8.2f} | {noise_str} | {voice_clip_flag:<6} | {voice_flag}",
                flush=True
            )

    except KeyboardInterrupt:
        print("\n 已停止检测", flush=True)

    print("-" * 25 + " 检测结束 " + "-" * 25, flush=True)

    # 数据最终打印结果
    print("\n========== 本次监测报告 ==========\n")
    if len(noise_sampler) > 0:
        final_noise = np.mean(noise_sampler[-NOISE_LONG:])
        final_noise_db = 20 * np.log10(final_noise + VALUE)
        print(f" 底噪水平:   {final_noise_db:8.2f} dB")
    else:
        print(f" 底噪水平:   未检测到安静片段:持续有声音")

    # 计算动态变化
    # 判断历史rms列表是否存在数据
    if len(rms_his_l) > 0:
        update_list = []
        for r in rms_his_l:
            if r > RMS_SILENCE:
                update_list.append(r)
        if update_list:
            max_rms = max(update_list)
            min_rms = min(update_list)
            rms_range_db = 20 * np.log10(max_rms / (min_rms + VALUE))
            print(f"最大RMS：{max_rms:.2f} || 最小RMS：{min_rms:.2f} || 动态范围变化大小：{rms_range_db:8.2f} dB")
        else:
            print("动态范围：有效声音数据不足")

    print(f" 检测结束", flush=True)


if __name__ == '__main__':
    audio_dev_list()
    print()
    monitor_realtime(duration=10)  # 实时监测10秒
