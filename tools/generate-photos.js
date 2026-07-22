#!/usr/bin/env node
/**
 * Build js/photos.js for cheerleading-gallery from Cloudinary folders.
 *
 * Reads tools/gallery-folders.json for folder → category mapping.
 * Emits responsive thumb + lightbox URLs (never raw 4000px originals).
 */

const fs = require("fs");
const path = require("path");
const { loadCloudinary, transformedUrl } = require("./lib/cloudinary-env");

const ROOT = path.join(__dirname, "..");
const CONFIG_PATH = path.join(__dirname, "gallery-folders.json");
const OUTPUT_PATH = path.join(ROOT, "js", "photos.js");

const THUMB_TRANSFORM = "c_limit,w_800,f_auto,q_auto";
const FULL_TRANSFORM = "c_limit,w_2000,f_auto,q_auto";

async function fetchAllFromFolder(cloudinary, folder) {
  let resources = [];
  let cursor = null;
  do {
    const params = { max_results: 500 };
    if (cursor) params.next_cursor = cursor;
    const res = await cloudinary.api.resources_by_asset_folder(folder, params);
    resources = resources.concat(res.resources || []);
    cursor = res.next_cursor;
    if (cursor) await new Promise((r) => setTimeout(r, 250));
  } while (cursor);
  return resources;
}

function titleFromPublicId(publicId, index) {
  const base = path.basename(publicId);
  const cleaned = base
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
    .trim();
  if (!cleaned || /^\d+(\s|$)/.test(cleaned) || /^DSC\d+/i.test(cleaned) || /^IMG\d+/i.test(cleaned)) {
    return `Photo ${String(index).padStart(2, "0")}`;
  }
  return cleaned;
}

function loadConfig() {
  if (!fs.existsSync(CONFIG_PATH)) {
    console.error(`Missing ${CONFIG_PATH}`);
    process.exit(1);
  }
  const config = JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8"));
  if (!Array.isArray(config) || !config.length) {
    console.error("gallery-folders.json must be a non-empty array");
    process.exit(1);
  }
  return config;
}

async function main() {
  const folders = loadConfig();
  const cloudinary = loadCloudinary();
  const photos = [];
  let id = 1;

  console.log("Building js/photos.js from Cloudinary folders...\n");

  for (const entry of folders) {
    const folder = entry.folder;
    process.stdout.write(`Fetching "${folder}"... `);
    try {
      const resources = await fetchAllFromFolder(cloudinary, folder);
      console.log(`${resources.length} assets`);

      let index = 0;
      for (const r of resources) {
        index += 1;
        const width = r.width || 800;
        const height = r.height || 1200;
        const title = entry.titlePrefix
          ? `${entry.titlePrefix} — ${titleFromPublicId(r.public_id, index)}`
          : titleFromPublicId(r.public_id, index);

        photos.push({
          id: id++,
          title,
          category: entry.category,
          categoryLabel: entry.categoryLabel,
          url: transformedUrl(r.secure_url, FULL_TRANSFORM),
          thumbUrl: transformedUrl(r.secure_url, THUMB_TRANSFORM),
          width,
          height,
          tags: Array.isArray(entry.tags) ? entry.tags : [],
        });
      }
    } catch (err) {
      console.log(`ERROR: ${err.message}`);
    }
  }

  if (!photos.length) {
    console.error("No photos generated. Check credentials, folder names, and rate limits.");
    process.exit(1);
  }

  const body = `const allPhotos = ${JSON.stringify(photos, null, 2)};\n`;
  fs.writeFileSync(OUTPUT_PATH, body, "utf8");

  const counts = {};
  for (const p of photos) counts[p.categoryLabel] = (counts[p.categoryLabel] || 0) + 1;

  console.log(`\nWrote ${photos.length} photos → ${path.relative(ROOT, OUTPUT_PATH)}`);
  for (const [label, count] of Object.entries(counts)) {
    console.log(`  ${label}: ${count}`);
  }
  console.log("\nCommit js/photos.js (metadata only) and push to publish.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
