from dataclasses import dataclass
from typing import List

from .task import AgentTask, TaskIntent, TaskKind
from ..skills.registry import select_skills


@dataclass(frozen=True)
class WorkflowStep:
    name: str
    objective: str


@dataclass(frozen=True)
class SecurityWorkflow:
    task: AgentTask
    selected_skills: List[str]
    steps: List[WorkflowStep]

    def decision_summary(self) -> str:
        skills = ", ".join(self.selected_skills) or "none"
        targets = ", ".join(self.task.target_values) or "待识别"
        steps = " -> ".join(step.name for step in self.steps) or "direct_answer"
        return f"目标: {targets} | 技能: {skills} | 流程: {steps}"

    def to_prompt_context(self) -> str:
        step_lines = "\n".join(f"- {step.name}: {step.objective}" for step in self.steps)
        return f"{self.task.to_prompt_context()}\n工作流:\n{step_lines or '- direct_answer: 直接回答'}"


def build_security_workflow(task: AgentTask) -> SecurityWorkflow:
    if task.kind != TaskKind.SECURITY_TEST:
        return SecurityWorkflow(task=task, selected_skills=[], steps=[])

    selected_skills = select_skills(task.request)
    if not selected_skills and task.targets:
        selected_skills = ["performing-external-network-penetration-test"]
    if task.intent == TaskIntent.EXTERNAL_RECON:
        steps = [
            WorkflowStep("scope", "确认目标格式、测试边界和可执行工具"),
            WorkflowStep("recon", "发现存活资产、端口、服务和 Web 入口"),
            WorkflowStep("triage", "按暴露面、版本和可访问入口排序风险"),
            WorkflowStep("findings", "输出证据、置信度和下一步验证建议"),
        ]
    elif task.intent == TaskIntent.VULNERABILITY_VALIDATION:
        steps = [
            WorkflowStep("scope", "确认目标、漏洞类型和验证条件"),
            WorkflowStep("probe", "执行低影响验证并保留原始证据"),
            WorkflowStep("analysis", "判断影响、误报可能性和复现路径"),
            WorkflowStep("findings", "输出结构化漏洞结论和修复建议"),
        ]
    else:
        steps = [
            WorkflowStep("scope", "提取目标、意图、限制和关键参数"),
            WorkflowStep("execute", "选择匹配工具或 skill 获取证据"),
            WorkflowStep("findings", "输出结构化分析和后续动作"),
        ]

    return SecurityWorkflow(task=task, selected_skills=selected_skills, steps=steps)
