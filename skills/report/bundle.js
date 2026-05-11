const esbuild = require("esbuild");

esbuild
  .build({
    entryPoints: ["scripts/weekly_render.js"],
    bundle: true,
    platform: "node",
    target: ["node18"],
    outfile: "scripts/weekly_render.js",
    allowOverwrite: true,
    format: "cjs",
  })
  .then(() => {
    console.log("✅ weekly_render.js bundled (docx inlined)");
  })
  .catch((err) => {
    console.error("❌ Bundle failed:", err);
    process.exit(1);
  });
