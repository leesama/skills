# Feishu Docs Yunxiao Skill

English | [中文](README.md)

Read Feishu Wiki/docs first, then split requirements into Yunxiao task plans only when the user explicitly asks for task work.

## One-Line Pitch

Read the Feishu requirement clearly first; summarize when it is read-only, produce three plans when task splitting is requested, and create Yunxiao workitems only after confirmation.

## Simplest Guide

### 1) Install

If this skill (or all skills) is already installed globally, you can skip this step.

```bash
pnpx skills add leesama/skills --skill=feishu-docs-yunxiao
```

### 2) Use

For read-only Feishu docs, send one of these prompts to your LLM (for example, Codex or Claude):

- Read this Feishu doc: `<Feishu Wiki/doc URL>`
- Summarize this requirement: `<Feishu Wiki/doc URL>`
- Can you access this document: `<Feishu Wiki/doc URL>`

For task splitting or Yunxiao creation, make the task intent explicit:

- Split Yunxiao tasks from this Feishu requirement: `<Feishu Wiki/doc URL>`
- Produce three plans according to the frontend project role: `<Feishu Wiki/doc URL>`
- Confirm and create Yunxiao workitems from plan B

## What This Skill Does

- Uses `lark-cli docs +fetch` first to read Feishu Wiki/doc content.
- Separates read-only requests from task-creation requests: read-only requests do not match Yunxiao projects, produce three plans, or create tasks.
- Matches Yunxiao projects by config, repo URL, requirement keywords, and local paths.
- Splits tasks by project responsibility, such as frontend-only page, component, route, menu permission, API integration, and frontend QA tasks.
- Produces A/B/C plans before creation and waits for user confirmation.
- Creates Yunxiao workitems through the Yunxiao OpenAPI after confirmation; uses `lark-cli task` only when the user explicitly asks for Feishu Todo tasks.

## Typical Use Cases

- "Read this Feishu requirement doc"
- "Summarize this Feishu Wiki"
- "Split Yunxiao tasks from this Feishu doc"
- "Give me three plans before creating tasks"
- "Split tasks according to the current frontend/backend project responsibility"
- "After confirmation, create workitems through the Yunxiao OpenAPI"

## Process Boundaries

- Read/summarize/extract: only fetch the document and answer key points.
- Split/create tasks: read the document first, then match project and responsibility, then present three plans for confirmation.
- Yunxiao task creation: must happen only after the user confirms one plan.
- Feishu Todo creation: only when the user explicitly asks for Feishu tasks/Todos.
- Yunxiao task descriptions contain only task scope; acceptance criteria, requirement links, project, and sprint metadata stay in the plan or creation result.
- Yunxiao sprint selection is live: child tasks inherit the parent workitem sprint; standalone tasks use the single active project sprint. Do not store sprint IDs in local config.

## Config Resolution and Initialization

Default config file:

```text
~/.agents/feishu-docs-yunxiao/config.json
```

Legacy path and environment variables are also supported:

- `~/.agents/feishu-yunxiao-task/config.json`
- `FEISHU_DOCS_YUNXIAO_CONFIG`
- `FEISHU_YUNXIAO_TASK_CONFIG`

The default config path only reads the `.agents` path above or an explicit environment variable.

Initialize config:

```bash
python3 ~/.agents/skills/feishu-docs-yunxiao/scripts/feishu_yunxiao_task.py init-config \
  --yunxiao-project-list-url '<Yunxiao project list URL>'
```

See `references/config.sample.json` for a complete example.

## Config Fields

- `cli_command`: Feishu CLI command, such as `lark-cli` or an absolute path.
- `default_task_target`: Default task target; `yunxiao` is recommended.
- `require_confirmation_before_create`: Whether confirmation is required before creation; keep this `true`.
- `projects[].delivery_domain`: Project responsibility, such as `frontend`, `backend`, `fullstack`, `qa`, or `product`.
- `projects[].local_paths`: Match a Yunxiao project from local repository paths.
- `projects[].repo_urls` / `repo_patterns`: Match a Yunxiao project from Git remotes.
- `projects[].requirement_keywords`: Match a Yunxiao project from requirement text.
- `projects[].yunxiao_defaults`: Yunxiao organization, project, task type, token owner user, priority, and post-create status defaults. Do not store sprint IDs in local config.

## Common Commands

Fetch Feishu document content:

```bash
lark-cli docs +fetch --as bot --api-version v2 --doc '<Feishu Wiki/doc URL>' --format json
```

Detect the matching project from a requirement file:

```bash
python3 ~/.agents/skills/feishu-docs-yunxiao/scripts/feishu_yunxiao_task.py detect-project \
  --requirement-file work/requirement.txt
```

Preview Yunxiao workitem creation:

```bash
python3 ~/.agents/skills/feishu-docs-yunxiao/scripts/feishu_yunxiao_task.py create-yunxiao-workitems \
  --items-file work/yunxiao-items.json \
  --requirement-file work/requirement.txt \
  --requirement-url '<Feishu Wiki/doc URL>' \
  --parent-workitem-id '<Yunxiao parent workitem ID>' \
  --require-parent-workitem
```

Append `--execute` only after the preview is confirmed.

## Permissions and Secrets

- Feishu document reading and Feishu Todo creation rely on `lark-cli`; check with `lark-cli auth status`.
- Yunxiao OpenAPI calls rely on `CODEUP_PERSONAL_ACCESS_TOKEN`.
- Do not put Feishu app secrets, access tokens, cookies, or Yunxiao tokens in skill config, logs, summaries, or replies.

## Troubleshooting

- A read-only request produced task plans:
  - Say "read only", "summarize", or "extract"; the skill rules keep the flow out of task creation.
- No Yunxiao project matched:
  - Check `projects[].local_paths`, `repo_urls`, `repo_patterns`, and `requirement_keywords`.
- Yunxiao workitems cannot be created:
  - Check `CODEUP_PERSONAL_ACCESS_TOKEN`, `organization_id`, `project_id`, `task_type_id`, and token owner user ID. Sprint selection must be readable live from the Yunxiao parent workitem or the project's active sprint.
- Feishu permission is missing:
  - Run `lark-cli auth status` and follow the CLI prompt to add document-read or task-write scopes.
