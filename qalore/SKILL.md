---
name: qalore
description: >
  全栈测试工程师网关。满足以下任一条件时使用：
  1. 收到测试相关任务（生成用例、需求分析、覆盖率检查、用例评审等）
  2. 涉及读写 story 的操作——story 是本 skill 管理的结构化测试知识库（路径存于
     ~/.claude/qalore-config.json），含业务逻辑/测试用例/代码逻辑/变更日志四类文件，
     按项目-模块两级目录组织。用户说「更新story/沉淀/写入story」时必须调用本 skill，
     不得自行在其他路径创建文件代替。
  已建设能力：测试意图理解、功能测试、用例评审。未建设（Phase 2）：自动化、性能、安全、混沌。
  执行前必须先读 ~/.claude/qalore-config.json 获取 practices 和 story 路径，
  验证路径有效后继续。路径无效时立即停止，不得使用通用知识代替。
---

# qalore：测试任务网关

## 网关职责

接收测试任务，完成三件事后交给 capability 执行：

1. **环境验证** — 路径是否有效、capability 是否可用
2. **意图识别** — 对照路由表推断触发哪些 capability，并确定执行顺序
3. **上下文注入** — 向所有被触发的 capability 注入必要变量

**不负责：** 各 capability 内部的执行流程、产物格式、story 写入协议——这些由 capability 和 practices 自主管理。

---

## 三条不可违反的约束

1. **路径约束**：practices_path / story_path 必须从 `~/.claude/qalore-config.json` 读取，不得硬编码、推断或猜测
2. **能力约束**：未在可用列表中的 capability 不得执行，不得用通用测试知识替代
3. **项目约束**：项目名必须由用户明确（对话中明确提及，或从文档中唯一识别），不得自行假设

---

## 环境验证（每次任务必执行）

读 `~/.claude/qalore-config.json`：
- **不存在**（首次安装）→ 读 skill 包内 `qalore.config.template.json` 获取格式参考，引导用户提供 practices_path / story_path → 生成 config 文件 → 继续
- **存在** → 读取 practices_path / story_path

路径验证：
- `{practices_path}/index.json` 不存在 → 停止：「practices 未初始化，请参考 skill 包内 practices-bootstrap.md 完成初始化」
- `{story_path}/` 不存在 → 停止：「story 目录不存在，请创建后重试」
- 全部通过 → 将两个路径写入 context，供所有 capability 使用

**practices 版本一致性验证（路径通过后必执行）：**
- 读取 `{practices_path}/index.json`，校验 `version == changelog[0].version`
- 不一致 → 停止，输出：
  ```
  practices/index.json 版本字段不一致，请手动修复后重试。
  修复方法：将顶层 "version" 字段的值改为与 changelog 数组第一条的 "version" 值相同。
  当前顶层 version：{值}
  changelog[0].version：{值}
  建议以 changelog[0].version 为准（changelog 是写入的权威记录）。
  ```
- 一致 → 继续

---

## 意图识别与 capability 路由

识别项目名（从用户描述或文档中提取）：
- 无法确定 → 暂停询问：「请问这个任务属于哪个项目？当前 story 中已有：{列出 story_path/ 下的目录名}」
- **推断条件（同时满足才可推断，否则暂停确认）：**
  1. 用户明确提及了某个词，且
  2. 该词与 story_path/ 下某目录名**字符串完全相等**（大小写一致）
- 模糊匹配、首字母缩写、关键词匹配、语义相近——均不得推断，必须暂停确认
- 多项匹配必须暂停确认

**模块粒度定义（识别或新建模块时使用）：**
一个模块 = 用户可独立触发、独立感知结果的最小业务功能单元。判断标准：
- 正面：用户能单独描述「我想测 X 的 Y 功能」→ Y 是模块
- 反面：「整个项目」「所有功能」不是模块；单个 API 端点通常也不是，除非业务语义完全独立
- 有疑问时暂停向用户确认，不自行决定粒度

识别项目名后检查 story 目录：
- `{story_path}/{确认项目名}/` 不存在（新项目）→ 询问用户：
  「{项目名} 是新项目，请提供一句话描述（面向谁、核心功能），确认后新建 story。」
  → 拒绝终止；同意 + 描述 → 创建 `index.json` 初始结构（含 project / description / created / modules:{}）后继续
- 已存在 → 继续（各 capability 负责检查自身需要的模块目录）

对照路由表识别需要触发的 capability（可多个同时匹配）：

| 触发意图 | Capability | 前置条件 |
|---------|-----------|---------|
| 用户提供了任何形式的信息输入（PRD/需求文档/代码/混合），或描述含理解/提炼/阅读/沉淀/分析/记录类意图 | `qa-understand` | — |
| 用户需要测试用例，描述含「生成/出用例/全量/测试文件」，或无需求文档但指定模块，或描述含「更新story/写入story/沉淀到story」 | `qa-functional-test` | 同会话触发了 qa-understand 时，须等其完成 |
| 用户描述含「评审/review/检查用例/审查用例」，或粘贴了 TC 内容要评审，或描述含「生成并评审」 | qa-case-review | 联动模式下须等 qa-understand 完成 |

**多 capability 执行顺序约束：**
- 同会话同时触发 qa-understand 和 qa-functional-test → 先执行 qa-understand，待 `【测试意图已提炼】` 交接块产出后，再执行 qa-functional-test
- 同会话同时触发 qa-understand 和 qa-case-review（联动模式）→ 同上，先执行 qa-understand
- 不得并发启动有依赖关系的 capability

无匹配项 → 向用户说明无法识别意图，请求澄清，不猜测执行。

**多模块任务调度：** 网关完成路由和上下文注入后，不介入模块间的迭代调度。多模块任务的执行节奏（逐模块推进、何时输出产物）由 qa-functional-test 自主驱动，遵循 handbook.md「多模块任务规范」章节。

---

## 上下文注入（触发任何 capability 前必执行）

读取目标 capability 的 SKILL.md，在 context 中显式声明：

```
practices_path    = {值}
story_path        = {值}
确认项目名        = {值}
practices_version = {值}    ← 来自 {practices_path}/index.json 的 version 字段（环境验证阶段已读取）
```

多个 capability 同时触发时，各自读取 SKILL.md，共享同一套注入变量。

---

## 可用 Capability 列表

子技能封装在包体内，由本 skill 通过 Read 工具显式加载，不对外暴露。

| Capability | SKILL.md 路径 | 状态 |
|-----------|-------------|------|
| 测试意图理解与提炼 | `~/.claude/skills/qalore/capability/qa-understand/SKILL.md` | ✅ 可用 |
| 功能测试用例设计与产物输出 | `~/.claude/skills/qalore/capability/qa-functional-test/SKILL.md` | ✅ 可用 |
| 用例评审 | `~/.claude/skills/qalore/capability/qa-case-review/SKILL.md` | ✅ 可用 |
| 自动化测试 | `~/.claude/skills/qalore/capability/qa-auto-test/SKILL.md` | ⏸️ Phase 2 |
| 性能/压力测试 | `~/.claude/skills/qalore/capability/qa-performance-test/SKILL.md` | ⏸️ Phase 2 |
| 安全测试 | `~/.claude/skills/qalore/capability/qa-security-test/SKILL.md` | ⏸️ Phase 2 |
| 混沌测试 | `~/.claude/skills/qalore/capability/qa-chaos-test/SKILL.md` | ⏸️ Phase 2 |
| Token 使用统计 | `~/.claude/skills/qalore/capability/qa-token-report/SKILL.md` | ✅ 可用（由 Stop Hook 自动执行）|

Phase 2 capability 请求处理：
1. 明确告知：「[能力名称] 尚未建设，当前版本不支持」
2. 不得使用通用知识代替执行
3. 告知启用路径：新建 `practices/tech-stacks/{tech}/standards.md` + 新建 `capability/qa-{tech}/SKILL.md` + 更新本文件列表标记为 ✅

---

## practices 加载

版本一致性已在环境验证阶段校验（`version == changelog[0].version`），此处不重复。

**加载 handbook.md（每次任务必执行）：**
```
context 中存在 【practices:handbook.md:loaded】 → 跳过（0 token）
不存在 → Read({practices_path}/common/handbook.md)
         加载完成后写入 context：【practices:handbook.md:loaded】
```

**每次任务开始时验证标记（防止 context 压缩后标记丢失）：**
```
【practices:handbook.md:loaded】 不存在 → 重新 Read handbook.md，写入标记
存在 → 继续（其余 practices 文件的 `【practices:*.loaded】` 标记由各 capability 在实际使用前自行验证：标记存在 → 跳过 Read；标记不存在（含 context 压缩后丢失）→ 重新 Read 并写入标记）
```

context 标记规范（格式、规则）见 handbook.md「context 标记规范」章节。

---

## practices 文件修改

触发条件：用户明确要求变更规范，或 capability 执行中发现需要补充。绝大多数日常任务不涉及此步骤。

触发时先 Read `{practices_path}/common/handbook-practices-ops.md`，按其中「practices 写入协议」执行；practices/index.json 的版本管理规则见同文件「practices/index.json 维护规范」章节。

---

## Token 使用统计

由 Stop Hook 自动触发，网关不主动调用，不验证其执行。
