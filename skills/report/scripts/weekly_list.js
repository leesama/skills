"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
function parseArgs(argv) {
    const args = { input: "" };
    for (let i = 0; i < argv.length; i += 1) {
        const current = argv[i];
        if (current === "-i" || current === "--input") {
            args.input = argv[i + 1] ?? "";
            i += 1;
        }
    }
    return args;
}
function formatTasks(tasks) {
    const lines = tasks
        .map((task) => {
        const content = String(task.content ?? "").trim();
        const date = String(task.date ?? "").trim();
        return { content, date };
    })
        .filter(({ content }) => content)
        .map(({ content, date }, index) => {
        const datePrefix = date ? date.replace(/-/g, ".") + " " : "";
        return `${index + 1}、${datePrefix}${content}`;
    });
    return lines.join("\n");
}
function main() {
    const args = parseArgs(process.argv.slice(2));
    if (!args.input) {
        console.error("缺少参数：-i / --input");
        process.exit(1);
    }
    const inputPath = path_1.default.resolve(args.input);
    const raw = fs_1.default.readFileSync(inputPath, "utf-8");
    const data = JSON.parse(raw);
    const tasks = Array.isArray(data.tasks) ? data.tasks : [];
    const output = formatTasks(tasks);
    if (!output) {
        console.error("未找到可输出的任务内容");
        process.exit(1);
    }
    console.log(output);
}
main();
