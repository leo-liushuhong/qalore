# qalore practices 操作规范

按需加载——仅在用户明确要求修改 practices 规范时才需要此文件。

---

## practices/index.json 维护规范

### changelog 写入规则

**新版本条目插入到 changelog 数组的最前面（倒序），最新的变更永远在第一位。**

```json
{
  "version": "vX",          ← 顶层 version 始终与 changelog[0].version 保持一致
  "changelog": [
    { "version": "vX", ... },   ← 最新版本，最前面
    { "version": "vX-1", ... },
    ...
    { "version": "v1", ... }    ← 最旧版本，最后面
  ]
}
```

每次更新必须同步执行以下三步，缺一不可：

| 步骤 | 操作 |
|------|------|
| 1 | 在 changelog 数组**头部**插入新条目（含 version、changed_files、summary） |
| 2 | 将顶层 `"version"` 字段更新为与新条目相同的版本号 |
| 3 | 若新增了规范文件类型，在 `common` 或 `tech_stacks` 下注册对应条目 |

### changelog 读取规则

增量读取时，从数组头部向下遍历，直到遇到已知版本号为止。

```
changelog[0] → changelog[1] → ... → changelog[N]（已知版本）
↑ 读这些条目的 changed_files，合并为本次需要更新的文件列表
```

若已知版本不在 changelog 中，退化为全量读取。

### 格式约束

- changelog 为 JSON 数组，条目之间必须有逗号，最后一条不加逗号
- 版本号格式：`{YYYY-MM-DD}-v{n}`，同日期内的 n 从 1 开始递增
- `changed_files` 使用相对于 `practices_path` 的路径

---

## practices 写入协议

### 写入前确认（强制，与 story 写入协议对等）

凡需要修改 `{practices_path}` 下任意文件时，**必须在写入前**展示待写入内容，等待人类确认：

```
【practices 写入确认】
| 文件 | 完整路径 | 操作 |
|------|---------|------|
| `{文件名}` | `{practices_path}/...` | {新建 / 新增章节 / 修改内容摘要} |
| `index.json` | `{practices_path}/` | 版本升至 {新版本号} |
```

等待人类响应：
- **同意** → 执行写入（主体文件 + index.json 并行，原子完成）
- **修正** → 调整后重新展示
- **拒绝** → 终止本次 practices 修改

### 写入后版本追踪（与写入操作并行，不得分步）

修改 practices 主体文件与更新 index.json 必须在同一执行步骤内并行完成，规则见「practices/index.json 维护规范」章节。
