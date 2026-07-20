from dataclasses import dataclass, field
from enum import Enum
from typing import List


class TaskKind(str, Enum):
    CHAT = "chat"
    SECURITY_TEST = "security_test"


class TaskIntent(str, Enum):
    EXTERNAL_RECON = "external_recon"
    VULNERABILITY_VALIDATION = "vulnerability_validation"
    GENERAL_SECURITY_TEST = "general_security_test"
    GENERAL_CHAT = "general_chat"


@dataclass(frozen=True)
class SecurityTarget:
    value: str
    kind: str


@dataclass(frozen=True)
class AgentTask:
    request: str
    kind: TaskKind
    intent: TaskIntent
    targets: List[SecurityTarget] = field(default_factory=list)
    vulnerability_hints: List[str] = field(default_factory=list)

    @property
    def target_values(self) -> List[str]:
        return [target.value for target in self.targets]

    @property
    def requires_tools(self) -> bool:
        return self.kind == TaskKind.SECURITY_TEST and bool(self.targets)

    def to_prompt_context(self) -> str:
        targets = ", ".join(self.target_values) or "未识别，需从用户补充"
        hints = ", ".join(self.vulnerability_hints) or "通用外网侦察"
        return f"目标: {targets}\n意图: {self.intent.value}\n漏洞线索: {hints}"

