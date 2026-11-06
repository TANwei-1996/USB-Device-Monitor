"""
日志模块
作者：TANYI
日期：2026-07-02
修改记录：
    2026-11-05 ：添加日志文件滚动功能
"""
import sys
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

# 定义日志等级
LOG_LEVEL = logging.INFO

# 定义日志格式
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"

# 日志文件路径
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "usb_monitor.log"


def setup_logger(name: str = None) -> logging.Logger:
    """
    定义logger实例，直接调用
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    if logger.handlers:
        return logger

    # 控制台输出
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(LOG_LEVEL)
    console.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(console)

    # 输出日志
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            #  日志文件路径
            #  最大文件大小2MB,超出则创建新文件,保留5个备份文件
            #  备份文件数量5个
            LOG_FILE, encoding="utf-8",maxBytes=1024 * 1024 * 2, backupCount=5
        )
        file_handler.setLevel(LOG_LEVEL)
        file_handler.setFormatter(
            logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
        )
        logger.addHandler(file_handler)
    except Exception as e:
        print(e)
        pass

    return logger
