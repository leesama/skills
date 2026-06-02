# Feishu Yunxiao Task Skill

English | [中文](README.md)

Read Feishu requirement docs, split task plans by project responsibility, and create Yunxiao workitems after confirmation.

## One-Line Pitch

Turn "create Yunxiao tasks from this Feishu requirement" into a guarded workflow: read the requirement, match the project role, present three plans, and only create tasks after approval.

## Install

Install this skill:

```bash
pnpx skills add leesama/skills --skill=feishu-yunxiao-task -g -y
```

Install all skills in this repository:

```bash
pnpx skills add leesama/skills --skill='*' -g -y
```

## When to Use It

Use this skill when you want the assistant to:

- Create Yunxiao tasks from a Feishu Wiki or cloud document requirement
- Read a requirement and split work by frontend, backend, fullstack, QA, or product ownership
- Present A / B / C task plans before creating anything
- Batch-create Yunxiao workitems through the Yunxiao OpenAPI after confirmation
- Associate new tasks with an existing requirement or main workitem in a sprint
- Create Feishu Todo items only when explicitly requested

## What This Skill Does

- Reads Feishu requirement content with `lark-cli docs +fetch`.
- Matches a Yunxiao project, sprint, assignee, priority, and project responsibility from global config.
- Filters task boundaries by `delivery_domain`; for example, a frontend project only creates page, component, route, menu permission, API integration, and frontend self-test tasks.
- Presents three plans before any real creation:
  - Plan A: minimal closure
  - Plan B: standard split, recommended by default
  - Plan C: more detailed and safer
- Creates Yunxiao tasks through the Yunxiao OpenAPI after user approval.
- Uses `lark-cli task` only when the user explicitly asks for Feishu Todo items.

## Quick Start

Send a Feishu requirement URL to the assistant:

```text
Create tasks, https://example.feishu.cn/wiki/xxxx
```

The assistant will read the requirement and present three plans. Reply with one of:

```text
Choose B
Continue
Create plan C
```

`Continue` means selecting the default recommended Plan B. Before creating tasks, the assistant still repeats the final task list and confirms the Yunxiao main workitem to associate.

## Config File

Default config path:

```text
~/.codex/feishu-yunxiao-task/config.json
```

Override it with:

```bash
export FEISHU_YUNXIAO_TASK_CONFIG=/path/to/config.json
```

Initialize a config:

```bash
python3 scripts/feishu_yunxiao_task.py init-config \
  --yunxiao-project-list-url 'https://devops.aliyun.com/projex/project/...'
```

See [references/config.sample.json](references/config.sample.json) for a sample config.

## Common Config Fields

- `cli_command`: Feishu CLI command, such as `lark-cli` or an absolute path.
- `default_task_target`: default task target; `yunxiao` is recommended.
- `require_confirmation_before_create`: whether plans must be confirmed before creation; keep it `true`.
- `projects[].delivery_domain`: project responsibility, such as `frontend`, `backend`, `fullstack`, `qa`, or `product`.
- `projects[].task_scope`: work scope this project owns.
- `projects[].task_split_guidance`: preferred task splitting rules.
- `projects[].exclude_task_keywords`: keywords to filter out during splitting.
- `projects[].requirement_keywords`: keywords used to match requirement text.
- `projects[].repo_urls` / `repo_patterns` / `local_paths`: project matching by repository.
- `projects[].yunxiao_defaults`: Yunxiao organization, project, sprint, task type, assignee, and priority defaults.

## Required Credentials

Reading Feishu docs requires a working `lark-cli` identity with document-read permissions:

```bash
lark-cli auth status
```

Creating Yunxiao workitems requires:

```bash
export CODEUP_PERSONAL_ACCESS_TOKEN='...'
```

Do not commit Feishu app secrets, access tokens, Yunxiao tokens, or cookies.

## Common Commands

Detect the matched project:

```bash
python3 scripts/feishu_yunxiao_task.py detect-project \
  --requirement-file work/requirement.txt
```

Preview Yunxiao task creation:

```bash
python3 scripts/feishu_yunxiao_task.py create-yunxiao-workitems \
  --items-file work/yunxiao-items.json \
  --requirement-file work/requirement.txt \
  --requirement-url 'https://example.feishu.cn/wiki/xxxx' \
  --related-workitem-id '<main-workitem-id>' \
  --require-related-workitem
```

Append `--execute` only after confirmation:

```bash
python3 scripts/feishu_yunxiao_task.py create-yunxiao-workitems \
  --items-file work/yunxiao-items.json \
  --requirement-file work/requirement.txt \
  --requirement-url 'https://example.feishu.cn/wiki/xxxx' \
  --related-workitem-id '<main-workitem-id>' \
  --require-related-workitem \
  --execute
```

## Safety Rules

- Always present three plans and wait for confirmation before creating Yunxiao workitems or Feishu Todo items.
- Yunxiao task descriptions should contain only "task scope"; acceptance criteria stay in the plan summary.
- Yunxiao tasks should be associated with an existing sprint requirement or main workitem unless the user explicitly says otherwise.
- `lark-cli task` creates Feishu Todo items and must not be used as a substitute for Yunxiao workitems.
- If project matching is ambiguous, list candidates and ask the user to confirm.

See [SKILL.md](SKILL.md) for the detailed workflow.
