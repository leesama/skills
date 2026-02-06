# Report Skill

English | [中文](README.md)

Turn Git commits into daily/weekly/monthly reports with ready-to-share outputs.

## What This Skill Does
- Scans one or multiple Git repositories.
- Aggregates work by day/week/month.
- Produces three artifacts:
  - Raw JSON (facts from commits)
  - Optimized JSON (Chinese, reporting-friendly wording)
  - Word document (`.docx`) for direct sharing

## Typical Use Cases
- "Generate today's/this week's/this month's report"
- "Create a weekly/monthly report from Git commits"
- "Render an existing report JSON to Word"

## Quick Start (3 minutes)

1. Tell the assistant what report you want:
- For example: today/this week/this month, which repos, and optional author filter.

2. The assistant generates raw JSON automatically:
- It aggregates Git commits into structured report data.

3. The assistant produces optimized JSON from raw JSON (using `resources/prompt.txt`):
- Convert commit messages into polished, reporting-friendly Chinese.
- Keep raw JSON unchanged; save optimized JSON as a new file (for example `*_ai.json`).

4. The assistant renders Word:
- It generates a `.docx` file and returns the final file path.

## Output Files
- Raw JSON: for example `本周工作周报_YYYY-MM-DD.json`
- Optimized JSON: for example `本周工作周报_ai.json`
- Word: the `.docx` path you provide

## Parameters and Time Rules
- `weekly.js` parameters:
  - `-m, --stat-mode <mode>`: report granularity (overrides `stat_mode` in config).
- `stat_mode` values:
  - Daily: `day` / `daily` / `日` / `日报`
  - Weekly: `week` / `weekly` / `周` / `周报`
  - Monthly: `month` / `monthly` / `月` / `月报`
- Offset rules:
  - `day_offset`: 0=today, 1=yesterday
  - `week_offset`: 0=this week, 1=last week
  - `month_offset`: 0=this month, 1=last month

## Config Resolution and Initialization

Configuration is searched in this order:

1. File pointed by `REPORT_CONFIG`
2. File pointed by `WEEKLY_REPORT_CONFIG` (legacy)
3. `report.config.json` in current directory
4. `weekly.config.json` in current directory (legacy)
5. `~/.config/report/config.json`
6. `~/.config/weekly-report/config.json` (legacy)
7. `~/.report.json`
8. `~/.weekly-report.json` (legacy)

If none is found, a default config is generated at `~/.config/report/config.json`, then the process exits with `CONFIG_INIT_REQUIRED`.  
If `REPORT_CONFIG` is set but the file does not exist, it will be generated at that path and the process exits as well.  
Use `REPORT_REPO_ROOTS` to temporarily specify repo roots (separated by your OS path delimiter).
Legacy env is also supported: `WEEKLY_REPORT_REPO_ROOTS`.

## Config Fields

- `author`: Author filter. Name/email, comma-separated string, or array. If empty, uses git `user.name` / `user.email`.
- `stat_mode`: `day` / `week` / `month`.
- `week_start`: Week start day (0=Mon, 1=Tue, etc).
- `week_offset`: Weeks to offset (0=this week, 1=last week).
- `day_offset`: Days to offset (0=today, 1=yesterday).
- `month_offset`: Months to offset (0=this month, 1=last month).
- `repo_roots`: Root directories to scan for repos.
- `company_git_patterns`: Only include repos whose remote URL contains any of these strings.
- `repo_paths`: Explicit repo paths (takes precedence when non-empty).
- `max_scan_depth`: Max directory depth when scanning `repo_roots`.

See `resources/config.example.json` for a full example.

## Raw JSON Shape (Simplified)
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
      "project_name": "Project A",
      "tasks": []
    }
  ],
  "tasks": [
    {
      "content": "【Project A】 Completed xx optimization",
      "completion_standard": "Completed development and committed",
      "status": "已完成",
      "notes": "",
      "project_name": "Project A"
    }
  ]
}
```

## Render Word Only (Skip Collection)
If you already have optimized JSON, render directly:
- Tell the assistant: "Render this JSON to Word."
- The assistant will read the JSON and return the `.docx` path.

`weekly_render.js` parameters:
- `-i, --input`: source JSON (required)
- `-o, --output`: output docx (optional; Desktop by default)

## Project Name Resolution

Project name is resolved in this order:

1. First line title in `README.md` (leading `#` removed)
2. `package.json` field `name`
3. Repository folder name

## How It Works

1. Config load & init  
   - Looks for config in a fixed order  
   - If missing, generates a default config and exits with `CONFIG_INIT_REQUIRED`
2. Repo discovery & filtering  
   - Scans `.git` repositories from `repo_paths` or `repo_roots`  
   - Filters by `company_git_patterns`
3. Commit collection  
   - Uses `git log --all --since --until --no-merges`  
   - Supports `author` filtering
4. Task aggregation  
   - Cleans common prefixes and deduplicates  
   - Sets all task status to "Completed"
5. Output  
   - Generates JSON (defaults to Desktop)  
   - Polishes JSON via `resources/prompt.txt`  
   - Renders Word if needed

## Troubleshooting
- `CONFIG_INIT_REQUIRED` appears:
  - This is an initialization guard, not a runtime crash. Update config first, then rerun.
- Zero repos found:
  - Check `repo_paths`, then verify `repo_roots` and `company_git_patterns`.
- Cannot find output file:
  - Default output is `~/Desktop`; if unavailable, current working directory is used.
