# story/index.json Schema 权威定义

本文件是 `story/{项目名}/index.json` 的 schema 权威来源。所有 capability 和 practices 文件以本文为准，`practices-bootstrap.md` 中的格式仅为初始化参考。

---

## 产品级路由（product_router）

当 `story/{产品名}/` 下包含多个独立子项目（各自持有 index.json）时，可在产品目录新增一个路由层 `index.json`，`kind` 字段固定为 `product_router`，用于让 agent 进入产品目录时先发现下辖子项目，再按需下钻。

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `project` | string | 是 | 产品名 |
| `kind` | string | 是 | 固定值 `product_router`，用于区分普通项目 index.json |
| `description` | string | 是 | 产品一句话描述，面向谁、核心子系统 |
| `sub_projects` | object | 是 | 子项目名 → 相对路径（指向该子项目的 index.json） |

**product_router 只做路由**，不含 `modules` / `assert_seq` / `tc_count` 等项目级字段，也不含子项目的模块明细。agent 进入产品目录：先读 product_router 获取子项目列表 → 按需进入子项目 index.json 读模块明细。

---

## 项目级字段

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `project` | string | 是 | 项目名 |
| `description` | string | 是 | 项目一句话描述，面向谁、核心功能 |
| `created` | string (YYYY-MM-DD) | 是 | 项目创建日期 |
| `last_updated` | string (YYYY-MM-DD) | 是 | 项目最后更新日期（各 capability 每次写入后同步更新） |
| `modules` | object | 是 | 模块名 → 模块详细信息 或 容器名 → 模块容器（module_group）的映射 |

## 模块级字段

```json
{
  "{模块名}": {
    "description": "string — 模块一句话描述，面向谁、核心职责",
    "tc_prefix": "string — TC ID 前缀，2-5 个大写字母，注册后不可变",
    "mm_short_id": "string — 模块脑图短 ID（= TC 前缀全小写），2-5 个小写字母，注册后不可变",
    "assert_seq": "number — 下一个待分配的 assert 序号（= 已分配最大序号 + 1），初始为 1（机器校验见 contracts.json#assert_seq）",
    "prd_version": "string — 业务逻辑基于的 PRD 版本（无版本时写「未关联版本」占位）",
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

## 模块容器（module_group）

当项目需要按菜单/功能域对模块分组时，可在 `modules` 中使用容器节点。容器只做分组，不承载断言/用例；断言 ID、TC 前缀、用例计数均只存在于叶子模块。

```json
{
  "{容器名}": {
    "kind": "module_group",
    "description": "string — 容器一句话描述，面向谁、分组含义",
    "sub_modules": {
      "{子模块名}": { /* 完整叶子模块（见「模块级字段」） */ },
      "{子容器名}": { /* 或递归嵌套容器 */ }
    },
    "last_updated": "string (YYYY-MM-DD) — 容器最后更新日期"
  }
}
```

**判别不变式（机器校验见 contracts.json#module_group）：**

| 判定 | 条件 |
|------|------|
| 是容器 | `kind == "module_group"` ⟺ 有 `sub_modules` ⟺ 无 `tc_prefix`/`mm_short_id`/`assert_seq`/`status` |
| 是叶子模块 | 无 `kind` ⟺ 无 `sub_modules` ⟺ 有 `tc_prefix` |

**语义边界：**
- 容器不得产生任何 `-功能-*.md` 内容文件；内容文件路径为 `story/{项目}/{容器链}/{叶子模块}/{叶子模块}-功能-*.md`，文件名恒用叶子模块名。
- `[模块::功能点]` 跨模块引用、`depends_on`、`business_related` 中的「模块名」均指**叶子模块名**（容器不作为引用目标），因叶子模块名在项目内唯一。
- `tc_prefix` / `mm_short_id` 唯一性范围为**叶子模块内**；容器无 prefix，不参与唯一性判定。
- 嵌套建议 ≤2 层（数据模型允许任意递归，verify 用递归 walker 统一处理）。

## 字段所有权

| 字段 | 首次写入 | 后续更新 | 写入时机 |
|------|---------|---------|---------|
| `description`（项目级）| gateway（新建项目时询问用户）| 不变 | 项目创建 |
| `description`（模块级）| gateway（新建模块时，可随后由 qa-understand 补充）| qa-understand | 模块创建 / qa-understand 执行 |
| `last_updated`（项目级）| 各 capability（每次写入后同步更新）| 各 capability | 每次 story 写入 |
| `prd_version` | qa-understand（文本适配器）| qa-understand（文本适配器）| qa-understand 执行 |
| `depends_on` | qa-understand（代码适配器，从上下游断言聚合）| qa-understand（代码适配器，每次写入含跨模块标签的上下游断言后重建）| qa-understand 执行 |
| `business_related` | qa-understand（文本或代码适配器，从上下游断言聚合）| qa-understand（每次写入含跨模块标签的上下游断言后重建）| qa-understand 执行 |
| `tc_prefix` | gateway/qa-understand（模块创建时，用户确认后预注册）| 不变（注册后不可变）| 模块创建 / 首次 TC 生成（未注册则补注册） |
| `mm_short_id` | gateway/qa-understand（模块创建时，用户确认后预注册）| 不变（注册后不可变）| 模块创建 / 首次 .mm 输出（未注册则补注册） |
| `code_paths` | qa-understand（代码适配器）| qa-understand（代码适配器）| qa-understand 执行 |
| `assert_seq` | qa-understand（text 或 code 适配器）| qa-understand（每次分配新 ID 后**立即更新**，不等【待沉淀】统一写入）| 断言 ID 分配时 |
| `status.business_logic` | qa-understand（文本适配器）| qa-understand（文本适配器）| 首次 BL.md 创建 |
| `status.business_logic_changelog` | qa-understand（文本适配器）| qa-understand（文本适配器）| 首次 BL changelog 创建 |
| `status.code_logic` | qa-understand（代码适配器）| qa-understand（代码适配器）| 首次 CL.md 创建 |
| `status.code_logic_changelog` | qa-understand（代码适配器）| qa-understand（代码适配器）| 首次 CL changelog 创建 |
| `status.tc_count` | qa-functional-test | qa-functional-test | 每次 TC 写入 |
| `status.pending_count` | qa-understand | qa-understand（每次写入后同步更新）| 每次 BL/CL 写入 |
| `last_updated`（模块级）| 各 capability | 各 capability | 每次该模块 story 写入 |
| `description`（容器级）| gateway（新建容器时）| 不变 | 容器创建 |
| `sub_modules` | gateway（新建容器时）| gateway（新建子模块 / 移动模块时）| 容器创建 / 结构调整 |
| `last_updated`（容器级）| 各 capability | 各 capability | 每次该容器下子模块 story 写入 |

## 写入规则

所有 capability 共同遵守：
- 只追加/更新自己所有权的字段，禁止覆盖他人字段
- 禁止删除已有模块条目
- 未发生变更的字段不写入声明
- `assert_seq` 特殊规则：每个适配器完成 ID 分配后**立即**更新此字段（不等【待沉淀】确认），确保跨适配器 ID 续接不受 context 压缩影响

---

## 依赖登记（dependencies.json）

`story/{项目名}/dependencies.json` 是项目级依赖登记文件，三类依赖统一登记。机器可判定契约（访问方法/安全围栏/权限左移/不变式）见 `contracts.json#dependencies`，本文件只定义数据结构，不重复契约定义。

| 类 | 含义 | 供血对象 |
|---|---|---|
| `input` | 输入依赖（源）：文档/设计稿/代码，帮助理解 | 需求理解 → 断言 |
| `execution` | 执行依赖（地基）：环境/地址/账号/DB/范围 | 用例 → 执行 |
| `unverifiable` | 不可测约束：官方硬逻辑/等不了时间的场景 | 断言 → 用例（可测性判定） |

**最小结构：**

```jsonc
{
  "environments": [{
    "id": "test", "executable": true, "web_url": "{Web UI 地址}", "api_url": "{API base 地址}",
    "accounts": [{ "label": "{角色档位}", "user_id": "{标识}", "credential_ref": "secret:{项目}/{账号名}", "permission_scope": ["{模块/范围}"] }],
    "databases": [{ "ref": "{库名}", "access_mode": "read-verify|write-mock", "table_scope": ["{表名}"] }],
    "device_profiles": [{ "id": "{档位名}", "viewport": "{宽x高}", "dpr": 1, "os": "{可选}" }]
  }],
  "inputs": [{ "type": "text|technical|design", "source": "{URL/路径}", "trust": "官方文档|需求文档|推断" }],
  "unverifiable": [{ "id": "DEP-{PREFIX}-{seq}", "symptom": "{症状/错误码}", "locate_path": "{定位路径}" }],
  "write_mocks": [{ "id": "{标识}", "target": "{表/字段/键}", "method": "{操作}", "confirmed_by": "{确认人}", "confirmed_date": "{YYYY-MM-DD}" }]
}
```

**字段所有权：** `environments`/`accounts` 由 gateway 新建项目时引导用户初始化；`inputs` 由 qa-understand 沉淀（输入依赖）；`unverifiable` 由 qa-understand 沉淀（不可测约束）；`write_mocks` 由 qa-functional-test 声明 + qa-case-review 人类确认后写入；qa-audit 校验一致性（引用闭环/脱敏/prod 排除/写 mock 确认标记）。

**`device_profiles`（环境档位）：** 声明该环境支持的机型/系统/viewport 档位（如 desktop/mobile/ios/android）。样式断言值用 `@档位` 后缀引用（如 `element-font-size(.title, 14@mobile)`），档位 ID 必须在此声明。practices 不写死档位值；verify-contracts.py 校验 `@档位` 在已声明档位内。新增机型/系统 → 往此表加一行，不改断言类型。

**安全围栏与访问方法契约：见 `contracts.json#dependencies`，本文件不重复定义。**

---

## 测试资源登记（data_fixtures，dependencies.json 内）

`data_fixtures` 是测试资源生命周期（factory/instance/policy）的数据结构，语义权威见 `tech-stacks/functional/data-prep.md`，机器可判定不变式见 `contracts.json#data_fixtures`。

> 分层边界：factory 的 `entry`/`payload_template`/`verify` 真实值（真实 API 端点/字段/表名）只出现在本 story 文件；practices 层只放占位符（`{api_path}`、`{字段}`、`{指纹键}`）。

**最小结构：**

```jsonc
"data_fixtures": {
  "factories": [{
    "id": "{工厂ID}", "name": "{人类可读名}", "serves": "{服务哪些断言场景}",
    "channel": "api|ui|db", "entry": "{造数入口}",
    "payload_template": "{载荷模板占位符}", "preconditions": ["{前置条件}"],
    "creates": "{造出什么}", "verify": "{验证方式}", "rollback": "{还原方式}"
  }],
  "instances": [{
    "id": "{实例ID}", "factory_id": "{引用工厂}", "fingerprint": { "{指纹键}": "{值}" },
    "state": "active|stale|cleaned", "serves_tc": ["TC-{PREFIX}-{seq}"],
    "retained_for_acceptance": true, "acceptance_status": "pending|accepted|rejected"
  }],
  "policy": { "retention": "{保留策略}", "reuse": "{复用策略}", "cleanup": "{清理策略}", "automation_mode": "{自动化模式行为}" }
}
```

**字段所有权：** `factories` 由 qa-data-prep 沉淀（造数入口逆向成功后登记）；`instances` 由 qa-data-prep 写入（造数后登记，随造数清单确认）；`policy` 由 gateway 初始化（默认值）；qa-audit 校验一致性（factory_id 引用存在、枚举合法、fingerprint 非空）。

---

## 缺陷登记（defects，dependencies.json 内）

`defects` 是外部缺陷系统登记的缺陷映射（需求 ↔ 缺陷 ID ↔ 状态快照），语义权威见 `tech-stacks/functional/report.md`，机器可判定不变式见 `contracts.json#defects`。

> 分层边界：真实 bug_id/title/status 只出现在本 story 文件；practices 层只放占位符（`{bug_id}`）。

**最小结构：**

```jsonc
"defects": [{
  "bug_id": "{缺陷ID}", "title": "{缺陷标题}", "source": "{外部缺陷系统标识}",
  "status": "{状态}", "priority": "{优先级}", "serious_level": "{严重度}",
  "assignee": "{负责人}", "mapped_to": ["{模块/功能点}"], "snapshot_at": "{YYYY-MM-DD}"
}]
```

**字段所有权：** `defects` 由 qa-report 沉淀（从外部缺陷系统拉取真实内容 + 状态快照）；qa-audit 校验一致性（bug_id/source/status 必填、mapped_to 指向存在的模块/功能点）。

> `defects` 与 `unverifiable`（环境不可测约束）不同：`unverifiable` 记录「无法验证的环境问题」，`defects` 记录「已验证的外部缺陷」。与业务逻辑.md 断言 `[pending/resolved]` 状态也不同：后者是断言级内部待确认项，前者是需求级外部缺陷映射。
