"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const fs_1 = __importDefault(require("fs"));
const os_1 = __importDefault(require("os"));
const path_1 = __importDefault(require("path"));
const docx_1 = require("docx");
const CONFIG_ENV = "REPORT_CONFIG";
const LEGACY_CONFIG_ENV = "WEEKLY_REPORT_CONFIG";
const DEFAULT_CONFIG_PATH = path_1.default.join(os_1.default.homedir(), ".config/report/config.json");
const LEGACY_CONFIG_PATH = path_1.default.join(os_1.default.homedir(), ".config/weekly-report/config.json");
const DEFAULT_CONFIG_FILE = path_1.default.join(os_1.default.homedir(), ".report.json");
const LEGACY_CONFIG_FILE = path_1.default.join(os_1.default.homedir(), ".weekly-report.json");
const OUTPUT_DIR_ENV = "REPORT_OUTPUT_DIR";
const LEGACY_OUTPUT_DIR_ENV = "WEEKLY_REPORT_OUTPUT_DIR";
function maybePath(value) {
    return typeof value === "string" ? value.trim() : "";
}
function readOutputDirFromConfig() {
    const envOutput = maybePath(process.env[OUTPUT_DIR_ENV]) || maybePath(process.env[LEGACY_OUTPUT_DIR_ENV]);
    if (envOutput)
        return envOutput;
    const configCandidates = [
        maybePath(process.env[CONFIG_ENV]),
        maybePath(process.env[LEGACY_CONFIG_ENV]),
        path_1.default.join(process.cwd(), "report.config.json"),
        path_1.default.join(process.cwd(), "weekly.config.json"),
        DEFAULT_CONFIG_PATH,
        LEGACY_CONFIG_PATH,
        DEFAULT_CONFIG_FILE,
        LEGACY_CONFIG_FILE,
    ];
    for (const candidate of configCandidates) {
        if (!candidate)
            continue;
        try {
            if (!fs_1.default.existsSync(candidate) || !fs_1.default.statSync(candidate).isFile())
                continue;
            const raw = fs_1.default.readFileSync(candidate, "utf-8");
            const data = JSON.parse(raw);
            const outputDir = maybePath(data?.output_dir);
            if (outputDir)
                return outputDir;
        }
        catch {
            continue;
        }
    }
    return "";
}
function resolveDefaultOutputDir() {
    const configuredDir = readOutputDirFromConfig();
    if (configuredDir) {
        const dir = path_1.default.resolve(configuredDir);
        try {
            if (!fs_1.default.existsSync(dir))
                fs_1.default.mkdirSync(dir, { recursive: true });
            if (fs_1.default.statSync(dir).isDirectory())
                return dir;
            console.warn(`⚠️ 输出目录不是文件夹，已忽略：${dir}`);
        }
        catch {
            console.warn(`⚠️ 输出目录不可用，已忽略：${dir}`);
        }
    }
    const desktopDir = path_1.default.join(os_1.default.homedir(), "Desktop");
    return fs_1.default.existsSync(desktopDir) && fs_1.default.statSync(desktopDir).isDirectory() ? desktopDir : process.cwd();
}
function periodTypeFromReport(reportType) {
    if (reportType && reportType.includes("月"))
        return "月";
    if (reportType && reportType.includes("日"))
        return "日";
    return "周";
}
function textParagraph(text, alignment = docx_1.AlignmentType.LEFT) {
    return new docx_1.Paragraph({
        alignment,
        children: [
            new docx_1.TextRun({
                text,
                size: 24,
                font: "SimHei",
            }),
        ],
    });
}
function createCell(text, alignment, columnSpan) {
    return new docx_1.TableCell({
        columnSpan,
        children: [textParagraph(text, alignment)],
    });
}
function createCombinedTaskTable(thisTasks, periodType) {
    const rows = [];
    rows.push(new docx_1.TableRow({
        children: [createCell(`本${periodType}任务`, docx_1.AlignmentType.CENTER, 4)],
    }));
    rows.push(new docx_1.TableRow({
        children: [
            createCell("任务内容", docx_1.AlignmentType.CENTER),
            createCell("完成标准", docx_1.AlignmentType.CENTER),
            createCell("完成状态", docx_1.AlignmentType.CENTER),
            createCell("备注", docx_1.AlignmentType.CENTER),
        ],
    }));
    for (const task of thisTasks) {
        const data = task.length >= 4 ? task.slice(0, 4) : [...task, "", "", ""].slice(0, 4);
        rows.push(new docx_1.TableRow({
            children: data.map((item) => createCell(item, docx_1.AlignmentType.LEFT)),
        }));
    }
    return new docx_1.Table({
        width: { size: 100, type: docx_1.WidthType.PERCENTAGE },
        rows,
    });
}
async function renderWord(data, outputFile) {
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
    const doc = new docx_1.Document({
        sections: [
            {
                children: [
                    new docx_1.Paragraph({
                        text: `本${periodType}工作${periodType}报`,
                        heading: docx_1.HeadingLevel.HEADING_1,
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
        file = path_1.default.join(outputDir, file);
    }
    const buffer = await docx_1.Packer.toBuffer(doc);
    fs_1.default.writeFileSync(file, buffer);
    return file;
}
function parseArgs(argv) {
    const args = { input: "", output: "" };
    for (let i = 0; i < argv.length; i += 1) {
        const current = argv[i];
        if (current === "-i" || current === "--input") {
            args.input = argv[i + 1] ?? "";
            i += 1;
        }
        else if (current === "-o" || current === "--output") {
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
    const inputPath = path_1.default.resolve(args.input);
    const raw = fs_1.default.readFileSync(inputPath, "utf-8");
    const data = JSON.parse(raw);
    const output = await renderWord(data, args.output || "");
    console.log(`✅ Word 已生成：${output}`);
}
main().catch((err) => {
    console.error(err instanceof Error ? err.message : String(err));
    process.exit(1);
});
