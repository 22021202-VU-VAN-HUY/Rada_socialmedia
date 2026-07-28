import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const targets = ["chromium", "firefox"];

await rm(resolve(root, "dist"), { recursive: true, force: true });

for (const target of targets) {
  const output = resolve(root, "dist", target);
  await mkdir(output, { recursive: true });
  await cp(resolve(root, "src"), output, { recursive: true });
  const manifest = await readFile(
    resolve(root, "manifests", `manifest.${target}.json`),
    "utf8",
  );
  await writeFile(resolve(output, "manifest.json"), manifest);
}

console.log(`Built: ${targets.map((target) => `dist/${target}`).join(", ")}`);
