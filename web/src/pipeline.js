(() => {
  'use strict';
  const host = document.querySelector('#pipeline');
  if (!host) return;
  const $ = s => host.querySelector(s);
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const flow = [
      ['Discover', 'Start with real research attempts.', 'Collect public trajectories and available local runs for each benchmark. Keep the source identity, task context, and original records together.', 'INPUT', 'Public traces + available local runs'],
      ['Organize', 'One hierarchy. Different kinds of runs.', 'Organize each source as Bench → Task → Run → Unit. A run may be a search tree, a complete agent session, or a single-step rollout; one run can produce several units.', 'STRUCTURE', 'Bench / Task / Run / Unit'],
      ['Extract & audit', 'Recover the algorithm and how it was made.', 'A Unit joins the generation process (edge), the algorithm artifact (node), and its real execution feedback. Audit completeness and links, screen the records, and preserve missing information explicitly.', 'OUTPUT', 'Screened units · no pairs yet'],
      ['Curate pairs', 'Find comparisons worth judging.', 'Codex-6 Astra follows the pair-curation skill to inspect each benchmark’s tasks, runs, and units. It identifies meaningful candidate differences under a shared task and decision rule, with evidence for the proposed label.', 'OUTPUT', 'Candidate pairs + review evidence'],
      ['Human review', 'Make the evidence accountable.', 'People review the task, candidate differences, input sufficiency, comparison rule, and label evidence. Revise or reject weak comparisons; retain the pairs that pass review.', 'GATE', 'Review → revise / reject / approve'],
      ['Freeze', 'A golden collection for each benchmark.', 'Freeze reviewed pairs with their task conditions and version. Separate the public judge inputs from private reference labels and supporting evidence.', 'OUTPUT', 'Versioned golden pairs, per benchmark']
  ];
  const state = {step:0, playing:false, visible:false, seen:false};
  let timer;
  const steps = $('#pipeline-steps');
  function schedule() {
    clearTimeout(timer);
    if (state.playing && state.visible && !document.hidden) timer = setTimeout(() => {
      if (state.step < 5) { state.step++; if (state.step === 5) state.playing = false; render(); }
    }, 6800);
  }
  function render() {
    const item = flow[state.step];
    steps.innerHTML = flow.map((s,i) => `<button type="button" data-step="${i}" aria-label="Step ${i+1}: ${s[0]}" aria-current="${i===state.step?'step':'false'}" class="${i<state.step?'is-complete':''}"><span>${String(i+1).padStart(2,'0')}</span>${s[0]}</button>`).join('');
    $('#pipeline-phase').textContent = state.step <= 2 ? '01 / UNIT EXTRACTION & SCREENING' : '02 / PAIR CURATION & REVIEW';
    $('#pipeline-boundary').textContent = state.step <= 2 ? 'No pairs are constructed in this stage.' : 'Pair construction begins after unit screening.';
    $('#pipeline-scene').innerHTML = window.renderPipelineScene(state.step);
    $('#pipeline-caption').setAttribute('aria-live', state.playing ? 'off' : 'polite');
    $('#pipeline-title').textContent = item[1];
    $('#pipeline-description').textContent = item[2];
    $('#pipeline-output-label').textContent = item[3];
    $('#pipeline-output').textContent = item[4];
    $('#pipeline-play').textContent = state.playing ? 'Ⅱ Pause' : state.step === 5 ? '↻ Replay' : '▶ Play';
    $('#pipeline-play').setAttribute('aria-label',state.playing?'Pause animation':state.step===5?'Replay animation':'Play animation');
    $('#pipeline-previous').disabled = state.step === 0;
    $('#pipeline-next').disabled = state.step === 5;
    $('#pipeline-status').textContent = `${state.playing?'Playing':'Step'} ${String(state.step+1).padStart(2,'0')} / 06`;
    host.classList.toggle('pipeline-paused', !state.playing);
    schedule();
  }
  function manualStep(step) { state.playing=false;state.seen=true;state.step=Math.max(0,Math.min(5,step));render(); }
  steps.addEventListener('click',event => {const b=event.target.closest('[data-step]');if(b) {manualStep(Number(b.dataset.step));steps.querySelector(`[data-step="${state.step}"]`).focus({preventScroll:true});}});
  steps.addEventListener('keydown',event => {
    if (!['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
    event.preventDefault();manualStep(event.key==='Home'?0:event.key==='End'?5:state.step+(event.key==='ArrowRight'?1:-1));
    steps.querySelector(`[data-step="${state.step}"]`).focus({preventScroll:true});
  });
  $('#pipeline-previous').addEventListener('click',() => manualStep(state.step-1));
  $('#pipeline-next').addEventListener('click',() => manualStep(state.step+1));
  $('#pipeline-play').addEventListener('click',() => {state.seen=true;state.playing=!state.playing;if(state.playing&&state.step===5)state.step=0;render();});
  host.addEventListener('focusin',event => {
    if (!state.playing || event.target.id === 'pipeline-play') return;
    state.playing = false; state.seen = true; clearTimeout(timer);
    $('#pipeline-play').textContent = '▶ Play';
    $('#pipeline-play').setAttribute('aria-label','Play animation');
    $('#pipeline-status').textContent = `Step ${String(state.step+1).padStart(2,'0')} / 06`;
    host.classList.add('pipeline-paused');
  });
  document.addEventListener('visibilitychange',schedule);
  reduced.addEventListener('change',() => {if(reduced.matches){state.playing=false;render();}});
  new IntersectionObserver(entries => {
    state.visible=entries[0].isIntersecting;
    if(state.visible&&!state.seen){state.seen=true;state.playing=!reduced.matches;render();}else schedule();
  },{threshold:0.15}).observe(host);
  render();
})();
