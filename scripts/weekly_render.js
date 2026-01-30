const fs = require("fs");
const path = require("path");
const {
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
} = require("docx");

function periodTypeFromReport(reportType) {
  if (reportType && reportType.includes("月")) return "月";
  return "周";
}

function textParagraph(text, alignment = AlignmentType.LEFT) {
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

function createCell(text, alignment, columnSpan) {
  return new TableCell({
    columnSpan,
    children: [textParagraph(text, alignment)],
  });
}

function createCombinedTaskTable(thisTasks, nextTasks, periodType) {
  const rows = [];

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

  rows.push(
    new TableRow({
      children: [createCell(`下${periodType}任务`, AlignmentType.CENTER, 4)],
    })
  );

  rows.push(
    new TableRow({
      children: [
        createCell("任务内容", AlignmentType.CENTER),
        createCell("完成标准", AlignmentType.CENTER),
        createCell("备注", AlignmentType.CENTER),
        createCell("", AlignmentType.CENTER),
      ],
    })
  );

  for (const task of nextTasks) {
    const data = [...task, "", "", ""].slice(0, 4);
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

async function renderWord(data, outputFile) {
  const periodType = periodTypeFromReport(data.report_type);
  const startDate = (data.period && data.period.start_date) || "";
  const endDate = (data.period && data.period.end_date) || "";
  const totalCommits = (data.statistics && data.statistics.total_commits) || "";

  const tasks = data.tasks || [];
  const thisTasks = tasks.map((t) => [
    t.content || "",
    t.completion_standard || "",
    t.status || "",
    t.notes || "",
  ]);

  const nextTasks = data.next_tasks || [["", "", ""]];

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
          createCombinedTaskTable(thisTasks, nextTasks, periodType),
        ],
      },
    ],
  });

  const file = outputFile || `本${periodType}工作${periodType}报_${endDate}.docx`;
  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync(file, buffer);
  return file;
}

function parseArgs(argv) {
  const args = { input: "", output: "" };
  for (let i = 0; i < argv.length; i += 1) {
    const current = argv[i];
    if (current === "-i" || current === "--input") {
      args.input = argv[i + 1] || "";
      i += 1;
    } else if (current === "-o" || current === "--output") {
      args.output = argv[i + 1] || "";
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
  const data = JSON.parse(raw);
  const output = await renderWord(data, args.output || "");
  console.log(`✅ Word 已生成：${output}`);
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : String(err));
  process.exit(1);
});
