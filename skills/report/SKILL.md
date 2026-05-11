---
name: report
description: 将 Git 提交自动整理为日报/周报/月报，并输出“原始 JSON + 优化 JSON + Word”。适用于“生成日报/周报/月报”“从提交记录生成汇报材料”“把报告渲染成 Word”等需求。
---

# report 技能说明

## 这个技能是做什么的
- 从一个或多个 Git 仓库收集提交记录，自动生成日报/周报/月报。
- 产出三类文件：`原始 JSON`、`优化后 JSON`、`Word(.docx)`。
- 适合把开发提交快速整理成可汇报材料。

## 何时使用
- 用户说“生成日报/周报/月报”。
- 用户说“根据 Git 提交出报告/周报/月报”。
- 用户已有报告 JSON，需要渲染成 Word。

## 输入与前置条件
- Node.js 18+。
- 可访问的 Git 仓库（单仓库或多仓库）。
- 可选作者过滤：`author`（姓名/邮箱，支持逗号分隔或数组）。
- 当用户明确要求日报/周报/月报时，分别使用：
  - `日报` -> `stat_mode=day`
  - `周报` -> `stat_mode=week`
  - `月报` -> `stat_mode=month`

## 参数与口径说明
- `weekly.js` 支持参数：
  - `-m, --stat-mode <mode>`：统计模式。
- `stat_mode` 兼容输入：
  - 日：`day` / `daily` / `日` / `日报`
  - 周：`week` / `weekly` / `周` / `周报`
  - 月：`month` / `monthly` / `月` / `月报`
- 时间偏移口径：
  - `day_offset=0` 今天，`1` 昨天
  - `week_offset=0` 本周，`1` 上周
  - `month_offset=0` 本月，`1` 上月

## 标准执行流程（必须严格按顺序执行，不可跳步、不可追问）

### Step 1：生成原始 JSON
```bash
node <skill_root>/scripts/weekly.js --stat-mode day|week|month
```
- 也支持中文参数：`日报` / `周报` / `月报`。
- 输出文件示例：`本日工作日报_YYYY-MM-DD.json`、`本周工作周报_YYYY-MM-DD.json`。
- 默认输出到 `output_dir`（若未配置则回退到 `~/Desktop`，再回退到当前目录）。
- 原始 JSON 只读，不覆盖。
- 若提交数为 0：自动回退到上一个周期（`week_offset=1` / `day_offset=1` / `month_offset=1`），通过临时修改 config 中对应 offset 字段实现，生成后立即还原。若回退后仍为 0，则告知用户并终止流程。

### Step 2：生成优化后 JSON（必做，禁止跳过）
- 使用 `resources/prompt.txt` 中的规则对原始 JSON 进行中文化和汇报化处理。
- **合并规则**：
  - 同项目内，功能目标相同的连续提交必须合并为一条（如：同一功能的开+关、同一模块的多次样式调整）。
  - 代码级实现细节必须移除（如：组件名、变量名、函数名）。
  - 每条事项 1–2 句话，使用完成式中文表达。
  - 合并后 `statistics.total_tasks` 必须更新为合并后的实际条数。
- **输出**：另存为 `*_ai.json`（与原始 JSON 同目录）。
- **禁止**：不得在优化阶段与用户对话或请求确认。

### Step 3：渲染 Word（必做，禁止跳过）
```bash
node <skill_root>/scripts/weekly_render.js -i <优化后的JSON> -o <输出文件>.docx
```
- 若提示缺少依赖，先执行 `cd <skill_root> && npm install`，然后重新渲染。
- **禁止**：不得询问用户”是否需要渲染 Word”，直接执行。

### Step 4：输出任务清单（必做，禁止跳过）
```bash
node <skill_root>/scripts/weekly_list.js -i <优化后的JSON>
```
- 序号格式固定为 `1、2、3、...`。

### Step 5：向用户返回结果（必须严格使用下方模板，禁止增减内容）

**必须且只能**输出以下格式，不要添加任何额外说明、问候语、总结或注释：

```
Word：<.docx 文件绝对路径>
JSON：<_ai.json 文件绝对路径>

可复制任务清单：
```text
1、<日期> 【项目名】任务描述
2、<日期> 【项目名】任务描述
...
```
```

**格式硬约束**：
- 任务清单必须放在 ` ```text ` 代码块内，**禁止**使用 Markdown 有序列表（`1. 2. 3.`）。
- 序号必须使用中文顿号 `1、`，**禁止**使用西式点号 `1.`。
- 每行格式固定为：`序号、日期 【项目名】任务内容`。
- **禁止**在模板之外添加”报告已生成”等额外文案。
- **禁止**询问用户是否需要继续渲染 Word 或其他后续操作——全流程自动执行。

## 配置与异常处理
- 配置文件读取顺序：
  1. `REPORT_CONFIG` 指向的文件
  2. `WEEKLY_REPORT_CONFIG`（兼容）
  3. 当前目录 `report.config.json`
  4. 当前目录 `weekly.config.json`（兼容）
  5. `~/.config/report/config.json`
  6. `~/.config/weekly-report/config.json`（兼容）
  7. `~/.report.json`
  8. `~/.weekly-report.json`（兼容）
- 字段示例：`resources/config.example.json`。
- 可用 `REPORT_REPO_ROOTS` 临时指定仓库根目录（系统路径分隔符分隔）。
- 兼容环境变量：`WEEKLY_REPORT_REPO_ROOTS`。
- 可用 `REPORT_OUTPUT_DIR` 临时指定输出目录。
- 兼容环境变量：`WEEKLY_REPORT_OUTPUT_DIR`。
- 首次运行若未找到配置，会自动生成默认配置到 `~/.config/report/config.json` 并立即退出。
- 当输出包含 `CONFIG_INIT_REQUIRED` 时，必须停止后续流程，仅提示用户先完成配置再重跑。

## 关键配置项
- `stat_mode`: `day` / `week` / `month`
- `day_offset`: 0=今天，1=昨天
- `week_offset`: 0=本周，1=上周
- `month_offset`: 0=本月，1=上月
- `repo_roots`: 仓库根目录列表（递归扫描）
- `repo_paths`: 显式仓库路径（非空时优先）
- `company_git_patterns`: 按远程地址关键词过滤仓库
- `max_scan_depth`: 扫描深度（默认 `4`）
- `output_dir`: 报告默认输出目录
- `project_names`: 项目名映射，优先于 README/package.json/目录名；key 支持绝对仓库路径、仓库目录名或路径后缀，例如：
```json
{
  "project_names": {
    "/Users/example/workspace/alpha-web": "星河管理前端",
    "nebula-service": "星河业务后端"
  }
}
```

## 输出结构（用于优化与渲染）
- 原始 JSON 关键字段：
  - `report_type`: `日报` / `周报` / `月报`
  - `period.start_date` / `period.end_date`
  - `statistics.total_commits` / `statistics.total_tasks`
  - `projects[].project_name + tasks[]`
  - `tasks[]` 每项包含：`content` / `completion_standard` / `status` / `notes` / `project_name`
- `weekly_render.js` 最少依赖：
  - `report_type`
  - `period.start_date`, `period.end_date`
  - `statistics.total_commits`
  - `tasks[]`

## 常见失败处理
- `CONFIG_INIT_REQUIRED`：先补全配置再重跑，不继续后续流程。
- 扫描到 0 个仓库：优先检查 `repo_paths`、`repo_roots`、`company_git_patterns`。
- 需要只渲染 Word：可跳过统计，直接执行：
```bash
node <skill_root>/scripts/weekly_render.js -i <已有JSON> -o <输出文件>.docx
```

## 说明
- 若未找到仓库，优先检查 `repo_paths` 或 `repo_roots`。
- 对用户侧应以“描述需求 -> 自动生成报告”为主，不要求用户手动执行安装或构建命令。
