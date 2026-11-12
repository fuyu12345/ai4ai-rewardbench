#!/usr/bin/env python3
"""Use an audited delivery index to publish three repeats of curated cases.

The input index determines the public repeat number and final result. Its
private scoring fields and original absolute paths never enter the export.
Existing historical Gemini/Sonnet traces and all curated presentation fields
are preserved. Call with --delivery-root pointing to an authorized local copy.
"""

import argparse
from collections import defaultdict
import json
from pathlib import Path

from enrich_cases import ROOT, CASE_IDS, enrich_trace, read_layer, sha


MODEL_ORDER = ['gpt-6.1-sol', 'gpt-6.1-terra', 'claude-opus-5-5',
               'gemini-4-argon', 'claude-sonnet-5-5']
SETTINGS = {
    'gpt-6.1-sol': ('Sol · xhigh', 'xhigh'),
    'gpt-6.1-terra': ('Terra · default', 'provider_default'),
    'claude-opus-5-5': ('Claude Opus · high', 'high'),
}


def indexed_trace(case, delivery, model, repeat):
    folder = delivery / 'trajectories' / model / f'rep{repeat}' / case['id']
    index_path = folder / 'index.json'
    index = json.loads(index_path.read_text())
    if (index['model'], index['repeat'], index['pair_id'], index['mode']) != (model, repeat, case['id'], case['mode']):
        raise ValueError('Delivery index identity does not match its logical cell')
    if index['input_sha256'] != case['provenance']['input_sha256']:
        raise ValueError('Delivery uses a different frozen public input')
    final_path = folder / 'final-result.json'
    final = json.loads(final_path.read_text())
    if index['status'] != 'valid' or final['status'] != 'valid' or final['answer'] != index['answer']:
        raise ValueError('Delivery final answer is not the indexed valid answer')
    if final['canonical_choice'] != index['choice']:
        raise ValueError('Indexed choice differs from the adopted result')
    label, effort = SETTINGS[model]
    if index['effort'] != effort:
        raise ValueError('Delivery effort differs from the displayed setting')

    details = []
    selected_layer = None
    selected_message = None
    for position, attempt in enumerate(index['attempts']):
        number = attempt['attempt']
        # Read the delivery-local symlink, not a guessed original rep directory.
        attempt_folder = folder / f'attempt-{number:02d}'
        if not attempt_folder.is_dir():
            raise ValueError('An indexed attempt is unavailable; expand the delivery links first')
        layer_id = 'main' if position == 0 else f'recovery-{position}'
        layer = read_layer(attempt_folder, layer_id)
        layer['info']['label'] = 'Initial run' if position == 0 else f'Recovery {position}'
        layer['info']['delivery_attempt'] = number
        result_path = attempt_folder / 'result.json'
        result = json.loads(result_path.read_text())
        layer['info']['original_repeat'] = result['repeat']
        observed_turns = [m['turn'] for m in layer['messages']] + [a['turn'] for a in layer['actions']]
        if observed_turns:
            layer['info']['resume_turn'] = min(observed_turns)
        # A transferred delivery may have expanded symlinks; exact bytes still
        # identify the selected result without relying on original host paths.
        is_final = result_path.samefile(final_path) or sha(result_path) == sha(final_path)
        if is_final:
            if selected_layer is not None:
                raise ValueError('More than one indexed attempt matches the adopted result')
            # Match the exact indexed answer to the saved response, not simply
            # the latest attempt or the response with the best outcome.
            matches = [m for m in layer['messages'] if m['parsed_final'] == index['answer']]
            if not matches:
                raise ValueError(f'No saved response matches indexed final answer for {model}/{repeat}/{case["id"]}')
            selected_message = matches[0]
            selected_layer = layer
            layer['info']['selected'] = True
        details.append(layer)
    if selected_layer is None:
        raise ValueError('The adopted result does not belong to an indexed attempt')

    trace = {
        'model': model, 'repeat': repeat, 'original_repeat': final['repeat'],
        'repeat_numbering': 'delivery', 'orientation': index['orientation'],
        'mode': case['mode'], 'status': 'valid', 'scoring_included': True,
        'accepted_turn': selected_message['turn'], 'answer': index['choice'],
        'layers': [layer['info'] for layer in details], 'events': [],
        'run_id': delivery.name, 'run_label': label, 'reasoning_effort': effort,
        'delivery_provenance': {
            'index_file': str(index_path.relative_to(delivery)), 'index_sha256': sha(index_path),
            'final_result_file': str(final_path.relative_to(delivery)), 'final_result_sha256': sha(final_path),
            'attempt_count': len(index['attempts']),
            'repeat_note': 'The displayed repeat is the delivery index number; original_repeat records the selected source run number.',
        },
    }
    for layer in details:
        key = layer['info']['id']
        if case['mode'] == 'reasoning':
            trace['events'].append({'kind': 'input', 'layer': key, 'turn': 0,
                                    'title': 'Complete input supplied inline',
                                    'detail': f'All {case["file_count"]} public files were supplied in full; no inspection tools were used.', 'tools': []})
        by_turn = defaultdict(list)
        for action in layer['actions']:
            by_turn[action['turn']].append(action['action'])
        for turn, actions in sorted(by_turn.items()):
            names = list(dict.fromkeys(action['name'] for action in actions))
            paths = [a['arguments']['path'] for a in actions if 'path' in a['arguments']]
            trace['events'].append({'kind': 'tool', 'layer': key, 'turn': turn,
                                    'title': ' + '.join(names) + f' · {len(actions)} calls',
                                    'detail': '; '.join(paths) or 'Inspect the manifest-listed public files.', 'tools': actions})
        if layer['info']['raw_status'] == 'failed_final':
            trace['events'].append({'kind': 'attempt', 'layer': key, 'turn': layer['info']['last_model_turn'],
                                    'title': 'Interrupted run recovered',
                                    'detail': 'This indexed attempt ended before a valid answer. The following recovery remains part of the same displayed repeat.', 'tools': []})
    trace['events'].append({'kind': 'answer', 'layer': selected_message['source']['layer'],
                            'turn': selected_message['turn'], 'title': f'Accepted model answer: {index["choice"]}',
                            'detail': 'The exact submitted reason, citations and uncertainties are shown in the final explanation panel. The reference label is not shown.', 'tools': []})
    enrich_trace(trace, {'answer': index['answer'], 'accepted_source': selected_message['source'], 'layers': details}, case['id'])
    return trace


def enrich_delivery(data, delivery):
    if {case['id'] for case in data['cases']} != set(CASE_IDS):
        raise ValueError('This extractor is scoped to the three curated cases')
    for case in data['cases']:
        historic = [trace for trace in case['traces'] if trace['model'] in MODEL_ORDER[3:]]
        expected = {(model, repeat) for model in MODEL_ORDER[3:] for repeat in (1, 2, 3)}
        if {(t['model'], t['repeat']) for t in historic} != expected or len(historic) != 6:
            raise ValueError('Expected six existing historical traces per case')
        for trace in historic:
            trace['run_label'] = 'Historical default run'
            trace.setdefault('original_repeat', trace['repeat'])
            trace.setdefault('repeat_numbering', 'historical')
        current = [indexed_trace(case, delivery, model, repeat)
                   for model in MODEL_ORDER[:3] for repeat in (1, 2, 3)]
        case['traces'] = current + sorted(historic, key=lambda t: (MODEL_ORDER.index(t['model']), t['repeat']))
        case['available_repeats'] = {model: [1, 2, 3] for model in MODEL_ORDER}
        if case['id'] == 'AAB15-P016':
            case['limitations'] = [text.replace('Claude repeat 2', 'Claude Sonnet repeat 2') for text in case['limitations']]
        # Other case fields, including show_limitations, are deliberately kept.
    data['schema_version'] = '0.3.0'
    data['snapshot_date'] = '2026-11-12'
    data['models'] = MODEL_ORDER
    data['disclosure'] = ('Curated task/source summaries, actual recorded inspection metadata, and attributed final model justifications. '
                          'Sol xhigh, Terra default and Claude Opus high use three delivery-indexed repeats; Gemini and Claude Sonnet retain three historical repeats. '
                          'Displayed repeats follow the delivery index, which can differ from original run numbering. '
                          'Editorial observations are distinguished from exact submitted final fields. '
                          'No private labels, raw tool-output bodies, encrypted state or hidden reasoning are published.')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--delivery-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'data/public-cases.json')
    args = parser.parse_args()
    data = enrich_delivery(json.loads(args.output.read_text()), args.delivery_root)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print(f'Exported {sum(len(c["traces"]) for c in data["cases"])} traces; '
          f'{sum(t["final_response"]["availability"] == "available" for c in data["cases"] for t in c["traces"])} accepted explanations.')


if __name__ == '__main__':
    main()
