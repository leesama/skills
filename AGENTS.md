# AGENTS

本仓库是 `leesama/skills` 的技能源仓库，不是运行时自动加载目录。

## 仓库用途

- 所有可发布技能都放在 `skills/` 目录下。
- 每个技能目录至少包含 `SKILL.md`，可按需要补充 `README.md`、`README.en.md`、`scripts/`、`resources/` 等文件。
- 改动技能时，优先保持 `SKILL.md`、README 与实际目录结构一致。

## 关键约定

- 不要把这个仓库目录误当成 `~/.agents/skills` 的直接加载目录。
- 在这个仓库里改完 skill 后，如需按“安装后的实际形态”验证，请通过 `pnpx skills` 重新安装对应 skill。
- 如果要验证 GitHub 远端版本，先提交并推送，再执行安装命令。

## 安装与验证

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

## 修改后默认动作

当本仓库中的 skill 被修改后，默认按以下顺序处理：

1. 更新对应 skill 目录下的说明文件
2. 需要对外分发或按安装态测试时，先提交并推送
3. 通过 `pnpx skills add leesama/skills --skill=<skill-name> -g -y` 重新安装并验证
