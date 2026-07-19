from dataclasses import dataclass
from enum import Enum


class RiskLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class CommandPattern:
    pattern: str
    risk_level: RiskLevel
    description: str


COMMAND_RISK_RULES = [
    CommandPattern(r"rm\s+-rf", RiskLevel.CRITICAL, "递归删除目录"),
    CommandPattern(r"rm\s+-r\s+-f", RiskLevel.CRITICAL, "递归删除目录"),
    CommandPattern(r"del\s+/f\s+/s", RiskLevel.CRITICAL, "强制删除文件"),
    CommandPattern(r"erase\s+/f\s+/s", RiskLevel.CRITICAL, "强制删除文件"),
    CommandPattern(r"drop\s+(database|table)", RiskLevel.CRITICAL, "删除数据库/表"),
    CommandPattern(r"delete\s+from", RiskLevel.CRITICAL, "删除数据库记录"),
    CommandPattern(r"truncate\s+table", RiskLevel.CRITICAL, "清空表"),
    CommandPattern(r"shutdown", RiskLevel.CRITICAL, "关闭系统"),
    CommandPattern(r"reboot", RiskLevel.CRITICAL, "重启系统"),
    CommandPattern(r"halt", RiskLevel.CRITICAL, "停机"),
    CommandPattern(r"init\s+(0|6)", RiskLevel.CRITICAL, "系统关机/重启"),
    CommandPattern(r"chmod\s+777", RiskLevel.HIGH, "设置全局可读写"),
    CommandPattern(r"chmod\s+-R", RiskLevel.HIGH, "递归修改权限"),
    CommandPattern(r"chown\s+-R", RiskLevel.HIGH, "递归修改所有权"),
    CommandPattern(r"kill\s+-9", RiskLevel.HIGH, "强制终止进程"),
    CommandPattern(r"killall", RiskLevel.HIGH, "终止所有进程"),
    CommandPattern(r"iptables\s+-F", RiskLevel.HIGH, "清空防火墙规则"),
    CommandPattern(r"firewall-cmd\s+--reload", RiskLevel.HIGH, "重新加载防火墙"),
    CommandPattern(r"nmap\s+-sS", RiskLevel.MEDIUM, "SYN扫描"),
    CommandPattern(r"nmap\s+-A", RiskLevel.MEDIUM, "全面扫描"),
    CommandPattern(r"sqlmap", RiskLevel.MEDIUM, "SQL注入检测"),
    CommandPattern(r"msfconsole", RiskLevel.MEDIUM, "Metasploit"),
    CommandPattern(r">>", RiskLevel.MEDIUM, "追加写入文件"),
    CommandPattern(r">", RiskLevel.MEDIUM, "覆盖写入文件"),
]