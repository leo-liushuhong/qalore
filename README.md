# qalore — 全栈测试工程师网关

> AI 是主体，框架是支撑。qalore 装备 AI 为全栈测试工程师，不把 AI 变成流水线。

## 概述

qalore 是一个 Claude Code skill，作为测试任务网关，接收测试任务后完成三件事：

1. **环境验证** — 验证路径有效性、capability 可用性、版本兼容性
2. **意图识别** — 对照路由表推断触发哪些 capability，确定执行顺序
3. **上下文注入** — 向被触发的 capability 注入 practices_path、story_path 等变量

**不负责：** 各 capability 内部的执行流程、产物格式、story 写入协议——这些由 capability 和 practices 自主管理。

## 架构

```
qalore (网关)
  ├── qa-understand       测试意图理解与提炼
  │   ├── adapters/text.md       文本适配器（PRD/需求/口述）
  │   ├── adapters/code.md       代码适配器（单仓库/多仓库）
  │   └── adapters/synthesis.md  多源证据聚合综合层
  ├── qa-functional-test  功能测试用例设计与产物输出
  ├── qa-case-review      用例评审
  ├── qa-execution        测试用例执行
  │   └── cdp_network/           CDP Network MCP Server
  └── qa-token-report     Token 使用统计（基础设施，Stop Hook 触发）
```

## 安装与配置

### 前置条件

- Claude Code 已安装
- Python 3.x（qa-execution 需要 `websocket-client` 和 `requests` 包）
- Playwright MCP（qa-execution 需要）

### 配置

创建 `~/.claude/qalore-config.json`：

```json
{
  "practices_path": "D:\\Test\\qalore\\practices",
  "story_path": "D:\\Test\\qalore\\story"
}
```

首次使用时若配置文件不存在，网关会自动引导完成配置。

### practices 初始化

参考 skill 包内 `practices-bootstrap.md` 完成 practices 目录初始化。

### Stop Hook（可选）

在 `~/.claude/settings.json` 中配置 Token 统计：

```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "python \"%USERPROFILE%/.claude/skills/qalore/capability/qa-token-report/read_usage.py\""
      }]
    }]
  }
}
```

## 能力矩阵

### 用户能力（由网关按路由表触发）

| Capability | 触发意图 | 核心思考哲学 | 状态 |
|-----------|---------|------------|------|
| **qa-understand** | 提供信息输入（PRD/代码/口述），或含理解/提炼/分析意图 | 三驱动认知框架（假设优先 → 模型驱动 → 证据驱动 → 边界驱动） | ✅ 可用 |
| **qa-functional-test** | 需要测试用例，含「生成/出用例」意图 | 用户影响优先的用例集 | ✅ 可用 |
| **qa-case-review** | 含「评审/review/检查用例」意图 | 溯源式质量判断（结构层 → 覆盖层 → 归因层） | ✅ 可用 |
| **qa-execution** | 含「执行/跑/运行 + 用例/测试」意图 | 断言驱动执行（UI + API 双通道） | ✅ 可用 |

### 基础设施

| Capability | 触发方式 | 状态 |
|-----------|---------|------|
| **qa-token-report** | Stop Hook 自动执行 | ✅ 可用 |

### 未建设（Phase 2）

- 性能/压力测试
- 安全测试
- 混沌测试

## 路由表

| 触发意图 | Capability | 前置条件 |
|---------|-----------|---------|
| 用户提供信息输入（PRD/需求文档/代码/混合），或描述含理解/提炼/阅读/沉淀/分析/记录 | `qa-understand` | — |
| 用户需要测试用例，描述含「生成/出用例/全量/测试文件」 | `qa-functional-test` | 同会话有 qa-understand 时须等其完成 |
| 用户描述含「评审/review/检查用例/审查用例」 | `qa-case-review` | 联动模式须等 qa-understand 完成 |
| 用户描述含「执行/跑/运行+用例/测试/TC/模块」 | `qa-execution` | Playwright MCP 已配置 |

**多 capability 执行顺序：** 同会话触发 qa-understand + qa-functional-test（或 qa-case-review）→ 先执行 qa-understand，待交接块产出后再执行下游。不得并发启动有依赖关系的 capability。

## qa-understand：测试意图理解与提炼

将任意信息源转化为可测试的理解，写入 story，供下游 capability 使用。

### 三驱动认知框架

- **假设优先** — 读任何信息源前，先用一句话假设模块"做什么、谁触发、影响什么"
- **模型驱动** — 每读一段，问：这证实还是推翻了假设？
- **证据驱动** — 每条论断必须有来源，无来源 = 待验证假设
- **边界驱动** — 每个系统交互检查两端是否已知；未知 → 主动寻找或标注待确认

### 渐进式阅读策略

1. **导航阶段** — 扫描结构建地图（低成本）
2. **切片精读** — 按语义单元对假设中的开放问题做深度阅读（按需）

### 适配器体系

| 适配器 | 信息源 | 认知方法 | 写入目标 |
|--------|--------|---------|---------|
| **text.md** | PRD/需求/口述 | 7问追问（正常结果/状态/触发者/输入/反馈/改变/失败）+ 波及与覆盖分析 | 业务逻辑.md |
| **code.md** | 代码文件/目录 | 五镜头追问（入口路径/数据约束/状态转换/副作用链/错误路径） | 代码逻辑.md |
| **synthesis.md** | 多源聚合 | 识别同一场景 → 按证据一致性分类 → 7种置信度标注 | 统一交接块 |

### 7种置信度标注

| 标注 | 触发条件 | 是否产出断言 |
|------|---------|------------|
| `（✓）` | 文本 + 所有代码源确认 | 产出 |
| `（✓,部分代码确认）` | 文本 + 部分代码源确认 | 产出 |
| `（待代码确认）` | 仅文本，无代码实现 | 产出 |
| `（代码独立）` | 仅单一代码源 | 产出 |
| `（代码独立,多源）` | 多个代码源均有，无文本 | 产出 |
| `⚠️` | 文本与代码结论矛盾 | **不产出，待确认** |
| `⚠️(代码)` | 多代码源描述同一场景但结论矛盾 | **不产出，待确认** |

### 信息范围层级（文本适配器）

| 层级 | 范围 | 适用场景 |
|------|------|---------|
| 1 | 目标模块 + 1-hop 上下游 + 待确认项 | text-only 起始（安全基线） |
| 2 | + 测试用例 | text-only 上限 |
| 3 | + 代码 | text+code 上限 |
| 4 | + 跨项目 | 用户指定 |

## qa-functional-test：功能测试用例设计与产物输出

以断言集合为输入，设计覆盖正向/边界/异常/上下游的测试用例，产出 story 和 .mm 脑图。

### 核心思考哲学：用户影响优先

> 如果这个模块今天在生产中出问题，用户最先感受到什么损失？

以这个答案定义 2-3 个优先测试场景，然后用断言集合补全覆盖。

### 测试维度

- **正向** — 功能按预期工作
- **边界** — 输入/状态的极限值
- **异常** — 错误输入和系统故障
- **上下游** — 跨模块联动

### 输入来源优先级

1. Context 中的 `【测试意图已提炼】` 交接块（联动模式）
2. Story 中的业务逻辑.md + 代码逻辑.md
3. Story 中仅有其中一个文件
4. 两者均无 → 告知用户先触发 qa-understand

### 存量用例处置

| 情况 | 操作 |
|------|------|
| TC 文件不存在 | 全新设计，TC 序号从 001 开始 |
| TC 文件已存在 + 有新输入 | 增量处理（3.1新增/3.2更新/3.3删除） |
| TC 文件已存在 + 无新输入 + 仅查看 | 直接输出模式（跳过设计，读 story 直接产出 .mm） |

### 执行后验证（5 项必检）

1. **计数验证** — tc_count、pending_count、assert_seq 与文件实际内容一致
2. **覆盖验证** — TC 功能点覆盖所有 BL 功能点
3. **格式验证** — 每条 TC 含 7 个必填字段，TC ID 无重复、无跳号
4. **语言验证** — 禁止工程语言泄漏（API 调用/组件名/CSS 类名/内部变量）
5. **断言覆盖验证** — 每条 TC 的 `→ 预期：` 对应 `→ 断言：`

### 产物

- **Story 文件：** 测试用例.md + 测试用例.changelog.md
- **脑图文件：** .mm 格式（飞书/FreeMind 兼容）

## qa-case-review：用例评审

对测试用例执行多层质量检查，输出问题报告。

### 核心思考哲学：溯源式

> 这批用例拿去执行，会漏掉什么、卡在哪里？

### 三层评审

- **结构层** — 用例本身是否可执行？字段是否完整？每个 `→ 预期：` 是否有 `→ 断言：`？
- **覆盖层** — 每个功能点是否覆盖了正向/边界/异常/上下游四个维度？
- **归因层** — 发现问题时追溯根源：用例写法问题 → 执行层；断言遗漏 → 理解层

### 评审模式

| 模式 | 输入 | 基准 |
|------|------|------|
| 联动模式 | 同会话交接块 | 三层完整比对 |
| Story 模式 | Story 中的文件 | 有什么用什么 |
| 临时模式 | 粘贴 TC 内容 | 仅结构层 + 覆盖层 |

### 结论判定

| 条件 | 结论 |
|------|------|
| 阻断 = 0 | 通过 |
| 阻断 > 0，需改进 ≤ 3 | 需修复后通过 |
| 阻断 > 0，需改进 > 3 | 不通过 |

## qa-execution：测试用例执行

读取 TC 文件中的断言规则，通过 Playwright MCP + CDP Network MCP 在浏览器中逐条执行，产出执行报告。

### 执行流程

1. 解析执行范围（全部模块 / 单模块 / 单条 TC / 指定优先级）
2. 读取目标 TC 文件，提取含断言规则的用例
3. 按优先级排序（P0 → P1 → P2 → P3）
4. 逐条执行：检查前置条件 → 执行步骤 → 执行断言 → 记录结果
5. 输出执行报告

### 断言类型（10 种）

**UI 断言（Playwright MCP，7 种）：**

| 类型 | 示例 |
|------|------|
| `element-exists` | `element-exists(.new-chat-btn)` |
| `element-not-exists` | `element-not-exists(.new-chat-btn)` |
| `element-count` | `element-count(.group-label, 5)` |
| `element-text` | `element-text(.sidebar-title, "历史记录")` |
| `element-width` | `element-width(.chat-sidebar, 380)` |
| `message-contains` | `message-contains("请输入请求消息！")` |
| `url-contains` | `url-contains("/login")` |

**API 断言（CDP Network MCP，3 种）：**

| 类型 | 示例 |
|------|------|
| `api-status` | `api-status(/api/agent/.*/sessions, 200)` |
| `api-field-exists` | `api-field-exists(/api/agent/.*/sessions, "total")` |
| `api-field-value` | `api-field-value(/api/agent/.*/sessions, "total", 9)` |

### 前置依赖

- **Playwright MCP** — 必须已配置
- **CDP Network MCP** — 内嵌于 `cdp_network/server.py`（需 `pip install websocket-client requests`）
- **TC 文件含断言规则** — 无断言规则 → SKIP

### 执行报告

每次执行覆盖写入 `{模块}-功能-执行报告.md`，格式：

```markdown
# {模块名} 执行报告
> 执行时间: {ISO 8601} | 工具: Playwright MCP + CDP Network MCP | 环境: {URL}

| TC ID | 标题 | 结果 | 实测 |
|-------|------|------|------|

汇总: 总 {n} | PASS {x} | FAIL {y} | SKIP {z} | 通过率 {x/n * 100}%
```

## qa-token-report：Token 使用统计

由 Claude Code Stop Hook 自动触发。从 transcript JSONL 累加本轮所有 API call 的 usage 数据并打印到对话。

**触发条件：** last_assistant_message 含 qalore 信号词（`TC-`、`.mm`、`用例总计`、`【功能测试执行计划】` 等）→ 统计并输出；否则静默退出。

**输出示例：**

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

## Practices 体系

Practices 是"公司规范"——划定边界，防止失控，但不干涉 AI 的智力发挥。

### 三层架构

```
practices/
  index.json              ← 版本管理入口（每次任务必读）
  common/
    handbook.md           ← 通用规范（每次任务必加载）
    handbook-practices-ops.md  ← practices 操作规范（按需加载）
    handbook-audit.md     ← 审计规范（人工执行时加载）
  tech-stacks/
    functional/
      assertions.md       ← 可测试断言规范
      cases.md            ← 功能测试用例规范
      changelog.md        ← 变更记录规范
      output.md           ← 产物输出规范（.mm 脑图）
      story-formats.md    ← Story 文件格式规范
      execution.md        ← 断言类型定义（10 种）和执行规则
      cloud-sync.md       ← 云效同步通道规范
  schemas/
    story-index.schema.md ← Story index.json 权威 Schema
```

### 核心原则

- **增量原则** — 所有 story 文件只增不删（执行报告除外）
- **自解释原则** — 每个文件必须能被全新 AI 实例独立读懂
- **断点恢复** — 每模块完成即写入，会话中断后可继续
- **渐进式披露** — context 标记按需加载，避免全量读取

## Story 体系

Story 是"项目上下文"——解决 AI 没有持久记忆但项目知识需要持久存在的矛盾。

```
story/{项目名}/
  index.json                        ← 项目全局索引
  {模块名}/
    {模块名}-功能-业务逻辑.md         ← 按功能点分节
    {模块名}-功能-业务逻辑.changelog.md
    {模块名}-功能-代码逻辑.md         ← 按组件分节
    {模块名}-功能-代码逻辑.changelog.md
    {模块名}-功能-测试用例.md         ← 测试用例
    {模块名}-功能-测试用例.changelog.md
    {模块名}-功能-执行报告.md         ← 执行结果快照
```

### index.json 结构

```json
{
  "project": "项目名",
  "description": "一句话描述",
  "created": "YYYY-MM-DD",
  "last_updated": "YYYY-MM-DD",
  "modules": {
    "{模块名}": {
      "description": "模块描述",
      "tc_prefix": "TC ID 前缀（注册后不可变）",
      "mm_short_id": "脑图短 ID",
      "assert_seq": 0,
      "depends_on": {},
      "business_related": [],
      "code_paths": [],
      "status": {
        "business_logic": false,
        "code_logic": false,
        "tc_count": 0,
        "pending_count": 0
      }
    }
  }
}
```

## 设计哲学

### qalore 本体五条

1. **AI 是主体，框架是支撑** — 框架只给工具、设边界、提供上下文，不规定每一个动作
2. **Capability = 思考哲学，不是执行步骤** — 装备 AI 某个专业领域的思考方式
3. **Practices = 公司规范，不是操作手册** — 划定边界防止失控，不干涉智力发挥
4. **Story = 项目上下文，不是任务数据** — 以 AI 快速理解为第一优先
5. **渐进式披露** — 按上下文流转切割，index.json → 内容文件 → changelog 三层按需加载

### 两道确认门槛

1. **执行前确认** — 展示计划，用户确认"做什么"
2. **写入前确认** — 展示 `【待沉淀】`，用户确认"写什么"

### 上下游断言是唯一真相

跨模块引用写在上下游断言里，`depends_on` 和 `business_related` 从断言聚合重建（完整替换，防止幽灵数据）。

```markdown
[assert-IMG-006] 【上下游】图片上传 · 上传成功
  → [内容审核::文件接收] 触发文件接收队列 | upd:v2.0
```

## 约束规则

### 三条不可违反

1. **路径约束** — practices_path / story_path 必须从 `~/.claude/qalore-config.json` 读取
2. **能力约束** — 未在可用列表中的 capability 不得执行
3. **项目约束** — 项目名必须由用户明确，不得自行假设

### 安全规范

- **批量操作安全** — 多条件精确过滤 + Dry-Run 前置 + 禁止全量删除重建
- **文件操作安全** — JSON 禁止行级 Edit；内容文件必须先 Read 再 Write
- **临时文件清理** — 任务完成后必须清理所有临时脚本和中间文件
- **通用性约束** — 禁止在 capability 和 practices 文件中嵌入项目定制内容

## 版本历史

当前 practices 版本：**2026-07-23-v6**

### 近期主要更新

| 版本 | 日期 | 摘要 |
|------|------|------|
| v6 | 2026-07-23 | 执行报告写入模式澄清（快照产物例外） |
| v5 | 2026-07-23 | 拓扑审计修复：context 标记引用修正 + cloud-sync 内部一致性 |
| v4 | 2026-07-23 | code-repo-count 标记 + 冗余分隔符清理 |
| v3 | 2026-07-23 | 审计修复：章节注册表补全 |
| v2 | 2026-07-23 | 新增「临时文件清理规范」 |
| v1 | 2026-07-23 | subagent 分层体系建设 + audit 升级（17步+20条哲学） |

### 历史演进概览

- **2026-04-10** — 初始版本，规范文件待建设
- **2026-05-15** — 重大架构升级：内容文件按功能点/组件分节、7种置信度标注、跨模块结构化标签
- **2026-06-12** — 基础设施重构：capability 分层、context 标记注册表、practices 版本兼容性检查
- **2026-06-15** — ChatBI 全量审计：TC 语言规范、计数一致性、文件操作规范
- **2026-06-24** — qa-execution 上线：10 种断言类型、CDP Network MCP
- **2026-07-14** — 云效通道建设：cloud-sync.md、批量操作安全规范
- **2026-07-23** — 多轮审计收敛：依赖图补全、合约对齐、临时文件清理

## 项目链接

- **qalore-audit** — 系统一致性审查方法（依赖图驱动 + 六类问题分类）
- **QALore** — 零侵入 Agent 黑盒评测平台（被测项目示例）

## 许可

qalore 是 Claude Code skill，随 Claude Code 环境使用。
