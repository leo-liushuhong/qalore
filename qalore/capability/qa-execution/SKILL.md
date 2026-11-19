---
name: qa-execution
description: >
  自动化测试执行。读取 TC 文件中的断言规则，通过 Playwright MCP
  在浏览器中逐条执行（UI/Console/API/样式断言统一走 Playwright，废弃 CDP Network MCP），产出执行报告。不修改 TC 文件。
practices_min_version: "2026-11-18-v1"
---

# qa-execution：自动化测试执行

## 前置说明

| 变量 | 来源 | fallback |
|------|------|---------|
| `{practices_path}` | qalore 注入 | 自动恢复：读 `~/.dsh/qalore-config.json` 重建 context |
| `{story_path}` | qalore 注入 | 自动恢复：读 `~/.dsh/qalore-config.json` 重建 context |
| `{确认项目名}` | qalore 注入 | 暂停，向用户重新确认 |
| `{执行环境 URL}` | qalore 注入 | 暂停，向用户确认 |

## 触发条件

用户描述含「执行/跑/运行 + 用例/测试/TC/模块」之一，且意图为执行已有测试用例。

## 前置依赖

- **Playwright MCP**：必须已配置（UI/Console/API/样式断言统一走 Playwright），由网关依赖体检检查
- **依赖登记**：读取 `{story_path}/{项目}/dependencies.json`（存在时），获取执行环境/测试账号/DB；不存在 → 依赖资源的断言降级为 SKIP
- **DB 断言**：`db_psql_available=true`（网关注入）才可执行；false → DB 断言全部 SKIP
- **TC 文件含断言规则**：无断言规则 → SKIP + 提示「请通过 qa-functional-test 更新 TC」
- **执行环境准备**：执行前显式声明浏览器上下文隔离策略——新建 isolatedContext 避免与其它会话窗口冲突；按 URL pattern 定位页面而非固定索引（contexts 索引会漂移）；目标应用在 iframe 内时通过 frame 定位。前置缺口（SKIP/FAIL 缺数据）时联动 qa-data-prep 造数

## 执行流程

```
1. 解析用户意图，确定执行范围：
   - 全部模块 → 遍历 story/{项目}/ 下所有叶子模块目录（递归展开 module_group 的 sub_modules）
   - 单模块 → 仅该模块
   - 单条 TC → 仅该 TC
   - 指定优先级 → 仅执行匹配优先级的 TC

2. 读取目标 TC 文件，提取所有含断言规则的用例

3. 按优先级排序执行（P0 → P1 → P2 → P3）

4. 装载测试资源（执行前）：
   - 从 dependencies.json 装载执行资源（环境/账号/DB/档位），边界与降级见 handbook.md「执行期资源装载」
   - 环境导航、账号鉴权、DB 连接、档位切换的具体动作依据执行上下文自主完成
   - 装载失败的资源相关断言 → SKIP + 原因（不现编资源/凭证）

4.5 解析元素定位 + 选择器存在性快照：
   - 断言选择器参数若为 `@句柄` → 查 `story/{项目}/locators.json` 解析为真实选择器；解析失败 → 该断言 SKIP + 「定位表缺句柄」原因
   - 对本次执行范围内全部选择器执行批量 `querySelector` 存在性探测，生成「选择器健康快照」
   - 同模块选择器失效率 ≥ 30%（阈值见 automation.md 漂移保护）→ 报「UI 结构变更」，不逐条 FAIL，进【待回写项】「依赖漂移」类型（定位表回写）

5. 逐条执行：
   a. 检查前置条件可满足性 → 不满足 → SKIP + 原因
   b. 处理前置写 mock：仅执行「已确认」的写 mock 声明（见 contracts.json#dependencies.permission_shift_left）；未确认/未声明的写操作 → 机器拦截，不新增判断，不向用户重复确认
   c. 按测试步骤顺序执行操作（导航/点击/输入）
   d. 执行断言规则：
      - UI/样式断言 → Playwright MCP browser_evaluate（getComputedStyle / getBoundingClientRect 批量）
      - API 断言 → Playwright MCP browser_network_requests / browser_network_request（被动观察）；page.request.*（主动直调）
      - DB 断言 → psql 只读 SELECT（db-field-value / db-row-count，见 execution.md）
   e. 记录结果：PASS（实测值）/ FAIL（实测值 vs 预期值）/ SKIP（原因）

6. 输出执行报告

7. 输出【待沉淀】声明
```

## 断言类型速查

**UI 断言（Playwright MCP）：**

| 类型 | 示例 |
|------|------|
| `element-exists` | `element-exists(.primary-btn)` |
| `element-not-exists` | `element-not-exists(.primary-btn)` |
| `element-count` | `element-count(.item-label, 5)` |
| `element-text` | `element-text(.panel-title, "标题文本")` |
| `element-width` | `element-width(.side-panel, 380)` |
| `element-enabled` | `element-enabled(.submit-btn)` |
| `element-disabled` | `element-disabled(.submit-btn)` |
| `message-contains` | `message-contains("提示文案")`（仅限 toast，字段标签用 `element-text`） |
| `url-contains` | `url-contains("/login")` |

**Console 断言（Playwright MCP）：**

| 类型 | 示例 |
|------|------|
| `console-error-contains` | `console-error-contains("Uncaught TypeError")` |

**视觉样式断言（Playwright MCP）：**

| 类型 | 示例 |
|------|------|
| `element-color` | `element-color(.panel-title, "rgb(24,144,255)")` |
| `element-background-color` | `element-background-color(.content-card, "#fff")` |
| `element-font-size` | `element-font-size(.panel-title, 16)` |
| `element-font-family` | `element-font-family(.panel-title, "PingFang SC")` |
| `element-font-weight` | `element-font-weight(.panel-title, "700")` |
| `element-padding` | `element-padding(.content-card, "top", 12)` |
| `element-margin` | `element-margin(.content-card, "top", 8)` |
| `element-size` | `element-size(.side-panel, 380, 640)` |
| `element-position` | `element-position(.primary-btn, 100, 50)` |
| `element-border-radius` | `element-border-radius(.content-card, 8)` |

**API 断言（Playwright MCP）：**

| 类型 | 示例 |
|------|------|
| `api-status` | `api-status(/api/{resource}/.*/list, 200)` |
| `api-field-exists` | `api-field-exists(/api/{resource}/.*/list, "total")` |
| `api-field-value` | `api-field-value(/api/{resource}/.*/list, "data.records[0].{字段}", 9)`（支持嵌套路径，顶层字段向后兼容） |
| `network-contains` | `network-contains(/api/{resource}/list)` |
| `api-request-field-value` | `api-request-field-value(/api/{resource}/.*/create, "type", "draft")` |
| `api-code` | `api-code(/api/{resource}/.*/create, 2000)` |

**DB 断言（psql 只读 SELECT，需 db_psql_available=true）：**

| 类型 | 示例 |
|------|------|
| `db-field-value` | `db-field-value({库名}, {表名}, {ID}, {字段}, "{值}")` |
| `db-row-count` | `db-row-count({库名}, {表名}, "{字段} < now()", 3)` |

完整定义和验证代码见 `{practices_path}/tech-stacks/functional/execution.md`。

## 执行报告格式

每次执行**覆盖写入** `{story_path}/{项目}/{容器链}/{模块}/{模块}-功能-执行报告.md`（**文件模式，默认**）。用户明确要求「不产生文件，对话里评审」时切换**对话模式**：结果仅在对话中呈现，不落盘任何文件。

```markdown
# {模块名} 执行报告
> 执行时间: {ISO 8601} | 工具: Playwright MCP | 环境: {id} {URL} | 账号: {角色} | 档位: {id}

| TC ID | 标题 | 结果 | 实测 |
|-------|------|------|------|
| TC-{PREFIX}-001 | 侧栏宽度 | PASS | 380px |
| TC-{PREFIX}-002 | 分组展示 | PASS | 分组A(8)/分组B(1) |
| TC-{PREFIX}-003 | 新建按钮 | PASS | 组件A显示/组件B隐藏 |
| TC-{PREFIX}-004 | 空输入校验 | PASS | "提示文案" |

汇总: 总 {n} | PASS {x} | FAIL {y} | SKIP {z} | 通过率 {x/(x+y) * 100}%（SKIP 不参与分母）
```

## 【待回写项】声明

执行中发现「断言与实测不符」「端点漂移」「预期需修正」等情况时，执行报告末尾**必须**追加【待回写项】清单，作为回写 story 的可追踪来源：

```markdown
## 【待回写项】

| 文件 | 断言/用例 ID | 问题 | 建议回写操作 |
|------|-------------|------|-------------|
| {模块}-功能-业务逻辑.md | assert-{PREFIX}-{seq} | 端点漂移：/api/{resource}/move 实测为 /api/{resource}/batch-move | 3.2 更新端点 |
| {模块}-功能-测试用例.md | TC-{PREFIX}-{seq} | 预期与实测不符：实际返回 code {码A} 而非 {码B} | 3.2 更新断言 |
```

【待回写项】与【待沉淀】分离：【待沉淀】是本次执行产物的写入声明，【待回写项】是"本次执行暴露了 story 中哪些内容已过时、需后续任务回写"的追踪清单。二者都写入执行报告，但【待回写项】是**发现清单**，不直接修改 story 文件。

### 待回写项四标准

**准入标准（什么能进）：**

| 类型 | 判据 | 证据要求 |
|------|------|---------|
| 断言漂移 | 已有断言实测 FAIL（实测值 ≠ 预期值） | 附实测值（API 响应 / trace / DB / 截图） |
| 覆盖缺口 | 实测发现 story 无对应功能点/断言 | 附新场景实测证据（端点/字段/行为） |
| 依赖漂移 | 实测发现 dependencies.json 登记资源漂移（环境 URL 变/账号权限变/DB 结构变/档位增减/造数入口漂移） | 附实测漂移证据（新 URL/新边界/新结构） |

不满足判据（无实测证据的「疑似」）不得准入，降级为观察记录，不写入【待回写项】。

**沉淀标准（怎么回流成 story）：**

| 类型 | 回写操作 | 执行者 |
|------|---------|--------|
| 断言漂移 | 3.2 更新 / 3.3 删除 | 执行者直接回写（走 handbook「断言变更规则」） |
| 覆盖缺口 | 3.1 新增 | 路由 qa-understand「实测反哺」子流程（理解→断言→用例→收敛，实测为准，需求未覆盖以开发实现为准） |
| 依赖漂移 | 回写 dependencies.json 对应字段（environments/accounts/databases/device_profiles/data_fixtures.factory） | 执行者直接回写（走 handbook「依赖登记规范」） |

**可信度标准（怎么保证真实）：**
- 每条绑定实测证据（具体端点/字段/值），不允许「推测」
- 覆盖缺口新增的断言置信度标注「实测确认」
- 无实测证据 → 不沉淀

**入库标准（怎么符合 qalore 入库）：**
- 断言格式：`[assert-{PREFIX}-{seq}] 【维度】对象·条件→预期 | upd:版本`
- 计数一致性：assert_seq = max+1，tc_count = grep 实际（见 handbook「计数一致性规范」）
- changelog 同步：3.1/3.2/3.3 均写 changelog
- 置信度标注必填

## 【待沉淀】声明

执行完成后输出：

```
【待沉淀】
| 文件 | 路径 | 操作 | 变更摘要 |
|------|------|------|---------|
| {模块}-功能-执行报告.md | {路径}/ | 覆盖写入 | {n} 条执行，PASS {x} / FAIL {y} / SKIP {z} |
```

## 自动化执行模式（无人值守）

宿主环境触发「自动化入口」（接收 `{执行范围}`：模块/优先级）时，按 `tech-stacks/functional/automation.md` 五条不变式执行：

- **幂等**：每次执行独立，跑前环境干净或只读 → 重复执行不累积脏状态
- **范围声明**：校验入口 `{执行范围}` 非空；执行只覆盖声明范围内用例，范围外用例不执行
- **只读安全**：只跑 `read-verify` 无副作用用例；含写 mock 的用例自动 SKIP（不执行有副作用用例）
- **漂移保护**：结构漂移（选择器失效）由「选择器存在性快照」前置捕获（见执行流程 4.5）；断言值漂移才按「同一 TC 连续 FAIL ≥ 3 次 → 标记疑似断言漂移 → 进【待回写项】清单」判定
- **失败可见**：报告落盘 `{story_path}/{项目}/{容器链}/{模块}/{模块}-功能-执行报告.md`，可被宿主/用户拉取
- 低置信度断言（校准模式）只做「校准采集」，不判 FAIL

触发源（DSH schedule / cron / CI / Hook）由宿主环境提供，本 capability 不规定触发器。

## 验证模式 vs 校准模式

执行时分两模式（分流依据：qa-understand/qa-functional-test 的置信度标注，标注是断言产出契约的必填项）：

- **验证模式**（高置信度断言 `✓` 等，或无标注时默认）：正常 pass/fail，任一断言 FAIL → TC FAIL
- **校准模式**（低置信度断言 `待代码确认`/`⚠️`/新 feature 推理断言）：首次执行不判 FAIL，产出「校准差异报告」（格式见 story-formats.md），按四分类归因（推理失真/实现漂移/文档不完整/产品口径变更）分流处置
