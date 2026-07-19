# SecAgent 项目交接文档

## 项目概述

SecAgent 是一个专为网络安全研究设计的 CLI Agent，支持交互式配置、多模型提供商、安全命令控制等核心功能。

## 技术栈

| 组件 | 技术方案 |
|------|---------|
| 语言 | Python 3.8+ |
| HTTP 客户端 | requests |
| 配置管理 | pyyaml |
| 缓存 | 文件 + 内存双层缓存 |
| 平台支持 | Linux / Windows |

## 项目结构

```
secagent/
├── secagent/              # 核心代码
│   ├── __init__.py
│   ├── cli/               # 命令行界面
│   │   ├── __init__.py
│   │   ├── interactive.py # 交互式主程序
│   │   └── main.py        # CLI 入口
│   ├── llm/               # LLM 模块
│   │   ├── __init__.py
│   │   ├── client.py      # 动态 LLM 客户端
│   │   ├── config.py      # 配置管理
│   │   ├── cache.py       # 缓存管理器
│   │   ├── thinking.py    # 思考强度预设
│   │   └── model_fetcher.py # 模型列表获取
│   ├── security/          # 安全模块
│   │   ├── __init__.py
│   │   ├── policy.py      # 安全模式枚举
│   │   ├── risk_levels.py # 风险等级规则
│   │   └── safety_manager.py # 安全管理器
│   ├── mcp/               # MCP 框架
│   │   ├── __init__.py
│   │   ├── server.py      # MCP Server
│   │   ├── client.py      # MCP Client
│   │   └── manager.py     # MCP 管理器
│   ├── config/            # 配置模块
│   │   └── __init__.py
│   └── utils/             # 工具模块
│       └── __init__.py
├── config/                # 配置文件
│   └── llm.yaml           # 默认 LLM 配置
├── tests/                 # 测试脚本
│   ├── test_llm.py        # LLM 模块测试
│   ├── test_security.py   # 安全模块测试
│   └── test_mcp.py        # MCP 模块测试
├── secagent.py            # 主入口脚本
├── requirements.txt       # 依赖列表
└── SECAGENT_DELIVERY.md   # 交接文档

```

## 核心功能

### 1. LLM 客户端

支持 OpenAI 和 Anthropic 双提供商，用户可自定义：
- provider: 模型厂商（openai/anthropic）
- model: 模型名称
- base_url: API 基础 URL
- api_key: API 密钥（支持环境变量）
- thinking: 思考强度（low/medium/high/max/ultra）

**思考强度预设：**
| 等级 | Temperature | Max Tokens | 适用场景 |
|------|-------------|-----------|---------|
| low | 0.1 | 1024 | 快速响应 |
| medium | 0.7 | 2048 | 日常任务 |
| high | 0.2 | 4096 | 复杂推理 |
| max | 0.1 | 8192 | 科研分析 |
| ultra | 0.05 | 16384 | 极限深度 |

### 2. 安全管理器

三种命令模式：
| 模式 | 说明 |
|------|------|
| strict | 逐一审批：所有命令需要确认 |
| smart | 智能放行：高危命令需要确认，其他自动放行 |
| yolo | 全部放行：无需确认，自主完成 |

**高危命令黑名单：**
- rm -rf, del /f/s, erase /f/s
- drop, delete from, truncate
- shutdown, reboot, halt, init 0/6
- chmod 777, chmod -R, chown -R
- kill -9, killall
- iptables -F, firewall-cmd --reload

### 3. MCP 框架

简单易扩展的工具调用协议：
```python
# 注册工具
@server.register("nmap_scan", "端口扫描", {"target": "目标IP", "ports": "端口范围"})
def nmap_scan(target, ports="1-1000"):
    return "扫描结果"
```

### 4. 缓存机制

双层缓存架构：
- L1: 内存缓存（进程内，TTL 5分钟）
- L2: 文件缓存（跨进程，TTL 24小时）
- L3: 内置默认列表（离线降级）

## 安装与运行

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行方式

```bash
# 方式1：直接运行
python secagent.py

# 方式2：设置为可执行
chmod +x secagent.py
./secagent.py
```

### 首次运行

首次运行会进入交互式配置：
1. 设置模型提供商
2. 设置 API 基础 URL
3. 设置 API 密钥（直接输入或环境变量）
4. 选择思考强度
5. 获取并选择可用模型
6. 选择安全模式

配置会保存到 `~/.secagent/config.yaml`

## 使用说明

### 命令列表

```
secagent> help

可用命令:
  exit/quit - 退出
  help - 显示帮助
  config - 重新配置
  thinking <level> - 设置思考强度
  safety <mode> - 设置安全模式
  llm <message> - 与 LLM 对话
  其他命令将作为 shell 命令执行
```

### 示例

```bash
# 与 LLM 对话
secagent> llm 帮我分析这段代码的安全漏洞

# 设置思考强度
secagent> thinking high

# 设置安全模式
secagent> safety smart

# 执行 shell 命令（受安全模式控制）
secagent> ls -la
secagent> nmap -p 1-100 192.168.1.1
```

## 测试验证

### 运行测试

```bash
python tests/test_llm.py
python tests/test_security.py
python tests/test_mcp.py
```

### 测试结果

所有测试已通过：
- ✓ LLMConfig 测试通过
- ✓ Thinking 测试通过
- ✓ Cache 测试通过
- ✓ SafetyMode 测试通过
- ✓ SafetyManager 测试通过
- ✓ MCPServer 测试通过

## 配置文件

```yaml
# ~/.secagent/config.yaml
llm:
  provider: openai
  model: gpt-4o
  base_url: https://api.openai.com
  api_key: "${ENV:OPENAI_API_KEY}"
  thinking: medium
```

## 扩展指南

### 添加新的 LLM 提供商

1. 实现 `LLMClient` 接口
2. 在 `client.py` 中添加提供商支持

### 添加新的 MCP 工具

```python
from secagent.mcp.server import MCPServer

server = MCPServer(port=8081)

@server.register("my_tool", "我的工具", {"param1": "参数1"})
def my_tool(param1):
    return "结果"

server.run()
```

### 添加新的思考强度

在 `thinking.py` 的 `THINKING_PRESETS` 中添加新配置。

## 注意事项

1. **API 密钥安全**：建议使用环境变量方式配置 API 密钥，避免硬编码
2. **安全模式选择**：生产环境建议使用 `smart` 或 `strict` 模式
3. **缓存清理**：缓存文件位于 `~/.secagent/cache/`，可定期清理
4. **网络依赖**：模型列表获取需要网络连接，离线时使用内置列表

## 版本信息

- 版本号：0.1.0
- 作者：SecAgent Team
- 描述：Security Agent - CLI based security research agent