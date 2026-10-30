# 设计适配器（Figma）

从设计稿中独立建立对系统可测试行为的理解。设计信息源是出发点，不依赖 PRD 框架。

> 本适配器通过 **Figma MCP** 读取设计稿（组件/布局/交互状态/视觉样式），产出 UI + 视觉样式断言。粒度上限 = 组件级（不覆盖字段级数据逻辑）。Figma MCP 未接线（`figma_mcp_available=false`）时降级为文本描述，不产出视觉样式断言。

---

## 核心思考哲学：四镜头追问

> 四镜头是设计信息源的认知哲学，与 qa-understand SKILL.md 的三驱动元框架共同构成完整认知体系：
> 三驱动决定「为什么读、何时停、如何识别边界」；四镜头决定「如何从设计稿中提取可测试的 UI 行为」。

读设计稿的语义单元是**组件/页面**（一个可独立感知的 UI 单元：按钮、表单、列表、弹窗、页面布局）。

| 镜头 | 追问 | 产出断言类型 |
|------|------|------------|
| **存在与结构** | 页面上有哪些组件？哪些应该出现/不出现？ | UI 存在性断言（element-exists / element-not-exists / element-count） |
| **文案与状态** | 组件显示什么文案？有哪些状态（默认/禁用/选中/加载）？ | UI 文本/状态断言（element-text / element-enabled / element-disabled） |
| **样式与视觉** | 组件的颜色/字号/字体/间距/尺寸/圆角与设计稿是否一致？ | 视觉样式断言（element-color / element-background-color / element-font-size / element-font-family / element-font-weight / element-padding / element-margin / element-size / element-position / element-border-radius）；仅校验宽度时用 UI 断言 `element-width`（width-only，视觉断言 `element-size` 为宽高同时校验） |
| **交互与反馈** | 用户操作后有什么反馈？弹窗/提示/跳转？ | 交互反馈断言（message-contains / url-contains） |

> 样式断言值支持 `@档位` 后缀（如 `element-font-size(.title, 16@mobile)`）以覆盖多机型/系统兼容，档位清单见 dependencies.json 的 `environments[].device_profiles`。

**追问原则：**
- 四镜头对每个组件/页面全部执行，设计稿有明确呈现 → 记为断言；无明确呈现 → 写入待确认项，不猜测
- 设计稿只描述「应该长什么样」，不描述「内部怎么实现」——数据逻辑/接口契约不属于本适配器范围，由技术适配器（code.md）负责
- 停止阅读：当前页面的所有组件都已建立「存在/文案/样式/交互」四镜头模型
- **不可测约束识别**：同 text.md「追问原则」——设计稿中遇到「等不了时间的场景」（时间维度超出可等待范围）或「官方硬逻辑」时，改记 `DEP-{PREFIX}-{seq}` 不可测约束条目（格式见 story-formats.md「统一交接块格式」）

---

## 信息范围层级

用户提供的设计稿（Figma 链接）是本次任务的主输入，始终首先完整读取，不受本层级约束。

每次任务在以下范围层级内读取 story 文件（与 text.md 层级定义一致，从层级 1 开始）：

- 层级 1 — 目标模块 BL 文件 + 1-hop 上下游 + 待确认项（安全基线）
- 层级 2 — + 测试用例；层级 3 — + 代码；层级 4 — + 跨项目

默认起始层级 1，上限层级 2（design 适配器无论单源或多源组合均不读代码——其任务是提取设计期望而非对照实现，层级 3 的代码读取由 code 适配器负责）。升级规则见 text.md「信息范围层级」章节。

---

## 断言 ID 分配

规则遵循 story-formats.md「断言 ID 规范」（权威来源）：
- 从 index.json 的 `assert_seq` 读取续接起点，直接作为新 ID 起点（语义见 contracts.json#assert_seq）
- **分配完成后立即更新 index.json 的 `assert_seq`**（设为新最大序号 + 1）
- 多源场景下【待沉淀】由 synthesis 统一输出，本节不单独输出

---

## 写入目标格式

遵循 `{practices_path}/tech-stacks/functional/story-formats.md`「业务逻辑文件」格式规范。设计类断言行末 `| upd:{日期}` 后追加 `[来源:design]`，供 synthesis 区分来源。

---

## 产出

**单源（仅设计适配器运行）：** 先输出【测试意图已提炼】交接块（格式见 story-formats.md「统一交接块格式」，供 qa-functional-test / qa-case-review 消费），再输出【待沉淀】声明（格式遵循 `{practices_path}/common/handbook.md`「story 写入协议」）：

```
【待沉淀】
| 文件 | 路径 | 操作 | 变更摘要 |
|------|------|------|---------|
| {模块名}-功能-业务逻辑.md | {story_path}/{项目}/{模块}/ | {新建/3.1新增/3.2更新} | {UI 断言变更摘要} |
| {模块名}-功能-业务逻辑.changelog.md | {story_path}/{项目}/{模块}/ | 只增不删 | {YYYY-MM-DD}（设计稿）{操作摘要} |
| index.json | {story_path}/{项目}/ | patch | {变更字段摘要} |
| dependencies.json | {story_path}/{项目}/ | patch | inputs={交接块「输入依赖」条目}，unverifiable={交接块「不可测约束」DEP 条目}（有则更新，无则不改；格式见 schemas/story-index.schema.md「依赖登记」） |
```

**写入规程：**
- 业务逻辑.md 按「断言变更规则」操作（见 handbook.md）；每条新增/更新断言行末附 `| upd:{日期} [来源:design]`；功能点节头刷新 `> last-upd:{日期}`
- 内容文件写入后必须同步追加 changelog（见 `tech-stacks/functional/changelog.md`）
- index.json 声明字段：`prd_version`（若有版本信号）、`status.pending_count`、`last_updated`（`assert_seq` 已在 ID 分配阶段实时更新）

**多源（文本 + 技术 + 设计同时运行）：** 本节不输出独立的【待沉淀】，执行结果传入 synthesis.md 统一输出。
