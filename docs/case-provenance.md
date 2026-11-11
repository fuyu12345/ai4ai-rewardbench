# Case provenance

The v0.1 case explorer contains three curated examples from the frozen Golden2 input and 27 observed trace records: three models × three repeats for each case. These are selected examples, not a representative performance sample.

## Included evidence

| Pair | Mode | Summarized source ranges | Public files | Input fingerprint |
|---|---|---|---:|---|
| AAB15-P016 | agent | `A/rsi_method/reconstruct.py:9–12`; `B/rsi_method/reconstruct.py:9–12` | 94 | `1cf91b2d8bf40cac696ef34177cbb3624a9adcbd4bb18eff5c9dd697b9635b58` |
| KBV3N-083 | reasoning | `A/solution.py:10–16`; `B/solution.py:10–18`; `B/solution.py:24–32` | 7 | `dfa5339a5e7dfd70a81db41188bf49e429cc33c68e36ae540f08abd69fbb4d75` |
| NG15-P001 | reasoning | `A/train_gpt_simple.py:301–307`; `B/train_gpt_simple.py:337–343` | 6 | `936d12747b61538838ce72d1f457e9e8b6f8260aa4251e37da792019ce92f3c4` |

Each included source file was read from the frozen public input on 2026-11-11 and its complete SHA-256 compared with its manifest entry before preparing an authored summary. No verbatim third-party source code is distributed. The one-based source line ranges identify the reviewed code, not lines of the displayed summary. The JSON contains the complete source-file SHA-256 (`hash_scope: complete_source_file`), which does not hash the summary text. Evidence items carry `kind: authored_summary`. Task descriptions, candidate descriptions, evidence text and the “insight” field are editorial summaries; they are not quotations or model reasoning.

## Trace export

- Models: `gpt-6.1-sol`, `gemini-4-argon`, and `claude-sonnet-5-5`.
- `status`, `answer`, `accepted_turn`, and `scoring_included` come from the merged trace index, which selects the earliest acceptable response independently of its correctness.
- Agent events come from recorded `tools.jsonl` entries. Tool names, turn numbers, relative paths, range/limit arguments and an error boolean are allowlisted. Tools are grouped by original logical turn; every extracted call is retained inside `tools`.
- Layer identifiers are presentation-local (`main`, `recovery-1`, `recovery-2`); they preserve chronological layer order. `raw_status` describes the individual run layer and may differ from the merged status after recovery or parsing.
- An `answer` event is the selected model prediction, not the reference label. It may refer to an earlier turn than the last raw interaction. No gold or correctness field is exported.
- Reasoning mode receives full public inputs inline; its input event is a protocol description, not a tool invocation. The accepted turn is observed metadata. No hidden reasoning is exposed.
- Claude/AAB15-P016/repeat 2 preserves three refusal layers and has no invented answer. The refusal description is verified against the handoff audit: HTTP 200, `stop_reason=refusal`, empty answer. This cell is excluded from scoring; the other two repeats form the unique avg@2 exception.

## Public boundary and limitations

This export is a lightweight case-view artifact, not the original 18.8 GB trace collection or complete task inputs. It contains no private organizer evidence, reference labels, transport bodies, encrypted model state, credentials, internal hosts, or absolute server paths. Tool output bodies are excluded; the underlying source files used for editorial summaries were separately verified against the frozen manifest.

The release includes authored summaries with benchmark attribution and source references. No source-code redistribution right has been inferred from the manifest or the ability to inspect a file. No blanket license is applied to upstream materials. Full datasets, raw traces, models and calibration assets remain separate release items pending their own provenance and permission review.

## Audit source fingerprints

These filenames identify the internal handoff sources without distributing them.

| Source | SHA-256 |
|---|---|
| `HANDOFF.md` | `fd20f8af68a45c0a2694c649c05caa155d8d4224fad07ca4fcd5d673583423d9` |
| `pairs.internal.jsonl` | `3af5598d0253eef63b4eaa78f6c3ffe33ff8c13c314994f72947259f0b674cd7` |
| `traces.internal.jsonl` | `7f7b48f9a114d2209008e5f451b595dfd32438112c6c5f6dd8a8f0135ce1f15a` |

Validation completed: three distinct cases; both modes represented; 27 model–repeat records; 26 valid records plus the one documented refusal; three refusal layers; all source ranges and fingerprints are retained; no verbatim candidate code remains; no reference-label/correctness fields or internal path strings in the export.

The release checks are executable with `python3 -m unittest discover -s tests -p test_cases.py -v`. They pin the reviewed source-file and input fingerprints, validate trace/layer relationships and the refusal exception, and check that public evidence stays an authored summary with no private payloads. The source bytes are not bundled, so these checks detect fingerprint drift in the export; they do not claim to re-hash remote files on each test run.

For AAB15-P016, both candidate summaries disclose the repair interpolation coefficient and the different final multiplier caps (A: 0.4 and 1.5; B: 0.1 and 1.15). The frozen task states that these final caps are inactive after the earlier ratio bounds, which is stated alongside the parameters rather than implying only one parameter differs in the code.
