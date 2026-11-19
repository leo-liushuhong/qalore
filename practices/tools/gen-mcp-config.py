#!/usr/bin/env python3
"""
qalore MCP 配置生成器（可移植方案）。

读取 contracts.json 的 external_tools 中的 MCP 工具，生成目标 agent 的 MCP 配置（三要素：
传输方式 / 启动命令 / 凭证占位）。凭证一律输出占位符，由用户自行填入。

用法：
    python3 gen-mcp-config.py [--agent dsh|claude-code]

输出：目标 agent 格式的 MCP 配置 JSON 片段（含凭证占位符），供用户粘贴到对应配置文件。
"""

import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CONFIG_PATH = os.path.expanduser("~/.dsh/qalore-config.json")

# MCP 服务器三要素（传输方式 / 启动命令 / 凭证占位）
MCP_SERVERS = {
    "playwright_mcp": {
        "transport": "stdio",
        "command": "npx",
        "args": ["@playwright/mcp@latest"],
        "credential": None,
    },
    "figma_mcp": {
        "transport": "stdio",
        "command": "npx",
        "args": ["@anthropic-ai/figma-mcp"],  # 具体包名按实际 figma mcp server 调整
        "credential": "{Figma Token}",       # 需用户填
    },
    "yunxiao_mcp": {
        "transport": "sse",
        "url": "{云效 MCP 服务地址}",          # 需用户填
        "credential": "{云效 Token}",          # 需用户填
    },
}

AGENT_CONFIG_KEYS = {
    "dsh": {"mcp_servers_key": "mcpServers", "config_path": "~/.dsh/mcp.json"},
    "claude-code": {"mcp_servers_key": "mcpServers", "config_path": "~/.claude.json"},
}


def load_contracts():
    with open(CONFIG_PATH, encoding="utf-8-sig") as f:
        cfg = json.load(f)
    with open(os.path.join(cfg["practices_path"], "contracts.json"), encoding="utf-8") as f:
        return json.load(f)


def main():
    agent = "dsh"
    for i, a in enumerate(sys.argv[1:]):
        if a == "--agent" and i + 1 < len(sys.argv[1:]):
            agent = sys.argv[i + 2]
    contracts = load_contracts()
    tools = contracts.get("external_tools", {}).get("tools", {})

    mcp = {}
    for name, t in tools.items():
        if t.get("type") != "mcp":
            continue
        spec = MCP_SERVERS.get(name)
        if not spec:
            continue
        entry = {}
        if spec["transport"] == "stdio":
            entry = {
                "command": spec["command"],
                "args": spec["args"],
            }
        elif spec["transport"] == "sse":
            entry = {"url": spec["url"]}
        if spec.get("credential"):
            entry["env"] = {"TOKEN": spec["credential"]}
        mcp[name] = entry

    key = AGENT_CONFIG_KEYS.get(agent, AGENT_CONFIG_KEYS["dsh"])
    print(f"# {agent} 的 MCP 配置（粘贴到 {key['config_path']}）")
    print("# ⏳ 占位符需用户自行填入真实凭证")
    print(json.dumps({key["mcp_servers_key"]: mcp}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
