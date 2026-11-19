# story-template（空骨架）

这是 qalore 的 story 空骨架模板，用于**场景 A（仅框架移植）**。

## 用途

- 种子指令（`qalore-bootstrap.md`）在对方机器上首次安装时，若选择「仅框架」，用本目录初始化 `story_path`。
- qalore 网关首次运行会引导对方建立自己的项目（新项目 → 提供一句话描述 → 创建 index.json）。

## 说明

- 本目录**不含任何业务内容**，符合 qalore 双螺旋分离原则（story = 业务知识库，框架分发物不带业务）。
- 场景 B（完整业务移植）时，用独立的私有 story 仓库（见 `qalore.manifest.json` 的 `story_source`），不用本骨架。
