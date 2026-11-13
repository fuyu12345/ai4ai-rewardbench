(() => {
  'use strict';
  const data = window.BENCHMARK.runtime;
  const $ = selector => document.querySelector(selector);
  const buttons = [...document.querySelectorAll('[data-runtime-model]')];
  const panels = [...document.querySelectorAll('[data-runtime-panel]')];
  const escape = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const format = seconds => seconds >= 3600 ? `${(seconds / 3600).toFixed(2)} h` : seconds >= 60 ? `${(seconds / 60).toFixed(2)} min` : `${seconds.toFixed(2)} s`;
  const scopes = {complete:'Complete execution', training_only:'Training only', published_subtask:'One environment × seed'};
  function selectModel(id) {
    const model = data.models.find(item => item.id === id);
    if (!model) return;
    buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.runtimeModel === id)));
    panels.forEach(panel => { panel.hidden = panel.dataset.runtimePanel !== id; });
    $('#runtime-current').textContent = model.label;
    $('#runtime-table-caption').textContent = `${model.label} · measured median times`;
    for (const ext of ['png', 'svg']) $(`#runtime-${ext}`).href = `assets/runtime/${model.asset}.${ext}`;
    $('#runtime-values').innerHTML = data.benchmarks.map(bench => {
      const point = data.points.find(item => item.model === id && item.bench === bench.name);
      return `<tr><th scope="row">${escape(bench.name)}</th><td>${bench.pairs}</td><td>${format(bench.experiment_seconds)}</td><td>${format(point.judgment_seconds)}</td><td>${scopes[bench.scope]}</td></tr>`;
    }).join('');
  }
  buttons.forEach(button => button.addEventListener('click', () => selectModel(button.dataset.runtimeModel)));
  selectModel(data.models[0].id);
})();
