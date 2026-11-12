#!/usr/bin/env python3
"""Enrich curated cases with allowlisted final answers and observed inspections.

All source roots are supplied by the caller. No credentials or private paths are
written into the release. Historical sources may be read through existing SSH
access; encrypted/hidden reasoning and tool output bodies never enter the export.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CASE_IDS = ('AAB15-P016', 'KBV3N-083', 'NG15-P001')
ARG_FIELDS = {'path', 'start', 'end', 'limit', 'offset', 'line_start', 'line_end'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_path(value):
    path = PurePosixPath(value)
    return not path.is_absolute() and '..' not in path.parts and 'organizer' not in path.parts and '\\' not in value


def safe_text(value):
    if not isinstance(value, str):
        return value
    value = re.sub(r'/(?:mnt|Users|home|root)/[^\s"\']+', '[private path omitted]', value)
    value = re.sub(r'\b(?:call_|req_|resp_|org-)[A-Za-z0-9_-]{10,}', '[provider identifier omitted]', value)
    return value


def source_ref(path, layer):
    return {'layer': layer, 'file': Path(path).name, 'sha256': sha(path)}


def read_layer(folder, layer):
    """Read only public response text, field metadata and sanitized tool actions."""
    folder = Path(folder)
    result_path = folder / 'result.json'
    result = json.loads(result_path.read_text()) if result_path.exists() else {}
    info = {
        'id': layer, 'label': 'Initial run' if layer == 'main' else 'Recovery 1',
        'resume_turn': 1, 'raw_status': result.get('status'), 'selected': False,
        'model_turns_attempted': result.get('model_turns_attempted'),
        'last_model_turn': result.get('last_model_turn'),
        'tool_interaction_rounds': result.get('tool_interaction_rounds'),
        'tool_calls_attempted': result.get('tool_calls_attempted'),
    }
    if result.get('error_type'):
        info['error_category'] = result['error_type']
    actions = []
    tool_path = folder / 'tools.jsonl'
    if tool_path.exists():
        for raw in tool_path.read_text().splitlines():
            row = json.loads(raw)
            args = row['arguments']
            args = json.loads(args) if isinstance(args, str) else args
            allowed = {k: v for k, v in args.items() if k in ARG_FIELDS and (k != 'path' or safe_path(v))}
            output = row.get('result', '')
            try:
                decoded = json.loads(output) if isinstance(output, str) else output
            except (ValueError, TypeError):
                decoded = {}
            action = {'name': row['name'], 'arguments': allowed, 'error': bool(row.get('error'))}
            if isinstance(decoded, dict):
                lines = decoded.get('lines', [])
                numbers = [x['line'] for x in lines if isinstance(x, dict) and isinstance(x.get('line'), int)]
                if numbers:
                    action['returned_range'] = {'start': min(numbers), 'end': max(numbers), 'count': len(numbers)}
                if isinstance(decoded.get('total'), int):
                    action['returned_file_count'] = decoded['total']
                if isinstance(decoded.get('total_lines'), int):
                    action['total_file_lines'] = decoded['total_lines']
            action['output_sha256'] = hashlib.sha256((output if isinstance(output, str) else json.dumps(output, sort_keys=True)).encode()).hexdigest()
            actions.append({'turn': row['turn'], 'action': action})
    messages = []
    for path in sorted(folder.glob('*.response.json')):
        response = json.loads(path.read_text())
        message = response.get('message', {})
        turn = response.get('turn') or int(re.search(r'turn-(\d+)', path.name).group(1))
        content = message.get('content')
        text = content if isinstance(content, str) else ''
        parsed = None
        if text:
            try:
                parsed = json.loads(text)
            except ValueError:
                pass
        readable = []
        for item in message.get('_response_items', []):
            if item.get('type') == 'reasoning':
                readable += [x.get('text', '') for x in item.get('summary', []) if isinstance(x, dict) and x.get('text')]
        # This field is a provider-returned public summary, not encrypted state.
        messages.append({
            'turn': turn, 'source': source_ref(path, layer),
            'has_tool_calls': bool(message.get('tool_calls')),
            'public_summary': safe_text(' '.join(readable)),
            'public_message': safe_text(text) if text and parsed is None else '',
            'parsed_final': parsed if isinstance(parsed, dict) and 'choice' in parsed else None,
        })
    return {'info': info, 'actions': actions, 'messages': messages,
            'tool_source': source_ref(tool_path, layer) if tool_path.exists() else None}


def read_historical(records):
    output = []
    for record in records:
        layers = []
        for n, layer in enumerate(record['layers']):
            key = 'main' if n == 0 else f'recovery-{n}'
            detail = read_layer(layer['trace_dir'], key)
            detail['info']['label'] = 'Initial run' if n == 0 else f'Recovery {n}'
            detail['info']['resume_turn'] = layer['resume_turn']
            layers.append(detail)
        answer = None
        accepted = None
        if record.get('selected_result'):
            selected = json.loads(Path(record['selected_result']).read_text())
            answer = selected.get('answer')
        if record.get('accepted_response_path'):
            layer_idx = next(i for i, layer in enumerate(record['layers']) if record['accepted_response_path'].startswith(layer['trace_dir'] + '/'))
            accepted = source_ref(record['accepted_response_path'], layers[layer_idx]['info']['id'])
        output.append({'pair_id': record['pair_id'], 'model': record['model'], 'repeat': record['repeat'],
                       'answer': answer, 'accepted_source': accepted, 'layers': layers})
    return output


def final_response(answer, source, status):
    if not answer:
        return {'kind': 'model_final_response', 'availability': 'refusal' if status == 'failed_final' else 'missing',
                'choice': None, 'confidence': None, 'reason': None, 'evidence': [], 'uncertainties': [],
                'source': None, 'text_policy': 'no_answer_returned'}
    output = {k: answer.get(k) for k in ('choice', 'confidence', 'reason')}
    output['reason'] = safe_text(output['reason'])
    output['evidence'] = []
    for evidence in answer.get('evidence', []):
        if not isinstance(evidence, dict) or not safe_path(evidence.get('file', '')):
            continue
        output['evidence'].append({k: safe_text(evidence[k]) for k in ('file', 'line_start', 'line_end', 'claim') if k in evidence})
    output['uncertainties'] = [safe_text(x) for x in answer.get('uncertainties', [])]
    output.update(kind='model_final_response', availability='available', source=source)
    output['text_policy'] = 'verbatim_fields' if output['reason'] == answer.get('reason') and output['uncertainties'] == answer.get('uncertainties', []) else 'private_identifiers_redacted'
    return output


def make_new_trace(case, root, model, recovery, run_label, effort):
    layers = []
    selected_result = None
    selected_layer = None
    for subdir in ('', recovery):
        folder = root / subdir / 'runs' / model / case['id'] / 'rep1' / 'AB'
        if not folder.exists():
            continue
        key = 'main' if not subdir else 'recovery-1'
        layer = read_layer(folder, key)
        if layer['messages']:
            layer['info']['resume_turn'] = min(message['turn'] for message in layer['messages'])
        layers.append(layer)
        result = json.loads((folder / 'result.json').read_text())
        if result.get('status') == 'valid' and selected_result is None:
            selected_result = result
            selected_layer = layer
    if selected_result is None:
        raise ValueError(f'No valid current repeat 1: {model} {case["id"]}')
    answer = selected_result['answer']
    matches = [m for m in selected_layer['messages'] if m['parsed_final'] == answer]
    if not matches:
        raise ValueError(f'Accepted final response not found: {model} {case["id"]}')
    accepted = matches[0]
    selected_layer['info']['selected'] = True
    trace = {'model': model, 'repeat': 1, 'orientation': 'AB', 'mode': case['mode'], 'status': 'valid',
             'scoring_included': True, 'accepted_turn': accepted['turn'], 'answer': answer['choice'],
             'layers': [layer['info'] for layer in layers], 'events': [],
             'run_id': root.name, 'run_label': run_label, 'reasoning_effort': effort}
    for layer in layers:
        key = layer['info']['id']
        if case['mode'] == 'reasoning':
            trace['events'].append({'kind': 'input', 'layer': key, 'turn': 0, 'title': 'Complete input supplied inline',
                                    'detail': f'All {case["file_count"]} public files were supplied in full; no inspection tools were used.', 'tools': []})
        by_turn = defaultdict(list)
        for row in layer['actions']:
            by_turn[row['turn']].append(row['action'])
        for turn, actions in sorted(by_turn.items()):
            paths = [a['arguments']['path'] for a in actions if 'path' in a['arguments']]
            names = list(dict.fromkeys(a['name'] for a in actions))
            trace['events'].append({'kind': 'tool', 'layer': key, 'turn': turn,
                                    'title': ' + '.join(names) + f' · {len(actions)} calls',
                                    'detail': '; '.join(paths) or 'Inspect the manifest-listed public files.', 'tools': actions})
        if layer['info']['raw_status'] == 'failed_final':
            trace['events'].append({'kind': 'attempt', 'layer': key, 'turn': layer['info']['last_model_turn'],
                                    'title': 'Interrupted run recovered',
                                    'detail': 'Transport or rate-limit interruption. The same repeat continues in the recovery layer; this is not an extra scored repeat.', 'tools': []})
    trace['events'].append({'kind': 'answer', 'layer': accepted['source']['layer'], 'turn': accepted['turn'],
                            'title': f'Accepted model answer: {answer["choice"]}',
                            'detail': 'The exact submitted reason, citations and uncertainties are shown in the final explanation panel. The reference label is not shown.', 'tools': []})
    return trace, {'answer': answer, 'accepted_source': accepted['source'], 'layers': layers}


def enrich_trace(trace, details, pair_id):
    # Recreate derived public-message events so repeated exports are idempotent.
    trace['events'] = [event for event in trace['events'] if event['kind'] != 'model_message']
    final = final_response(details['answer'], details['accepted_source'], trace['status'])
    trace['final_response'] = final
    available = final['availability'] == 'available'
    summaries = {
        'AAB15-P016': 'Favors B’s weaker mean repair: matching calibration means alone can distort surviving weights, and stronger perturbations can propagate through later pruning steps. This is the model’s prediction, not an observed validation result.',
        'KBV3N-083': 'Favors B’s contiguous memory access over A’s row-strided warp accesses, while accounting for B’s explicit synchronization and the shared output allocation.',
        'NG15-P001': ('Expects the optimizer substitution to have only a small effect under the shared Muon branch, schedule and training horizon, and selects tie.' if trace['answer'] == 'tie' else 'Favors A’s AdamW recipe because B changes gradient weighting and BF16 update behavior while retaining the same learning rates and schedule.'),
    }
    trace['analysis_summary'] = {
        'kind': 'authored_summary',
        'text': summaries[pair_id] if available else 'No final justification was returned. Three recorded refusal attempts remain visible; no replacement explanation is invented.',
        'source_refs': [final['source']] if final['source'] else [],
    }
    trace['analysis_availability'] = 'No readable pre-tool model analysis was returned in the inspected messages. Inspection observations are authored from recorded calls and returned ranges; final justifications are the model’s own submitted fields.'
    layer_map = {layer['info']['id']: layer for layer in details['layers']}
    for event in trace['events']:
        detail = layer_map[event['layer']]
        messages = [m for m in detail['messages'] if m['turn'] == event['turn']]
        message = messages[-1] if messages else None
        refs = [m['source'] for m in messages]
        if event['kind'] == 'tool':
            if detail['tool_source']:
                refs.append(detail['tool_source'])
            # Use recorded tool outcomes rather than infer an unobserved mental step.
            actions = [a['action'] for a in detail['actions'] if a['turn'] == event['turn']]
            event['tools'] = actions
            reads = []
            for action in actions:
                path = action['arguments'].get('path')
                returned = action.get('returned_range')
                if path:
                    reads.append(path + (f':{returned["start"]}–{returned["end"]}' if returned else ''))
            text = 'Recorded inspection: ' + '; '.join(reads) + '.' if reads else f'Recorded {len(actions)} manifest-inspection call(s).'
            event['analysis'] = {'kind': 'authored_observation', 'availability': 'tool_only', 'text': text,
                                 'basis': 'Recorded tool calls and returned line ranges; not a model thought transcript.', 'source_refs': refs}
            matching = []
            for citation in final['evidence']:
                for action in actions:
                    if action['arguments'].get('path') != citation.get('file'):
                        continue
                    returned = action.get('returned_range')
                    if returned and citation.get('line_end', 0) < returned['start']:
                        continue
                    if returned and citation.get('line_start', 10**9) > returned['end']:
                        continue
                    if citation not in matching:
                        matching.append(citation)
            event['final_evidence_links'] = matching
            if matching:
                event['analysis']['text'] += f' The later final justification cites {len(matching)} matching source passage(s), reproduced as attributed claims below.'
        elif event['kind'] == 'answer':
            event['detail'] = 'The exact submitted reason, citations and uncertainties are shown in the final explanation panel. The reference label is not shown.'
            event['analysis'] = {'kind': 'model_final_reason', 'availability': final['availability'],
                                 'text': final['reason'], 'basis': 'Exact accepted reason field.', 'source_refs': [final['source']] if final['source'] else []}
        else:
            event['analysis'] = {'kind': 'missing', 'availability': 'not_returned', 'text': 'No readable model analysis is available for this event.', 'basis': 'No analysis invented from a failure, refusal or input record.', 'source_refs': refs}
        if message and message['public_summary']:
            event['analysis'] = {'kind': 'model_summary', 'availability': 'available', 'text': message['public_summary'],
                                 'basis': 'Provider-returned readable summary; encrypted state excluded.', 'source_refs': [message['source']]}
    # Preserve short public assistant messages before format repair as exact text.
    present = {(event['layer'], event['turn']) for event in trace['events']}
    for layer in details['layers']:
        for message in layer['messages']:
            text = message['public_message']
            if not text or (layer['info']['id'], message['turn']) in present:
                continue
            trace['events'].append({'kind': 'model_message', 'layer': layer['info']['id'], 'turn': message['turn'],
                                    'title': 'Model message before accepted answer',
                                    'detail': 'Public assistant text returned before the selected structured response. Not a scored replacement answer.',
                                    'tools': [], 'analysis': {'kind': 'model_message_excerpt', 'availability': 'available',
                                    'text': text[:3000], 'truncated': len(text) > 3000,
                                    'basis': 'Exact public assistant message, bounded to 3,000 characters.', 'source_refs': [message['source']]}})
    order = {layer['id']: i for i, layer in enumerate(trace['layers'])}
    trace['events'].sort(key=lambda event: (order[event['layer']], event['turn'], event['kind'] == 'answer'))


def historical_details(args, records):
    if not args.historical_ssh:
        return read_historical(records)
    # The same allowlist functions run on the source host. Only their sanitized
    # result returns; no raw streams, credentials or encrypted state are copied.
    own = Path(__file__).read_text()
    code = own[:own.index('\ndef main():')]
    code = code.replace('ROOT = Path(__file__).resolve().parents[1]', 'ROOT = Path.cwd()')
    code += '\nimport sys\nprint(json.dumps(read_historical(json.load(sys.stdin)), ensure_ascii=False))\n'
    response = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-p', str(args.historical_port),
                               args.historical_ssh, 'python3', '-c', shlex.quote(code)],
                              input=json.dumps(records), text=True, capture_output=True, check=True)
    return json.loads(response.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sol-root', type=Path, required=True)
    parser.add_argument('--terra-root', type=Path, required=True)
    parser.add_argument('--historical-index', type=Path, required=True)
    parser.add_argument('--historical-ssh', help='Optional existing SSH host or alias; not saved in output')
    parser.add_argument('--historical-port', type=int, default=22)
    parser.add_argument('--output', type=Path, default=ROOT / 'data/public-cases.json')
    args = parser.parse_args()
    data = json.loads(args.output.read_text())
    records = [row for row in map(json.loads, args.historical_index.read_text().splitlines())
               if row['pair_id'] in CASE_IDS and row['model'] in ('gemini-4-argon', 'claude-sonnet-5-5')]
    old = {(row['pair_id'], row['model'], row['repeat']): row for row in historical_details(args, records)}
    for case in data['cases']:
        retained = [trace for trace in case['traces'] if trace['model'] in ('gemini-4-argon', 'claude-sonnet-5-5')]
        for trace in retained:
            trace.update(run_id='golden2-20261110-avg3', run_label='Historical default run', reasoning_effort='provider_default')
            enrich_trace(trace, old[(case['id'], trace['model'], trace['repeat'])], case['id'])
        new = []
        for model, root, recovery, label, effort in (
            ('gpt-6.1-sol', args.sol_root, 'recovery-network-v1', 'Sol · xhigh', 'xhigh'),
            ('gpt-6.1-terra', args.terra_root, 'recovery-rate-limit-v1', 'Terra · default', 'provider_default')):
            trace, details = make_new_trace(case, root, model, recovery, label, effort)
            enrich_trace(trace, details, case['id'])
            new.append(trace)
        case['traces'] = new + retained
        case['available_repeats'] = {model: sorted({t['repeat'] for t in case['traces'] if t['model'] == model})
                                     for model in ['gpt-6.1-sol', 'gpt-6.1-terra', 'gemini-4-argon', 'claude-sonnet-5-5']}
    data['schema_version'] = '0.2.0'
    data['snapshot_date'] = '2026-11-12'
    data['models'] = ['gpt-6.1-sol', 'gpt-6.1-terra', 'gemini-4-argon', 'claude-sonnet-5-5']
    data['disclosure'] = 'Curated task/source summaries, actual recorded inspection metadata, and attributed final model justifications. Sol xhigh and Terra include only repeat 1; Gemini and Claude retain three historical repeats. Editorial observations are distinguished from exact submitted final fields. No private labels, raw tool-output bodies, encrypted state or hidden reasoning are published.'
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print(f'Exported {sum(len(c["traces"]) for c in data["cases"])} traces; '
          f'{sum(t["final_response"]["availability"] == "available" for c in data["cases"] for t in c["traces"])} final explanations.')


if __name__ == '__main__':
    main()
