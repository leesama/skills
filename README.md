# Skills 工具集

中文 | [English](README.en.md)

这是一个 skills 合集仓库，所有技能都放在 `skills/` 目录下，可通过 `pnpx` 直接安装全部或单个技能。

## 安装

安装全部技能：

```bash
pnpx skills add leesama/skills --skill='*'
```

安装单个技能（示例：`report`）：

```bash
pnpx skills add leesama/skills --skill=report
```

## 技能列表

| 技能 | 说明 |
| --- | --- |
| [report](skills/report) | 生成日报/周报/月报，支持多仓库扫描、按日/周/月统计、输出 JSON 与 Word。 |

## 说明

- 每个技能目录下都有独立的 `README.md` / `SKILL.md`，点击技能名可进入对应目录。
