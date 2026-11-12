#!/usr/bin/env python3
"""Export readable task details from authorized frozen public inputs.

No candidate execution, model calls, private labels, data rows, or code bodies.
English source task prose is lightly edited; Chinese statements are condensed
English translations. The export explicitly distinguishes these from summaries.
"""
import argparse
import ast
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CN = re.compile(r"[\u4e00-\u9fff]")

# Human-reviewed, task-specific English summaries of Chinese public statements.
# Each tuple is title, background, task details, candidate A, candidate B, rule.
TRANSLATIONS = {
"PTB-P103": (
    "GPQA post-training with Gemma 3 4B",
    "Compare two complete science-question post-training routes starting from google/gemma-3-4b-pt.",
    "Both routes use the supplied LoRA trainer and existing Nemotron science SFT data. They train for one epoch with rank 32, alpha 64 and dropout 0.05, adapting the language-model attention and feed-forward projections. Dataset size, shuffling, length filtering, batch setup and training length limits vary together; this is not a single-variable reasoning ablation. The target is the original first 128 GPQA-main questions under the preserved Gemma template and choice parser. Each route has one historical training run and evaluation; shuffled answer options were not seeded. The common H100 80 GB session had a ten-hour research allowance, which is not a per-candidate training budget. Full recipe files, data preparation and trainer implementations define the active routes.",
    "The complete Gemma LoRA route specified in A/recipe.json, including its own preparation, length filters and batch settings.",
    "The alternative complete Gemma LoRA route in B/recipe.json; its data and training conditions must be assessed jointly.",
    "Higher parsed-choice accuracy on the original 128-question GPQA development panel. Do not extrapolate to all 448 questions, independent training seeds or exact paired prompts."),
"PTB-P110": (
    "GSM8K post-training and model export",
    "Choose a Qwen3-1.7B-Base training-and-export pipeline for the original GSM8K evaluation.",
    "Both routes begin with the same Orca stage: 49,630 examples remain after filtering the first 50,000 records at length 768; training uses one epoch, learning rate 1e-4, batch 16 with accumulation 4, and rank-32 scaled LoRA. B adds a GSM/OMI stage at learning rate 5e-6 with length 1,024, choosing a checkpoint by held-out GSM loss. The comparison includes the actual loading, merging, tokenizer and saved generation settings in each recipe; an unexecuted repaired export is not a candidate. Evaluation uses the fixed first 50 GSM8K test questions, a ten-shot prompt sampled with seed 42, numeric matching and the original Qwen template. The shared saved generation setup specifies temperature zero and EOS 151645. Historical weight hashes and complete example logs were not preserved.",
    "The common first-stage training and the export/evaluation path declared by A/recipe.json.",
    "The additional mixed GSM/OMI training stage and the actual export/evaluation path declared by B/recipe.json.",
    "Higher numeric-match accuracy on the original first 50 GSM8K test questions. Evaluate the complete historical export, not a hypothetical corrected variant."),
"PTB-P112": (
    "GPQA GRPO: 350 versus 600 updates",
    "Compare two GRPO routes from the same science-question SFT checkpoint of Qwen3-1.7B.",
    "Both candidates start independently from the same epoch-2 SFT checkpoint and train all parameters with GRPO. A uses 3,000 shuffled questions and 350 optimizer updates; B uses all 3,147 questions and 600 updates. Both use learning rate 1e-6, ten warmup steps, KL coefficient 0.04, eight rollouts per prompt, microbatch 8 with accumulation 2, and generation temperature 0.7 with a 320-token cap. Training questions include MMLU-Pro science categories, not GPQA examples. Dataset membership and sampler order change alongside duration, so the pair is not two checkpoints from one run. The frozen evaluator measures parsed-choice accuracy on all 448 GPQA-main questions with greedy generation and a 2,048-token cap. Choices are independently shuffled at evaluation; repeated scores are historical observations, not independent training seeds.",
    "Full-parameter GRPO for 350 updates on 3,000 questions selected after seed-0 shuffling.",
    "Full-parameter GRPO for 600 updates on all 3,147 questions after the same initial shuffle.",
    "Higher mean historical accuracy on the complete 448-question GPQA-main panel. Training time and step count do not replace the quality objective."),
"mlagentbench-v3-20261107-006": (
    "English-learner essay scoring",
    "Predict six writing-quality scores for ELLIPSE essays written by English learners in grades 8–12.",
    "The targets are cohesion, syntax, vocabulary, phraseology, grammar and conventions, each on a 1.0–5.0 scale in 0.5 increments. Candidates drop missing rows and use a 90/10 split with seed 42. Compare the final returned model on that local holdout, averaging the six per-dimension RMSE values. Validation labels cannot train model parameters. The complete scripts define preprocessing, pretrained resources, optimization and training duration. Hidden submission quality and any later CSV are outside the target. Exact source data bytes, resource digests, hardware and dependency patch versions were not archived.",
    "The text representation and six-target regression pipeline in A/solution.py.",
    "The alternative complete representation and regression pipeline in B/solution.py.",
    "Lower final holdout MCRMSE. Quality alone determines preference; uncertainty does not mean tie."),
"mlagentbench-v3-20261107-020": (
    "Learning Floyd–Warshall beyond training graph sizes",
    "Learn all-pairs shortest-path predecessor pointers and evaluate transfer to 64-node graphs.",
    "Training cycles through generated graphs with 4, 7, 11, 13 and 16 nodes. Both scripts use batch 32, 500 training steps and seed 42. A checkpoint is selected by validation on 16-node graphs and restored after training; its predecessor-pointer accuracy is then measured on the fixed CLRS 64-node test set. The target is this restored checkpoint, not training loss or small-graph validation accuracy. Each call initializes afresh and saves at step zero before accepting later strict validation improvements. Archived CLRS reference modules were recovered, but their byte identity with the originally imported installation is not established.",
    "The complete graph-learning implementation and checkpoint-selection path in A/solution.py.",
    "The alternative implementation in B/solution.py under the same size progression and restored-checkpoint test.",
    "Higher 64-node test predecessor-pointer accuracy after restoring the validation-selected checkpoint. Runtime is not a tie-breaker."),
"mlagentbench-v3-20261107-024": (
    "Marine image classification: final probability quality",
    "Predict the presence of 290 labels in marine images; each image may contain multiple classes.",
    "PNG images are resized to 256 × 256 RGB and scaled by 255; label lists become 290-dimensional multi-hot targets. A seed-20 split assigns 70% to training and 30% to validation. Compare the model in memory after the final training epoch by mean binary cross-entropy across images and labels. Neither candidate adds parameter regularization to the reported loss. This is not thresholded accuracy, open-set detection, later CSV quality or a best-epoch selection. Both models start from random initialization with Keras Adam; the complete code specifies architecture, epochs and batch size. Exact images, random initial states, patch versions and hardware are not frozen.",
    "The randomly initialized multilabel network and full training recipe in A/solution.py.",
    "The alternative randomly initialized network and recipe in B/solution.py.",
    "Lower final validation binary cross-entropy on the fixed 30% holdout, without a runtime or memory tie-breaker."),
"mlagentbench-v3-20261107-029": (
    "Ames house prices: local validation MAE",
    "Predict SalePrice from house attributes in the Ames housing data.",
    "Compare the complete fitting recipes on their declared fixed holdout from the same training table. The metric is validation mean absolute error on the original price scale. Printed training MAE and the subsequent submission CSV's hidden-test quality are outside this question. Candidate code determines selected columns, missing-data handling, splits, model seeds and hyperparameters; no extra tuning is permitted. Validation labels must not train model parameters. Original CSV bytes, exact row counts for the historical runs and software patch versions were not recovered.",
    "The feature-selection, preprocessing and regression recipe in A/solution.py.",
    "The alternative complete regression recipe in B/solution.py.",
    "Lower holdout MAE in original price units. A tie requires practically similar quality, not missing information."),
"mlagentbench-v3-20261107-043": (
    "CIFAR-10: final online accuracy on 9,984 images",
    "Compare two complete training recipes for ten-class classification of 32 × 32 RGB CIFAR-10 images.",
    "Both use the standard 50,000 training and 10,000 test images, tensor conversion and per-channel normalization with mean and standard deviation 0.5. There is no random augmentation. Training shuffles with drop_last enabled; test loading does not shuffle but also drops the last incomplete batch. The score is the last test_model call after training, covering the first 9,984 test examples. It is not the best epoch or the later 10,000-row CSV score. Scripts create new models and optimizers, have no learning-rate schedule and do not set a training seed. Their full epoch and hyperparameter choices define the pair; historical results are not multi-seed expectations.",
    "The fresh model and complete fixed-epoch PyTorch recipe in A/solution.py.",
    "The alternative fresh model and fixed-epoch recipe in B/solution.py.",
    "Higher final online test accuracy on the exact 9,984-example prefix. No speed or parameter-count preference is added."),
"mlagentbench-v3-20261107-060": (
    "Essay scoring: does the selected model remain usable?",
    "Compare search pipelines for six-dimensional ELLIPSE essay scoring, including the validity of their returned states.",
    "Essays use six 1.0–5.0 writing scores, a missing-row filter and a seed-42 90/10 split. Each route searches three regressors and two text representations. First determine whether the returned model and its preprocessing can produce the final validation predictions without changing the code. If only one is valid, prefer it; if both are valid, compare final six-target MCRMSE. A temporary model's search score is not the returned object's score. Validation may select a recipe, but model parameters fit only the training split and the selected model/representation state must be retained or restored consistently. The historical environment supplied scikit-learn and spaCy en_core_web_lg; exact resource versions were not frozen.",
    "The regressor/representation search and returned-state handling in A/solution.py.",
    "The alternative search and retained preprocessing/model state in B/solution.py.",
    "Validity first; then lower final validation MCRMSE. If both returned states are invalid, escalate rather than infer a quality preference."),
"mlagentbench-v3-20261107-071": (
    "Marine multilabel learning with ten training epochs",
    "Compare neural-network recipes for 290-class multilabel marine-image prediction.",
    "Images are resized to 256 × 256 RGB, scaled by 255 and paired with multi-hot labels. The fixed seed-20 split is 70/30. Both candidates train from a fresh initialization for ten epochs using default Adam; their batch sizes and network structures are defined by the complete scripts. Measure the final in-memory model's binary cross-entropy over all validation images and 290 labels. No extra regularization loss is included. Thresholded decisions, reported accuracy and later submission files do not define the score. Identical historical paths and split code support the comparison, but raw bytes and initialization states were not preserved.",
    "The ten-epoch architecture and batch configuration in A/solution.py.",
    "The alternative ten-epoch architecture and batch configuration in B/solution.py.",
    "Lower final validation binary cross-entropy. Do not generalize the historical pair to all seeds or training budgets."),
"mlagentbench-v3-20261107-080": (
    "Ames housing: two random-forest fitting recipes",
    "Compare two 100-tree random-forest recipes for Ames house-price prediction.",
    "Both scripts read the same training table without dropping rows and make a seed-1 75/25 split. They use the code's 25 numerical housing fields, including area, quality, age and room/facility counts. B first handles missing and categorical values over the full table, while the final selected columns determine the actual model inputs. Both forests use 100 trees and random_state 0, with depth and leaf settings left to their code defaults. Compare validation MAE in original price units, not training error or hidden submission quality. No new grid search is allowed; the cost of an absolute-error splitting criterion is not itself a quality penalty. Exact data bytes and scikit-learn patch version were not archived.",
    "The 100-tree random forest and feature preparation declared in A/solution.py.",
    "The alternative preprocessing and forest-fitting recipe in B/solution.py.",
    "Lower fixed-holdout MAE. The comparison does not establish a fully paired or statistically significant general effect."),
"RSI-031": (
    "Chromatin embeddings: one neighborhood or multiple scales?",
    "Embed 67,790 blood immune cells from 524,151 accessible-chromatin peaks into 50 dimensions.",
    "The permitted input is a sparse binary cell-by-peak matrix, nine batch labels and chromosome/start/end peak names. A marks whether any peak is detected within ±5,000 bases of each peak. B computes the same binary neighborhood detection at ±1,000, ±5,000 and ±10,000 bases, then averages the feature matrices before one TF-IDF/LSI pass. Both recompute IDF after aggregation, L2-normalize rows and apply 50-component TruncatedSVD with seed 2002. Batch labels and the differing diagnostic sample sizes do not affect the final embedding. The evaluator uses all fixed public cells, a 15-neighbor graph and the maximum NMI over eight Leiden resolutions. The fallback KMeans path is outside the captured metric. The task declares eight CPUs, 64 GiB and no GPU; diagnostic runtime is not the quality target.",
    "Single ±5,000-base binary neighborhood aggregation before one TF-IDF/LSI embedding.",
    "Equal-weight fusion of ±1,000/5,000/10,000-base neighborhood features before the same embedding.",
    "Higher full-public-cell cell-type NMI from the captured successful Leiden evaluations. Hidden cells and diagnostic subsamples are excluded."),
"RSI-036": (
    "Paged attention: narrow versus adaptive head blocks",
    "Accelerate paged grouped-query decoding while preserving the complete attention contract.",
    "Queries have shape (batch, query_heads, head_dim); K/V pages are indexed by an int32 CSR page table. Valid-token handling, optional Llama rotary encoding, windows, dot-product scaling, tanh clipping, softmax and the fresh output tensor must remain correct. Both candidates use the same Triton split-context algorithm with 256-token partitions and at most 16 partitions, online softmax and log-sum-exp merging. On all six public shapes, head_dim is 256 and each K/V head serves 128 query heads. A uses head blocks of 32 and eight decode warps; B uses blocks of 64 and sixteen warps under a 16,384-element FP32 accumulator budget. Both merge with eight warps. On the recorded L20X, each case has 128 warmups and 21 CUDA-event samples, each comprising eight calls. The reference is timed before and after the candidate; its two medians are combined geometrically. Numerical correctness and timing-dispersion/drift gates must pass.",
    "Fixed small query-head tiles: 32 heads and eight decode warps on the six scored shapes.",
    "Adaptive larger tiles: 64 heads and sixteen decode warps on those shapes, with unchanged merge logic.",
    "Higher geometric mean of bracketed-reference speedups over all six public cases, subject to correctness and timing gates. These are L20X observations, not an H100 leaderboard result."),
"RSI-041": (
    "2048 expectimax: complete versus approximate chance branches",
    "Select deterministic 2048 moves to maximize mean raw game score within a shared evaluation budget.",
    "Both programs encode the 4 × 4 board in 64 bits and precompute all 65,536 row transitions. A considers every empty spawn location with the true 0.9/0.1 probabilities of tiles 2/4, using adaptive move depths 2–4 based on empty cells. Its leaf score uses emptiness, mergeability, monotonicity and smoothness terms, with 150,000-entry LRU caches per node type. B uses depth four, at most two sampled empty locations per row, only tile-2 spawns and explicit immediate merge reward. Its leaf score includes corners and snake ordering; each cache holds up to 1.5 million entries. The full 16-game retained seed suite has a shared 3,600 CPU-second allowance, a five-second action cap and persistent caches across games. The container has four CPUs, 12 GiB and no GPU; both historical final submissions completed the suite. Eight public development seeds are available, but retained seeds and outcomes are hidden.",
    "Adaptive-depth expectimax with complete spawn branches and probability-weighted tiles 2 and 4.",
    "Fixed deeper expectimax with approximated chance branches, immediate merge reward and larger caches.",
    "Higher mean raw score on the full retained 16-game suite within the common limits. Maximum tile and speed do not replace score."),
"RSI-043": (
    "Glass cutting: column simulation or sequence search?",
    "Produce legal guillotine-cut trees for rectangular glass orders on defective 6,000 × 3,210 mm stock sheets.",
    "Items may rotate but must avoid defects and preserve within-stack production order. Cuts proceed through vertical columns, horizontal rows and vertical pieces, with optional fourth-level trimming. Column widths, row heights and minimum waste widths are constrained. Only the rightmost full strip of the final sheet is reusable; other unused area is waste. A simulates complete candidate columns from current stack-front items and target widths, then searches orientations and row/column scoring rules. B searches legal interleavings and shelf-style layouts, adds height-fill selection with reachable-height bitsets, and attempts dynamic-programming compression of final-sheet row groupings when defect bands permit it. Both use an internal 18-second target with differing stopping checks; the public subprocess cap is 120 seconds. All ten public instances must pass the supplied official checker before mean waste is compared.",
    "Simulate complete candidate columns and choose layouts through varied orientation, width and row/column scores.",
    "Search legal sequences and shelf/fill layouts, then attempt guarded dynamic-programming compression of the final sheet.",
    "All ten public instances must be valid; among valid complete programs, lower mean waste area wins. Extra search branches do not by themselves establish better quality."),
"RSI-048": (
    "Visual counting: full training or language-only LoRA?",
    "Adapt Qwen2-VL-2B-Instruct from ordinary object counts to out-of-distribution relational counting.",
    "The public setting contains 20,000 training examples, 2,000 in-distribution validation examples and 1,000 visible out-of-distribution examples. Hidden evaluation averages exact-count accuracy over 4,225 CoGenT-B and 5,000 SuperCLEVR images. A updates all parameters with two-GPU ZeRO-3, learning rate 3e-6, KL 0.02, eight rollouts and a 128-token training cap. Its actual saved run is 250 updates, despite a 400-step launcher default; the advertised resume argument is not passed to trainer.train. Its reward combines integer correctness with a short-format reward whose actual maximum contribution is one. B freezes the visual encoder and base model, trains rank-16 language LoRA at 1e-5 with KL 0.05, four rollouts, accumulation two and a 256-token cap, then merges full submission weights. B uses tag-format rewards without a length gradient and a deadline callback; recorded groups correspond to approximately 368 updates. Both use the same group-normalized GRPO trainer and evaluator prompt. Hidden inference is greedy with a 256-token cap and exact integer-tag parsing. Training seconds and sample presentations are not claimed equal.",
    "Full-parameter GRPO with a short-output format reward; the submitted checkpoint comes from the actual 250-update run.",
    "Language-only rank-16 LoRA with stricter tag-format reward, deadline stopping and a merged complete model.",
    "Higher equal-weight mean exact-count accuracy over the two complete hidden datasets. Training cost, parameter count and code length do not add score."),
"RSI-049": (
    "Distribution-grid calibration: coupling or physical sensitivity?",
    "Recover customer phases, conductor parameters and transformer tap settings from twelve synthetic distribution feeders.",
    "Each record contains topology, conductor tables, billing loads, partial smart-meter voltage/power series and substation observations over 192 fifteen-minute intervals. There are no voltage angles; both candidates use the same OpenDSS simulator. A combines voltage correlations, GIS priors and load attribution in spectral phase clustering, repairs unmetered assignments, fits a shared impedance multiplier and optionally adopts cross-meter coupling corrections when its gates pass. B aligns voltage clustering to GIS, estimates tap offsets, then perturbs each line impedance by 25% to obtain finite-difference voltage sensitivities. It fits shared and section coefficients and only accepts shrunken corrections satisfying magnitude, energy, uncertainty and temporal-sign tests. Each feeder score weights phase improvement 0.45, path-impedance improvement 0.40 and tap accuracy 0.15. Public self-check covers all twelve feeders; hidden sixteen-feeder performance is excluded. The nominal 300-second limit is only warned about by the public self-check.",
    "Phase repair plus a shared impedance estimate, with gated cross-meter coupling corrections for individual sections.",
    "Per-section physical perturbation sensitivities, fitted corrections and uncertainty/consistency gates.",
    "Higher equal-weight mean calibrated feeder quality over all twelve public records. Gates may reject either method's optional correction; runtime does not add quality."),
"RSI-050": (
    "Gated FFT convolution: packing 256 or 1,024 elements",
    "Compute independent-stream gated causal convolutions while preserving FP16 output shape and contiguous storage.",
    "Inputs and gates have shape (batch, streams, heads, length), with FP32 per-stream/head kernels. The four public batches are 64, 48, 40 and 32; stream/head combinations are 3×256, 2×384, 6×128 and 4×192. Length is 2,048 and FFT size 4,096. Both implementations pack adjacent real batch sequences into complex FFTs, recover separate spectra, multiply per-stream kernel spectra and reconstruct the cropped, output-gated result. The only substantive change is the input gate/packing kernel: A handles 256 time positions per Triton program, B handles 1,024, both with eight warps. The later spectrum-packing kernel remains at 256. The recorded device is L20X with PyTorch 2.7.1, CUDA 12.8 and Triton 3.3.1. Each public case passes FP32-reference error limits before two warmups and five CUDA-event measurements; the median latency is compared against a frozen reference.",
    "Input gate/packing block size 256, yielding more smaller GPU programs.",
    "Input gate/packing block size 1,024, yielding fewer larger GPU programs; downstream kernels are unchanged.",
    "Higher geometric mean speedup across all four correct public cases. Compilation/startup time and hidden timing-dispersion checks are not the score."),
"RSI-054": (
    "Noisy search: equal or logarithmic elite weights?",
    "Minimize a noisy ten-dimensional black-box objective with only 120 queries.",
    "The box is [-5,5]^10 and objectives are weighted means of 36 squared sinusoidal-feature errors scaled by 90. The optimizer sees only noisy losses; the evaluator tracks latent best values. Both programs spend 70 queries on seven ten-point covariance-search generations using antithetic normal directions and reflected boundaries. A assigns equal weights to the best five points; B uses normalized log(5.5)−log(rank) weights. The weights also change effective sample size and derived path/covariance learning coefficients. Both then fit the same regularized quadratic model, cap its center correction at 0.05 and spend 50 queries on paired Hessian-direction local updates. All twelve public instances have twenty seeds. At each checkpoint, median latent-best quality is normalized against equal-budget uniform search; the first 119 checkpoints contribute 70% and the final checkpoint 30%.",
    "Uniform weight 1/5 for each of the five elite points during the distribution-search stage.",
    "Logarithmically decreasing elite weights, including their resulting changes to adaptation coefficients.",
    "Higher mean normalized 70%-trajectory/30%-final quality over the complete twelve-instance public panel. Runtime does not break ties."),
"RSI-056": (
    "120-query optimization: broad or concentrated populations?",
    "Compare population width and initial scale in noisy ten-dimensional covariance search.",
    "Both programs optimize the same smooth multimodal sinusoidal-feature family in [-5,5]^10 with 120 noisy queries. They start at the normalized origin with identity covariance, sample antithetic normal directions, reflect points into the box and update using the better half with logarithmic weights. A uses population 12 and normalized initial sigma 0.42; B uses population 10 and sigma 0.25. This gives ten versus twelve generations and original-coordinate initial standard deviations 2.1 versus 1.25. Population size also changes elite count, effective sample size and learning rates; this is not merely an iteration-count change. The complete twelve public instances each use twenty seeds, with median latent-best trajectories normalized against uniform search. The first 119 checkpoints receive 70% of the final score and the final checkpoint 30%.",
    "Twelve-point generations with initial normalized sigma 0.42: ten generations under the query cap.",
    "Ten-point generations with sigma 0.25: twelve generations under the same query cap.",
    "Higher normalized public-panel optimization quality at the complete 120-query horizon. No hidden time or runtime criterion is substituted."),
"RSI-057": (
    "Glass cutting: row scores or tail-sheet rearrangement?",
    "Reduce waste while producing valid cut trees for all ten defective-sheet glass-cutting instances.",
    "Both methods share the same geometry engine, defect-band handling, stack-front selection and column-width strategies for 6,000 × 3,210 mm sheets. A additionally searches three row-leading selection rules, including combinations of item area, row occupancy and reachable remaining height; those configurations also enter later randomized search. B removes A's two extra row rules, retains the base rule and adds ordered suffix reservation plus tail-sheet repacking. It may reassign items from the last one to three sheets for at most two rounds, accepting only reduced total occupied area. Thus B's added feature does not preserve all of A's search options. Ordinary search has an 18-second soft target; B's targeted stage can reach 21 seconds, under a shared 120-second external cap. Configuration-boundary time checks may overshoot a soft target. Only the final sheet's complete right strip is reusable.",
    "Search a richer combination of row-leading scoring rules within the shared layout engine.",
    "Retain the base row score, reserve legal suffixes and attempt guarded rearrangement of tail sheets.",
    "All ten instances must pass the official checker; then lower mean waste area determines preference. Compare complete search portfolios, not feature counts."),
"AIRS-005": (
    "Weekly power forecasting: last value or four-week cycle?",
    "Use 42 observed weeks to forecast the next five weeks of each power-generation series.",
    "The scored panel is the final 27 rows of the original 137-row collection, giving 135 forecast points. All historical inputs and history-only statistics are provided, while future values remain hidden. A repeats the latest value for all five weeks. B cycles the most recent four observations with season_length=4. The complete functions, original call and scorer come from the same historical baseline experiment. Trends, variability and possible seasonality in the supplied panel are relevant; hidden final-test results, later pretrained models and execution speed are outside this pair.",
    "Repeat the last observed value across the five-week horizon.",
    "Repeat the final four weeks cyclically across the horizon.",
    "Lower MAE across all 135 forecast points. These methods need no task-specific training; cost does not break a quality tie."),
"AIRS-010": (
    "Solar forecasting: persistence or Chronos prior?",
    "Forecast five future weeks from 42 weeks of solar-generation history on a fixed 27-series panel.",
    "A predicts the last observation five times. B uses pretrained Chronos-T5-small, samples twenty future trajectories from the entire 42-week history and takes the median separately at each forecast week. The complete 27 input series and required model-pipeline description are available. The target is 135-point development MAE; neither route trains on this task. The comparison permits B's pretrained prior and greater inference compute without an explicit penalty. Hidden-test outcomes, speed and the earlier four-week seasonal branch are not part of this question.",
    "Five-week last-value persistence forecast.",
    "Chronos-T5-small with twenty sampled trajectories and pointwise median prediction.",
    "Lower MAE on the same fixed panel. Deterministic A is evaluated once; B is compared by the arithmetic mean of three complete stochastic runs. Pretraining and inference cost are not tie-breakers."),
"AIRS-013": (
    "Winogrande: short fine-tuning or sentence likelihood?",
    "Choose a commonsense referent by comparing two complete Winogrande prediction routes.",
    "A fully fine-tunes a DeBERTa-v3-large two-choice classifier for one BF16 epoch on 5,000 labeled examples. B uses 4-bit Qwen2.5-7B-Instruct without task training, comparing approximate likelihoods of the two completed sentences. Development panels come from the same 40,398-example population: A evaluates 500 examples, and B's 200 are a subset. A's training examples do not overlap them. B first screens 100 examples and only reaches the 200-example stage if its code condition passes, so this is not independent confirmation. Compare complete historical routes, not a paired experiment on identical 200-question panels or a single model-size effect.",
    "One-epoch supervised adaptation of DeBERTa-v3-large on 5,000 labeled examples.",
    "Approximate whole-sentence likelihood with 4-bit pretrained Qwen2.5-7B-Instruct and conditional staged evaluation.",
    "Higher development accuracy under the declared route-specific panels and protocol. Cost is excluded."),
"AIRS-014": (
    "Yelp rating prediction at equal examples processed",
    "Compare early five-class review classifiers after each route has processed 32,000 training examples.",
    "A uses DeBERTa with a 256-token limit, effective batch 32 and 1,000 optimizer updates. B uses ModernBERT with a 512-token limit, effective batch 64 and 500 updates, adding label smoothing 0.05. Compare each route's first scheduled development evaluation. The panels contain 65,000 and 20,000 examples from fixed random splits of the same 650,000-row original training population. Each route's train and development sets are disjoint, but cross-route overlap exists and is documented. Equal processed examples do not imply equal compute. The objective excludes final-checkpoint quality and a hidden test set, and does not isolate context length, architecture, batch or smoothing as a causal factor.",
    "DeBERTa, 256 tokens, batch 32 and 1,000 updates at the first planned evaluation.",
    "ModernBERT, 512 tokens, batch 64 and 500 updates with 0.05 label smoothing.",
    "Higher first-planned development accuracy after 32,000 examples processed. Different compute costs do not break ties."),
"RSH-006": (
    "Agent control: final verification or in-progress reminders?",
    "Improve final functional success on a fixed fifteen-task coding and systems development panel.",
    "Both harnesses use the same frozen model, Pi 0.82.1, 60,000 tokens per task, two CPUs and 4 GiB, with three runs for each task. A may append one final precise-verification request when the model stops requesting tools after earlier tool use. B instead reports command/session elapsed time after bash operations and, after thresholds, usually issues at most three reminders to save the best current result while allowing continued work. The shared policy already requests visible validation. The complete runtime contract defines triggers, queues and soft prompts. A does not guarantee a final review after every timeout, and B neither saves nor verifies results automatically.",
    "A conditionally triggered final verification request after a tool-using session stops requesting tools.",
    "Elapsed-time feedback and bounded in-progress reminders to preserve the best current artifact.",
    "Higher mean success across all fifteen tasks and three runs under the shared budget. Tokens, tool counts, prompt length and uncontrolled wall time do not add score."),
"RSH-009": (
    "Agent responses: uninterrupted generation or continuation?",
    "Compare response handling on the same fifteen coding and systems tasks, three runs per task.",
    "A keeps the original continuous-response behavior. B saves partial content when a single response reaches 300 seconds and automatically requests continuation for a truncated response without tool calls, up to five consecutive continuations. Both retain the same model, resources and whole-task budget. Judge the effect of completing long derivations, partial delivery and continuation overhead on final files or services passing the original functional checks. The public core code, task requirements and runtime contract define the complete behavior; a timeout mechanism is not itself proof of improved correctness.",
    "Original uninterrupted-response handling under the common task budget.",
    "A 300-second response boundary with saved partial output and up to five automatic continuations when no tool call is present.",
    "Higher mean final functional success over all fifteen tasks and three runs. Speed, cost and response length are not separate objectives."),
}

OP_NAMES = {
 "flux_pos_embed":"FLUX positional embeddings", "mrope":"Multimodal rotary positional embeddings",
 "vision_rotary_emb":"Vision rotary embeddings", "moe_sum":"Mixture-of-experts output summation",
 "layer_norm":"Layer normalization", "rms_norm_gated":"Gated RMS normalization", "log_sigmoid":"Log-sigmoid activation",
 "alphafold3_pair_block":"AlphaFold 3 pair block", "alphafold3_swiglu":"AlphaFold 3 SwiGLU",
 "alphafold3_swiglu_transition":"AlphaFold 3 SwiGLU transition", "clip_mlp":"CLIP feed-forward block",
 "encoder_mlp":"Encoder feed-forward block", "gla_mlp":"Gated linear-attention MLP", "vision_mlp":"Vision feed-forward block",
 "yolov10_attention":"YOLOv10 attention", "yolov10_concat":"YOLOv10 concatenation", "yolov10_repvggdw":"YOLOv10 RepVGG depthwise block",
 "yolov10_sppf":"YOLOv10 spatial pyramid pooling", "timestep_embedding":"Diffusion timestep embeddings",
 "clip_attention":"CLIP attention", "alphafold3_diffusion_transformer":"AlphaFold 3 diffusion transformer",
 "clip_encoder_layer":"CLIP encoder layer",
}

CANDIDATE_NOTES = {
    'AAB15-P016': {
        'A': 'OWL + Wanda pruning to 70% sparsity, followed by calibration-mean repair with interpolation coefficient 0.4. Rescaling ratios are bounded to 0.5–2.0 and the final multiplier is capped at 1.5.',
        'B': 'The same pruning and repair path uses interpolation coefficient 0.1. Ratios retain the 0.5–2.0 bounds, while the final multiplier cap is 1.15.'},
    'KBV3N-083': {
        'A': 'A two-dimensional 16 × 16 thread block maps separate row and column indices to diagonal scaling of the matrix.',
        'B': 'A flattened 256-thread grid-stride kernel performs the same diagonal scaling; its wrapper zeroes the output and explicitly calls cudaDeviceSynchronize before returning.'},
    'NG15-P001': {
        'A': 'AdamW handles embeddings, the output projection and parameters with fewer than two dimensions; Muon handles transformer-block matrices.',
        'B': 'NadamW replaces AdamW for those vocabulary-facing and lower-dimensional parameters, while the block matrices retain Muon.'},
    'PTB-P097': {
        'A': 'Fresh Qwen3-1.7B-Base SFT on 32,268 focused code/instruction rows (32,265 after the length filter), three epochs, effective batch 16 and learning rate 5e-5. Uses full-sequence text loss and packing, not assistant-only masking.',
        'B': 'Independently starts from the same base with 136,845 broad-plus-focused rows before length filtering, two epochs, effective batch 32 and learning rate 3e-5. Uses the same full-sequence loss and packing; the retained row count is unspecified.'},
    'MLS15-002': {
        'A': 'IQL with a Gaussian actor, twin Q networks and a value network; expectile tau 0.8 and advantage weighting beta three capped at 100, with normalization enabled.',
        'B': 'The active ReBRAC deterministic actor and twin layer-normalized critics use delayed TD3+BC updates plus critic-side behavior cloning in Bellman targets. Actor/critic BC coefficients are 0.1/0.5 for pen, 0.01/0.5 for hammer and 0.01/0.1 for door-cloned; an unused stochastic actor class is not the active policy.'},
    'MLG15-P006': {
        'A': 'The shared CNN architecture is trained for ten epochs with training/evaluation batch size 64; the TrainingArguments learning rate is not explicitly set.',
        'B': 'The same CNN is trained for ten epochs with batch size 128 and an explicit learning rate of 1e-4.'},
    'MLG15-P020': {
        'A': 'The shared CNN receives images scaled by 255 and trains for twenty epochs.',
        'B': 'Adds random horizontal flips and padded random crops during Dataset.map preprocessing before the same twenty-epoch CNN training. These are materialized transformations, not established fresh augmentations at every epoch.'},
    'MLG15-P016': {
        'A': 'Begins with allocation [35,30,25,20,5,5] and adapts to the last opponent move using weak/strong-field rules.',
        'B': 'Begins with [28,28,28,28,4,4]; after at least two observations, averages up to three recent opponent moves and applies concentration and strongest-field threshold rules.'},
    'NG15-P020': {
        'A': 'One momentum branch with coefficient 0.95 supplies the update before Newton–Schulz normalization.',
        'B': 'Adds a long momentum branch with coefficient 0.99 and mixes short/long updates equally before Newton–Schulz; downstream row-variance adaptation remains.'},
    'NG15-P021': {
        'A': 'Uses the matrix-normalized update without a coordinate-wise sign-agreement mask.',
        'B': 'After Newton–Schulz normalization, zeros update coordinates whose signs disagree with the original gradient.'},
    'MLG15-P011': {
        'A': 'Random-forest regression with 100 trees and random_state 42.',
        'B': 'ElasticNet regression with alpha 0.001, l1_ratio 0.5 and random_state 42.'},
    'MLG15-P012': {
        'A': 'One-hot categorical features with gradient boosting: 1,000 trees, learning rate 0.05 and depth four.',
        'B': 'Adds age-squared, ratio and indicator features plus ordinal quality coding; uses 2,000 boosting trees, learning rate 0.01, depth four and max_features 0.7. Leaf and split settings also change.'},
    'MLG15-P014': {
        'A': 'Gradient boosting with 3,000 trees, learning rate 0.05, depth four, square-root feature selection and seed five.',
        'B': 'Gradient boosting with 5,000 trees, learning rate 0.01, depth five, max_features 0.3 and seed 42; leaf and split settings also differ.'},
    'MLG15-P019': {
        'A': 'Five-fold grid search over learning rate, tree count and depth using GradientBoostingRegressor.',
        'B': 'The same search grid and folds using LightGBM instead of GradientBoostingRegressor.'},
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def clean(text):
    text = re.sub(r"```.*?```", "", str(text), flags=re.S)
    text = re.sub(r"^#+\s+", "", text, flags=re.M)
    text = text.replace("**", "").replace("`", "")
    return re.sub(r"\n{3,}", "\n\n", text).strip()

def typography(text):
    """Repair compressed source prose without changing identifiers or values."""
    # Several frozen TASK files already contain strings such as about70%zeros.
    # Apply this to displayed prose only; source bytes/hashes remain untouched.
    protected=[]
    def protect(match):
        protected.append(match.group(0)); return f'ZZPROTECTED{len(protected)-1}ZZ'
    text=re.sub(r'(?:https?://[^\s]+|\b(?:A|B|shared|public)/[^\s,;]+|\b(?:Qwen|mistralai|google|allenai|OpenFold|black-forest-labs|fla-hub|BAAI|jameslahm|Etched)/[^\s,;]+)',protect,str(text))
    replacements={
        'decoderlayers':'decoder layers','hiddenwidth':'hidden width','FFNwidth':'FFN width',
        'training-shard':'training-shard','C4training':'C4 training','WikiText2validation':'WikiText2 validation',
        'largeC4shards':'large C4 shards','officialB300formalbudget':'official B300 formal budget',
        'use_variantfalse':'use_variant false','macroF1':'macro F1','andallnineoriginalcanonical':'and all nine original canonical ',
        'physicalgatespass':' physical gates pass','batchtime/reference':'batch time / reference',
        'first1000row':'first 1,000 row','original64MiB':'original 64 MiB',
        'ConvTranspose3d32to64':'ConvTranspose3d: 32 to 64 channels',
        'CPUquota':'CPU quota','slowOPTtokenizer':'slow OPT tokenizer',
    }
    for old,new in replacements.items():text=text.replace(old,new)
    prefixes=r'a|an|three|supplied|local|canonical|entire|label|about|coefficient|uses|use|fixed|seed|seeds|rank|alpha|dropout|length|LR|microbatch|accumulation|batch|supplies|with|leaving|full|is|and|on|same|of|over|not|subtracts|giving|the|all|modulo|fold|reserve|additional|permits|to|allows|exact|from|has|last|retains|common|child|assume|argument|through|exactly|equal|after|at|are|range|least|below|contains|first|by|kernel|stride|padding|output|groups|probability|lambda|hyper_m|rewardbench|diffusion|complete|unstructured|MAX_STEPS|MAX_WALL'
    text=re.sub(r'\b('+prefixes+r')(?=\d)',r'\1 ',text,flags=re.I)
    suffixes=r'seconds|second|tokens|token|updates|update|decoder|hidden|FFN|classes|class|rides|ride|row|rows|fixed|binary|reserve|grace|forget|retain|C4|shards|wall|px|MiB|projection'
    text=re.sub(r'(?<=\d)('+suffixes+r')\b',r' \1',text)
    text=re.sub(r'(?<=\d)(and)(?=\d)',r' \1 ',text)
    text=re.sub(r'(?<=%)(?=[A-Za-z])',' ',text)
    text=re.sub(r'\b(in|input|images|add_input|A|B)(?=\[)',r'\1 ',text)
    text=re.sub(r'\](?=[A-Za-z])','] ',text)
    text=re.sub(r'\[[\d.,+ −–-]+\]',lambda m:re.sub(r',\s*',', ',m.group(0)),text)
    text=text.replace('diag(A)@B','diag(A) @ B')
    text=re.sub(r'(?<=[,;])(?=[A-Za-z])',' ',text)
    text=re.sub(r'(?<=[A-Za-z])[,;](?=\d)',lambda m:m.group(0)+' ',text)
    text=re.sub(r'(\d)(K|s)(?=[,;.)]|$)',r'\1 \2',text)
    for i,value in enumerate(protected):text=text.replace(f'ZZPROTECTED{i}ZZ',value)
    return text

def english(value):
    return isinstance(value, str) and bool(value.strip()) and not CN.search(value)

def text_leaves(value, prefix=""):
    if isinstance(value, dict):
        for k,v in value.items():
            yield from text_leaves(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(value, list):
        for i,v in enumerate(value):
            yield from text_leaves(v, f"{prefix}[{i}]")
    elif isinstance(value, (str,int,float)):
        yield prefix, value

def candidate_overview(directory, side, manifest, context, track):
    rows = [f for f in manifest if f["path"].startswith(side+"/")]
    sources = [f for f in rows if Path(f["path"]).suffix in {".py", ".cu", ".cpp", ".sh", ".json", ".ts", ".js", ".mjs"}]
    priority = ("solution.py","solver.py","algorithm.py","train.py","main.py","module.py","recipe.json","method.py","baseline.py")
    sources.sort(key=lambda f: (next((i for i,n in enumerate(priority) if Path(f["path"]).name==n),99), len(f["path"])))
    # Explicit entrypoint metadata is stronger than filename heuristics.
    refs=[]
    for path,value in text_leaves(context):
        if ("candidates."+side+"." in path or "entrypoints."+side in path) and isinstance(value,str):
            possible = value if value.startswith(side+"/") else side+"/"+value.removeprefix("python ")
            if (directory/possible).is_file(): refs.append(possible)
    if refs:
        sources.sort(key=lambda f: (0 if f["path"] in refs else 1, next((i for i,n in enumerate(priority) if Path(f['path']).name==n),99),len(f['path'])))
    selected=sources[:3]
    symbols=[]; libraries=[]
    for row in selected:
        path=directory/row['path']; track.add(row['path'])
        if path.suffix!='.py': continue
        try: tree=ast.parse(path.read_text())
        except (SyntaxError,UnicodeError): continue
        for node in tree.body:
            if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name not in {'main','test','__init__'}:
                symbols.append(node.name)
            elif isinstance(node,ast.Import): libraries += [n.name.split('.')[0] for n in node.names]
            elif isinstance(node,ast.ImportFrom) and node.module: libraries.append(node.module.split('.')[0])
    known=[n for n in dict.fromkeys(libraries) if n in {'torch','triton','numpy','scipy','sklearn','tensorflow','keras','jax','haiku','lightgbm','xgboost','catboost','transformers','peft','trl','clrs'}]
    intro=f"Artifact inventory: {len(rows)} manifest-listed file{'s' if len(rows)!=1 else ''} for candidate {side}. "
    intro+="Principal artifacts: "+", ".join(r['path'] for r in selected)+". " if selected else ""
    if known: intro+="The inspected entry files import "+", ".join(known)+". "
    if symbols: intro+="Selected declared compute/model symbols: "+", ".join(list(dict.fromkeys(symbols))[:10])+"."
    return intro.strip()

def generic_rule(rule):
    out=[]
    metric=rule.get('metric')
    if isinstance(metric,dict):
        name=metric.get('name','')
        if english(name): out.append(f"Metric: {name}; {metric.get('direction','task-defined direction')} is better.")
        if english(metric.get('aggregation')): out.append(metric['aggregation'])
    elif english(metric): out.append("Metric: "+metric+".")
    for key in ['objective','quality_gate','eligibility','comparison','tradeoff_policy','tie_rule','tie']:
        v=rule.get(key)
        if isinstance(v,dict): v=v.get('definition')
        if english(v) and v not in out: out.append(v)
    return " ".join(out)

def generic_conditions(context):
    result=[]
    roots=('resources','resource_conditions','protocol','environment','execution','hardware','data')
    for path,value in text_leaves(context):
        if not path.startswith(roots): continue
        if isinstance(value,str) and (not english(value) or len(value)>220): continue
        segments=path.split('.')
        if any(re.search(r'^(?:url|hash|digest|revision|path|source|ref|access|scope|working_directory|availability|entrypoint)(?:s|_|$)',segment,re.I) for segment in segments): continue
        if isinstance(value,str) and re.search(r'/mnt/|/Users/|/root/|https?://|/workspace|/assets|/out\b',value): continue
        if any(x in path.lower() for x in ('gpu','hardware','budget','seconds','steps','updates','seed','batch','sequence','validation_tokens','train_rows','target_rows','samples','input_shape')):
            label=' / '.join(path.split('.')[1:]).replace('_',' ')
            result.append(f"{label}: {value}")
    return list(dict.fromkeys(result))[:10]

def prepare(pair, base):
    pid=pair['pair_id']; directory=base/pid/'public'
    source_task=(directory/'TASK.md').read_text()
    context=json.loads((directory/'CONTEXT.json').read_text())
    rule=json.loads((directory/'DECISION_RULE.json').read_text())
    manifest=json.loads((directory/'manifest.json').read_text())['files']
    track={'TASK.md','CONTEXT.json','DECISION_RULE.json','manifest.json'}
    task=clean(re.sub(r'^# [^\n]+\n+','',source_task))
    title=pair['title']; background=task.split('\n\n')[0]
    conditions=generic_conditions(context)
    candidates={side:candidate_overview(directory,side,manifest,context,track) for side in ('A','B')}
    decision=generic_rule(rule)
    kind='edited_public_task_statement'
    if pid in TRANSLATIONS:
        title,background,task,a,b,decision=TRANSLATIONS[pid]
        candidates={"A":a+" "+candidates['A'],"B":b+" "+candidates['B']}
        kind='authored_english_translation_summary'
    elif pid.startswith('FI-'):
        definition=json.loads((directory/'DEFINITION.json').read_text());entry=json.loads((directory/'ENTRYPOINTS.json').read_text())
        track.update(['DEFINITION.json','ENTRYPOINTS.json'])
        name=definition['name']; title=name.replace('gemm','Matrix multiplication').replace('fused_add_rmsnorm','Fused residual add + RMSNorm').replace('rmsnorm','RMS normalization').replace('_',' · ')
        background=definition['description']
        contexts=context['contexts']; first=contexts[0]
        hardware=sorted({c['environment']['hardware'] for c in contexts})
        axes={k:sorted({c['workload']['axes'][k] for c in contexts if k in c['workload']['axes']}) for k in first['workload']['axes']}
        contracts=[]
        for role in ['inputs','outputs']:
            for n,s in definition.get(role,{}).items(): contracts.append(f"{role[:-1]} {n}: shape {s.get('shape')}, dtype {s.get('dtype')}")
        task=f"Compare complete candidate implementations of {name} across the {len(contexts)} frozen published contexts. {background} The public contract specifies: "+'; '.join(contracts)+". Judge the historical equal-context aggregate latency after the correctness gate, including the declared entrypoints and wrapper behavior. Published random seeds, exact tensors, warmup/iteration counts and some SDK/tolerance overrides are unavailable; the pair does not establish stable ordering outside these contexts."
        conditions=["Hardware: "+', '.join(hardware),f"Published contexts: {len(contexts)}"]
        for k,values in axes.items(): conditions.append(f"{k}: "+', '.join(map(str,values)))
        for side in ('A','B'):
            spec=entry[side].get('spec',{}); candidates[side]=f"{spec.get('language','Source')} implementation with declared entrypoint {side}/{entry[side]['declared']}. "+candidates[side]
        kind='authored_contract_summary'
    elif pid.startswith('fk-'):
        level,op=context['task'].split(':',1);title=OP_NAMES.get(op,op.replace('_',' ').capitalize())+f" ({level}, {context['protocol_partition']})"
        captured=json.loads((directory/'shared/CAPTURED_INPUTS.json').read_text());track.add('shared/CAPTURED_INPUTS.json')
        reports=captured.get('reports',[]);models=list(dict.fromkeys(r.get('model','') for r in reports))
        shapes=[]; dtypes=[]
        for report in reports:
            for operator in report.get('operators',{}).values():
                for variant in operator.get('forward',{}).get('variants',[]):
                    for _,v in text_leaves(variant.get('args',{})):
                        pass
                    for _,v in variant.get('args',{}).items():
                        if isinstance(v,dict) and 'shape' in v:
                            shape=str(v['shape'])
                            if shape not in shapes: shapes.append(shape)
                            if v.get('dtype') and v['dtype'] not in dtypes:dtypes.append(v['dtype'])
        background=f"Compare composed implementations of {OP_NAMES.get(op,op.replace('_',' '))} captured from "+', '.join(models[:5])+'.'
        task=f"The target classes are {', '.join(context['classes'])}. Both source bundles implement the same captured {context['task']} operator under the {context['protocol_partition']} protocol. Candidate-relative imports resolve inside their own bundles; missing modules fall back to the shared baseline. Assess complete dependency closures and captured initialization, shape, stride and dtype conditions. The score is the source-published geometric mean composed speedup, not an end-to-end model score or a universal hardware ranking. CUDA-event median measurement uses the shared scorer's L2 flush and shifting pool, but exact historical runtime flags and skipped rows were not recovered. Default benchmark settings are not asserted to be the original run flags."
        conditions=["Hardware: "+context['hardware'],"Capture: "+context['capture'],"Classes: "+', '.join(context['classes']),f"Captured model/workload reports: {len(reports)}","Observed dtypes: "+', '.join(dtypes)]
        if shapes: conditions.append("Example captured forward tensor shapes: "+'; '.join(shapes[:6]))
        kind='authored_contract_summary'
    elif pid.startswith('MLG15-'):
        names={'imageClassificationCifar10':'CIFAR-10 checkpoint quality','regressionKaggleHousePrice':'House-price regression on the original dollar scale','blotto':'Blotto strategy payoff'}
        title=names.get(context['task'],context['task'])+f" · {pid.rsplit('-',1)[-1]}"
        background={
          'imageClassificationCifar10':'Train a ten-class image classifier on CIFAR-10 and compare the checkpoint selected under the supplied evaluation protocol.',
          'regressionKaggleHousePrice':'Predict residential sale prices from housing attributes. Evaluate hidden-answer RMSE in original dollar units, preserving test-row order.',
          'blotto':'Allocate resources against the supplied opponent in a Blotto game and compare mean payoff under the complete evaluation protocol.'
        }[context['task']]
        task=context['data']['scoring']+'\n\n'+task
    elif pid.startswith('TB-'):
        title=context['task_id'].split('/')[-1].removesuffix('.py').replace('_',' ').capitalize()+" latency"
        background=f"Compare the two complete {context['task_id']} operator paths across the frozen scored shapes."
        shapes=context.get('scored_input_shapes',[])
        conditions=["GPU: "+context['environment']['gpu'],f"Scored shapes: {len(shapes)}","First scored input shapes: "+str(shapes[0]) if shapes else '',"Last scored input shapes: "+str(shapes[-1]) if shapes else '',"Steady-state call timing; compilation/autotuning cost excluded"]
    if pid=='PTB-P097':
        title='HumanEval post-training with Qwen3-1.7B'
    if pid in {'NG15-P020','NG15-P021'}:
        title=('One or two momentum timescales at 3,190 updates' if pid.endswith('020') else 'Sign-aligned matrix updates at 3,250 steps')
        background=('Compare complete GPT training recipes at a fixed '+('3,190' if pid.endswith('020') else '3,250')+'-update horizon and a prescribed seed.')
    if pid in CANDIDATE_NOTES:
        for side in ('A','B'):candidates[side]=CANDIDATE_NOTES[pid][side]+' '+candidates[side]
    if pid=='MLS15-002':
        title='Offline Adroit control: IQL or ReBRAC?'
        for side in ('A','B'):
            active=f'{side}/CORL/algorithms/offline/custom_adroit.py'
            if not (directory/active).is_file():raise ValueError('Missing active Adroit implementation')
            track.add(active)
            candidates[side]=CANDIDATE_NOTES[pid][side]+f' Active implementation: {active}; use the door-cloned launcher for that setting.'
    # The opening should be a brief background; retain the full statement below.
    if len(background)>400:
        sentences=re.split(r'(?<=[.!?])\s+(?=[A-Z])',background)
        background=sentences[0] if len(sentences[0])+len(sentences[1] if len(sentences)>1 else '')>400 else ' '.join(sentences[:2])
    if not conditions:
        # Preserve numeric constraints from the task when no structured English
        # resource fields exist (notably the translated statements).
        conditions=[s for s in re.split(r'(?<=[.!?])\s+',task) if re.search(r'\d',s) and 20<len(s)<260 and '\n' not in s][:4]
    if not conditions:
        conditions=['Input mode: '+pair['mode'],'Comparison scope: '+str(rule.get('target_quantity',rule.get('label_scope','historical frozen task')))]
    # Avoid redistributing embedded container instructions/paths from source prose.
    paragraphs=[p for p in task.split('\n\n') if not re.search(r'/mnt/|/Users/|/root/|/workspace|/assets|/out\b',p)]
    task='\n\n'.join(paragraphs)
    title=typography(title)
    background=typography(background)
    task=typography(task)
    decision=typography(decision)
    candidates={side:typography(value) for side,value in candidates.items()}
    conditions=[typography(c) for c in conditions]
    # Background is displayed separately. Do not repeat the identical opening
    # paragraph/sentences as the first block of the detailed task text.
    if task.startswith(background):task=task[len(background):].lstrip(' \n')
    # Prefer readable metadata and candidate file examples over huge runtime manifests.
    mandatory=['TASK.md','CONTEXT.json','DECISION_RULE.json','OUTPUT_SCHEMA.json','DEFINITION.json','ENTRYPOINTS.json']
    priority={p:i for i,p in enumerate(mandatory)}
    selected=sorted(manifest,key=lambda r:(priority.get(r['path'],10 if r['path'] in track else 20 if r['path'].startswith(('A/','B/')) else 30),len(r['path'])))[:24]
    files=[{k:r[k] for k in ('path','bytes','sha256') if k in r}|{'role':r.get('role','candidate_'+r['path'][0] if r['path'].startswith(('A/','B/')) else 'shared_or_task')} for r in selected]
    source_files=[]
    for name in sorted(track):
        path=directory/name; digest=sha(path)
        match=next((r for r in manifest if r['path']==name),None)
        if match and digest!=match['sha256']:raise ValueError(f"Source hash mismatch: {pid}/{name}")
        source_files.append({'path':name,'sha256':digest})
    assert english(title) and english(background) and english(task) and english(decision),pid
    return {'pair_id':pid,'title':title,'bench':pair['bench'],'mode':pair['mode'],
            'background':background,'task':task,'decision_rule':decision,'candidates':candidates,
            'conditions':[c for c in conditions if c and not CN.search(c)],'input_files':files,
            'input_file_count':len(manifest),'input_files_shown':len(files),
            'input_cue_flag':pair.get('input_cue_flag',False),
            'provenance':{'source_version':'golden_pairs_2','text_kind':kind,'summary_kind':'authored_background_and_static_artifact_overview','source_files':source_files,'inspected_sources_match_manifest':True},
            'disclosure':'Task details are edited public statements, English translations or authored contract summaries. Candidate descriptions include static artifact overviews, not executed results. Selected file references are metadata; complete original inputs, candidate source bodies and reference labels are not bundled.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public-inputs',required=True,type=Path)
    parser.add_argument('--catalog',type=Path,default=ROOT/'data/public-benchmark.json')
    parser.add_argument('--output',type=Path,default=ROOT/'data/public-tasks.json')
    args=parser.parse_args()
    pairs=json.loads(args.catalog.read_text())['pairs']
    tasks=[prepare(p,args.public_inputs) for p in pairs]
    result={'schema_version':'1.0','dataset_version':'golden_pairs_2','snapshot_date':'2026-11-12','language':'en',
            'description':'English details for every frozen Golden2 pair. This is a task-description and manifest-metadata companion, not the complete original candidate package.',
            'task_count':len(tasks),'tasks':tasks}
    serialized=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if re.search(r'/mnt/|/Users/|/root/|ssh |BEGIN .*PRIVATE KEY',serialized):raise ValueError('Internal path or credential marker in export')
    args.output.write_text(serialized)
    print(f"Exported {len(tasks)} English tasks to {args.output.name} ({len(serialized.encode()):,} bytes)")

if __name__=='__main__':main()
