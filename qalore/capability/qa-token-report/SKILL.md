---
name: qa-token-report
description: >
  Token 使用统计能力。由 Claude Code Stop Hook 自动触发，不由 qalore 主动调用。
  从 transcript JSONL 累加本轮所有 API call 的 usage 数据，以固定格式打印到对话。
  仅统计本轮；通过 last_assistant_message 信号词过滤，非 qalore 会话静默退出；无需额外 API 调用。
practices_min_version: "2026-06-12-v11"
---

# qa-token-report：Token 使用统计

## 前置说明

本 capability 由 Claude Code **Stop Hook** 自动触发，不由 qalore 主动调用。
qalore SKILL.md 中注册此能力仅用于标记其存在；实际执行由 hook 完成。

---

## 数据来源

```
Stop Hook stdin
  └── last_assistant_message  →  关键词过滤（非 qalore 静默退出）
  └── transcript_path         →  读 JSONL，找本轮起点（最后一条无 toolUseResult 的 user 消息）
                                     └── 收集起点后全部唯一 type=assistant 记录
                                             └── message.usage 字段（每条记录独立完整）
```

### qalore 信号词（任一匹配即触发）

| 信号词 | 出现场景 |
|--------|---------|
| `TC-` | 测试用例 ID（计划轮 + 执行轮）|
| `.mm` | 产物文件路径（执行轮）|
| `用例总计` | 执行结束摘要 |
| `用例总数` | story 文件头引用 |
| `【功能测试执行计划】` | 功能测试计划展示轮 |
| `【测试意图理解执行计划】` | 测试意图理解计划展示轮 |
| `【用例评审执行计划】` | 用例评审计划展示轮 |
| `【用例评审报告】` | 用例评审结果展示轮 |

**均不匹配** → `sys.exit(0)`，静默退出，不打印任何内容。

---

## 提取字段（A 层，全部精确）

一次 qalore 任务包含多次 API call，各字段取值方式不同：

| 字段 | 取值方式 | 说明 |
|------|----------|------|
| `output_tokens` | **本轮累加** | 所有 API call 生成 token 的总量 |
| `cache_creation_input_tokens` | **本轮累加** | 本轮写入 prompt cache 的总量 |
| `cache_creation.ephemeral_5m/1h` | **本轮累加** | cache_creation 细分 |
| `input_tokens` | 取最后一条 | 最终上下文规模；中间 call 的 input 已被 cache 覆盖，累加会重复计算 |
| `cache_read_input_tokens` | 取最后一条 | 最终缓存读取量（同上，不累加）|

---

## 实现文件

```
capability/qa-token-report/
  SKILL.md          ← 本文件
  probe_hook.py     ← 一次性探测脚本（已完成使命，保留备用）
  read_usage.py     ← 正式脚本，Stop Hook 调用此文件
```

Stop Hook 配置位于 `~/.claude/settings.json`：
```json
"hooks": {
  "Stop": [{
    "hooks": [{
      "type": "command",
      "command": "python \"%USERPROFILE%/.claude/skills/qalore/capability/qa-token-report/read_usage.py\""
    }]
  }]
}
```

---

## 输出格式

```
────────────────────────────────────────────────────
Token 统计（本轮 9 次 API call 合计）

  输出（本轮累计）           20,895 tokens
  缓存写入（本轮累计）       27,534 tokens
    └ 5m 缓存                27,534 tokens
  输入（最终上下文）              8 tokens
  缓存读取                  517,035 tokens

  服务层级             standard
  响应速度             standard
────────────────────────────────────────────────────
```

- output + cache_creation：本轮所有 API call 累加，反映实际生产量
- input + cache_read：取最后一条，反映上下文规模
- API call 次数：标注在标题行，帮助判断任务复杂度
