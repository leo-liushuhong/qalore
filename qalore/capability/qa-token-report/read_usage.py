#!/usr/bin/env python3
"""
read_usage.py - 从 transcript JSONL 读取本轮全量 token 使用量并打印到对话。
统计从本轮用户消息到 Stop Hook 触发期间所有 API call 的 token 合计：
  - output_tokens / cache_creation：累加（代表本轮实际生成和写入缓存的量）
  - input_tokens / cache_read：取最后一条（代表上下文规模，累加会重复计算）
由 Claude Code Stop Hook 调用，stdin 为 Stop Hook JSON（含 transcript_path）。
"""
import sys
import json
from pathlib import Path
import threading


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    # ── 读 stdin（带 3s 超时）──
    raw_holder = [None]

    def _read():
        try:
            raw_holder[0] = sys.stdin.buffer.read().decode('utf-8', errors='replace')
        except Exception:
            raw_holder[0] = ''

    t = threading.Thread(target=_read, daemon=True)
    t.start()
    t.join(timeout=3.0)
    raw = raw_holder[0] or ''

    # ── 解析 Stop Hook JSON ──
    try:
        hook_data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        hook_data = {}

    # ── qalore 会话过滤 ──
    QALORE_SIGNALS = [
        'TC-', '.mm', '用例总计', '用例总数',
        '【功能测试执行计划】', '【测试意图理解执行计划】',
        '【用例评审执行计划】', '【用例评审报告】',
    ]
    last_msg = hook_data.get('last_assistant_message', '')
    if not any(s in last_msg for s in QALORE_SIGNALS):
        return

    transcript_path = hook_data.get('transcript_path', '')
    if not transcript_path or not Path(transcript_path).exists():
        return

    # ── 读取全部 transcript 条目 ──
    entries = []
    with open(transcript_path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    # ── 找本轮起点 ──
    last_user_idx = -1
    for i, entry in enumerate(entries):
        if entry.get('type') == 'user' and not entry.get('toolUseResult'):
            last_user_idx = i

    # ── 收集本轮所有唯一 assistant 条目 ──
    turn_usages = []
    seen_uuid = set()
    source = entries[last_user_idx + 1:] if last_user_idx >= 0 else entries

    for entry in source:
        if entry.get('type') != 'assistant':
            continue
        uuid = entry.get('uuid', '')
        if uuid in seen_uuid:
            continue
        seen_uuid.add(uuid)
        usage = entry.get('message', {}).get('usage')
        if usage:
            turn_usages.append(usage)

    if not turn_usages:
        return

    # ── 计算各指标 ──
    total_output       = sum(u.get('output_tokens', 0)                   for u in turn_usages)
    total_cache_create = sum(u.get('cache_creation_input_tokens', 0)      for u in turn_usages)
    total_cc_5m        = sum(u.get('cache_creation', {}).get('ephemeral_5m_input_tokens', 0) for u in turn_usages)
    total_cc_1h        = sum(u.get('cache_creation', {}).get('ephemeral_1h_input_tokens', 0) for u in turn_usages)

    last           = turn_usages[-1]
    last_input     = last.get('input_tokens', 0)
    last_cache_read = last.get('cache_read_input_tokens', 0)

    api_calls      = len(turn_usages)
    service_tier   = last.get('service_tier', '')
    speed          = last.get('speed', '')
    stu            = last.get('server_tool_use', {})
    web_search     = stu.get('web_search_requests', 0)
    web_fetch      = stu.get('web_fetch_requests', 0)

    # ── 格式化输出 ──
    def fmt(n):
        return f"{n:,}"

    W = 52
    lines = []
    lines.append("─" * W)
    lines.append(f"Token 统计（本轮 {api_calls} 次 API call 合计）")
    lines.append("")

    lines.append(f"  输出（本轮累计）     {fmt(total_output):>12} tokens")

    if total_cache_create > 0:
        lines.append(f"  缓存写入（本轮累计） {fmt(total_cache_create):>12} tokens")
        if total_cc_5m > 0:
            lines.append(f"    └ 5m 缓存          {fmt(total_cc_5m):>12} tokens")
        if total_cc_1h > 0:
            lines.append(f"    └ 1h 缓存          {fmt(total_cc_1h):>12} tokens")

    lines.append(f"  输入（最终上下文）   {fmt(last_input):>12} tokens")

    if last_cache_read > 0:
        lines.append(f"  缓存读取             {fmt(last_cache_read):>12} tokens")

    if service_tier or speed:
        lines.append("")
        if service_tier:
            lines.append(f"  服务层级             {service_tier}")
        if speed:
            lines.append(f"  响应速度             {speed}")

    if web_search > 0 or web_fetch > 0:
        lines.append("")
        if web_search > 0:
            lines.append(f"  Web Search           {web_search:>12} 次")
        if web_fetch > 0:
            lines.append(f"  Web Fetch            {web_fetch:>12} 次")

    known = {
        'input_tokens', 'output_tokens',
        'cache_creation_input_tokens', 'cache_read_input_tokens',
        'cache_creation', 'server_tool_use',
        'service_tier', 'speed', 'inference_geo', 'iterations'
    }
    extras = {k: v for k, v in last.items() if k not in known and v}
    if extras:
        lines.append("")
        lines.append("  其他字段")
        for k, v in extras.items():
            lines.append(f"    {k}: {v}")

    lines.append("─" * W)

    print(json.dumps({"systemMessage": "\n".join(lines)}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        pass
