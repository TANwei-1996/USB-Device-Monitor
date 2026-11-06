"""
数据模型测试
作者：TANYI
日期：2026-07-02
修改记录：
    2026-11-06：v0.1.4 (refactor/v0.1.4-code-quality) - 新建，覆盖 USBDeviceInfo 字段校验(P2-4)
"""
import sys
from pathlib import Path

# 让测试文件能导入项目模块（tests/ 在项目下一级，需回退一层）
PROJECT_PATH = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_PATH))

from models.usb_devices_info import USBDeviceInfo

def run_case(label: str, expect: type, *args, **kwargs) -> bool:
    """执行一条用例：期望抛出 expect 类型异常则 PASS"""
    try:
        USBDeviceInfo(*args, **kwargs)
        print(f"[FAIL] {label} —— 未抛出 {expect.__name__}")
        return False
    except expect as e:
        print(f"[PASS] {label} —— {e}")
        return True
    except Exception as e:
        print(f"[FAIL] {label} —— 异常类型不符：{type(e).__name__}: {e}")
        return False

def main() -> int:
    results = [
        run_case("空名称应拒绝", ValueError, "", "x", "0BDA", "B00C", "OK"),
        run_case("空实例ID应拒绝", ValueError, "耳机", "", "0BDA", "B00C", "OK"),
        run_case("VID为None应拒绝", ValueError, "耳机", "x", None, "B00C", "OK"),
        run_case("PID为空串应拒绝", ValueError, "耳机", "x", "0BDA", "", "OK"),
        run_case("audio_children类型错误应拒绝", TypeError,
                 "耳机", "x", "0BDA", "B00C", "OK", audio_children={"a": 1}),
    ]

    # 正常用例：不抛异常则 PASS
    try:
        USBDeviceInfo("耳机", "x", "0BDA", "B00C", "OK", audio_children=[])
        print("[PASS] 合法数据可正常构造")
        results.append(True)
    except Exception as e:
        print(f"[FAIL] 合法数据构造失败 —— {e}")
        results.append(False)

    passed = sum(results)
    print(f"\n结果：{passed}/{len(results)} 通过")
    return 0 if passed == len(results) else 1

if __name__ == '__main__':
    sys.exit(main())