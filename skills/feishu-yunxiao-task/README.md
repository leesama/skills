# 飞书云效任务技能

中文 | [English](README.en.md)

读取飞书需求文档，按项目职责拆分任务方案，并在确认后创建云效工作项。

## 一句话说明

把“根据飞书需求创建云效任务”变成可控流程：先读需求，再匹配项目职责，先给三版方案，确认后才真正创建任务。

## 怎么安装

安装单个技能：

```bash
pnpx skills add leesama/skills --skill=feishu-yunxiao-task -g -y
```

安装仓库内全部技能：

```bash
pnpx skills add leesama/skills --skill='*' -g -y
```

## 什么时候用

当你希望助手处理下面这些事情时使用：

- 根据飞书 Wiki / 云文档需求创建云效任务
- 读取需求后按前端、后端、全栈等项目职责拆任务
- 创建前先输出 A / B / C 三版任务方案
- 确认后通过云效 OpenAPI 批量创建工作项
- 需要把新任务关联到迭代中的已有需求或主工作项
- 明确要求创建飞书 Todo，而不是云效任务

## 这个技能会做什么

- 使用 `lark-cli docs +fetch` 读取飞书需求正文。
- 根据全局配置匹配云效项目、迭代、负责人、优先级和项目职责。
- 按 `delivery_domain` 过滤任务边界，例如前端项目只创建页面、组件、路由、菜单权限、接口联调和前端自测任务。
- 在任何真实创建前输出三版方案：
  - 方案 A：最小闭环
  - 方案 B：标准拆分，默认推荐
  - 方案 C：细化稳妥
- 用户确认后，通过云效 OpenAPI 创建任务并关联到已有主工作项。
- 只有用户明确要求飞书 Todo 时，才使用 `lark-cli task` 创建飞书任务。

## 最简单用法

把飞书需求链接发给助手：

```text
创建任务，https://example.feishu.cn/wiki/xxxx
```

助手会先读取需求并输出三版方案。回复下面任一内容即可继续：

```text
选 B
继续
按 C 创建
```

其中 `继续` 等同于选择默认推荐的方案 B。创建前，助手仍会复述最终任务清单，并确认需要关联的云效主工作项。

## 配置文件

默认配置文件：

```text
~/.codex/feishu-yunxiao-task/config.json
```

可通过环境变量覆盖：

```bash
export FEISHU_YUNXIAO_TASK_CONFIG=/path/to/config.json
```

初始化配置：

```bash
python3 scripts/feishu_yunxiao_task.py init-config \
  --yunxiao-project-list-url 'https://devops.aliyun.com/projex/project/...'
```

配置示例见 [references/config.sample.json](references/config.sample.json)。

## 常用配置项

- `cli_command`：飞书 CLI 命令，例如 `lark-cli` 或绝对路径。
- `default_task_target`：默认任务目标，推荐 `yunxiao`。
- `require_confirmation_before_create`：创建前是否必须先确认方案，推荐保持 `true`。
- `projects[].delivery_domain`：项目职责，可填 `frontend`、`backend`、`fullstack`、`qa`、`product`。
- `projects[].task_scope`：当前项目可创建任务的范围。
- `projects[].task_split_guidance`：拆任务偏好。
- `projects[].exclude_task_keywords`：拆分时需要过滤的关键词。
- `projects[].requirement_keywords`：从需求正文匹配项目的关键词。
- `projects[].repo_urls` / `repo_patterns` / `local_paths`：按仓库匹配项目。
- `projects[].yunxiao_defaults`：云效组织、项目、迭代、任务类型、负责人、优先级等默认值。

## 需要的凭据

读取飞书文档需要 `lark-cli` 可用，并具有文档读取权限：

```bash
lark-cli auth status
```

创建云效工作项需要环境变量：

```bash
export CODEUP_PERSONAL_ACCESS_TOKEN='...'
```

不要把飞书 app secret、访问令牌、云效 token 或 Cookie 写进仓库。

## 常用命令

检测需求命中的项目：

```bash
python3 scripts/feishu_yunxiao_task.py detect-project \
  --requirement-file work/requirement.txt
```

预览云效任务创建请求：

```bash
python3 scripts/feishu_yunxiao_task.py create-yunxiao-workitems \
  --items-file work/yunxiao-items.json \
  --requirement-file work/requirement.txt \
  --requirement-url 'https://example.feishu.cn/wiki/xxxx' \
  --related-workitem-id '<主工作项ID>' \
  --require-related-workitem
```

确认无误后追加 `--execute` 才会真实创建：

```bash
python3 scripts/feishu_yunxiao_task.py create-yunxiao-workitems \
  --items-file work/yunxiao-items.json \
  --requirement-file work/requirement.txt \
  --requirement-url 'https://example.feishu.cn/wiki/xxxx' \
  --related-workitem-id '<主工作项ID>' \
  --require-related-workitem \
  --execute
```

## 安全约束

- 创建云效工作项或飞书 Todo 前必须先输出三版方案并等待确认。
- 云效任务描述只写“任务范围”，验收标准只放在方案确认说明中。
- 云效任务必须关联到迭代中的已有需求或主工作项，除非用户明确要求不关联。
- `lark-cli task` 只能创建飞书 Todo，不能替代云效工作项。
- 如果项目匹配有歧义，应先列出候选项目让用户确认。

详细执行规则见 [SKILL.md](SKILL.md)。
