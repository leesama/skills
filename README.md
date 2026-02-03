# Skills 工具集

这是一个 skills 合集仓库，所有技能都放在 `skills/` 目录下，可通过 `pnpx` 直接安装全部或单个技能。

## 安装

安装全部技能：

```bash
pnpx skills add <你的仓库> --skill='*'
```

安装单个技能（示例：`weekly-report`）：

```bash
pnpx skills add <你的仓库> --skill=weekly-report
```

## 技能列表

- `weekly-report`：生成周报/月报，支持多仓库扫描、按周/月统计、输出 JSON 与 Word。

## 本地运行（以 `weekly-report` 为例）

进入技能目录并安装依赖：

```bash
cd skills/weekly-report
npm install
```

编译 TypeScript（生成 `scripts/`）：

```bash
npm run build
```

生成原始 JSON：

```bash
node scripts/weekly.js
```

默认输出到桌面（`~/Desktop`），若不存在则输出到当前目录。

将 JSON 内容中文化并润色为汇报表达（参考 `skills/weekly-report/resources/prompt.txt`），再渲染 Word：

```bash
node scripts/weekly_render.js -i <优化后的JSON> -o <输出文件>.docx
```

首次运行若未找到配置，会自动生成默认配置到 `~/.config/weekly-report/config.json`，并立即退出（不会继续执行统计）。如果输出包含 `CONFIG_INIT_REQUIRED`，需要先修改配置后再运行。

## 说明

- 各技能的详细使用方式见对应目录下的 `SKILL.md`。
