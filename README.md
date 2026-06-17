# qalore — 测试任务网关

> 接收测试任务 → 环境验证 → 意图识别 → 上下文注入 → 交给 capability 执行
>
> 已建设：测试意图理解、功能测试、用例评审。未建设（Phase 2）：自动化、性能、安全、混沌。

---

## 快速索引

- [网关职责](#网关职责)
- [三条不可违反的约束](#三条不可违反的约束)
- [环境验证流程](#环境验证流程)
- [意图识别与路由](#意图识别与路由)
- [上下文注入协议](#上下文注入协议)
- [可用 Capability 列表](#可用-capability-列表)
- [practices 加载规范](#practices-加载)
- [快速上手（安装与配置）](#快速上手)
- [文件包结构](#文件包结构)

---

## 网关职责

接收测试任务后，完成三件事：

1. **环境验证** — 路径是否有效、practices 版本是否一致、capability 版本是否兼容
2. **意图识别** — 对照路由表推断触发哪些 capability，确定执行顺序
3. **上下文注入** — 向所有被触发的 capability 注入 practices_path、story_path、项目名、practices_version

**不负责：** capability 内部执行流程、产物格式、story 写入协议——这些由各 capability 和 practices 自主管理。

---

## 三条不可违反的约束

1. **路径约束**：practices_path / story_path 必须从 `~/.claude/qalore-config.json` 读取，不得硬编码、推断或猜测
2. **能力约束**：未在可用列表中的 capability 不得执行，不得用通用测试知识替代
3. **项目约束**：项目名必须由用户明确（对话中明确提及，或从文档中唯一识别），不得自行假设

---

## 环境验证流程

### 1. 读取配置

读 `~/.claude/qalore-config.json`：
- **不存在**（首次安装）→ 读 skill 包内 `qalore.config.template.json` 获取格式参考，引导用户提供 practices_path / story_path → 生成 config → 继续
- **存在** → 读取 practices_path / story_path

### 2. 路径验证

- `{practices_path}/index.json` 不存在 → 停止：「practices 未初始化，请参考 skill 包内 practices-bootstrap.md 完成初始化」
- `{story_path}/` 不存在 → 停止：「story 目录不存在，请创建后重试」
- 全部通过 → 将两个路径写入 context

### 3. practices 版本一致性验证

读 `{practices_path}/index.json`，校验 `version == changelog[0].version`：
- 不一致 → 停止，输出版本不一致提示（建议以 changelog[0].version 为准）
- 一致 → 继续

### 4. capability 版本兼容性验证

对所有已注册 capability（含基础设施），逐一读其 SKILL.md frontmatter 的 `practices_min_version` 字段：
- `practices_min_version` > 当前 practices version → 停止，告知升级 practices
- `practices_min_version` ≤ 当前 → 继续
- 未声明 → 不阻断，输出警告

> 基础设施 capability（qa-token-report，由 Hook 触发）同样参与此检查，不因触发方式不同而跳过。

---

## 意图识别与路由

### 项目名识别

- 无法确定 → 暂停确认：「请问这个任务属于哪个项目？当前 story 中已有：{story_path/ 下目录列表}」
- **推断条件（同时满足才可推断）：**
  1. 用户明确提及了某个词
  2. 该词与 story_path/ 下某目录名**字符串完全相等**（大小写一致）
- 模糊匹配、首字母缩写、语义相近 → 均不得推断，必须暂停确认。多项匹配必须暂停确认

### 模块粒度定义

一个模块 = 用户可独立触发、独立感知结果的最小业务功能单元：
- 正面：用户能单独描述「我想测 X 的 Y 功能」→ Y 是模块
- 反面：「整个项目」「所有功能」不是模块；单个 API 端点通常也不是
- 有疑问时暂停向用户确认

### 新项目处理

`{story_path}/{确认项目名}/` 不存在 → 询问用户提供一句话描述（面向谁、核心功能）→ 创建 `index.json` 初始结构（含 project/description/created/modules:{}）

### 路由表

| 触发意图 | Capability | 前置条件 |
|---------|-----------|---------|
| 用户提供信息输入（PRD/需求文档/代码/混合），或描述含理解/提炼/阅读/沉淀/分析/记录 | `qa-understand` | — |
| 用户需要测试用例，描述含「生成/出用例/全量/测试文件」，或无需求文档但指定模块，或含「更新story/写入story/沉淀到story」 | `qa-functional-test` | 同会话触发了 qa-understand 时，须等其完成 |
| 用户描述含「评审/review/检查用例/审查用例」，或粘贴了 TC 内容要评审，或含「生成并评审」 | `qa-case-review` | 联动模式下须等 qa-understand 完成 |

### 多 capability 执行顺序

- 同会话同时触发 qa-understand + qa-functional-test → 先执行 qa-understand，等 `【测试意图已提炼】` 交接块产出后再执行 qa-functional-test
- 同会话同时触发 qa-understand + qa-case-review → 同上
- 不得并发启动有依赖关系的 capability

### 多模块任务调度

网关完成路由和上下文注入后，不介入模块间调度。多模块任务的执行节奏由 qa-functional-test 自主驱动。

---

## 上下文注入协议

触发任何 capability 前，读取其 SKILL.md，在 context 中显式声明：

```
practices_path    = {值}
story_path        = {值}
确认项目名        = {值}
practices_version = {值}    ← 来自 {practices_path}/index.json 的 version 字段
```

多个 capability 同时触发时，各自读 SKILL.md，共享同一套注入变量。

---

## 可用 Capability 列表

### 用户能力（由网关按路由表触发）

#### qa-understand：测试意图理解与提炼

- **路径**：`~/.claude/skills/qalore/capability/qa-understand/SKILL.md`
- **职责**：将任意信息源（PRD/代码/混合）转化为可测试断言，写入 story 的业务逻辑.md 和代码逻辑.md
- **核心思考**：三驱动认知框架（假设优先、模型驱动、证据驱动、边界驱动）+ 渐进式阅读策略
- **适配器**：
  - `text.md`：文本源（PRD/口述），7问追问法
  - `code.md`：代码源（支持多仓库），五镜头追问法
  - `synthesis.md`：多源证据聚合，7种置信度标注
- **产物**：业务逻辑.md + 代码逻辑.md + 统一交接块 `【测试意图已提炼】`

#### qa-functional-test：功能测试用例设计与产物输出

- **路径**：`~/.claude/skills/qalore/capability/qa-functional-test/SKILL.md`
- **职责**：以断言集合为输入，设计覆盖正向/边界/异常/上下游的测试用例，产出 story 和 .mm 脑图
- **核心思考**：用户影响优先——先问「如果这个模块在生产中出问题，用户最先感受到什么损失」
- **输入来源**（按优先级）：context 交接块 → story 业务逻辑+代码逻辑 → 提示用户先触发 qa-understand
- **产物**：测试用例.md + .mm 脑图（可选）

#### qa-case-review：用例评审

- **路径**：`~/.claude/skills/qalore/capability/qa-case-review/SKILL.md`
- **职责**：对测试用例执行多层质量检查，输出问题报告，不产出持久化产物
- **核心思考**：溯源式质量判断——「这批用例拿去执行，会漏掉什么、卡在哪里」
- **三层检查**：结构层（可执行性）→ 覆盖层（四维度+断言比对）→ 归因层（追溯根源）
- **产物**：对话内评审报告（阻断/需改进/建议三级）

### 基础设施（由 Hook 自动触发）

| Capability | 路径 | 触发方式 |
|-----------|------|---------|
| Token 使用统计 | `~/.claude/skills/qalore/capability/qa-token-report/SKILL.md` | Stop Hook 自动执行 |

### Phase 2（未建设）

以下能力尚未实现，对应的 SKILL.md 文件未创建：
- 自动化测试、性能测试、安全测试、混沌测试

Phase 2 请求处理：
1. 告知用户能力尚未建设
2. 不得用通用知识代替
3. 告知启用路径：按 practices-bootstrap.md 新建 practices + 新建 capability/qa-{name}/SKILL.md + 更新本文件能力列表

---

## practices 加载

### 加载 handbook.md（每次任务必执行）

```
context 中存在 【practices:handbook.md:loaded】 → 跳过（0 token）
不存在 → Read({practices_path}/common/handbook.md) → 写入标记
```

### 标记验证

每次任务开始时验证 `【practices:handbook.md:loaded】`：
- 不存在 → 重新 Read handbook.md，写入标记
- 存在 → 继续

其余 practices 文件的 `【practices:*.loaded】` 标记由各 capability 在实际使用前自行验证。

### practices 文件修改

触发条件：用户明确要求变更规范，或 capability 执行中发现需要补充。
触发时先读 `{practices_path}/common/handbook-practices-ops.md`，按写入协议执行。

---

## 快速上手

### 第一步：安装

将 `qalore/` 目录放置到 `~/.claude/skills/qalore/`（Claude Code 自动发现 skills 目录下的技能）。

### 第二步：配置

创建 `~/.claude/qalore-config.json`：

```json
{
  "practices_path": "/absolute/path/to/practices",
  "story_path": "/absolute/path/to/story"
}
```

首次使用时，若 config 不存在，网关会自动引导完成配置。

### 第三步：初始化 practices

确保 practices 目录结构完整，参考 skill 包内 `practices-bootstrap.md` 完成初始化。practices 目录必须包含：

```
practices/
  index.json
  common/
    handbook.md
    handbook-practices-ops.md
    handbook-audit.md
  tech-stacks/functional/
    assertions.md
    cases.md
    changelog.md
    output.md
    story-formats.md
```

### 第四步：使用

在 Claude Code 中直接描述测试任务即可自动触发网关：

```
"帮我分析用户登录模块的需求文档，沉淀到 story"
"读 src/auth/ 目录下的代码，更新登录模块的 story"
"给登录模块出测试用例"
"评审登录模块的测试用例"
"给登录模块出全量用例并输出脑图"
```

---

## 文件包结构

```
qalore/
├── SKILL.md                              # 网关主文件（本文件）
├── practices-bootstrap.md                # practices 初始化指南 + story/index.json Schema
├── qalore.config.template.json           # 配置文件模板
└── capability/
    ├── qa-understand/                    # 测试意图理解与提炼
    │   ├── SKILL.md                      # 三驱动 + 渐进式阅读 + 适配器调度
    │   └── adapters/
    │       ├── text.md                   # 文本源：7问追问
    │       ├── code.md                   # 代码源：五镜头（支持多仓库）
    │       └── synthesis.md              # 多源证据聚合与置信度判断
    ├── qa-functional-test/               # 功能测试用例设计与产物输出
    │   └── SKILL.md
    ├── qa-case-review/                   # 用例质量评审
    │   └── SKILL.md
    └── qa-token-report/                  # Token 使用统计（Stop Hook）
        └── SKILL.md
```

配套的两个独立目录（不包含在 skill 包内）：

```
practices/                                # 测试规范库（跨项目复用）
├── index.json                            # 版本管理入口
├── common/
│   ├── handbook.md                       # 通用规范
│   ├── handbook-practices-ops.md         # practices 操作规范
│   └── handbook-audit.md                 # 审计规范
└── tech-stacks/functional/
    ├── assertions.md                     # 断言规范
    ├── cases.md                          # 用例规范
    ├── changelog.md                      # 变更记录规范
    ├── output.md                         # 产物输出规范
    └── story-formats.md                  # 文件格式规范

story/                                    # 项目测试知识库
└── {项目名}/
    ├── index.json                        # 项目全局视图
    └── {模块名}/
        ├── {模块名}-功能-业务逻辑.md
        ├── {模块名}-功能-代码逻辑.md
        └── {模块名}-功能-测试用例.md
```
