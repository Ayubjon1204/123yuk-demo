const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const output = path.join(root, "dist", "zavod-preview");
const apiBase = process.env.PREVIEW_API_BASE_URL;
if (!apiBase) throw new Error("PREVIEW_API_BASE_URL is required");

const apiUrl = new URL(apiBase);
if (apiUrl.protocol !== "https:" || apiUrl.pathname !== "/" || apiUrl.search || apiUrl.hash || apiUrl.username || apiUrl.password) {
  throw new Error("PREVIEW_API_BASE_URL must be a public HTTPS origin");
}

const source = path.join(root, "zavod");
const publishRoot = path.join(output, "123yuk-demo");
const htmlFiles = [];
function findHtml(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) findHtml(absolute);
    else if (entry.name.endsWith(".html")) htmlFiles.push(absolute);
  }
}

fs.rmSync(output, { recursive: true, force: true });
findHtml(source);
for (const file of htmlFiles) {
  const relative = path.relative(source, file);
  const destination = path.join(publishRoot, "zavod", relative);
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  const html = fs.readFileSync(file, "utf8");
  const widgetTag = 'src="/123yuk-demo/zavod/ai-support/widget.js" data-api-base-url=""';
  if (html.split(widgetTag).length !== 2) throw new Error(`Expected one widget tag in ${relative}`);
  fs.writeFileSync(
    destination,
    html.replace(widgetTag, `src="/123yuk-demo/frontend/support-agent/widget.js" data-api-base-url="${apiUrl.origin}"`),
  );
}

fs.cpSync(path.join(source, "assets"), path.join(publishRoot, "zavod", "assets"), { recursive: true });
fs.copyFileSync(path.join(source, "favicon.svg"), path.join(publishRoot, "zavod", "favicon.svg"));
const widgetOutput = path.join(publishRoot, "frontend", "support-agent", "widget.js");
fs.mkdirSync(path.dirname(widgetOutput), { recursive: true });
fs.copyFileSync(path.join(root, "frontend", "support-agent", "widget.js"), widgetOutput);

const dashboard = path.join(publishRoot, "zavod", "dashboard", "index.html");
if (!fs.existsSync(dashboard) || htmlFiles.length === 0) throw new Error("Unexpected Zavod preview source layout");
for (const file of htmlFiles) {
  const relative = path.relative(source, file);
  const html = fs.readFileSync(path.join(publishRoot, "zavod", relative), "utf8");
  for (const [, url] of html.matchAll(/(?:src|href)="(\/[^/][^"]*)"/g)) {
    if (!url.startsWith("/123yuk-demo/")) throw new Error(`Unexpected local path ${url} in ${relative}`);
    const resource = path.join(output, url.slice(1));
    if (!fs.existsSync(resource)) throw new Error(`Missing preview resource ${url}`);
  }
}
if (fs.existsSync(path.join(output, "backend")) || fs.existsSync(path.join(output, "admin"))) {
  throw new Error("Preview output contains an unrelated application or backend");
}
process.stdout.write(`Built ${htmlFiles.length} Zavod routes at ${path.relative(root, publishRoot)}\n`);
