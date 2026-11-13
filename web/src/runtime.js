(() => {
  'use strict';
  const data = window.BENCHMARK.runtime;
  const $ = selector => document.querySelector(selector);
  const buttons = [...document.querySelectorAll('[data-runtime-model]')];
  const panels = [...document.querySelectorAll('[data-runtime-panel]')];
  function selectModel(id) {
    const model = data.models.find(item => item.id === id);
    if (!model) return;
    buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.runtimeModel === id)));
    panels.forEach(panel => { panel.hidden = panel.dataset.runtimePanel !== id; });
    $('#runtime-current').textContent = model.label;

  }
  buttons.forEach(button => button.addEventListener('click', () => selectModel(button.dataset.runtimeModel)));
  selectModel(data.models[0].id);
})();
