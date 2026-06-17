# story/index.json Schema 权威定义

本文件是 `story/{项目名}/index.json` 的 schema 权威来源。所有 capability 和 practices 文件以本文为准，`practices-bootstrap.md` 中的格式仅为初始化参考。

---

## 项目级字段

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `project` | string | 是 | 项目名 |
| `description` | string | 是 | 项目一句话描述，面向谁、核心功能 |
| `created` | string (YYYY-MM-DD) | 是 | 项目创建日期 |
| `last_updated` | string (YYYY-MM-DD) | 是 | 项目最后更新日期（各 capability 每次写入后同步更新） |
| `modules` | object | 是 | 模块名 → 模块详细信息的映射 |

## 模块级字段

```json
{
  "{模块名}": {
    "description": "string — 模块一句话描述，面向谁、核心职责",
    "tc_prefix": "string — TC ID 前缀，2-5 个大写字母，注册后不可变",
    "mm_short_id": "string — 脑图短 ID，2-5 个小写字母，注册后不可变",
    "assert_seq": "number — 当前模块已分配的最大 assert 序号，初始为 0",
    "prd_version": "string — 业务逻辑基于的 PRD 版本（可选，无版本时省略此字段）",
    "depends_on": {
      "{模块名}": ["string — 本模块调用的该模块的具体组件/服务/接口名"]
    },
    "business_related": ["string — 本模块业务上影响的其他模块的功能点，格式：{模块名}::{功能点名}"],
    "code_paths": [
      {
        "path": "string — 代码文件或目录路径",
        "entry": "string — 入口函数/类名，如 submit()",
        "depth": "string — 阅读深度（字段级/函数体/接口级/全文）",
        "last_read": "string (YYYY-MM-DD)"
      }
    ],
    "status": {
      "business_logic": "boolean — 业务逻辑.md 是否存在",
      "business_logic_changelog": "boolean — 业务逻辑.changelog.md 是否存在",
      "code_logic": "boolean — 代码逻辑.md 是否存在",
      "code_logic_changelog": "boolean — 代码逻辑.changelog.md 是否存在",
      "tc_count": "number — 测试用例数量，0 表示无用例",
      "pending_count": "number — 当前 [pending] 状态的待确认项数量，0 表示无待确认项"
    },
    "last_updated": "string (YYYY-MM-DD) — 该模块最后更新日期"
  }
}
```

## 字段所有权

| 字段 | 首次写入 | 后续更新 | 写入时机 |
|------|---------|---------|---------|
| `description`（项目级）| gateway（新建项目时询问用户）| 不变 | 项目创建 |
| `description`（模块级）| gateway（新建模块时，可随后由 qa-understand 补充）| qa-understand | 模块创建 / qa-understand 执行 |
| `last_updated`（项目级）| 各 capability（每次写入后同步更新）| 各 capability | 每次 story 写入 |
| `prd_version` | qa-understand（文本适配器）| qa-understand（文本适配器）| qa-understand 执行 |
| `depends_on` | qa-understand（代码适配器，从上下游断言聚合）| qa-understand（代码适配器，每次写入含跨模块标签的上下游断言后重建）| qa-understand 执行 |
| `business_related` | qa-understand（文本或代码适配器，从上下游断言聚合）| qa-understand（每次写入含跨模块标签的上下游断言后重建）| qa-understand 执行 |
| `tc_prefix` | qa-functional-test（首次生成用例时）| 不变（注册后不可变）| 首次 TC 生成 |
| `mm_short_id` | qa-functional-test（首次生成脑图时）| 不变（注册后不可变）| 首次 .mm 输出 |
| `code_paths` | qa-understand（代码适配器）| qa-understand（代码适配器）| qa-understand 执行 |
| `assert_seq` | qa-understand（text 或 code 适配器）| qa-understand（每次分配新 ID 后**立即更新**，不等【待沉淀】统一写入）| 断言 ID 分配时 |
| `status.business_logic` | qa-understand（文本适配器）| qa-understand（文本适配器）| 首次 BL.md 创建 |
| `status.business_logic_changelog` | qa-understand（文本适配器）| qa-understand（文本适配器）| 首次 BL changelog 创建 |
| `status.code_logic` | qa-understand（代码适配器）| qa-understand（代码适配器）| 首次 CL.md 创建 |
| `status.code_logic_changelog` | qa-understand（代码适配器）| qa-understand（代码适配器）| 首次 CL changelog 创建 |
| `status.tc_count` | qa-functional-test | qa-functional-test | 每次 TC 写入 |
| `status.pending_count` | qa-understand | qa-understand（每次写入后同步更新）| 每次 BL/CL 写入 |
| `last_updated`（模块级）| 各 capability | 各 capability | 每次该模块 story 写入 |

## 写入规则

所有 capability 共同遵守：
- 只追加/更新自己所有权的字段，禁止覆盖他人字段
- 禁止删除已有模块条目
- 未发生变更的字段不写入声明
- `assert_seq` 特殊规则：每个适配器完成 ID 分配后**立即**更新此字段（不等【待沉淀】确认），确保跨适配器 ID 续接不受 context 压缩影响
