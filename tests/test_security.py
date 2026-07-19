import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from secagent.security.policy import SafetyMode
from secagent.security.safety_manager import SafetyManager


def test_safety_mode():
    mode = SafetyMode.from_string("smart")
    assert mode == SafetyMode.SMART
    mode = SafetyMode.from_string("unknown")
    assert mode == SafetyMode.SMART
    print("✓ SafetyMode 测试通过")


def test_safety_manager():
    manager = SafetyManager(SafetyMode.YOLO)
    result = manager.check_execution("ls -la")
    assert result.allowed == True
    result = manager.check_execution("rm -rf /")
    assert result.allowed == True

    manager.set_mode(SafetyMode.STRICT)
    result = manager.check_execution("ls -la")
    assert result.allowed == False

    manager.set_mode(SafetyMode.SMART)
    result = manager.check_execution("ls -la")
    assert result.allowed == True
    result = manager.check_execution("rm -rf /")
    assert result.allowed == False
    print("✓ SafetyManager 测试通过")


if __name__ == "__main__":
    test_safety_mode()
    test_safety_manager()
    print("\n所有测试通过！")