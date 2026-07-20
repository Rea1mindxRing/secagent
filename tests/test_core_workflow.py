import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from secagent.core.task import TaskIntent, TaskKind
from secagent.core.workflow import build_security_workflow
from secagent.findings.model import Evidence, Finding
from secagent.skills.registry import build_runtime_system_prompt
from secagent.skills.task_parser import parse_security_task


def test_security_workflow_defaults_to_external_recon_for_target():
    parsed = parse_security_task("目标 demo.example.com 帮我看看")
    task = parsed.to_agent_task("目标 demo.example.com 帮我看看")
    workflow = build_security_workflow(task)

    assert task.kind == TaskKind.SECURITY_TEST
    assert task.intent == TaskIntent.GENERAL_SECURITY_TEST
    assert workflow.selected_skills == ["performing-external-network-penetration-test"]
    assert "scope" in workflow.decision_summary()


def test_chat_workflow_has_no_tools_or_skills():
    parsed = parse_security_task("你好，你是什么模型")
    task = parsed.to_agent_task("你好，你是什么模型")
    workflow = build_security_workflow(task)

    assert task.kind == TaskKind.CHAT
    assert task.requires_tools is False
    assert workflow.selected_skills == []
    assert workflow.steps == []


def test_runtime_prompt_accepts_workflow_selected_skills():
    parsed = parse_security_task("目标 demo.example.com 帮我看看")
    workflow = build_security_workflow(parsed.to_agent_task("目标 demo.example.com 帮我看看"))
    selected, prompt = build_runtime_system_prompt(
        "目标 demo.example.com 帮我看看",
        workflow.to_prompt_context(),
        selected_skills=workflow.selected_skills,
    )

    assert selected == ["performing-external-network-penetration-test"]
    assert "ACTIVE SKILL" in prompt
    assert "工作流" in prompt


def test_finding_renders_required_report_fields():
    finding = Finding(
        title="Exposed Admin Panel",
        target="https://demo.example.com",
        entrypoint="/admin",
        severity="high",
        confidence="medium",
        impact="unauthenticated management surface",
        reproduction_steps=["Open /admin", "Observe login panel"],
        evidence=[Evidence(source="httpx", content="200 OK title=Admin")],
        remediation="Restrict access and require strong authentication.",
    )

    rendered = finding.to_markdown()
    assert "Exposed Admin Panel" in rendered
    assert "Severity: high" in rendered
    assert "200 OK" in rendered
