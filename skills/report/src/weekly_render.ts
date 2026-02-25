import fs from "fs";
import os from "os";
import path from "path";
import {
  AlignmentType,
  Document,
  HeadingLevel,
  Packer,
  Paragraph,
  Table,
  TableCell,
  TableRow,
  TextRun,
  WidthType,
} from "docx";

const CONFIG_ENV = "REPORT_CONFIG";
const LEGACY_CONFIG_ENV = "WEEKLY_REPORT_CONFIG";
const DEFAULT_CONFIG_PATH = path.join(os.homedir(), ".config/report/config.json");
const LEGACY_CONFIG_PATH = path.join(os.homedir(), ".config/weekly-report/config.json");
const DEFAULT_CONFIG_FILE = path.join(os.homedir(), ".report.json");
const LEGACY_CONFIG_FILE = path.join(os.homedir(), ".weekly-report.json");
const OUTPUT_DIR_ENV = "REPORT_OUTPUT_DIR";
const LEGACY_OUTPUT_DIR_ENV = "WEEKLY_REPORT_OUTPUT_DIR";

type ReportData = {
  report_type?: string;
  period?: { start_date?: string; end_date?: string };
  statistics?: { total_commits?: number };
  tasks?: Array<{ content?: string; completion_standard?: string; status?: string; notes?: string }>;
};
type AlignmentValue = (typeof AlignmentType)[keyof typeof AlignmentType];

function maybePath(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function readOutputDirFromConfig(): string {
  const envOutput = maybePath(process.env[OUTPUT_DIR_ENV]) || maybePath(process.env[LEGACY_OUTPUT_DIR_ENV]);
  if (envOutput) return envOutput;

  const configCandidates = [
    maybePath(process.env[CONFIG_ENV]),
    maybePath(process.env[LEGACY_CONFIG_ENV]),
    path.join(process.cwd(), "report.config.json"),
    path.join(process.cwd(), "weekly.config.json"),
    DEFAULT_CONFIG_PATH,
    LEGACY_CONFIG_PATH,
    DEFAULT_CONFIG_FILE,
    LEGACY_CONFIG_FILE,
  ];

  for (const candidate of configCandidates) {
    if (!candidate) continue;
    try {
      if (!fs.existsSync(candidate) || !fs.statSync(candidate).isFile()) continue;
      const raw = fs.readFileSync(candidate, "utf-8");
      const data = JSON.parse(raw) as { output_dir?: string };
      const outputDir = maybePath(data?.output_dir);
      if (outputDir) return outputDir;
    } catch {
      continue;
    }
  }

  return "";
}

function resolveDefaultOutputDir(): string {
  const configuredDir = readOutputDirFromConfig();
  if (configuredDir) {
    const dir = path.resolve(configuredDir);
    try {
      if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
      if (fs.statSync(dir).isDirectory()) return dir;
      console.warn(`⚠️ 输出目录不是文件夹，已忽略：${dir}`);
    } catch {
      console.warn(`⚠️ 输出目录不可用，已忽略：${dir}`);
    }
  }

  const desktopDir = path.join(os.homedir(), "Desktop");
  return fs.existsSync(desktopDir) && fs.statSync(desktopDir).isDirectory() ? desktopDir : process.cwd();
}

function periodTypeFromReport(reportType?: string): "日" | "周" | "月" {
  if (reportType && reportType.includes("月")) return "月";
  if (reportType && reportType.includes("日")) return "日";
  return "周";
}

function textParagraph(text: string, alignment: AlignmentValue = AlignmentType.LEFT) {
  return new Paragraph({
    alignment,
    children: [
      new TextRun({
        text,
        size: 24,
        font: "SimHei",
      }),
    ],
  });
}

function createCell(text: string, alignment: AlignmentValue, columnSpan?: number) {
  return new TableCell({
    columnSpan,
    children: [textParagraph(text, alignment)],
  });
}

function createCombinedTaskTable(thisTasks: string[][], periodType: string) {
  const rows: TableRow[] = [];

  rows.push(
    new TableRow({
      children: [createCell(`本${periodType}任务`, AlignmentType.CENTER, 4)],
    })
  );

  rows.push(
    new TableRow({
      children: [
        createCell("任务内容", AlignmentType.CENTER),
        createCell("完成标准", AlignmentType.CENTER),
        createCell("完成状态", AlignmentType.CENTER),
        createCell("备注", AlignmentType.CENTER),
      ],
    })
  );

  for (const task of thisTasks) {
    const data = task.length >= 4 ? task.slice(0, 4) : [...task, "", "", ""].slice(0, 4);
    rows.push(
      new TableRow({
        children: data.map((item) => createCell(item, AlignmentType.LEFT)),
      })
    );
  }

  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows,
  });
}

async function renderWord(data: ReportData, outputFile?: string) {
  const periodType = periodTypeFromReport(data.report_type);
  const startDate = data.period?.start_date ?? "";
  const endDate = data.period?.end_date ?? "";
  const totalCommits = data.statistics?.total_commits ?? "";

  const tasks = data.tasks ?? [];
  const thisTasks = tasks.map((t) => [
    t.content ?? "",
    t.completion_standard ?? "",
    t.status ?? "",
    t.notes ?? "",
  ]);

  const doc = new Document({
    sections: [
      {
        children: [
          new Paragraph({
            text: `本${periodType}工作${periodType}报`,
            heading: HeadingLevel.HEADING_1,
          }),
          textParagraph(`统计时间：${startDate} 至 ${endDate}`),
          textParagraph(`本${periodType}提交总数：${totalCommits} 条`),
          createCombinedTaskTable(thisTasks, periodType),
        ],
      },
    ],
  });

  let file = outputFile || `本${periodType}工作${periodType}报_${endDate}.docx`;
  if (!outputFile) {
    const outputDir = resolveDefaultOutputDir();
    file = path.join(outputDir, file);
  }
  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync(file, buffer);
  return file;
}

function parseArgs(argv: string[]) {
  const args = { input: "", output: "" };
  for (let i = 0; i < argv.length; i += 1) {
    const current = argv[i];
    if (current === "-i" || current === "--input") {
      args.input = argv[i + 1] ?? "";
      i += 1;
    } else if (current === "-o" || current === "--output") {
      args.output = argv[i + 1] ?? "";
      i += 1;
    }
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.input) {
    console.error("缺少参数：-i / --input");
    process.exit(1);
  }
  const inputPath = path.resolve(args.input);
  const raw = fs.readFileSync(inputPath, "utf-8");
  const data = JSON.parse(raw) as ReportData;
  const output = await renderWord(data, args.output || "");
  console.log(`✅ Word 已生成：${output}`);
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : String(err));
  process.exit(1);
});
