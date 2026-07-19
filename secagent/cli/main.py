#!/usr/bin/env python3

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .interactive import main_interactive


def main():
    parser = argparse.ArgumentParser(description="SecAgent - Security Research Agent")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--thinking", help="思考强度: low/medium/high/max/ultra")
    parser.add_argument("--safety", help="安全模式: strict/smart/yolo")
    args = parser.parse_args()

    main_interactive(
        config_path=args.config,
        thinking=args.thinking,
        safety=args.safety,
    )


if __name__ == "__main__":
    main()
