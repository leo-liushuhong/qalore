---
name: qa-audit
description: >
  qalore 全量审计。先运行 verify-contracts.py 机器校验，再执行 handbook-audit.md
  审计流水线中仍属人工判断的语义步骤，产出审计报告与待修复清单。只读诊断，
  不直接修改 story/practices 文件（修复需用户确认）。
practices_min_version: "2026-10-29-v7"
---

# qa-audit：qalore 全量审计

## 前置说明

| 变量 | 来源 | fallback |
|------|------|---------|
| `{practices_path}` | qalore 注入 | 读 `~/.dsh/qalore-config.json` 重建 |
| `{story_path}` | qalore 注入 | 读 `~/.dsh/qalore-config.json` 重建 |
| `{practices_version}` | qalore 注入 | 读 `{practices_path}/index.json` 的 version |

## 触发条件

用户描述含「审计/体检/全面检查/审计 story/审计 practices/检查一致性/查漂移」之一。

## 执行流程

```
1. 机器校验（必须第一步）：
   python3 {practices_path}/tools/verify-contracts.py
   → 覆盖 11 项：assert_seq 数据 / 断言类型数据 / assert_seq 副本语义 /
     断言类型计数副本 / 计数字段（tc_count·pending_count）/ ID 规则 / index.json 版本一致性 /
     依赖登记（prod 排除·秘密脱敏·写 mock 确认标记）/ 外部工具（probe 必填·cli 探测）/
    @档位合法性 / audit 依赖图对齐（practices version == dependency-map 对齐版本）
   → 记录全部 ❌ 项，作为审计报告第一部分

2. 语义审计（脚本无法覆盖的部分）：
   Read {practices_path}/common/handbook-audit.md（十九步流水线）
   Read {practices_path}/common/handbook-audit-philosophies.md（二十一条设计哲学，按需参考根因）
   执行脚本未覆盖的步骤，重点：
   - 步骤7   原子变更验证（跨模块原子对：模块 A 删除对象 ↔ 模块 B 更新引用）
   - 步骤8   示例即契约检查（文档示例 ↔ 真实数据匹配）
   - 步骤13  Changelog 声明真实性（「声称已修」↔「文件实际状态」）
   - 步骤15  跨模块引用一致性（含悬空引用静态扫描）
   - 步骤17  subagent 分层合规（practices 只含「是什么」，capability 只含「怎么做」）
   - 步骤18  环境可用性一致性（机器探测：跑 external_tools probe ↔ 目标环境实际接线）
   - 步骤19  依赖一致性（依赖↔用例引用闭环、账号边界 ⊇ 用例角色声明、输入依赖↔断言来源可追溯）
   其余步骤（1-6、9-12、14、16）中可由脚本判定的部分已被 verify-contracts.py 覆盖，
   仍剩余的人工判断部分按 handbook-audit.md 原文执行，不得省略。

3. 汇总审计报告（见下方格式）
```

## 审计报告格式

```markdown
# qalore 审计报告
> 审计时间: {ISO 8601} | practices: {version} | 工具: verify-contracts.py + 人工语义审计

## 一、机器校验
| 检查项 | 结果 |
|-------|------|
| assert_seq 数据 | ✅/❌ |
| 断言类型数据 | ✅/❌ |
| assert_seq 副本语义 | ✅/❌ |
| 断言类型计数副本 | ✅/❌ |
| 计数字段 | ✅/❌ |
| ID 规则 | ✅/❌ |
| index.json 版本一致性 | ✅/❌ |
| 依赖登记 | ✅/❌ |
| 外部工具 | ✅/❌ |
| @档位 | ✅/❌ |

## 二、语义审计发现
| 严重级别 | 步骤 | 位置 | 问题 | 建议修复 |
|---------|------|------|------|---------|
| P0/P1/P2/P3 | 步骤N | {文件}:{行} | ... | ... |

## 三、待修复清单（修复前需用户确认）
| 序号 | 文件 | 操作 | 变更 |
|-----|------|------|------|
| 1 | ... | ... | ... |
```

## 约束

- **只读诊断**：本 capability 不直接修改 story/practices 文件。发现的问题进入「待修复清单」，由用户确认后再执行修复。
- **严重级别**：P0 = 阻断级（版本不一致、JSON 损坏、机器校验失败）；P1 = 数据漂移/契约断裂；P2 = 规范自身缺陷；P3 = 建议级完善。判定规则见 handbook.md「评审规范」。
- **范围**：全量审计覆盖 practices + 全部 story 项目；用户指定单项目/单模块时缩小范围。
- **不得用通用测试知识替代**：审计方法只能来自 handbook-audit.md，不得自行发明检查项。
