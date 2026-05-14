#!/usr/bin/env python3
"""AtomCode2API 配置检查和辅助工具"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    get_access_token,
    load_atomcode_config,
    load_atomcode_auth,
    ATOMCODE_CONFIG_DIR,
    ATOMCODE_CONFIG_PATH,
    ATOMCODE_AUTH_PATH,
    SERVER_HOST,
    SERVER_PORT,
    DEFAULT_MODEL,
    API_BASE_URL,
    fetch_codingplan_models,
    get_model_list,
)


def check():
    print("=" * 50)
    print("  AtomCode2API 环境检查")
    print("=" * 50)

    print(f"\n[配置目录] {ATOMCODE_CONFIG_DIR}")
    print(f"  存在: {'是' if ATOMCODE_CONFIG_DIR.exists() else '否'}")

    print(f"\n[认证文件] {ATOMCODE_AUTH_PATH}")
    print(f"  存在: {'是' if ATOMCODE_AUTH_PATH.exists() else '否'}")
    if ATOMCODE_AUTH_PATH.exists():
        auth = load_atomcode_auth()
        print(f"  用户: {auth.get('user', {}).get('username', '未知')}")

    token = get_access_token()
    print(f"\n[Access Token] {'已配置 (' + token[:8] + '...)' if token else '未找到'}")

    print(f"\n[上游 API] {API_BASE_URL}")
    print(f"\n[服务配置]")
    print(f"  监听: {SERVER_HOST}:{SERVER_PORT}")
    print(f"  默认模型: {DEFAULT_MODEL}")

    print(f"\n[检测 CodingPlan 可用模型...]")
    models = asyncio.run(fetch_codingplan_models())
    if models:
        for m in models:
            name = m.get("display_model_name", "unknown")
            exclusive = "独占" if m.get("is_atomcode_exclusive") else "公开"
            infinity = "无限" if m.get("is_infinity") else "有限"
            print(f"  - {name:40s} [{exclusive}/{infinity}]")
    else:
        print("  未检测到模型（可能未登录）")

    print(f"\n[使用说明]")
    print(f"  1. 先运行 'atomcode login' 登录 AtomGit 账号")
    print(f"  2. 运行 'atomcode codingplan' 领取免费额度")
    print(f"  3. 启动本服务: python server.py")
    print(f"  4. 使用 OpenAI SDK 连接 http://localhost:{SERVER_PORT}/v1")
    print()


if __name__ == "__main__":
    check()
