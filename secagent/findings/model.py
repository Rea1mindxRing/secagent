from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class Evidence:
    source: str
    content: str
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Finding:
    title: str
    target: str
    entrypoint: str
    severity: str
    confidence: str
    impact: str
    reproduction_steps: List[str]
    evidence: List[Evidence]
    remediation: str

    def to_markdown(self) -> str:
        steps = "\n".join(f"{index + 1}. {step}" for index, step in enumerate(self.reproduction_steps))
        evidence = "\n".join(f"- {item.source}: {item.content}" for item in self.evidence)
        return (
            f"## {self.title}\n"
            f"- Target: {self.target}\n"
            f"- Entrypoint: {self.entrypoint}\n"
            f"- Severity: {self.severity}\n"
            f"- Confidence: {self.confidence}\n"
            f"- Impact: {self.impact}\n\n"
            f"### Reproduction\n{steps or '待补充'}\n\n"
            f"### Evidence\n{evidence or '待补充'}\n\n"
            f"### Remediation\n{self.remediation}"
        )
