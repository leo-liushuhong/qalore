# 飞书思维笔记输出规范

> 飞书云文档「思维笔记」是 qalore 的第三条用例输出通道，与 `.mm`（FreeMind，见 output.md）、云效测试平台（见 cloud-sync.md）平行。通过外部工具 `lark-cli` 实现，机器可判定契约见 `contracts.json#external_tools.lark_cli`；本文件为语义权威。

## 适用场景

| 用户描述信号 | 输出策略 |
|------------|---------|
| 含「输出思维笔记 / 同步思维笔记 / 生成思维笔记」 | 输出飞书思维笔记 |
| 含「输出 .mm / 云效同步 / 沉淀 / 只更新」 | 走对应通道，不输出思维笔记 |
| 无明确信号 | 询问用户后决定 |

## 标题规范

思维笔记标题 = `{需求名称 / 版本号 / 总结标题} 测试用例`

> **概念区分（wiki 节点 title ≠ 根节点 text）**：思维笔记的 **wiki 节点 title**（文档名，创建思维笔记文档时传入的 `title`）= `{需求名称/版本号}测试用例`；而思维笔记的 **根节点（central topic）text**（导图中心主题，创建节点时省略 `parent_id`）= `{项目名}`。二者是不同概念，勿混淆。

## 层级映射（通道无关统一层级）

story 的模块结构映射为思维笔记节点树，与 `.mm`、云效共用同一统一层级：

| story 结构 | 思维笔记节点 | 说明 |
|-----------|-------------|------|
| 项目名 | 根节点 | 笔记根节点 |
| 叶子模块名 | 一级节点 | 模块节点 |
| BL「## 功能点」节名 | 二级节点（= 模块分区） | 功能点分组，TC 挂其下 |
| TC 标题 | 三级节点（= 用例名称） | 用例节点 |
| 前置条件 / 优先级 / 执行步骤 / 预期结果 | 用例节点的字段子节点 | 用例字段 |

> 「模块分区」即 story 的「功能点」，与 `.mm` / 云效通道的「功能点」层同义，三通道术语统一。容器（module_group）不承载 TC，仅作模块之上的可选分组层。

## 节点规则

1. 用例名称节点颜色：P0 → `highlight=olive`；P1/P2/P3 不标。颜色 = P0 的可视化标识。
2. 用例字段：每个用例节点下挂「前置条件：{内容}」「优先级：{P0|P1|P2|P3}」及若干「执行步骤：{步骤文本}」。
3. 预期结果挂执行步骤下：「执行步骤」节点下紧跟一个「预期结果：{内容}」子节点，一一对应。
4. 多步骤拆分：用例含多个测试步骤时，按步骤顺序依次增加多个「执行步骤」节点，每个后面跟随其对应「预期结果」节点，禁止合并。
5. 用例名称 = TC 标题（不含 `TC-{PREFIX}-` 前缀、不含功能点路径前缀）。
6. 节点文本用通用占位符/抽象描述，禁止业务内容泄漏（见 handbook.md「通用性约束」）。
7. 同步是**增量**操作：已存在的节点/内容不改写元数据，仅新增缺失节点；禁止「全删重建」。

## 输出前格式对齐（强制）

批量写入前必须执行两步对齐，避免全量返工：

1. **读模板**：用 `lark-cli wiki +node-list --parent-node-token <目标节点>` 列出目标节点下已有思维笔记；再 `lark-cli mindnotes nodes list --mindnote-id <已有笔记 token>` 读其节点结构作为格式模板。
2. **最小样本确认**：先产 1 个用例的完整节点（1 用例名称 + 前置条件/优先级/执行步骤/预期结果），经用户确认格式后，再批量写入其余用例。

## 外部工具：lark-cli 最快通路

依赖 `lark_cli`（type=cli，probe=`which lark-cli`），契约见 `contracts.json#external_tools.lark_cli`。完整操作链路：

1. **解包 URL**：`lark-cli drive +inspect --url <飞书 wiki URL> --as user` → 返回 space_id / node_token / obj_token / obj_type（须确认 obj_type=mindnote 才继续）。
2. **创建思维笔记文档**（仅当目标节点下无现成笔记时）：`lark-cli api POST /open-apis/wiki/v2/spaces/{space_id}/nodes`，body `{"obj_type":"mindnote","parent_node_token":"<父节点>","node_type":"origin","title":"<标题>"}`。
3. **创建节点**：`lark-cli mindnotes nodes create --mindnote-id <obj_token> --data @file`；nodes[] 字段：`parent_id`（父节点 ID）、`texts:[{element_type:"text", text:{content:"..."}}]`、`highlight`（仅 P0 用 "olive"）。根节点省略 parent_id；子节点 parent_id = 父节点 node_id；一次可传多个 nodes，返回 ids[] 按序对应，用于后续层级挂载。
4. **读节点**：`lark-cli mindnotes nodes list --mindnote-id <obj_token>`。

> Windows 注意：lark-cli 是 npm 包，未全局安装时 `which lark-cli` 不可用；用 `pnpm add @larksuite/cli` 装到临时目录后，若 `lark-cli.CMD` 报「node 不是命令」，直接 `node.exe <包路径>/scripts/run.js <子命令>` 运行（bin 入口见 package.json）。

## 同步后验证

| 检查项 | 方法 | 阈值 |
|--------|------|------|
| 用例节点数 | 统计用例名称节点数（三级节点） | 等于本次输出用例总数 |
| 执行步骤↔预期结果 | 统计「执行步骤」节点数与「预期结果」节点数 | 两者相等（一一对应） |
| 容器无 TC | 检查容器节点下无 TC 叶节点 | 必须为 0 |

任一验证不通过 → 列出差异清单，不得静默通过。

## 文件命名

本文件属于 `tech-stacks/functional/` 技术栈，与 `output.md`、`cloud-sync.md` 平行。
