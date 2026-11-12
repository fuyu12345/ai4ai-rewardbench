# Case provenance

The case explorer contains three curated examples from the frozen Golden2 input and 45 observed model–repeat records: five models × three delivery or historical repeats for each case. It includes 44 accepted final explanations and one historical Claude Sonnet refusal. These are selected examples, not a representative performance sample.

## Included task evidence

| Pair | Mode | Summarized source ranges | Public files | Input fingerprint |
|---|---|---|---:|---|
| AAB15-P016 | agent | `A/rsi_method/reconstruct.py:9–12`; `B/rsi_method/reconstruct.py:9–12` | 94 | `1cf91b2d8bf40cac696ef34177cbb3624a9adcbd4bb18eff5c9dd697b9635b58` |
| KBV3N-083 | reasoning | `A/solution.py:10–16`; `B/solution.py:10–18`; `B/solution.py:24–32` | 7 | `dfa5339a5e7dfd70a81db41188bf49e429cc33c68e36ae540f08abd69fbb4d75` |
| NG15-P001 | reasoning | `A/train_gpt_simple.py:301–307`; `B/train_gpt_simple.py:337–343` | 6 | `936d12747b61538838ce72d1f457e9e8b6f8260aa4251e37da792019ce92f3c4` |

Each source file underlying an authored source summary was read from the frozen public input on 2026-11-11 and its complete SHA-256 compared with its manifest entry. No complete third-party source code is redistributed. The source line ranges identify the reviewed code, not lines of the displayed summary. Evidence items retain `kind: authored_summary`, the original source filename and line range, and `hash_scope: complete_source_file`. That hash identifies the full source file, not the summary text. Task descriptions, candidate descriptions, and `insight` are authored summaries rather than quotations or model reasoning.

For AAB15-P016, candidate summaries disclose both changed repair parameters: A uses interpolation 0.4 and final multiplier cap 1.5; B uses 0.1 and 1.15. The frozen task states that these final caps are inactive after the earlier ratio bounds. The known refusal exception applies specifically to Claude Sonnet, not Claude Opus.

## Model and repeat identity

The display order is Sol, Terra, Claude Opus, Gemini, Claude Sonnet. All five offer three real records per case.

| Model | Setting | Displayed repeat source |
|---|---|---|
| `gpt-6.1-sol` | xhigh | Three-model delivery index |
| `gpt-6.1-terra` | provider default | Three-model delivery index |
| `claude-opus-5-5` | high | Three-model delivery index |
| `gemini-4-argon` | provider default | Historical Golden2 merged index |
| `claude-sonnet-5-5` | provider default | Historical Golden2 merged index |

For the first three models, **the delivery index determines `repeat`**. The original directory's rep number is not used as the displayed identity. Within these three cases, Sol and Terra displayed repeats 1/2/3 correspond to original source-run repeats 1/1/2; Opus corresponds to original repeats 1/2/3. `original_repeat` records the selected raw result's number and each layer retains its own source repeat. `repeat_numbering` distinguishes `delivery` from `historical`. This mapping reflects the delivery's aggregation across separate runs; it does not merge two answers into one record.

The index's `final-result.json` link selects the adopted attempt. The extractor verifies that its answer equals the index answer and matches the exact structured answer in a saved response in that attempt. A single enclosing JSON code fence may be removed for parsing without changing the answer's fields. No selection depends on gold or correctness. `delivery_provenance` contains only relative index/final-result filenames, their SHA-256 values, and attempt count; private source paths and scoring fields are omitted.

All indexed original and recovery attempts are retained as layers. A recovery is part of its delivery repeat, not a fourth repeat. Layer IDs (`main`, `recovery-1`, ...) are presentation-local and preserve the delivery's attempt order. `delivery_attempt`, `original_repeat`, `raw_status`, logical turns, tool counts and selection status remain available. The original Gemini/Sonnet data also preserve all historical layers.

## Explanations and inspection observations

`final_response` contains the accepted model's `choice`, `confidence`, `reason`, source-cited `evidence`, and `uncertainties`. `text_policy: verbatim_fields` means these are submitted model words, not an editorial endorsement or independently verified scientific explanation. Confidence is the model's self-report, not a calibrated success probability. The source identifies a layer-local response filename and the full response-file SHA-256. Any private-identifier redaction must be labeled `private_identifiers_redacted`.

`analysis_summary` is a concise authored summary of the selected response, distinct from the exact answer. Different repeats can disagree: for example, Sol on NG15-P001 selects A/B/A across displayed repeats 1/2/3, and its authored summaries reflect those different choices.

An event's `analysis.kind` distinguishes:

- `model_final_reason`: the exact accepted `reason` text in an answer event. The complete structured answer retains `final_response.kind: model_final_response`.
- `model_message_excerpt`: bounded public assistant text returned before the selected structured answer, including a format-repair stage. It is not substituted for the accepted answer.
- `authored_observation`: recorded inspection actions and returned source-line ranges. `final_evidence_links` connects an inspected range to a claim in the later final justification. This is a retrospective source link, not a claim that the model had already reached that conclusion at the inspection turn.
- `missing`: no readable model analysis was returned for that event.

The inspected Sol/Terra Agent responses contain tool calls, empty readable reasoning content/summary arrays and opaque state. Opus thinking blocks in these records have empty readable text and signatures; historical Gemini/Sonnet pre-tool turns largely contain tool calls. No hidden thoughts are reconstructed. Each trace states this in `analysis_availability`, while actual public pre-final messages remain visible when returned.

Agent calls are grouped by original logical turn. An allowlist retains names, relative paths, numeric range/limit arguments, returned line ranges, output fingerprints and error booleans; tool output bodies are excluded. Reasoning input events describe the complete files supplied inline and are not fictitious tool calls.

The Claude Sonnet AAB15-P016 repeat-2 cell preserves the initial refusal and two retries, all at logical turn 5, with no invented answer or explanation. It is excluded from scoring; only that model–pair uses the other two repeats as avg@2. The exception does not apply to Claude Opus or another pair.

## Public boundary

This is a lightweight case-view artifact, not the complete trace collection or full task inputs. It excludes private reference labels, correctness fields, organizer evidence, raw transport bodies, encrypted state, credentials, internal hosts and absolute source paths. Deliberately extracted final-response fields and bounded public messages remain attributed to their model and saved response.

Source-code redistribution rights are not inferred from a manifest or the ability to inspect a file. Full datasets, raw traces, models and calibration assets remain separate release items. The source-summary section introduces no new blanket license for upstream material. The curated `show_limitations: false` presentation setting for NG15-P001 is preserved; provenance remains available here.

## Repeatable extraction and checks

For the current three-model delivery, run:

```bash
python3 scripts/enrich_delivery_cases.py --delivery-root /path/to/authorized-delivery
python3 -m unittest discover -s tests -p test_cases.py -v
```

The delivery contains symlinks to source runs. Keep them valid, or expand the links when transferring the delivery. The extractor follows each indexed attempt and verifies its adopted result; it never guesses the public repeat from a raw directory name. Existing Gemini/Sonnet records and curated case fields are preserved. Repeated exports are deterministic.

`scripts/enrich_cases.py` remains the legacy extractor and shared sanitized-reading helper. Its historical-source mode can use caller-supplied source roots/index plus an existing SSH alias; no credentials are embedded. Its older repeat-1 workflow is not the current publication route—use `enrich_delivery_cases.py` to maintain the complete three-repeat collection.

Offline checks pin the original input/source fingerprints and all 27 newly selected response fingerprints. They validate 45 unique records, model order and effort, original-versus-display repeat mapping, every indexed attempt count, final-answer attribution, the Sonnet refusal exception, public-data boundaries and preservation of the curated display setting. They do not claim to re-hash remote sources during an offline test run.

## Historical audit source fingerprints

These names identify the internal handoff sources without distributing their contents.

| Source | SHA-256 |
|---|---|
| `HANDOFF.md` | `fd20f8af68a45c0a2694c649c05caa155d8d4224fad07ca4fcd5d673583423d9` |
| `pairs.internal.jsonl` | `3af5598d0253eef63b4eaa78f6c3ffe33ff8c13c314994f72947259f0b674cd7` |
| `traces.internal.jsonl` | `7f7b48f9a114d2209008e5f451b595dfd32438112c6c5f6dd8a8f0135ce1f15a` |

Snapshot checks: 45 model–repeat records; 44 accepted explanations; 54 retained attempt layers; 104 observed inspection steps; 7 bounded public pre-final messages; no private-label/correctness fields or internal path strings in the export.
