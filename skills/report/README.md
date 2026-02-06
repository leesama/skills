# 报告（report）技能

中文 | [English](README.en.md)

把 Git 提交自动整理成日报/周报/月报，并输出可汇报文件。

## 这个技能能做什么
- 扫描单仓库或多仓库提交记录。
- 按日/周/月汇总工作内容。
- 输出三类结果：
  - 原始 JSON（提交事实）
  - 优化后 JSON（中文化、汇报化）
  - Word（`.docx`，可直接发给上级/团队）

## 适用场景
- “帮我生成今天/本周/本月的工作报告”
- “根据 Git 提交生成周报/月报”
- “我有报告 JSON，帮我渲染成 Word”

## 3 分钟快速开始

1. 告诉助手你要的报告类型和范围：
- 例如：今天/本周/本月、哪些仓库、是否指定作者。

2. 助手自动生成原始 JSON：
- 从 Git 提交汇总出结构化报告数据。

3. 助手基于原始 JSON 生成优化后 JSON（使用 `resources/prompt.txt`）：
- 将 commit message 中文化并润色为汇报表达。
- 原始 JSON 不覆盖，优化内容另存为新文件（例如 `*_ai.json`）。

4. 助手渲染 Word：
- 生成 `.docx` 并返回可直接使用的文件路径。

## 结果文件
- 原始 JSON：如 `本周工作周报_YYYY-MM-DD.json`
- 优化后 JSON：如 `本周工作周报_ai.json`
- Word：你指定的 `.docx` 输出路径

## 参数与统计口径
- `weekly.js` 参数：
  - `-m, --stat-mode <mode>`：统计模式（可覆盖配置文件中的 `stat_mode`）。
- `stat_mode` 支持：
  - 日：`day` / `daily` / `日` / `日报`
  - 周：`week` / `weekly` / `周` / `周报`
  - 月：`month` / `monthly` / `月` / `月报`
- 偏移口径：
  - `day_offset`：0=今天，1=昨天
  - `week_offset`：0=本周，1=上周
  - `month_offset`：0=本月，1=上月

## 配置加载与初始化

启动时按以下顺序查找配置（找到第一个即使用）：

1. 环境变量 `REPORT_CONFIG` 指定的文件
2. 环境变量 `WEEKLY_REPORT_CONFIG` 指定的文件（兼容）
3. 当前目录 `report.config.json`
4. 当前目录 `weekly.config.json`（兼容）
5. `~/.config/report/config.json`
6. `~/.config/weekly-report/config.json`（兼容）
7. `~/.report.json`
8. `~/.weekly-report.json`（兼容）

如果都没找到，会自动生成默认配置到 `~/.config/report/config.json`，输出 `CONFIG_INIT_REQUIRED` 并立即退出。  
如果设置了 `REPORT_CONFIG` 但文件不存在，会在该路径生成默认配置并同样退出。  
可用环境变量 `REPORT_REPO_ROOTS` 临时指定仓库根目录列表（用系统路径分隔符分隔）。
兼容环境变量：`WEEKLY_REPORT_REPO_ROOTS`。

## 配置项说明

- `author`：作者过滤。可填姓名或邮箱，支持逗号分隔或数组。为空则使用 git 配置里的 `user.name`/`user.email`。
- `stat_mode`：`day` / `week` / `month`，按日/按周/按月统计。
- `week_start`：周起始日（0=周一，1=周二，依此类推）。
- `week_offset`：向前偏移多少周（0=本周，1=上周）。
- `day_offset`：向前偏移多少天（0=今天，1=昨天）。
- `month_offset`：向前偏移多少月（0=本月，1=上月）。
- `repo_roots`：仓库扫描根目录数组（会向下递归搜索 `.git`）。
- `company_git_patterns`：只统计 remote URL 含这些关键词的仓库（为空则不过滤）。
- `repo_paths`：直接指定仓库路径列表（非空时优先使用它）。
- `max_scan_depth`：扫描 `repo_roots` 时最大递归深度。

配置示例见 `resources/config.example.json`。

## 原始 JSON 结构（简版）
```json
{
  "report_type": "周报",
  "period": {
    "start_date": "2026-02-02",
    "end_date": "2026-02-08"
  },
  "statistics": {
    "total_commits": 12,
    "total_tasks": 8
  },
  "projects": [
    {
      "project_name": "项目A",
      "tasks": []
    }
  ],
  "tasks": [
    {
      "content": "【项目A】 完成xx能力优化",
      "completion_standard": "完成开发并提交",
      "status": "已完成",
      "notes": "",
      "project_name": "项目A"
    }
  ]
}
```

## 仅渲染 Word（跳过统计）
如果你已经有优化后的 JSON，可以直接渲染：
- 直接告诉助手“用这个 JSON 渲染 Word”。
- 助手会读取 JSON 并输出 `.docx` 文件路径。

`weekly_render.js` 支持：
- `-i, --input`：输入 JSON（必填）
- `-o, --output`：输出 docx（选填；不传则默认输出到桌面）

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

## 常见问题
- 看到 `CONFIG_INIT_REQUIRED`：
  - 这是首次初始化提示，不是脚本异常。先修改配置后重新执行。
- 扫描到 0 个仓库：
  - 先检查 `repo_paths` 是否为空，再检查 `repo_roots` 与 `company_git_patterns` 是否过严。
- 输出路径找不到：
  - 默认写到 `~/Desktop`，若桌面不存在则写当前执行目录。
