# qalore 审计规范

每次审计按十九步流水线执行，一步通过才进入下一步。每步的检查方法可独立用于日常增量审计。

> 章节导航：**十九步审计流水线**（1 JSON 结构 → 2 注册表双向 → 3 Schema 双向 → 4 计数字段 → 5 格式合规率 → 6 元数据对齐 → 7 原子变更 → 8 示例即契约 → 9 注册表同质性 → 10 状态通道盘点 → 11 版本契约 → 12 权威-副本 → 13 Changelog 真实性 → 14 基础设施健康 → 15 跨模块引用 → 16 外部系统 → 17 subagent 分层 → 18 环境可用性 → 19 依赖一致性）· **二十一条设计哲学**（哲学 1-21，已迁移至 `common/handbook-audit-philosophies.md`，按需 Read）

---

## 十九步审计流水线

### 步骤1：JSON 结构完整性（F）

**目标**：所有 JSON 可解析，结构一致，无静默错误。特别注意结构体交界处。

```
1. json.load() 全部 JSON 文件
2. version == changelog[0].version
3. changelog 条目数单调递增
4. 无重复 key（Python json.load 静默取最后值，需人工检查 editor diff）
5. 边界专项：每次 changelog 头部插入后，验证 [{...},{...}] 的 },{ 边界完整
   — changelog 条目之间的 },{ 是最脆弱的编辑点
6. 版本号连续性（日期格式专用）：
   — 对同一日期的版本序列（如 2026-06-12-vN），检查 v 值从最大值连续递减到 1，无跳号
   — 不连续 → 标记缺失版本号（如 v12→v10 跳过 v11）
7. changelog 条目 version 字段必填检查：
   — 遍历 changelog 所有条目，逐一检查 `version` 字段存在性
   — 缺失 → 标记「无法索引的 changelog 条目」
```

**适用范围**：`practices/index.json`、全部 `story/{项目}/index.json`（含 `kind=product_router` 的产品级路由文件）。

**product_router 专项**：`kind=product_router` 的产品级路由文件无 `version` / `changelog` 字段，步骤1 中的版本一致性检查（第 2-7 项）对其不适用——仅做 json.load() 合法性 + `sub_projects` 指向存在性检查。

**执行纪律**：每次 `Edit` 后立即 `json.load()` 验证——不等一轮审计结束再统一检查。JSON 损坏最多发生在 changelog 头部插入后的 `},{` 边界，立即验证可将断裂半径限制在单次编辑内。

---

### 步骤2：注册表 ↔ 文件系统双向校验（B）

**目标**：注册表中的每个条目对应磁盘文件，磁盘上的每个文件在注册表中有条目。

```
正向（注册表 → 磁盘）：
  遍历 index.json 中 common 和 tech_stacks 下所有 file 字段
  → 逐一 os.path.exists()
  
反向（磁盘 → 注册表）：
  遍历 practices_path 下所有 .md 文件
  → 逐一检查是否在注册表中
  → 不在 = 未注册（遗漏或废弃文件）
```

**适用范围**：`practices/index.json` 的 `common` / `tech_stacks` / `schemas` 注册段 + `practices_path` 磁盘文件。

**注册表条目字段完整性**（2026-10-22 起，配合 tech_stacks 条目补齐 summary）：
```
  遍历 index.json 中 common / tech_stacks / schemas 下所有条目
  → 每条目必须含 file + summary + when_to_load 三字段
  → 缺失任一字段 → 标记「注册表条目字段不完整」
```

---

### 步骤3：Schema ↔ 数据双向比对（A）

**目标**：Schema 定义的字段在数据中存在且格式正确；数据中存在的字段在 Schema 中有定义。

```
正向（Schema → 数据）：
  对 Schema 中每个字段：取至少 1 个真实数据实例
  → 字段存在？类型匹配？值域合法？
  → 枚举型字段：检查所有实例

反向（数据 → Schema）：
  取 1 个完整数据实例，列出所有字段路径
  → 逐一在 Schema 中找到对应定义
  → 找不到 = Schema 遗漏
```

**适用范围**：`schemas/story-index.schema.md` Schema ↔ 全部 `story/{项目}/index.json`（含 `kind=product_router` 的产品级路由文件）。

**product_router 专项**（2026-10-22 起，配合 schema 新增 product_router 定义）：
```
  - kind 字段必须为固定值 product_router（区分项目 index.json）
  - sub_projects 中每个子项目相对路径指向的 index.json 必须存在（os.path.exists）
  - product_router 不得含 modules / assert_seq / tc_count 等项目级字段（只做路由）
  - 反向：含 kind=product_router 的目录，其 index.json 不得被当作普通项目（modules 缺失不应误报为「项目未初始化」）
```

**枚举型格式字段专项**（适用于 Schema 定义了内部格式模式的 string 字段）：
```
  — 对 Schema 中定义了格式模式的 string 字段（如 {X}::{Y}、YYYY-MM-DD、TC-{PREFIX}-{seq}）
  — 提取所有数据实例，正则验证格式合规率
  — 合规率 < 100% → 逐项列出不合规实例及其所属模块
  — 特别注意部分正确但格式不完整的条目（如「模块名」存在但缺少「::功能点名」）——这类条目比完全缺失更隐蔽，仅靠"字段存在"检查无法发现
```

---

### 步骤4：计数字段完整性校验（C）

**目标**：所有可从源数据推导的计数字段与源一致。

```
对每个计数字段：
  1. 从源数据重新计算实际值
  2. 与存储值比对
  3. 不一致 → 数据漂移，标记差异

计数字段清单：
  - pending_count ← BL.md + CL.md 中 [pending] 行数
  - tc_count       ← TC.md 中 用例 ID：TC- 出现次数
  - assert_seq     ← BL.md + CL.md 中最大 assert ID 序号 + 1
  - BL 头部增量    ← BL changelog 声称的断言数变更（如"31→47"）vs BL 文件新旧版本断言数差异
                   若 changelog 无计数声明 → 标记「changelog 缺少计数声明」
  - 用例 ID 连续性 ← TC.md 中用例 ID 序号无重复（唯一）；允许 3.3 删除导致的缺号，ID 不复用（2026-10-22 起）
  - 断言-用例闭环 ← 每条断言所在的功能点节（BL `## 功能点`）至少被 1 条用例「功能点」字段（路径）覆盖；机制见 cases.md#TC 覆盖验证（功能点路径匹配，**非** [assert-ID] 直接引用；2026-10-27 修正）

操作语义一致性（ID 类字段，2026-10-27 起）：
  - 对每个「ID 类字段」（assert_seq / tc_count / 用例序号），既查存储值（字段值是否正确），也查操作指令（所有写入该字段的 capability/adapter 的操作描述是否与语义一致）
  - assert_seq 操作语义 ← text.md / code.md / qa-functional-test 中的分配指令应为「读续接起点直接作新 ID，分配后设为新最大 + 1」（见 contracts.json#assert_seq），不得出现「读最大序号再 +1」的旧描述
```

**适用范围**：全部 `story/{项目}/index.json` 的 `status` 字段 + 对应的内容文件。

---

### 步骤5：格式合规率采样（D）

**目标**：对每条格式规则，统计所有应遵守实例的合规比例。

```
对每条格式规则：
  1. 列出所有应遵循该规则的实例（文件、条目、章节）
  2. 逐个检查合规性
  3. 报告合规率 = 合规数 / 总数
  4. 合规率 != 100% → 逐项列出不合规实例

关键规则清单：
  - changelog 断言格式           ← 所有 *changelog.md 文件
  - TC 来源标记规则              ← 所有测试用例.md 中备注含"实现待确认"或位于代码独立节
  - mm_short_id 规则             ← 所有 story index.json 模块条目
  - 置信度标注单一权威           ← story-formats.md 全文（查重复定义）
  - 交叉引用章节名               ← 所有 SKILL.md 中 「...」引用
  - 断言类型合法性               ← execution.md 权威类型清单 vs 所有 TC 文件中 `→ 断言：` 实际使用的类型名
  - 通用性合规                   ← 所有 capability SKILL.md + practices .md 文件（不含 index.json changelog）
                                 搜索业务内容（完整类别见 handbook.md「通用性约束」章节「业务内容的完整定义」）：
                                 项目名/产品名/公司名、业务模块/功能名、真实 API 端点、真实组件/服务/类/方法、
                                 真实 CSS 类名/选择器、真实内部变量、真实产品文案、真实 DB 数据、真实 TC ID、真实 URL 路径
                                 命中 → 标记「通用框架含项目定制内容」
                                 注意：practices/index.json changelog 中的 story: 路径引用是历史数据，不在此规则范围内
                                 注意：practices 格式示例中的占位符（如 {项目名}、{模块名}）不视为污染
                                 注意：框架术语（agent=AI代理、gateway=qalore网关、mcp=MCP协议、skill=DSH skill、
                                       credential=凭证引用、member=角色档位、标签=断言/测试平台标签）不属业务内容
	  - subagent prompt 模板完整性   ← cloud-sync.md「subagent 执行约束」章节
	                                 检查：硬约束是否覆盖全部 practices 规则
	                                 检查：标识符速查是否与同文件「字段 Identifier 速查表」一致
	                                 检查：API 模板是否与同文件「API 能力矩阵」一致
	                                 检查：模板占位符是否在 capability 的 prompt 构造指令中被全部引用
	                                 任一不一致 → 标记「subagent prompt 模板不完整」
	  - 章节导航 TOC 存在性       ← 长规范文件（>150 行）头部应有「章节导航」行，点名关键章节
	                               检查：cases.md / story-formats.md / handbook.md 等长文件头是否有「章节导航」
	                               检查：TOC 点名的章节名是否在文件中真实存在（锚点与内容同步）
```

**判断原则**：找到"至少一个正确例子" ≠ 规则被遵守。必须统计全部实例。

---

### 步骤6：元数据 ↔ 行为对齐（E）

**目标**：元数据描述（when_to_load、字段所有权、状态字段）与实际系统行为一致。

```
对每条元数据：
  1. "谁写的" → 对照代码中实际写入该字段的 capability
  2. "何时加载" → 对照 gateway 和各 capability 的 Read 调用
  3. "状态是什么" → 对照实际文件存在性和内容

关键元数据清单：
  - index.json when_to_load     ← 对照 gateway practices 加载 节
  - practices-bootstrap 字段所有权表 ← 对照各 adapter/capability 写入代码
  - story index.json status.*   ← 对照实际文件是否存在
```

---

### 步骤7：原子变更验证（G）

**目标**：规范中用"缺一不可""必须同步"描述的写入对，在数据中逐对验证。

```
从字段所有权表和写入规程提取所有原子对：
  BL.md 写入  → pending_count 同步更新
  CL.md 写入  → pending_count 同步更新
  TC.md 写入  → tc_count 同步更新
  assert 分配 → assert_seq 同步更新
  内容文件写入 → changelog 同步追加
  跨模块波及   → 1-hop 模块 BL 同步更新
    — 若模块 A 的 BL changelog 含删除/废弃条目，且模块 B（∈ A.business_related ∪ A.depends_on）
      的 BL 文件中含引用被删除对象的断言，则 B 的 BL changelog 应有同期的 3.2 更新条目
    — 无 → 标记「跨模块原子性断裂」

对每个原子对：
  → changelog 有对应日期的条目 → 内容文件同日期有变更？
  → pending_count 的变更量 = BL/CL 中 [pending] 净增减？
  → tc_count 的变更量 = TC 文件中用例 ID 净增减？
```

**适用范围**：全部 story/{项目}/index.json 的计数字段 + 对应的 changelog 和内容文件。

**与步骤4（C）的区别**：步骤4 检查"当前值是否等于源推导值"（静态快照），本步骤检查"两个字段是否在同一个变更事件中一起更新了"（动态一致性）。

---

### 步骤8：示例即契约检查（H）

**目标**：文档中的每个具体示例都能在真实数据中找到匹配实例。示例不一致比没有文档更危险。

```
提取所有 practices 文件中的具体示例：
  代码块中的 JSON/XML/markdown 片段
  "如 xxx"、"例：xxx" 后面的值
  ID 格式示例（如 {prefix}001、TC-{PREFIX}-001）
  初始化/最小格式类示例

对每个示例：
  → 找至少 1 个真实数据实例与该示例格式一致
  → 找不到 → 示例过时 或 数据偏离规范
  → 两者都可能是正确的，但不可能同时正确

特殊规则：
  → 初始化/最小格式类示例 → 直接用于 bootstrap 验证（能否用此模板创建合法文件）
  → 格式规范类示例 → 必须与实际数据一致
```

**适用范围**：全部 practices .md 文件中的示例 ↔ 全部 story 数据文件；practices 内部自引用示例（如 bootstrap 最小格式 ↔ practices/index.json 实际格式）。

**与步骤5（D）的区别**：步骤5 检查"数据是否遵循规则"，本步骤检查"文档示例是否真实"——方向相反。规则正确 + 示例错误 = 规范本身有 bug。

---

### 步骤9：注册表同质性检查（I）

**目标**：同一个注册表/清单中的所有条目属于同一语义类别。类别混杂会导致标记含义不一致。

```
对每个注册表/清单：
  1. 提取所有条目，从行为推导其语义类别（不依赖标签文字）
  2. 分类标准：用户可路由触发 / 基础设施自动触发 / 计划中未创建 / 已废弃
  3. 同一清单中出现 ≥2 个类别 → 清单不同质，标记
  4. 对标记的清单：建议按类别拆分为独立表格或章节
```

**适用范围**：gateway capability 列表、practices/index.json 中的文件注册表、story/index.json 的模块列表。

**判断原则**：标签上写「✅ 可用」但一个指"用户可触发"、另一个指"hook 自动运行"、第三个指"文件未创建"——这就是同质性断裂。关键不是标签的样子，是标签背后的行为类别。

---

### 步骤10：状态通道盘点（J）

**目标**：所有组件间的隐式通信通道都有明确的契约（写入者、读取者、格式、恢复策略）。

```
1. 扫描所有组件文件，提取所有共享状态通道：
   — context 标记（【...】格式）
   — 临时文件 / 环境变量
   — 跨 capability 传递的内存状态
2. 对每个通道检查四要素：
   — 写入者：谁创建/更新这个状态？
   — 读取者：谁消费这个状态？
   — 格式：数据的 schema 是什么？有没有可变数据嵌入？
   — 恢复策略：状态丢失（context 压缩、文件被删）后如何重建？
3. 任一要素缺失 → 标记「契约不完整」
4. 特别标记「存储不可恢复数据」的通道（如递增计数器、用户确认结果）→ 高风险
5. 有恢复策略的通道，验证策略是否真的可执行（不是"从 context 重新读"这种循环依赖）
```

**适用范围**：所有 `【...】` context 标记、capability 间传递的交接块、practices 文件的 loaded 标记。

**与哲学9（会话边界即状态边界）的关系**：本步骤是哲学9 的工程化落地——哲学9 诊断了跨会话状态丢失的必然性，本步骤提供系统方法发现所有缺乏契约的状态通道。

---

### 步骤11：消费者-生产者版本契约（K）

**目标**：每个消费 practices 文件的组件声明了它期望的最低版本，且该版本与当前 practices 版本兼容。

```
对每个消费者-生产者关系：
  1. 生产者是否有版本号？
     — practices: index.json 的 version 字段
     — story 内容文件: index.json 的 prd_version / last_updated
  2. 消费者是否声明了最低版本要求？
     — capability SKILL.md: practices_min_version
  3. 消费者未声明 → 标记「隐式依赖」（格式变更时无告警）
  4. 消费者声明的版本 > 生产者当前版本 → 标记「不兼容」
  5. 消费者声明的版本 ≤ 生产者当前版本 → 通过
```

**适用范围**：
- practices ↔ capability（如 qa-functional-test 消费 cases.md）
- capability ↔ capability（如 qa-functional-test 消费 qa-understand 交接块）
- story 文件 ↔ practices（如 TC 文件格式依赖 cases.md 规范版本）
- 基础设施组件 ↔ practices（如 qa-token-report 由 Hook 触发，其版本依赖同样应显式声明）

**强制执行可达性检查**（版本声明的校验路径必须存在）：
```
对每个声明了 practices_min_version 的消费者：
  → 追溯到负责校验此声明的组件（当前为 gateway 的环境验证阶段）
  → 验证该校验组件是否会在运行中读取此消费者的 SKILL.md
  → 不会被读取 → 标记「孤立版本声明：声明存在但永远不会被校验」
  → 注意：校验机制中的"遍历所有 capability" ≠ "遍历被触发的 capability"——前者覆盖基础设施，后者只覆盖用户能力
```

**与步骤1（F）的区别**：步骤1 检查单个文件的版本自洽（version == changelog[0].version），本步骤检查跨组件的版本兼容——两个文件各自自洽，但放在一起可能不兼容。

---

### 步骤12：权威-副本一致性检查（L）

**目标**：所有存在"权威源→副本"关系的文件对，副本内容与权威源一致。副本不是便利——是待偿还的同步债务。

**前置（机器校验）：** 先运行 `python3 {practices_path}/tools/verify-contracts.py`，自动校验 contracts.json 中的机器可判定契约（assert_seq 语义、断言类型清单、计数公式、ID 规则）与 story 数据及所有副本的一致性。脚本通过后，再执行下方的人工语义检查（脚本无法覆盖的语义漂移）。

```
1. 扫描 practices 生态，识别所有"权威-副本"关系：
   — 字段定义：schemas/story-index.schema.md → practices-bootstrap.md（schema 节）
   — 规范内容摘要：handbook-audit.md → index.json（summary 字段）
   — 格式示例：practices/index.json 实际格式 → bootstrap 最小格式示例
   — 注册表条目：index.json 各条目 → 外部引用这些条目的文字描述
   — 章节标题计数：handbook-*.md 实际步骤/哲学数量 → 标题中的数字
   — 标记状态：context 标记注册表（handbook.md）→ 各 SKILL.md 中对标记的引用
   — 断言类型权威-副本：execution.md（权威源）→ cases.md / qa-execution SKILL.md / qa-functional-test SKILL.md（「N 种」计数与类型名清单一致性）
   — assert_seq 权威-副本：contracts.json（单一权威源）→ schema / handbook / audit / story-formats / qa-understand SKILL.md / qa-functional-test SKILL.md / text.md / code.md / bootstrap（存储语义「= 最大 + 1」与操作语义「读续接起点直接作新 ID」一致性）

2. 对每个关系：
   — 提取权威源的当前状态（字段类型、步骤数量、版本格式等）
   — 提取副本的对应描述
   — 不一致 → 标记「副本过期」

3. 特别标记：
   — 描述中嵌入的计数（"六步""十条"等）—— 这些是文本层面的缓存
   — 副本中与权威源矛盾的字段类型/约束（如 number vs string）
   — 副本中使用了与权威源不一致的示例格式

4. 单一权威源检查：
   — 机器可判定的契约（assert_seq / 断言类型 / 计数公式 / ID 规则）只允许一个权威定义（contracts.json）
   — 发现第二个"定义"（完整复制语义，而非「见 contracts.json#xxx」引用）→ 标记「重复定义」，应改为引用
```

**适用范围**：practices 内部文件间的权威-副本关系（schema↔bootstrap、handbook↔index.json summary、bootstrap 示例↔practices 实际格式）、capability SKILL.md 中对 handbook 章节和 context 标记的引用文字。

**与步骤3（A）的区别**：步骤3 检查「规范定义（Schema）vs 实际数据（story JSON）」，本步骤检查「权威文档 vs 其参考副本」——两方都是 practices 内的文档，不是数据文件。与步骤5（D）的关系：步骤5 检查数据是否遵循规则，步骤8（H）检查文档示例是否在数据中有匹配——本步骤更底层：检查同一事物的两份文档描述是否一致。

**与哲学13（副本即债务）的关系**：本步骤是哲学13 的工程化落地——哲学13 诊断了副本的必然漂移性，本步骤提供系统方法发现所有权威-副本不一致。

---

### 步骤13：Changelog 声明真实性验证（M）

**目标**：changelog 中声称的变更在对应文件中确实已被应用。changelog 条目中的行为声明是承诺，不是收据——未兑现的 changelog 比没有 changelog 更危险。

```
对 changelog 采样（最近 N 条，或变更类型含"修复/更新/改为/新增/移除"的条目）：
  1. 提取 changelog 中的可验证行为声明：
     — 标题/名称变更声明（如「A→B」「标题X→Y」）
     — 计数变更声明（如「N→M步」「X→Y条」）
     — 字段类型/值变更声明（如「number→string」「格式X→Y」）
     — 新增/删除节或文件的声明
  2. 对每条声明，读取对应文件的当前实际状态
  3. 声明 ≠ 实际 → 标记「changelog 声明未兑现」
     — 例如：changelog 说标题改成了 B，文件中标题仍是 A
     — 例如：changelog 说计数从 N 改到了 M，文件中实际计数是 K
  4. 特别标记：声明中嵌入了具体数字、名称、路径的条目——这类声明可自动验证，也最容易出错

判断原则：
  — changelog 条目的写入时刻与文件修改时刻之间存在时间差——changelog 可能写于修改之前（预设承诺），
    也可能写于修改之后（追记）。审计不追究时间差的原因，只验证最终文件状态是否与声明一致。
```

**适用范围**：`practices/index.json` changelog 全部条目 ↔ 对应 changed_files 的实际文件内容；`story/{项目}/index.json` changelog（如有）同样适用。

**与步骤7（G）的区别**：步骤7 检查「两个字段是否在同一个变更事件中一起更新了」（A 和 B 的同步性），本步骤检查「changelog 声称做的事，文件是否真的做了」（声明和现实的对应性）。这是两个独立维度——一对原子变更可以都写了（通过步骤7），但 changelog 声称的内容和实际写入的内容可以不同（被步骤13 捕获）。

**与哲学14（Changelog 是承诺不是收据）的关系**：本步骤是哲学14 的工程化落地——哲学14 诊断了 changelog 声明的易假性，本步骤提供系统方法验证每一条可验证声明。

---

### 步骤14：基础设施健康检查（N）

**目标**：skill 自身的可执行文件（脚本、配置）不包含阻碍可移植性或正确性的缺陷。审计不仅覆盖 practices/story 数据生态，也覆盖 skill 的运行环境。

```
1. 硬编码路径检查：
   — 扫描所有可执行文件（.py / .bat / .sh / .ps1）
   — 匹配 C:\Users\...、/home/...、/Users/... 等绝对路径模式
   — 命中 → 标记「硬编码用户路径：不可移植」

2. 环境假设检查：
   — Python 版本假设（如 3.8+ 特性）
   — OS 特定调用（如 win32api、osascript）
   — 文件系统布局假设（如假定 practices_path 在 D: 盘）

3. 错误处理检查：
   — 脚本是否静默吞异常（try/except pass 或 exit 0 在错误路径上）
   — 外部命令调用是否有超时机制

4. 配置外部化检查：
   — 密码/token/key 是否硬编码
   — 路径是否可配置（通过环境变量或配置文件）vs 硬编码
```

**适用范围**：skill 包中所有可执行代码文件（`capability/qa-token-report/read_usage.py`、`probe_hook.py`、`run_silent.bat` 等）、Hook 配置（`settings.json` 中引用的命令路径）、技能包外依赖（如 Python 解释器路径）。

**与其他步骤的关系**：本步骤是审计流水线中唯一检查 skill 自身运行环境的步骤，其余步骤全部聚焦 practices/story 数据生态。当 skill 在非原始开发环境中部署时（如不同用户、不同机器、不同 OS），本步骤发现的问题将直接导致功能不可用。

---

### 步骤15：跨模块引用一致性（O）

**目标**：当某个模块的 BL 变更涉及删除/废弃/重命名对象时，所有通过 `business_related` 或 `depends_on` 显式关联的模块中引用该对象的断言被同步更新。

```
触发条件（从 BL changelog 中检测以下关键词的条目）：
  · 删除 / 废弃 / 移除 / 不再 / 取消
  · 重命名 / 改为 / 合并
  · 角色名、功能点名、入口名的变更声明

1. 从触发条目中提取被变更的对象标识（角色名/功能点名/入口名/模块名）
2. 对每个被变更对象：
   — 扫描当前模块 business_related + depends_on 中列出的所有模块 BL 文件
   — 搜索引用该对象的断言行（文本匹配 或 [模块::功能点] 标签匹配）
   — 存在引用 → 检查该模块的 BL changelog 在同日期或之后是否有对应 3.2 更新条目
   — 无对应更新 → 标记「跨模块波及遗漏：{模块}::{断言ID} 引用了被删除的 {对象}」
3. 对每个被删除/废弃对象：
   — 扫描当前模块自身的 BL 文件
   — 搜索引用该对象的断言行（排除本次变更中已标记 3.3 删除的）
   — 存在未被删除的引用 → 标记「模块内波及遗漏：{断言ID} 仍引用已废弃的 {对象}」

4. 静态悬空引用扫描（不依赖删除/重命名事件，2026-10-27 起）：
   — 对每个模块的 `business_related`（格式 {模块名}::{功能点名}）与 `depends_on`（key = 模块名）
   — 提取被引用模块名，检查其是否存在于当前项目 index.json 的 `modules` 中
   — 不存在 → 标记「悬空引用：{源模块} → {目标模块}（目标模块不存在）」
   — 被引用模块存在时，对 `business_related` 的功能点名（"::" 后段）在该模块 BL 中搜索
     → 无匹配断言行 → 标记「悬空功能点引用：{源模块} → {目标模块}::{功能点名}」
   — 此检查与删除/重命名事件无关，可随时静态执行；命中即记录，不判定对错，供人工确认

判断原则：
  — 标记为「遗漏」的条目可能是合理的（如确认过不需要更新），审计不判定对错，
    只标记供人工确认。但同一变更中 ≥3 处遗漏 → 标记「系统性问题」
  — 此步骤不检查"变更是否应该发生"——只检查"变更发生后，引用方是否跟进了"
```

**适用范围**：所有 story 模块的 BL changelog + BL 文件 + business_related/depends_on 字段。

**与步骤7（G）的区别**：步骤7 检查"同一模块内的写入对是否同步"（BL 写入 ↔ pending_count 更新），本步骤检查"跨模块的、由业务引用关系决定的写入对是否同步"（模块 A 删除对象 ↔ 模块 B 更新引用）。步骤7 的原子对是规范强制定义的（固定的 A-B 对），本步骤的原子对是数据驱动的（谁引用了被删除的对象，谁就需要更新）。

**与步骤13（M）的区别**：步骤13 检查"changelog 声称改了 X，文件是否真的改了 X"（声明 vs 现实），本步骤检查"文件改了 X，引用 X 的其他文件是否也改了"（变更 vs 波及）。

**执行方式**：本步骤依赖文本搜索和人工判断，不要求全自动化。最小执行方式：取最近一次涉及删除/废弃的 BL changelog 条目，对其执行步骤 1-3。完整执行：对所有模块的最近 N 条此类条目执行。

---

### 步骤16：外部系统一致性（P）

**目标**：story 中的 TC 数据与外部系统（如测试管理平台）同步后保持一致；同步过程遵守 `cloud-sync.md` 的方法规范。

本步骤含两个方向：数据一致性（方向 A）和方法合规性（方向 B）。

**方向 A：数据一致性（story ↔ 测试平台）**

```
1. 逐模块读取测试平台目录列表 API，获取每个模块的 TC 数
2. 与 story index.json 中对应模块的 tc_count 比对
3. 对于每个模块：
   — count 不一致 → 标记具体差值
   — 读取平台 TC 列表，检查 type 字段缺失率（必须为 0）
   — 检查 tag 字段缺失率（必须为 0）
   — 检查新增 TC 的 tag 分布是否与预期版本号对齐（如 V2.1.2 版本 TC 应带 V2.1.2 标签）
4. 任一检查不通过 → 标记模块为「不一致」，列出具体差异条目
```

**方向 B：方法合规性（平台同步过程）**

```
1. cloud-sync.md 文件存在性检查：
   — os.path.exists({practices_path}/tech-stacks/functional/cloud-sync.md)
   — 不存在 → 标记「测试平台同步通道规范文件缺失」

2. 同步前差异分析检查：
   — 本次会话若执行了平台同步，是否在操作前输出了差异分析清单（新增/更新/删除明细）？
   — 未输出 → 标记「缺少同步前差异分析」

3. 全删重建检测：
   — 检测平台模块 TC 数是否在同一会话窗口内先降为 0 再恢复到目标值
   — 存在 → 标记「违规：全删重建」
   — 说明：测试平台不支持更新 API，全删重建是绕过限制的错误方式——应只对缺失 TC 做新增、对失效 TC 做删除

4. 批量删除 Dry-Run 检查：
   — 若执行了批量删除，删除前是否输出了 dry-run 清单并获得用户确认？
   — 未输出 → 标记「批量删除缺少 dry-run」

5. 同步后验证执行检查：
   — 同步完成后是否执行了逐模块 count / type 缺失 / tag 分布的校验？
   — 未执行 → 标记「缺少同步后验证」

6. 更新操作合规性：
   — 是否存在通过 API 执行 TC 更新操作（而非由用户在 UI 手动编辑）？
   — 检测方法：同模块内同 TC ID 的新建 TC 出现多次（间隔时间短）
   — 存在 → 标记「违规：使用 API 更新 TC（API 不支持更新）」
```

**适用范围**：story 全模块 index.json + 测试管理平台（或任何外部 TC 管理系��）。方向 A 依赖测试平台 API 可访问性；方向 B 依赖会话行为日志。

**与其他步骤的关系**：本步骤是审计流水线中唯一检查外部系统（而非 practices/story 数据生态）的步骤。步骤 4（C）检查 story 内部计数字段自洽，本步骤检查 story 数据与外部系统的对应关系。步骤 1（F）检查 JSON 结构，本步骤检查 JSON 中的数值是否与外部系统对齐。

**与哲学 2（合规率优先于存在性）的关系**：方向 A 的 type/tag 检查直接贯彻哲学 2——不满足于「至少有一个正确」，而是统计全部实例的合规率。

---

### 步骤17：subagent 分层合规检查（Q）

**目标**：涉及 subagent 委托的 practices 和 capability 文件严格遵守分层——practices 只含规则和数据（"是什么"），capability 只含执行方法和调度决策（"怎么做"）。

```
1. 定位 subagent 相关内容：
   — 搜索 practices 文件中含「subagent」的章节
   — 搜索 capability SKILL.md 文件中含「subagent」的章节

2. practices 侧检查：
   — practices 中是否包含执行方法声明（如"使用单例模式""调用时不加延时"）
     → 是 → 标记「practices 越界：含执行方法」
   — practices 中是否包含项目特定数据（如具体的 spaceId、assignedTo、目录 ID、真实 API 端点、真实 DB 连接串/库表字段）
     → 是 → 标记「practices 越界：含项目特定数据」（通用性约束）

3. capability 侧检查：
   — capability 中是否直接嵌入了 practices 规则原文（而非引用）
     → 是 → 标记「capability 越界：嵌入 practices 规则」
   — capability 中对 practices 的引用是否具体到章节名
     → 未指定具体章节 → 标记「引用粒度不足：应精确到### 标题」
   — capability 的触发条件是否覆盖 practices 中定义的全部硬约束类型
     → 遗漏 → 标记「触发条件不完整：遗漏 practices 中的{约束类型}」

4. 双向引用闭合：
   — practices 中声明的"本章节由 {capability} 引用"是否与实际引用它的 capability 匹配
   — capability 中引用的 practices 章节是否在 practices 文件中实际存在
   — 引用存在但章节标题不匹配 → 标记「引用断裂」
```

**适用范围**：`cloud-sync.md` ↔ `qa-functional-test/SKILL.md` 的 subagent 相关章节（当前阶段）；后续扩展至其他 capability 的 subagent 委托。

**与哲学19（通用框架不得下沉）的关系**：本步骤检查 practices 侧是否混入了项目特定数据——这是哲学19 在 subagent 维度的具体化。

**与哲学20（执行隔离可靠性）的关系**：本步骤是哲学20 的工程化落地——哲学20 定义了分层契约，本步骤提供系统方法验证分层是否被遵守。

---

### 步骤18：环境可用性一致性（R）

**目标**：gateway 能力列表中声明的「可用性」与各 capability 在目标环境（如 DeepSeek Harness / Claude Code）中的实际接线一致。同一 capability 在不同环境的可用面不同——「✅ 可用」声明与「该环境实际不可用」之间的漂移，是 DSH 迁移引入的**新一类漂移轴**（哲学5：元数据是代码投影）。

```
1. 机器探测：遍历 contracts.json#external_tools.tools，逐条运行 probe（type=cli → 命令探测；type=mcp → 查工具列表）
2. 探测结果与「环境可用性标注」表逐项比对，不一致 → 标记「声明 vs 接线漂移」：
   — qa-execution：Playwright MCP 已接线 → 声明「✅ 完整」是否成立
   — qa-token-report：依赖 Stop Hook → 声明「DSH 不生效」与实际是否一致
3. 检查 gateway 能力列表中的「✅ 可用」标记是否被「环境可用性标注」细化
   — 未细化 → 标记「环境可用性未标注：{capability} 的可用性声明未区分环境」
4. 检查环境验证阶段的版本兼容性检查是否遍历「所有已注册 capability」（含基础设施）
   — 只遍历被路由触发的 capability → 标记（哲学15：强制执行可达性）
```

**适用范围**：gateway SKILL.md 能力列表 + 环境可用性标注表 + contracts.json#external_tools 的工具接线（Playwright/psql/Figma MCP/Stop Hook）。

**与步骤14（N）的区别**：步骤14 检查 skill 自身可执行文件的硬编码路径/环境假设（能否在别的机器跑，即可移植性）；本步骤检查「capability 可用性声明 ↔ 目标环境实际接线」（在这个环境里声明可用是不是真的可用，即环境分叉漂移）。两者都是哲学5 的投影失真，但维度不同：一个跨机器，一个跨运行环境。

**与哲学5（元数据是代码投影）的关系**：本步骤是哲学5 在「跨环境」维度的具体化——「✅ 可用」是元数据，目标环境的实际接线是行为，DSH 迁移后两者产生新的投影失真，需要独立步骤校验。

---

### 步骤19：依赖一致性（S）

**目标**：story 依赖登记（`dependencies.json`）与断言/用例之间引用闭环，账号边界覆盖用例角色声明，输入依赖可追溯到断言来源。机器可判定部分（prod 排除 / 秘密脱敏 / 写 mock 确认标记）由 verify-contracts.py 第 8 项覆盖；本步骤补脚本无法覆盖的语义一致性。

```
1. 引用闭环（正向：依赖 → 用例）：
   — dependencies.json 中每条 execution 依赖（账号/DB/环境）被至少 1 条用例引用
   — 未被引用 → 标记「死依赖：登记了但无用例消费」
2. 引用闭环（反向：用例 → 依赖）：
   — 用例「前置条件」引用的执行依赖（账号角色/DB 表/环境）在 dependencies.json 中存在
   — 不存在 → 标记「悬空依赖：用例引用了未登记的依赖」
3. 账号边界覆盖：
   — 用例声明的角色（admin/member/无权限/越权）在 dependencies.json 的 accounts 中有映射
   — 缺映射 → 标记「账号档位缺失：用例声明 {角色} 但无对应账号」
4. 输入依赖可追溯：
   — dependencies.json 的 inputs 条目与断言/待确认项的来源标注（官方文档/需求文档/推断）一致
   — 断言标了「官方文档」但 inputs 无对应条目 → 标记「输入依赖断裂」
5. 写 mock 合法性（脚本覆盖确认标记后的人工侧）：
   — 写 mock 声明是否满足安全围栏五边界（环境白名单/数据白名单/可还原/已声明/已确认）
   — 副作用是否可接受 → 由人类拍板，AI 只做形式核对
```

**适用范围**：全部 `story/{项目}/dependencies.json` + 对应项目的断言/用例文件。

**与哲学15（声明范围=强制执行范围）的关系**：dependencies 契约声明了五围栏/访问方法/引用闭环，机器校验（verify-contracts.py 第 8 项）+ 本步骤共同构成强制执行路径。

---

## 二十一条设计哲学

> 已迁移至 `common/handbook-audit-philosophies.md`，按需 Read。哲学是审计步骤的根因背景（解释「为什么这一步存在」），审计执行时先读本文件（十九步流水线），需要理解步骤背后根因时再 Read 哲学文件。

