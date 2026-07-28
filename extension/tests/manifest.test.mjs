import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);

for (const target of ["chromium", "firefox"]) {
  test(`${target} manifest contains all platform collectors`, async () => {
    const manifest = JSON.parse(
      await readFile(new URL(`manifests/manifest.${target}.json`, root), "utf8"),
    );
    assert.equal(manifest.manifest_version, 3);
    assert.ok(manifest.permissions.includes("cookies"));
    assert.deepEqual(
      manifest.content_scripts[0].js.slice(1, 4),
      [
        "collectors/facebook.js",
        "collectors/tiktok.js",
        "collectors/threads.js",
      ],
    );
    for (const domain of ["facebook.com", "tiktok.com", "threads.net"]) {
      assert.ok(
        manifest.host_permissions.some((permission) =>
          permission.includes(domain),
        ),
      );
    }
    assert.ok(
      manifest.content_scripts.some((script) =>
        script.js.includes("website.js"),
      ),
    );
  });
}
