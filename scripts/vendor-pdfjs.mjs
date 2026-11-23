// Copies the PDF reader library (pdfjs-dist) from node_modules into static/vendor/.
// Usage: npm install && npm run vendor
import { copyFileSync, mkdirSync, readFileSync, rmSync } from "node:fs";

const pkg = JSON.parse(readFileSync("node_modules/pdfjs-dist/package.json", "utf8"));
const dest = `static/vendor/pdfjs-dist`;
rmSync(dest, { recursive: true, force: true });
mkdirSync(dest, { recursive: true });
for (const f of ["pdf.min.mjs", "pdf.worker.min.mjs"]) {
  copyFileSync(`node_modules/pdfjs-dist/build/${f}`, `${dest}/${f}`);
}
copyFileSync("node_modules/pdfjs-dist/LICENSE", `${dest}/LICENSE`);
console.log(`pdfjs-dist ${pkg.version} copied to ${dest}`);
