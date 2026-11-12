# Case provenance

The case explorer contains three curated examples from the frozen Golden2 input and 24 observed trace records. Each case offers Sol xhigh repeat 1, Terra repeat 1, and three historical repeats each for Gemini and Claude. There are 23 accepted final explanations and one documented refusal. These are selected examples, not a representative performance sample.

## Included evidence

| Pair | Mode | Summarized source ranges | Public files | Input fingerprint |
|---|---|---|---:|---|
| AAB15-P016 | agent | `A/rsi_method/reconstruct.py:9–12`; `B/rsi_method/reconstruct.py:9–12` | 94 | `1cf91b2d8bf40cac696ef34177cbb3624a9adcbd4bb18eff5c9dd697b9635b58` |
| KBV3N-083 | reasoning | `A/solution.py:10–16`; `B/solution.py:10–18`; `B/solution.py:24–32` | 7 | `dfa5339a5e7dfd70a81db41188bf49e429cc33c68e36ae540f08abd69fbb4d75` |
| NG15-P001 | reasoning | `A/train_gpt_simple.py:301–307`; `B/train_gpt_simple.py:337–343` | 6 | `936d12747b61538838ce72d1f457e9e8b6f8260aa4251e37da792019ce92f3c4` |

Each included source file was read from the frozen public input on 2026-11-11 and its complete SHA-256 compared with its manifest entry before preparing an authored summary. No verbatim third-party source code is distributed. The one-based source line ranges identify the reviewed code, not lines of the displayed summary. The JSON contains the complete source-file SHA-256 (`hash_scope: complete_source_file`), which does not hash the summary text. Evidence items carry `kind: authored_summary`. Task descriptions, candidate descriptions, evidence text and the “insight” field are editorial summaries; they are not quotations or model reasoning.

## Trace export

- Models: `gpt-6.1-sol` (new xhigh run, repeat 1), `gpt-6.1-terra` (provider-default effort, repeat 1 only), and the historical `gemini-4-argon` / `claude-sonnet-5-5` runs (repeats 1–3). The old default-effort Sol records have been replaced, not relabeled as xhigh. Terra repeats 2–3 are intentionally absent to match the current leaderboard scope.
- Historical `status`, `answer`, `accepted_turn`, and `scoring_included` come from the merged trace index, which selects the earliest acceptable response independently of its correctness. New Sol/Terra selections come from a valid result in the original/recovery layers and are matched to the saved response containing the same structured answer. Recovery is continuation of the same repeat, not another scored repeat.
- Agent events come from recorded `tools.jsonl` entries. Tool names, turn numbers, relative paths, range/limit arguments, returned line ranges, output fingerprints and an error boolean are allowlisted. Tools are grouped by original logical turn; every extracted call is retained inside `tools`. Tool output bodies are excluded.
- Layer identifiers are presentation-local (`main`, `recovery-1`, `recovery-2`); they preserve chronological layer order. `raw_status` describes the individual run layer and may differ from the merged status after recovery or parsing.
- An `answer` event is the selected model prediction, not the reference label. It may refer to an earlier turn than the last raw interaction. No gold or correctness field is exported.
- Reasoning mode receives full public inputs inline; its input event is a protocol description, not a tool invocation. The accepted turn is observed metadata. No hidden reasoning is exposed.
- Claude/AAB15-P016/repeat 2 preserves three refusal layers and has no invented answer. The refusal description is verified against the handoff audit: HTTP 200, `stop_reason=refusal`, empty answer. This cell is excluded from scoring; the other two repeats form the unique avg@2 exception.

## Public boundary and limitations

This export is a lightweight case-view artifact, not the original complete trace collection or task inputs. It contains no private organizer evidence, reference labels, raw transport bodies, encrypted model state, credentials, internal hosts, or absolute server paths. Final submitted fields and a few bounded public assistant messages are deliberately extracted from saved responses; tool output bodies are excluded. The underlying source files used for editorial source summaries were separately verified against the frozen manifest.

The release includes authored summaries with benchmark attribution and source references. No source-code redistribution right has been inferred from the manifest or the ability to inspect a file. No blanket license is applied to upstream materials. Full datasets, raw traces, models and calibration assets remain separate release items pending their own provenance and permission review.

## Audit source fingerprints

These filenames identify the internal handoff sources without distributing them.

| Source | SHA-256 |
|---|---|
| `HANDOFF.md` | `fd20f8af68a45c0a2694c649c05caa155d8d4224fad07ca4fcd5d673583423d9` |
| `pairs.internal.jsonl` | `3af5598d0253eef63b4eaa78f6c3ffe33ff8c13c314994f72947259f0b674cd7` |
| `traces.internal.jsonl` | `7f7b48f9a114d2209008e5f451b595dfd32438112c6c5f6dd8a8f0135ce1f15a` |

Validation completed: three distinct cases; both modes represented; 24 model–repeat records; 23 valid records plus the one documented refusal; three refusal layers; all source ranges and fingerprints are retained; no verbatim candidate code remains; no reference-label/correctness fields or internal path strings in the export.

The release checks are executable with `python3 -m unittest discover -s tests -p test_cases.py -v`. They pin the reviewed source-file and input fingerprints, validate trace/layer relationships and the refusal exception, and check that public evidence stays an authored summary with no private payloads. The source bytes are not bundled, so these checks detect fingerprint drift in the export; they do not claim to re-hash remote files on each test run.

For AAB15-P016, both candidate summaries disclose the repair interpolation coefficient and the different final multiplier caps (A: 0.4 and 1.5; B: 0.1 and 1.15). The frozen task states that these final caps are inactive after the earlier ratio bounds, which is stated alongside the parameters rather than implying only one parameter differs in the code.


## Explanations and inspection observations

`final_response` preserves the accepted model's `choice`, `confidence`, `reason`, source-cited `evidence`, and `uncertainties`. `text_policy: verbatim_fields` means these are the model's submitted words, not an editorial endorsement or an independently verified explanation. Confidence is the model's self-report, not a calibrated success probability. The source identifies a layer-local response filename and the full response-file SHA-256. Any future redaction must be labeled `private_identifiers_redacted`.

`analysis_summary` is a short authored summary of that final answer. It is explicitly separate from the exact answer. An event's `analysis` distinguishes:

- `model_final_reason`: exact accepted final justification within an answer event; the complete structured answer remains `final_response.kind: model_final_response`.
- `model_message_excerpt`: a bounded public assistant message returned before the selected structured answer, including format-repair stages; it is not substituted for the accepted answer.
- `authored_observation`: recorded inspection actions and returned source-line ranges. `final_evidence_links` connects those inspected ranges to claims in the later final justification. This is a retrospective source link, not a claim that the model had already reached that conclusion at the inspection turn.
- `missing`: no readable model analysis was returned for that event.

In the inspected Agent pre-tool responses, Sol/Terra returned empty readable reasoning-summary/content arrays and opaque state, while the historical Gemini/Claude turns largely returned tool calls. No hidden thoughts are reconstructed. This limitation is stated in each trace's `analysis_availability`; a missing analysis is not replaced with fictional reasoning. The export contains 23 actual final explanations, 56 observed inspection steps, and six public pre-final assistant message excerpts.

## Repeatable extraction

Run `scripts/enrich_cases.py` with `--sol-root`, `--terra-root`, and `--historical-index` pointing to authorized source copies. The script follows the Sol `recovery-network-v1` and Terra `recovery-rate-limit-v1` layers and restricts both new runs to repeat 1. Historical sources can be locally mounted, or accessed with an existing SSH configuration using `--historical-ssh HOST_ALIAS` and optional `--historical-port PORT`. Credentials are supplied by the existing SSH mechanism and are never embedded in the script or output. Re-running the extractor replaces derived records and preserves curated case descriptions.

The default output is `data/public-cases.json`. All source locations are caller-supplied; internal filesystem locations and host addresses are not saved in the release. The script reads a strict set of response fields and tool-result metadata and never exports encrypted state, full thought transcripts, or raw tool outputs. A source-fingerprint assertion confirms the six newly selected final responses; offline tests additionally verify 24 unique records, available-repeat filters, and the original Claude refusal exception.
