import fs from "fs";
import path from "path";

type Task = {
  content?: string;
};

type WeeklyData = {
  tasks?: Task[];
};

function parseArgs(argv: string[]): { input: string } {
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

function formatTasks(tasks: Task[]): string {
  const lines = tasks
    .map((task) => String(task.content ?? "").trim())
    .filter(Boolean)
    .map((content, index) => `${index + 1}、${content}`);

  return lines.join("\n");
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.input) {
    console.error("缺少参数：-i / --input");
    process.exit(1);
  }

  const inputPath = path.resolve(args.input);
  const raw = fs.readFileSync(inputPath, "utf-8");
  const data = JSON.parse(raw) as WeeklyData;
  const tasks = Array.isArray(data.tasks) ? data.tasks : [];
  const output = formatTasks(tasks);

  if (!output) {
    console.error("未找到可输出的任务内容");
    process.exit(1);
  }

  console.log(output);
}

main();
