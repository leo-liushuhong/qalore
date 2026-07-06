---
name: qa-execution
description: >
  测试用例执行。读取 TC 文件中的断言规则，通过 Playwright MCP + CDP Network MCP
  在浏览器中逐条执行，产出执行报告。不修改 TC 文件。
practices_min_version: "2026-06-24-v19"
---

# qa-execution：测试用例执行

## 前置说明

| 变量 | 来源 |
|------|------|
| `{practices_path}` | qalore 注入 |
| `{story_path}` | qalore 注入 |
| `{确认项目名}` | qalore 注入 |
| `{执行环境 URL}` | qalore 注入（用户提供，或从 story/index.json 的 test_url 字段读取） |

## 触发条件

用户描述含「执行/跑/运行 + 用例/测试/TC/模块」之一，且意图为执行已有测试用例。

## 前置依赖

- **Playwright MCP**：必须已配置，由网关环境验证阶段检查
- **CDP Network MCP**：内嵌于本 capability 的 `cdp_network/server.py`，执行时启动
- **TC 文件含断言规则**：无断言规则 → SKIP + 提示「请通过 qa-functional-test 更新 TC」

## 执行流程

```
1. 解析用户意图，确定执行范围：
   - 全部模块 → 遍历 story/{项目}/ 下所有模块目录
   - 单模块 → 仅该模块
   - 单条 TC → 仅该 TC
   - 指定优先级 → 仅执行匹配优先级的 TC

2. 读取目标 TC 文件，提取所有含断言规则的用例

3. 按优先级排序执行（P0 → P1 → P2 → P3）

4. 逐条执行：
   a. 检查前置条件可满足性 → 不满足 → SKIP + 原因
   b. 按测试步骤顺序执行操作（导航/点击/输入）
   c. 执行断言规则：
      - UI 断言 → Playwright MCP browser_evaluate（批量）
      - API 断言 → CDP Network MCP network_wait / network_list
   d. 记录结果：PASS（实测值）/ FAIL（实测值 vs 预期值）/ SKIP（原因）

5. 输出执行报告

6. 输出【待沉淀】声明
```

## 断言类型速查

**UI 断言（Playwright MCP）：**

| 类型 | 示例 |
|------|------|
| `element-exists` | `element-exists(.new-chat-btn)` |
| `element-not-exists` | `element-not-exists(.new-chat-btn)` |
| `element-count` | `element-count(.group-label, 5)` |
| `element-text` | `element-text(.sidebar-title, "历史记录")` |
| `element-width` | `element-width(.chat-sidebar, 380)` |
| `message-contains` | `message-contains("请输入请求消息！")` |
| `url-contains` | `url-contains("/login")` |

**API 断言（CDP Network MCP）：**

| 类型 | 示例 |
|------|------|
| `api-status` | `api-status(/api/agent/.*/sessions, 200)` |
| `api-field-exists` | `api-field-exists(/api/agent/.*/sessions, "total")` |
| `api-field-value` | `api-field-value(/api/agent/.*/sessions, "total", 9)` |

完整定义和验证代码见 `{practices_path}/tech-stacks/functional/execution.md`。

## CDP Network MCP

本 capability 内嵌 CDP Network MCP 于 `cdp_network/server.py`。

**首次安装依赖：**
```
pip install websocket-client requests
```

**执行时启动：**
```
python {qa-execution 目录}/cdp_network/server.py
```

## 执行报告格式

每次执行**覆盖写入** `{story_path}/{项目}/{模块}/{模块}-功能-执行报告.md`：

```markdown
# {模块名} 执行报告
> 执行时间: {ISO 8601} | 工具: Playwright MCP + CDP Network MCP | 环境: {URL}

| TC ID | 标题 | 结果 | 实测 |
|-------|------|------|------|
| TC-DIA-006 | 侧栏380px | PASS | 380px |
| TC-DIA-007 | 时间段分组 | PASS | 今天(8)/昨天(1) |
| TC-DIA-011 | 新建对话按钮 | PASS | AgentRun显示/AgentList隐藏 |
| TC-DIA-016 | 空输入校验 | PASS | "请输入请求消息！" |

汇总: 总 {n} | PASS {x} | FAIL {y} | SKIP {z} | 通过率 {x/n * 100}%
```

## 【待沉淀】声明

执行完成后输出：

```
【待沉淀】
| 文件 | 路径 | 操作 | 变更摘要 |
|------|------|------|---------|
| {模块}-功能-执行报告.md | {路径}/ | 覆盖写入 | {n} 条执行，PASS {x} / FAIL {y} / SKIP {z} |
```
