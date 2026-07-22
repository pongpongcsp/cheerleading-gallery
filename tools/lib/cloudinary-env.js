const fs = require("fs");
const path = require("path");

function loadDotEnv() {
  const envPath = path.join(__dirname, "..", ".env");
  if (!fs.existsSync(envPath)) return;
  const text = fs.readFileSync(envPath, "utf8");
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq).trim();
    let value = trimmed.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (!(key in process.env)) process.env[key] = value;
  }
}

function loadCloudinary() {
  loadDotEnv();
  // eslint-disable-next-line global-require
  const cloudinary = require("cloudinary").v2;

  if (process.env.CLOUDINARY_URL) {
    cloudinary.config(true);
    return cloudinary;
  }

  const cloud_name = process.env.CLOUDINARY_CLOUD_NAME;
  const api_key = process.env.CLOUDINARY_API_KEY;
  const api_secret = process.env.CLOUDINARY_API_SECRET;

  if (!cloud_name || !api_key || !api_secret) {
    console.error(
      "Missing Cloudinary credentials. Set CLOUDINARY_URL or CLOUDINARY_CLOUD_NAME / CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET (see .env.example)."
    );
    process.exit(1);
  }

  cloudinary.config({ cloud_name, api_key, api_secret, secure: true });
  return cloudinary;
}

/** Insert a Cloudinary transformation segment into a delivery URL. */
function transformedUrl(secureUrl, transform) {
  if (!secureUrl || !transform) return secureUrl;
  const marker = "/upload/";
  const idx = secureUrl.indexOf(marker);
  if (idx === -1) return secureUrl;
  const before = secureUrl.slice(0, idx + marker.length);
  const after = secureUrl.slice(idx + marker.length);
  // Avoid double-inserting the same transform
  if (after.startsWith(transform + "/")) return secureUrl;
  return `${before}${transform}/${after}`;
}

module.exports = { loadCloudinary, transformedUrl, loadDotEnv };
