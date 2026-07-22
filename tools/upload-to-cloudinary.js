#!/usr/bin/env node
/**
 * Upload compressed JPG/JPEG files to Cloudinary (resumable).
 * Credentials via CLOUDINARY_URL or CLOUDINARY_* env vars — never hardcode secrets.
 *
 * Usage:
 *   node tools/upload-to-cloudinary.js <source_dir> <cloudinary_folder>
 */

const fs = require("fs");
const path = require("path");
const { loadCloudinary } = require("./lib/cloudinary-env");

const SOURCE_DIR = process.argv[2];
const CLOUDINARY_FOLDER = process.argv[3];
const CONCURRENCY = Number(process.env.UPLOAD_CONCURRENCY || 8);
const LOG_FILE = path.join(process.cwd(), "upload-log.json");
const SKIP_EXISTING = process.env.UPLOAD_FORCE !== "1";

if (!SOURCE_DIR || !CLOUDINARY_FOLDER) {
  console.error("Usage: node tools/upload-to-cloudinary.js <source_dir> <cloudinary_folder>");
  console.error('Example: node tools/upload-to-cloudinary.js "./compressed/event" "20250810_台北大巨蛋_樂天女孩"');
  process.exit(1);
}

const cloudinary = loadCloudinary();

function walkJPGs(dir) {
  if (!fs.existsSync(dir)) {
    console.error(`Folder not found: ${dir}`);
    process.exit(1);
  }
  const out = [];
  const stack = [dir];
  while (stack.length) {
    const current = stack.pop();
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) stack.push(full);
      else if (/\.(jpe?g)$/i.test(entry.name)) out.push(full);
    }
  }
  return out.sort();
}

function loadDoneSet() {
  try {
    const data = JSON.parse(fs.readFileSync(LOG_FILE, "utf8"));
    return new Set(data.map((r) => r.localFile));
  } catch {
    return new Set();
  }
}

function appendLog(entry) {
  let log = [];
  try {
    log = JSON.parse(fs.readFileSync(LOG_FILE, "utf8"));
  } catch {
    /* empty */
  }
  log.push(entry);
  fs.writeFileSync(LOG_FILE, JSON.stringify(log, null, 2), "utf8");
}

async function uploadOne(filePath) {
  const basename = path.basename(filePath);
  const publicId = path.parse(basename).name;

  const result = await cloudinary.uploader.upload(filePath, {
    folder: CLOUDINARY_FOLDER,
    public_id: publicId,
    resource_type: "image",
    overwrite: false,
    use_filename: true,
    unique_filename: false,
  });

  return {
    localFile: filePath,
    folder: CLOUDINARY_FOLDER,
    publicId: result.public_id,
    url: result.secure_url,
    bytes: result.bytes,
    format: result.format,
    width: result.width,
    height: result.height,
  };
}

async function runPool(items, concurrency, worker) {
  let index = 0;
  let failed = 0;
  let completed = 0;
  const start = Date.now();

  async function run() {
    while (index < items.length) {
      const i = index++;
      const file = items[i];
      try {
        const entry = await worker(file);
        appendLog(entry);
        completed++;
        const elapsed = ((Date.now() - start) / 1000).toFixed(1);
        const pct = (((completed + failed) / items.length) * 100).toFixed(1);
        console.log(`[${elapsed}s] [${pct}%] ${path.basename(file)} → ${entry.url}`);
      } catch (err) {
        failed++;
        console.error(`FAIL ${path.basename(file)}: ${err.message}`);
      }
    }
  }

  await Promise.all(Array.from({ length: Math.min(concurrency, items.length) }, () => run()));
  return { completed, failed, elapsed: ((Date.now() - start) / 1000).toFixed(1) };
}

async function main() {
  const files = walkJPGs(path.resolve(SOURCE_DIR));
  const doneSet = loadDoneSet();
  const pending = SKIP_EXISTING ? files.filter((f) => !doneSet.has(f)) : files;

  console.log(`Source: ${path.resolve(SOURCE_DIR)}`);
  console.log(`Cloudinary folder: ${CLOUDINARY_FOLDER}`);
  console.log(`Total JPGs: ${files.length}`);
  console.log(`Already uploaded: ${files.length - pending.length}`);
  console.log(`Pending: ${pending.length}`);

  if (!pending.length) {
    console.log("Nothing to upload.");
    return;
  }

  const { completed, failed, elapsed } = await runPool(pending, CONCURRENCY, uploadOne);
  console.log(`Done in ${elapsed}s · success ${completed} · failed ${failed}`);
  console.log(`Log: ${LOG_FILE}`);
  if (failed) process.exitCode = 1;
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
