# AGENTS

本仓库是 `leesama/skills` 的技能源仓库，不是运行时自动加载目录。

## 仓库用途

- 所有可发布技能都放在 `skills/` 目录下。
- 每个技能目录至少包含 `SKILL.md`，可按需要补充 `README.md`、`README.en.md`、`scripts/`、`resources/` 等文件。
- 改动技能时，优先保持 `SKILL.md`、README 与实际目录结构一致。

## 关键约定

- 不要把这个仓库目录误当成 `~/.agents/skills` 的直接加载目录。
- 在这个仓库里改完 skill 后，默认通过 `pnpx skills` 重新安装对应 skill，不直接把仓库工作区当成安装态。
- 本仓库中的 skill 只要发生修改，默认流程就是：提交、本地推送到远端、再执行安装命令。

## 安装与验证

**首次安装和重新安装都使用同一条命令**，`pnpx skills add` 会自动覆盖已有安装：

安装单个技能：

```bash
pnpx skills add leesama/skills --skill=<skill-name> -g -y
```

安装全部技能：

```bash
pnpx skills add leesama/skills --skill='*' -g -y
```

示例：

```bash
pnpx skills add leesama/skills --skill=report -g -y
pnpx skills add leesama/skills --skill=trunk-based-development -g -y
```

**注意**：不要手动复制文件或创建符号链接到 `~/.claude/skills/`，始终通过 `pnpx skills add` 来安装和更新。

## 修改后默认动作

当本仓库中的 skill 被修改后，默认按以下顺序处理：

1. 更新对应 skill 目录下的说明文件
2. 提交并推送到远端
3. 通过 `pnpx skills add leesama/skills --skill=<skill-name> -g -y` 重新安装并验证

**重要**：每次推送到 GitHub 后，必须执行第 3 步重新安装。因为运行时加载的是 `~/.agents/skills/` 下的副本，推送后不会自动同步，必须通过 `pnpx skills add` 拉取最新代码覆盖安装。
