(() => {
  'use strict';
  const { dataset: data, cases: caseData } = window.BENCHMARK;
  const $ = s => document.querySelector(s);
  const $$ = s => [...document.querySelectorAll(s)];
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const percent = n => (n * 100).toFixed(2);
  const millions = n => n == null ? '—' : `${(n / 1e6).toFixed(2)}M`;
  const state = { mode: 'all', asc: false, caseId: caseData.cases[0]?.id, detail: 'evidence', model: caseData.models?.[0] || 'gpt-6.1-sol', repeat: 1, layer: 'all', page: 1 };
  const providers = { 'gemini-4-argon': 'Gemini', 'gpt-6.1-sol': 'GPT', 'hy4': 'HY', 'claude-sonnet-5-5': 'Claude', 'deepseek-v4.1-flash': 'DeepSeek', 'glm-5.3-flash': 'GLM', 'qwen3.8-flash': 'Qwen', 'kimi-k3.1-pro': 'Kimi', 'kimi-k2.6': 'Kimi' };
  const scoreKey = () => state.mode === 'all' ? 'question_equal_weight_accuracy' : `${state.mode}_accuracy`;
  function boardRows() {
    const key = scoreKey();
    const sorted = [...data.leaderboard].sort((a,b) => b[key] - a[key] || a.rank - b.rank);
    let rank = 1;
    const rows = sorted.map((row,i) => { if(i && Math.abs(row[key] - sorted[i-1][key]) > 1e-12) rank = i+1; return {...row, displayRank: rank}; });
    return state.asc ? rows.reverse() : rows;
  }
  function renderLeaderboard() {
    const key = scoreKey();
    $('#leaderboard-body').innerHTML = boardRows().map(row => `<tr><td>${String(row.displayRank).padStart(2,'0')}</td><td><span class="model-name">${escape(row.model)}${row.model.startsWith('claude') ? '<sup>*</sup>':''}</span><span class="model-provider">${escape(providers[row.model] || row.model)} · DMX</span></td><td class="score-cell"><div class="score-content"><div class="score-bar" aria-hidden="true"><i style="width:${row[key]*100}%"></i></div><span class="score-value">${percent(row[key])}<small>%</small></span></div></td><td class="numeric">${millions(row.input_tokens_known)}</td><td class="numeric">${millions(row.output_tokens_known)}</td><td class="numeric">${Number(row.agent_mean_model_turns_per_planned_cell).toFixed(1)}</td></tr>`).join('');
    const n = state.mode === 'all' ? data.pair_count : data.modes[state.mode];
    $('#board-context').textContent = `Question-weighted accuracy · ${n} ${state.mode === 'all' ? '' : state.mode + ' '}pairs · higher is better · resource columns cover the full run`;
    $$('[data-board]').forEach(b => { const active = b.dataset.board === state.mode; b.classList.toggle('active',active); b.setAttribute('aria-pressed',String(active)); });
    $('#sort-score').innerHTML = `ACCURACY <span>${state.asc?'↑':'↓'}</span>`;
    $('#sort-score').setAttribute('aria-label',`Sort accuracy ${state.asc?'descending':'ascending'}`);
    $('.score-heading').setAttribute('aria-sort',state.asc?'ascending':'descending');
    const baseline = data.mode_baselines?.[state.mode];
    if (baseline) {
      $('#baseline-uniform').innerHTML = `${percent(baseline.uniform_three)}<span>%</span>`;
      $('#baseline-ab').innerHTML = `${percent(baseline.random_ab)}<span>%</span>`;
      $('#baseline-fixed').innerHTML = `${percent(baseline.always_a)}<span>%</span>`;
      const labels = baseline.gold_distribution;
      const below = data.leaderboard.filter(r => r[key] < baseline.always_a).length;
      $('#baseline-note').textContent = `${below} of 9 models score below the always-A baseline on ${state.mode === 'all' ? 'this fixed-order development collection' : `the ${state.mode} subset`}. Gold distribution: A ${labels.A} / B ${labels.B} / tie ${labels.tie}.`;
    }
  }
  $$('[data-board]').forEach(b => b.addEventListener('click',()=>{state.mode=b.dataset.board;state.asc=false;renderLeaderboard();}));
  $('#sort-score').addEventListener('click',()=>{state.asc=!state.asc;renderLeaderboard();});
  function download(name, contents, mime) {
    const url=URL.createObjectURL(new Blob([contents],{type:mime}));
    const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    $('#toast').textContent='Download ready';$('#toast').classList.add('visible');setTimeout(()=>$('#toast').classList.remove('visible'),2200);
  }
  $('#download-scores').addEventListener('click',()=>{
    const header=['rank','model','mode','question_equal_weight_accuracy','input_tokens_all_attempts','output_tokens_all_attempts','agent_model_turns_per_315_planned_cells','scoring_note'];
    const rows=boardRows().map(r=>[r.displayRank,r.model,state.mode,r[scoreKey()],r.input_tokens_known,r.output_tokens_known,r.agent_mean_model_turns_per_planned_cell,r.model.startsWith('claude')&&state.mode!=='reasoning'?'AAB15-P016 avg@2 (rep1 rep3); all other pairs avg@3':'avg@3 per pair']);
    const csv=[header,...rows].map(row=>row.map(v=>`"${String(v).replaceAll('"','""')}"`).join(',')).join('\r\n');
    download(`ai4ai-rewardbench-golden2-${state.mode}.csv`,csv,'text/csv;charset=utf-8');
  });
  const maxBench=Math.max(...data.benches.map(b=>b.pairs));
  $('#bench-bars').innerHTML=data.benches.map(b=>`<button class="bench-row" data-bench="${escape(b.bench)}" aria-label="Browse ${escape(b.bench)}: ${b.pairs} pairs"><span class="bench-name">${escape(b.bench)}</span><span class="bench-track" aria-hidden="true"><i style="width:${b.pairs/maxBench*100}%"></i></span><span class="bench-count">${b.pairs}</span></button>`).join('');
  $('#bench-filter').innerHTML+=[...data.benches].sort((a,b)=>a.bench.localeCompare(b.bench)).map(b=>`<option value="${escape(b.bench)}">${escape(b.bench)}</option>`).join('');
  function explorer(view) {
    $$('[data-explorer]').forEach(b=>{const active=b.dataset.explorer===view;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
    $('#cases-view').hidden=view!=='cases';$('#catalog-view').hidden=view!=='catalog';
    if(view==='catalog')renderCatalog();
  }
  $$('[data-explorer]').forEach(b=>b.addEventListener('click',()=>explorer(b.dataset.explorer)));
  $('#catalog-shortcut').addEventListener('click',()=>{state.page=1;$('#task-search').value='';$('#mode-filter').value='all';$('#bench-filter').value='all';explorer('catalog');});
  $$('.bench-row').forEach(b=>b.addEventListener('click',()=>{
    $('#bench-filter').value=b.dataset.bench;$('#mode-filter').value='all';$('#task-search').value='';state.page=1;explorer('catalog');$('#explorer').scrollIntoView({behavior:'smooth'});
  }));
  function renderCatalog() {
    const search=$('#task-search').value.trim().toLowerCase();
    const mode=$('#mode-filter').value, bench=$('#bench-filter').value;
    const filtered=data.pairs.filter(p=>(mode==='all'||p.mode===mode)&&(bench==='all'||p.bench===bench)&&[p.pair_id,p.title,p.bench].join(' ').toLowerCase().includes(search));
    const pages=Math.max(1,Math.ceil(filtered.length/10));state.page=Math.min(state.page,pages);
    $('#catalog-count').textContent=`${filtered.length} of ${data.pair_count} pairs · metadata catalog · complete task packages are not included in v0.1`;
    $('#catalog-list').innerHTML=filtered.slice((state.page-1)*10,state.page*10).map(p=>`<div class="catalog-item"><span class="catalog-id">${escape(p.pair_id)}</span><span class="catalog-title">${escape(p.title)}${p.input_cue_flag?'<span class="catalog-cue">Input cue: source retains performance self-report</span>':''}</span><span class="catalog-bench">${escape(p.bench)}</span><span class="catalog-mode">${p.mode==='agent'?'Agent':'Reasoning'}</span></div>`).join('')||'<p class="empty-state">No matching tasks. Try another keyword or clear the filters.</p>';
    $('#page-number').textContent=`${state.page} / ${pages}`;$('#prev-page').disabled=state.page===1;$('#next-page').disabled=state.page===pages;
  }
  ['task-search','mode-filter','bench-filter'].forEach(id=>$('#'+id).addEventListener(id==='task-search'?'input':'change',()=>{state.page=1;renderCatalog();}));
  $('#prev-page').addEventListener('click',()=>{state.page--;renderCatalog();});$('#next-page').addEventListener('click',()=>{state.page++;renderCatalog();});
  $('#case-count').textContent=caseData.cases.length;
  function renderCase() {
    const c=caseData.cases.find(c=>c.id===state.caseId);
    if(!c)return;
    $('#case-picker').innerHTML=caseData.cases.map(x=>`<button class="case-pick ${x.id===c.id?'active':''}" data-case="${escape(x.id)}" aria-pressed="${x.id===c.id}"><span class="case-kicker"><span>${x.mode.toUpperCase()}</span><span>${escape(x.bench)}</span></span><strong>${escape(x.display_title || x.title)}</strong><span class="case-id">${escape(x.pair_id)} ↗</span></button>`).join('');
    $('#case-detail').innerHTML=`<div class="case-top"><div><span class="mode-badge">${c.mode.toUpperCase()} / ${escape(c.pair_id)}</span><h3>${escape(c.display_title || c.title)}</h3><p>${escape(c.task_summary)}</p><div class="case-rule"><span class="tiny-label">DECISION RULE</span><p>${escape(c.decision_rule)}</p></div><div class="case-conditions">${(c.conditions||[]).map(x=>`<span>${escape(x)}</span>`).join('')}</div></div><div><div class="candidate-comparison"><div class="candidate-block"><b>A</b><p>${escape(c.candidates.A)}</p></div><div class="candidate-block"><b>B</b><p>${escape(c.candidates.B)}</p></div></div><div class="case-evidence"><div class="detail-tabs" role="group" aria-label="Case detail"><button data-detail="evidence" class="${state.detail==='evidence'?'active':''}" aria-pressed="${state.detail==='evidence'}">Source evidence</button><button data-detail="trace" class="${state.detail==='trace'?'active':''}" aria-pressed="${state.detail==='trace'}">Evaluation trace <span>↗</span></button></div><div id="detail-content"></div></div></div></div><p class="case-disclosure">${escape((c.limitations||[]).join(' '))} Only curated input summaries and observed tool actions are shown; full raw logs are not bundled.</p>`;
    $$('[data-case]').forEach(b=>b.addEventListener('click',()=>{state.caseId=b.dataset.case;state.layer='all';renderCase();}));
    $$('[data-detail]').forEach(b=>b.addEventListener('click',()=>{state.detail=b.dataset.detail;renderCase();}));
    if(state.detail==='evidence') {
      $('#detail-content').innerHTML=c.evidence.map(e=>`<div class="evidence-row"><span class="evidence-source">${escape(e.source)} · source lines ${e.line_start}–${e.line_end}</span><h4>${escape(e.label || 'Source evidence')}</h4><p>${escape(e.summary || e.text)}</p></div>`).join('');
    } else renderTrace(c);
  }
  function renderTrace(c) {
    const models=[...new Set(c.traces.map(t=>t.model))];
    if(!models.includes(state.model))state.model=models[0];
    const trace=c.traces.find(t=>t.model===state.model&&t.repeat===state.repeat) || c.traces[0];
    const layers=trace.layers||[];
    if(state.layer!=='all'&&!layers.some(l=>l.id===state.layer))state.layer='all';
    const activeLayer=layers.find(l=>l.id===state.layer);
    const events=trace.events.filter(e=>state.layer==='all'||e.layer===state.layer);
    $('#detail-content').innerHTML=`<div class="trace-controls"><label for="trace-model">Model</label><select id="trace-model">${models.map(m=>`<option value="${escape(m)}" ${m===state.model?'selected':''}>${escape(m)}</option>`).join('')}</select><label for="trace-repeat">Repeat</label><select id="trace-repeat">${[1,2,3].map(r=>`<option value="${r}" ${r===state.repeat?'selected':''}>${r} / 3</option>`).join('')}</select><label for="trace-layer">Layer</label><select id="trace-layer"><option value="all">All layers (${layers.length})</option>${layers.map(l=>`<option value="${escape(l.id)}" ${l.id===state.layer?'selected':''}>${escape(l.label)}</option>`).join('')}</select></div><div class="trace-info">${activeLayer?`<span>LAYER · ${escape(activeLayer.raw_status).toUpperCase()} · ${activeLayer.selected?'SELECTED':'NOT SELECTED'}</span>`:''}<span>MERGED STATUS · ${escape(trace.status).toUpperCase()}</span><span>${trace.answer?`PREDICTION · ${escape(trace.answer)}`:'NO ACCEPTED ANSWER'}</span><span>${trace.accepted_turn?`ACCEPTED TURN · ${trace.accepted_turn}`:'EXCLUDED FROM SCORING'}</span></div><div class="trace-events">${events.map((e,i)=>`<div class="trace-event"><span class="trace-index">${e.turn ?? String(i+1).padStart(2,'0')}</span><div><h4>${escape(e.title)}</h4><span class="event-layer">${escape(layers.find(l=>l.id===e.layer)?.label || e.layer || '')}</span><p>${escape(e.detail)}</p>${e.tools?.length?`<details class="tool-details"><summary>Inspect ${e.tools.length} tool call${e.tools.length===1?'':'s'} +</summary><pre>${escape(e.tools.map(t=>`${t.name}(${JSON.stringify(t.arguments)})${t.error?' · tool error':''}`).join('\n'))}</pre></details>`:''}</div></div>`).join('')}</div><p class="trace-caption">Model predictions are not reference labels. Turns retain their original numbers. Tool-call arguments are inspected metadata; model reasoning and raw provider payloads are not displayed.</p>`;
    $('#trace-model').addEventListener('change',e=>{state.model=e.target.value;state.layer='all';renderTrace(c);});
    $('#trace-repeat').addEventListener('change',e=>{state.repeat=Number(e.target.value);state.layer='all';renderTrace(c);});
    $('#trace-layer').addEventListener('change',e=>{state.layer=e.target.value;renderTrace(c);});
  }
  $('#resource-body').innerHTML=data.leaderboard.map(r=>`<tr><td>${escape(r.model)}</td><td class="numeric">${millions(r.cached_input_tokens_known)}</td><td class="numeric">${r.agent_model_turns.toLocaleString('en-US')}</td><td class="numeric">${r.agent_tool_rounds.toLocaleString('en-US')}</td><td class="numeric">${r.agent_tool_calls.toLocaleString('en-US')}</td><td class="numeric">${r.api_request_attempts.toLocaleString('en-US')}</td><td class="numeric">${r.reported_cost_cny==null?'Unknown':r.reported_cost_cny.toFixed(2)}</td></tr>`).join('');
  renderLeaderboard();renderCatalog();renderCase();
})();
