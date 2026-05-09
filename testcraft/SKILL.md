---
name: testcraft
description: >
  全栈测试工程师网关。满足以下任一条件时使用：
  1. 收到测试相关任务（生成用例、需求分析、覆盖率检查、用例评审等）
  2. 涉及读写 story 或 practices 的操作（更新需求知识库、同步文档等）
  已建设能力：测试意图理解、功能测试、用例评审。未建设（Phase 2）：自动化、性能、安全、混沌。
  执行前必须先读 ~/.claude/testcraft-config.json 获取 practices 和 story 路径，
  验证路径有效后继续。路径无效时立即停止，不得使用通用知识代替。
---

# testcraft：测试任务网关

## 网关职责

接收测试任务，完成三件事后交给 capability 执行，不干预执行过程：

1. **环境验证** — 路径是否有效、capability 是否可用
2. **意图识别** — 对照路由表推断触发哪些 capability
3. **上下文注入** — 向所有被触发的 capability 注入必要变量

**不负责：** 执行顺序、并发时序、流程控制、写入协议。这些由各 capability 自主声明和管理，执行时序由 Claude 根据 capability 的输入/输出依赖推断。

---

## 三条不可违反的约束

1. **路径约束**：practices_path / story_path 必须从 `~/.claude/testcraft-config.json` 读取，不得硬编码、推断或猜测
2. **能力约束**：未在可用列表中的 capability 不得执行，不得用通用测试知识替代
3. **项目约束**：项目名必须由用户明确（对话中明确提及，或从文档中唯一识别），不得自行假设

---

## 环境验证（每次任务必执行）

读 `~/.claude/testcraft-config.json`：
- **不存在**（首次安装）→ 读 skill 包内 `testcraft.config.template.json` 获取格式参考，引导用户提供 practices_path / story_path → 生成 config 文件 → 继续
- **存在** → 读取 practices_path / story_path

路径验证：
- `{practices_path}/index.json` 不存在 → 停止：「practices 未初始化，请参考 skill 包内 practices-bootstrap.md 完成初始化」
- `{story_path}/` 不存在 → 停止：「story 目录不存在，请创建后重试」
- 全部通过 → 将两个路径写入 context，供所有 capability 使用

---

## 意图识别与 capability 路由

识别项目名（从用户描述或文档中提取）：
- 无法确定 → 暂停询问：「请问这个任务属于哪个项目？当前 story 中已有：{列出 story_path/ 下的目录名}」
- 不得自行假设；模块名与项目名歧义时，唯一匹配直接推断，多项匹配必须暂停确认

识别项目名后检查 story 目录：
- `{story_path}/{确认项目名}/` 不存在（新项目）→ 询问用户：
  「{项目名} 是新项目，请提供一句话描述（面向谁、核心功能），确认后新建 story。」
  → 拒绝终止；同意 + 描述 → 创建 `index.json` 初始结构（含 project / description / created / modules:{}）后继续
- 已存在 → 继续（各 capability 负责检查自身需要的模块目录）

对照路由表识别需要触发的 capability（可多个同时匹配）：

| 触发意图 | Capability |
|---------|-----------|
| 用户提供了任何形式的信息输入（PRD/需求文档/代码/混合），或描述含理解/提炼/阅读/沉淀/分析/记录类意图 | `qa-understand` |
| 用户需要测试用例，描述含「生成/出用例/全量/测试文件」，或无需求文档但指定模块 | `qa-functional-test` |
| 用户描述含「评审/review/检查用例/审查用例」，或粘贴了 TC 内容要评审，或描述含「生成并评审」 | qa-case-review |

无匹配项 → 向用户说明无法识别意图，请求澄清，不猜测执行。

---

## 上下文注入（触发任何 capability 前必执行）

读取目标 capability 的 SKILL.md，在 context 中显式声明：

```
practices_path = {值}
story_path     = {值}
确认项目名     = {值}
```

多个 capability 同时触发时，各自读取 SKILL.md，共享同一套注入变量。

---

## 可用 Capability 列表

子技能封装在包体内，由本 skill 通过 Read 工具显式加载，不对外暴露。

| Capability | SKILL.md 路径 | 状态 |
|-----------|-------------|------|
| 测试意图理解与提炼 | `~/.claude/skills/testcraft/capability/qa-understand/SKILL.md` | ✅ 可用 |
| 功能测试用例设计与产物输出 | `~/.claude/skills/testcraft/capability/qa-functional-test/SKILL.md` | ✅ 可用 |
| 用例评审 | `~/.claude/skills/testcraft/capability/qa-case-review/SKILL.md` | ✅ 可用 |
| 自动化测试 | `~/.claude/skills/testcraft/capability/qa-auto-test/SKILL.md` | ⏸️ Phase 2 |
| 性能/压力测试 | `~/.claude/skills/testcraft/capability/qa-performance-test/SKILL.md` | ⏸️ Phase 2 |
| 安全测试 | `~/.claude/skills/testcraft/capability/qa-security-test/SKILL.md` | ⏸️ Phase 2 |
| 混沌测试 | `~/.claude/skills/testcraft/capability/qa-chaos-test/SKILL.md` | ⏸️ Phase 2 |
| Token 使用统计 | `~/.claude/skills/testcraft/capability/qa-token-report/SKILL.md` | ✅ 可用（由 Stop Hook 自动执行）|

Phase 2 capability 请求处理：
1. 明确告知：「[能力名称] 尚未建设，当前版本不支持」
2. 不得使用通用知识代替执行
3. 告知启用路径：新建 `practices/tech-stacks/{tech}/standards.md` + 新建 `capability/qa-{tech}/SKILL.md` + 更新本文件列表标记为 ✅

---

## practices 版本管理

读取 `{practices_path}/index.json`：
- 校验 `version` == `changelog[0].version`：不一致 → 停止，提示手动修复
- 对比 memory 中记录的版本：
  - 无 memory / 版本不一致 → 读取变更文件，更新 memory
  - 版本一致 → 继续

**加载 handbook.md（每次任务必执行）：**
```
context 中存在 【practices:handbook.md:loaded】 → 跳过（0 token）
不存在 → Read({practices_path}/common/handbook.md)
         加载完成后写入 context：【practices:handbook.md:loaded】
```

**Practices 文件 context 标记规范（供所有 capability 统一使用）：**
```
格式：【practices:{文件简称}:loaded】
示例：【practices:cases.md:loaded】
      【practices:assertions.md:loaded】
      【practices:output.md:loaded】

标记存在 → 该文件内容在 context 中可用，跳过加载
标记不存在（新会话 / 被压缩 / 未加载）→ 加载该文件，加载后写入标记
版本更新时：网关重新加载文件并覆写标记，capability 无需处理版本判断
```

---

## practices 文件修改

触发条件：用户明确要求变更规范，或 capability 执行中发现需要补充。绝大多数日常任务不涉及此步骤。

遵循 `{practices_path}/common/handbook.md`「practices 写入协议」执行：
- 写入前：所有待修改文件合并为一张确认表，一次性展示，不逐文件打断
- 同意后：主体文件 + index.json **并行原子写入**，不得分步

---

## Token 使用统计

由 Stop Hook 自动触发，网关不主动调用，不验证其执行。
