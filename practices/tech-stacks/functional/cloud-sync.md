# 产物输出规范 — 云效通道

与 `.mm` 脑图通道平行。云效通道将 story 中的测试用例同步到阿里云效 TestHub，供团队在线管理、执行和跟踪。

---

## 通道选择

两个通道独立、不互斥。用户可任选其一或同时使用：

| 触发信号 | 通道 | 产物 |
|---------|------|------|
| 含「输出用例 / 生成用例 / 全量 / .mm」 | `.mm` 通道（`output.md`）| FreeMind `.mm` 文件 |
| 含「云效 / 同步到云效 / 更新到云效」 | 云效通道（本文件）| 云效 TestHub 在线用例 |

两个信号同时存在时，两个通道都执行。

---

## 同步范围

| 用户描述 | 操作范围 |
|---------|---------|
| 含「全量 / 全部模块」 | 全量（同步所有模块到云效） |
| 指定版本号（如「同步 V2.1.2」） | 版本级（仅同步该版本涉及的新增/更新 TC） |
| 指定模块名 | 模块级（仅同步该模块的 TC） |
| 无法匹配 | 询问用户明确范围 |

---

## 执行前确认

遵循 handbook.md「执行前确认规范」章节。云效通道的计划摘要格式：

```
【云效同步执行计划】
项目：{项目名}
范围：{全量 / 版本级 / 模块级}
差异分析：
| 模块 | story tc_count | 云效 count | 新增 | 更新 | 删除 |
|------|---------------|-----------|------|------|------|
| xxx  | n             | m         | +x   | y    | z    |
预估操作数：新增 {n} 条 / 更新 {m} 条 / 删除 {k} 条
```

---

## 写入方法

### API 能力矩阵

| 操作 | API | 可用 | 备注 |
|------|-----|------|------|
| 创建 TC | `POST /testhub/webapi/workitem/testcase` | ✅ | body 见下方模板 |
| 删除 TC | `DELETE /testhub/webapi/workitem/testcase/{id}` | ✅ | 需先 list 获取 identifier |
| 更新 TC | — | ❌ | **必须由用户手动在云效 UI 编辑** |
| 创建目录 | — | ❌ | **必须由用户手动在云效 UI 创建** |
| 获取标签列表 | — | ❌ | **必须由用户从云效设置页面提供 identifier** |

### API 调用方式

云效 API 的 CSRF Token 由 HttpOnly Cookie 管理，无法从 JS 直接获取。**必须通过浏览器会话内的 `fetch()` 调用**——浏览器自动携带认证 Cookie。在 Playwright 环境中的调用方式为 `page.evaluate( async () => { await fetch(...) } )`。

### 创建 TC — 正确 Body 模板

```json
{
  "subject": "TC-{PREFIX}-{seq}: {标题}",
  "testcaseInfo": {
    "stepType": "TABLE",
    "precondition": "<p>{前置条件}</p>",
    "preconditionFormat": "RICHTEXT",
    "stepContent": "[{\"id\":1,\"step\":\"{步骤}\",\"expected\":\"{预期}\"}]",
    "stepContentFormat": "TEST_TABLE",
    "expectedResult": "",
    "expectedResultFormat": "RICHTEXT"
  },
  "spaceIdentifier": "{spaceId}",
  "space": "{spaceId}",
  "directoryIdentifier": "{模块目录ID}",
  "workitemTypeIdentifier": "c8d1f58d7e070faab50a41a98c",
  "category": "Testcase",
  "fieldValueList": [
    { "fieldIdentifier": "tc.priority", "value": "{P0_ID}" },
    { "fieldIdentifier": "tc.type", "value": "{TYPE_ID}" }
  ],
  "tag": ["{TAG_IDENTIFIER}"],
  "assignedTo": "{用户ID}",
  "attachmentIdList": []
}
```

**关键约束：**
- `fieldValueList` 必须同时包含 `tc.priority` 和 `tc.type`，缺一不可
- `tag` 是独立字段，不在 `fieldValueList` 内，格式为 identifier 数组
- `stepContent` 是 JSON 字符串（需 `JSON.stringify`），不是 JSON 对象
- `precondition` 为空时传空字符串 `""`
- `preconditionFormat` 为 `RICHTEXT` 时内容用 `<p>...</p>` 包裹

### 删除 TC

```
DELETE /testhub/webapi/workitem/testcase/{identifier}
```

响应 200 即成功。identifier 通过 `listByDirectory` API 获取。

### 获取模块目录列表

```
POST /testhub/webapi/workitem/directory/list?spaceType=TestRepo&spaceIdentifier={spaceId}
```

每个模块对应一个 directory，`identifier` 字段用于创建 TC 时的 `directoryIdentifier`。

### 获取模块 TC 列表

```
POST /testhub/webapi/workitem/testCase/listByDirectory
Body: {
  "spaceType": "TestRepo",
  "spaceIdentifier": "{spaceId}",
  "category": "Testcase",
  "toPage": 1, "pageSize": 200,
  "conditions": "{\"conditionGroups\":[]}",
  "searchType": "LIST",
  "directoryIdentifier": "{模块目录ID}"
}
```

### 字段 Identifier 速查表

**优先级（tc.priority）：**

| 值 | identifier |
|----|-----------|
| P0 | `e985775e027314af7ea6582904` |
| P1 | `7cff89275873a16f9c32d3d91e` |
| P2 | `f88a006888f443a35fef552f82` |
| P3 | `01c2c957d44e12389f330e0af2` |

**类型（tc.type）：**

| 值 | identifier |
|----|-----------|
| 功能测试 | `9b160e281b765ca83b4e02c947` |

**标签（tag）：**

标签 identifier 无法通过 API 获取。获取方式：
- 用户从云效「设置 → 标签管理」页面提供
- 或从已有 TC 的 `tag` 字段中查找

---

## 安全规则

### 禁止全删重建

**禁止**对一个模块执行「删除全部 TC → 重新创建全部 TC」。TC 的云效内部 ID（USZC 编号）和 identifier 一旦删除无法恢复，且云效不支持修改 TC 的创建时间、创建人等元数据。

允许的操作类型：
- **新增**：云效中不存在的 TC，调用创建 API
- **删除**：无法通过 UI 编辑的 TC（如 3.3 删除），逐条确认后调用删除 API
- **更新**：**必须由用户在云效 UI 手动编辑**（API 不支持更新）

### 批量删除前 Dry-Run

批量删除前必须执行 dry-run，输出将影响的条目清单：

```
【删除 Dry-Run】
| 模块 | 云效序号 | TC ID | 标题 |
|------|---------|-------|------|
| xxx  | USZC-n  | TC-x  | xxxx |
操作：删除以上 {n} 条
确认？(yes/no)
```

用户确认后才能执行。

### 多条件精确过滤

批量操作（删除、查重）必须使用至少三条件联合过滤：
1. 标签（如 `tag` 不含 V2.1.2）
2. 标题正则（如 `/TC-(AGT|ACF|SYS|FIM)-\d{3}:/`）
3. 目录 ID（限定模块范围）

**禁止单条件过滤。**

### 不可用时的 Fallback

| 不可用操作 | Fallback |
|-----------|---------|
| 更新 TC | 在同步计划中列出需更新的条目，用户手动在云效 UI 编辑 |
| 创建模块目录 | 在同步计划中提示用户手动创建，TC 可先建在根目录 |
| 获取标签 ID | 在同步计划中要求用户提供，暂停等待 |

---

## 同步后验证

每次云效同步完成后，**必须**执行以下检查，任一项不通过则暂停展示问题清单：

### 1. 计数验证

| 检查项 | 方法 |
|--------|------|
| 模块 TC 数 | 逐模块对比 `listByDirectory` 返回的 count 与 story index.json `tc_count` |
| 全量 TC 数 | 根目录 count 与 `sum(index.json tc_count)` 一致 |

### 2. 字段完整性验证

| 检查项 | 方法 | 阈值 |
|--------|------|------|
| 类型（tc.type）缺失 | 统计 `tc.type` 为 null/EMPTY 的 TC 数 | 必须为 0 |
| 标签（tag）缺失 | 统计 `tag` 为空的 TC 数 | 必须为 0 |
| 优先级缺失 | 统计 `tc.priority` 为 null/EMPTY 的 TC 数 | 必须为 0 |

### 3. 标签分布验证

| 检查项 | 方法 |
|--------|------|
| V2.1.x 标签数 | 新增 TC 的标签应为对应版本号（如 V2.1.2），旧 TC 保留原标签 |
| 异常标签 | 不应出现与预期版本不匹配的标签（如新增 V2.1.2 TC 不应带 V2.1.1 标签） |

不通过时的处理：
- 计数不一致 → 列出差异模块和数量，重新执行差异分析
- 字段缺失 → 定位缺失的 TC 序号，调用 API 补全（重建该 TC）
- 标签异常 → 定位异常 TC 的序号，删除后以正确标签重建

---

## 文件命名

本文件属于 `tech-stacks/functional/` 技术栈，与 `output.md` 平行。

---

## subagent 执行约束

本章节由 qa-functional-test 在构造 subagent prompt 时引用。
定义 subagent 执行云效同步时的硬约束和参考数据。

### 硬约束

以下规则在 subagent 执行期间零容忍，违反即停止并报告：

#### 标题前缀

前缀判断优先级（从高到低，上一级匹配则停止）：

1. TC 位于 story 的 `## 代码独立` 或 `## 代码独立断言` section → `[仅代码] `
2. TC 对应的断言标注 `（待代码确认）` → `[仅需求] `
3. TC changelog 条目含"代码沉淀"且 BL changelog 无对应新增 → `[仅代码] `
4. TC changelog 条目含"BL-CL synthesis"或 BL changelog 有对应新增 → 不加前缀
5. 以上均无法判定 → 不加前缀

**禁止**在标题中使用 `[V2.1.x]`、`[年-月-日]` 等非 practices 定义的版本标记。

#### 字段完整性
- fieldValueList 必须同时包含 `tc.priority` 和 `tc.type`
- tag 必须是非空 identifier 数组
- stepContent 值必须是 `JSON.stringify` 后的字符串，不是 JSON 对象

#### 删除安全
- 删除前必须输出 dry-run 清单
- 禁止对同一模块执行"删除全部后重建全部"
- 单次删除不超过 50 条
- 包含删除时优先执行删除，再执行创建

#### 执行安全
- 首个 API 调用返回 401 → 立即停止全部操作，报告"未登录"状态
- 失败不阻塞后续独立操作（同条 TC 的创建和删除间存在依赖除外）

#### 并发安全边界
- 同一模块同一时刻只允许一个写操作（创建/删除/更新）
- 不同模块的操作天然隔离，无此约束

#### 同步后验证

所有创建/删除操作完成后必须逐条执行：

1. **计数验证**：调用 directory/list API，逐模块对比 `workitemCount` 与 story `tc_count`
2. **字段完整性验证**：抽查每个模块至少 3 条 TC（不足 3 条则查全部），
   调用 listByDirectory 获取 TC 详情，确认 tc.type、tag、tc.priority 均非空
3. **标签分布验证**：新增 TC 的 tag 与预期版本 identifier 一致

任一验证不通过 → 列出差异清单，不得静默通过。

#### 错误处理

执行结束时返回结构化结果：
```
已完成: [{操作类型, TC ID, 云效 identifier}]
失败:   [{操作类型, TC ID, 错误原因}]
```
不得静默吞错。

### 标识符速查

#### 优先级
| 值 | identifier |
|----|-----------|
| P0 | e985775e027314af7ea6582904 |
| P1 | 7cff89275873a16f9c32d3d91e |
| P2 | f88a006888f443a35fef552f82 |
| P3 | 01c2c957d44e12389f330e0af2 |

#### 类型
| 值 | identifier |
|----|-----------|
| 功能测试 | 9b160e281b765ca83b4e02c947 |

#### 标签
标签 identifier 从已有 TC 的 `tag` 字段提取，或调用 tag/list API 获取。新增 TC 时 tag 必须与预期版本 identifier 一致。

### API 模板

#### 创建 TC
```
POST /testhub/webapi/workitem/testcase
Content-Type: application/json

{
  "subject": "TC-{PREFIX}-{seq}: {标题}",
  "testcaseInfo": {
    "stepType": "TABLE",
    "precondition": "<p>{前置条件}</p>",
    "preconditionFormat": "RICHTEXT",
    "stepContent": "[{\"id\":1,\"step\":\"{步骤}\",\"expected\":\"{预期}\"}]",
    "stepContentFormat": "TEST_TABLE",
    "expectedResult": "",
    "expectedResultFormat": "RICHTEXT"
  },
  "spaceIdentifier": "{spaceId}",
  "space": "{spaceId}",
  "directoryIdentifier": "{dirId}",
  "workitemTypeIdentifier": "c8d1f58d7e070faab50a41a98c",
  "category": "Testcase",
  "fieldValueList": [
    { "fieldIdentifier": "tc.priority", "value": "{优先级ID}" },
    { "fieldIdentifier": "tc.type", "value": "9b160e281b765ca83b4e02c947" }
  ],
  "tag": ["{标签ID}"],
  "assignedTo": "{assignedTo}",
  "attachmentIdList": []
}
```

#### 删除 TC
```
DELETE /testhub/webapi/workitem/testcase/{identifier}
```

#### 查询目录列表
```
POST /testhub/webapi/workitem/directory/list?spaceType=TestRepo&spaceIdentifier={spaceId}
```

#### 查询模块内 TC
```
POST /testhub/webapi/workitem/testCase/listByDirectory
Body: {
  "spaceType": "TestRepo",
  "spaceIdentifier": "{spaceId}",
  "category": "Testcase",
  "toPage": 1, "pageSize": 200,
  "conditions": "{\"conditionGroups\":[]}",
  "searchType": "LIST",
  "directoryIdentifier": "{dirId}"
}
```
