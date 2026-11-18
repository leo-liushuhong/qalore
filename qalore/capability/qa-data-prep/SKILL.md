---
name: qa-data-prep
description: >
  测试数据准备。由 qalore 调用，不独立触发。
  管理测试资源生命周期：识别前置缺口→造数→登记实例→复用/回收，
  测试数据是资产，不是一次性消耗品。
practices_min_version: "2026-10-30-v14"
---

# qa-data-prep：测试数据准备

## 前置说明

| 变量 | 来源 | fallback |
|------|------|---------|
| `{practices_path}` | qalore 注入 | 自动恢复：读 `~/.dsh/qalore-config.json` 重建 context |
| `{story_path}` | qalore 注入 | 自动恢复：读 `~/.dsh/qalore-config.json` 重建 context |
| `{确认项目名}` | qalore 注入 | 立即终止，输出「项目名 context 已丢失，请重新执行任务」 |

---

## 核心思考哲学：测试数据是资产，不是一次性消耗品

职责 = 资源生命周期管理（识别缺口→造数→登记→复用→回收），
不是「跑用例」，不是「判断功能对不对」。这是 qa-execution 覆盖不到的跨会话、跨执行视角。

数据模型与生命周期见 `{practices_path}/tech-stacks/functional/data-prep.md`（唯一权威来源）。

---

## 触发条件

- 联动触发：qa-execution 扫描出 SKIP/FAIL 前置缺口时
- 显式触发：用户说「造数据/准备数据/前置数据/缺数据」之一

---

## 执行流程

```
1. 扫描执行范围 → 汇总前置条件缺口清单（哪些用例缺什么数据）
2. 缺口分类：
   - 命中已登记 factory → 直接引用造数入口
   - 未命中 → 现场逆向，成功后沉淀为新 factory（可复用闭环）
3. 产出「造数清单」交用户确认（走 write-mock 五边界 declared+confirmed）
4. 执行造数（api/ui/db 三通道）
5. 验证成功（factory.verify）
6. 登记实例（指纹 + state=active + 验收标记）
7. 输出「造数验收清单」供用户亲自验收
```

---

## 与 write_mocks 的关系（引用，不合并）

- `data_fixtures.factories` = 可复用的造数方法**注册表**
- `write_mocks` = 逐次写操作**声明**（需 `confirmed_by`/`confirmed_date`）
- 执行一个 factory = 产生一条 write_mock 声明，声明新增可选字段 `factory_id` 引用工厂
- 两者都走 `safety_fence` 五边界

---

## 约束

- 造数清单（造数前）必须交用户确认
- instances 登记随造数清单确认，不二次确认
- 自动化模式下 fixtures 只作只读参照

---

## 输出

| 输出 | 落点 |
|------|------|
| 造数清单 | 对话内（确认后执行）|
| instances 登记 | story `dependencies.json` 的 `data_fixtures.instances` |
| 造数验收清单 | 对话内（供用户验收）|

---

## practices 文件

- `tech-stacks/functional/data-prep.md`（资源生命周期规范，唯一权威来源）
