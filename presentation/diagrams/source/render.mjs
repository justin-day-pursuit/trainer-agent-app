import { createRequire } from "module";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const dir = new URL("./", import.meta.url).pathname;
const names = process.argv.slice(2);
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2 });
for (const n of names) {
  await p.goto("file://" + dir + n + ".html", { waitUntil: "networkidle" });
  await p.evaluate(() => document.fonts.ready);
  await p.reload({ waitUntil: "networkidle" }); await p.evaluate(() => document.fonts.ready);
  await p.screenshot({ path: dir + n + ".png" });
  await p.pdf({ path: dir + n + ".pdf", width: "1920px", height: "1080px", printBackground: true });
  const over = await p.evaluate(() => [...document.querySelectorAll("body *")].filter(e => { const r = e.getBoundingClientRect(); return r.width && (r.right > 1921 || r.bottom > 1081); }).map(e => e.className || e.tagName).slice(0, 5));
  console.log(n, "overflow:", JSON.stringify(over));
}
await b.close();
