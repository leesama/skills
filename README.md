# Skills 工具集

中文 | [English](README.en.md)

这是一个 skills 合集仓库，所有技能都放在 `skills/` 目录下，可通过 `pnpx` 直接安装全部或单个技能。

## 安装

安装全部技能：

```bash
pnpx skills add leesama/skills --skill='*'
```

安装单个技能（示例：`weekly-report`）：

```bash
pnpx skills add leesama/skills --skill=weekly-report
```

## 技能列表

- `weekly-report`：生成周报/月报，支持多仓库扫描、按周/月统计、输出 JSON 与 Word。

## 本地运行（以 `weekly-report` 为例）

进入技能目录并安装依赖：

```bash
cd skills/weekly-report
npm install
```

编译 TypeScript（生成 `scripts/`）：

```bash
npm run build
```

生成原始 JSON：

```bash
node scripts/weekly.js
```

默认输出到桌面（`~/Desktop`），若不存在则输出到当前目录。

将 JSON 内容中文化并润色为汇报表达（参考 `skills/weekly-report/resources/prompt.txt`），再渲染 Word：

```bash
node scripts/weekly_render.js -i <优化后的JSON> -o <输出文件>.docx
```

首次运行若未找到配置，会自动生成默认配置到 `~/.config/weekly-report/config.json`，并立即退出（不会继续执行统计）。如果输出包含 `CONFIG_INIT_REQUIRED`，需要先修改配置后再运行。

## 说明

- 各技能的详细使用方式见对应目录下的 `SKILL.md`。

## 配置文件生成逻辑

启动时按以下顺序查找配置（找到第一个就用）：

1. 环境变量 `WEEKLY_REPORT_CONFIG` 指定的文件
2. 当前目录 `weekly.config.json`
3. `~/.config/weekly-report/config.json`
4. `~/.weekly-report.json`

如果都没找到，会自动生成默认配置到 `~/.config/weekly-report/config.json`，输出 `CONFIG_INIT_REQUIRED` 并立即退出。  
如果设置了 `WEEKLY_REPORT_CONFIG` 但文件不存在，会在该路径生成默认配置并同样退出。

## 配置项说明

- `author`：作者过滤。可填姓名或邮箱，支持逗号分隔或数组。为空则使用 git 配置里的 `user.name`/`user.email`。
- `stat_mode`：`week` 或 `month`，按周/按月统计。
- `week_start`：周起始日（0=周一，1=周二，依此类推）。
- `week_offset`：向前偏移多少周（0=本周，1=上周）。
- `month_offset`：向前偏移多少月（0=本月，1=上月）。
- `repo_roots`：仓库扫描根目录数组（会向下递归搜索 `.git`）。
- `company_git_patterns`：只统计 remote URL 含这些关键词的仓库（为空则不过滤）。
- `repo_paths`：直接指定仓库路径列表（非空时优先使用它）。
- `max_scan_depth`：扫描 `repo_roots` 时最大递归深度。

## 项目名获取逻辑

生成报告时，项目名按以下顺序获取：

1. 仓库根目录的 `README.md` 第一行标题（去掉 `#`）
2. `package.json` 的 `name` 字段
3. 仓库目录名

## 工具原理

1. 配置加载与初始化  
   - 启动时按固定顺序寻找配置文件  
   - 若未找到则自动生成默认配置并输出 `CONFIG_INIT_REQUIRED`，立即退出
2. 仓库发现与筛选  
   - 根据 `repo_paths` 或 `repo_roots` 扫描 `.git` 仓库  
   - 可按 `company_git_patterns` 过滤远程地址
3. 提交采集  
   - 使用 `git log --all --since --until --no-merges` 拉取指定区间提交  
   - 支持按 `author` 过滤
4. 任务归并与结构化  
   - 清理常见前缀并做去重归并  
   - 统一任务状态为“已完成”
5. 输出结果  
   - 生成 JSON（默认输出到桌面）  
   - 根据 `resources/prompt.txt` 中文化润色生成最终 JSON  
   - 可渲染为 Word
