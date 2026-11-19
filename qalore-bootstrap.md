# qalore 自举安装指令（种子指令）

> 本文件是 qalore 测试框架的**自包含安装入口**。把它整段复制粘贴给任意 agent，即可在对方本地完成 qalore 的移植，**不依赖任何已挂载的 skill**。

## 你的任务

你是 qalore 测试框架的安装助手。当前工作目录就是 qalore 仓库根目录。请按顺序完成以下 7 步，把 qalore 完整移植到本环境，最后输出「移植验收报告」。

## 步骤 0：确认仓库内容

确认当前目录包含以下组件（读 `qalore.manifest.json` 核对）：

- `qalore/` — skill 包（网关 + capability）
- `practices/` — 规范 + 契约 + 校验脚本
- `qalore-bootstrap.md` — 本文件（种子指令）
- `qalore.manifest.json` — 分发清单
- `agents.json` — agent 适配器注册表
- `story-template/` — 空 story 骨架

缺任一组件 → 停止并报告「仓库不完整」。

## 步骤 1：探测环境

1. 读 `agents.json`，根据 `probe_hints` 判断当前 agent 类型（dsh / claude-code / generic / chat-only）
2. 识别 OS（Windows / Linux / macOS）
3. 记录判断结果（将在验收报告中标注能力分级）

## 步骤 2：挂载 skill（完整模式）

读 `agents.json` 中对应 agent 的 `skill_dir`：

- dsh → `~/.dsh/skills/`；claude-code → `~/.claude/skills/`
- 把 `qalore/` 整个目录复制到 `{skill_dir}qalore/`
- generic / chat-only 模式：跳过本步（无 skill 机制，见步骤 3 降级说明）

## 步骤 3：生成配置

生成 `qalore-config.json`（路径见 `agents.json` 的 `config_path`）：

```json
{
  "_readme": "qalore 配置。由种子指令自动生成。",
  "practices_path": "{仓库绝对路径}/practices",
  "story_path": "{仓库绝对路径}/story",
  "audit_path": "{仓库绝对路径}/audit"
}
```

- `story_path` 若不存在：用 `story-template/` 初始化空骨架（场景 A）；或按 `manifest.story_source` 获取完整业务 story（场景 B）
- `audit_path` 若不存在：创建空目录 `audit/qalore-audit/`
- **降级模式（generic）**：无 skill 时，把 `practices/common/handbook.md` 的关键规范（story 维护约定 / 写入协议 / 依赖登记）作为后续任务 prompt 前缀注入，替代 skill 的 context 标记机制

## 步骤 4：探测工具

读 `practices/contracts.json` 的 `external_tools.tools`，逐一探测：

- `type=mcp` → 查可用 MCP 工具列表（playwright_mcp / figma_mcp / yunxiao_mcp）
- `type=cli` → 运行 probe（`which psql` / `python3 --version` / `lark-cli`）
- `type=skill` → 查 skill 列表（office_xlsx）

产出「工具就绪度报告」，标注每个工具 ✅已就绪 / ❌缺失。

## 步骤 5：安装缺失工具

- **CLI（lark-cli / psql / python3）**：按 `contracts.json` 的 `install_hint` 执行安装；无法自动安装 → 生成安装命令清单交给用户
- **MCP（Playwright / Figma / 云效）**：运行 `python3 practices/tools/gen-mcp-config.py` 生成目标 agent 的 MCP 配置（含传输方式 + 启动命令 + 凭证占位符），引导用户填入凭证
- 安装失败 → 标注「降级」，不阻断

## 步骤 6：获取 story 与 audit 数据

- **已内置（本包根目录已有 `story/` 与 `audit/`）**：直接使用，跳过 clone；步骤 3 生成的 config 路径已指向它们，无需额外操作
- **未内置（仅框架包）**：
  - audit 数据（必做）：按 `manifest.audit_source` 获取 audit 仓库到 `audit_path`（verify 第 11 项依赖 audit 依赖图对齐校验）
  - story：场景 A（仅框架）用 `story-template/`；场景 B（完整业务）按 `manifest.story_source` 引导 clone 到 `story_path`

## 步骤 7：验收

1. 运行 `python3 practices/tools/verify-contracts.py` → 18 项机器校验应全过
2. 路由冒烟：读 `story-template/` 中一个示例模块，产出 1 条测试用例，验证 skill→practices→story 路由通
3. 输出「移植验收报告」：

```
【qalore 移植验收报告】
agent 类型：{dsh / claude-code / generic / chat-only}
能力分级：{完整 / 降级 / 只读}
skill 挂载：{✅ 已挂载到 ~/.dsh/skills/qalore / ⏭ 跳过（无 skill 机制）}
配置生成：{✅ ~/.dsh/qalore-config.json}
机器校验：{18 项 ✅ / ❌（列出失败项）}
工具就绪：playwright {✅/❌} | figma {✅/❌} | 云效 {✅/❌} | lark-cli {✅/❌} | psql {✅/❌}
路由冒烟：{✅ 生成 1 条用例成功 / ❌}
待填凭证：{飞书 appSecret / 云效 token / figma token（列出未填项）}
```

> **幂等性**：本指令可重复执行（= 增量升级），重跑会重挂 skill + 版本比对 + 补齐缺失工具。
