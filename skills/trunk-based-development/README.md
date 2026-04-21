# Trunk-Based Development 技能

中文 | [English](README.en.md)

帮助大模型按 Trunk-Based Development 的方式做 Git 协作：小批次改动、短分支、快速回 trunk。

## 一句话说明

把“主干开发”从口号变成可执行工作流，避免长分支、大 PR 和迟迟不回 trunk。

## 怎么安装

```bash
pnpx skills add leesama/skills --skill=trunk-based-development
```

## 什么时候用

当你想让助手按下面这些方式工作时：

- 我们团队用 trunk-based / 主干开发
- 先从 `main` / `master` 拉一个短分支
- 这个需求太大了，帮我拆成几次可合并的小改动
- 先用 feature flag 藏起来，能尽快合回 trunk
- 帮我看这个 PR/改动是不是太大了

## 这个技能会约束什么

- 先识别仓库真正的 trunk，而不是想当然指定分支
- 优先把任务拆成可独立验证、可独立合并的小增量
- 默认使用短生命周期分支，而不是长期功能分支
- 合并前尽量同步最新 trunk
- 未完成能力优先通过 feature flag、隐藏入口、默认关闭配置等方式落到 trunk
- 输出结论时会说明改动是否足够小、是否可独立合并、还存在哪些验证缺口

## 典型场景

- “我们现在使用 trunk-based，帮我按这个方式改需求”
- “先从 main 拉分支，然后尽快合回去”
- “这个功能太大了，拆成 3 个可独立 PR”
- “新逻辑先别开放，先用开关保护”
- “检查一下我这个分支是否偏离 trunk-based 节奏”

## 适合搭配的动作

- 创建短分支
- rebase / 同步 trunk
- 准备小而清晰的 PR 描述
- 对大改动做增量拆分

详细规则见 [SKILL.md](SKILL.md)。
