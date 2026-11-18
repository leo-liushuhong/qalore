# 测试资源生命周期规范

qa-data-prep 的资源管理标准：**测试数据是资产，不是一次性消耗品。** 定义工厂（factory）、实例（instance）、策略（policy）的格式契约与生命周期闭环。

> 章节导航：生命周期闭环 · 数据模型（factory/instance/policy）· 两态策略 · 登记时机 · 验收清单

---

## 生命周期闭环

```
① 识别缺口 ──→ ② 造数 ──→ ③ 登记 ──→ ④ 复用/回收
 (Identify)    (Create)    (Register)   (Reuse/Recycle)
     ↑                                       │
     └──────────── 复测后新缺口 ───────────────┘
```

闭环价值：① 避免重复逆向（造数入口沉淀为工厂）；② 避免数据失控（实例有指纹+状态）；③ 支持验收（验收清单）；④ 支持跨会话复用与回归（数据可寻址）。

---

## 数据模型

> 分层边界：本文件定义**格式契约**，一律使用占位符（`{api_path}`、`{字段}`、`{指纹键}`、`TC-{PREFIX}-{seq}`）；**真实端点/字段/值只出现在 `story/{项目}/dependencies.json`**，不得出现在 practices 层（类型7 分层越界）。

### factory（资源工厂：可复用的造数入口）

| 字段 | 语义 |
|------|------|
| `id` | 工厂唯一 ID |
| `name` | 人类可读名 |
| `serves` | 造出的数据服务于哪些断言场景 |
| `channel` | 造数通道：`api` / `ui` / `db` |
| `entry` | 造数入口（`{api_path}` / UI 流程 / `{表名}`）|
| `payload_template` | 造数载荷模板（占位符）|
| `preconditions` | 前置条件 |
| `creates` | 造出什么（数据形态）|
| `verify` | 造数后如何验证成功 |
| `rollback` | 如何还原（write-mock 可还原边界）|

### instance（资源实例：已造数据的状态登记）

| 字段 | 语义 |
|------|------|
| `id` | 实例唯一 ID |
| `factory_id` | 引用工厂（必须指向存在的 factory）|
| `fingerprint` | 数据指纹（可寻址、可验收，非空）|
| `state` | `active` / `stale` / `cleaned` |
| `serves_tc` | 服务于哪些用例（`TC-{PREFIX}-{seq}` 列表）|
| `retained_for_acceptance` | 是否保留供验收 |
| `acceptance_status` | `pending` / `accepted` / `rejected` |

### policy（策略）

| 字段 | 语义 |
|------|------|
| `retention` | 保留策略（默认保留供验收）|
| `reuse` | 复用策略（同指纹实例直接复用）|
| `cleanup` | 清理策略（stale 走 write-mock 可还原清理）|
| `automation_mode` | 自动化模式行为（只读参照）|

---

## 两态策略

| 模式 | 数据行为 |
|------|---------|
| 交互模式 | 复用 + 保留供验收（本次造数数据保留，供用户亲自验收）|
| 自动化模式 | fixtures 只作**只读参照**（读取指纹/预期值），执行不依赖现成数据；需造数时走隔离重建，跑完不残留脏态 |

（对齐 `contracts.json#automation` 幂等不变式：自动化每次执行独立、环境干净或只读）

---

## 登记时机

- **造数清单（造数前）** → 用户确认（走 write-mock 五边界 `declared` + `confirmed`）
- **instances 登记（造数后）** → 随造数清单一并确认，**不二次确认**（登记是造数动作的产物记录）

---

## 验收清单

造数后输出验收清单，供用户亲自验收：

| 实例 ID | 指纹 | 状态 | 服务用例 |
|--------|------|------|---------|
| {id} | {指纹键}={值} | active | TC-{PREFIX}-{seq} |
