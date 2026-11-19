---
name: qa-bootstrap
description: >
  qalore 移植与维护。由 qalore 调用，不参与测试任务路由。
  首次移植由仓库根目录的 qalore-bootstrap.md 种子指令完成（不依赖本 capability）；
  本 capability 负责挂载后的维护：增量升级、缺失工具补装、凭证引导、版本三元组校验。
  不产生测试产物。
practices_min_version: "2026-11-19-v2"
---

# qa-bootstrap：qalore 移植与维护

## 职责边界

| 阶段 | 执行者 | 入口 |
|------|--------|------|
| 首次移植（自举） | 任意 agent | 仓库根 `qalore-bootstrap.md` 种子指令（自包含，不依赖 skill） |
| 挂载后维护 | 本 capability | 用户说「升级 qalore / 补装工具 / 检查移植状态」时触发 |

本 capability **不重复**种子指令的 7 步——只做挂载后的增量维护。

## 前置说明

| 变量 | 来源 | fallback |
|------|------|---------|
| `{practices_path}` | `~/.dsh/qalore-config.json` | 停止，提示先跑种子指令 |
| 仓库根路径 | 用户提供或 config 推断 | 停止，向用户确认 |

## 维护操作

### 1. 升级（幂等）

```
1. 读 {仓库根}/qalore.manifest.json 的 version_lock
2. 比对本地 practices/index.json 的 version + audit 依赖图对齐版本
3. manifest 版本 > 本地版本 → 升级：
   a. 重新挂载 skill（复制 qalore/ 到 skill_dir）
   b. 同步 practices + audit
   c. 运行 verify-contracts.py 校验（第 7 项 index 版本一致 + 第 11 项 audit 对齐）
   d. 补齐缺失工具（见下方「补装工具」）
4. manifest 版本 == 本地版本 → 报告「已是最新」，不动作
```

### 2. 补装工具

```
1. 读 practices/contracts.json 的 external_tools
2. 逐工具探测（复用网关依赖体检语义）
3. 缺失 → 按 install_hint 安装；MCP → 运行 practices/tools/gen-mcp-config.py 生成配置
4. 输出「工具就绪度报告」
```

### 3. 凭证引导

```
1. 读 manifest.requires_user_credentials
2. 逐项检查是否已填（MCP 配置 / lark-cli keychain）
3. 未填 → 输出「待填凭证清单」，引导用户填，不代填、不现编
```

### 4. 移植状态体检

```
输出：
【qalore 移植状态】
agent 类型 / 能力分级 / skill 版本 / practices 版本 / audit 对齐版本 /
工具就绪度 / 待填凭证 / 机器校验结果
```

## 约束

- **不现编凭证**：飞书 appSecret / 云效 token / figma token 一律由用户填，本 capability 只引导
- **不破坏业务**：升级只动 skill + practices + audit，不触碰 story 业务数据
- **版本三元组**：skill / practices / audit 对齐版本必须一致，不一致先修复再报告

## practices 文件

- `practices/contracts.json`（external_tools 探测 + install_hint）
- `practices/index.json`（版本比对）
- `practices/tools/gen-mcp-config.py`（MCP 配置生成）
