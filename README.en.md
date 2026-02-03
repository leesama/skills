# Skills Collection

English | [中文](README.md)

This is a skills collection repository. All skills live under `skills/`, and you can install all skills or a single skill via `pnpx`.

## Install

Install all skills:

```bash
pnpx skills add leesama/skills --skill='*'
```

Install a single skill (example: `report`):

```bash
pnpx skills add leesama/skills --skill=report
```

## Skills

- `report`: Generate daily/weekly/monthly reports, scan multiple repos, aggregate by day/week/month, output JSON and Word.

## Local Usage (report)

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

Polish the JSON for reporting (see `skills/report/resources/prompt.txt`), then render Word:

```bash
node scripts/weekly_render.js -i <optimized-json> -o <output>.docx
```

On first run, if no config is found, a default config will be generated at `~/.config/report/config.json` and the process will exit immediately. If the output includes `CONFIG_INIT_REQUIRED`, update the config and rerun.
Use `REPORT_REPO_ROOTS` to temporarily specify repo root directories (separated by your OS path delimiter).

## Notes

- See each skill's `SKILL.md` for details.

## Project Name Resolution

Report project names are resolved in this order:

1. First line title in `README.md` (with leading `#` removed)
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
