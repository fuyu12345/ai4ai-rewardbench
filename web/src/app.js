(() => {
  'use strict';
  const { dataset: data } = window.BENCHMARK;
  const $ = selector => document.querySelector(selector);
  const $$ = selector => [...document.querySelectorAll(selector)];
  const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const percent = value => (value * 100).toFixed(2);
  const millions = value => value == null ? '—' : `${(value / 1e6).toFixed(2)}M`;
  const number = value => value == null ? '—' : value.toLocaleString('en-US');
  const state = { mode:'all', asc:false };
  const scoreKey = () => state.mode === 'all' ? 'question_equal_weight_accuracy' : `${state.mode}_accuracy`;
  const configLabel = row => !row.config_label || row.config_label === 'default' ? 'default setting' : `${row.config_label} reasoning effort`;
  const hasRepeatException = row => row.model === 'claude-sonnet-5-5';
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
    $('#leaderboard-body').innerHTML = boardRows().map(row => `<tr class="${row.displayRank===1?'top-ranked':''}"><td>${String(row.displayRank).padStart(2,'0')}</td><td><span class="model-name">${escape(row.model)}${hasRepeatException(row)?'<sup>*</sup>':''}</span><span class="model-provider">${escape(configLabel(row))}</span></td><td class="score-cell"><div class="score-content"><div class="score-bar" aria-hidden="true"><i style="width:${row[key]*100}%"></i></div><span class="score-value">${percent(row[key])}<small>%</small></span></div></td><td class="numeric">${millions(row.input_tokens_known)}</td><td class="numeric">${millions(row.output_tokens_known)}</td><td class="numeric">${row.agent_mean_model_turns_per_planned_cell==null?'—':Number(row.agent_mean_model_turns_per_planned_cell).toFixed(1)}</td></tr>`).join('');
    const count = state.mode === 'all' ? data.pair_count : data.modes[state.mode];
    $('#board-context').textContent = `Question-weighted accuracy · avg@3* · ${count} ${state.mode==='all'?'':state.mode+' '}pairs · higher is better · resource columns cover each displayed run`;
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
    const rows=boardRows().map(row => [row.displayRank,row.model,row.config_label,state.mode,row[scoreKey()],row.evaluated_repeats,row.input_tokens_known,row.output_tokens_known,row.agent_mean_model_turns_per_planned_cell,row.agent_planned_cells,hasRepeatException(row)&&state.mode!=='reasoning'?'AAB15-P016 uses repeats 1 and 3; all other tasks use repeats 1 to 3':`Included repeats: ${(row.included_repeats || []).join(' ')}`]);
    const csv=[header,...rows].map(row => row.map(value => `"${String(value).replaceAll('"','""')}"`).join(',')).join('\r\n');
    download(`ai4ai-rewardbench-${state.mode}.csv`,csv,'text/csv;charset=utf-8');
  });
  $('#model-count').textContent=data.model_count;
  $('#resource-body').innerHTML=data.leaderboard.map(row => `<tr><td>${escape(row.model)}<span class="model-provider">${escape(configLabel(row))}</span></td><td class="numeric">${millions(row.cached_input_tokens_known)}</td><td class="numeric">${number(row.agent_model_turns)}</td><td class="numeric">${number(row.agent_tool_rounds)}</td><td class="numeric">${number(row.agent_tool_calls)}</td><td class="numeric">${number(row.api_request_attempts)}</td><td class="numeric">${row.reported_cost_cny==null?'—':row.reported_cost_cny.toFixed(2)}${row.cost_status==='partial_explicit_cny'?'<span class="model-provider">Partial coverage</span>':''}</td></tr>`).join('');
  renderLeaderboard();
})();
