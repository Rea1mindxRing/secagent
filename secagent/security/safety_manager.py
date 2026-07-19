import re
from typing import Tuple, Optional, Callable, Dict, Any
from dataclasses import dataclass
from .policy import SafetyMode
from .risk_levels import RiskLevel, CommandPattern, COMMAND_RISK_RULES


@dataclass
class ApprovalRequest:
    cmd: str
    risk_level: RiskLevel
    description: str


@dataclass
class ExecutionResult:
    allowed: bool
    approved: bool
    risk_level: RiskLevel
    message: str


class SafetyManager:
    def __init__(self, mode: SafetyMode = SafetyMode.SMART):
        self.mode = mode
        self._approval_callback: Optional[Callable[[ApprovalRequest], bool]] = None

    def set_approval_callback(self, callback: Callable[[ApprovalRequest], bool]):
        self._approval_callback = callback

    def analyze_command(self, cmd: str) -> ApprovalRequest:
        cmd_lower = cmd.strip().lower()

        for rule in COMMAND_RISK_RULES:
            if re.search(rule.pattern, cmd_lower):
                return ApprovalRequest(
                    cmd=cmd,
                    risk_level=rule.risk_level,
                    description=rule.description,
                )

        return ApprovalRequest(
            cmd=cmd,
            risk_level=RiskLevel.LOW,
            description="未知命令",
        )

    def check_execution(self, cmd: str) -> ExecutionResult:
        request = self.analyze_command(cmd)

        if self.mode == SafetyMode.YOLO:
            return ExecutionResult(
                allowed=True,
                approved=True,
                risk_level=request.risk_level,
                message="YOLO模式：命令已自动放行"
            )

        if self.mode == SafetyMode.STRICT:
            if self._approval_callback:
                approved = self._approval_callback(request)
                return ExecutionResult(
                    allowed=approved,
                    approved=approved,
                    risk_level=request.risk_level,
                    message=f"严格模式：{'已审批' if approved else '被拒绝'}"
                )
            return ExecutionResult(
                allowed=False,
                approved=False,
                risk_level=request.risk_level,
                message="严格模式：需要用户审批"
            )

        if self.mode == SafetyMode.SMART:
            if request.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
                if self._approval_callback:
                    approved = self._approval_callback(request)
                    return ExecutionResult(
                        allowed=approved,
                        approved=approved,
                        risk_level=request.risk_level,
                        message=f"智能模式：高危命令{'已审批' if approved else '被拒绝'}"
                    )
                return ExecutionResult(
                    allowed=False,
                    approved=False,
                    risk_level=request.risk_level,
                    message="智能模式：高危命令需要审批"
                )

            return ExecutionResult(
                allowed=True,
                approved=True,
                risk_level=request.risk_level,
                message=f"智能模式：{request.risk_level.value}风险命令已自动放行"
            )

        return ExecutionResult(
            allowed=False,
            approved=False,
            risk_level=request.risk_level,
            message="未知模式"
        )

    def execute_with_safety(self, cmd: str, executor: Callable[[str], dict]) -> Dict[str, Any]:
        result = self.check_execution(cmd)

        if not result.allowed:
            return {
                "success": False,
                "error": result.message,
                "risk_level": result.risk_level.value,
                "blocked": True
            }

        try:
            return executor(cmd)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "risk_level": result.risk_level.value,
                "blocked": False
            }

    def set_mode(self, mode: SafetyMode):
        self.mode = mode