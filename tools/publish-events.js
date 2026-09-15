#!/usr/bin/env node
/**
 * Batch cull → manual confirm → compress → upload for every event in
 * tools/gallery-folders.json, then generate js/photos.js once.
 *
 * Usage:
 *   node tools/publish-events.js
 *   node tools/publish-events.js --skip-upload
 *   node tools/publish-events.js --skip-confirm
 *   node tools/publish-events.js --max-keepers 0
 *   node tools/publish-events.js --only 20250928_桃園_樂天女孩
 *
 * Requires: Python 3.11–3.12 + pixcull (pip install -r requirements.txt), Node deps,
 * .env Cloudinary credentials (unless --skip-upload).
 * Default: uncapped keepers from PixCull "keep" decisions. Optional --max-keepers N for a hard cap.
 * After each cull, waits for manual confirm (review report / edit keepers) before compress.
 * Offline CLI only — do not use pixcull serve / LAN / DeepSeek in this pipeline.
 */

const fs = require("fs");
const path = require("path");
const readline = require("readline");
const { spawnSync } = require("child_process");

const ROOT = path.join(__dirname, "..");
const CONFIG_PATH = path.join(__dirname, "gallery-folders.json");
const MAX_KEEPERS_DEFAULT = 0; // 0 = no hard cap

function parseArgs(argv) {
  const opts = {
    maxKeepers: MAX_KEEPERS_DEFAULT,
    skipUpload: false,
    skipGenerate: false,
    skipConfirm: false,
    only: null,
    photoRoot: process.env.PHOTO_ROOT || null,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--skip-upload") opts.skipUpload = true;
    else if (a === "--skip-generate") opts.skipGenerate = true;
    else if (a === "--skip-confirm" || a === "-y" || a === "--yes") opts.skipConfirm = true;
    else if (a === "--max-keepers") opts.maxKeepers = Number(argv[++i]);
    else if (a === "--only") opts.only = argv[++i];
    else if (a === "--photo-root") opts.photoRoot = argv[++i];
    else if (a === "--help" || a === "-h") {
      console.log(
        `Usage: node tools/publish-events.js [--max-keepers 0] [--only FOLDER] [--photo-root DIR] [--skip-upload] [--skip-generate] [--skip-confirm]`
      );
      process.exit(0);
    }
  }
  return opts;
}

function loadConfig() {
  return JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8"));
}

function resolveLocalPath(entry, photoRoot) {
  if (entry.localPath) {
    // Allow PHOTO_ROOT override to rewrite D:\Photo\...
    if (photoRoot && entry.folder) {
      const candidate = path.join(photoRoot, entry.folder);
      if (fs.existsSync(candidate)) return candidate;
    }
    return entry.localPath;
  }
  if (photoRoot) return path.join(photoRoot, entry.folder);
  return path.join("D:\\Photo", entry.folder);
}

function run(cmd, args, label) {
  console.log(`\n>>> ${label}`);
  console.log(`$ ${cmd} ${args.map((a) => (/\s/.test(a) ? `"${a}"` : a)).join(" ")}`);
  const result = spawnSync(cmd, args, {
    cwd: ROOT,
    stdio: "inherit",
    shell: process.platform === "win32",
    env: process.env,
  });
  if (result.error) {
    console.error(result.error.message);
    return 1;
  }
  return result.status ?? 1;
}

function pythonCmd() {
  // Prefer project .venv (holds pixcull); then py -3 / python3 / python.
  const venvWin = path.join(ROOT, ".venv", "Scripts", "python.exe");
  const venvUnix = path.join(ROOT, ".venv", "bin", "python");
  if (process.platform === "win32" && fs.existsSync(venvWin)) {
    return { cmd: venvWin, prefix: [] };
  }
  if (fs.existsSync(venvUnix)) {
    return { cmd: venvUnix, prefix: [] };
  }
  if (process.platform === "win32") {
    const probe = spawnSync("py", ["-3", "--version"], { shell: true });
    if ((probe.status ?? 1) === 0) return { cmd: "py", prefix: ["-3"] };
    return { cmd: "python", prefix: [] };
  }
  const probe3 = spawnSync("python3", ["--version"]);
  if ((probe3.status ?? 1) === 0) return { cmd: "python3", prefix: [] };
  return { cmd: "python", prefix: [] };
}

function countImages(dir) {
  if (!fs.existsSync(dir)) return 0;
  let n = 0;
  const stack = [dir];
  while (stack.length) {
    const cur = stack.pop();
    for (const name of fs.readdirSync(cur)) {
      const full = path.join(cur, name);
      const st = fs.statSync(full);
      if (st.isDirectory()) stack.push(full);
      else if (/\.(jpe?g|png|webp)$/i.test(name)) n++;
    }
  }
  return n;
}

function openPath(target) {
  if (!target || !fs.existsSync(target)) return;
  try {
    if (process.platform === "win32") {
      spawnSync("cmd", ["/c", "start", "", target], {
        cwd: ROOT,
        shell: false,
        stdio: "ignore",
      });
    } else if (process.platform === "darwin") {
      spawnSync("open", [target], { stdio: "ignore" });
    } else {
      spawnSync("xdg-open", [target], { stdio: "ignore" });
    }
  } catch {
    // Best-effort only — user can open the path manually.
  }
}

function askLine(prompt) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => {
    rl.question(prompt, (answer) => {
      rl.close();
      resolve(answer);
    });
  });
}

/**
 * After cull: review HTML report / edit keepers/, then continue or skip.
 * Returns "continue" | "skip" | "abort".
 */
async function manualConfirm(folder, reportHtml, keepersDir, skipConfirm) {
  console.log(`\n>>> Manual confirm — ${folder}`);
  console.log(`Report:  ${reportHtml}`);
  console.log(`Keepers: ${keepersDir}`);
  console.log("Review the report. Delete unwanted files from keepers/ if needed.");

  if (skipConfirm) {
    console.log("(--skip-confirm) continuing to compress without pause.");
    return "continue";
  }

  openPath(reportHtml);

  const answer = (
    await askLine("Continue to compress? [Y]es / [s]kip this event / [a]bort all: ")
  )
    .trim()
    .toLowerCase();

  if (!answer || answer === "y" || answer === "yes") return "continue";
  if (answer === "s" || answer === "skip" || answer === "n" || answer === "no") {
    return "skip";
  }
  if (answer === "a" || answer === "abort" || answer === "q" || answer === "quit") {
    return "abort";
  }
  // Unknown input → treat as continue (safe default after review)
  console.log(`Unrecognized "${answer}" — continuing to compress.`);
  return "continue";
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const py = pythonCmd();
  let entries = loadConfig();
  if (opts.only) {
    entries = entries.filter((e) => e.folder === opts.only);
    if (!entries.length) {
      console.error(`No gallery-folders.json entry for --only ${opts.only}`);
      process.exit(1);
    }
  } else {
    const skipped = entries.filter((e) => e.skip);
    entries = entries.filter((e) => !e.skip);
    for (const e of skipped) {
      console.log(`SKIP (deferred): ${e.folder}${e.skipReason ? ` — ${e.skipReason}` : ""}`);
    }
  }

  console.log(`Events: ${entries.length}`);
  console.log(
    opts.maxKeepers > 0
      ? `Max keepers per event: ${opts.maxKeepers}`
      : "Max keepers per event: uncapped (PixCull keep decisions)"
  );
  console.log(
    opts.skipConfirm
      ? "Manual confirm: skipped (--skip-confirm)"
      : "Manual confirm: ON (pause after each cull before compress)"
  );

  const summary = [];
  let aborted = false;

  for (const entry of entries) {
    if (aborted) {
      summary.push({ folder: entry.folder, status: "aborted", input: 0, keepers: 0 });
      continue;
    }

    const localPath = resolveLocalPath(entry, opts.photoRoot);
    const cullOut = path.join(ROOT, "culling", entry.folder);
    const keepers = path.join(cullOut, "keepers");
    const reportHtml = path.join(cullOut, "culling-report.html");
    const compressed = path.join(ROOT, "compressed", entry.folder);

    console.log(`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
    console.log(`Event: ${entry.folder}`);
    console.log(`Local: ${localPath}`);

    if (!fs.existsSync(localPath)) {
      console.log(`SKIP — folder not found`);
      summary.push({ folder: entry.folder, status: "missing", input: 0, keepers: 0 });
      continue;
    }

    const inputCount = countImages(localPath);

    let code = run(
      py.cmd,
      [
        ...py.prefix,
        path.join("tools", "cull-photos.py"),
        localPath,
        cullOut,
        "--max-keepers",
        String(opts.maxKeepers),
        "--copy-keepers",
      ],
      `Cull ${entry.folder}`
    );
    if (code !== 0) {
      summary.push({ folder: entry.folder, status: "cull-failed", input: inputCount, keepers: 0 });
      continue;
    }

    let keeperCount = countImages(keepers);
    const decision = await manualConfirm(
      entry.folder,
      reportHtml,
      keepers,
      opts.skipConfirm
    );
    if (decision === "abort") {
      aborted = true;
      summary.push({
        folder: entry.folder,
        status: "aborted-after-cull",
        input: inputCount,
        keepers: keeperCount,
      });
      continue;
    }
    if (decision === "skip") {
      summary.push({
        folder: entry.folder,
        status: "confirm-skipped",
        input: inputCount,
        keepers: keeperCount,
      });
      continue;
    }

    // Re-count after possible manual edits to keepers/
    keeperCount = countImages(keepers);
    if (keeperCount === 0) {
      console.log("No keepers left after confirm — skip compress/upload for this event.");
      summary.push({
        folder: entry.folder,
        status: "no-keepers",
        input: inputCount,
        keepers: 0,
      });
      continue;
    }

    code = run(
      py.cmd,
      [
        ...py.prefix,
        path.join("tools", "compress-photos.py"),
        keepers,
        compressed,
        "--quality",
        "85",
        "--max-edge",
        "2000",
      ],
      `Compress ${entry.folder}`
    );
    if (code !== 0) {
      summary.push({ folder: entry.folder, status: "compress-failed", input: inputCount, keepers: keeperCount });
      continue;
    }

    if (!opts.skipUpload) {
      code = run(
        "node",
        [path.join("tools", "upload-to-cloudinary.js"), compressed, entry.folder],
        `Upload ${entry.folder}`
      );
      if (code !== 0) {
        summary.push({ folder: entry.folder, status: "upload-failed", input: inputCount, keepers: keeperCount });
        continue;
      }
    }

    summary.push({
      folder: entry.folder,
      status: opts.skipUpload ? "culled-compressed" : "uploaded",
      input: inputCount,
      keepers: keeperCount,
    });
  }

  if (!opts.skipGenerate && !aborted) {
    const code = run("node", [path.join("tools", "generate-photos.js")], "Generate js/photos.js");
    if (code !== 0) process.exitCode = 1;
  } else if (aborted) {
    console.log("\nAborted — skipped generate. Re-run when ready.");
    process.exitCode = 1;
  }

  console.log(`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
  console.log("Summary");
  for (const row of summary) {
    console.log(
      `  ${row.folder}: ${row.status} · input ${row.input} → keepers ${row.keepers}`
    );
  }
  console.log(`\nNext: commit js/photos.js when uploads look good`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
