# practices 初始化指南

本文件帮助首次使用 testcraft 的用户完成 practices 目录的初始化，并作为 story/index.json 的 schema 权威来源。

---

## 必须存在的目录结构

```
practices/
  index.json                               ← 版本管理入口（必须）
  common/
    handbook.md                            ← 通用规范（必须）
  tech-stacks/
    functional/
      assertions.md                        ← 可测试断言规范
      cases.md                             ← 功能测试用例规范
      changelog.md                         ← 用例变更记录规范
      output.md                            ← 产物输出规范
      story-formats.md                     ← story 文件格式规范
```

---

## practices/index.json 最小格式

```json
{
  "version": "1.0.0",
  "changelog": [
    {
      "version": "1.0.0",
      "date": "YYYY-MM-DD",
      "changed_files": []
    }
  ]
}
```

**约束：** 顶层 `version` 必须与 `changelog[0].version` 保持一致，testcraft 会校验此一致性。

---

## capability 按需加载的 practices 文件

| 文件 | when_to_load |
|------|-------------|
| `common/handbook.md` | 每次任务必加载（由网关预加载）|
| `functional/assertions.md` | 理解需求或代码时（qa-understand）|
| `functional/cases.md` | 设计或评审测试用例时（qa-functional-test、qa-case-review）|
| `functional/changelog.md` | 写入用例变更记录时（qa-functional-test）|
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
  "modules": {
    "{模块名}": {
      "description": "string — 模块一句话描述，面向谁、核心职责",
      "tc_prefix": "string — TC ID 前缀，如 PIPE（由 qa-functional-test 首次写入，注册后不可变）",
      "mm_short_id": "string — 脑图短 ID，如 p1（由 qa-functional-test 首次写入）",
      "prd_version": "string — 业务逻辑基于的 PRD 版本（可选，无版本时省略此字段）",
      "code_paths": [
        {
          "path": "string — 代码文件或目录路径",
          "entry": "string — 入口函数/类名，如 submit()",
          "depth": "number — 阅读深度",
          "last_read": "YYYY-MM-DD"
        }
      ],
      "status": {
        "business_logic": "boolean — 业务逻辑.md 是否存在",
        "code_logic": "boolean — 代码逻辑.md 是否存在",
        "tc_count": "number — 测试用例数量，0 表示无用例",
        "has_pending_items": "boolean — 是否有待确认项未解决"
      },
      "last_updated": "YYYY-MM-DD"
    }
  }
}
```

---

## 字段所有权（谁写谁的字段）

| 字段 | 首次写入 | 后续更新 |
|------|---------|---------|
| `description`（项目级）| 网关（新建项目时询问用户）| 不变 |
| `description`（模块级）| qa-understand | qa-understand |
| `prd_version` | qa-understand（文本适配器）| qa-understand（文本适配器）|
| `tc_prefix` | qa-functional-test | 不变 |
| `mm_short_id` | qa-functional-test | 不变 |
| `code_paths` | qa-understand（代码适配器）| qa-understand（代码适配器）|
| `status.business_logic` | qa-understand（文本适配器）| qa-understand（文本适配器）|
| `status.code_logic` | qa-understand（代码适配器）| qa-understand（代码适配器）|
| `status.tc_count` | qa-functional-test | qa-functional-test |
| `status.has_pending_items` | qa-understand | qa-understand |
| `last_updated` | 任意写入操作 | 任意写入操作 |

**写入规则（所有 capability 共同遵守）：**
- 只追加/更新自己所有权的字段，禁止覆盖他人字段
- index.json 禁止删除已有模块条目
- 未发生变更的字段不写入声明

---

## handbook.md 必须包含的章节

| 章节标题 | 用途 |
|---------|------|
| `## story 维护约定` | 增量原则、自解释原则、断点恢复、用例变更规则 |
| `## story 写入协议` | Write Manifest 格式、确认与执行 |
| `## practices 写入协议` | practices 文件变更的确认与原子写入 |
| `## 评审规范` | 通用问题严重级别和结论判定规则 |
