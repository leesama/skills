---
name: weekly-report
description: 生成周报/月报的技能。适用于“生成周报/工作周报/月报”“从 Git 提交生成周报”“将周报 JSON 渲染为 Word”等需求；支持多仓库扫描、按周/月统计、输出 JSON 与 Word。
---

# 工作流

## 1) 确定范围与配置
- 统计范围：按周或按月
- 仓库范围：单仓库或多仓库
- 作者：可指定 user.name 或 user.email（支持逗号分隔或数组）
- 运行环境：需要 Node.js 18+

**全局配置文件**（用于覆盖脚本默认值）：
- 读取顺序：
  1. 环境变量 `WEEKLY_REPORT_CONFIG`
  2. 当前目录 `weekly.config.json`
  3. `~/.config/weekly-report/config.json`
  4. `~/.weekly-report.json`
- 字段示例见 `resources/config.example.json`
- 还可用 `WEEKLY_REPORT_REPO_ROOTS` 临时指定仓库根目录列表（用系统路径分隔符分隔）
- 首次运行若未找到配置，会自动生成默认配置到 `~/.config/weekly-report/config.json`（`repo_roots` 默认当前目录），并提示用户修改后再运行

## 2) 安装依赖（仅首次）

```bash
cd <skill_root>
npm install
```

## 3) 编译（生成 scripts）

```bash
npm run build
```

## 4) 生成原始 JSON
- 在任意目录执行以下命令（`<skill_root>` 为本 SKILL.md 所在目录）：

```bash
node <skill_root>/scripts/weekly.js
```

- 输出文件形如：`本周工作周报_YYYY-MM-DD.json`
- 输出目录：默认输出到桌面（`~/Desktop`），若不存在则输出到当前目录
- 不要覆盖或修改原始 JSON

## 5) 生成优化版 JSON（可选）
- 按需使用 `resources/prompt.txt` 对原始 JSON 进行周报化与中文化
- 输出新文件，例如：`本周工作周报_ai.json`

## 6) 渲染 Word

```bash
node <skill_root>/scripts/weekly_render.js -i <优化后的JSON> -o <输出文件>.docx
```
## 7) 回复结果
- 返回最终 Word 文件的完整路径
- 若仅输出 JSON，也返回 JSON 文件路径

# 注意事项
- 若未找到仓库，优先配置 `repo_paths` 或 `repo_roots`
- 如需多仓库统计，建议设置 `repo_roots` 并结合 `company_git_patterns` 过滤
