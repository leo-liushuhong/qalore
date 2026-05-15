---
name: qa-case-review
description: >
  用例评审。由 testcraft 调用，不独立触发。
  对测试用例执行多层质量检查，输出问题报告。不产生持久化产物，报告仅在对话中呈现。
  修复路径由 qa-functional-test 承接。
---

# qa-case-review：用例评审

## 前置说明

| 变量 | 来源 | fallback |
|------|------|---------|
| `{practices_path}` | testcraft 注入 | 自动恢复：读 `~/.claude/testcraft-config.json` 重建 context |
| `{story_path}` | testcraft 注入 | 自动恢复：读 `~/.claude/testcraft-config.json` 重建 context |
| `{确认项目名}` | testcraft 注入 | 临时模式下不强制要求；story 模式下暂停向用户确认 |

---

## 核心思考哲学：溯源式质量判断

评审的目标不是找格式问题，而是回答一个问题：**这批用例拿去执行，会漏掉什么、卡在哪里？**

从三个层次思考：

**结构层**：用例本身是否可执行？字段是否完整？每个触发性步骤是否有对应预期？
遵循 `{practices_path}/tech-stacks/functional/cases.md`「用例格式」和「用例质量标准」章节。

**覆盖层**：该测的场景是否都测了？
- 每个功能点是否覆盖了正向/边界/异常/上下游四个维度
- 有断言基准时（业务逻辑.md / 代码逻辑.md / 交接块），逐条比对：每条断言是否有对应 TC？

**归因层**：发现问题时，追溯根源在哪一层？
- 用例写法问题 → qa-functional-test 执行层问题
- 断言没被设计进来 → qa-understand 理解层遗漏
遵循 `{practices_path}/common/handbook.md`「评审规范」章节的严重级别定义。

**评审基准优先级：**
```
联动模式（同会话）：context 中的【测试意图已提炼】交接块 → 三层完整比对
独立评审（跨会话）：story 中的业务逻辑.md + 代码逻辑.md → 有什么用什么
临时模式（粘贴内容）：无基准 → 只做结构层和覆盖层（L2a 四维度）
```

**独立评审模式下两个文件都存在时的合并规则：**
- 以业务逻辑.md 的断言集合为主基准，逐条核查 TC 覆盖
- 代码逻辑.md 中标注了「代码独立」的断言作为补充基准，也逐条核查 TC 覆盖
- 遇到业务逻辑.md 中标注 `⚠️`（文本-代码冲突）的断言：在评审报告中列出冲突并标注「需先与 PM/开发确认后再判断覆盖」，跳过该断言的覆盖检查，不阻断后续评审
- 遇到业务逻辑.md 中标注 `⚠️(代码)`（多源代码冲突）的断言：在评审报告中标注「多源代码冲突未解决，需先在 qa-understand 确认以哪个仓库逻辑为准」，跳过该断言的覆盖检查，不阻断后续评审
- 不重新执行 synthesis 合并逻辑，直接使用 story 中已有的置信度标注

---

## practices 文件

按需加载规范遵循 `{practices_path}/common/handbook.md`「context 标记规范」章节。

本 capability 使用的 practices 文件：
- `tech-stacks/functional/assertions.md`（评审断言覆盖时）
- `tech-stacks/functional/cases.md`（评审用例格式和质量标准时）

handbook.md 已由网关预加载，直接使用；评审严重级别和结论判定规则见 handbook.md「评审规范」章节。

---

## 执行前确认

遵循 handbook.md「执行前确认规范」章节。本 capability 的计划摘要格式：

```
【用例评审执行计划】
项目：{确认项目名}
模块：{模块名}
输入模式：{story 模式 / 临时模式 / 联动模式}
评审用例数：{n} 条
基准：{交接块 / 业务逻辑.md + 代码逻辑.md / 无}
规范版本：{practices version}
```

---

## 产出格式

```
【用例评审报告】
项目：{确认项目名}  模块：{模块名}  评审时间：{YYYY-MM-DD}
评审用例数：{n} 条  规范版本：{practices version}

■ 阻断问题（{n} 条，必须修复）
  [{TC-ID 或 覆盖项}] {问题描述} → 根源：{执行层 / 理解层}

■ 需改进（{n} 条）
  [{TC-ID 或 覆盖项}] {问题描述}

■ 建议优化（{n} 条）
  [{TC-ID 或 覆盖项}] {建议内容}

总结：{n} 条阻断 / {m} 条需改进 / {k} 条建议
结论：{通过 / 需修复后通过 / 不通过}
```

结论判定规则遵循 `{practices_path}/common/handbook.md`「评审规范 · 结论判定规则」。

有阻断问题时：
```
如需修复：执行「修复 {模块名} 以下用例的阻断问题：{TC-ID-001, ...}」
```

评审是过程验证，不写入 story，不更新 index.json。

**评审记录（可选持久化，仅 story 模式和联动模式可用）：**

临时模式下无项目路径，跳过此步骤。

story 模式或联动模式时，报告输出完成后询问用户：
```
是否将本次评审结果写入评审记录？（方便后续跟踪质量趋势）
路径：{story_path}/{项目}/{模块}/{模块名}-功能-评审记录.md
```

用户同意 → 追加写入，格式见 `{practices_path}/tech-stacks/functional/story-formats.md`「评审记录文件」章节。

用户拒绝 → 不写入任何文件，流程结束。
