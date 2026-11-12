(() => {
  'use strict';
  const { dataset: data, cases: caseData, tasks: taskData } = window.BENCHMARK;
  const $ = selector => document.querySelector(selector);
  const $$ = selector => [...document.querySelectorAll(selector)];
  const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const percent = value => (value * 100).toFixed(2);
  const millions = value => value == null ? '—' : `${(value / 1e6).toFixed(2)}M`;
  const number = value => value == null ? '—' : value.toLocaleString('en-US');
  const paragraphs = value => String(value ?? '').split(/\n\s*\n/).filter(Boolean).map(text => `<p>${escape(text)}</p>`).join('');
  const tasks = new Map(taskData.tasks.map(task => [task.pair_id, task]));
  const state = { mode:'all', asc:false, caseId:caseData.cases[0]?.id, detail:'trace', model:caseData.models?.[0] || 'gpt-6.1-sol', repeat:1, layer:'all', page:1 };
  const scoreKey = () => state.mode === 'all' ? 'question_equal_weight_accuracy' : `${state.mode}_accuracy`;
  const configLabel = row => row.config_label === 'xhigh' ? 'xhigh reasoning effort' : 'default setting';
  const modelLabel = model => {
    const row = data.leaderboard.find(row => row.model === model);
    return `${model} · ${row?.config_label || 'default'}`;
  };

  function boardRows() {
    const key = scoreKey();
    const sorted = [...data.leaderboard].sort((a,b) => b[key] - a[key] || a.rank - b.rank);
    let rank = 1;
    const rows = sorted.map((row,index) => {
      if (index && Math.abs(row[key] - sorted[index-1][key]) > 1e-12) rank = index + 1;
      return {...row, displayRank:rank};
    });
    return state.asc ? rows.reverse() : rows;
  }
  function renderLeaderboard() {
    const key = scoreKey();
    $('#leaderboard-body').innerHTML = boardRows().map(row => `<tr class="${row.displayRank===1?'top-ranked':''}"><td>${String(row.displayRank).padStart(2,'0')}</td><td><span class="model-name">${escape(row.model)}${row.model.startsWith('claude')?'<sup>*</sup>':''}</span><span class="model-provider">${escape(configLabel(row))}</span></td><td class="score-cell"><div class="score-content"><div class="score-bar" aria-hidden="true"><i style="width:${row[key]*100}%"></i></div><span class="score-value">${percent(row[key])}<small>%</small></span></div></td><td class="numeric">${millions(row.input_tokens_known)}</td><td class="numeric">${millions(row.output_tokens_known)}</td><td class="numeric">${Number(row.agent_mean_model_turns_per_planned_cell).toFixed(1)}</td></tr>`).join('');
    const count = state.mode === 'all' ? data.pair_count : data.modes[state.mode];
    $('#board-context').textContent = `Question-weighted accuracy · ${count} ${state.mode==='all'?'':state.mode+' '}pairs · higher is better · resource columns cover each displayed run`;
    $$('[data-board]').forEach(button => {
      const active = button.dataset.board === state.mode;
      button.classList.toggle('active',active);
      button.setAttribute('aria-pressed',String(active));
    });
    $('#sort-score').innerHTML = `ACCURACY <span>${state.asc?'↑':'↓'}</span>`;
    $('#sort-score').setAttribute('aria-label',`Sort accuracy ${state.asc?'descending':'ascending'}`);
    $('.score-heading').setAttribute('aria-sort',state.asc?'ascending':'descending');
    const baseline = data.mode_baselines[state.mode];
    $('#baseline-uniform').innerHTML = `${percent(baseline.uniform_three)}<span>%</span>`;
    $('#baseline-ab').innerHTML = `${percent(baseline.random_ab)}<span>%</span>`;
    $('#baseline-fixed').innerHTML = `${percent(baseline.always_a)}<span>%</span>`;
  }
  $$('[data-board]').forEach(button => button.addEventListener('click',() => {state.mode=button.dataset.board;state.asc=false;renderLeaderboard();}));
  $('#sort-score').addEventListener('click',() => {state.asc=!state.asc;renderLeaderboard();});
  function download(name,contents,mime) {
    const url = URL.createObjectURL(new Blob([contents],{type:mime}));
    const link = document.createElement('a');link.href=url;link.download=name;link.click();
    setTimeout(() => URL.revokeObjectURL(url),1000);
    $('#toast').textContent='Download ready';$('#toast').classList.add('visible');
    setTimeout(() => $('#toast').classList.remove('visible'),2200);
  }
  $('#download-scores').addEventListener('click',() => {
    const header=['rank','model','configuration','mode','question_equal_weight_accuracy','scored_repeats','input_tokens_all_attempts','output_tokens_all_attempts','mean_agent_model_turns','agent_planned_cells','scoring_note'];
    const rows=boardRows().map(row => [row.displayRank,row.model,row.config_label,state.mode,row[scoreKey()],row.evaluated_repeats,row.input_tokens_known,row.output_tokens_known,row.agent_mean_model_turns_per_planned_cell,row.agent_planned_cells,row.model.startsWith('claude')&&state.mode!=='reasoning'?'AAB15-P016 uses repeats 1 and 3; all other tasks use repeats 1 to 3':`Included repeats: ${(row.included_repeats || []).join(' ')}`]);
    const csv=[header,...rows].map(row => row.map(value => `"${String(value).replaceAll('"','""')}"`).join(',')).join('\r\n');
    download(`ai4ai-rewardbench-${state.mode}.csv`,csv,'text/csv;charset=utf-8');
  });
  $('#model-count').textContent=data.model_count;
  const maxBench=Math.max(...data.benches.map(bench => bench.pairs));
  $('#bench-bars').innerHTML=data.benches.map(bench => `<button class="bench-row" data-bench="${escape(bench.bench)}" aria-label="Browse ${escape(bench.bench)}: ${bench.pairs} pairs"><span class="bench-name">${escape(bench.bench)}</span><span class="bench-track" aria-hidden="true"><i style="width:${bench.pairs/maxBench*100}%"></i></span><span class="bench-count">${bench.pairs}</span></button>`).join('');
  $('#bench-filter').innerHTML+=[...data.benches].sort((a,b) => a.bench.localeCompare(b.bench)).map(bench => `<option value="${escape(bench.bench)}">${escape(bench.bench)}</option>`).join('');

  function explorer(view) {
    $$('[data-explorer]').forEach(button => {const active=button.dataset.explorer===view;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));});
    $('#cases-view').hidden=view!=='cases';$('#catalog-view').hidden=view!=='catalog';
    if(view==='catalog')renderCatalog();
  }
  $$('[data-explorer]').forEach(button => button.addEventListener('click',() => explorer(button.dataset.explorer)));
  $('#catalog-shortcut').addEventListener('click',() => {state.page=1;$('#task-search').value='';$('#mode-filter').value='all';$('#bench-filter').value='all';explorer('catalog');});
  $$('.bench-row').forEach(button => button.addEventListener('click',() => {
    $('#bench-filter').value=button.dataset.bench;$('#mode-filter').value='all';$('#task-search').value='';state.page=1;explorer('catalog');$('#explorer').scrollIntoView({behavior:'smooth'});
  }));
  function renderCatalog() {
    const search=$('#task-search').value.trim().toLowerCase();
    const mode=$('#mode-filter').value, bench=$('#bench-filter').value;
    const filtered=data.pairs.filter(pair => (mode==='all'||pair.mode===mode)&&(bench==='all'||pair.bench===bench)&&[pair.pair_id,pair.title,pair.bench].join(' ').toLowerCase().includes(search));
    const pages=Math.max(1,Math.ceil(filtered.length/10));state.page=Math.min(state.page,pages);
    $('#catalog-count').textContent=`${filtered.length} of ${data.pair_count} tasks · select a task for its background, question, candidates, and decision rule`;
    $('#catalog-list').innerHTML=filtered.slice((state.page-1)*10,state.page*10).map(pair => `<button class="catalog-item" data-task="${escape(pair.pair_id)}" aria-haspopup="dialog"><span class="catalog-id">${escape(pair.pair_id)}</span><span class="catalog-title">${escape(pair.title)} <span class="catalog-open" aria-hidden="true">↗</span>${pair.input_cue_flag?'<span class="catalog-cue">Source retains a performance self-report</span>':''}</span><span class="catalog-bench">${escape(pair.bench)}</span><span class="catalog-mode">${pair.mode==='agent'?'Agent':'Reasoning'}</span></button>`).join('')||'<p class="empty-state">No matching tasks. Try another keyword or clear the filters.</p>';
    $('#page-number').textContent=`${state.page} / ${pages}`;$('#prev-page').disabled=state.page===1;$('#next-page').disabled=state.page===pages;
    $$('[data-task]').forEach(button => button.addEventListener('click',() => openTask(button.dataset.task)));
  }
  ['task-search','mode-filter','bench-filter'].forEach(id => $('#'+id).addEventListener(id==='task-search'?'input':'change',() => {state.page=1;renderCatalog();}));
  $('#prev-page').addEventListener('click',() => {state.page--;renderCatalog();});
  $('#next-page').addEventListener('click',() => {state.page++;renderCatalog();});

  function openTask(id) {
    const task=tasks.get(id);if(!task)return;
    const files=task.input_files || [];
    $('#task-dialog-content').innerHTML=`<div class="task-title"><span class="mode-badge">${escape(task.mode).toUpperCase()} / ${escape(task.bench)}</span><p class="task-id">${escape(task.pair_id)}</p><h2 id="task-dialog-title">${escape(task.title)}</h2></div><div class="task-section"><h3>Background</h3>${paragraphs(task.background)}</div><div class="task-section task-question"><h3>The question</h3>${paragraphs(task.task || task.question)}</div><div class="task-candidates"><div><span class="tiny-label">CANDIDATE A</span>${paragraphs(task.candidates?.A)}</div><div><span class="tiny-label">CANDIDATE B</span>${paragraphs(task.candidates?.B)}</div></div><div class="task-section"><h3>How to decide</h3>${paragraphs(task.decision_rule)}</div>${task.conditions?.length?`<div class="task-section"><h3>Conditions & constraints</h3><ul>${task.conditions.map(condition => `<li>${escape(condition)}</li>`).join('')}</ul></div>`:''}<details class="task-files"><summary>Public input inventory <span>${files.length} of ${task.input_file_count || files.length} files +</span></summary><div class="task-file-list">${files.map(file => `<div><span>${escape(file.path)}</span><span>${escape(file.role || '')}</span></div>`).join('')}</div></details><p class="task-source-note">English task presentation adapted from the frozen public input. Source file references and checksums are available in the task-details download. Candidate source code, full datasets, and private labels are not bundled.</p>`;
    $('#task-dialog').showModal();$('#task-dialog').scrollTop=0;document.body.classList.add('dialog-open');
  }
  $('#close-task').addEventListener('click',() => $('#task-dialog').close());
  $('#task-dialog').addEventListener('close',() => document.body.classList.remove('dialog-open'));
  $('#task-dialog').addEventListener('click',event => {if(event.target===$('#task-dialog')) {const r=event.target.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)event.target.close();}});

  $('#case-count').textContent=caseData.cases.length;
  function renderCase() {
    const current=caseData.cases.find(item => item.id===state.caseId);if(!current)return;
    $('#case-picker').innerHTML=caseData.cases.map(item => `<button class="case-pick ${item.id===current.id?'active':''}" data-case="${escape(item.id)}" aria-pressed="${item.id===current.id}"><span class="case-kicker"><span>${item.mode.toUpperCase()}</span><span>${escape(item.bench)}</span></span><strong>${escape(item.display_title || item.title)}</strong><span class="case-id">${escape(item.pair_id)} ↗</span></button>`).join('');
    $('#case-detail').innerHTML=`<div class="case-top"><div><span class="mode-badge">${current.mode.toUpperCase()} / ${escape(current.pair_id)}</span><h3>${escape(current.display_title || current.title)}</h3><p>${escape(current.task_summary)}</p><div class="case-rule"><span class="tiny-label">DECISION RULE</span><p>${escape(current.decision_rule)}</p></div><div class="case-conditions">${(current.conditions||[]).map(item => `<span>${escape(item)}</span>`).join('')}</div><button class="text-link case-task-link" data-open-case-task="${escape(current.pair_id)}">Open task details <span>↗</span></button></div><div><div class="candidate-comparison"><div class="candidate-block"><b>A</b><p>${escape(current.candidates.A)}</p></div><div class="candidate-block"><b>B</b><p>${escape(current.candidates.B)}</p></div></div><div class="case-evidence"><div class="detail-tabs" role="group" aria-label="Case detail"><button data-detail="trace" class="${state.detail==='trace'?'active':''}" aria-pressed="${state.detail==='trace'}">Decision & explanation</button><button data-detail="evidence" class="${state.detail==='evidence'?'active':''}" aria-pressed="${state.detail==='evidence'}">Source evidence</button></div><div id="detail-content"></div></div></div></div>${current.show_limitations!==false&&current.limitations?.length?`<p class="case-disclosure">${escape(current.limitations.join(' '))}</p>`:''}`;
    $$('[data-case]').forEach(button => button.addEventListener('click',() => {state.caseId=button.dataset.case;state.layer='all';renderCase();}));
    $$('[data-detail]').forEach(button => button.addEventListener('click',() => {state.detail=button.dataset.detail;renderCase();}));
    $('[data-open-case-task]').addEventListener('click',() => openTask(current.pair_id));
    if(state.detail==='evidence') {
      $('#detail-content').innerHTML=current.evidence.map(item => `<div class="evidence-row"><span class="evidence-source">${escape(item.source)} · source lines ${item.line_start}–${item.line_end}</span><h4>${escape(item.label || 'Source evidence')}</h4><p>${escape(item.summary || item.text)}</p></div>`).join('');
    } else renderTrace(current);
  }
  function renderFinalResponse(trace) {
    const final=trace.final_response;
    if(!final || final.availability!=='available')return `<div class="rationale-panel"><span class="tiny-label">MODEL EXPLANATION</span><p>${final?.availability==='refusal'?'This run ended in refusal. No explanation or accepted choice was returned.':'No readable final explanation is available in this exported record. The observed actions and outcome are preserved below.'}</p></div>`;
    const evidence=final.evidence || [];
    return `<div class="rationale-panel"><div class="rationale-heading"><span class="tiny-label">MODEL’S FINAL EXPLANATION</span><span class="prediction-chip">CHOICE ${escape(final.choice || trace.answer)}${final.confidence!=null?` · CONFIDENCE ${escape(final.confidence)}`:''}</span></div><div class="rationale-text">${paragraphs(final.reason)}</div>${evidence.length?`<details class="rationale-evidence"><summary>Cited evidence <span>${evidence.length} references +</span></summary>${evidence.map(item => `<div><span>${escape(item.file || item.path || 'Source')}${item.line_start?` · L${item.line_start}${item.line_end?`–${item.line_end}`:''}`:''}</span><p>${escape(item.claim || item.reason || item.text || '')}</p></div>`).join('')}</details>`:''}${final.uncertainties?.length?`<details class="rationale-evidence"><summary>Uncertainties acknowledged by the model <span>+</span></summary><ul>${final.uncertainties.map(item => `<li>${escape(item)}</li>`).join('')}</ul></details>`:''}<p class="rationale-source">${final.kind==='model_final_response'?'Recorded final response':'Curated explanation from the saved response'} · ${escape(final.source?.file || 'accepted response')} · This is the model’s rationale, not a verified reference answer.</p></div>`;
  }
  function renderTrace(current) {
    const models=[...new Set(current.traces.map(trace => trace.model))];
    if(!models.includes(state.model))state.model=models[0];
    const repeats=current.traces.filter(trace => trace.model===state.model).map(trace => trace.repeat).sort((a,b) => a-b);
    if(!repeats.includes(state.repeat))state.repeat=repeats[0];
    const trace=current.traces.find(trace => trace.model===state.model && trace.repeat===state.repeat);
    const layers=trace.layers||[];
    if(state.layer!=='all'&&!layers.some(layer => layer.id===state.layer))state.layer='all';
    const activeLayer=layers.find(layer => layer.id===state.layer);
    const events=trace.events.filter(event => state.layer==='all'||event.layer===state.layer);
    $('#detail-content').innerHTML=`<div class="trace-controls"><label for="trace-model">Model</label><select id="trace-model">${models.map(model => `<option value="${escape(model)}" ${model===state.model?'selected':''}>${escape(modelLabel(model))}</option>`).join('')}</select><label for="trace-repeat">Repeat</label><select id="trace-repeat">${repeats.map(repeat => `<option value="${repeat}" ${repeat===state.repeat?'selected':''}>Repeat ${repeat}</option>`).join('')}</select></div><div class="trace-info"><span>${escape(trace.run_label || modelLabel(trace.model))}</span><span>MERGED STATUS · ${escape(trace.status).toUpperCase()}</span><span>${trace.accepted_turn?`ACCEPTED TURN · ${trace.accepted_turn}`:'NO ACCEPTED ANSWER'}</span></div>${renderFinalResponse(trace)}<details class="interaction-details"><summary>${current.mode==='agent'?'Follow the inspection steps':'See the response record'} <span>${trace.events.length} recorded events +</span></summary>${trace.analysis_summary?.text?`<p class="analysis-disclosure"><span class="tiny-label">EDITORIAL SUMMARY</span>${escape(trace.analysis_summary.text)}</p>`:''}<div class="trace-controls"><label for="trace-layer">Run layer</label><select id="trace-layer"><option value="all">All layers (${layers.length})</option>${layers.map(layer => `<option value="${escape(layer.id)}" ${layer.id===state.layer?'selected':''}>${escape(layer.label)}</option>`).join('')}</select></div>${activeLayer?`<p class="trace-info">LAYER · ${escape(activeLayer.raw_status).toUpperCase()} · ${activeLayer.selected?'SELECTED':'NOT SELECTED'}</p>`:''}<div class="trace-events">${events.map((event,index) => `<div class="trace-event"><span class="trace-index">${event.turn ?? String(index+1).padStart(2,'0')}</span><div><h4>${escape(event.title)}</h4><span class="event-layer">${escape(layers.find(layer => layer.id===event.layer)?.label || event.layer || '')}</span><p>${escape(event.detail)}</p>${event.analysis?.text?`<div class="event-analysis"><span class="tiny-label">${event.analysis.kind==='missing'?'ANALYSIS AVAILABILITY':event.analysis.kind==='model_summary'?'RETURNED MODEL SUMMARY':event.analysis.kind==='model_final_reason'?'MODEL’S FINAL REASON':'OBSERVATION FROM THE RECORD'}</span><p>${escape(event.analysis.text)}</p>${event.analysis.basis?`<span class="analysis-basis">${escape(event.analysis.basis)}</span>`:''}</div>`:''}${event.final_evidence_links?.length?`<details class="linked-claims"><summary>How these passages appear in the final explanation <span>${event.final_evidence_links.length} claims +</span></summary><p class="link-timing-note">These are later claims from the final response, not thoughts recorded at this step.</p>${event.final_evidence_links.map(item => `<div><span>${escape(item.file)} · L${item.line_start}–${item.line_end}</span><p>${escape(item.claim)}</p></div>`).join('')}</details>`:''}${event.tools?.length?`<details class="tool-details"><summary>Inspect ${event.tools.length} tool call${event.tools.length===1?'':'s'} +</summary><pre>${escape(event.tools.map(tool => `${tool.name}(${JSON.stringify(tool.arguments)})${tool.error?' · tool error':''}${tool.returned_range?`\n  → returned lines ${tool.returned_range.start}–${tool.returned_range.end} (${tool.returned_range.count} lines)`:tool.returned_file_count!=null?`\n  → returned ${tool.returned_file_count} files`:''}`).join('\n'))}</pre></details>`:''}</div></div>`).join('')}</div><p class="trace-caption">Recorded model explanations and editorial observations are labeled separately. Empty or encrypted intermediate reasoning is not reconstructed. Turn numbers and original/recovery layer distinctions are preserved.</p></details>`;
    $('#trace-model').addEventListener('change',event => {state.model=event.target.value;state.layer='all';renderTrace(current);});
    $('#trace-repeat').addEventListener('change',event => {state.repeat=Number(event.target.value);state.layer='all';renderTrace(current);});
    $('#trace-layer').addEventListener('change',event => {state.layer=event.target.value;renderTrace(current);$('.interaction-details').open=true;});
  }
  $('#resource-body').innerHTML=data.leaderboard.map(row => `<tr><td>${escape(row.model)}<span class="model-provider">${escape(configLabel(row))}</span></td><td class="numeric">${millions(row.cached_input_tokens_known)}</td><td class="numeric">${number(row.agent_model_turns)}</td><td class="numeric">${number(row.agent_tool_rounds)}</td><td class="numeric">${number(row.agent_tool_calls)}</td><td class="numeric">${number(row.api_request_attempts)}</td><td class="numeric">${row.reported_cost_cny==null?'—':row.reported_cost_cny.toFixed(2)}</td></tr>`).join('');
  renderLeaderboard();renderCatalog();renderCase();
})();
