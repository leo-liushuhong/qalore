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
├── practices/                     # 规范（spec，纯测试 + 企业 spec）
│   ├── common/                    # 通用规范（handbook 主规范、审计流水线、依赖登记、写入协议…）
│   ├── tech-stacks/functional/    # 技术栈规范（断言、用例、执行、输出、自动化…）
│   ├── schemas/                   # schema 权威定义（story/index.json 结构）
│   ├── contracts.json             # 机器契约（外部工具、自动化不变式、依赖登记）
│   ├── index.json                 # 版本 + changelog（增量读取入口）
│   └── tools/verify-contracts.py  # 机器校验脚本（11 项）
├── capability/                    # 能力（思考方式，5 个用户能力 + 1 个基础设施）
│   ├── qa-understand/             # 测试意图理解与提炼（含 text/code/design 适配器 + synthesis）
│   ├── qa-functional-test/        # 功能测试用例设计与产物输出
│   ├── qa-case-review/            # 用例评审
│   ├── qa-execution/              # 自动化测试执行
│   ├── qa-audit/                  # 全量审计
│   └── qa-token-report/           # Token 统计（基础设施，由 Stop Hook 触发）
└── story/                         # 业务知识库（项目-模块两级，唯一承载业务内容）
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
| 「审计/体检/检查一致性/查漂移」 | qa-audit |

### 4. 上下文注入

向触发的 capability 注入：路径、项目名、practices 版本、依赖体检结果、执行环境。多个 capability 共享同一套注入变量，有依赖关系的不得并发。

---

## 五个能力（一句话各做什么）

| 能力 | 职责 | 思考方式 |
|------|------|---------|
| **qa-understand** | 把任意信息源（文本/代码/设计稿）转化为可测试断言 | 三驱动认知框架 + 渐进式阅读 + 多源证据聚合 |
| **qa-functional-test** | 以断言为输入，设计覆盖正向/边界/异常/上下游的用例 | 用户影响优先 + 覆盖拓扑 |
| **qa-case-review** | 对用例做多层质量检查，输出问题报告 | 溯源式质量判断 |
| **qa-execution** | 按 TC 的断言规则在浏览器里逐条执行，产出执行报告 | 断言驱动执行 + 自动化不变式 |
| **qa-audit** | 全量审计 practices/story 的一致性，产出待修复清单 | 机器校验 + 语义审计流水线（19 步） |

**未建设能力**（Phase 2）：性能、安全、混沌。请求时明确告知不支持，不得用通用测试知识替代。

> 内建 `qa-audit` 与独立 skill `qalore-audit` 的分工、以及「双螺旋自迭代」模型，见「双螺旋与自审计」章节。

---

## 机器校验（verify-contracts.py）

`tools/verify-contracts.py` 提供 11 项契约校验，机器能判定的不靠 AI 直觉：

1. assert_seq 数据
2. 断言类型数据
3. assert_seq 副本语义
4. 断言类型计数副本
5. 计数字段（tc_count / pending_count）
6. ID 规则
7. index.json 版本一致性
8. 依赖登记（prod 排除 / 秘密脱敏 / 写 mock 确认）
9. 外部工具（probe 必填 + CLI 探测）
10. @档位合法性
11. **audit 依赖图对齐**（practices version == audit 依赖图「对齐版本」，版本 gap 由机器暴露）

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
| **qa-audit** | qalore 内建能力 | 全量审计：19 步流水线 + verify-contracts.py 11 项机器校验，覆盖机器可判定契约与 story 数据一致性 |
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

## 关键约定

- **渐进式披露**：按上下文流转切割（index.json → 内容文件 → changelog），不按角色切割。
- **人工确认两道门槛**：执行前确认「做什么」、写入前确认「写什么」，不合并、不跳过。
- **不得用通用测试知识替代**：审计方法只来自审计流水线，测试方法只来自 practices/capability。
- **AI 自解释格式**：断言 ID、更新标记、来源标签、待确认状态都内嵌在断言行里，读到即懂。
