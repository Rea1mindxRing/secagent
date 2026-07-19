THINKING_PRESETS = {
    "low": {
        "temperature": 0.1,
        "max_tokens": 1024,
        "top_p": 0.5,
        "description": "快速响应，确定性高，适合简单任务"
    },
    "medium": {
        "temperature": 0.7,
        "max_tokens": 2048,
        "top_p": 0.9,
        "description": "平衡速度与质量，适合日常任务"
    },
    "high": {
        "temperature": 0.2,
        "max_tokens": 4096,
        "top_p": 0.95,
        "description": "深度思考，适合复杂推理和代码分析"
    },
    "max": {
        "temperature": 0.1,
        "max_tokens": 8192,
        "top_p": 0.99,
        "description": "最大思考深度，适合科研和安全分析"
    },
    "ultra": {
        "temperature": 0.05,
        "max_tokens": 16384,
        "top_p": 1.0,
        "description": "极限思考模式，协调多智能体并行处理"
    }
}


def get_thinking_params(level: str) -> dict:
    return THINKING_PRESETS.get(level, THINKING_PRESETS["medium"])


def list_thinking_levels() -> list:
    return list(THINKING_PRESETS.keys())