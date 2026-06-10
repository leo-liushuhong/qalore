# qalore

> 面向 AI 的结构化测试知识管理系统

qalore 是一套运行于 AI 助手之上的测试能力框架，解决 AI 跨会话无持久记忆的根本问题，让测试知识可以在模块之间、会话之间、模型之间持续积累。

思考框架不绑定特定工具或平台，任何 AI 模型或智能体均可按其执行；当前实现以 Claude Code skill 形式提供。

---

## 为什么需要 qalore

| 问题 | 原生 AI | qalore |
|------|---------|-----------|
| 跨会话知识 | 每次重新分析，重复劳动 | story 系统持久化，下次从断点继续 |
| 覆盖完整性 | 依赖提示词质量，随机性高 | 7问/五镜头结构保底，不遗漏维度 |
| 测试方向 | 验证性（系统是否工作）| 对抗性（用户在哪里会受伤）|
| PRD→TC 可追溯 | 无，黑盒输出 | 断言链路显式记录 |
| 多模块覆盖管理 | 无，无法全局视图 | index.json 统一管理进度和状态 |
| 团队协作 | 每人各做一套 | story 是共享知识库 |

---

## 核心思考哲学

### 三驱动认知框架

**假设优先** — 读之前先用一句话假设模块「做什么、谁触发、影响什么」，读是验证假设。

**模型驱动** — 每读一段，问：这证实还是推翻了假设的哪个部分？

**证据驱动** — 每条论断必须有来源（PRD 文字 / 代码实现）。

**边界驱动** — 每个系统交互都有两端，遇到边界判断另一端是否已知。

### 用户影响优先（测试设计原则）

> **如果这个模块今天在生产中出问题，用户最先感受到什么损失？**

以此定义优先测试场景，再用断言集合补全覆盖。

---

## 架构

```
qalore/
├── SKILL.md                          # 网关：任务路由、环境验证、能力调度
├── practices-bootstrap.md            # story/index.json 完整字段 Schema
├── qalore.config.template.json       # 配置文件模板
└── capability/
    ├── qa-understand/                # 测试意图理解与提炼
    │   ├── SKILL.md                  # 三驱动 + 渐进式阅读策略 + 适配器调度
    │   └── adapters/
    │       ├── text.md               # 文本源：7问追问
    │       ├── code.md               # 代码源：五镜头（支持多仓库）
    │       └── synthesis.md          # 多源证据聚合与置信度判断
    ├── qa-functional-test/           # 功能测试用例设计与产物输出
    │   └── SKILL.md
    ├── qa-case-review/               # 用例质量评审
    │   └── SKILL.md
    └── qa-token-report/              # Token 使用统计（Stop Hook 自动触发）
        ├── SKILL.md
        └── read_usage.py
```

配套的两个独立目录（不包含在 skill 包内）：

```
practices/                            # 测试规范库（一次建设，跨项目复用）
├── index.json                        # 版本管理入口
├── common/
│   ├── handbook.md                   # 通用规范（story维护、写入协议、评审规范）
│   └── handbook-practices-ops.md     # practices 操作规范
└── tech-stacks/functional/
    ├── assertions.md                 # 可测试断言规范
    ├── cases.md                      # 功能测试用例规范
    ├── changelog.md                  # 变更记录规范
    ├── output.md                     # 产物输出规范
    └── story-formats.md              # Story 文件格式规范

story/                                # 项目测试知识库（按项目维护）
└── {项目名}/
    ├── index.json                    # 项目全局视图
    └── {模块名}/
        ├── {模块名}-功能-业务逻辑.md
        ├── {模块名}-功能-代码逻辑.md
        └── {模块名}-功能-测试用例.md
        （及对应 .changelog.md 文件）
```

---

## 快速上手

### 第一步：安装

将 `qalore/` 目录复制到 `~/.claude/skills/qalore/`。

### 第二步：配置

创建 `~/.claude/qalore-config.json`：

```json
{
  "practices_path": "/absolute/path/to/practices",
  "story_path": "/absolute/path/to/story"
}
```

Stop Hook（可选，用于 Token 统计）配置在 `~/.claude/settings.json`：

```json
{
  "hooks": {
    "Stop": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "cmd /c \"python \"path/to/read_usage.py\" 2>nul || ver >nul\""
      }]
    }]
  }
}
```

### 第三步：使用

```bash
# 理解需求，提炼测试断言
"帮我分析用户登录模块的需求文档，沉淀到 story"

# 阅读代码，提炼测试断言
"帮我阅读 src/auth/ 目录下的代码，更新登录模块的 story"

# 同时读需求和代码（多源模式，自动聚合置信度）
"读登录模块的 PRD 和代码，更新 story"

# 生成测试用例
"给登录模块出测试用例"

# 评审测试用例
"评审登录模块的测试用例"

# 生成脑图产物
"给登录模块出全量测试用例并输出脑图"
```

---

## 能力详解

### qa-understand：测试意图理解与提炼

**输入**：需求文档（PRD）/ 代码文件 / 两者混合

**思考哲学**：
- **文本源** — 7问追问：正常结果、状态、触发者、输入约束、交互反馈、副作用、失败场景
- **代码源** — 五镜头：入口与路径、数据约束、状态与转换、副作用链、错误路径
- **综合层** — 多源证据聚合：独立提炼后对比，7 种置信度标注

**输出**：
- `业务逻辑.md`：从需求视角提炼的可测试断言
- `代码逻辑.md`：从代码视角提炼的可测试断言
- 统一交接块 `【测试意图已提炼】`

**断言格式**：
```
[assert-AUTH-001] 【权限】（✓）登录接口 · 正确用户名密码 → 返回 JWT token | upd:v1.0
[assert-AUTH-003] 【异常】（待代码确认）登录 · 账号被锁定时 → 返回具体错误码 | upd:v1.0
[assert-AUTH-004] 【上下游】（✓）登录成功 · token 写入后
  → [用户中心::会话管理] 创建活跃会话记录 | upd:v1.0
```

置信度标注：`（✓）` / `（✓,部分代码确认）` / `（待代码确认）` / `（代码独立）` / `（代码独立,多源）` / `⚠️` / `⚠️(代码)`

---

### qa-functional-test：功能测试用例设计与产物输出

**思考哲学**：用户影响优先 — 先问用户最先感受什么损失，再系统性补全覆盖。

**输入来源**（按优先级）：
1. context 中的 `【测试意图已提炼】` 交接块
2. story 中的业务逻辑.md + 代码逻辑.md
3. 两者均无 → 提示用户先触发 qa-understand

**用例格式**：
```
用例 ID：TC-AUTH-001
标题：正确账号密码登录返回有效 token
功能点：用户登录 > 账号密码登录
前置条件：存在状态正常的用户账号
测试步骤：
  1. 输入正确凭据，点击登录
     → 预期：返回 HTTP 200，响应体含有效 JWT token
优先级：P0  |  测试维度：正向
```

**可选产物**：FreeMind `.mm` 格式脑图，可直接导入 XMind / FreeMind / MindManager。

---

### qa-case-review：用例质量评审

**思考哲学**：溯源式质量判断 — 这批用例拿去执行，会漏掉什么、卡在哪里？

三层检查：
- **结构层**：字段完整性、步骤可执行性、预期完整性
- **覆盖层**：每个功能点是否覆盖正向/边界/异常/上下游四维度
- **归因层**：发现问题时追溯根源（用例设计遗漏 / 断言理解遗漏）

输出评审报告，含阻断（必须修复）/ 需改进 / 建议三级。

---

### qa-token-report：Token 使用统计

由 Claude Code Stop Hook 自动触发。从 transcript JSONL 累加本轮 API call 的 token 数据，以固定格式打印到对话。非 qalore 会话静默退出。

---

## Story 设计原则

### 三层加载

| 层 | 内容 | 加载策略 |
|------|------|---------|
| Layer 1 | index.json | 每次任务必读，极小，全局概览 |
| Layer 2 | 内容文件 (.md) | 按需读，只读当前需要的模块 |
| Layer 3 | changelog 文件 | 正常任务不读，只在溯源时读 |

### 只维护当前态，变更追踪入 changelog

内容文件按功能点/组件分节，变更时原地更新（3.1新增 / 3.2更新 / 3.3删除）。变更原因写入对应的 `.changelog.md`。

### 跨模块关联结构化标签

```
[assert-ORDER-012] 【上下游】订单创建 · 支付成功后
  → [库存::扣减] 触发库存扣减事务 | upd:v2.0
```

index.json 的 `depends_on` 和 `business_related` 从上下游断言自动聚合，不独立维护。

---

## Story 三层架构

```
Layer 1  index.json          每次任务必读，极小，给 AI 概览全局
Layer 2  内容文件 (.md)       按需读，只读当前需要的模块
Layer 3  changelog 文件       正常任务绝不读，只在溯源时读
```

越频繁访问的层，信息密度越高、体积越小。

---

## 配置参考

### story/index.json 模块字段

```json
{
  "project": "项目名",
  "description": "面向谁、核心功能",
  "created": "YYYY-MM-DD",
  "modules": {
    "{模块名}": {
      "description": "模块描述",
      "tc_prefix": "AUTH",
      "assert_seq": 12,
      "prd_version": "v1.2",
      "depends_on": { "订单模块": ["orderService"] },
      "business_related": { "库存模块": ["扣减"] },
      "code_paths": [{ "path": "src/", "entry": "submit()", "depth": 3, "last_read": "2026-01-01" }],
      "status": {
        "business_logic": true,
        "code_logic": false,
        "tc_count": 15,
        "pending_count": 2
      },
      "last_updated": "2026-01-01"
    }
  }
}
```

---

## License

MIT License

---

> **一句话定位**：qalore 不是替代 AI 的测试能力，而是让 AI 的测试工作可积累、可追溯、可跨会话延续的知识基础设施——原生 AI 提供智力，qalore 提供记忆和结构。
