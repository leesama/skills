import fs from "fs";
import path from "path";
import os from "os";
import { spawnSync } from "child_process";

const CONFIG_ENV = "WEEKLY_REPORT_CONFIG";

type Config = {
  author?: string;
  stat_mode?: string;
  week_start?: number;
  week_offset?: number;
  month_offset?: number;
  repo_roots?: string[] | string;
  company_git_patterns?: string[] | string;
  repo_paths?: string[] | string;
  max_scan_depth?: number;
};

type CommitItem = string;

type TaskRow = [string, string, string, string, string?];

let AUTHOR = "";
let STAT_MODE = "week";
let WEEK_START = 0;
let WEEK_OFFSET = 0;
let MONTH_OFFSET = 0;
let REPO_ROOTS: string[] = [];
let COMPANY_GIT_PATTERNS: string[] = [];
let REPO_PATHS: string[] = [];
let MAX_SCAN_DEPTH = 4;

function normalizeList(value: unknown): string[] {
  if (!value) return [];
  if (Array.isArray(value)) {
    return value.map((v) => String(v).trim()).filter(Boolean);
  }
  if (typeof value === "string") {
    return value
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean);
  }
  return [];
}

function maybeInt(value: unknown, fallback: number): number {
  const n = Number(value);
  return Number.isFinite(n) ? Math.trunc(n) : fallback;
}

function loadConfig(): { config: Config; configPath: string } {
  const candidates = [
    process.env[CONFIG_ENV] ?? "",
    path.join(process.cwd(), "weekly.config.json"),
    path.join(os.homedir(), ".config/weekly-report/config.json"),
    path.join(os.homedir(), ".weekly-report.json"),
  ];

  for (const candidate of candidates) {
    if (!candidate) continue;
    try {
      if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) {
        const raw = fs.readFileSync(candidate, "utf-8");
        const data = JSON.parse(raw);
        if (data && typeof data === "object") {
          return { config: data, configPath: candidate };
        }
      }
    } catch {
      continue;
    }
  }

  return { config: {}, configPath: "" };
}

function applyConfig(config: Config) {
  if (!config || typeof config !== "object") return;

  if (config.author !== undefined) AUTHOR = String(config.author ?? "").trim();
  if (config.stat_mode !== undefined) {
    const mode = String(config.stat_mode ?? STAT_MODE).trim().toLowerCase();
    if (mode) STAT_MODE = mode;
  }
  if (config.week_start !== undefined) WEEK_START = maybeInt(config.week_start, WEEK_START);
  if (config.week_offset !== undefined) WEEK_OFFSET = maybeInt(config.week_offset, WEEK_OFFSET);
  if (config.month_offset !== undefined) MONTH_OFFSET = maybeInt(config.month_offset, MONTH_OFFSET);
  if (config.repo_roots !== undefined) REPO_ROOTS = normalizeList(config.repo_roots);
  if (config.company_git_patterns !== undefined) COMPANY_GIT_PATTERNS = normalizeList(config.company_git_patterns);
  if (config.repo_paths !== undefined) REPO_PATHS = normalizeList(config.repo_paths);
  if (config.max_scan_depth !== undefined) MAX_SCAN_DEPTH = maybeInt(config.max_scan_depth, MAX_SCAN_DEPTH);
}

function defaultRepoRoots(): string[] {
  const env = (process.env.WEEKLY_REPORT_REPO_ROOTS ?? "").trim();
  if (env) {
    if (env.includes(path.delimiter)) {
      return env
        .split(path.delimiter)
        .map((v) => v.trim())
        .filter(Boolean);
    }
    return normalizeList(env);
  }
  return [process.cwd()];
}

function formatDate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function getWeekRange(weekOffset = 0, weekStart = 0): [string, string] {
  const today = new Date();
  const jsDay = today.getDay();
  const weekday = (jsDay + 6) % 7; // Monday=0
  const daysSinceWeekStart = (weekday - weekStart + 7) % 7;
  const start = new Date(today);
  start.setDate(today.getDate() - daysSinceWeekStart - weekOffset * 7);
  const end = new Date(start);
  end.setDate(start.getDate() + 6);
  return [formatDate(start), formatDate(end)];
}

function getMonthRange(monthOffset = 0): [string, string] {
  const today = new Date();
  let year = today.getFullYear();
  let month = today.getMonth() + 1 - monthOffset;
  while (month <= 0) {
    month += 12;
    year -= 1;
  }
  while (month > 12) {
    month -= 12;
    year += 1;
  }
  const start = new Date(year, month - 1, 1);
  const end = new Date(year, month, 0);
  return [formatDate(start), formatDate(end)];
}

function runGit(args: string[], cwd?: string): { status: number; stdout: string; stderr: string } {
  const result = spawnSync("git", args, {
    cwd,
    encoding: "utf-8",
  });
  return {
    status: result.status ?? 1,
    stdout: result.stdout || "",
    stderr: result.stderr || "",
  };
}

function iterGitRepos(root: string, maxDepth = 4): string[] {
  const repos: string[] = [];
  const rootAbs = path.resolve(root);
  const stack: Array<{ dir: string; depth: number }> = [{ dir: rootAbs, depth: 0 }];

  while (stack.length) {
    const { dir, depth } = stack.pop()!;
    if (depth > maxDepth) continue;
    let entries: fs.Dirent[] = [];
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      continue;
    }

    const hasGit = entries.some((entry) => entry.isDirectory() && entry.name === ".git");
    if (hasGit) {
      repos.push(dir);
      continue;
    }

    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      if (entry.name.startsWith(".")) continue;
      stack.push({ dir: path.join(dir, entry.name), depth: depth + 1 });
    }
  }

  return repos;
}

function getRepoRemotes(repoPath: string): Set<string> {
  const result = runGit(["-C", repoPath, "remote", "-v"]);
  const remotes = new Set<string>();
  if (result.status === 0 && result.stdout) {
    for (const line of result.stdout.split("\n")) {
      const parts = line.trim().split(/\s+/);
      if (parts.length >= 2) remotes.add(parts[1]);
    }
  }
  return remotes;
}

function isCompanyRepo(repoPath: string, patterns: string[]): boolean {
  if (!patterns || patterns.length === 0) return true;
  const remotes = getRepoRemotes(repoPath);
  for (const url of remotes) {
    for (const pattern of patterns) {
      if (pattern && url.includes(pattern)) return true;
    }
  }
  return false;
}

function discoverRepoPaths(repoRoots: string[], patterns: string[], maxDepth = 4): string[] {
  const repoPaths: string[] = [];
  for (const root of repoRoots) {
    if (!root) continue;
    if (!fs.existsSync(root) || !fs.statSync(root).isDirectory()) continue;
    for (const repoPath of iterGitRepos(root, maxDepth)) {
      if (isCompanyRepo(repoPath, patterns)) repoPaths.push(repoPath);
    }
  }
  return Array.from(new Set(repoPaths)).sort();
}

function getRepoPaths(): string[] {
  if (REPO_PATHS.length > 0) return REPO_PATHS;
  const roots = REPO_ROOTS.length > 0 ? REPO_ROOTS : defaultRepoRoots();
  if (roots.length === 0) {
    const cwd = process.cwd();
    if (fs.existsSync(path.join(cwd, ".git"))) return [cwd];
    return [];
  }
  return discoverRepoPaths(roots, COMPANY_GIT_PATTERNS, MAX_SCAN_DEPTH);
}

function getGitConfigValue(repoPath: string, key: string, useGlobal = false): string {
  const args = useGlobal ? ["config", "--global", key] : ["-C", repoPath, "config", key];
  const result = runGit(args);
  if (result.status === 0) return result.stdout.trim();
  return "";
}

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function resolveAuthorPattern(repoPath: string, author: string): { pattern: string; useExtended: boolean } {
  if (author && author.trim()) {
    const pattern = author.trim();
    return { pattern, useExtended: pattern.includes("|") };
  }
  const email =
    getGitConfigValue(repoPath, "user.email") ||
    getGitConfigValue(repoPath, "user.email", true);
  const name =
    getGitConfigValue(repoPath, "user.name") ||
    getGitConfigValue(repoPath, "user.name", true);
  if (email) return { pattern: escapeRegex(email), useExtended: false };
  if (name) return { pattern: escapeRegex(name), useExtended: false };
  return { pattern: "", useExtended: false };
}

function checkCommitInBranches(repoPath: string, commitHash: string): string {
  const result = runGit(["-C", repoPath, "branch", "--contains", commitHash]);
  if (result.status !== 0 || !result.stdout.trim()) return "unknown";
  const branches = result.stdout
    .split("\n")
    .map((b) => b.replace("*", "").trim())
    .filter(Boolean);

  for (const branch of branches) {
    if (branch.toLowerCase().includes("release")) return "release";
  }
  for (const branch of branches) {
    if (branch.toLowerCase().startsWith("zsxr")) return "zsxr";
  }
  for (const branch of branches) {
    if (branch.toLowerCase().includes("pre-test")) return "pre-test";
  }
  for (const branch of branches) {
    if (branch.toLowerCase().includes("feature")) return "feature";
  }
  return "other";
}

function getProjectNameFromReadme(repoPath: string): string | null {
  const candidates = ["README.md", "readme.md", "Readme.md"];
  for (const name of candidates) {
    const readmePath = path.join(repoPath, name);
    if (!fs.existsSync(readmePath)) continue;
    try {
      const content = fs.readFileSync(readmePath, "utf-8");
      const line = content.split("\n")[0] ?? "";
      let cleaned = line.trim();
      while (cleaned.startsWith("#")) cleaned = cleaned.replace(/^#+/, "").trim();
      if (cleaned) return cleaned;
    } catch {
      continue;
    }
  }
  return null;
}

function getGitCommits(author: string, repoPaths: string[], startDate: string, endDate: string): CommitItem[] {
  const sinceArg = `${startDate} 00:00:00`;
  const untilArg = `${endDate} 23:59:59`;
  const allCommits: CommitItem[] = [];

  for (const repoPath of repoPaths) {
    try {
      const { pattern, useExtended } = resolveAuthorPattern(repoPath, author);
      const args = [
        "-C",
        repoPath,
        "log",
        "--all",
        `--since=${sinceArg}`,
        `--until=${untilArg}`,
        "--pretty=format:%ad | %s | %H",
        "--date=short",
      ];
      if (pattern) {
        args.splice(6, 0, `--author=${pattern}`);
        if (useExtended) args.splice(6, 0, "--extended-regexp");
      }
      const result = runGit(args);
      if (result.status === 0 && result.stdout.trim()) {
        const projectName = getProjectNameFromReadme(repoPath);
        if (!projectName) {
          throw new Error(`仓库 ${repoPath} 本周有提交但未找到 README.md，无法提取项目名！`);
        }

        const repoName = projectName;
        const commits = result.stdout.trim().split("\n");
        const filtered: CommitItem[] = [];
        for (const line of commits) {
          if (
            line.includes("Merge branch") ||
            line.includes("Merge pull request") ||
            line.includes("Merge remote-tracking branch") ||
            line.toLowerCase().includes("merge")
          ) {
            continue;
          }
          const parts = line.split(" | ");
          if (parts.length >= 3) {
            const date = parts[0];
            const msg = parts[1];
            const commitHash = parts[2];
            const parentCheck = runGit(["-C", repoPath, "rev-list", "--parents", "-n", "1", commitHash]);
            if (parentCheck.status === 0) {
              const parents = parentCheck.stdout.trim().split(/\s+/);
              if (parents.length <= 2) {
                const branchStatus = checkCommitInBranches(repoPath, commitHash);
                filtered.push(`${date} | ${msg} | [${repoName}] | ${branchStatus}`);
              }
            }
          } else if (parts.length >= 2) {
            const date = parts[0];
            const msg = parts[1];
            filtered.push(`${date} | ${msg} | [${repoName}] | unknown`);
          }
        }
        allCommits.push(...filtered);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      console.log(`❌ 处理仓库 ${repoPath} 时出错: ${message}`);
    }
  }

  allCommits.sort((a, b) => {
    const da = a.split(" | ")[0];
    const db = b.split(" | ")[0];
    return db.localeCompare(da);
  });
  return allCommits;
}

function countCommitsByDate(commits: CommitItem[]): Record<string, number> {
  const map: Record<string, number> = {};
  for (const commit of commits) {
    const date = commit.split(" | ")[0];
    map[date] = (map[date] ?? 0) + 1;
  }
  return Object.fromEntries(Object.entries(map).sort((a, b) => a[0].localeCompare(b[0])));
}

function cleanCommitMessage(message: string): string {
  const prefixes = [
    "feat:",
    "feature:",
    "fix:",
    "docs:",
    "style:",
    "refactor:",
    "perf:",
    "test:",
    "chore:",
    "build:",
    "ci:",
  ];
  for (const prefix of prefixes) {
    if (message.startsWith(prefix)) return message.slice(prefix.length).trim();
  }
  return message.trim();
}

function normalizeMessageForDedup(message: string): string {
  if (!message) return message;
  let normalized = message.replace(/\d+$/, "").trim();
  normalized = normalized.replace(/\d+[^\w]*$/, "").trim();
  return normalized;
}

function analyzeCommitsForStats(commits: CommitItem[]): number {
  if (commits.length === 0) return 0;
  const unique = new Set<string>();
  for (const commit of commits) {
    const parts = commit.split(" | ");
    if (parts.length >= 3) {
      const msg = cleanCommitMessage(parts[1]);
      const repoName = parts[2].replace(/\[|\]/g, "");
      const normalized = normalizeMessageForDedup(msg);
      const key = `${repoName}::${normalized}`;
      if (!unique.has(key)) unique.add(key);
    }
  }
  return unique.size;
}

function getTaskStatusByBranch(branchStatus: string): string {
  if (!branchStatus || branchStatus === "unknown") return "已完成";
  if (branchStatus === "pre-test") return "测试中";
  if (branchStatus === "release") return "已完成";
  if (branchStatus === "zsxr") return "已完成";
  if (branchStatus === "feature") return "待测试";
  return "已完成";
}

function processCommitsToTasks(commits: CommitItem[]): TaskRow[] {
  const tasks: TaskRow[] = [];
  if (commits.length === 0) {
    tasks.push(["", "", "", "", ""]);
    return tasks;
  }

  const commitsByDate: Record<string, CommitItem[]> = {};
  for (const commit of commits) {
    const date = commit.split(" | ")[0];
    if (!commitsByDate[date]) commitsByDate[date] = [];
    commitsByDate[date].push(commit);
  }

  const dates = Object.keys(commitsByDate).sort((a, b) => b.localeCompare(a));
  for (const date of dates) {
    const dateCommits = commitsByDate[date];
    const commitData: Array<{ msg: string; repoName: string; branchStatus: string }> = [];

    for (const commit of dateCommits) {
      const parts = commit.split(" | ");
      if (parts.length >= 4) {
        commitData.push({
          msg: cleanCommitMessage(parts[1]),
          repoName: parts[2].replace(/\[|\]/g, ""),
          branchStatus: parts[3].trim() || "unknown",
        });
      } else if (parts.length >= 3) {
        commitData.push({
          msg: cleanCommitMessage(parts[1]),
          repoName: parts[2].replace(/\[|\]/g, ""),
          branchStatus: "unknown",
        });
      }
    }

    const grouped = new Map<string, string[]>();
    const orderedKeys: string[] = [];
    const seen = new Set<string>();

    for (const item of commitData) {
      const normalized = normalizeMessageForDedup(item.msg);
      const key = `${item.repoName}::${normalized}`;
      const list = grouped.get(key) ?? [];
      list.push(item.branchStatus || "unknown");
      grouped.set(key, list);
      if (!seen.has(key)) {
        seen.add(key);
        orderedKeys.push(key);
      }
    }

    const priority: Record<string, number> = {
      release: 1,
      zsxr: 2,
      "pre-test": 3,
      feature: 4,
      other: 5,
      unknown: 6,
    };

    for (const key of orderedKeys) {
      const [repoName, msg] = key.split("::");
      if (!msg) continue;
      const statuses = grouped.get(key) ?? ["unknown"];
      statuses.sort((a, b) => (priority[a] ?? 7) - (priority[b] ?? 7));
      const branchStatus = statuses[0] || "unknown";
      const status = getTaskStatusByBranch(branchStatus);
      tasks.push([msg, "完成开发并提交", status, "", repoName]);
    }
  }

  return tasks;
}

function finalDeduplicateTasks(tasks: TaskRow[]): TaskRow[] {
  if (tasks.length === 0) return tasks;
  const taskData: Array<{ key: string; task: TaskRow }> = [];
  const orderedKeys: string[] = [];
  const seen = new Set<string>();

  for (const task of tasks) {
    if (task.length >= 5 && task[0]) {
      const content = normalizeMessageForDedup(task[0]);
      const repoName = task[4] ?? "";
      const key = `${repoName}::${content}`;
      taskData.push({ key, task });
      if (!seen.has(key)) {
        seen.add(key);
        orderedKeys.push(key);
      }
    }
  }

  const statusPriority: Record<string, number> = {
    已完成: 1,
    测试中: 2,
    待测试: 3,
  };

  const result: TaskRow[] = [];
  for (const key of orderedKeys) {
    const [repoName, content] = key.split("::");
    if (!content) continue;
    const matched = taskData.filter((item) => item.key === key).map((item) => item.task);
    matched.sort((a, b) => (statusPriority[a[2]] ?? 4) - (statusPriority[b[2]] ?? 4));
    const best = matched[0];
    const prefix = `【${repoName}】 `;
    result.push([
      `${prefix}${content}`,
      best[1] ?? "完成开发并提交",
      best[2] ?? "已完成",
      best[3] ?? "",
      repoName,
    ]);
  }

  return result;
}

function saveTasksToJson(tasks: TaskRow[], startDate: string, endDate: string, totalCommits: number, periodType: string) {
  const jsonData: any = {
    report_type: `${periodType}报`,
    period: {
      start_date: startDate,
      end_date: endDate,
    },
    statistics: {
      total_commits: totalCommits,
      total_tasks: tasks.length,
      completed: tasks.filter((t) => t[2] === "已完成").length,
      testing: tasks.filter((t) => t[2] === "测试中").length,
      pending_test: tasks.filter((t) => t[2] === "待测试").length,
    },
    tasks: [],
  };

  const grouped: Record<string, any[]> = {};
  for (const task of tasks) {
    const item = {
      content: task[0] ?? "",
      completion_standard: task[1] ?? "",
      status: task[2] ?? "",
      notes: task[3] ?? "",
    };
    const projectName = task[4] ?? "其他项目";
    item.project_name = projectName;
    if (!grouped[projectName]) grouped[projectName] = [];
    grouped[projectName].push(item);
  }

  jsonData.projects = [];
  for (const [projectName, projectTasks] of Object.entries(grouped)) {
    jsonData.projects.push({ project_name: projectName, tasks: projectTasks });
    jsonData.tasks.push(...projectTasks);
  }

  const jsonFile = `本${periodType}工作${periodType}报_${endDate}.json`;
  fs.writeFileSync(jsonFile, JSON.stringify(jsonData, null, 2), "utf-8");
  console.log(`✅ JSON数据已生成：${jsonFile}`);
  return jsonData;
}

function main() {
  const { config, configPath } = loadConfig();
  if (Object.keys(config).length > 0) applyConfig(config);
  if (configPath) console.log(`🔧 已加载配置：${configPath}`);

  const repoPaths = getRepoPaths();
  if (repoPaths.length === 0) {
    console.log("⚠️ 未找到匹配公司 Git 地址的仓库，请检查 repo_roots 和 company_git_patterns 配置。");
  }
  console.log(`📂 正在扫描 ${repoPaths.length} 个仓库...`);
  repoPaths.forEach((repo, idx) => {
    console.log(`   ${idx + 1}. ${repo}`);
  });
  console.log("");

  let startDate = "";
  let endDate = "";
  let periodType = "周";
  if (STAT_MODE === "month") {
    [startDate, endDate] = getMonthRange(MONTH_OFFSET);
    periodType = "月";
  } else {
    [startDate, endDate] = getWeekRange(WEEK_OFFSET, WEEK_START);
    periodType = "周";
  }

  console.log(`🗓️ 统计模式：按${periodType}统计`);
  console.log(`🗓️ 统计区间：${startDate} 至 ${endDate}`);

  const commits = getGitCommits(AUTHOR, repoPaths, startDate, endDate);
  const countMap = countCommitsByDate(commits);
  const totalCommits = commits.length;
  console.log(`📊 本${periodType}共找到 ${totalCommits} 条提交记录`);
  for (const [date, count] of Object.entries(countMap)) {
    console.log(`📅 ${date}：${count} 条`);
  }
  const uniqueTasksCount = analyzeCommitsForStats(commits);
  const duplicatesRemoved = Math.max(0, totalCommits - uniqueTasksCount);
  console.log(`🧹 去重提交：移除 ${duplicatesRemoved} 条重复记录（从 ${totalCommits} 条合并为 ${uniqueTasksCount} 条）`);

  let tasks = processCommitsToTasks(commits);
  tasks = finalDeduplicateTasks(tasks);

  saveTasksToJson(tasks, startDate, endDate, totalCommits, periodType);
}

main();
