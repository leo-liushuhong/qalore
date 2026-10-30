# 外部工具依赖规范

qalore 依赖的外部工具（MCP / CLI / Python 包）统一在此登记，机器可判定契约见 `contracts.json#external_tools`。注意区分：本文件登记的是 **qalore 框架自身依赖的外部工具**；story 项目级依赖（输入/执行/不可测三类）登记在 `{story}/{项目}/dependencies.json`，规范见 `handbook.md`「依赖登记规范」章节。

---

## 五要素

每个外部工具声明五要素：

| 要素 | 说明 |
|------|------|
| `serves` | 该工具服务哪些断言/能力（ui/console/api/style/design/db） |
| `type` | 工具类型（mcp / cli / python 包） |
| `probe` | **可机器执行的探测方式**（必填，缺 probe = 契约不完整） |
| `min_version` | 最低版本（无约束为 null） |
| `upgrade` | 升级路径（无则 null） |

## 探测分层

- **脚本可探测**（cli/python 包：`which psql` / `python3 --version`）→ verify-contracts.py check #9 运行。
- **MCP 可探测**（Playwright/Figma 是否在 MCP 工具列表）→ 网关环境验证阶段查工具列表。

## 首次体检

网关每次任务环境验证阶段，遍历 `external_tools` 逐一探测，产出「依赖体检报告」：

```
【依赖体检报告】
✅ playwright_mcp（MCP 已接线）
✅ figma_mcp（MCP 已接线）
✅ psql（≥14）
✅ python3（≥3.8）
```

## 更新

外部工具版本升级遵循各工具自身路径（`upgrade` 字段）；升级后由 qa-audit 步骤18（机器探测）核对「声明 vs 实际」是否漂移。

## 版本契约

像 `practices_min_version` 一样，外部工具用 `min_version` 声明最低版本，不兼容时网关/审计告警。
