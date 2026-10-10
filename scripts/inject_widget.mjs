import { readdir, readFile, writeFile } from "node:fs/promises";
import { join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(fileURLToPath(new URL("..", import.meta.url)));
const zavod = join(root, "zavod");
const tag = '<script defer src="/123yuk-demo/zavod/ai-support/widget.js" data-api-base-url=""></script>';
const remove = process.argv.includes("--remove");

async function htmlFiles(directory) {
  const found = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) found.push(...await htmlFiles(path));
    else if (entry.isFile() && entry.name.endsWith(".html")) found.push(path);
  }
  return found;
}

const files = await htmlFiles(zavod);
for (const path of files) {
  const before = await readFile(path, "utf8");
  const newline = before.includes("\r\n") ? "\r\n" : "\n";
  const pattern = /<script\b[^>]*\/zavod\/ai-support\/widget\.js[^>]*><\/script>\s*/g;
  const matches = before.match(pattern) || [];
  if (matches.length > 1) throw new Error(`Duplicate widget launcher in ${relative(root, path)}`);
  const after = remove
    ? before.replace(/^[ \t]*<script\b[^>]*\/zavod\/ai-support\/widget\.js[^>]*><\/script>\r?\n/gm, "")
    : matches.length === 1 ? before : before.replace(/<\/body>/i, `${tag}${newline}    </body>`);
  if (!remove && after === before && !matches.length) throw new Error(`No closing body tag in ${relative(root, path)}`);
  if (after !== before) await writeFile(path, after, "utf8");
}
console.log(`Widget ${remove ? "removed from" : "installed in"} ${files.length} Zavod HTML files.`);
