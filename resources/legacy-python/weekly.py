import subprocess
import json
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

# 配置
AUTHOR = ""   # 例如 "Alice" 或 "alice@example.com"
# AUTHOR 为空时，自动使用本机 git 的 user.name/user.email
# 统计模式："week" 按周统计，"month" 按月统计
STAT_MODE = "week"  # "week" 或 "month"
# 使用按周统计，而不是最近 N 天
WEEK_START = 0  # 一周起始：0=周一, 6=周日
WEEK_OFFSET = 0  # 0=本周, 1=上周, 2=上上周...
# 按月统计的偏移量
MONTH_OFFSET = 0  # 0=本月, 1=上月, 2=上上月...
# 自动识别仓库配置
# 1) REPO_ROOTS：本地仓库存放的根目录列表（会在这些目录下扫描 Git 仓库）
# 2) COMPANY_GIT_PATTERNS：公司 Git 地址的关键字（只保留 remote.url 命中这些关键字的仓库）
# 3) REPO_PATHS：若显式填写则直接使用，不再自动识别（为空表示启用自动识别）
REPO_ROOTS = []
COMPANY_GIT_PATTERNS = []  # 留空表示不做远程地址过滤
REPO_PATHS = []  # 为空时自动识别
MAX_SCAN_DEPTH = 4  # 扫描深度，避免遍历过多目录

CONFIG_ENV = "WEEKLY_REPORT_CONFIG"

def _normalize_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []

def _maybe_int(value, default):
    try:
        return int(value)
    except Exception:
        return default

def load_config():
    """从环境变量或默认位置读取配置"""
    config_paths = [
        os.environ.get(CONFIG_ENV, "").strip(),
        os.path.join(os.getcwd(), "weekly.config.json"),
        os.path.expanduser("~/.config/weekly-report/config.json"),
        os.path.expanduser("~/.weekly-report.json"),
    ]
    for path in config_paths:
        if not path:
            continue
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data, path
            except Exception:
                pass
    return {}, ""

def apply_config(config):
    """将配置覆盖到全局默认值"""
    global AUTHOR, STAT_MODE, WEEK_START, WEEK_OFFSET, MONTH_OFFSET
    global REPO_ROOTS, COMPANY_GIT_PATTERNS, REPO_PATHS, MAX_SCAN_DEPTH

    if not isinstance(config, dict):
        return

    if "author" in config:
        AUTHOR = str(config.get("author") or "").strip()
    if "stat_mode" in config:
        STAT_MODE = str(config.get("stat_mode") or STAT_MODE).strip().lower() or STAT_MODE
    if "week_start" in config:
        WEEK_START = _maybe_int(config.get("week_start"), WEEK_START)
    if "week_offset" in config:
        WEEK_OFFSET = _maybe_int(config.get("week_offset"), WEEK_OFFSET)
    if "month_offset" in config:
        MONTH_OFFSET = _maybe_int(config.get("month_offset"), MONTH_OFFSET)
    if "repo_roots" in config:
        REPO_ROOTS = _normalize_list(config.get("repo_roots"))
    if "company_git_patterns" in config:
        COMPANY_GIT_PATTERNS = _normalize_list(config.get("company_git_patterns"))
    if "repo_paths" in config:
        REPO_PATHS = _normalize_list(config.get("repo_paths"))
    if "max_scan_depth" in config:
        MAX_SCAN_DEPTH = _maybe_int(config.get("max_scan_depth"), MAX_SCAN_DEPTH)

def _default_repo_roots():
    env = os.environ.get("WEEKLY_REPORT_REPO_ROOTS", "").strip()
    if env:
        if os.pathsep in env:
            return [p.strip() for p in env.split(os.pathsep) if p.strip()]
        return _normalize_list(env)
    return [os.getcwd()]



def get_week_range(week_offset: int = 0, week_start: int = 0):
    """返回指定周的开始和结束日期（YYYY-MM-DD）
    week_offset: 0=本周, 1=上周...
    week_start: 0=周一, 6=周日
    """
    today = datetime.now().date()
    weekday = today.weekday()  # 周一=0, 周日=6
    days_since_week_start = (weekday - week_start) % 7
    start_of_this_week = today - timedelta(days=days_since_week_start)
    start_date = start_of_this_week - timedelta(weeks=week_offset)
    end_date = start_date + timedelta(days=6)
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

def get_month_range(month_offset: int = 0):
    """返回指定月的开始和结束日期（YYYY-MM-DD）
    month_offset: 0=本月, 1=上月, 2=上上月...
    """
    from calendar import monthrange
    today = datetime.now().date()
    
    # 计算目标月份
    year = today.year
    month = today.month - month_offset
    
    # 处理跨年的情况
    while month <= 0:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    
    # 获取该月的第一天和最后一天
    start_date = datetime(year, month, 1).date()
    _, last_day = monthrange(year, month)
    end_date = datetime(year, month, last_day).date()
    
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

def iter_git_repos(root, max_depth=4):
    """在指定根目录下查找 Git 仓库路径"""
    root = os.path.abspath(root)
    for dirpath, dirnames, _ in os.walk(root):
        depth = dirpath[len(root):].count(os.sep)
        if depth > max_depth:
            dirnames[:] = []
            continue
        if ".git" in dirnames:
            yield dirpath
            dirnames[:] = []
            continue

def get_repo_remotes(repo_path):
    """获取仓库的远程地址列表"""
    cmd = ["git", "-C", repo_path, "remote", "-v"]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, stderr=subprocess.PIPE)
    remotes = set()
    if result.returncode == 0 and result.stdout:
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                remotes.add(parts[1])
    return remotes

def is_company_repo(repo_path, git_patterns):
    """判断仓库 remote 是否匹配公司 Git 地址关键字"""
    if not git_patterns:
        return True
    remotes = get_repo_remotes(repo_path)
    for url in remotes:
        for pattern in git_patterns:
            if pattern and pattern in url:
                return True
    return False

def discover_repo_paths(repo_roots, git_patterns, max_depth=4):
    """自动识别匹配公司 Git 地址的仓库路径"""
    repo_paths = []
    for root in repo_roots:
        if not root or not os.path.isdir(root):
            continue
        for repo_path in iter_git_repos(root, max_depth=max_depth):
            if is_company_repo(repo_path, git_patterns):
                repo_paths.append(repo_path)
    return sorted(set(repo_paths))

def get_repo_paths():
    """获取仓库路径列表：优先使用 REPO_PATHS，否则自动识别"""
    if REPO_PATHS:
        return REPO_PATHS
    roots = REPO_ROOTS or _default_repo_roots()
    if not roots:
        cwd = os.getcwd()
        if os.path.isdir(os.path.join(cwd, ".git")):
            return [cwd]
        return []
    return discover_repo_paths(roots, COMPANY_GIT_PATTERNS, MAX_SCAN_DEPTH)

def get_git_config_value(repo_path, key, use_global=False):
    """读取 git 配置值"""
    if use_global:
        cmd = ["git", "config", "--global", key]
    else:
        cmd = ["git", "-C", repo_path, "config", key]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, stderr=subprocess.PIPE)
    if result.returncode == 0:
        return result.stdout.strip()
    return ""

def resolve_author_pattern(repo_path, author):
    """AUTHOR 为空时自动使用 git user.name/user.email 生成 author 匹配模式"""
    if author and str(author).strip():
        pattern = str(author).strip()
        return pattern, ("|" in pattern)
    email = get_git_config_value(repo_path, "user.email") or get_git_config_value(repo_path, "user.email", use_global=True)
    name = get_git_config_value(repo_path, "user.name") or get_git_config_value(repo_path, "user.name", use_global=True)
    if email:
        return re.escape(email), False
    if name:
        return re.escape(name), False
    return "", False



def check_commit_in_branches(repo_path, commit_hash):
    """检查提交是否存在于特定分支中
    返回分支类型：release, pre-test, feature, zsxr, unknown
    优先级：release > zsxr > pre-test > feature
    """
    try:
        # 检查提交是否在分支中
        cmd_pretest = ["git", "-C", repo_path, "branch", "--contains", commit_hash]
        result = subprocess.run(cmd_pretest, stdout=subprocess.PIPE, text=True, stderr=subprocess.PIPE)
        
        if result.returncode == 0 and result.stdout.strip():
            branches = result.stdout.strip().split('\n')
            branches = [b.strip().replace('*', '').strip() for b in branches]
            
            # 按优先级检查：release > zsxr > pre-test > feature
            # 检查是否包含release分支（最高优先级）
            for branch in branches:
                if 'release' in branch.lower():
                    return 'release'
            
            # 检查是否包含zsxr开头的分支（已完成状态）
            for branch in branches:
                if branch.lower().startswith('zsxr'):
                    return 'zsxr'
            
            # 检查是否包含pre-test分支
            for branch in branches:
                if 'pre-test' in branch.lower():
                    return 'pre-test'
            
            # 检查是否包含feature分支
            for branch in branches:
                if 'feature' in branch.lower():
                    return 'feature'
            
            return 'other'
        else:
            return 'unknown'
    except Exception as e:
        return 'unknown'

def get_project_name_from_readme(repo_path):
    """从 README.md 读取第一行作为项目名"""
    possible_names = ["README.md", "readme.md", "Readme.md"]
    for name in possible_names:
        readme_path = os.path.join(repo_path, name)
        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    line = f.readline()
                    while line.startswith('#'):
                        line = line.lstrip('#').strip()
                    if line:
                        return line.strip()
            except Exception:
                pass
    return None

def get_git_commits(author, repo_paths, start_date, end_date):
    """从多个仓库获取Git提交记录（按周范围）"""
    since_arg = f"{start_date} 00:00:00"
    until_arg = f"{end_date} 23:59:59"
    all_commits = []
    
    for repo_path in repo_paths:
        try:
            author_filter, use_extended = resolve_author_pattern(repo_path, author)
            cmd = [
                "git", "-C", repo_path, "log",
                "--all",  # 扫描所有分支
                f"--since={since_arg}",
                f"--until={until_arg}",
                "--pretty=format:%ad | %s | %H",  # 日期、提交信息和提交哈希
                "--date=short"
            ]
            if author_filter:
                cmd.insert(6, f"--author={author_filter}")
                if use_extended:
                    cmd.insert(6, "--extended-regexp")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, stderr=subprocess.PIPE)
            
            if result.returncode == 0 and result.stdout.strip():
                # 检查 README 并获取项目名
                project_name = get_project_name_from_readme(repo_path)
                if not project_name:
                    raise ValueError(f"仓库 {repo_path} 本周有提交但未找到 README.md，无法提取项目名！")
                
                repo_name = project_name
                commits = result.stdout.strip().split("\n")
                # 过滤掉合并相关的提交，只保留本人的直接提交
                filtered_commits = []
                for c in commits:
                    # 过滤掉各种合并相关的提交
                    if ("Merge branch" not in c and 
                        "Merge pull request" not in c and
                        "Merge remote-tracking branch" not in c and
                        "merge" not in c.lower()):
                        
                        # 解析提交信息：日期 | 消息 | 提交哈希
                        parts = c.split(" | ")
                        if len(parts) >= 3:
                            date, msg, commit_hash = parts[0], parts[1], parts[2]
                            
                            # 进一步验证这是本人的直接提交（非合并提交）
                            # 检查提交是否有多个父提交（合并提交的特征）
                            parent_check_cmd = ["git", "-C", repo_path, "rev-list", "--parents", "-n", "1", commit_hash]
                            parent_result = subprocess.run(parent_check_cmd, stdout=subprocess.PIPE, text=True, stderr=subprocess.PIPE)
                            
                            if parent_result.returncode == 0:
                                parents = parent_result.stdout.strip().split()
                                # 如果有超过2个父提交（包括自己），说明是合并提交，跳过
                                if len(parents) <= 2:  # 自己 + 1个父提交 = 正常提交
                                    # 检查该提交是否存在于各个分支
                                    branch_status = check_commit_in_branches(repo_path, commit_hash)
                                    # 添加仓库名和分支状态
                                    filtered_commits.append(f"{date} | {msg} | [{repo_name}] | {branch_status}")
                        elif len(parts) >= 2:
                            date, msg = parts[0], parts[1]
                            # 没有提交哈希的情况，保守处理
                            filtered_commits.append(f"{date} | {msg} | [{repo_name}] | unknown")
                all_commits.extend(filtered_commits)
            else:
                # print(f"⚠️  仓库 {repo_path} 获取提交记录失败或无提交记录")
                pass
                
        except Exception as e:
            print(f"❌ 处理仓库 {repo_path} 时出错: {e}")
            # 如果是 ValueError (README 缺失), 这里的 print 可能不够，但用户要求"报错"。
            # 这里的 print(..., error) 已经算是报错了。
            # 脚本会继续执行其他仓库。
    
    # 按日期排序所有提交
    all_commits.sort(key=lambda x: x.split(" | ")[0], reverse=True)
    return all_commits

def count_commits_by_date(commits):
    count_map = defaultdict(int)
    for c in commits:
        date, _ = c.split(" | ", 1)
        count_map[date] += 1
    # 按日期排序返回
    return dict(sorted(count_map.items()))

def clean_commit_message(message):
    """清理提交信息，去除前缀"""
    # 常见的提交前缀
    prefixes = ['feat:', 'feature:', 'fix:', 'docs:', 'style:', 'refactor:', 'perf:', 'test:', 'chore:', 'build:', 'ci:']
    
    for prefix in prefixes:
        if message.startswith(prefix):
            return message[len(prefix):].strip()
    
    return message.strip()

def normalize_message_for_dedup(message):
    """规范化消息用于去重（去除末尾数字/符号）"""
    if not message:
        return message
    normalized = re.sub(r'\d+$', '', message).strip()
    normalized = re.sub(r'\d+[^\w]*$', '', normalized).strip()
    return normalized

def deduplicate_similar_messages(messages):
    """去重相似的提交信息（只是末尾数字不同的），并去除末尾数字"""
    if not messages:
        return messages
    
    # 用于存储去重后的消息
    unique_messages = []
    seen_patterns = set()
    
    for msg in messages:
        # 将末尾的数字替换为占位符，用于比较相似性
        pattern = normalize_message_for_dedup(msg)
        
        if pattern not in seen_patterns:
            seen_patterns.add(pattern)
            # 返回去除末尾数字后的消息
            unique_messages.append(pattern)
    
    return unique_messages

def process_commits_to_tasks(commits):
    """将Git提交记录转换为任务格式"""
    tasks = []
    
    if not commits:
        # 如果没有提交记录，添加示例任务
        tasks.append([
            "",
            "", 
            "",
            "",  # 备注栏留空
            ""   # 仓库信息栏，用于后续添加前缀
        ])
    else:
        # 按日期分组提交
        commits_by_date = defaultdict(list)
        for commit in commits:
            date = commit.split(" | ")[0]
            commits_by_date[date].append(commit)
        
        # 为每个提交记录创建单独的任务条目
        for date in sorted(commits_by_date.keys(), reverse=True):
            date_commits = commits_by_date[date]
            
            # 提取并清理提交信息，同时获取仓库信息和分支状态
            commit_data = []
            for commit in date_commits:
                parts = commit.split(" | ")
                if len(parts) >= 4:
                    msg = clean_commit_message(parts[1])  # 清理提交信息前缀
                    repo_name = parts[2].strip("[]")
                    branch_status = parts[3].strip() if parts[3].strip() else "unknown"
                    commit_data.append((msg, repo_name, branch_status))
                elif len(parts) >= 3:
                    msg = clean_commit_message(parts[1])
                    repo_name = parts[2].strip("[]")
                    branch_status = "unknown"
                    commit_data.append((msg, repo_name, branch_status))
            
            # 同项目相同 commit-msg 只保留一条
            grouped = defaultdict(list)
            ordered_keys = []
            seen_keys = set()
            
            for msg, repo_name, branch_status in commit_data:
                normalized_msg = normalize_message_for_dedup(msg)
                key = (repo_name, normalized_msg)
                grouped[key].append(branch_status or "unknown")
                if key not in seen_keys:
                    seen_keys.add(key)
                    ordered_keys.append(key)
            
            # 为每个去重后的提交信息创建单独的任务行
            for repo_name, msg in ordered_keys:
                if msg:  # 只处理非空消息
                    # 选择优先级最高的分支状态
                    priority_order = {'release': 1, 'zsxr': 2, 'pre-test': 3, 'feature': 4, 'other': 5, 'unknown': 6}
                    statuses = grouped.get((repo_name, msg), ["unknown"])
                    statuses.sort(key=lambda x: priority_order.get(x, 7))
                    branch_status = statuses[0] if statuses else "unknown"
                    
                    # 根据分支状态判断完成状态
                    status = get_task_status_by_branch(branch_status)
                    
                    # 翻译英文提交信息
                    task_content = msg
                    completion_standard = "完成开发并提交"
                    notes = ""  # 备注栏留空
                    repo_info = repo_name  # 保存仓库信息
                    
                    tasks.append([task_content, completion_standard, status, notes, repo_info])
    
    return tasks

def analyze_commits_for_stats(commits):
    """预统计：去重数量"""
    if not commits:
        return 0
    unique_keys = set()
    for commit in commits:
        parts = commit.split(" | ")
        if len(parts) >= 3:
            msg = clean_commit_message(parts[1])
            repo_name = parts[2].strip("[]")
            normalized_msg = normalize_message_for_dedup(msg)
            key = (repo_name, normalized_msg)
            if key in unique_keys:
                continue
            unique_keys.add(key)
    return len(unique_keys)

def get_task_status_by_branch(branch_status):
    """根据分支状态判断任务完成状态"""
    if not branch_status or branch_status == 'unknown':
        return "已完成"  # 默认状态
    
    # 根据分支状态直接判断
    if branch_status == 'pre-test':
        return "测试中"
    elif branch_status == 'release':
        return "已完成"
    elif branch_status == 'zsxr':
        return "已完成"
    elif branch_status == 'feature':
        return "待测试"
    else:
        return "已完成"

def final_deduplicate_tasks(tasks):
    """对所有任务进行最终去重，包括跨行去重，并添加仓库前缀"""
    if not tasks:
        return tasks
    
    # 提取任务内容和仓库信息，并按仓库去重
    task_data = []
    ordered_keys = []
    seen_keys = set()
    
    for task in tasks:
        if task and len(task) >= 5 and task[0]:  # 确保有仓库信息
            content = normalize_message_for_dedup(task[0])
            repo_name = task[4] if len(task) > 4 else ""
            key = (repo_name, content)
            task_data.append((key, task))
            if key not in seen_keys:
                seen_keys.add(key)
                ordered_keys.append(key)
    
    # 重建任务列表，添加仓库前缀
    deduplicated_tasks = []
    for repo_name, content in ordered_keys:
        if content:  # 只保留非空内容
            # 找到所有匹配的任务，选择状态优先级最高的
            matched_tasks = [t for k, t in task_data if k == (repo_name, content)]
            if matched_tasks:
                # 按任务状态优先级排序：已完成 > 测试中 > 待测试
                status_priority = {'已完成': 1, '测试中': 2, '待测试': 3}
                matched_tasks.sort(key=lambda x: status_priority.get(x[2] if len(x) > 2 else '已完成', 4))
                best_task = matched_tasks[0]
                
                # 根据仓库名添加前缀
                prefix = f"【{repo_name}】 "
                new_task_content = prefix + content
                
                # 构建新任务，只保留前4列
                new_task = [
                    new_task_content,
                    best_task[1] if len(best_task) > 1 else "完成开发并提交",
                    best_task[2] if len(best_task) > 2 else "已完成",
                    best_task[3] if len(best_task) > 3 else "",
                    repo_name
                ]
                deduplicated_tasks.append(new_task)
    
    return deduplicated_tasks

def save_tasks_to_json(tasks, start_date, end_date, total_commits, period_type="周"):
    """将任务数据保存为JSON格式"""
    # 构建JSON数据结构
    json_data = {
        "report_type": f"{period_type}报",
        "period": {
            "start_date": start_date,
            "end_date": end_date
        },
        "statistics": {
            "total_commits": total_commits,
            "total_tasks": len(tasks),
            "completed": sum(1 for t in tasks if len(t) > 2 and t[2] == "已完成"),
            "testing": sum(1 for t in tasks if len(t) > 2 and t[2] == "测试中"),
            "pending_test": sum(1 for t in tasks if len(t) > 2 and t[2] == "待测试")
        },
        "tasks": []
    }
    
    # 临时存储按项目分组的任务
    grouped_tasks = defaultdict(list)
    
    # 添加任务详情
    for task in tasks:
        task_item = {
            "content": task[0] if len(task) > 0 else "",
            "completion_standard": task[1] if len(task) > 1 else "",
            "status": task[2] if len(task) > 2 else "",
            "notes": task[3] if len(task) > 3 else ""
        }
        # 获取项目名 (第5列)
        project_name = task[4] if len(task) > 4 else "其他项目"
        
        task_item["project_name"] = project_name
        grouped_tasks[project_name].append(task_item)
    
    # 将分组后的任务写入 JSON
    json_data["projects"] = []
    for project_name, project_tasks in grouped_tasks.items():
        json_data["projects"].append({
            "project_name": project_name,
            "tasks": project_tasks
        })
        # 同时也保留扁平的 tasks 列表以便通过旧方式查看（可选，这里我保留了扁平列表，或者可以清空）
        json_data["tasks"].extend(project_tasks)
    
    # 保存JSON文件
    json_file = f"本{period_type}工作{period_type}报_{end_date}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ JSON数据已生成：{json_file}")
    return json_data

if __name__ == "__main__":
    config, config_path = load_config()
    if config:
        apply_config(config)
    if config_path:
        print(f"🔧 已加载配置：{config_path}")

    repo_paths = get_repo_paths()
    if not repo_paths:
        print("⚠️ 未找到匹配公司 Git 地址的仓库，请检查 REPO_ROOTS 和 COMPANY_GIT_PATTERNS 配置。")
    print(f"📂 正在扫描 {len(repo_paths)} 个仓库...")
    for i, repo in enumerate(repo_paths, 1):
        print(f"   {i}. {repo}")
    print()

    # 根据统计模式计算日期范围
    if STAT_MODE == "month":
        start_date, end_date = get_month_range(MONTH_OFFSET)
        period_type = "月"
    else:
        start_date, end_date = get_week_range(WEEK_OFFSET, WEEK_START)
        period_type = "周"
    print(f"🗓️ 统计模式：按{period_type}统计")
    print(f"🗓️ 统计区间：{start_date} 至 {end_date}")
    
    commits = get_git_commits(AUTHOR, repo_paths, start_date, end_date)
    
    # 统计每日提交数并输出
    count_map = count_commits_by_date(commits)
    total_commits = len(commits)
    print(f"📊 本{period_type}共找到 {total_commits} 条提交记录")
    for date, count in count_map.items():
        print(f"📅 {date}：{count} 条")
    # 预统计去重与翻译条数（在耗时处理前先提示）
    unique_tasks_count = analyze_commits_for_stats(commits)
    duplicates_removed = max(0, total_commits - unique_tasks_count)
    print(f"🧹 去重提交：移除 {duplicates_removed} 条重复记录（从 {total_commits} 条合并为 {unique_tasks_count} 条）")
    
    # 处理提交记录为任务
    final_tasks = process_commits_to_tasks(commits)
    final_tasks = final_deduplicate_tasks(final_tasks)

    
    # 同时生成JSON数据
    save_tasks_to_json(final_tasks, start_date, end_date, len(commits), period_type)
