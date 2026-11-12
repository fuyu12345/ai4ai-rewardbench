import { readFileSync, writeFileSync, mkdirSync, copyFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { Script } from 'node:vm';
const root = resolve(import.meta.dirname, '..');
const read = p => readFileSync(resolve(root, p), 'utf8');
const dataset = JSON.parse(read('data/public-benchmark.json'));
const cases = JSON.parse(read('data/public-cases.json'));
const tasks = JSON.parse(read('data/public-tasks.json'));
const taskById = new Map(tasks.tasks.map(task => [task.pair_id, task]));
if (taskById.size !== dataset.pair_count || dataset.pairs.some(pair => !taskById.has(pair.pair_id))) throw new Error('Task detail coverage does not match the benchmark catalog');
for (const pair of dataset.pairs) pair.title = taskById.get(pair.pair_id).title;
const json = JSON.stringify({ dataset, cases, tasks }).replaceAll('<', '\\u003c');
const html = read('web/src/index.html')
  .replace('/* INLINE_STYLES */', () => read('web/src/styles.css'))
  .replace('/* INLINE_DATA */', () => `window.BENCHMARK = ${json};`)
  .replace('/* INLINE_APP */', () => read('web/src/app.js'));
for (const [, script] of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) new Script(script);
mkdirSync(resolve(root, 'dist'), { recursive: true });
writeFileSync(resolve(root, 'dist/index.html'), html);
writeFileSync(resolve(root, 'dist/public-benchmark.json'), JSON.stringify(dataset, null, 2) + '\n');
for (const name of ['public-cases.json', 'public-tasks.json']) copyFileSync(resolve(root, 'data', name), resolve(root, 'dist', name));
copyFileSync(resolve(root, 'docs/protocol.md'), resolve(root, 'dist/protocol.md'));
mkdirSync(resolve(root, 'dist/snapshots'), { recursive: true });
copyFileSync(resolve(root, 'data', dataset.original_snapshot.path), resolve(root, 'dist', dataset.original_snapshot.path));
console.log(`Built dist/index.html (${Math.round(Buffer.byteLength(html) / 1024)} KB), with inline styles, scripts and data.`);
