(() => {
  'use strict';
  const escape = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const text = (x,y,label,cls='scene-label',anchor='start') => `<text x="${x}" y="${y}" class="${cls}" text-anchor="${anchor}">${escape(label)}</text>`;
  const lines = (x,y,labels,cls='scene-copy',gap=28) => labels.map((label,i) => text(x,y+i*gap,label,cls)).join('');
  const link = (d,delay=0,dashed=false) => `<path d="${d}" class="scene-link${dashed?' scene-link-dashed':''}" pathLength="1" style="--scene-delay:${delay}ms"/>`;
  const dot = (x,y,large=false) => `<circle cx="${x}" cy="${y}" r="${large?6:4}" class="scene-dot"/>`;
  const tag = (x,y,label) => `${dot(x,y-6)}${text(x+15,y,label,'scene-meta')}`;
  const box = (x,y,w,h,title,body=[],index=0,accent=false) => `<g class="scene-enter" style="--scene-delay:${index*90}ms"><rect x="${x}" y="${y}" width="${w}" height="${h}" class="scene-box${accent?' scene-box-active':''}"/>${accent?`<path d="M${x} ${y}V${y+h}" class="scene-accent"/>`:''}${text(x+22,y+36,title,'scene-title')}${lines(x+22,y+72,body)}</g>`;
  const note = (label) => `<div class="scene-note"><span class="scene-note-line" aria-hidden="true"></span><span>${escape(label)}</span></div>`;
  const mobile = (items) => `<div class="scene-mobile">${items.map((item,i)=>`<div class="scene-mobile-step" style="--scene-delay:${i*70}ms"><span class="scene-mobile-index">${String(i+1).padStart(2,'0')}</span><div><strong>${escape(item[0])}</strong><p>${escape(item[1])}</p></div></div>`).join('')}</div>`;
  const scene = (label,svg,items,caption) => `<figure class="pipeline-scene"><svg class="scene-desktop" viewBox="0 0 1000 360" role="img" aria-label="${escape(label)}">${svg}</svg>${mobile(items)}${note(caption)}</figure>`;
  const runGlyph = (type,x,y) => {
    if(type==='session')return `${link(`M${x+12} ${y+10}V${y+90}`)}${[0,35,70].map((v,i)=>`${dot(x+12,y+10+v)}${text(x+30,y+17+v,`Turn ${i+1}`,'scene-meta')}`).join('')}`;
    if(type==='single')return `${text(x,y+12,'Prompt','scene-meta')}${link(`M${x+30} ${y+25}V${y+48}`)}${text(x,y+75,'Response','scene-meta')}`;
    return `${link(`M${x+50} ${y+10}V${y+35}M${x+50} ${y+35}L${x+15} ${y+65}M${x+50} ${y+35}L${x+85} ${y+65}M${x+85} ${y+65}L${x+110} ${y+95}`)}${[[50,10],[15,65],[85,65],[110,95]].map(([a,b])=>dot(x+a,y+b)).join('')}`;
  };
  const runName = type => ({tree:'Search tree',session:'Agent session',single:'Single-step rollout'}[type] || 'Search tree');
  const runMeaning = type => ({tree:'Each recoverable path to an algorithm node becomes a Unit.',session:'The interactions that form a submission become a Unit.',single:'Available prompt, response and visible reasoning form a Unit.'}[type] || 'Each recoverable path to an algorithm node becomes a Unit.');
  function construction(step,runType) {
    switch(step) {
      case 0:return scene('Public trajectories and available local trajectories are gathered for each benchmark.',
        box(40,40,300,112,'Public trajectories',['Published runs & artifacts'],0)+box(40,193,300,112,'Local trajectories',['When available'],1)+link('M340 96H440L500 172H635',180)+link('M340 249H440L500 172',270)+dot(500,172,true)+box(635,106,325,132,'Per-bench intake',['Source identity','Original run boundaries'],2,true)+tag(662,280,'Tree · session · rollout'),
        [['Public trajectories','Collect published runs and available algorithm artifacts.'],['Local trajectories','Include local records when available.'],['Per-bench intake','Keep source identity and original run boundaries.']],
        'Start from real records. Preserve their origin and what is actually available.');
      case 1:return scene(`Bench, Task, Run and Unit hierarchy. The selected run format is ${runName(runType)}.`,
        [40,275,510,745].map((x,i)=>text(x,34,`0${i+1}`,'scene-number')).join('')+box(40,61,190,207,'Bench',['Source','Version','Protocol'],0)+box(275,61,190,207,'Task',['Objective','Data','Constraints'],1)+box(510,61,190,207,'Run',[],2)+runGlyph(runType,540,120)+box(745,61,215,87,'Unit 01',['Process + output'],3,true)+box(745,170,215,87,'Unit 02',['Process + output'],4)+link('M230 162H275',150)+link('M465 162H510',260)+link('M700 162H720V104H745M720 162V213H745',360)+tag(515,315,runName(runType)),
        [['Bench → Task','A benchmark contains tasks with their own goals and constraints.'],['Task → Run',`A complete attempt may be a ${runName(runType).toLowerCase()}.`],['Run → Unit',runMeaning(runType)]],
        'One Run can contain multiple Units. Shared context is referenced, so each output remains traceable.');
      case 2:return scene('A Unit links the generation process, the algorithm artifact and its real evaluation feedback. Completeness is audited before pairing.',
        text(40,34,'ONE UNIT · THREE LINKED RECORDS','scene-meta')+box(40,62,275,182,'Generation edge',[],0,true)+runGlyph(runType,65,112)+lines(192,136,runType==='single'?['Visible','reasoning','if returned']:runType==='session'?['Tools','Observations','Context']:['Paths','Actions','Context'],'scene-meta',28)+box(362,62,275,182,'Algorithm node',['Submitted code','Project or patch','Recoverable identity'],1)+box(685,62,275,182,'Real feedback',['Metrics & logs','Seed / environment','Evaluation identity'],2)+link('M315 154H362',180)+link('M637 154H685',300)+link('M177 244V284H822V244',400)+dot(500,284,true)+text(500,326,'Completeness audit → selected Unit pool','scene-label','middle'),
        [['Generation edge',runMeaning(runType)],['Algorithm node','Store the actual submitted algorithm, project or recoverable patch.'],['Real execution feedback','Link each evaluation to the exact artifact and conditions.'],['Completeness audit','Retain missing-material explanations; select Units before forming pairs.']],
        'Extraction and Unit screening stop here. Missing material is recorded, never invented.');
      case 3:return scene('Codex-6 Astra follows the pair-curation skill to inspect same-task runs and Units and construct candidate pairs.',
        text(40,35,'WITHIN THE SAME TASK & COMPARISON CONDITIONS','scene-meta')+box(40,70,230,66,'Unit 01',[],0)+box(40,154,230,66,'Unit 02',[],1)+box(40,238,230,66,'Unit …',[],2)+link('M270 103H310V186H355M270 187H355M270 271H310V186',200)+box(355,104,300,170,'Codex-6 Astra',['Pair-curation skill','Audit artifacts & validity','Check comparison evidence'],2,true)+link('M655 188H706V115H750M706 188V260H750',390)+box(750,70,210,86,'Candidate A',['Task-bound plan'],3)+box(750,215,210,86,'Candidate B',['Task-bound plan'],4),
        [['Same-task Units','Inspect runs and outputs under explicit comparison conditions.'],['Codex-6 Astra + skill','Audit validity, artifact identity and supporting evidence.'],['Candidate pair','Build a meaningful A/B comparison with a task-specific rule.']],
        'Pair construction is a separate audit stage. Co-occurring Units are not automatically paired.');
      case 4:return scene('Human reviewers inspect candidate pairs and evidence, approving, revising or rejecting them.',
        box(40,112,250,142,'Candidate pair',['A / B + task context','Comparison evidence'],0)+link('M290 183H404',150)+`<g class="scene-enter" style="--scene-delay:160ms"><circle cx="500" cy="173" r="96" class="scene-review-ring"/>${text(500,160,'Human','scene-review-label','middle')}${text(500,194,'review','scene-review-label','middle')}</g>`+link('M596 173H655V81H710M655 173H710M655 173V266H710',300)+box(710,43,250,76,'Approve',[],2,true)+box(710,135,250,76,'Revise',[],3)+box(710,228,250,76,'Reject',[],4)+text(500,316,'Trace the claim back to its evidence.','scene-copy','middle'),
        [['Candidate pair','Read both approaches, task conditions and comparison evidence.'],['Human review','Check that the preference is supported and the comparison is valid.'],['Approve · revise · reject','Keep only pairs that pass review; preserve review decisions.']],
        'Human review is an explicit quality gate before a pair enters the golden collection.');
      default:return scene('Reviewed golden pairs are retained per benchmark with versioned task context, evidence and reference preferences.',
        text(40,35,'REVIEWED PAIRS, ORGANIZED BY BENCHMARK','scene-meta')+[40,360,680].map((x,i)=>`<g class="scene-enter" style="--scene-delay:${i*130}ms"><path d="M${x+10} 98H${x+270}V287H${x+10}" class="scene-stack"/><path d="M${x+20} 88H${x+280}V277H${x+20}" class="scene-stack"/>${box(x,108,260,190,i===2?'Bench …':`Bench ${i+1}`,['Golden pairs','Task-bound context','Versioned references'],i,i===0)}</g>`).join('')+tag(43,340,'Public task inputs')+tag(389,340,'Reference labels kept separate'),
        [['Per-bench golden pairs','Retain the reviewed subset for each benchmark.'],['Versioned context','Preserve the task, candidate identity and comparison rule.'],['Separate reference records','Keep private preference labels and supporting evidence outside judge inputs.']],
        'The animation illustrates the curation workflow; it does not claim a new data release or reconstruction of every v0.1 pair.');
    }
  }
  function evaluation(step,mode) {
    const agent=mode!=='reasoning';
    switch(step) {
      case 0:return scene('A frozen pair exposes task context and two candidate approaches to the judge. Reference labels remain separate.',
        box(40,45,300,245,'Frozen task context',['Goal & constraints','Decision rule','Candidate A','Candidate B'],0,true)+link('M340 169H420',180)+box(420,100,290,140,'Public input package',['Judge-visible evidence','Bound to this pair'],1)+link('M710 169H770',260)+text(865,163,'Judge','scene-review-label','middle')+text(865,195,agent?'Reward Agent':'Reasoning','scene-copy','middle')+`<path d="M420 292H960" class="scene-divider"/>`+text(437,328,'Reference preference stays outside model input.','scene-meta'),
        [['Frozen pair','Use the task, candidates A/B and the task-specific rule.'],['Public materials only','Provide only the pair’s permitted evidence.'],['Separate reference label','The judge does not see organizer labels or private feedback.']],
        'The model judges existing artifacts; this does not rerun the underlying research experiment.');
      case 1:return agent?scene('Reward Agent reads public files through manifest-bound list, read and search tools.',
        box(40,80,270,200,'Public manifest',['Allowed file inventory','Pair-scoped access','Read-only boundary'],0)+link('M310 180H367',180)+box(367,80,270,200,'Read-only tools',['list_files','read_file','search'],1,true)+link('M637 180H695',290)+box(695,80,265,200,'Reward Agent',['Inspect selected files','Follow useful references','Request more context'],2),
        [['Public manifest','Defines the files available for this pair.'],['Read-only tools','List, read and search the permitted materials.'],['Reward Agent','Chooses what evidence to inspect next.']],
        'No candidate execution, training run or web access is part of this judge loop.'):
        scene('Reasoning mode receives the complete public materials inline in one input.',
        box(40,55,315,250,'Complete public input',['Task & decision rule','Candidate A materials','Candidate B materials','Shared public context'],0)+link('M355 180H435',180)+box(435,105,255,150,'Inline context',['All public files','One supplied input'],1,true)+link('M690 180H760',290)+text(860,166,'Reasoning','scene-review-label','middle')+text(860,198,'Read → compare','scene-copy','middle'),
        [['Complete public materials','Include task context, both candidate artifacts and shared materials.'],['Inline context','Supply the full public input directly to the model.'],['Reasoning','Compare the approaches using the supplied evidence.']],
        'Reasoning mode reads inline materials; it does not follow a tool-inspection loop.');
      case 2:return agent?scene('Reward Agent iterates through inspection, returned observations and comparison before deciding.',
        box(40,115,250,130,'Inspect',['Choose a file or query','Read-only request'],0)+link('M290 180H375',170)+box(375,115,250,130,'Observe',['Source excerpts','Tool output & context'],1)+link('M625 180H710',280)+box(710,115,250,130,'Compare',['Compare A and B','Check uncertainty'],2,true)+link('M835 245V302H165V245',390)+text(500,337,'Need more evidence? Inspect again.','scene-copy','middle')+tag(40,54,'Evidence guides the next inspection'),
        [['Inspect','Choose a file or query within the public manifest.'],['Observe','Read returned source ranges and tool observations.'],['Compare → inspect again','Compare A and B and pursue unresolved questions.']],
        'Only returned model text is shown as model analysis. Empty or encrypted reasoning is not reconstructed.'):
        scene('Reasoning mode compares both candidates against the task rule using the complete inline materials.',
        box(40,90,265,170,'Candidate A',['Algorithm & assumptions','Evidence in context'],0)+box(695,90,265,170,'Candidate B',['Algorithm & assumptions','Evidence in context'],1)+link('M305 176H378M695 176H622',220)+`<g class="scene-enter" style="--scene-delay:180ms"><path d="M500 69L610 177L500 285L390 177Z" class="scene-compare"/>${text(500,166,'Compare','scene-review-label','middle')}${text(500,199,'under the rule','scene-copy','middle')}</g>`+tag(40,325,'Validity')+tag(350,325,'Expected task value')+tag(695,325,'Remaining uncertainty'),
        [['Candidate A and B','Examine algorithmic differences and assumptions.'],['Apply the task rule','Consider validity and expected value under the stated constraints.'],['Weigh uncertainty','State what the supplied evidence can and cannot establish.']],
        'A predicted advantage is a model judgment, not a newly measured execution result.');
      case 3:return scene('The judge submits A, B or tie with a rationale, source citations and uncertainty.',
        text(40,43,'A STRUCTURED JUDGMENT','scene-meta')+`<g class="scene-enter"><rect x="40" y="76" width="375" height="220" class="scene-box scene-box-active"/>${text(227,171,'A / B / tie','scene-choice','middle')}${text(227,228,'predicted preference','scene-copy','middle')}</g>`+link('M415 186H485',180)+box(485,76,475,220,'Supporting explanation',['Reason under the task’s conditions','Citations to the inspected evidence','Acknowledged uncertainty'],1),
        [['Preference','Submit A, B or tie under the task-specific rule.'],['Rationale and citations','Explain the choice and cite the supporting public material.'],['Uncertainty','Record limits without inventing exact experimental outcomes.']],
        'These are the model’s submitted claims. Correctness is assessed separately against the frozen reference.');
      case 4:return scene('Responses are validated and original and recovery attempts are grouped by the same pair, model and scheduled repeat.',
        box(40,52,260,111,'Initial attempt',['Response & usage'],0)+box(40,202,260,111,'Recovery attempt',['Only where needed'],1)+link('M300 109H350V181H405M300 259H350V181',210)+box(405,96,260,170,'Validate & group',['Response schema','Pair / model / repeat','Accepted result record'],2,true)+link('M665 181H728',360)+box(728,110,232,142,'One result cell',['Linked attempts','Preserved history'],3),
        [['Original and recovery','Keep the original attempts and any required recovery records.'],['Validate and group','Check response validity and the pair/model/repeat identity.'],['One result cell','Recovery belongs to the scheduled repeat, not an additional scored repeat.']],
        'Retain failed attempts and resource usage; preserve exceptions instead of silently replacing the record.');
      default:return scene('Accuracy is averaged across repeats for each task and then equally across tasks, alongside cumulative resource use.',
        box(40,60,275,230,'Scheduled repeats',['Repeat 1','Repeat 2','Repeat 3'],0)+link('M315 174H371',170)+box(371,100,285,150,'Per-task accuracy',['Average correctness','Documented exceptions'],1,true)+link('M656 174H715',290)+box(715,60,245,230,'Benchmark score',['Equal task weights','Agent / Reasoning','Cumulative resources'],2)+tag(40,335,'Tokens · model turns · tool calls · API attempts'),
        [['Scheduled repeats','Average accepted repeat correctness under the published protocol.'],['Per-task accuracy','Give each task equal weight; retain the documented exception.'],['Results + resources','Report the total and mode scores alongside cumulative resource use.']],
        'Avg@3 is question-weighted. The documented Claude Sonnet refusal uses the two accepted repeats.');
    }
  }
  window.renderPipelineScene = (kind,step=0,mode='agent',runType='tree') => kind==='evaluation'?evaluation(step,mode):construction(step,runType);
})();
