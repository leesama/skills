# 飞书文档云效（feishu-docs-yunxiao）技能

中文 | [English](README.en.md)

读取飞书 Wiki/云文档，并在用户明确要求时，把需求按项目职责拆成云效任务方案。

## 一句话说明

先把飞书需求读明白；只读就只总结，要建任务才给三版方案，确认后再创建云效工作项。

## 最简单教程

### 1) 怎么装

如果你已经全局安装过该技能（或已安装全部 skills），可跳过这一步。

```bash
pnpx skills add leesama/skills --skill=feishu-docs-yunxiao
```

### 2) 怎么用

只读飞书文档时，直接对大模型（如 Codex、Claude 等）说：

- 读一下这个飞书文档：`<飞书 Wiki/云文档 URL>`
- 总结这个需求：`<飞书 Wiki/云文档 URL>`
- 这个文档能读到吗：`<飞书 Wiki/云文档 URL>`

需要拆任务或创建云效任务时，说清楚任务意图：

- 根据这个飞书需求拆云效任务：`<飞书 Wiki/云文档 URL>`
- 按前端项目职责拆三版方案：`<飞书 Wiki/云文档 URL>`
- 确认后按方案 B 创建云效工作项

## 这个技能能做什么

- 使用 `lark-cli docs +fetch` 优先读取飞书 Wiki/云文档正文。
- 区分只读场景和任务创建场景：只读时不匹配云效项目、不输出三版方案、不创建任务。
- 根据配置匹配云效项目、仓库地址、需求关键词和本地路径。
- 按项目职责拆任务，例如前端项目只生成页面、组件、路由、菜单权限、接口联调和前端自测任务。
- 创建前输出 A/B/C 三版方案，并等待用户确认。
- 确认后通过云效 OpenAPI 创建云效工作项；只有用户明确要求飞书 Todo 时才使用 `lark-cli task`。

## 适用场景

- “读一下这个飞书需求文档”
- “总结这个飞书 Wiki”
- “根据飞书文档拆云效任务”
- “创建任务前先给三版方案”
- “按当前前端/后端项目职责拆分任务”
- “确认后通过云效 OpenAPI 创建工作项”

## 流程边界

- 只读/总结/提取信息：只读取文档并回答要点，不进入云效任务流程。
- 拆任务/建任务：先读文档，再匹配项目和职责，最后输出三版方案等待确认。
- 创建云效任务：必须在用户确认某一版方案后执行。
- 创建飞书 Todo：只有用户明确要求“飞书任务/Todo”时才执行。
- 云效任务描述只写“任务范围”；验收标准、需求链接、项目和迭代放在方案说明或创建结果里。
- 云效迭代实时读取：有父工作项时继承父项迭代；无父项时读取项目唯一进行中迭代，不在本地配置迭代。

## 配置加载与初始化

默认配置文件：

```text
~/.agents/feishu-docs-yunxiao/config.json
```

兼容旧路径和旧环境变量：

- `~/.agents/feishu-yunxiao-task/config.json`
- `FEISHU_DOCS_YUNXIAO_CONFIG`
- `FEISHU_YUNXIAO_TASK_CONFIG`

默认配置只读取上方 `.agents` 路径或显式环境变量。

首次创建配置：

```bash
python3 ~/.agents/skills/feishu-docs-yunxiao/scripts/feishu_yunxiao_task.py init-config \
  --yunxiao-project-list-url '<云效项目列表 URL>'
```

完整配置示例见 `references/config.sample.json`。

## 常用配置项

- `cli_command`：飞书 CLI 命令，可填 `lark-cli` 或绝对路径。
- `default_task_target`：默认任务目标，推荐 `yunxiao`。
- `require_confirmation_before_create`：创建前是否必须确认，应保持 `true`。
- `projects[].delivery_domain`：项目职责，可填 `frontend`、`backend`、`fullstack`、`qa`、`product`。
- `projects[].local_paths`：按本地仓库路径匹配云效项目。
- `projects[].repo_urls` / `repo_patterns`：按 Git remote 匹配云效项目。
- `projects[].requirement_keywords`：按需求正文关键词匹配云效项目。
- `projects[].yunxiao_defaults`：云效组织、项目、任务类型、token 所属账号、优先级和创建后状态。迭代不要写入本地配置。

## 常用命令

读取飞书文档正文：

```bash
lark-cli docs +fetch --as bot --api-version v2 --doc '<飞书 Wiki/云文档 URL>' --format json
```

根据需求文件匹配项目：

```bash
python3 ~/.agents/skills/feishu-docs-yunxiao/scripts/feishu_yunxiao_task.py detect-project \
  --requirement-file work/requirement.txt
```

预览创建云效工作项：

```bash
python3 ~/.agents/skills/feishu-docs-yunxiao/scripts/feishu_yunxiao_task.py create-yunxiao-workitems \
  --items-file work/yunxiao-items.json \
  --requirement-file work/requirement.txt \
  --requirement-url '<飞书 Wiki/云文档 URL>' \
  --parent-workitem-id '<云效父工作项 ID>' \
  --require-parent-workitem
```

确认无误后，追加 `--execute` 才会真实创建。

## 权限与凭证

- 飞书读取和飞书 Todo 创建依赖 `lark-cli` 授权，可用 `lark-cli auth status` 检查。
- 云效 OpenAPI 依赖 `CODEUP_PERSONAL_ACCESS_TOKEN`。
- 不要把飞书 app secret、访问令牌、Cookie 或云效 token 写入技能配置、日志摘要或回复里。

## 常见问题

- 只想总结文档却输出了任务方案：
  - 使用时明确说“只读/总结/提取”，技能规则会阻止进入任务创建流程。
- 匹配不到云效项目：
  - 检查 `projects[].local_paths`、`repo_urls`、`repo_patterns`、`requirement_keywords` 是否覆盖当前仓库和需求关键词。
- 云效任务不能创建：
  - 检查 `CODEUP_PERSONAL_ACCESS_TOKEN`、`organization_id`、`project_id`、`task_type_id` 和 token 所属账号 ID；迭代需能从云效父项或项目进行中迭代实时读取。
- 缺少飞书权限：
  - 先运行 `lark-cli auth status`，按 CLI 提示补充文档读取或任务写入 scope。
