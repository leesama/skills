# Report Skill

English | [中文](README.md)

Generate daily/weekly/monthly reports, scan multiple repos, aggregate by day/week/month, output JSON and Word.

## Local Usage

Install dependencies:

```bash
cd skills/report
npm install
```

Build TypeScript (generates `scripts/`):

```bash
npm run build
```

Generate raw JSON:

```bash
node scripts/weekly.js
```

Default output is the Desktop (`~/Desktop`). If the Desktop does not exist, it falls back to the current directory.

Polish the JSON for reporting (see `resources/prompt.txt`), then render Word:

```bash
node scripts/weekly_render.js -i <optimized-json> -o <output>.docx
```

On first run, if no config is found, a default config will be generated at `~/.config/report/config.json` and the process will exit immediately. If the output includes `CONFIG_INIT_REQUIRED`, update the config and rerun.

## Config Resolution

Configuration is searched in this order:

1. File pointed by `REPORT_CONFIG`
2. `report.config.json` in current directory
3. `~/.config/report/config.json`
4. `~/.report.json`

If none is found, a default config is generated at `~/.config/report/config.json`, then the process exits with `CONFIG_INIT_REQUIRED`.  
If `REPORT_CONFIG` is set but the file does not exist, it will be generated at that path and the process exits as well.  
Use `REPORT_REPO_ROOTS` to temporarily specify repo roots (separated by your OS path delimiter).

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
