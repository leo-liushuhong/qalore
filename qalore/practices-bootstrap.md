# practices 初始化指南

本文件帮助首次使用 qalore 的用户完成 practices 目录的初始化。

> **Schema 权威来源：** `story/index.json` 的完整字段定义、字段所有权表、写入规则见 `{practices_path}/schemas/story-index.schema.md`（唯一权威）。本文件中引用的格式片段仅为初始化参考。

---

## 必须存在的目录结构

```
practices/
  index.json                               ← 版本管理入口（必须）
  common/
    handbook.md                            ← 通用规范（必须）
    handbook-practices-ops.md             ← practices 操作规范，按需加载（必须）
    handbook-audit.md                      ← 审计规范，按需加载（必须）
  tech-stacks/
    functional/
      assertions.md                        ← 可测试断言规范
      cases.md                             ← 功能测试用例规范
      changelog.md                         ← 变更记录规范（断言 + 用例）
      output.md                            ← 产物输出规范
      story-formats.md                     ← story 文件格式规范
```

---

## practices/index.json 最小格式

```json
{
  "version": "2026-01-01-v1",
  "usage_hint": "先读此文件，按需读具体规范，禁止全量读取",
  "conflict_resolution": "规范冲突时，更具体的规范优先：项目特有规范 > 技术栈规范 > 通用规范",
  "changelog": [
    {
      "version": "2026-01-01-v1",
      "changed_files": [],
      "summary": "初始版本"
    }
  ],
  "schemas": {},
  "common": {},
  "tech_stacks": {},
  "projects": {}
}
```

**约束：** 顶层 `version` 必须与 `changelog[0].version` 保持一致，qalore 会校验此一致性。

---

## capability 按需加载的 practices 文件

| 文件 | when_to_load |
|------|-------------|
| `common/handbook.md` | 每次任务必加载（由网关预加载）|
| `functional/assertions.md` | 理解需求或代码时（qa-understand）|
| `functional/cases.md` | 设计或评审测试用例时（qa-functional-test、qa-case-review）|
| `functional/changelog.md` | 写入任何变更记录时（qa-understand 写业务/代码逻辑 changelog；qa-functional-test 写用例 changelog）|
| `functional/output.md` | 生成脑图产物时（qa-functional-test）|
| `functional/story-formats.md` | 读取或写入 story 业务/代码/用例文件时 |

---

## story/index.json 完整字段 Schema

### 项目级（story/{项目名}/index.json）

```json
{
  "project": "string — 项目名",
  "description": "string — 项目一句话描述，面向谁、核心功能",
  "created": "YYYY-MM-DD",
  "last_updated": "YYYY-MM-DD",
  "modules": {
    "{模块名}": {
      "description": "string — 模块一句话描述，面向谁、核心职责",
      "tc_prefix": "string — TC ID 前缀，如 PIPE（由 qa-functional-test 首次写入，注册后不可变）",
      "mm_short_id": "string — 脑图短 ID，如 agt（由 qa-functional-test 首次写入，规则见 cases.md「.mm 短 ID」）",
      "assert_seq": "number — 当前模块已分配的最大 assert 序号，初始为 0（由 qa-understand 维护）",
      "prd_version": "string — 业务逻辑基于的 PRD 版本（可选，无版本时省略此字段）",
      "depends_on": {
        "{模块名}": ["string — 本模块调用的该模块的具体组件/服务/接口名，由 qa-understand 代码适配器从上下游断言聚合"]
      },
      "business_related": ["string — 本模块业务上影响的其他模块的功能点，由 qa-understand 文本/代码适配器从上下游断言聚合，格式：{模块名}::{功能点名}"],
      "code_paths": [
        {
          "path": "string — 代码文件或目录路径",
          "entry": "string — 入口函数/类名，如 submit()",
          "depth": "string — 阅读深度（字段级/函数体/接口级/全文）",
          "last_read": "YYYY-MM-DD"
        }
      ],
      "status": {
        "business_logic": "boolean — 业务逻辑.md 是否存在",
        "business_logic_changelog": "boolean — 业务逻辑.changelog.md 是否存在",
        "code_logic": "boolean — 代码逻辑.md 是否存在",
        "code_logic_changelog": "boolean — 代码逻辑.changelog.md 是否存在",
        "tc_count": "number — 测试用例数量，0 表示无用例",
        "pending_count": "number — 当前 [pending] 状态的待确认项数量，0 表示无待确认项"
      }
    }
  }
}
```

---

## 字段所有权（谁写谁的字段）

| 字段 | 首次写入 | 后续更新 |
|------|---------|---------|
| `description`（项目级）| 网关（新建项目时询问用户）| 不变 |
| `description`（模块级）| 网关（新建模块时，可随后由 qa-understand 补充）| qa-understand |
| `last_updated`（项目级）| 各 capability（每次写入后同步更新）| 各 capability |
| `prd_version` | qa-understand（文本适配器）| qa-understand（文本适配器）|
| `depends_on` | qa-understand（代码适配器，从上下游断言聚合）| qa-understand（代码适配器）|
| `business_related` | qa-understand（文本或代码适配器，从上下游断言聚合）| qa-understand（每次写含跨模块标签的上下游断言后更新）|
| `tc_prefix` | qa-functional-test | 不变 |
| `mm_short_id` | qa-functional-test | 不变 |
| `code_paths` | qa-understand（代码适配器）| qa-understand（代码适配器）|
| `status.business_logic` | qa-understand（文本适配器）| qa-understand（文本适配器）|
| `status.business_logic_changelog` | qa-understand（文本适配器）| qa-understand（文本适配器）|
| `status.code_logic` | qa-understand（代码适配器）| qa-understand（代码适配器）|
| `status.code_logic_changelog` | qa-understand（代码适配器）| qa-understand（代码适配器）|
| `status.tc_count` | qa-functional-test | qa-functional-test |
| `status.pending_count` | qa-understand | qa-understand（每次写入后同步更新）|
| `assert_seq` | qa-understand（text 或 code 适配器）| qa-understand（每次分配新 ID 后更新）|

**写入规则（所有 capability 共同遵守）：**
- 只追加/更新自己所有权的字段，禁止覆盖他人字段
- index.json 禁止删除已有模块条目
- 未发生变更的字段不写入声明

---

## handbook.md 必须包含的章节

| 章节标题 | 用途 |
|---------|------|
| `## story 维护约定` | 增量原则、自解释原则、断点恢复、断言变更规则、用例变更规则 |
| `## story 写入协议` | Write Manifest 格式、确认与执行 |
| `## 评审规范` | 通用问题严重级别和结论判定规则 |

> `practices 写入协议` 和 `practices/index.json 维护规范` 已移至 `handbook-practices-ops.md`，不在 handbook.md 中。

## handbook-practices-ops.md 必须存在

路径：`{practices_path}/common/handbook-practices-ops.md`

仅在用户要求修改 practices 规范时按需加载，包含两节：
- `## practices/index.json 维护规范`
- `## practices 写入协议`
