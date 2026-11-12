# English task details

`data/public-tasks.json` provides English details for every one of the 135 frozen Golden2 pairs. Join `tasks[].pair_id` to the benchmark catalog. It adds task-specific titles, background, comparison statements, decision rules, candidate descriptions, conditions and selected input-file references. It does not change the source questions, candidate order, reference labels or recorded scores.

## Content and provenance

The original public task packages were read locally from an authorized frozen copy. Three forms of description are explicitly distinguished by `provenance.text_kind`:

- `edited_public_task_statement`: existing English task prose, with Markdown formatting and environment-specific navigation prose reduced for display.
- `authored_english_translation_summary`: a task-specific English summary of a Chinese task statement and its context. It is an editorial translation, not the exact original model input.
- `authored_contract_summary`: an operation-specific description assembled from structured public contracts, captured shapes and evaluation rules, used for FastKernels and FlashInfer tasks.

Candidate descriptions may combine a documented method contrast with a clearly marked **artifact inventory**. Inventories report file counts, principal entry files, imports and declared symbols found by static parsing; they do not certify runtime behavior or claim that a symbol name establishes an algorithmic advantage. No candidate program is imported or executed.

Every inspected source in `provenance.source_files` has a SHA-256 digest. Where the source appears in the frozen manifest, its bytes are checked against that manifest before export. The manifest itself is independently fingerprinted. Digests identify source files, not the generated English summaries, and do not grant redistribution rights.

`input_files` contains at most 24 selected references per question, prioritizing task/rule files and inspected candidate artifacts. `input_file_count` gives the original full manifest count; `input_files_shown` gives the displayed subset. Each reference includes its original relative path, available byte size, SHA-256 and role. These are metadata references, not clickable downloads of the complete original file contents.

## Release boundary

The export includes public task prose, authored summaries, contract facts and file metadata. It excludes candidate source bodies, dataset rows, model weights, reference labels, organizer evidence, credentials, internal hosts and absolute infrastructure paths. All 135 tasks have substantial descriptions, but this companion is **not the complete original evaluation input package**. A candidate's full code, data and shared environment may contain details absent from a summary. Full-package redistribution remains a separate release item.

The two source-cue flags remain visible. Historical scope and task-specific tie/abstention rules are preserved. The task details do not add evidence that a result generalizes to other seeds, hardware, task states or independent hidden tests.

## Rebuild and validate

With authorized access to the frozen public input tree:

```bash
python3 scripts/prepare_tasks.py --public-inputs /path/to/frozen/public-inputs
python3 -m unittest discover -s tests -p 'test_tasks.py' -v
```

The tree must contain `<pair_id>/public/TASK.md`, `CONTEXT.json`, `DECISION_RULE.json`, `manifest.json` and referenced inspected artifacts. The existing benchmark catalog defines the exact task set. The script uses only Python's standard library. The public tests run without the original task packages and check coverage, English display fields, source fingerprints, relative paths and key task-specific protocol exceptions.
