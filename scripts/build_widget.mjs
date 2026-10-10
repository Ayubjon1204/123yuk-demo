import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(fileURLToPath(new URL("..", import.meta.url)));
const source = join(root, "frontend", "support-agent", "widget.js");
const output = join(root, "zavod", "ai-support", "widget.js");
await mkdir(dirname(output), { recursive: true });
await writeFile(output, await readFile(source));
console.log("Standalone widget copied to the Zavod Pages asset path.");
