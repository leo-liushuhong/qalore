# testcraft 文件依赖图

testcraft 系统的 producer-consumer 关系图。变更文件 X 后，查此图确定需要检查哪些下游文件。

---

## 核心原则

- **Producer**：定义格式、规则或数据的文件
- **Consumer**：读取并依赖该定义执行任务的文件
- 变更 Producer → 检查所有标注的 Consumer
- 变更 Consumer → 不需要向上检查（消费方不影响定义方）

---

## Practices 文件的依赖关系

### `practices/common/handbook.md`
**Consumer（所有 capability 都消费）：**
- `testcraft/SKILL.md` — 消费：增量原则、写入协议、操作类型定义
- `adapters/text.md` — 消费：写入规程、changelog 触发规则
- `adapters/code.md` — 消费：写入规程、changelog 触发规则
- `adapters/synthesis.md` — 消费：待沉淀格式
- `qa-functional-test/SKILL.md` — 消费：用例变更规则、多模块规范
- `qa-case-review/SKILL.md` — 消费：评审规范

**变更时重点检查：** 操作类型定义（3.1/3.2/3.3）是否与各适配器的操作声明一致

---

### `practices/tech-stacks/functional/story-formats.md`
**Consumer：**
- `adapters/text.md` — 消费：业务逻辑文件格式、置信度标注
- `adapters/code.md` — 消费：代码逻辑文件格式
- `adapters/synthesis.md` — 消费：统一交接块格式（关键合约）
- `qa-functional-test/SKILL.md` — 消费：统一交接块格式（输入来源）
- `qa-case-review/SKILL.md` — 消费：评审记录文件格式

**高风险合约点：** synthesis.md 产出的交接块格式 ↔ story-formats.md 定义的统一交接块格式，两者必须完全一致

---

### `practices/tech-stacks/functional/assertions.md`
**Consumer：**
- `adapters/text.md` — 消费：断言格式（含 upd 标记、置信度）
- `adapters/code.md` — 消费：断言格式（含 upd 标记、来源标注）
- `qa-case-review/SKILL.md` — 消费：断言格式（评审时比对）

---

### `practices/tech-stacks/functional/cases.md`
**Consumer：**
- `qa-functional-test/SKILL.md` — 消费：用例格式、覆盖率规则、跨模块 TC 归属
- `qa-case-review/SKILL.md` — 消费：用例质量标准

**高风险合约点：** cases.md 的跨模块覆盖规则（上下游断言 `[模块::功能点]` 触发）↔ qa-functional-test 的 TC 关联标注步骤

---

### `practices/tech-stacks/functional/changelog.md`
**Consumer：**
- `adapters/text.md` — 消费：断言 changelog 格式
- `adapters/code.md` — 消费：断言 changelog 格式
- `qa-functional-test/SKILL.md` — 消费：用例 changelog 格式

---

### `practices-bootstrap.md`（index.json Schema）
**Consumer：**
- `adapters/text.md` — 消费：business_related 字段格式、status 字段
- `adapters/code.md` — 消费：depends_on 字段格式、code_paths、status 字段
- `adapters/synthesis.md` — 消费：index.json 声明字段列表
- `qa-functional-test/SKILL.md` — 消费：tc_count、tc_prefix 字段

**高风险合约点：** depends_on / business_related 的数据结构（对象 vs 数组），所有写入方必须一致

---

## Skill 文件的依赖关系

### `adapters/synthesis.md`
**Consumer（下游执行者）：**
- `qa-functional-test/SKILL.md` — 消费：统一交接块格式（输入降级链最高优先级）
- `qa-case-review/SKILL.md` — 消费：统一交接块格式

**高风险合约点：** synthesis.md 产出的交接块格式 = story-formats.md 定义 = qa-functional-test 期望的输入格式，三者必须一致

---

### `qa-understand/SKILL.md`（调度层）
**Consumer（被调度）：**
- `adapters/text.md`
- `adapters/code.md`
- `adapters/synthesis.md`

**Consumer（依赖调度层写入的 context 标记）：**
- `adapters/code.md` 依赖 `【qa-understand-mode】` 和 `【code-source: {仓库名}】`
- `adapters/synthesis.md` 依赖 `【assert_seq_runtime: N】`

---

## 高风险合约对（优先检查）

| Producer | Consumer | 合约内容 | 风险说明 |
|---------|---------|---------|---------|
| `story-formats.md` | `synthesis.md` | 统一交接块格式（含回归候选、信息源字段）| 最常出现不一致 |
| `synthesis.md` | `qa-functional-test` | 交接块输入格式 | synthesis 变更必须向下传播 |
| `cases.md` | `qa-functional-test` | 跨模块覆盖规则（上下游断言触发条件）| 曾有"上下游依赖节"旧引用问题 |
| `assertions.md` | `text.md` / `code.md` | 置信度标注体系（7种）| 新增置信度类型必须同步到用例设计策略 |
| `practices-bootstrap.md` | `adapters/*.md` | depends_on / business_related 数据结构 | 对象格式 vs 数组格式易混淆 |

---

## 变更影响速查

| 变更的文件 | 必须检查的文件 |
|-----------|--------------|
| `story-formats.md` | `synthesis.md`, `text.md`, `code.md`, `qa-functional-test`, `qa-case-review` |
| `handbook.md` | 所有 capability SKILL.md 和适配器 |
| `assertions.md` | `text.md`, `code.md`, `qa-case-review` |
| `cases.md` | `qa-functional-test`, `qa-case-review` |
| `changelog.md` | `text.md`, `code.md`, `qa-functional-test` |
| `practices-bootstrap.md` | `text.md`, `code.md`, `synthesis.md`, `qa-functional-test` |
| `synthesis.md` | `story-formats.md`（合约验证）, `qa-functional-test`, `qa-case-review` |
| `text.md` / `code.md` | `synthesis.md`（多源场景下的待沉淀格式）|
| `qa-understand/SKILL.md` | `text.md`, `code.md`, `synthesis.md`（context 标记协议）|
