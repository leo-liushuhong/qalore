---
name: qa-understand
description: >
  测试意图理解与提炼。将任意信息源转化为可测试的理解，写入 story，供 qa-functional-test 和 qa-case-review 使用。
  调度层设计：按需加载对应适配器，不预加载所有内容。
  内置适配器：文本（PRD/需求/口述）、代码（文件/目录/片段）。
  多源时顺序执行各适配器（文本适配器完成后再执行代码适配器），完成后加载综合层产出统一交接块。
  由 testcraft 调用，不独立触发。
---

# qa-understand：测试意图理解与提炼

## 前置说明

| 变量 | 来源 | fallback |
|------|------|---------|
| `{practices_path}` | testcraft 注入 | 自动恢复：读 `~/.claude/testcraft-config.json` 重建 context |
| `{story_path}` | testcraft 注入 | 自动恢复：读 `~/.claude/testcraft-config.json` 重建 context |
| `{确认项目名}` | testcraft 注入 | 暂停，向用户重新确认 |

**不得用猜测值继续执行。**

---

## 适配器注册表

按需加载对应适配器，不预加载所有内容。

**适配器基础路径：** `~/.claude/skills/testcraft/capability/qa-understand/adapters/`

| 信息源类型 | 触发信号 | 适配器文件 | 写入目标 |
|---------|---------|----------|---------|
| 需求文档 / PRD / 口述 / URL | 用户提供文档或需求描述，或描述含「沉淀/提炼/分析/记录/更新业务逻辑」 | `adapters/text.md` | `{模块名}-功能-业务逻辑.md` |
| 代码文件 / 目录 / 片段 | 用户提供代码路径或片段，或描述含「读代码/阅读代码/代码逻辑/更新代码逻辑」 | `adapters/code.md` | `{模块名}-功能-代码逻辑.md` |
| （可扩展） | — | — | — |

**加载规则：**

每个模块处理开始前，先在 context 写入当前模式标记（覆盖上一个模块的旧标记，保证 code.md 读到的是本模块的模式）：

- 单源 → 写入 `【qa-understand-mode: single】`；Read 对应适配器文件，按其协议独立执行
- 多源 → 写入 `【qa-understand-mode: multi】`；顺序执行（不并发），确保 assert_seq 不冲突：
  1. Read 并执行文本适配器（text.md）；执行完成后文本适配器向 context 写入 `【assert_seq_runtime: N】`
  2. Read 并执行代码适配器（code.md）；代码适配器依据 `【qa-understand-mode: multi】` 读取 `【assert_seq_runtime: N】` 续接，不读文件
  3. 两个适配器均完成后，Read `adapters/synthesis.md` 产出统一交接块
- 未注册类型 → 告知用户不支持，提供扩展路径：注册表新增行 + 新建适配器文件

---

## 执行前确认

遵循 handbook.md「执行前确认规范」章节。本 capability 的计划摘要格式：

```
【测试意图理解执行计划】
项目：{确认项目名}
模块：{模块名}
信息源：
  · 文本（{来源描述}，操作：{新建/patch}）     ← 文本源时
  · 代码（{路径}，depth={N}，操作：{新建/patch}）← 代码源时
综合层：{多源时：是 / 单源时：否}
规范版本：{practices version}
```

---

## 统一交接块格式（所有适配器的输出契约）

无论单源或多源，最终向 qa-functional-test 和 qa-case-review 输出统一格式。格式定义、字段声明、置信度标注规则见 `{practices_path}/tech-stacks/functional/story-formats.md`「统一交接块格式」章节。

多模块任务：按模块逐个处理，每个模块完成后立即输出该模块的交接块，不等全部模块完成后再统一输出。
