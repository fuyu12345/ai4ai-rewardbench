# Homepage design references

Official project pages were reviewed on 11 November 2026. These are information-architecture references; the AI4AI visual system follows FRONTIS VI and uses its own content and components.

| Reference | Observed pattern | Application in AI4AI v0.1 |
| --- | --- | --- |
| [SWE-bench](https://www.swebench.com/) | Dataset tabs, a defined primary metric, a compact leaderboard, and links to detailed results | Keep All / Agent / Reasoning views close to the leaderboard. Show the denominator and score definition beside results. |
| [Terminal-Bench](https://www.tbench.ai/) | Short mission statement, direct task access, and rank / model / agent / score / cost / token columns | Give visitors a clear path from the premise to results and concrete tasks. Keep resource usage visible without overwhelming the main table. |
| [RewardBench](https://github.com/allenai/reward-bench) and its [leaderboard](https://huggingface.co/spaces/allenai/reward-bench) | Separate links for evaluation data, results, and models; explicit documentation of section weighting | Separate data and protocol resources, and document question weighting rather than leave aggregation implicit. The embedded live leaderboard was not inspectable through the text browser. |
| [MLE-bench](https://github.com/openai/mle-bench) | Overall and split scores accompanied by runtime, date, code availability, and grading-report availability; non-comparable submissions separated | Keep provenance and resource conditions beside scores. Mark exceptions and avoid implying that every run used an identical realized budget. |

Recommended flow: a concise research premise and dataset counts; a leaderboard with its metric and baselines; task taxonomy and searchable catalog; paired Reasoning / Agent examples; protocol, limits, and downloadable results.

The first release deliberately avoids account systems, complex dashboards, unverified submission workflows, and paper/DOI links that do not yet exist. Its interaction should help visitors inspect evidence, switch modes, and understand what a score means.
