#!/usr/bin/env python3
"""
敏感配置检查脚本 — 扫描代码仓库中泄露的 API Key、Token、密钥等敏感信息。

用法:
    python scripts/check_sensitive_config.py
    python scripts/check_sensitive_config.py --path /path/to/repo
    python scripts/check_sensitive_config.py --verbose

退出码:
    0  — 未发现敏感信息
    1  — 发现敏感信息
    2  — 运行时错误
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# 敏感信息检测规则
# ---------------------------------------------------------------------------

@dataclass
class SecretRule:
    name: str
    pattern: re.Pattern
    severity: str          # critical / high / medium / low
    description: str
    allowed_examples: List[str] = field(default_factory=list)


SECRET_RULES: List[SecretRule] = [
    # ── 云服务密钥 ──
    SecretRule(
        name="AWS Access Key ID",
        pattern=re.compile(r"(?<![A-Za-z0-9/+=])(AKIA[0-9A-Z]{16})(?![A-Za-z0-9/+=])"),
        severity="critical",
        description="AWS 访问密钥 ID 泄露可能导致云服务被未授权访问",
    ),
    SecretRule(
        name="AWS Secret Access Key",
        pattern=re.compile(r"(?<![A-Za-z0-9/+=])(?:(?i)aws[_-]?secret[_-]?access[_-]?key|secret[_-]?access[_-]?key)\s*[:=]\s*[\"']?[A-Za-z0-9/+=]{40}[\"']?"),
        severity="critical",
        description="AWS Secret Key 泄露可导致云环境完全沦陷",
    ),
    # ── LLM API Key ──
    SecretRule(
        name="OpenAI API Key",
        pattern=re.compile(r"(?<![A-Za-z0-9])(sk-[A-Za-z0-9]{20,70})(?![A-Za-z0-9])"),
        severity="critical",
        description="OpenAI API Key 泄露可导致被恶意调用造成经济损失",
        allowed_examples=["sk-your-api-key-here", "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
    ),
    SecretRule(
        name="Anthropic API Key",
        pattern=re.compile(r"(?<![A-Za-z0-9])(sk-ant-[A-Za-z0-9]{20,70})(?![A-Za-z0-9])"),
        severity="critical",
        description="Anthropic API Key 泄露可导致被恶意调用",
    ),
    SecretRule(
        name="DeepSeek API Key",
        pattern=re.compile(r"(?<![A-Za-z0-9])(sk-[a-f0-9]{32,64})(?![A-Za-z0-9])"),
        severity="critical",
        description="DeepSeek / 通用 API Key 泄露",
        allowed_examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
    ),
    # ── 代码托管平台 Token ──
    SecretRule(
        name="GitHub Personal Access Token",
        pattern=re.compile(r"(?<![A-Za-z0-9])(ghp_[A-Za-z0-9]{36,40})(?![A-Za-z0-9])"),
        severity="critical",
        description="GitHub Token 泄露可导致代码仓库被未授权访问",
    ),
    SecretRule(
        name="GitHub OAuth Access Token",
        pattern=re.compile(r"(?<![A-Za-z0-9])(gho_[A-Za-z0-9]{36,40})(?![A-Za-z0-9])"),
        severity="critical",
        description="GitHub OAuth Token 泄露",
    ),
    SecretRule(
        name="GitLab Personal Access Token",
        pattern=re.compile(r"(?<![A-Za-z0-9])(glpat-[A-Za-z0-9\-]{20,40})(?![A-Za-z0-9])"),
        severity="critical",
        description="GitLab Token 泄露",
    ),
    # ── 通用密钥文件 ──
    SecretRule(
        name="Private SSH Key",
        pattern=re.compile(r"-----BEGIN\s+(RSA|DSA|EC|OPENSSH|PRIVATE)\s+KEY-----"),
        severity="critical",
        description="私钥泄露可导致服务器被未授权登录",
    ),
    SecretRule(
        name="JWT Token / Bearer Token",
        pattern=re.compile(r"(?:(?i)bearer\s+)[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+"),
        severity="high",
        description="JWT Token 泄露可能导致身份被冒用",
    ),
    SecretRule(
        name="Generic Password in Config",
        pattern=re.compile(r"(?:(?i)(?:password|passwd|pwd|secret)\s*[:=]\s*['\"]?[^'\"\s]{6,}['\"]?)"),
        severity="high",
        description="配置文件中发现密码/密钥字段，确认是否为占位符或测试值",
    ),
    SecretRule(
        name="Database Connection String with Password",
        pattern=re.compile(r"(?:postgres(?:ql)?|mysql|mongodb|redis|mssql)://[^:]+:[^@]+@"),
        severity="critical",
        description="数据库连接字符串包含明文密码",
    ),
    SecretRule(
        name="Slack Bot / Webhook Token",
        pattern=re.compile(r"(?:(?i)xox[baprs]-[A-Za-z0-9\-]{10,80}|hooks\.slack\.com/services/[A-Za-z0-9/]+)"),
        severity="high",
        description="Slack Token / Webhook 泄露",
    ),
    SecretRule(
        name="Google API Key",
        pattern=re.compile(r"(?:(?i)AIza[0-9A-Za-z\-_]{35})"),
        severity="high",
        description="Google API Key 泄露",
    ),
    SecretRule(
        name="Heroku API Key",
        pattern=re.compile(r"(?<![A-Za-z0-9])(?:[hH][eE][rR][oO][kK][uU]\s*[:=]\s*[\"']?[A-Za-z0-9\-]{20,40}[\"']?)"),
        severity="high",
        description="Heroku API Key 泄露",
    ),
    SecretRule(
        name="Twilio API Key",
        pattern=re.compile(r"(?:(?i)SK[0-9a-fA-F]{32})"),
        severity="high",
        description="Twilio API Key / SID 泄露",
    ),
    # ── 证书/PEM 文件 ──
    SecretRule(
        name="Certificate / PEM Data",
        pattern=re.compile(r"-----BEGIN\s+CERTIFICATE-----"),
        severity="medium",
        description="证书文件泄露可能导致中间人攻击",
    ),
    # ── YAML/JSON 中的内联密钥 ──
    SecretRule(
        name="Potential Hardcoded API Key",
        pattern=re.compile(r"(?i)(?:api[_-]?key|api[_-]?secret|app[_-]?secret|client[_-]?secret|auth[_-]?token)[\s]*[:=][\s]*['\"][A-Za-z0-9_\-./+=]{16,}['\"]"),
        severity="high",
        description="配置文件或代码中硬编码了 API 密钥类字段",
    ),
]


# ---------------------------------------------------------------------------
# 跳过规则（白名单路径 / 文件扩展名）
# ---------------------------------------------------------------------------

SKIP_DIRS = {
    ".git", "__pycache__", ".pytest_cache", "node_modules",
    ".venv", "venv", "env", ".egg-info", "build", "dist",
    ".cache", ".atomcode", ".ai_completion",
}

SKIP_EXTENSIONS = {
    ".pyc", ".pyo", ".so", ".dll", ".dylib", ".exe",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".eot",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".lock",  # package-lock, poetry.lock 等
}

SKIP_FILE_PATTERNS = [
    re.compile(r"\.secret\.", re.IGNORECASE),
    re.compile(r"\.env\.example", re.IGNORECASE),
    re.compile(r"\.env\.template", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# 检测结果
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    rule: SecretRule
    file_path: str
    line_number: int
    matched_text: str
    context: str


# ---------------------------------------------------------------------------
# 扫描器
# ---------------------------------------------------------------------------

class SensitiveConfigScanner:
    def __init__(self, repo_root: str, verbose: bool = False):
        self.repo_root = os.path.abspath(repo_root)
        self.verbose = verbose
        self.findings: List[Finding] = []
        self.files_scanned = 0
        self.files_skipped = 0

    def _should_skip(self, file_path: str) -> bool:
        rel = os.path.relpath(file_path, self.repo_root)
        parts = rel.split(os.sep)

        # 跳过黑名单目录
        for part in parts[:-1]:  # 不检查文件名本身
            if part in SKIP_DIRS:
                return True

        # 跳过黑名单扩展名
        _, ext = os.path.splitext(file_path)
        if ext.lower() in SKIP_EXTENSIONS:
            return True

        # 跳过白名单文件模式
        for pattern in SKIP_FILE_PATTERNS:
            if pattern.search(rel):
                return True

        # 只检查文本文件
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(1024)
                try:
                    chunk.decode("utf-8")
                except UnicodeDecodeError:
                    # 尝试常见编码
                    try:
                        chunk.decode("latin-1")
                    except UnicodeDecodeError:
                        return True
            return False
        except (OSError, IOError):
            return True

    def _is_allowed(self, rule: SecretRule, line: str, match: str) -> bool:
        """检查是否属于允许的例外（如占位符、测试数据）"""
        # 检查显式白名单
        for example in rule.allowed_examples:
            if example in line:
                return True

        # 检查常见占位符模式
        placeholders = [
            "your-api-key", "your-key", "your_token", "your_secret",
            "xxxxxxxxx", "00000000", "****", "change-me", "changeme",
            "placeholder", "dummy", "test-key", "example",
            "sk-your-api-key", "sk-xxxxxxxx",
        ]
        line_lower = line.lower()
        if any(p in line_lower for p in placeholders):
            return True

        return False

    def scan_file(self, file_path: str):
        rel = os.path.relpath(file_path, self.repo_root)

        if self._should_skip(file_path):
            self.files_skipped += 1
            return

        self.files_scanned += 1
        if self.verbose:
            print(f"  🔍 扫描: {rel}")

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except (OSError, IOError) as e:
            if self.verbose:
                print(f"  ⚠️  无法读取 {rel}: {e}")
            return

        for line_num, line in enumerate(lines, 1):
            stripped = line.rstrip("\n")
            for rule in SECRET_RULES:
                for match in rule.pattern.findall(stripped):
                    # 多行匹配时取第一个元素
                    if isinstance(match, tuple):
                        match = match[0]

                    if self._is_allowed(rule, stripped, match):
                        continue

                    # 截取上下文
                    idx = stripped.find(match)
                    start = max(0, idx - 30)
                    end = min(len(stripped), idx + len(match) + 30)
                    context = stripped[start:end].strip()
                    # 对匹配到的内容做脱敏处理
                    safe_match = match[:6] + "****" + match[-4:] if len(match) > 12 else match[:4] + "****"

                    self.findings.append(Finding(
                        rule=rule,
                        file_path=rel,
                        line_number=line_num,
                        matched_text=safe_match,
                        context=context.replace(match, safe_match),
                    ))

    def scan(self):
        self.findings.clear()
        self.files_scanned = 0
        self.files_skipped = 0

        if self.verbose:
            print(f"\n📁 扫描仓库: {self.repo_root}\n")

        for root, dirs, files in os.walk(self.repo_root):
            # 原地过滤跳过的目录
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for file in files:
                file_path = os.path.join(root, file)
                self.scan_file(file_path)

    def report(self) -> str:
        lines = []
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        if not self.findings:
            lines.append("✅ 未发现敏感信息泄露！")
            lines.append("")
            lines.append(f"📊 扫描统计: {self.files_scanned} 个文件已扫描, {self.files_skipped} 个文件已跳过")
            return "\n".join(lines)

        lines.append("🚨 发现敏感信息泄露！")
        lines.append("=" * 70)
        lines.append("")

        # 按严重级别分组
        for severity in ("critical", "high", "medium", "low"):
            severity_findings = [f for f in self.findings if f.rule.severity == severity]
            if not severity_findings:
                continue
            severity_counts[severity] = len(severity_findings)

            sev_label = {
                "critical": "🔴 CRITICAL",
                "high": "🟠 HIGH",
                "medium": "🟡 MEDIUM",
                "low": "🔵 LOW",
            }[severity]
            lines.append(f"  [{sev_label}] — {len(severity_findings)} 个发现")
            lines.append("")

            for finding in severity_findings:
                lines.append(f"    文件: {finding.file_path}:{finding.line_number}")
                lines.append(f"    规则: {finding.rule.name}")
                lines.append(f"    说明: {finding.rule.description}")
                lines.append(f"    匹配: {finding.matched_text}")
                lines.append(f"    上下文: ...{finding.context}...")
                lines.append("")

        lines.append("=" * 70)
        lines.append(f"📊 扫描统计:")
        lines.append(f"   • 扫描文件: {self.files_scanned}")
        lines.append(f"   • 跳过文件: {self.files_skipped}")
        lines.append(f"   • 发现总数: {len(self.findings)}")
        lines.append(f"   • 严重级别: 🔴 CRITICAL {severity_counts['critical']}  | "
                     f"🟠 HIGH {severity_counts['high']}  | "
                     f"🟡 MEDIUM {severity_counts['medium']}  | "
                     f"🔵 LOW {severity_counts['low']}")

        return "\n".join(lines)

    def has_critical_or_high(self) -> bool:
        return any(f.rule.severity in ("critical", "high") for f in self.findings)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="敏感配置检查工具 — 扫描代码仓库中的 API Key、Token、密钥等泄露",
    )
    parser.add_argument(
        "--path", "-p",
        default=".",
        help="仓库根目录路径（默认: 当前目录）",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出模式",
    )
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="显示所有级别的发现（默认只显示 critical + high）",
    )
    args = parser.parse_args()

    repo_root = os.path.abspath(args.path)

    if not os.path.isdir(repo_root):
        print(f"❌ 路径不存在或不是目录: {repo_root}", file=sys.stderr)
        sys.exit(2)

    # 确认是 git 仓库
    git_dir = os.path.join(repo_root, ".git")
    if not os.path.isdir(git_dir):
        print(f"⚠️  警告: {repo_root} 不是一个 Git 仓库（未找到 .git 目录）", file=sys.stderr)
        print(f"   脚本将继续扫描，但建议在 Git 仓库中运行以获得最佳效果。\n", file=sys.stderr)

    scanner = SensitiveConfigScanner(repo_root, verbose=args.verbose)
    scanner.scan()

    print()
    print(scanner.report())
    print()

    if scanner.findings:
        if args.show_all:
            sys.exit(1)
        if scanner.has_critical_or_high():
            print("🔴 CI 阻断: 发现高危/严重级别的敏感信息泄露，请修复后重新提交。")
            sys.exit(1)
        else:
            print("🟡 仅发现中低风险项，建议审查但 CI 不阻断。")
            sys.exit(0)
    else:
        print("✅ 通过！")
        sys.exit(0)


if __name__ == "__main__":
    main()