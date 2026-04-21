---
description: 根据 Git 提交生成日报、周报或月报
argument-hint: [日报|周报|月报 或 额外要求]
---

严格按照 @/Users/lee/code/leesama-skills/skills/report/SKILL.md 的流程执行当前任务。

本次用户补充要求如下：

$ARGUMENTS

要求：

- 如果参数里明确包含“日报”“周报”“月报”，按对应统计口径处理。
- 如果没有额外参数，则结合当前会话上下文判断用户要生成什么报告。
- 输出时继续遵守该 skill 中约定的结果格式、文件路径返回方式和后续处理流程。
