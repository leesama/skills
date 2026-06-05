#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


LEGACY_CONFIG_PATH = Path("~/.codex/feishu-yunxiao-task/config.json").expanduser()
CONFIG_ENV_VALUE = os.environ.get("FEISHU_DOCS_YUNXIAO_CONFIG") or os.environ.get(
    "FEISHU_YUNXIAO_TASK_CONFIG"
)
DEFAULT_CONFIG_PATH = Path(
    CONFIG_ENV_VALUE or "~/.codex/feishu-docs-yunxiao/config.json"
).expanduser()

if (
    CONFIG_ENV_VALUE is None
    and not DEFAULT_CONFIG_PATH.exists()
    and LEGACY_CONFIG_PATH.exists()
):
    DEFAULT_CONFIG_PATH = LEGACY_CONFIG_PATH

YUNXIAO_OPENAPI_BASE = "https://openapi-rdc.aliyuncs.com"


def print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def default_config(yunxiao_project_list_url="", cli_command="lark-cli", with_example=False):
    projects = []
    if with_example:
        projects.append(
            {
                "name": "示例云效项目",
                "project_id": "",
                "delivery_domain": "frontend",
                "task_scope": "当前项目职责范围说明，例如前端项目只承接页面、组件、路由、菜单权限、接口联调和前端自测任务。",
                "task_split_guidance": [
                    "按项目职责拆分任务，标题体现前端/后端/测试等职责。",
                    "当前项目是前端项目时，只生成前端相关任务。",
                ],
                "yunxiao_defaults": {
                    "organization_id": "<organization-id>",
                    "task_type_id": "<task-workitem-type-id>",
                    "task_type_name": "任务",
                    "default_assignee": {
                        "name": "负责人姓名",
                        "id": "<yunxiao-user-id>",
                    },
                    "default_sprint": {
                        "name": "迭代名",
                        "id": "<sprint-id>",
                    },
                    "default_priority": {
                        "name": "中",
                        "id": "<priority-option-id>",
                    },
                    "post_create_status": "处理中",
                },
                "exclude_task_keywords": [
                    "后端",
                    "数据库",
                    "定时任务",
                ],
                "project_url": "https://devops.aliyun.com/projex/project/example",
                "tasklist_id": "",
                "repo_urls": [
                    "git@example.com:group/example-repo.git",
                    "https://example.com/group/example-repo.git",
                ],
                "local_paths": [
                    "/Users/lee/code/example-repo"
                ],
                "repo_patterns": [
                    "example\\.com[:/]group/example-repo(?:\\.git)?$"
                ],
                "requirement_keywords": ["示例需求", "example-repo"],
                "sprint_urls": [
                    "https://devops.aliyun.com/projex/project/example/sprint/example#activeTab=Workitem"
                ],
                "workitem_keywords": ["示例需求"],
                "aliases": ["example-repo"],
            }
        )
    return {
        "version": 1,
        "cli_command": cli_command,
        "task_identity": "",
        "default_task_target": "yunxiao",
        "require_confirmation_before_create": True,
        "yunxiao_project_list_url": yunxiao_project_list_url,
        "default_tasklist_id": "",
        "default_assignee": "",
        "default_followers": [],
        "description_footer": "由 Codex 通过 feishu-docs-yunxiao 创建。",
        "projects": projects,
    }


def load_config(path):
    if not path.exists():
        raise FileNotFoundError(
            f"配置不存在：{path}。请先运行 init-config，或设置 FEISHU_DOCS_YUNXIAO_CONFIG。"
        )
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_config(path, config, force=False):
    if path.exists() and not force:
        raise FileExistsError(f"配置已存在：{path}。如需覆盖请加 --force。")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
        f.write("\n")


def git_remote_url(cwd):
    for remote in ["origin", "codeup"]:
        proc = subprocess.run(
            ["git", "-C", str(cwd), "remote", "get-url", remote],
            text=True,
            capture_output=True,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()

    remotes = subprocess.run(
        ["git", "-C", str(cwd), "remote"],
        text=True,
        capture_output=True,
    )
    if remotes.returncode != 0:
        return ""
    for remote in remotes.stdout.splitlines():
        remote = remote.strip()
        if not remote:
            continue
        proc = subprocess.run(
            ["git", "-C", str(cwd), "remote", "get-url", remote],
            text=True,
            capture_output=True,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    return ""


def strip_git_suffix(path):
    return path[:-4] if path.endswith(".git") else path


def normalize_repo_url(repo_url):
    repo_url = (repo_url or "").strip()
    if not repo_url:
        return ""

    scp_like = re.match(r"^(?:[^@]+@)?([^:]+):(.+)$", repo_url)
    if scp_like and "://" not in repo_url:
        host = scp_like.group(1).lower()
        path = strip_git_suffix(scp_like.group(2).strip("/").lower())
        return f"{host}/{path}"

    parsed = urlparse(repo_url)
    if parsed.scheme and parsed.netloc:
        host = parsed.hostname or parsed.netloc
        path = strip_git_suffix(parsed.path.strip("/").lower())
        return f"{host.lower()}/{path}"

    return strip_git_suffix(repo_url.strip("/").lower())


def repo_basename(normalized_repo):
    if not normalized_repo:
        return ""
    return normalized_repo.rstrip("/").split("/")[-1]


def project_label(project):
    return project.get("name") or project.get("project_id") or project.get("project_url") or "<unnamed>"


def compact_text(text):
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def normalize_local_path(path):
    if not path:
        return ""
    return str(Path(str(path)).expanduser().resolve(strict=False))


def is_same_or_child_path(cwd, configured_path):
    cwd_norm = normalize_local_path(cwd)
    configured_norm = normalize_local_path(configured_path)
    if not cwd_norm or not configured_norm:
        return False
    return cwd_norm == configured_norm or cwd_norm.startswith(configured_norm.rstrip("/") + "/")


def score_project_path(project, cwd):
    if not cwd:
        return 0, "no-cwd"
    for local_path in project.get("local_paths") or []:
        if is_same_or_child_path(cwd, local_path):
            return 110, "local_paths"
    return 0, "none"


def score_project(project, original_repo, normalized_repo):
    if not normalized_repo:
        return 0, "no-repo"

    repo_urls = project.get("repo_urls") or []
    normalized_known = [normalize_repo_url(url) for url in repo_urls if url]
    if normalized_repo in normalized_known:
        return 100, "repo_urls"

    for known in normalized_known:
        if known and (normalized_repo.endswith(known) or known.endswith(normalized_repo)):
            return 90, "repo_urls-suffix"

    for pattern in project.get("repo_patterns") or []:
        try:
            if re.search(pattern, original_repo) or re.search(pattern, normalized_repo):
                return 80, "repo_patterns"
        except re.error:
            continue

    base = repo_basename(normalized_repo)
    path_parts = set(normalized_repo.split("/"))
    for alias in project.get("aliases") or []:
        alias_norm = str(alias).lower()
        if alias_norm and (alias_norm == base or alias_norm in path_parts):
            return 50, "aliases"

    name = str(project.get("name") or "").lower()
    if name and (name == base or name in normalized_repo):
        return 30, "name"

    return 0, "none"


def score_project_text(project, requirement_text):
    text = compact_text(requirement_text)
    if not text:
        return 0, "no-text"

    for keyword in project.get("requirement_keywords") or []:
        keyword_text = compact_text(str(keyword))
        if keyword_text and keyword_text in text:
            return 75, "requirement_keywords"

    for alias in project.get("aliases") or []:
        alias_text = compact_text(str(alias))
        if alias_text and alias_text in text:
            return 55, "aliases"

    for repo_url in project.get("repo_urls") or []:
        normalized = normalize_repo_url(repo_url)
        base = repo_basename(normalized)
        if normalized and normalized in text:
            return 70, "repo_urls-in-text"
        if base and base in text:
            return 45, "repo-name-in-text"

    name = compact_text(str(project.get("name") or ""))
    if name and name in text:
        return 50, "name"

    project_id = compact_text(str(project.get("project_id") or ""))
    if project_id and project_id in text:
        return 50, "project_id"

    return 0, "none"


def detect_project(config, repo_url="", requirement_text="", cwd=""):
    normalized = normalize_repo_url(repo_url)
    scored = []
    for project in config.get("projects") or []:
        path_score, path_reason = score_project_path(project, cwd)
        repo_score, repo_reason = score_project(project, repo_url, normalized)
        text_score, text_reason = score_project_text(project, requirement_text)
        score, reason = max(
            [
                (path_score, path_reason),
                (repo_score, repo_reason),
                (text_score, text_reason),
            ],
            key=lambda item: item[0],
        )
        if score > 0:
            scored.append(
                {
                    "score": score,
                    "reason": reason,
                    "name": project_label(project),
                    "project": project,
                }
            )

    scored.sort(key=lambda item: item["score"], reverse=True)
    winner = scored[0] if scored else None
    ambiguous = False
    if len(scored) > 1 and scored[0]["score"] == scored[1]["score"]:
        ambiguous = True

    return {
        "repo_url": repo_url,
        "normalized_repo": normalized,
        "cwd": normalize_local_path(cwd),
        "has_requirement_text": bool(compact_text(requirement_text)),
        "project": None if ambiguous or not winner else winner["project"],
        "matched_by": None if ambiguous or not winner else winner["reason"],
        "ambiguous": ambiguous,
        "candidates": [
            {
                "name": item["name"],
                "score": item["score"],
                "reason": item["reason"],
                "project_url": item["project"].get("project_url", ""),
                "tasklist_id": item["project"].get("tasklist_id", ""),
                "local_paths": item["project"].get("local_paths", []),
                "sprint_urls": item["project"].get("sprint_urls", []),
            }
            for item in scored[:10]
        ],
    }


def list_from_config_or_args(config_value, arg_values):
    values = []
    if isinstance(config_value, str) and config_value:
        values.append(config_value)
    elif isinstance(config_value, list):
        values.extend([str(value) for value in config_value if value])
    values.extend(arg_values or [])
    return values


def compose_description(args, config, project, repo_url):
    chunks = []
    if args.description:
        chunks.append(args.description.strip())

    meta = []
    if repo_url:
        meta.append(f"仓库：{repo_url}")
    if project:
        project_name = project.get("name") or project.get("project_id") or ""
        project_url = project.get("project_url") or ""
        if project_name and project_url:
            meta.append(f"云效项目：{project_name} {project_url}")
        elif project_name:
            meta.append(f"云效项目：{project_name}")
        elif project_url:
            meta.append(f"云效项目：{project_url}")
    elif config.get("yunxiao_project_list_url"):
        meta.append(f"云效项目列表：{config['yunxiao_project_list_url']}")

    if meta:
        chunks.append("\n".join(meta))

    links = []
    if getattr(args, "requirement_url", ""):
        links.append(f"需求文档：{args.requirement_url}")
    if getattr(args, "sprint_url", ""):
        links.append(f"云效迭代：{args.sprint_url}")
    workitem_bits = []
    if getattr(args, "workitem_id", ""):
        workitem_bits.append(args.workitem_id)
    if getattr(args, "workitem_title", ""):
        workitem_bits.append(args.workitem_title)
    if getattr(args, "workitem_url", ""):
        workitem_bits.append(args.workitem_url)
    if workitem_bits:
        links.append(f"关联工作项：{' '.join(workitem_bits)}")
    if links:
        chunks.append("\n".join(links))

    footer = config.get("description_footer")
    if footer:
        chunks.append(str(footer))

    return "\n\n".join(chunks)


def selected_tasklist_id(args, config, project):
    return (
        args.tasklist_id
        or (project or {}).get("tasklist_id")
        or config.get("default_tasklist_id")
    )


def build_task_data_payload(args, config, project, repo_url):
    payload = {
        "summary": args.summary,
    }
    description = compose_description(args, config, project, repo_url)
    if description:
        payload["description"] = description

    if args.requirement_url:
        payload["origin"] = {
            "href": {
                "title": args.requirement_title or "需求文档",
                "url": args.requirement_url,
            },
            "platform_i18n_name": {
                "zh_cn": "飞书需求文档",
                "en_us": "Feishu requirement doc",
            },
        }

    members = []
    for assignee in list_from_config_or_args(config.get("default_assignee"), args.assignee):
        members.append({"id": assignee, "role": "assignee"})
    for follower in list_from_config_or_args(config.get("default_followers"), args.follower):
        members.append({"id": follower, "role": "follower"})
    if members:
        payload["members"] = members

    if args.extra_json:
        try:
            extra = json.loads(args.extra_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"--extra-json 不是合法 JSON：{exc}") from exc
        if not isinstance(extra, dict):
            raise ValueError("--extra-json 必须是 JSON object")
        payload.update(extra)

    idempotency_key = args.idempotency_key
    if not idempotency_key and not args.no_idempotency_key:
        key_source = "|".join(
            [
                args.summary,
                repo_url or "",
                args.requirement_url or "",
                args.workitem_url or args.workitem_id or args.workitem_title or "",
                (project or {}).get("project_url") or (project or {}).get("name") or "",
            ]
        )
        idempotency_key = "codex-" + hashlib.sha256(key_source.encode("utf-8")).hexdigest()[:24]
    if idempotency_key and not args.no_idempotency_key:
        payload["client_token"] = idempotency_key

    return payload


def shell_command_from_config(config):
    raw = os.environ.get("LARK_CLI") or config.get("cli_command") or "lark-cli"
    if isinstance(raw, list):
        return [str(part) for part in raw]
    return shlex.split(str(raw))


def selected_lark_identity(args, config):
    identity = getattr(args, "as_identity", "") or config.get("task_identity", "")
    identity = str(identity).strip()
    return identity if identity in ("bot", "user") else ""


def build_lark_command(args, config, project, repo_url):
    use_data_payload = bool(args.requirement_url or args.extra_json or args.use_data_payload)
    if use_data_payload:
        payload = build_task_data_payload(args, config, project, repo_url)
        cmd = shell_command_from_config(config) + [
            "task",
            "+create",
        ]
        identity = selected_lark_identity(args, config)
        if identity:
            cmd += ["--as", identity]
        cmd += [
            "--data",
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            "--format",
            args.format,
        ]

        tasklist_id = selected_tasklist_id(args, config, project)
        if tasklist_id:
            cmd += ["--tasklist-id", tasklist_id]
        if args.due:
            cmd += ["--due", args.due]
        if args.lark_dry_run:
            cmd.append("--dry-run")
        return cmd

    cmd = shell_command_from_config(config) + [
        "task",
        "+create",
    ]
    identity = selected_lark_identity(args, config)
    if identity:
        cmd += ["--as", identity]
    cmd += [
        "--summary",
        args.summary,
        "--format",
        args.format,
    ]

    tasklist_id = selected_tasklist_id(args, config, project)
    if tasklist_id:
        cmd += ["--tasklist-id", tasklist_id]

    description = compose_description(args, config, project, repo_url)
    if description:
        cmd += ["--description", description]

    for assignee in list_from_config_or_args(config.get("default_assignee"), args.assignee):
        cmd += ["--assignee", assignee]

    for follower in list_from_config_or_args(config.get("default_followers"), args.follower):
        cmd += ["--follower", follower]

    if args.due:
        cmd += ["--due", args.due]

    idempotency_key = args.idempotency_key
    if not idempotency_key and not args.no_idempotency_key:
        key_source = "|".join(
            [
                args.summary,
                repo_url or "",
                (project or {}).get("project_url") or (project or {}).get("name") or "",
            ]
        )
        idempotency_key = "codex-" + hashlib.sha256(key_source.encode("utf-8")).hexdigest()[:24]
    if idempotency_key:
        cmd += ["--idempotency-key", idempotency_key]

    if args.lark_dry_run:
        cmd.append("--dry-run")

    return cmd


def json_from_file_or_text(file_path, raw_text, default):
    if file_path:
        return json.loads(file_path.read_text(encoding="utf-8"))
    if raw_text:
        return json.loads(raw_text)
    return default


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if isinstance(value, str):
        return [value] if value else []
    return [str(value)]


def selected_item_value(item, spec, cli_args, name, default=""):
    if name in item:
        return item.get(name) or default
    if name in spec:
        return spec.get(name) or default
    return getattr(cli_args, name, default) or default


def selected_item_list(item, spec, cli_args, name):
    if name in item:
        return as_list(item.get(name))
    if name in spec:
        return as_list(spec.get(name))
    return as_list(getattr(cli_args, name, []))


def as_markdown_lines(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    return [str(value).strip()]


def format_yunxiao_section(title, value):
    lines = as_markdown_lines(value)
    if not lines:
        return ""
    if len(lines) == 1 and not lines[0].startswith(("-", "*", "1.")):
        return f"{title}：\n{lines[0]}"
    return f"{title}：\n" + "\n".join(
        line if line.startswith(("-", "*")) or re.match(r"^\d+\.", line) else f"- {line}"
        for line in lines
    )


def selected_yunxiao_item_value(item, spec, *names):
    for name in names:
        if name in item and item.get(name):
            return item.get(name)
    for name in names:
        if name in spec and spec.get(name):
            return spec.get(name)
    return ""


def build_yunxiao_description(item, spec, index):
    scope = selected_yunxiao_item_value(
        item,
        spec,
        "scope",
        "task_scope",
        "range",
        "任务范围",
    )
    if not scope:
        raise ValueError(f"云效任务项 #{index + 1} 缺少 scope/task_scope/任务范围。")
    return format_yunxiao_section("任务范围", scope)


def project_yunxiao_defaults(project):
    if not project:
        return {}
    defaults = project.get("yunxiao_defaults") or {}
    if not isinstance(defaults, dict):
        return {}
    return defaults


def nested_id(value):
    if isinstance(value, dict):
        return value.get("id") or value.get("value") or ""
    return value or ""


def selected_yunxiao_settings(args, project):
    defaults = project_yunxiao_defaults(project)
    project_id = args.project_id or (project or {}).get("project_id") or ""
    post_create_status = getattr(args, "post_create_status", None)
    if getattr(args, "skip_post_create_status", False):
        post_create_status = ""
    elif post_create_status is None:
        post_create_status = defaults.get("post_create_status", "处理中")
    settings = {
        "organization_id": args.organization_id or defaults.get("organization_id") or "",
        "project_id": project_id,
        "workitem_type_id": args.workitem_type_id or defaults.get("task_type_id") or "",
        "assignee": args.assignee or nested_id(defaults.get("default_assignee")) or "",
        "sprint": args.sprint_id or nested_id(defaults.get("default_sprint")) or "",
        "priority": args.priority_id or nested_id(defaults.get("default_priority")) or "",
        "post_create_status": post_create_status,
        "format_type": args.format_type,
        "api_base": args.api_base.rstrip("/"),
    }
    missing = [
        name
        for name in ("organization_id", "project_id", "workitem_type_id", "assignee")
        if not settings[name]
    ]
    if missing:
        raise ValueError(
            "缺少云效创建参数："
            + ", ".join(missing)
            + "。请在项目 yunxiao_defaults 中配置，或通过命令行参数传入。"
        )
    return settings


def make_yunxiao_payload(item, spec, settings, index):
    subject = item.get("subject") or item.get("summary") or item.get("title")
    if not subject:
        raise ValueError(f"云效任务项 #{index + 1} 缺少 subject/summary/title。")

    payload = {
        "assignedTo": item.get("assignee") or settings["assignee"],
        "description": build_yunxiao_description(item, spec, index),
        "formatType": item.get("format_type") or settings["format_type"],
        "spaceId": item.get("project_id") or settings["project_id"],
        "subject": subject,
        "workitemTypeId": item.get("workitem_type_id") or settings["workitem_type_id"],
    }
    sprint = item.get("sprint_id") or item.get("sprint") or settings.get("sprint")
    if sprint:
        payload["sprint"] = sprint
    priority = item.get("priority_id") or item.get("priority") or settings.get("priority")
    if priority:
        payload["customFieldValues"] = {"priority": priority}
    extra = item.get("extra_payload") or item.get("extra")
    if extra:
        if not isinstance(extra, dict):
            raise ValueError(f"云效任务项 #{index + 1} 的 extra_payload/extra 必须是 JSON object。")
        payload.update(extra)
    return payload


def as_id_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in re.split(r"[,，\s]+", value) if part.strip()]
    return [str(value).strip()]


def first_nonempty_mapping_value(mapping, names):
    if not isinstance(mapping, dict):
        return None
    for name in names:
        if name in mapping and mapping.get(name):
            return mapping.get(name)
    return None


def selected_relation_ids(item, spec, args):
    names = [
        "related_workitem_ids",
        "related_workitem_id",
        "relation_workitem_ids",
        "relation_workitem_id",
        "associated_workitem_ids",
        "associated_workitem_id",
        "iteration_workitem_ids",
        "iteration_workitem_id",
        "workitem_ids",
        "workitem_id",
        "关联项",
        "关联工作项",
        "迭代工作项",
    ]
    value = first_nonempty_mapping_value(item, names)
    if value is None:
        value = first_nonempty_mapping_value(spec, names)
    if value is None:
        value = args.related_workitem_id
    return as_id_list(value)


def make_relation_payload(related_workitem_id, args):
    payload = {
        "relationType": str(args.relation_type or "ASSOCIATED").upper(),
        "workitemId": related_workitem_id,
    }
    if args.operator_id:
        payload["operatorId"] = args.operator_id
    return payload


def yunxiao_request(method, url, token, data=None, timeout=30):
    headers = {
        "Content-Type": "application/json",
        "x-yunxiao-token": token,
    }
    body = None
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8")
            parsed = json.loads(text) if text else {}
            return response.status, parsed, text
    except HTTPError as exc:
        text = exc.read().decode("utf-8")
        try:
            parsed = json.loads(text) if text else {}
        except json.JSONDecodeError:
            parsed = {"raw": text}
        return exc.code, parsed, text
    except URLError as exc:
        raise ValueError(f"云效 OpenAPI 请求失败：{exc}") from exc


def yunxiao_workitem_endpoint(settings, workitem_id):
    return (
        f"{settings['api_base']}/oapi/v1/projex/organizations/"
        f"{settings['organization_id']}/workitems/{workitem_id}"
    )


def yunxiao_workflow_endpoint(settings):
    return (
        f"{settings['api_base']}/oapi/v1/projex/organizations/"
        f"{settings['organization_id']}/projects/{settings['project_id']}"
        f"/workitemTypes/{settings['workitem_type_id']}/workflows"
    )


def resolve_yunxiao_status_id(workflow, target_status):
    target = str(target_status or "").strip()
    if not target:
        return "", []
    statuses = workflow.get("statuses") if isinstance(workflow, dict) else []
    if not isinstance(statuses, list):
        statuses = []
    normalized_target = target.lower()
    available = []
    for status in statuses:
        if not isinstance(status, dict):
            continue
        values = [
            str(status.get("id") or "").strip(),
            str(status.get("name") or "").strip(),
            str(status.get("displayName") or "").strip(),
            str(status.get("nameEn") or "").strip(),
        ]
        available.append(
            {
                "id": status.get("id") or "",
                "name": status.get("name") or "",
                "displayName": status.get("displayName") or "",
                "nameEn": status.get("nameEn") or "",
            }
        )
        if any(value and value.lower() == normalized_target for value in values):
            return str(status.get("id") or target), available
    raise ValueError(
        f"未在云效工作流中找到状态：{target}。可用状态："
        + ", ".join(
            f"{item.get('displayName') or item.get('name')}({item.get('id')})"
            for item in available
            if item.get("id")
        )
    )


def fetch_yunxiao_status_id(settings, token, timeout):
    target_status = settings.get("post_create_status") or ""
    if not target_status:
        return "", {}, []
    endpoint = yunxiao_workflow_endpoint(settings)
    status, body, raw = yunxiao_request("GET", endpoint, token, timeout=timeout)
    if not 200 <= status < 300:
        raise ValueError(f"获取云效工作流状态失败：HTTP {status} {raw}")
    status_id, available = resolve_yunxiao_status_id(body, target_status)
    return status_id, body, available


def command_create_yunxiao_workitems(args):
    config = load_config(args.config)
    repo_url = args.repo_url or git_remote_url(args.cwd)
    requirement_text = args.requirement_text or ""
    if args.requirement_file:
        requirement_text = args.requirement_file.read_text(encoding="utf-8")
    detection = detect_project(config, repo_url, requirement_text, args.cwd)
    project = detection["project"]

    if args.project_name or args.project_url or args.project_id:
        project = {
            "name": args.project_name or args.project_url or args.project_id,
            "project_id": args.project_id,
            "project_url": args.project_url,
            "yunxiao_defaults": {
                "organization_id": args.organization_id,
                "task_type_id": args.workitem_type_id,
                "default_assignee": {"id": args.assignee},
                "default_sprint": {"id": args.sprint_id},
                "default_priority": {"id": args.priority_id},
            },
        }
        detection["project"] = project
        detection["matched_by"] = "manual"
        detection["ambiguous"] = False

    if detection["ambiguous"]:
        print_json(
            {
                "ok": False,
                "error": "多个云效项目同分命中，请指定 --project-name/--project-id/--project-url 或更新配置。",
                "detection": detection,
            }
        )
        return 2

    if not project and not args.allow_no_project:
        print_json(
            {
                "ok": False,
                "error": "未匹配到云效项目；请更新全局配置，或追加 --allow-no-project 并手动传入云效 ID。",
                "detection": detection,
            }
        )
        return 2

    spec = json_from_file_or_text(args.items_file, args.items_json, {})
    if isinstance(spec, list):
        spec = {"items": spec}
    items = spec.get("items") or spec.get("tasks") or []
    if not isinstance(items, list) or not items:
        print_json({"ok": False, "error": "云效任务 JSON 必须包含非空 items/tasks 数组。"})
        return 1

    settings = selected_yunxiao_settings(args, project)
    endpoint = (
        f"{settings['api_base']}/oapi/v1/projex/organizations/"
        f"{settings['organization_id']}/workitems"
    )
    relation_endpoint_template = (
        f"{settings['api_base']}/oapi/v1/projex/organizations/"
        f"{settings['organization_id']}/workitems/<created-workitem-id>/relationRecords"
    )
    status_endpoint_template = (
        f"{settings['api_base']}/oapi/v1/projex/organizations/"
        f"{settings['organization_id']}/workitems/<created-workitem-id>"
    )
    prepared = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            print_json({"ok": False, "error": f"云效任务项 #{index + 1} 必须是 JSON object。"})
            return 1
        payload = make_yunxiao_payload(item, spec, settings, index)
        relation_ids = selected_relation_ids(item, spec, args)
        if args.require_related_workitem and not relation_ids:
            print_json(
                {
                    "ok": False,
                    "error": f"云效任务项 #{index + 1} 缺少关联项 ID；请传 --related-workitem-id 或在 JSON 中写 related_workitem_id。",
                }
            )
            return 1
        prepared.append(
            {
                "key": str(item.get("key") or item.get("id") or index + 1),
                "subject": payload["subject"],
                "payload": payload,
                "relation_records": [
                    make_relation_payload(related_id, args)
                    for related_id in relation_ids
                ],
            }
        )

    result = {
        "ok": True,
        "execute": args.execute,
        "config_path": str(args.config),
        "repo_url": repo_url,
        "requirement_url": args.requirement_url or spec.get("requirement_url", ""),
        "requirement_title": args.requirement_title or spec.get("requirement_title", ""),
        "detection": detection,
        "endpoint": endpoint,
        "relation_endpoint_template": relation_endpoint_template,
        "workflow_endpoint": yunxiao_workflow_endpoint(settings),
        "status_endpoint_template": status_endpoint_template,
        "post_create_status": settings.get("post_create_status") or "",
        "items": prepared,
    }

    if not args.execute:
        result["note"] = "未调用云效 OpenAPI；确认无误后追加 --execute。"
        print_json(result)
        return 0

    token = os.environ.get(args.token_env)
    if not token:
        print_json(
            {
                "ok": False,
                "error": f"环境变量 {args.token_env} 未设置，无法调用云效 OpenAPI。",
                "token_env": args.token_env,
            }
        )
        return 1

    post_create_status_id = ""
    workflow_statuses = []
    if settings.get("post_create_status"):
        try:
            post_create_status_id, workflow, workflow_statuses = fetch_yunxiao_status_id(
                settings,
                token,
                args.timeout,
            )
        except ValueError as exc:
            result.update(
                {
                    "ok": False,
                    "error": str(exc),
                    "post_create_status": settings.get("post_create_status") or "",
                }
            )
            print_json(result)
            return 1
        result["post_create_status"] = {
            "target": settings.get("post_create_status") or "",
            "status_id": post_create_status_id,
            "available_statuses": workflow_statuses,
        }

    created = []
    relation_results = []
    status_results = []
    for task in prepared:
        status, body, raw = yunxiao_request(
            "POST",
            endpoint,
            token,
            data=task["payload"],
            timeout=args.timeout,
        )
        record = {
            "key": task["key"],
            "subject": task["subject"],
            "http_status": status,
            "ok": 200 <= status < 300,
            "id": body.get("id") if isinstance(body, dict) else "",
            "body": body,
        }
        created.append(record)
        if not record["ok"]:
            result.update(
                {
                    "ok": False,
                    "created": created,
                    "relation_results": relation_results,
                    "status_results": status_results,
                    "stopped_on": task["subject"],
                }
            )
            print_json(result)
            return 1
        if task["relation_records"]:
            created_id = record["id"]
            if not created_id:
                result.update(
                    {
                        "ok": False,
                        "created": created,
                        "relation_results": relation_results,
                        "status_results": status_results,
                        "error": f"云效任务 {task['subject']} 创建成功但响应缺少 id，无法创建关联项。",
                    }
                )
                print_json(result)
                return 1
            relation_endpoint = (
                f"{settings['api_base']}/oapi/v1/projex/organizations/"
                f"{settings['organization_id']}/workitems/{created_id}/relationRecords"
            )
            for relation_payload in task["relation_records"]:
                rel_status, rel_body, rel_raw = yunxiao_request(
                    "POST",
                    relation_endpoint,
                    token,
                    data=relation_payload,
                    timeout=args.timeout,
                )
                relation_record = {
                    "key": task["key"],
                    "subject": task["subject"],
                    "created_workitem_id": created_id,
                    "related_workitem_id": relation_payload.get("workitemId", ""),
                    "relation_type": relation_payload.get("relationType", ""),
                    "http_status": rel_status,
                    "ok": 200 <= rel_status < 300,
                    "id": rel_body.get("id") if isinstance(rel_body, dict) else "",
                    "body": rel_body,
                }
                relation_results.append(relation_record)
                if not relation_record["ok"]:
                    result.update(
                        {
                            "ok": False,
                            "created": created,
                            "relation_results": relation_results,
                            "status_results": status_results,
                            "stopped_on": task["subject"],
                            "error": "云效任务已创建，但创建关联项失败。",
                        }
                    )
                    print_json(result)
                    return 1
        if post_create_status_id:
            created_id = record["id"]
            if not created_id:
                result.update(
                    {
                        "ok": False,
                        "created": created,
                        "relation_results": relation_results,
                        "status_results": status_results,
                        "error": f"云效任务 {task['subject']} 创建成功但响应缺少 id，无法更新状态。",
                    }
                )
                print_json(result)
                return 1
            status_payload = {"status": post_create_status_id}
            if args.operator_id:
                status_payload["operatorId"] = args.operator_id
            status_endpoint = yunxiao_workitem_endpoint(settings, created_id)
            update_status, update_body, update_raw = yunxiao_request(
                "PUT",
                status_endpoint,
                token,
                data=status_payload,
                timeout=args.timeout,
            )
            status_record = {
                "key": task["key"],
                "subject": task["subject"],
                "created_workitem_id": created_id,
                "target_status": settings.get("post_create_status") or "",
                "target_status_id": post_create_status_id,
                "http_status": update_status,
                "ok": 200 <= update_status < 300,
                "body": update_body,
            }
            status_results.append(status_record)
            if not status_record["ok"]:
                result.update(
                    {
                        "ok": False,
                        "created": created,
                        "relation_results": relation_results,
                        "status_results": status_results,
                        "stopped_on": task["subject"],
                        "error": "云效任务已创建，但更新创建后状态失败。",
                    }
                )
                print_json(result)
                return 1

    result.update(
        {
            "ok": True,
            "created": created,
            "relation_results": relation_results,
            "status_results": status_results,
        }
    )
    print_json(result)
    return 0


def make_item_args(base_args, item, spec, index):
    summary = item.get("summary") or item.get("title")
    if not summary:
        raise ValueError(f"任务项 #{index + 1} 缺少 summary/title。")

    key = item.get("key") or item.get("id") or str(index + 1)
    extra_json = item.get("extra_json", item.get("extra"))
    if isinstance(extra_json, dict):
        extra_json = json.dumps(extra_json, ensure_ascii=False)
    elif extra_json is None:
        extra_json = selected_item_value(item, spec, base_args, "extra_json", "")
    if isinstance(extra_json, dict):
        extra_json = json.dumps(extra_json, ensure_ascii=False)

    idempotency_key = item.get("idempotency_key") or ""
    if not idempotency_key and not base_args.no_idempotency_key:
        key_source = "|".join(
            [
                str(key),
                summary,
                selected_item_value(item, spec, base_args, "requirement_url", ""),
                selected_item_value(item, spec, base_args, "workitem_url", ""),
                selected_item_value(item, spec, base_args, "workitem_title", ""),
            ]
        )
        idempotency_key = "codex-" + hashlib.sha256(key_source.encode("utf-8")).hexdigest()[:24]

    return SimpleNamespace(
        summary=summary,
        description=item.get("description") or selected_item_value(item, spec, base_args, "description", ""),
        requirement_url=selected_item_value(item, spec, base_args, "requirement_url", ""),
        requirement_title=selected_item_value(item, spec, base_args, "requirement_title", ""),
        project_name=selected_item_value(item, spec, base_args, "project_name", ""),
        project_url=selected_item_value(item, spec, base_args, "project_url", ""),
        sprint_url=selected_item_value(item, spec, base_args, "sprint_url", ""),
        workitem_id=selected_item_value(item, spec, base_args, "workitem_id", ""),
        workitem_title=selected_item_value(item, spec, base_args, "workitem_title", ""),
        workitem_url=selected_item_value(item, spec, base_args, "workitem_url", ""),
        tasklist_id=selected_item_value(item, spec, base_args, "tasklist_id", ""),
        assignee=selected_item_list(item, spec, base_args, "assignee"),
        follower=selected_item_list(item, spec, base_args, "follower"),
        due=item.get("due") or selected_item_value(item, spec, base_args, "due", ""),
        format=base_args.format,
        as_identity=item.get("as") or item.get("as_identity") or spec.get("as") or spec.get("as_identity") or base_args.as_identity,
        idempotency_key=idempotency_key,
        no_idempotency_key=base_args.no_idempotency_key,
        extra_json=extra_json or "",
        use_data_payload=True,
        lark_dry_run=base_args.lark_dry_run,
    )


def extract_task_guid(parsed):
    if isinstance(parsed, dict):
        for key in ("task", "subtask", "data", "result"):
            value = parsed.get(key)
            guid = extract_task_guid(value)
            if guid:
                return guid
        for key in ("guid", "task_guid", "task_id"):
            value = parsed.get(key)
            if isinstance(value, str) and value:
                return value
        for value in parsed.values():
            guid = extract_task_guid(value)
            if guid:
                return guid
    if isinstance(parsed, list):
        for value in parsed:
            guid = extract_task_guid(value)
            if guid:
                return guid
    return ""


def extract_task_url(parsed):
    if isinstance(parsed, dict):
        value = parsed.get("url")
        if isinstance(value, str) and value.startswith("http"):
            return value
        for value in parsed.values():
            url = extract_task_url(value)
            if url:
                return url
    if isinstance(parsed, list):
        for value in parsed:
            url = extract_task_url(value)
            if url:
                return url
    return ""


def parse_lark_stdout(stdout):
    text = (stdout or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def build_set_ancestor_command(args, config, child_guid, parent_guid):
    cmd = shell_command_from_config(config) + [
        "task",
        "+set-ancestor",
    ]
    identity = selected_lark_identity(args, config)
    if identity:
        cmd += ["--as", identity]
    cmd += [
        "--task-id",
        child_guid,
        "--ancestor-id",
        parent_guid,
        "--format",
        args.format,
    ]
    if args.lark_dry_run:
        cmd.append("--dry-run")
    return cmd


def command_create_task_items(args):
    config = load_config(args.config)
    repo_url = args.repo_url or git_remote_url(args.cwd)
    requirement_text = args.requirement_text or ""
    if args.requirement_file:
        requirement_text = args.requirement_file.read_text(encoding="utf-8")
    detection = detect_project(config, repo_url, requirement_text, args.cwd)
    project = detection["project"]

    if args.project_name or args.project_url:
        project = {
            "name": args.project_name or args.project_url,
            "project_url": args.project_url,
            "tasklist_id": args.tasklist_id or "",
        }
        detection["project"] = project
        detection["matched_by"] = "manual"
        detection["ambiguous"] = False

    if detection["ambiguous"]:
        print_json(
            {
                "ok": False,
                "error": "多个云效项目同分命中，请指定 --project-name/--project-url 或更新配置。",
                "detection": detection,
            }
        )
        return 2

    if not project and not args.allow_no_project:
        print_json(
            {
                "ok": False,
                "error": "未匹配到云效项目；请更新全局配置，或追加 --allow-no-project。",
                "detection": detection,
            }
        )
        return 2

    spec = json_from_file_or_text(args.items_file, args.items_json, {})
    if isinstance(spec, list):
        spec = {"items": spec}
    items = spec.get("items") or spec.get("tasks") or []
    if not isinstance(items, list) or not items:
        print_json({"ok": False, "error": "任务项 JSON 必须包含非空 items/tasks 数组。"})
        return 1

    prepared = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            print_json({"ok": False, "error": f"任务项 #{index + 1} 必须是 JSON object。"})
            return 1
        item_args = make_item_args(args, item, spec, index)
        command = build_lark_command(item_args, config, project, repo_url)
        prepared.append(
            {
                "key": str(item.get("key") or item.get("id") or index + 1),
                "summary": item_args.summary,
                "parent_key": item.get("parent_key") or item.get("parent"),
                "parent_guid": item.get("parent_guid") or "",
                "command": command,
                "shell_command": shlex.join(command),
            }
        )

    relation_previews = []
    for task in prepared:
        parent_key = task.get("parent_key")
        parent_guid = task.get("parent_guid")
        if parent_key or parent_guid:
            relation_previews.append(
                {
                    "child_key": task["key"],
                    "parent_key": parent_key or "",
                    "parent_guid": parent_guid or "",
                    "shell_command": " ".join(
                        [
                            shlex.quote(part)
                            for part in build_set_ancestor_command(
                                args,
                                config,
                                f"<task:{task['key']}.guid>",
                                parent_guid or f"<task:{parent_key}.guid>",
                            )
                        ]
                    ),
                }
            )

    payload = {
        "ok": True,
        "execute": args.execute,
        "config_path": str(args.config),
        "repo_url": repo_url,
        "detection": detection,
        "commands": prepared,
        "set_ancestor_commands": relation_previews,
    }

    if not args.execute:
        payload["note"] = "未执行飞书 CLI；确认无误后追加 --execute。"
        print_json(payload)
        return 0

    created_by_key = {}
    results = []
    for task in prepared:
        proc = subprocess.run(task["command"], text=True, capture_output=True)
        parsed = parse_lark_stdout(proc.stdout)
        guid = extract_task_guid(parsed) if parsed else ""
        url = extract_task_url(parsed) if parsed else ""
        if guid:
            created_by_key[task["key"]] = guid
        results.append(
            {
                "key": task["key"],
                "summary": task["summary"],
                "returncode": proc.returncode,
                "guid": guid,
                "url": url,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }
        )
        if proc.returncode != 0:
            payload.update({"ok": False, "results": results})
            print_json(payload)
            return proc.returncode

    relation_results = []
    if not args.lark_dry_run:
        for task in prepared:
            parent_key = task.get("parent_key")
            parent_guid = task.get("parent_guid")
            if not parent_key and not parent_guid:
                continue
            child_guid = created_by_key.get(task["key"])
            parent_guid = parent_guid or created_by_key.get(str(parent_key))
            if not child_guid or not parent_guid:
                payload.update(
                    {
                        "ok": False,
                        "results": results,
                        "relation_results": relation_results,
                        "error": f"无法设置父子任务关系：child={task['key']} parent={parent_key or parent_guid} 缺少 guid。",
                    }
                )
                print_json(payload)
                return 1
            command = build_set_ancestor_command(args, config, child_guid, parent_guid)
            proc = subprocess.run(command, text=True, capture_output=True)
            relation_results.append(
                {
                    "child_key": task["key"],
                    "parent_key": parent_key or "",
                    "parent_guid": parent_guid,
                    "shell_command": shlex.join(command),
                    "returncode": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                }
            )
            if proc.returncode != 0:
                payload.update(
                    {
                        "ok": False,
                        "results": results,
                        "relation_results": relation_results,
                    }
                )
                print_json(payload)
                return proc.returncode

    payload.update({"ok": True, "results": results, "relation_results": relation_results})
    print_json(payload)
    return 0


def command_init_config(args):
    config = default_config(
        yunxiao_project_list_url=args.yunxiao_project_list_url,
        cli_command=args.cli_command,
        with_example=args.with_example,
    )
    write_config(args.config, config, force=args.force)
    print_json({"ok": True, "config_path": str(args.config), "config": config})
    return 0


def command_show_config(args):
    config = load_config(args.config)
    print_json({"config_path": str(args.config), "config": config})
    return 0


def command_detect_project(args):
    config = load_config(args.config)
    repo_url = args.repo_url or git_remote_url(args.cwd)
    requirement_text = args.requirement_text or ""
    if args.requirement_file:
        requirement_text = args.requirement_file.read_text(encoding="utf-8")
    result = detect_project(config, repo_url, requirement_text, args.cwd)
    result["config_path"] = str(args.config)
    result["yunxiao_project_list_url"] = config.get("yunxiao_project_list_url", "")
    print_json(result)
    if result["ambiguous"] or not result["project"]:
        return 2
    return 0


def command_create_task(args):
    config = load_config(args.config)
    repo_url = args.repo_url or git_remote_url(args.cwd)
    requirement_text = args.requirement_text or ""
    if args.requirement_file:
        requirement_text = args.requirement_file.read_text(encoding="utf-8")
    detection = detect_project(config, repo_url, requirement_text, args.cwd)
    project = detection["project"]

    if args.project_name or args.project_url:
        project = {
            "name": args.project_name or args.project_url,
            "project_url": args.project_url,
            "tasklist_id": args.tasklist_id or "",
        }
        detection["project"] = project
        detection["matched_by"] = "manual"
        detection["ambiguous"] = False

    if detection["ambiguous"]:
        print_json(
            {
                "ok": False,
                "error": "多个云效项目同分命中，请指定 --project-name/--project-url 或更新配置。",
                "detection": detection,
            }
        )
        return 2

    if not project and not args.allow_no_project:
        print_json(
            {
                "ok": False,
                "error": "未匹配到云效项目；请更新全局配置，或追加 --allow-no-project。",
                "detection": detection,
            }
        )
        return 2

    cmd = build_lark_command(args, config, project, repo_url)
    payload = {
        "ok": True,
        "execute": args.execute,
        "config_path": str(args.config),
        "repo_url": repo_url,
        "detection": detection,
        "command": cmd,
        "shell_command": shlex.join(cmd),
    }

    if args.print_shell and not args.execute:
        print(payload["shell_command"])
        return 0

    if not args.execute:
        payload["note"] = "未执行飞书 CLI；确认无误后追加 --execute。"
        print_json(payload)
        return 0

    try:
        proc = subprocess.run(cmd, text=True, capture_output=True)
    except FileNotFoundError as exc:
        payload.update(
            {
                "ok": False,
                "error": f"找不到飞书 CLI：{cmd[0]}。请更新配置 cli_command 或设置 LARK_CLI。",
                "exception": str(exc),
            }
        )
        print_json(payload)
        return 127

    payload.update(
        {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    )
    payload["ok"] = proc.returncode == 0
    print_json(payload)
    return proc.returncode


def build_parser():
    parser = argparse.ArgumentParser(
        description="按 Git 仓库匹配云效项目，并创建云效工作项或飞书任务。"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-config", help="创建全局配置")
    init_parser.add_argument("--force", action="store_true")
    init_parser.add_argument("--with-example", action="store_true")
    init_parser.add_argument("--cli-command", default=os.environ.get("LARK_CLI", "lark-cli"))
    init_parser.add_argument("--yunxiao-project-list-url", default="")
    init_parser.set_defaults(func=command_init_config)

    show_parser = subparsers.add_parser("show-config", help="显示全局配置")
    show_parser.set_defaults(func=command_show_config)

    detect_parser = subparsers.add_parser("detect-project", help="根据仓库地址匹配云效项目")
    detect_parser.add_argument("--cwd", type=Path, default=Path.cwd())
    detect_parser.add_argument("--repo-url", default="")
    detect_parser.add_argument("--requirement-text", default="")
    detect_parser.add_argument("--requirement-file", type=Path)
    detect_parser.set_defaults(func=command_detect_project)

    yunxiao_parser = subparsers.add_parser("create-yunxiao-workitems", help="通过云效 OpenAPI 批量创建云效任务/工作项")
    yunxiao_parser.add_argument("--cwd", type=Path, default=Path.cwd())
    yunxiao_parser.add_argument("--repo-url", default="")
    yunxiao_parser.add_argument("--items-file", type=Path)
    yunxiao_parser.add_argument("--items-json", default="")
    yunxiao_parser.add_argument("--requirement-url", default="")
    yunxiao_parser.add_argument("--requirement-title", default="")
    yunxiao_parser.add_argument("--requirement-text", default="")
    yunxiao_parser.add_argument("--requirement-file", type=Path)
    yunxiao_parser.add_argument("--project-name", default="")
    yunxiao_parser.add_argument("--project-url", default="")
    yunxiao_parser.add_argument("--project-id", default="")
    yunxiao_parser.add_argument("--organization-id", default="")
    yunxiao_parser.add_argument("--workitem-type-id", default="")
    yunxiao_parser.add_argument("--assignee", default="")
    yunxiao_parser.add_argument("--sprint-id", default="")
    yunxiao_parser.add_argument("--priority-id", default="")
    yunxiao_parser.add_argument("--post-create-status", default=None)
    yunxiao_parser.add_argument("--skip-post-create-status", action="store_true")
    yunxiao_parser.add_argument("--related-workitem-id", default="")
    yunxiao_parser.add_argument("--relation-type", default="ASSOCIATED")
    yunxiao_parser.add_argument("--operator-id", default="")
    yunxiao_parser.add_argument("--format-type", default="MARKDOWN")
    yunxiao_parser.add_argument("--api-base", default=YUNXIAO_OPENAPI_BASE)
    yunxiao_parser.add_argument("--token-env", default="CODEUP_PERSONAL_ACCESS_TOKEN")
    yunxiao_parser.add_argument("--timeout", type=int, default=30)
    yunxiao_parser.add_argument("--require-related-workitem", action="store_true")
    yunxiao_parser.add_argument("--allow-no-project", action="store_true")
    yunxiao_parser.add_argument("--execute", action="store_true")
    yunxiao_parser.set_defaults(func=command_create_yunxiao_workitems)

    create_parser = subparsers.add_parser("create-task", help="生成或执行创建飞书任务命令")
    create_parser.add_argument("--cwd", type=Path, default=Path.cwd())
    create_parser.add_argument("--repo-url", default="")
    create_parser.add_argument("--summary", required=True)
    create_parser.add_argument("--description", default="")
    create_parser.add_argument("--requirement-url", default="")
    create_parser.add_argument("--requirement-title", default="")
    create_parser.add_argument("--requirement-text", default="")
    create_parser.add_argument("--requirement-file", type=Path)
    create_parser.add_argument("--project-name", default="")
    create_parser.add_argument("--project-url", default="")
    create_parser.add_argument("--sprint-url", default="")
    create_parser.add_argument("--workitem-id", default="")
    create_parser.add_argument("--workitem-title", default="")
    create_parser.add_argument("--workitem-url", default="")
    create_parser.add_argument("--tasklist-id", default="")
    create_parser.add_argument("--assignee", action="append", default=[])
    create_parser.add_argument("--follower", action="append", default=[])
    create_parser.add_argument("--due", default="")
    create_parser.add_argument("--as", dest="as_identity", choices=["bot", "user"], default="")
    create_parser.add_argument("--format", default="json")
    create_parser.add_argument("--idempotency-key", default="")
    create_parser.add_argument("--no-idempotency-key", action="store_true")
    create_parser.add_argument("--extra-json", default="")
    create_parser.add_argument("--use-data-payload", action="store_true")
    create_parser.add_argument("--allow-no-project", action="store_true")
    create_parser.add_argument("--execute", action="store_true")
    create_parser.add_argument("--lark-dry-run", action="store_true")
    create_parser.add_argument("--print-shell", action="store_true")
    create_parser.set_defaults(func=command_create_task)

    items_parser = subparsers.add_parser("create-task-items", help="通过 lark-cli 批量创建飞书任务项，并可设置父子任务关系")
    items_parser.add_argument("--cwd", type=Path, default=Path.cwd())
    items_parser.add_argument("--repo-url", default="")
    items_parser.add_argument("--items-file", type=Path)
    items_parser.add_argument("--items-json", default="")
    items_parser.add_argument("--description", default="")
    items_parser.add_argument("--requirement-url", default="")
    items_parser.add_argument("--requirement-title", default="")
    items_parser.add_argument("--requirement-text", default="")
    items_parser.add_argument("--requirement-file", type=Path)
    items_parser.add_argument("--project-name", default="")
    items_parser.add_argument("--project-url", default="")
    items_parser.add_argument("--sprint-url", default="")
    items_parser.add_argument("--workitem-id", default="")
    items_parser.add_argument("--workitem-title", default="")
    items_parser.add_argument("--workitem-url", default="")
    items_parser.add_argument("--tasklist-id", default="")
    items_parser.add_argument("--assignee", action="append", default=[])
    items_parser.add_argument("--follower", action="append", default=[])
    items_parser.add_argument("--due", default="")
    items_parser.add_argument("--as", dest="as_identity", choices=["bot", "user"], default="")
    items_parser.add_argument("--format", default="json")
    items_parser.add_argument("--no-idempotency-key", action="store_true")
    items_parser.add_argument("--extra-json", default="")
    items_parser.add_argument("--allow-no-project", action="store_true")
    items_parser.add_argument("--execute", action="store_true")
    items_parser.add_argument("--lark-dry-run", action="store_true")
    items_parser.set_defaults(func=command_create_task_items)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except (FileNotFoundError, FileExistsError, json.JSONDecodeError, ValueError) as exc:
        print_json({"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
