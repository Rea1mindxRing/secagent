from pathlib import Path
from typing import List, Tuple

from ..llm.system_prompt import SECURITY_AGENT_SYSTEM_PROMPT


SKILL_ROOT = Path(__file__).resolve().parent
SKILL_ROUTES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("performing-external-network-penetration-test", ("外网", "外部", "打点", "渗透", "pentest", "penetration", "红队", "red team")),
    ("scanning-network-with-nmap-advanced", ("nmap", "端口", "服务枚举", "主机发现", "网络扫描", "探测", "扫描")),
    ("performing-subdomain-enumeration-with-subfinder", ("子域", "域名枚举", "资产发现", "subfinder", "subdomain")),
    ("performing-web-application-penetration-test", ("web", "网站", "网页", "web渗透", "应用测试", "burp")),
    ("conducting-api-security-testing", ("api", "接口", "graphql", "rest")),
    ("testing-api-security-with-owasp-top-10", ("api漏洞", "api安全", "owasp api", "接口安全")),
    ("testing-for-broken-access-control", ("越权", "idor", "bola", "访问控制", "权限绕过")),
    ("testing-for-business-logic-vulnerabilities", ("业务逻辑", "逻辑漏洞", "流程漏洞", "竞态")),
    ("testing-for-xss-vulnerabilities", ("xss", "跨站", "脚本注入")),
    ("performing-ssrf-vulnerability-exploitation", ("ssrf", "服务端请求伪造")),
    ("conducting-full-scope-red-team-engagement", ("红队", "red team", "初始访问", "横向", "攻击路径")),
)


def select_skills(request: str, limit: int = 3) -> List[str]:
    normalized = request.lower()
    scored = []
    for name, keywords in SKILL_ROUTES:
        score = sum(1 for keyword in keywords if keyword.lower() in normalized)
        if score:
            scored.append((score, name))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [name for _, name in scored[:limit]]


def load_skill_context(request: str, limit: int = 3, max_chars_per_skill: int = 7000) -> Tuple[List[str], str]:
    selected = select_skills(request, limit=limit)
    sections = []
    for name in selected:
        path = SKILL_ROOT / name / "SKILL.md"
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")[:max_chars_per_skill]
        sections.append(f"### ACTIVE SKILL: {name}\n{content}")
    return selected, "\n\n".join(sections)


def build_runtime_system_prompt(request: str, task_context: str = "") -> Tuple[List[str], str]:
    selected, skill_context = load_skill_context(request)
    sections = [SECURITY_AGENT_SYSTEM_PROMPT]
    if task_context:
        sections.append(f"## NORMALIZED TASK\n{task_context}")
    if skill_context:
        sections.append(f"## ROUTED SKILLS\n{skill_context}")
    return selected, "\n\n".join(sections)
