import os
import json
import subprocess
from typing import Optional, List
from datetime import datetime

from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.markdown import Markdown
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.rule import Rule
from rich import box
from rich.align import Align

from ..llm.config import LLMConfig
from ..llm.client import LLMClient, LLMRequestError, get_model_context_limit
from ..llm.model_fetcher import ModelFetcher, ModelFetchError
from ..skills.registry import build_runtime_system_prompt
from ..skills.task_parser import parse_security_task
from ..tools.builtin import build_default_registry
from ..tools.loop import ToolLoopError, run_tool_loop
from ..mcp.manager import MCPManager
from ..llm.thinking import list_thinking_levels
from ..llm.cache import ModelCache
from ..security.safety_manager import SafetyManager, ApprovalRequest
from ..security.policy import SafetyMode

console = Console()
_cache = ModelCache()


def print_banner() -> Panel:
    return Panel(
        "[bold cyan]SecAgent[/] - [green]Security Research Agent[/]\n"
        "[dim]专为网络安全研究设计的 CLI Agent[/]",
        box=box.DOUBLE_EDGE,
        border_style="cyan",
        padding=(1, 2),
        title="[bold yellow]🛡️  SECAGENT[/]",
        subtitle="v0.1.0",
    )


def approval_prompt(request: ApprovalRequest) -> bool:
    risk_styles = {
        "critical": "bold red",
        "high": "bold yellow",
        "medium": "bold blue",
        "low": "bold green",
    }
    risk_icons = {
        "critical": "🔥",
        "high": "⚠️",
        "medium": "📌",
        "low": "✅",
    }
    style = risk_styles.get(request.risk_level.value, "")
    icon = risk_icons.get(request.risk_level.value, "")

    panel = Panel(
        f"[{style}]{icon} 风险等级: {request.risk_level.value.upper()}[/]\n\n"
        f"[bold]命令:[/] [white]{request.cmd}[/]\n"
        f"[bold]描述:[/] {request.description}",
        title="[bold red]⚡ 命令审批请求[/]",
        border_style="red",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    console.print(panel)
    return Prompt.ask("是否允许执行", choices=["y", "n"], default="n") == "y"


def configure_llm() -> LLMConfig:
    console.print(Panel.fit("[bold]配置 LLM 参数[/]", border_style="cyan", box=box.ROUNDED))
    provider = Prompt.ask("模型提供商", choices=["openai", "anthropic"], default="openai")
    base_url = Prompt.ask("API 基础 URL", default="https://api.openai.com")

    console.print("\n[bold]API Key 配置:[/]")
    key_option = Prompt.ask("选择方式", choices=["1", "2"], default="1")
    if key_option == "1":
        api_key = Prompt.ask("请输入 API Key", password=True)
    else:
        env_var = Prompt.ask("环境变量名称", default=f"{provider.upper()}_API_KEY")
        api_key = f"${{ENV:{env_var}}}"

    console.print("\n[bold]思考强度:[/]")
    levels = list_thinking_levels()
    table = Table(box=box.SIMPLE, border_style="dim")
    table.add_column("#", style="dim", width=4)
    table.add_column("等级", style="cyan", width=12)
    table.add_column("说明", style="white")
    for i, level in enumerate(levels):
        table.add_row(str(i + 1), level, "")
    console.print(table)
    thinking_idx = IntPrompt.ask("选择思考强度", default=3) - 1
    thinking = levels[thinking_idx]

    def _resolve_api_key(key: str) -> str:
        if key.startswith("${ENV:") and key.endswith("}"):
            return os.environ.get(key[6:-1], "")
        return key

    resolved_api_key = _resolve_api_key(api_key).strip()
    console.print(Panel.fit("[bold yellow]⏳ 正在验证接口并获取可用模型...[/]", border_style="yellow"))
    fetcher = ModelFetcher(provider, resolved_api_key, base_url)
    try:
        models = fetcher.fetch_verified()
    except ModelFetchError as exc:
        console.print(Panel.fit(f"[red]❌ {exc}[/]\n[dim]请先修正 API 地址或 Key，再重新配置。[/]", border_style="red"))
        return configure_llm()

    model_table = Table(title="[bold]可用模型[/]", box=box.ROUNDED, border_style="cyan", highlight=True)
    model_table.add_column("#", style="dim", width=4)
    model_table.add_column("模型 ID", style="bold green", no_wrap=True)
    model_table.add_column("优点", style="green")
    model_table.add_column("缺点", style="red")
    for i, model in enumerate(models):
        pros = ", ".join(model.get("pros", [])) or "—"
        cons = ", ".join(model.get("cons", [])) or "—"
        model_table.add_row(str(i + 1), model["id"], pros, cons)
    console.print(model_table)

    model_idx = IntPrompt.ask("选择模型编号", default=1) - 1
    model = models[model_idx]["id"]

    config = LLMConfig(provider=provider, model=model, base_url=base_url, api_key=api_key, thinking=thinking)
    config_path = os.path.expanduser("~/.secagent/config.yaml")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    config.to_yaml(config_path)
    console.print(Panel.fit(f"[green]✅ 配置已保存到:[/] [bold]{config_path}[/]", border_style="green"))
    return config


def configure_safety() -> SafetyMode:
    console.print(Panel.fit("[bold]配置安全模式[/]", border_style="cyan", box=box.ROUNDED))
    mode_table = Table(box=box.SIMPLE, border_style="dim")
    mode_table.add_column("#", style="dim", width=4)
    mode_table.add_column("模式", style="bold", width=12)
    mode_table.add_column("说明", style="white")
    mode_table.add_row("1", "strict", "逐一审批：所有命令需要确认")
    mode_table.add_row("2", "smart", "智能放行：高危命令确认，其他自动放行")
    mode_table.add_row("3", "yolo", "全部放行：无需确认，自主完成（谨慎使用）")
    console.print(mode_table)
    while True:
        choice = Prompt.ask("选择安全模式", choices=["1", "2", "3"], default="2")
        if choice == "1":
            return SafetyMode.STRICT
        elif choice == "2":
            return SafetyMode.SMART
        elif choice == "3":
            return SafetyMode.YOLO


def execute_command(cmd: str) -> dict:
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "命令执行超时", "stdout": "", "stderr": ""}
    except Exception as e:
        return {"success": False, "error": str(e), "stdout": "", "stderr": ""}


def build_status_bar(config: LLMConfig, safety_mode: SafetyMode, llm_client: LLMClient) -> Panel:
    """构建精简单行状态栏"""
    model = config.model
    context_limit = get_model_context_limit(model)
    usage = llm_client.last_usage
    total_used = usage.get("total_tokens", 0)
    context_pct = (total_used / context_limit * 100) if context_limit > 0 else 0

    # 上下文用量颜色
    if context_pct < 50:
        ctx_color = "green"
    elif context_pct < 80:
        ctx_color = "yellow"
    else:
        ctx_color = "red"

    # 安全模式颜色
    if safety_mode == SafetyMode.YOLO:
        safety_color = "bold red"
    elif safety_mode == SafetyMode.STRICT:
        safety_color = "yellow"
    else:
        safety_color = "green"

    # 缓存命中率
    cache_rate = _cache.get_cache_hit_rate()
    cache_color = "green" if cache_rate > 50 else "dim"

    # 会话消耗
    session = llm_client.session_stats
    cost = session.get("cost", 0)

    status_text = Text.assemble(
        (" 🤖 ", ""),
        (f"{model}", "bold bright_cyan"),
        (" │ ", "dim"),
        ("🧠 ", ""),
        (f"{config.thinking}", "magenta"),
        (" │ ", "dim"),
        ("🛡️ ", ""),
        (f"{safety_mode.value}", safety_color),
        (" │ ", "dim"),
        ("📊 ", ""),
        (f"{total_used:,}/{context_limit:,}", ctx_color),
        (f" ({context_pct:.1f}%)", "dim"),
        (" │ ", "dim"),
        ("💾 ", ""),
        (f"{cache_rate:.0f}%", cache_color),
        (" │ ", "dim"),
        ("💰 ", ""),
        (f"¥{cost:.4f}", "bright_yellow"),
    )

    return Panel(
        status_text,
        border_style="bright_black",
        box=box.SQUARE,
        padding=(0, 1),
        height=3,
    )


def build_input_box(placeholder: bool = True, current_input: str = "") -> Panel:
    """构建底部输入框

    placeholder=True 时显示占位提示，False 时显示当前输入内容
    """
    if placeholder:
        content = Text.assemble(
            ("❯ ", "bold cyan"),
            ("输入消息，按 Enter 发送 · ", "dim"),
            ("!cmd", "yellow"),
            (" 执行命令 · ", "dim"),
            ("help", "green"),
            (" 查看帮助", "dim"),
        )
        border_style = "cyan"
        title = "[bold cyan]💬 输入[/]"
    else:
        content = Text.assemble(
            ("❯ ", "bold cyan"),
            (current_input, "bold white"),
            ("_", "cyan blink"),
        )
        border_style = "bright_cyan"
        title = "[bold bright_cyan]💬 输入[/]"

    return Panel(
        content,
        border_style=border_style,
        box=box.HEAVY,
        padding=(0, 1),
        height=3,
        title=title,
        title_align="left",
    )


def build_conversation_body(conversation: List) -> Panel:
    """构建对话正文"""
    if not conversation:
        welcome = Text.assemble(
            ("\n\n", ""),
            ("🛡️  ", "bold cyan"),
            ("欢迎使用 SecAgent", "bold white"),
            ("\n\n", ""),
            ("专为网络安全研究设计的 CLI Agent\n\n", "dim"),
            ("  ❯  ", "bold cyan"),
            ("直接输入内容与 AI 对话\n", "white"),
            ("  ❯  ", "bold yellow"),
            ("输入 ", "white"),
            ("!command", "yellow"),
            (" 执行 shell 命令\n", "white"),
            ("  ❯  ", "bold green"),
            ("输入 ", "white"),
            ("help", "green"),
            (" 查看所有命令\n\n", "white"),
        )
        return Panel(
            Align.center(welcome, vertical="middle"),
            border_style="bright_black",
            box=box.ROUNDED,
            padding=(1, 2),
            title="[bold bright_black]💬 对话[/]",
        )

    return Panel(
        Group(*conversation),
        border_style="bright_black",
        box=box.ROUNDED,
        padding=(1, 2),
        title="[bold bright_black]💬 对话[/]",
    )


def main_interactive(
    config_path: Optional[str] = None,
    thinking: Optional[str] = None,
    safety: Optional[str] = None,
):
    console.clear()

    # ── 初始配置 ──
    console.print(print_banner())
    config_path = os.path.expanduser(config_path or "~/.secagent/config.yaml")

    if os.path.exists(config_path):
        if Prompt.ask("发现现有配置，是否使用？", choices=["y", "n"], default="y") == "y":
            config = LLMConfig.from_yaml(config_path)
        else:
            config = configure_llm()
    else:
        config = configure_llm()

    if thinking and thinking in list_thinking_levels():
        config.thinking = thinking

    safety_mode = SafetyMode.from_string(safety) if safety else configure_safety()
    safety_manager = SafetyManager(safety_mode)
    safety_manager.set_approval_callback(approval_prompt)
    llm_client = LLMClient(config)
    mcp_manager = MCPManager()
    tool_registry = build_default_registry(safety_manager, mcp_manager)

    # ── 交互循环（静态渲染：每次输入前清屏重绘，输入框边框始终可见）──
    conversation: List = []

    # Layout 仅用于流式响应期间的实时刷新
    layout = Layout()
    layout.split_column(
        Layout(name="body", ratio=1, minimum_size=10),
        Layout(name="status", size=3),
        Layout(name="input", size=3),
    )

    def render_screen():
        """静态渲染整个屏幕：对话区（自适应高度）+ 状态栏 + 输入框"""
        console.clear()
        console.print(build_conversation_body(conversation))
        console.print(build_status_bar(config, safety_mode, llm_client))
        console.print(build_input_box(placeholder=True))

    while True:
        render_screen()
        try:
            cmd = console.input("[bold bright_cyan]❯ [/]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[bold yellow]👋 再见！[/]")
            break

        if not cmd:
            continue

        # ── exit ──
        if cmd in ("exit", "quit"):
            console.print("\n[bold yellow]👋 再见！[/]")
            break

        # ── help ──
        if cmd == "help":
            help_table = Table(box=box.ROUNDED, border_style="cyan", show_header=False, padding=(0, 2))
            help_table.add_column("命令", style="bold green", no_wrap=True)
            help_table.add_column("说明", style="white")
            help_table.add_row("exit / quit", "退出程序")
            help_table.add_row("help", "显示帮助信息")
            help_table.add_row("config", "重新配置 LLM 参数")
            help_table.add_row("thinking <level>", "设置思考强度 (low/medium/high/max/ultra)")
            help_table.add_row("safety <mode>", "设置安全模式 (strict/smart/yolo)")
            help_table.add_row("!<command>", "执行 shell 命令（如 !dir）")
            help_table.add_row("<text>", "直接输入内容与 AI 对话")
            conversation.append(Panel(help_table, title="[bold]📖 帮助[/]", border_style="cyan"))
            continue

        # ── config ──
        if cmd.startswith("config"):
            config = configure_llm()
            llm_client = LLMClient(config)
            tool_registry = build_default_registry(safety_manager, mcp_manager)
            conversation = []
            conversation.append(Panel(
                "[green]✅ 配置已更新，已清空对话历史[/]",
                border_style="green",
                box=box.ROUNDED,
            ))
            continue

        # ── thinking ──
        if cmd.startswith("thinking "):
            level = cmd.split()[1]
            if level in list_thinking_levels():
                llm_client.set_thinking(level)
                conversation.append(Text(f"✅ 思考强度已设置为: {level}", style="green"))
            else:
                conversation.append(Text(f"❌ 无效的思考强度: {level}", style="red"))
            continue

        # ── safety ──
        if cmd.startswith("safety "):
            mode = cmd.split()[1]
            if mode in SafetyMode.list_values():
                safety_mode = SafetyMode.from_string(mode)
                safety_manager.set_mode(safety_mode)
                conversation.append(Text(f"✅ 安全模式已设置为: {mode}", style="green"))
            else:
                conversation.append(Text(f"❌ 无效的安全模式: {mode}", style="red"))
            continue

        # ── 执行 shell 命令 ──
        if cmd.startswith("!"):
            shell_cmd = cmd[1:].strip()
            if not shell_cmd:
                conversation.append(Text("请输入要执行的 shell 命令，例如: !dir", style="yellow"))
                continue

            start_time = datetime.now()
            result = safety_manager.execute_with_safety(shell_cmd, execute_command)
            elapsed = (datetime.now() - start_time).total_seconds()

            if result.get("blocked"):
                msg = Panel(
                    f"[red]❌ {result.get('error')}[/]",
                    title=f"[bold red]⛔ 命令被阻止: $ {shell_cmd}[/]",
                    border_style="red",
                    box=box.ROUNDED,
                )
            else:
                output = ""
                if result.get("stdout"):
                    output += result["stdout"].rstrip()
                if result.get("stderr"):
                    output += f"\n[red]{result['stderr'].rstrip()}[/]"

                if output:
                    msg = Panel(
                        output,
                        title=f"[bold green]🖥️  $ {shell_cmd}[/]",
                        subtitle=f"[dim]完成 ({elapsed:.1f}s)  exit code: {result.get('returncode', '?')}[/]",
                        border_style="green",
                        box=box.ROUNDED,
                    )
                else:
                    msg = Panel(
                        f"[green]✅ 命令执行完成 (exit code: {result.get('returncode', '?')})[/]",
                        title=f"$ {shell_cmd}",
                        border_style="green",
                        box=box.ROUNDED,
                    )

            conversation.append(msg)
            continue

        # ── 默认：LLM 对话 ──
        # 用户消息（右对齐标题，模拟聊天应用）
        user_msg = Panel(
            Text(cmd, style="white"),
            title="[bold cyan]👤 你[/]",
            title_align="right",
            border_style="cyan",
            box=box.SQUARE,
            padding=(0, 1),
        )
        conversation.append(user_msg)

        # 流式请求 LLM，实时更新
        response_chunks = []
        thinking_panel = Panel(
            "[dim]🤔 思考中...[/]",
            title="[bold green]🤖 AI[/]",
            title_align="left",
            border_style="green",
            box=box.SQUARE,
            padding=(0, 1),
        )
        conversation.append(thinking_panel)

        task = parse_security_task(cmd)
        selected_skills, runtime_system_prompt = build_runtime_system_prompt(cmd, task.to_context())
        if selected_skills:
            conversation.append(Text(
                f"技能路由: {', '.join(selected_skills)} | 目标: {', '.join(task.targets) or '待识别'}",
                style="dim cyan",
            ))

            try:
                content, trace = run_tool_loop(
                    llm_client,
                    cmd,
                    runtime_system_prompt,
                    tool_registry,
                )
                conversation.pop()
                for event in trace:
                    conversation.append(Panel(
                        f"工具: {event['tool']}\n参数: {event['arguments']}\n结果: {event['result']}",
                        title=f"🔧 工具执行 #{event['round']}",
                        border_style="yellow",
                        box=box.SQUARE,
                    ))
                conversation.append(Panel(
                    Markdown(content or "模型未返回文本结果"),
                    title="[bold green]🤖 AI[/]",
                    border_style="green",
                    box=box.SQUARE,
                ))
            except (LLMRequestError, ToolLoopError) as exc:
                conversation[-1] = Panel(
                    f"[red]❌ {exc}[/]",
                    title="[bold red]🤖 AI[/]",
                    border_style="red",
                    box=box.SQUARE,
                )
            continue

        # 流式响应期间用 Live 实时刷新整个屏幕
        with Live(layout, refresh_per_second=10, screen=False, transient=False) as live:
            layout["body"].update(build_conversation_body(conversation))
            layout["status"].update(build_status_bar(config, safety_mode, llm_client))
            layout["input"].update(build_input_box(placeholder=True))
            live.update(layout)

            try:
                for chunk in llm_client.stream(cmd, system=runtime_system_prompt):
                    response_chunks.append(chunk)
                    md = Markdown("".join(response_chunks).strip())
                    ai_panel = Panel(
                        md,
                        title="[bold green]🤖 AI[/]",
                        title_align="left",
                        border_style="green",
                        box=box.SQUARE,
                        padding=(0, 1),
                    )
                    conversation[-1] = ai_panel
                    layout["body"].update(build_conversation_body(conversation))
                    layout["status"].update(build_status_bar(config, safety_mode, llm_client))
                    live.update(layout)
            except KeyboardInterrupt:
                conversation[-1] = Panel(
                    "[yellow]⚠️ 已取消本次模型请求[/]",
                    title="[bold yellow]🤖 AI[/]",
                    title_align="left",
                    border_style="yellow",
                    box=box.SQUARE,
                    padding=(0, 1),
                )
            except LLMRequestError as exc:
                conversation[-1] = Panel(
                    f"[red]❌ {exc}[/]\n[dim]可执行 `config` 重新配置模型，或检查网络/API Key。[/]",
                    title="[bold red]🤖 AI[/]",
                    title_align="left",
                    border_style="red",
                    box=box.SQUARE,
                    padding=(0, 1),
                )
