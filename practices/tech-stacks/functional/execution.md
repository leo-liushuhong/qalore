# 用例执行规范

qa-execution 的执行标准：断言类型定义、MCP 工具映射、执行规则。

> 章节导航：断言类型权威定义（UI 断言 · 视觉样式断言 · Console 断言 · API 断言 · DB 断言）· 断言规则写入格式 · 执行规则 · 访问方法契约 · MCP 工具使用约定 · 断言校准与验证模式

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
| `element-enabled` | `element-enabled(selector)` | CSS 选择器，元素可用（未 disabled） | `!document.querySelector(selector)?.disabled` |
| `element-disabled` | `element-disabled(selector)` | CSS 选择器，元素禁用（disabled） | `document.querySelector(selector)?.disabled === true` |
| `message-contains` | `message-contains("text")` | 期望文本（不含选择器，固定查 `.el-message__content`） | `.el-message__content` 任一 `.includes("text")` |
| `url-contains` | `url-contains("text")` | 期望 URL 片段 | `page.url().includes("text")` |

### 视觉样式断言（由 Playwright MCP 执行，校验与设计稿一致）

> 样式断言值支持可选 `@档位` 后缀（如 `element-font-size(.title, 14@mobile)`），档位清单见 `contracts.json#assertion_types.environment_qualifier`。验证代码统一 `getComputedStyle` / `getBoundingClientRect`。

| 类型 | 格式 | 参数说明 | Playwright 验证代码 |
|------|------|---------|-------------------|
| `element-color` | `element-color(selector, "rgb(24,144,255)")` | CSS 选择器 + 期望文字颜色 | `getComputedStyle(el).color === "rgb(24, 144, 255)"` |
| `element-background-color` | `element-background-color(selector, "#fff")` | CSS 选择器 + 期望背景色 | `getComputedStyle(el).backgroundColor` |
| `element-font-size` | `element-font-size(selector, 16)` | CSS 选择器 + 期望字号 px | `parseFloat(getComputedStyle(el).fontSize) === 16` |
| `element-font-family` | `element-font-family(selector, "PingFang SC")` | CSS 选择器 + 期望字体族 | `getComputedStyle(el).fontFamily.includes("PingFang SC")` |
| `element-font-weight` | `element-font-weight(selector, "700")` | CSS 选择器 + 期望字重 | `getComputedStyle(el).fontWeight === "700"` |
| `element-padding` | `element-padding(selector, "top", 12)` | CSS 选择器 + 方向(all/top/right/bottom/left) + 期望 px | `parseFloat(getComputedStyle(el).paddingTop) === 12` |
| `element-margin` | `element-margin(selector, "top", 8)` | CSS 选择器 + 方向 + 期望 px | `parseFloat(getComputedStyle(el).marginTop) === 8` |
| `element-size` | `element-size(selector, 380, 640)` | CSS 选择器 + 期望宽 + 期望高 | `el.offsetWidth === 380 && el.offsetHeight === 640` |
| `element-position` | `element-position(selector, 100, 50)` | CSS 选择器 + 期望 x + 期望 y（相对视口） | `getBoundingClientRect(el).x === 100 && .y === 50` |
| `element-border-radius` | `element-border-radius(selector, 8)` | CSS 选择器 + 期望圆角 px | `parseFloat(getComputedStyle(el).borderRadius) === 8` |

### Console 断言（由 Playwright MCP 执行）

| 类型 | 格式 | 参数说明 | Playwright 验证代码 |
|------|------|---------|-------------------|
| `console-error-contains` | `console-error-contains("text")` | 期望文本（console 的 error 级别输出） | `browser_console_messages(level="error")` 任一消息 `.includes("text")` |

### API 断言

> 全部 API 断言由 Playwright MCP 执行（废弃 CDP Network MCP）。被动观察：`browser_network_requests` 列出请求 + `browser_network_request` 读请求/响应体；主动直调：`page.request.get/post`。

| 类型 | 格式 | 参数说明 | 验证逻辑 |
|------|------|---------|---------|
| `api-status` | `api-status(pattern, code)` | URL 正则 + HTTP 状态码 | `browser_network_request` → `response.status === code` |
| `api-field-exists` | `api-field-exists(pattern, "field")` | URL 正则 + JSON 字段名 | `browser_network_request(part="response-body")` → `JSON.parse(body)[field] !== undefined` |
| `api-field-value` | `api-field-value(pattern, "field", val)` | URL 正则 + JSON 字段名 + 期望值 | `browser_network_request(part="response-body")` → `JSON.parse(body)[field] === val` |
| `network-contains` | `network-contains(pattern)` | URL 正则，捕获到匹配该 pattern 的网络请求 | `browser_network_requests` 列表含匹配 URL 的请求 |
| `api-request-field-value` | `api-request-field-value(pattern, "field", val)` | URL 正则 + JSON 字段名 + 期望值（请求体） | `browser_network_request(part="request-body")` → `JSON.parse(body)[field] === val` |
| `api-code` | `api-code(pattern, code)` | URL 正则 + 业务码（区分业务成功/业务拦截，二者可能同为 HTTP 200） | `browser_network_request(part="response-body")` → `JSON.parse(body).code === code` |

### DB 断言

> db-field-value / db-row-count 由 psql 执行（只读 SELECT）。需网关注入 `db_psql_available=true`，否则 SKIP。访问方法契约见 `contracts.json#dependencies.access_methods`。

| 类型 | 格式 | 参数说明 | 验证逻辑 |
|------|------|---------|---------|
| `db-field-value` | `db-field-value(连接, 表, 主键, 字段, 期望值)` | DB 连接引用 + 表名 + 主键值 + 字段名 + 期望值 | `SELECT {字段} FROM {表} WHERE {主键}={值}` → 结果 === 期望值 |
| `db-row-count` | `db-row-count(连接, 表, 条件, 期望数)` | DB 连接引用 + 表名 + WHERE 条件 + 期望行数 | `SELECT COUNT(*) FROM {表} WHERE {条件}` → 结果 === 期望数 |

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
| 参数引号 | 参数含空格或特殊字符时用双引号包裹（如 `"提示文案"`） |
| 类型限域 | 断言类型名必须在本文档定义的 28 种范围内 |

**示例：**

```
1. 展开右侧侧边栏         → 预期：条目按"今天""昨天""近7天""近30天""更早"五组展示
   → 断言：element-count(.item-label, 5)
   → 断言：element-text(.item-label, "今天")

2. 输入框为空点击发送     → 预期：弹出黄色警告"提示文案"
   → 断言：message-contains("提示文案")
```

---

## 执行规则

| 规则 | 说明 |
|------|------|
| 优先级顺序 | P0 → P1 → P2 → P3 |
| 前置条件 | 不满足 → SKIP + 记录原因 |
| 断言缺失 | TC 无任何断言规则 → SKIP（提示通过 qa-functional-test 更新 TC） |
| 失败判定 | 同一条 TC 中任一断言 FAIL → TC 整体标记 FAIL |
| API 断言失败 | `browser_network_requests` 无匹配 pattern 的请求 → FAIL |
| 批量优化 | 同页面的多条断言在单次 `browser_evaluate` 中批量执行 |

---

## 访问方法契约

执行依赖（DB/redis/MQ/第三方/文件/时间/配置）的访问方法分两态，权威定义见 `contracts.json#dependencies.access_methods`：

- `read-verify`（默认）：无副作用，无需确认，直接执行。
- `write-mock`（例外）：有副作用，必须满足安全围栏五边界（`contracts.json#dependencies.safety_fence`）且经人类评审确认（`contracts.json#dependencies.permission_shift_left`），否则执行期机器拦截，不新增判断。

DB 断言（`db-field-value` / `db-row-count`）默认只读 SELECT；需要写 mock（如 UPDATE/SET 造数据）时走上述 write-mock 契约，且写前快照可还原。

---

## MCP 工具使用约定

| 场景 | 首选工具 |
|------|---------|
| 导航到页面 | Playwright `browser_navigate` |
| UI 断言执行 | Playwright `browser_evaluate`（单次批量执行多条 UI 断言） |
| 视觉样式断言执行 | Playwright `browser_evaluate`（getComputedStyle / getBoundingClientRect 批量） |
| Console 断言执行 | Playwright `browser_console_messages`（level=error 过滤运行时错误） |
| API 断言执行 | 被动观察用 Playwright `browser_network_requests` / `browser_network_request`；主动直调用 `browser_run_code_unsafe(page => page.request.*)` |
| 联合断言 | 同一条 TC 中 UI/Console/样式/API 断言全部走 Playwright MCP |

---

## 断言校准与验证模式

左移推理产出的断言是「假设」不是「事实」。执行时分两模式（分流依据见 qa-understand/qa-functional-test 的置信度标注）：

**验证模式**（高置信度断言）：正常 pass/fail，任一断言 FAIL → TC FAIL。

**校准模式**（低置信度断言：`待代码确认` / `⚠️` / 新 feature 推理断言）：首次执行不判 FAIL，产出「校准差异报告」。

三分类归因不变式：

| 归因 | 判据 | 处置 |
|------|------|------|
| 推理失真 | 实测值能被文档另一种解释覆盖 | 自动改断言（可回写） |
| 实现漂移/文档过时 | 实测值与文档明确矛盾 | 上报，人拍板报 bug 还是改文档 |
| 文档输入不完整 | 文档根本没写该细节 | 回写待确认项 |

校准差异报告格式见 story-formats.md「校准差异报告」章节。
