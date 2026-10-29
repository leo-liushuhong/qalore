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
| `modules` | object | 是 | 模块名 → 模块详细信息的映射 |

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
