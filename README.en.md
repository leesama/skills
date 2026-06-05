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

| Skill | Description |
| --- | --- |
| [feishu-docs-yunxiao](skills/feishu-docs-yunxiao) | Prefer reading Feishu Wiki/docs first; read-only requests only summarize or extract, while explicit task-splitting requests produce three Yunxiao plans by project responsibility and create workitems after confirmation. |
| [report](skills/report) | Generate daily/weekly/monthly reports, scan multiple repos, support custom project names, aggregate by day/week/month, output JSON and Word. |
| [trunk-based-development](skills/trunk-based-development) | Git collaboration guidance for Trunk-Based Development with short-lived branches, small batches, and fast return to trunk. |

## Notes

- Each skill directory contains its own `README.md` / `SKILL.md`. Click the skill name to view details.
