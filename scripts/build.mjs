import { readFileSync, writeFileSync, mkdirSync, copyFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { Script } from 'node:vm';
const root = resolve(import.meta.dirname, '..');
const read = p => readFileSync(resolve(root, p), 'utf8');
const dataset = JSON.parse(read('data/public-benchmark.json'));
const cases = JSON.parse(read('data/public-cases.json'));
const tasks = JSON.parse(read('data/public-tasks.json'));
const runtime = JSON.parse(read('data/public-runtime.json'));
const escape = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const runtimeCharts = runtime.models.map((model, index) => {
  let svg = read(`docs/assets/runtime/${model.asset}.svg`);
  svg = svg.slice(svg.indexOf('<svg')).replace(/<metadata>[\s\S]*?<\/metadata>/, '');
  svg = svg.replace('width="1080pt" height="648pt" viewBox="0 0 1080 648"', 'width="1080" height="380" viewBox="0 170 1080 380"');
  // Each inline SVG owns its glyphs and clip paths, including in hidden panels.
  svg = svg.replace(/\bid="([^"]+)"/g, (_, id) => `id="runtime-${index}-${id}"`)
    .replace(/(href="#|url\(#)([^"\)]+)/g, (_, start, id) => `${start}runtime-${index}-${id}`)
    .replace('<svg ', `<svg role="img" aria-label="${escape(model.label)}: experiment and judgment times for six selected typical benchmarks" `)
    .replace('*{stroke-linejoin:', '.runtime-chart svg *{stroke-linejoin:');
  return `<div class="runtime-panel" data-runtime-panel="${escape(model.id)}"${index ? ' hidden' : ''}>${svg}</div>`;
}).join('\n');
const taskById = new Map(tasks.tasks.map(task => [task.pair_id, task]));
if (taskById.size !== dataset.pair_count || dataset.pairs.some(pair => !taskById.has(pair.pair_id))) throw new Error('Task detail coverage does not match the benchmark catalog');
for (const pair of dataset.pairs) pair.title = taskById.get(pair.pair_id).title;
const json = JSON.stringify({ dataset, cases, tasks, runtime }).replaceAll('<', '\\u003c');
const html = read('web/src/index.html')
  .replace('/* INLINE_STYLES */', () => [read('web/src/styles.css'), read('web/src/runtime.css')].join('\n'))
  .replace('<!-- INLINE_RUNTIME_CHARTS -->', () => runtimeCharts)
  .replace('/* INLINE_DATA */', () => `window.BENCHMARK = ${json};`)
  .replace('/* INLINE_APP */', () => [read('web/src/app.js'), read('web/src/runtime.js')].join('\n'));
for (const [, script] of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) new Script(script);
mkdirSync(resolve(root, 'dist'), { recursive: true });
writeFileSync(resolve(root, 'dist/index.html'), html);
writeFileSync(resolve(root, 'dist/public-benchmark.json'), JSON.stringify(dataset, null, 2) + '\n');
for (const name of ['public-cases.json', 'public-tasks.json', 'public-runtime.json', 'public-runtime.csv']) copyFileSync(resolve(root, 'data', name), resolve(root, 'dist', name));
mkdirSync(resolve(root, 'dist/assets/runtime'), { recursive: true });
for (const model of runtime.models) for (const ext of ['svg', 'png']) {
  const filename = `${model.asset}.${ext}`;
  copyFileSync(resolve(root, 'docs/assets/runtime', filename), resolve(root, 'dist/assets/runtime', filename));
}
copyFileSync(resolve(root, 'docs/protocol.md'), resolve(root, 'dist/protocol.md'));
mkdirSync(resolve(root, 'dist/snapshots'), { recursive: true });
copyFileSync(resolve(root, 'data', dataset.original_snapshot.path), resolve(root, 'dist', dataset.original_snapshot.path));
console.log(`Built dist/index.html (${Math.round(Buffer.byteLength(html) / 1024)} KB), with inline styles, scripts and data.`);
