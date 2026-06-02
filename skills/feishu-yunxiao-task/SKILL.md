---
name: feishu-yunxiao-task
description: 使用飞书官方 lark-cli/Feishu CLI 读取飞书 Wiki/云文档需求，按配置中的项目职责拆分任务，并在创建前输出三版方案等待确认；确认后通过云效 OpenAPI 创建云效任务/工作项，或按用户明确要求通过 lark-cli task 创建飞书任务。适用于用户给出飞书需求文档 URL、要求“创建云效任务”“根据需求拆任务”“按前端/后端项目职责拆分任务”“创建任务前给三版方案”“用云效 OpenAPI 建工作项”“用 lark-cli 读取需求/建飞书任务”等场景；支持全局配置项目列表、项目职责、需求关键词、仓库 URL 映射、云效迭代 URL、默认负责人和关注人。
---

# 飞书云效任务

## 需求驱动流程

用户给飞书需求文档 URL 时，按这个顺序做：

1. 读取需求文档：优先用 `lark-cli docs +fetch --as bot --api-version v2 --doc '<飞书 Wiki URL>'` 直接拉取 Wiki 背后的 docx 正文；失败时再用 `wiki +node-get` 或用户身份 `docs +fetch` 补查节点/权限。如果 CLI 权限不足，用已登录浏览器打开文档并提取标题、背景、涉及模块、仓库链接、验收标准和关键词。
2. 匹配云效项目：运行 `scripts/feishu_yunxiao_task.py detect-project --requirement-file <file>`，按 `requirement_keywords`、`repo_urls`、`repo_patterns`、`aliases`、项目名匹配。
3. 读取项目职责：从命中的 `projects[]` 读取 `delivery_domain`、`task_scope`、`task_split_guidance`、`exclude_task_keywords`。这些字段决定任务拆分边界；例如当前仓库是前端项目，就只生成前端相关任务。
4. 生成三版方案：在任何真实创建前，先输出 A/B/C 三版任务方案并停下等待用户确认。即使用户说“创建任务”，也先出方案，不直接创建。
5. 创建云效任务：用户明确确认某版后，优先通过云效 OpenAPI 创建云效任务/工作项；`lark-cli` 只用于读取飞书文档和创建飞书 Todo，不能创建云效任务。不要因为 `lark-cli task` 能创建飞书任务就把云效需求建到飞书 Todo。
6. 回传结果：说明需求文档、云效项目、迭代、创建的云效任务编号/ID/状态，以及是否使用了云效 OpenAPI。

如果用户明确要求创建飞书任务/Todo，仍然必须先出三版方案并等待确认；确认后才运行 `create-task` 或 `create-task-items --execute`。

## 任务方案确认门

在用户确认前，不要点击云效创建/保存按钮，不要调用云效创建接口，不要运行任何会新增云效工作项的命令，也不要运行任何会新增飞书任务的命令。

方案必须一次给三版：

- 方案 A：最小闭环。只创建完成需求必需的少量工作项，适合小改动或赶进度。
- 方案 B：标准拆分。按开发、联调、自测/测试、验收等常规环节拆分，作为默认推荐。
- 方案 C：细化稳妥。额外覆盖数据迁移、兼容、灰度、回归、监控或风险验证，适合影响面不确定的需求。

每版都要先应用项目职责过滤，再明确列出“我会创建哪些任务”。例如 `delivery_domain=frontend` 时，只创建前端页面、组件、路由、菜单权限、接口联调、导出/下载交互、字段展示、前端自测等任务；不要创建后端 API、数据库、定时任务、第三方回调、数据对账等后端任务，除非配置或用户明确说明当前项目负责这些内容。

每个任务包含：

- 标题
- 类型（需求/任务/缺陷/子任务，以云效页面可选项为准）
- 所属云效项目和迭代
- 关联需求文档 URL
- 关联或父级工作项（如果有）
- 任务范围
- 验收标准
- 建议负责人/关注人（不确定时写“待确认”）
- 创建目标（云效任务/飞书任务），默认是云效任务

云效任务创建时，任务描述只保留“任务范围”一段；验收标准只放在方案确认说明中，不写入云效任务描述。需求文档、项目、迭代、负责人和创建来源放在方案说明、命令参数或回传结果里，不写入云效任务描述。

输出三版后，必须停下来等用户回复。用户可以回复“选 A/B/C”“按 B 创建”“继续”“重新出三版”“把 B 的测试项拆细一点”等。当用户回复“继续”时，视为选择默认推荐方案 B，并表示同意按方案 B 继续创建；仍需先复述最终将创建的任务清单再执行。用户选择后，先复述最终将创建的任务清单；如果用户没有明确说“创建/确认/按这版执行”，且不是“继续”，继续等待确认。

## 项目职责拆分

命中项目后，先看 `projects[].delivery_domain`：

- `frontend`：只生成前端相关任务。优先拆页面入口、Vue 组件、列表/详情页字段、筛选、表格交互、导出/下载、菜单按钮权限、接口联调、前端状态与错误处理、自测验收。过滤后端 API、数据表、定时任务、消息回调、服务端对账、录音文件服务等任务。
- `backend`：只生成后端相关任务。优先拆接口、数据模型、权限校验、定时任务、回调、导出服务、日志和联调。
- `fullstack`：可以覆盖前后端，但仍按模块边界拆分，并标明前端/后端归属。
- 未配置时，不要猜项目职责；先根据仓库名、README、AGENTS 或用户说明判断，仍不确定就让用户确认。

任务标题要体现项目职责。例如前端项目中的标题应包含“前端”“页面”“列表”“详情”“菜单权限”“导出交互”等语义，而不是泛化的“API 对接”“通话对账任务”。

## 读取飞书需求

首选命令。读取飞书 Wiki 需求文档时先试这个；它通常比 `wiki +node-get` 更稳定，因为可以直接用 bot 身份读取 Wiki 背后的 docx 正文：

```bash
lark-cli docs +fetch --as bot --api-version v2 --doc '<飞书 Wiki URL>' --format json
```

从返回里提取正文内容：

```bash
lark-cli docs +fetch --as bot --api-version v2 --doc '<飞书 Wiki URL>' --format json --jq '.data.document.content'
```

备选命令：

```bash
lark-cli wiki +node-get --node-token '<飞书 Wiki URL>' --format json
lark-cli docs +fetch --api-version v2 --doc '<飞书 Wiki URL 或 docx token>' --format json
```

如果 `wiki +node-get` 返回缺少 `wiki:node:retrieve`、`wiki:node:read` 或 `wiki:node:read` 未启用，但首选 `docs +fetch --as bot` 已能拿到正文，可以继续使用正文做项目判断，不必卡在 Wiki 节点详情。

如果用户身份读取缺 `docx:document:readonly` 或其他读取权限，先检查：

```bash
lark-cli auth status
```

必要时按 CLI 提示补充文档读取 scope。不要把飞书 app secret、访问令牌或 Cookie 写入配置。

## 全局配置

默认配置文件：`~/.codex/feishu-yunxiao-task/config.json`。也可用 `FEISHU_YUNXIAO_TASK_CONFIG` 指定。

首次创建配置：

```bash
python3 /Users/lee/.codex/skills/feishu-yunxiao-task/scripts/feishu_yunxiao_task.py init-config \
  --yunxiao-project-list-url 'https://devops.aliyun.com/projex/project?_userId=69a2b4c2a407dfca290cd885&timestamp=1780366091877&mode=redirect&sign=f26b29bd7bff1b95c7db154271c17195#viewIdentifier=4e225857724c64c16037fe76'
```

详细字段见 `references/config.sample.json`。常用字段：

- `cli_command`: 飞书 CLI 命令；可填 `lark-cli` 或绝对路径。
- `task_identity`: 创建飞书任务时默认使用的身份，可填 `bot` 或 `user`；留空时使用 lark-cli 默认身份。
- `yunxiao_project_list_url`: 云效项目列表入口。
- `default_task_target`: 默认任务创建目标；本流程推荐 `yunxiao`，只有用户明确要求飞书 Todo 时才使用 `feishu`。
- `require_confirmation_before_create`: 是否创建前必须出三版方案并等待确认；应保持 `true`。
- `default_tasklist_id`: 默认飞书任务清单 ID 或 applink URL。
- `projects[].delivery_domain`: 项目职责，可填 `frontend`、`backend`、`fullstack`、`qa`、`product`。
- `projects[].task_scope`: 当前项目可创建任务的范围说明。
- `projects[].task_split_guidance`: 当前项目拆任务的偏好。
- `projects[].exclude_task_keywords`: 当前项目拆任务时要过滤的关键词。
- `projects[].requirement_keywords`: 从需求正文匹配项目的关键词。
- `projects[].local_paths`: 从当前工作目录匹配项目；例如 `/Users/lee/code/crm/crm_front` 固定映射到指定云效项目。
- `projects[].repo_urls` / `repo_patterns`: 从需求或当前仓库 remote 匹配项目；脚本会先找 `origin`，找不到时使用 `codeup` 或第一个 remote。
- `projects[].project_url`: 云效项目链接。
- `projects[].sprint_urls`: 常用云效迭代链接，通常指向 `#activeTab=Workitem`。
- `projects[].workitem_keywords`: 搜索迭代工作项时优先使用的关键词。
- `projects[].tasklist_id`: 该项目对应的飞书任务清单。

如果项目未命中，打开 `yunxiao_project_list_url`，按需求标题、模块名、仓库名或项目名查云效项目，然后把 `name`、`project_url`、`requirement_keywords`、`repo_urls`、`sprint_urls` 写回配置。

## 创建云效任务

先把飞书需求正文保存到临时文件，例如 `work/requirement.txt`，再匹配项目：

```bash
python3 /Users/lee/.codex/skills/feishu-yunxiao-task/scripts/feishu_yunxiao_task.py detect-project \
  --requirement-file work/requirement.txt
```

创建云效任务使用云效 OpenAPI，不使用 `lark-cli task`。`lark-cli` 只属于飞书开放平台，不能写入 `https://devops.aliyun.com/projex/.../task` 页面。

确认用户选择某一版方案后，优先使用脚本封装创建，不要临场手写 curl/Node：

```bash
python3 /Users/lee/.codex/skills/feishu-yunxiao-task/scripts/feishu_yunxiao_task.py create-yunxiao-workitems \
  --items-file work/yunxiao-items.json \
  --requirement-file work/requirement.txt \
  --requirement-url 'https://fz6gwn68j3.feishu.cn/wiki/BD3vw1GB8i3zLAk7L5IcfqeLnuf' \
  --related-workitem-id '<迭代中已有需求/工作项 ID>' \
  --require-related-workitem
```

确认预览无误后才追加 `--execute` 真正创建：

```bash
python3 /Users/lee/.codex/skills/feishu-yunxiao-task/scripts/feishu_yunxiao_task.py create-yunxiao-workitems \
  --items-file work/yunxiao-items.json \
  --requirement-file work/requirement.txt \
  --requirement-url 'https://fz6gwn68j3.feishu.cn/wiki/BD3vw1GB8i3zLAk7L5IcfqeLnuf' \
  --related-workitem-id '<迭代中已有需求/工作项 ID>' \
  --require-related-workitem \
  --execute
```

任务项 JSON 使用 `items` 或 `tasks` 数组。每个任务项只写标题、任务范围和验收标准；脚本会把云效 `description` 只生成为一段 Markdown：`任务范围`。不要把验收标准、需求链接、项目名、迭代、页脚、创建说明等元信息写进云效任务描述；这些信息通过方案说明、命令参数和创建结果追踪即可。

创建云效任务前，必须先确认要关联的“迭代中的项”（通常是迭代里已有的需求/主工作项）并拿到工作项 ID。所有拆出的任务都要在“关联项”中关联到该迭代工作项：统一关联时传 `--related-workitem-id`；不同任务关联不同项时，在每个 item 写 `related_workitem_id`。执行时保留 `--require-related-workitem`，缺少关联项 ID 就停止。

```json
{
  "requirement_title": "SJFCRM-169 指掌易通话记录接入",
  "requirement_url": "https://fz6gwn68j3.feishu.cn/wiki/BD3vw1GB8i3zLAk7L5IcfqeLnuf",
  "related_workitem_id": "<迭代中已有需求/工作项 ID>",
  "items": [
    {
      "key": "route-permission",
      "subject": "SJFCRM-169 前端开发：通话记录菜单、路由与按钮权限",
      "scope": [
        "新增通话记录列表菜单入口与前端路由。",
        "配置客户详情“详情通话记录”按钮权限。"
      ],
      "acceptance": [
        "有权限账号可进入通话记录列表菜单。",
        "客户详情通话记录页签入口受按钮权限控制。"
      ]
    }
  ]
}
```

脚本会从命中的 `projects[].yunxiao_defaults` 和 `projects[].project_id` 读取以下云效参数，也可通过命令行参数覆盖；只有配置缺失时才需要补查云效基础信息：

- 组织 ID：来自 `organization_id`；缺失时查 `GET /oapi/v1/platform/organizations` 后写回配置。
- 项目 ID：来自配置 `projects[].project_id`。
- 任务类型 ID：来自 `task_type_id`；缺失时查 `GET /oapi/v1/projex/organizations/{organizationId}/projects/{projectId}/workitemTypes?category=Task` 后写回配置。
- 负责人 ID：优先从已有同项目任务或用户配置中获取。
- 迭代 ID：优先来自 `default_sprint.id`。
- 创建后状态：默认更新为 `处理中`；可在 `projects[].yunxiao_defaults.post_create_status` 配置，或创建命令传 `--post-create-status '<状态名或状态ID>'` 覆盖；如需保留云效默认状态，传 `--skip-post-create-status`。

脚本实际调用的创建接口固定为：

```text
POST https://openapi-rdc.aliyuncs.com/oapi/v1/projex/organizations/<organizationId>/workitems
```

请求头：

```text
Content-Type: application/json
x-yunxiao-token: ${CODEUP_PERSONAL_ACCESS_TOKEN}
```

请求体模板：

```json
{
  "assignedTo": "<负责人云效用户 ID>",
  "description": "任务范围：\n- ...",
  "formatType": "MARKDOWN",
  "spaceId": "<云效项目 ID>",
  "sprint": "<迭代 ID>",
  "subject": "<任务标题>",
  "workitemTypeId": "<任务类型 ID>",
  "customFieldValues": {
    "priority": "<优先级选项 ID>"
  }
}
```

创建工作项成功后，脚本会继续为每个新任务创建“关联项”记录，关联到迭代中的已有项：

```text
POST https://openapi-rdc.aliyuncs.com/oapi/v1/projex/organizations/<organizationId>/workitems/<createdWorkitemId>/relationRecords
```

关联项请求体：

```json
{
  "relationType": "ASSOCIATED",
  "workitemId": "<迭代中已有需求/工作项 ID>"
}
```

`relationType` 默认使用 `ASSOCIATED`，表示普通关联项；不要用 `parentId` 替代，除非用户明确要创建父子关系。

创建和关联成功后，脚本会查询任务类型工作流状态，并把每个新建云效任务更新为 `处理中`：

```text
GET https://openapi-rdc.aliyuncs.com/oapi/v1/projex/organizations/<organizationId>/projects/<projectId>/workitemTypes/<taskTypeId>/workflows
PUT https://openapi-rdc.aliyuncs.com/oapi/v1/projex/organizations/<organizationId>/workitems/<createdWorkitemId>
```

状态更新请求体：

```json
{
  "status": "<处理中状态 ID>"
}
```

如果工作流中不存在目标状态，脚本必须停止并报告可用状态；不要在找不到状态时继续创建任务。

如果必须手动调接口，使用同一 payload 结构：

```bash
curl -sS \
  -H "Content-Type: application/json" \
  -H "x-yunxiao-token: ${CODEUP_PERSONAL_ACCESS_TOKEN}" \
  --data '<上方 CreateWorkitem JSON>' \
  "https://openapi-rdc.aliyuncs.com/oapi/v1/projex/organizations/<organizationId>/workitems"
```

不要把 `x-yunxiao-token` 打印到回复或日志摘要里。

## 创建飞书任务项

只有用户明确要求创建飞书任务/Todo 时才使用本节。创建前仍必须先出三版方案并等待确认。

创建单个飞书任务时，先生成命令预览：

```bash
python3 /Users/lee/.codex/skills/feishu-yunxiao-task/scripts/feishu_yunxiao_task.py create-task \
  --summary '跟进：工资项调整需求' \
  --description '从需求拆出的待办、验收口径和注意事项' \
  --requirement-url 'https://fz6gwn68j3.feishu.cn/wiki/BD3vw1GB8i3zLAk7L5IcfqeLnuf' \
  --requirement-title '需求文档标题' \
  --requirement-file work/requirement.txt \
  --sprint-url 'https://devops.aliyun.com/projex/project/4be8a2ddf3088379b16f53e760/sprint/959d1669597a8629c4577f1568#activeTab=Workitem&viewIdentifier=ead4d6570d314e123d03122ecd' \
  --workitem-title '云效工作项标题' \
  --workitem-url 'https://devops.aliyun.com/projex/project/.../workitem/...'
```

用户确认某一版飞书任务方案后，追加 `--execute` 真正创建：

```bash
python3 /Users/lee/.codex/skills/feishu-yunxiao-task/scripts/feishu_yunxiao_task.py create-task ... --execute
```

创建多个飞书任务项或父子任务时，写入 JSON 文件后使用 `create-task-items`。所有任务项都会通过 `lark-cli task +create` 创建；存在 `parent_key` 时，脚本会在创建后调用 `lark-cli task +set-ancestor` 建立父子关系：

```json
{
  "requirement_url": "https://fz6gwn68j3.feishu.cn/wiki/BD3vw1GB8i3zLAk7L5IcfqeLnuf",
  "requirement_title": "SJFCRM-169指掌易通话记录接入",
  "sprint_url": "https://devops.aliyun.com/projex/project/.../sprint/...",
  "items": [
    {
      "key": "parent",
      "summary": "SJFCRM-169 指掌易通话记录接入",
      "description": "父任务：承接需求文档，跟进前后端联调和验收。"
    },
    {
      "key": "customer-detail",
      "parent_key": "parent",
      "summary": "客户详情新增通话记录页签",
      "description": "展示客户维度通话记录，支持录音播放和下载。"
    }
  ]
}
```

```bash
python3 /Users/lee/.codex/skills/feishu-yunxiao-task/scripts/feishu_yunxiao_task.py create-task-items \
  --items-file work/task-items.json \
  --requirement-file work/requirement.txt \
  --requirement-url 'https://fz6gwn68j3.feishu.cn/wiki/BD3vw1GB8i3zLAk7L5IcfqeLnuf'
```

确认无误后追加 `--execute`：

```bash
python3 /Users/lee/.codex/skills/feishu-yunxiao-task/scripts/feishu_yunxiao_task.py create-task-items ... --execute
```

常用可选参数：

- `--repo-url`: 用户指定仓库地址，覆盖当前目录的 Git remote。
- `--items-file` / `--items-json`: `create-task-items` 的任务项清单；支持顶层 `items` 或 `tasks` 数组。
- `items[].key`: 任务项本地标识，用于 `parent_key` 引用和幂等 token。
- `items[].parent_key` / `items[].parent_guid`: 设置父任务；`parent_key` 引用同批次内已创建或将创建的任务项。
- `--tasklist-id`: 覆盖配置中的飞书任务清单。
- `--assignee`: 指定负责人 open_id，可多次传入。
- `--follower`: 指定关注人 open_id，可多次传入。
- `--due`: 截止日期，支持 `YYYY-MM-DD`、`+2d`、ISO 8601 或毫秒时间戳。
- `--as bot|user`: 覆盖配置里的 `task_identity`，指定通过机器人或用户身份调用 `lark-cli task`。
- `--extra-json`: 合并到飞书任务 API `--data` 的 JSON object，用于自定义字段等高级能力。
- `--allow-no-project`: 没匹配到云效项目时仍允许创建；需求驱动流程中默认不要使用。
- `--lark-dry-run`: 搭配 `--execute` 时调用飞书 CLI 的 `--dry-run`。

传入 `--requirement-url` 时，脚本会自动构造 `--data` payload，并设置：

- `origin.href.title`: 需求文档标题或“需求文档”。
- `origin.href.url`: 需求文档 URL。
- `origin.platform_i18n_name.zh_cn`: “飞书需求文档”。
- `client_token`: 自动生成幂等 token，`create-task-items` 会把 `items[].key` 纳入 token，避免同批次任务项互相冲突。

## 权限检查

创建任务前验证飞书 CLI：

```bash
lark-cli auth status
```

如果创建任务返回 `missing required scope(s): task:task:write`，先完成授权：

```bash
lark-cli auth login --scope "task:task:write"
```

云效页面需要登录态时，用已登录浏览器打开；不要把云效登录 Cookie 或带敏感凭证的接口响应保存进 skill。

## 判断准则

- 需求文档是入口，不要仅凭当前 Git 仓库创建任务，除非用户明确要求。
- 用户要求创建云效项目任务时，使用云效 OpenAPI；不要用 `lark-cli task` 创建飞书 Todo 来替代云效任务。
- 创建任何云效任务或飞书任务前，必须先输出三版方案并等待用户确认。
- 任务拆分必须遵守项目职责配置；当前仓库若配置为前端项目，只创建前端相关任务。
- 多个项目或多个工作项候选同样可信时，不要猜，列出候选让用户确认。
- 创建结果要包含任务标题、需求文档、云效项目/迭代、云效任务编号/ID/链接入口、OpenAPI 返回状态。
