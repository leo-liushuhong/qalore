# 用例执行规范

qa-execution 的执行标准：断言类型定义、MCP 工具映射、执行规则。

---

## 断言类型权威定义

以下为所有断言类型的**唯一权威来源**。cases.md 引用此文件，不重复定义。
每条断言的语义、参数格式和执行代码在此唯一定义。

### UI 断言（由 Playwright MCP 执行）

| 类型 | 格式 | 参数说明 | Playwright 验证代码 |
|------|------|---------|-------------------|
| `element-exists` | `element-exists(selector)` | CSS 选择器，存在即可 | `!!document.querySelector(selector)` |
| `element-not-exists` | `element-not-exists(selector)` | CSS 选择器，不应存在 | `!document.querySelector(selector)` |
| `element-count` | `element-count(selector, n)` | CSS 选择器 + 期望数量 | `document.querySelectorAll(selector).length === n` |
| `element-text` | `element-text(selector, "text")` | CSS 选择器 + 期望文本 | `el.textContent.includes("text")` |
| `element-width` | `element-width(selector, px)` | CSS 选择器 + 像素值 | `el.offsetWidth === px` |
| `message-contains` | `message-contains("text")` | 期望文本（不含选择器，固定查 `.el-message__content`） | `.el-message__content` 任一 `.includes("text")` |
| `url-contains` | `url-contains("text")` | 期望 URL 片段 | `page.url().includes("text")` |

### API 断言（由 CDP Network MCP 执行）

| 类型 | 格式 | 参数说明 | CDP 验证逻辑 |
|------|------|---------|------------|
| `api-status` | `api-status(pattern, code)` | URL 正则 + HTTP 状态码 | `network_wait(pattern)` → `response.status === code` |
| `api-field-exists` | `api-field-exists(pattern, "field")` | URL 正则 + JSON 字段名 | `network_wait(pattern)` → `JSON.parse(body)[field] !== undefined` |
| `api-field-value` | `api-field-value(pattern, "field", val)` | URL 正则 + JSON 字段名 + 期望值 | `network_wait(pattern)` → `JSON.parse(body)[field] === val` |

---

## 断言规则写入格式（TC 文件中）

每个 `→ 预期：` 后紧跟一个或多个 `→ 断言：`：

```
→ 预期：{人读的自然语言描述}
→ 断言：{类型}({参数})
→ 断言：{类型}({参数})
```

**格式规则：**

| 规则 | 说明 |
|------|------|
| 同步产出 | 断言规则与预期由 qa-functional-test 同步产出，不可后补 |
| 紧跟原则 | `→ 断言：` 行紧接在对应的 `→ 预期：` 行之后 |
| 一对多 | 一个 `→ 预期：` 可对应多个 `→ 断言：` |
| 参数引号 | 参数含空格或特殊字符时用双引号包裹（如 `"请输入请求消息！"`） |
| 类型限域 | 断言类型名必须在本文档定义的 10 种范围内 |

**示例：**

```
1. 展开右侧历史记录栏     → 预期：会话按"今天""昨天""近7天""近30天""更早"五组展示
   → 断言：element-count(.group-label, 5)
   → 断言：element-text(.group-label, "今天")

2. 输入框为空点击发送     → 预期：弹出黄色警告"请输入请求消息！"
   → 断言：message-contains("请输入请求消息！")
```

---

## 执行规则

| 规则 | 说明 |
|------|------|
| 优先级顺序 | P0 → P1 → P2 → P3 |
| 前置条件 | 不满足 → SKIP + 记录原因 |
| 断言缺失 | TC 无任何断言规则 → SKIP（提示通过 qa-functional-test 更新 TC） |
| 失败判定 | 同一条 TC 中任一断言 FAIL → TC 整体标记 FAIL |
| API 超时 | CDP Network MCP 的 `network_wait` 默认超时 15s，超时 → FAIL |
| 批量优化 | 同页面的多条断言在单次 `browser_evaluate` 中批量执行 |

---

## MCP 工具使用约定

| 场景 | 首选工具 |
|------|---------|
| 导航到页面 | Playwright `browser_navigate`（已登录时）/ CDP `navigate_and_capture`（需 API 断言时） |
| UI 断言执行 | Playwright `browser_evaluate`（单次批量执行多条 UI 断言） |
| API 断言执行 | CDP `network_wait` / `network_list` |
| 联合断言 | 同一条 TC 中 UI 断言用 Playwright，API 断言用 CDP |
