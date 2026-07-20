import re
from dataclasses import dataclass
from typing import List


TARGET_PATTERN = re.compile(
    r"(?<![\w.-])(?:https?://(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}|(?:\d{1,3}\.){3}\d{1,3})(?::\d{1,5})?(?:/[\w./?%=&+#:-]*)?|(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}|(?:\d{1,3}\.){3}\d{1,3})(?::\d{1,5})?(?:/[\w./?%=&+#:-]*)?)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SecurityTask:
    targets: List[str]
    intent: str
    vulnerability_hints: List[str]

    def to_context(self) -> str:
        targets = ", ".join(self.targets) or "未识别，需从用户补充"
        hints = ", ".join(self.vulnerability_hints) or "通用外网侦察"
        return f"目标: {targets}\n意图: {self.intent}\n漏洞线索: {hints}"


def parse_security_task(request: str) -> SecurityTask:
    targets = list(dict.fromkeys(match.group(0).rstrip(".,;，。") for match in TARGET_PATTERN.finditer(request)))
    normalized = request.lower()
    if any(word in normalized for word in ("扫描", "探测", "打点", "枚举", "端口", "资产")):
        intent = "外网侦察与攻击面枚举"
    elif any(word in normalized for word in ("漏洞", "渗透", "pentest", "bounty", "bug")):
        intent = "漏洞验证与渗透测试"
    else:
        intent = "安全测试任务"
    hints = [hint for hint in ("xss", "ssrf", "sql注入", "越权", "idor", "bola", "api", "业务逻辑", "红队") if hint in normalized]
    return SecurityTask(targets=targets, intent=intent, vulnerability_hints=hints)
