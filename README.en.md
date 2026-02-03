# Skills Collection

English | [中文](README.md)

This is a skills collection repository. All skills live under `skills/`, and you can install all skills or a single skill via `pnpx`.

## Install

Install all skills:

```bash
pnpx skills add <your-repo> --skill='*'
```

Install a single skill (example: `weekly-report`):

```bash
pnpx skills add <your-repo> --skill=weekly-report
```

## Skills

- `weekly-report`: Generate weekly/monthly reports, scan multiple repos, aggregate by week/month, output JSON and Word.

## Local Usage (weekly-report)

Install dependencies:

```bash
cd skills/weekly-report
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

Polish the JSON for reporting (see `skills/weekly-report/resources/prompt.txt`), then render Word:

```bash
node scripts/weekly_render.js -i <optimized-json> -o <output>.docx
```

On first run, if no config is found, a default config will be generated at `~/.config/weekly-report/config.json` and the process will exit immediately. If the output includes `CONFIG_INIT_REQUIRED`, update the config and rerun.

## Notes

- See each skill's `SKILL.md` for details.
