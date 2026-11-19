# qalore

> 全栈测试工程师网关 + 结构化测试知识库。AI 是主体，框架提供工具、边界与上下文。

---

## 这是什么

qalore 是一个给 AI 使用的测试工程框架。它把「如何测试一个软件系统」这件事，拆成三层可维护的资产：

| 资产 | 是什么 | 类比 |
|------|--------|------|
| **practices** | 测试与工程规范（spec） | 公司规范 |
| **capability** | 测试专业能力（思考方式） | 专业技能 |
| **story** | 结构化测试知识库（业务知识） | 项目上下文 |

**一句话**：story 记住「测什么」，practices 规定「按什么规矩测」，capability 提供「怎么思考着去测」。

---

## 最重要的分离原则

qalore 有一条不可违反的边界：

- **story 是唯一业务知识库** —— 只有 story 承载业务内容（项目名、模块名、API、组件、文案、数据等）。
- **practices 与 capability 是纯测试 + 企业 spec** —— 不得出现任何业务内容，只用占位符（`{模块名}`、`{功能点}`、`{组件}`）描述通用规则。

**判据（换一个项目还能用吗？）**：一条 practices 规范或一个 capability 的思考方式，如果换个被测项目仍然成立，它就是通用 spec；如果依赖某个具体项目的名称，它就泄漏了业务内容，必须下沉到 story。

**断言三层映射**：业务逻辑断言（story 里的 BL）→ 测试用例断言（TC）→ 执行结果（执行报告），三层一一对应，这是 qalore 内部「业务螺旋」与「方法螺旋」的碱基配对。

---

## 目录结构

```
qalore/
├── qalore-bootstrap.md            # 种子指令（自举安装唯一入口，粘贴即触发）
├── qalore.manifest.json           # 分发清单（版本三元组 + story_source + plugins + 待填凭证）
├── agents.json                    # agent 适配器注册表（dsh/claude-code/generic/chat-only）
├── story-template/                # story 空骨架（场景 A 仅框架移植）
├── qalore/                        # skill 包（网关 + capability）
│   └── capability/                # 能力（7 个用户能力 + 1 个维护能力）
│       ├── qa-understand/         # 测试意图理解与提炼（含 text/code/design 适配器 + synthesis）
│       ├── qa-functional-test/    # 功能测试用例设计与产物输出
│       ├── qa-case-review/        # 用例评审
│       ├── qa-execution/          # 自动化测试执行
│       ├── qa-report/             # 测试报告产出
│       ├── qa-data-prep/          # 测试数据准备（资源生命周期）
│       ├── qa-audit/              # 全量审计
│       ├── qa-bootstrap/          # qalore 移植与维护（升级/补装/凭证引导）
│       └── qa-token-report/       # 已废弃（DSH 无 Stop Hook）
├── practices/                     # 规范（spec，纯测试 + 企业 spec）
│   ├── common/                    # 通用规范（handbook 主规范、审计流水线、依赖登记、写入协议…）
│   ├── tech-stacks/functional/    # 技术栈规范（断言、用例、执行、输出、自动化…）
│   ├── schemas/                   # schema 权威定义（story/index.json 结构）
│   ├── contracts.json             # 机器契约（外部工具、自动化不变式、依赖登记）
│   ├── index.json                 # 版本 + changelog（增量读取入口）
│   └── tools/                     # verify-contracts.py（18 项）+ scan-dependency-map.py + gen-mcp-config.py
└── story/                         # 业务知识库（场景 A 用 story-template，场景 B 用独立私有仓库）
```

---

## 快速上手（AI 必读）

执行任何测试任务前，按这个顺序走：

### 1. 读配置

读 `qalore-config.json`，获取三个路径：`practices_path`、`story_path`、`audit_path`。路径必须来自配置，不得硬编码或猜测。

### 2. 环境验证（每次任务必执行）

- **路径有效**：practices / story 目录存在且可读写，`index.json` 是合法 JSON。
- **版本一致**：`index.json` 顶层 `version == changelog[0].version`。
- **能力版本兼容**：每个 capability 的 `practices_min_version` ≤ 当前 practices 版本。
- **依赖体检**：遍历 `contracts.json` 的外部工具，探测 MCP / CLI 是否可用，产出体检报告注入 context。

### 3. 意图识别与路由

对照路由表，把用户意图映射到 capability：

| 触发意图 | Capability |
|---------|-----------|
| 提供需求/代码/文档，或「理解/提炼/沉淀/分析」 | qa-understand |
| 需要测试用例，「生成/出用例/更新story」 | qa-functional-test |
| 「评审/审查用例」 | qa-case-review |
| 「执行/跑+用例/测试」 | qa-execution |
| 「测试报告/测试总结/出具报告/输出测试报告」 | qa-report |
| 「造数据/准备数据/前置数据/缺数据」 | qa-data-prep |
| 「审计/体检/检查一致性/查漂移」 | qa-audit |

### 4. 上下文注入

向触发的 capability 注入：路径、项目名、practices 版本、依赖体检结果、执行环境。多个 capability 共享同一套注入变量，有依赖关系的不得并发。

---

## 七个能力（一句话各做什么）

| 能力 | 职责 | 思考方式 |
|------|------|---------|
| **qa-understand** | 把任意信息源（文本/代码/设计稿）转化为可测试断言 | 三驱动认知框架 + 渐进式阅读 + 多源证据聚合 |
| **qa-functional-test** | 以断言为输入，设计覆盖正向/边界/异常/上下游的用例 | 用户影响优先 + 覆盖拓扑 |
| **qa-case-review** | 对用例做多层质量检查，输出问题报告 | 溯源式质量判断 |
| **qa-execution** | 按 TC 的断言规则在浏览器里逐条执行，产出执行报告 | 断言驱动执行 + 自动化不变式 |
| **qa-report** | 聚合四权威来源产出需求级测试报告，每字段绑定唯一来源 | 报告=聚合不现编 + 机器重算 |
| **qa-data-prep** | 测试资源生命周期管理（识别缺口→造数→登记→复用→回收） | 测试数据是资产，不是消耗品 |
| **qa-audit** | 全量审计 practices/story 的一致性，产出待修复清单 | 机器校验 + 语义审计流水线（19 步） |

**未建设能力**（Phase 2）：性能、安全、混沌。请求时明确告知不支持，不得用通用测试知识替代。

> 内建 `qa-audit` 与独立 skill `qalore-audit` 的分工、以及「双螺旋自迭代」模型，见「双螺旋与自审计」章节。

---

## 机器校验（verify-contracts.py）

`tools/verify-contracts.py` 提供 18 项契约校验，机器能判定的不靠 AI 直觉：

1. assert_seq 数据
2. 断言类型数据
3. assert_seq 副本语义
4. 断言类型计数副本
5. 计数字段（tc_count / pending_count）
6. ID 规则
7. index.json 版本一致性
8. 依赖登记（prod 排除 / 秘密脱敏 / 写 mock 确认 / 凭证解析格式 / 可执行环境 web_url / DB 连接闭环）
9. 外部工具（probe 必填 + CLI 探测）
10. @档位合法性
11. **audit 依赖图对齐**（practices version == audit 依赖图「对齐版本」，版本 gap 由机器暴露）
12. module_group 结构（容器判别不变式 + 递归遍历）
13. 断言语义检查（message-contains 误用分层：强=阻断/弱=提示）
14. 资源/缺陷登记（data_fixtures / defects 结构）
15. 反向 schema（dependencies.json 顶层字段 ⊆ schema，幽灵字段检测）
16. 定位表闭环（@句柄 ↔ locators.json 双向引用）
17. 能力验证状态（data_fixtures 实例数 / code_logic 模块数，报告非阻断）
18. 依赖图完整性（声明 practices_min_version 的 capability 必须在依赖图有记录）

---

## 双螺旋与自审计

qalore 整体遵循「双螺旋自迭代」模型，并配套一个独立的审计方法，二者互为镜像、双向回馈：

**两条螺旋：**

- **业务链（story）** —— 唯一的业务知识库，承载业务逻辑 / 测试用例 / 代码逻辑 / 变更日志，按「项目 → 模块」组织。
- **方法链（qalore = practices + capability）** —— 纯测试 + 企业 spec，只承载测试方法、契约与哲学，严禁参杂业务内容。

两条螺旋通过「断言」碱基配对（BL 断言 → TC 断言 → 执行断言，三层一一映射），通过「审计」自迭代。

**两套审计，分工明确：**

| 审计 | 归属 | 职责 |
|------|------|------|
| **qa-audit** | qalore 内建能力 | 全量审计：19 步流水线 + verify-contracts.py 18 项机器校验，覆盖机器可判定契约与 story 数据一致性 |
| **qalore-audit** | 独立 skill（已注册 DSH） | 变更驱动定点审查：沿依赖图只查受影响下游（七类问题闭合集），不全量重读 |

两者共享版本锚点（机器强制对齐，见 verify 第 11 项），不重复审计同一维度：qalore 每次变更后同步 audit 的依赖图，audit 审查 qalore 后回馈更新 qalore。

**七类问题闭合集**（qalore-audit 的分类）：合约不一致 / 传播遗漏 / 术语陈旧 / 机制模糊 / 结构破损 / 时序错误 / 分层越界。

**核心纲领（分离原则）**：只有 story 承载业务内容；qalore + audit 完全是测试 + 企业 spec，不得参杂任何业务内容。

---

## 版本机制

- **版本号格式**：`{YYYY-MM-DD}-v{n}`（同日递增 n）。
- **practices 变更四步**（缺一不可）：
  1. changelog 头部插入新条目
  2. 顶层 version 同步
  3. 新增规范文件类型时注册
  4. 同步 audit 依赖图对齐版本（新增/修改 producer-consumer 关系时补齐依赖图）
- **practices_min_version**：每个 capability 声明自己依赖的最低 practices 版本，网关在路由前校验（声明要准确投影实际依赖）。

---

## 可移植（自举安装）

qalore 支持把完整测试能力移植到任意 agent / 模型：

**入口**：把仓库根目录的 `qalore-bootstrap.md`（种子指令，自包含）整段复制粘贴给任意 agent，即可完成自举安装——不依赖任何已挂载的 skill。

**能力分级**（诚实承诺，不谎报"完整"）：

| 模式 | 触发条件 | 能力面 |
|------|---------|--------|
| 完整 | 有 skill + MCP + subagent（DSH / Claude Code） | 全部 7 能力 + Playwright/Figma/云效 + 自动化执行 |
| 降级 | 无 skill 但有文件/命令行工具 | practices 注入 prompt；无 Playwright → 手动执行 |
| 只读 | 仅对话 | 只做需求理解/用例设计，产物在对话 |

**分发物**：`qalore.manifest.json`（版本三元组 + story_source + plugins + 待填凭证）、`agents.json`（agent 适配器）、`story-template/`（空骨架）、`tools/gen-mcp-config.py`（MCP 配置生成）。

**story 分发**：框架仓库公开（不含业务）；完整业务 story 走独立私有仓库（`manifest.story_source`）。

**维护**：挂载后由 `qa-bootstrap` capability 负责升级（幂等重跑）、补装工具、凭证引导。

---

## 关键约定

- **渐进式披露**：按上下文流转切割（index.json → 内容文件 → changelog），不按角色切割。
- **人工确认两道门槛**：执行前确认「做什么」、写入前确认「写什么」，不合并、不跳过。
- **不得用通用测试知识替代**：审计方法只来自审计流水线，测试方法只来自 practices/capability。
- **AI 自解释格式**：断言 ID、更新标记、来源标签、待确认状态都内嵌在断言行里，读到即懂。
