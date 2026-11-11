import { readFileSync, writeFileSync, mkdirSync, copyFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { Script } from 'node:vm';
const root = resolve(import.meta.dirname, '..');
const read = p => readFileSync(resolve(root, p), 'utf8');
const dataset = JSON.parse(read('data/public-benchmark.json'));
const cases = JSON.parse(read('data/public-cases.json'));
const json = JSON.stringify({ dataset, cases }).replaceAll('<', '\\u003c');
const html = read('web/src/index.html')
  .replace('/* INLINE_STYLES */', () => read('web/src/styles.css'))
  .replace('/* INLINE_DATA */', () => `window.BENCHMARK = ${json};`)
  .replace('/* INLINE_APP */', () => read('web/src/app.js'));
for (const [, script] of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) new Script(script);
mkdirSync(resolve(root, 'dist'), { recursive: true });
writeFileSync(resolve(root, 'dist/index.html'), html);
for (const name of ['public-benchmark.json', 'public-cases.json']) copyFileSync(resolve(root, 'data', name), resolve(root, 'dist', name));
copyFileSync(resolve(root, 'docs/protocol.md'), resolve(root, 'dist/protocol.md'));
console.log(`Built dist/index.html (${Math.round(Buffer.byteLength(html) / 1024)} KB), with inline styles, scripts and data.`);
