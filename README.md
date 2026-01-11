# SUP: Sycophancy Under Pressure

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
## A trajectory-level evaluation of policy-compliant manipulation in multi-turn AI agents.

What does this repo provide?
- A multi-turn prompt suite (SUP) designed to elicit **sycophancy under social pressure**
- Trajectory-level metrics for **agreement drift**, **correction decay**, and **normative softening**
- An end-to-end, reproducible harness to run **ablation conditions**: (1) baseline, (2) logging-only, (3) runtime enforcement.

The core goal is **measurement-first**: quantify policy-compliant sycophancy that can evade refusal-based or single-turn evaluations.

---

## Why this matters

Sycophancy is often **policy-compliant**: models may avoid explicit rule violations while gradually validating false or autonomy-undermining premises under social pressure. This can undermine decision quality without overt deception.

SUP focuses on **trajectory-level drift**, which single-prompt tests can miss.

## Operational definition (what we measure)

We measure **policy-compliant sycophancy under social pressure**, defined as:

> progressive validation of a false or autonomy-undermining user premise across turns **in contexts where epistemic correction is normatively required**, while remaining broadly policy-compliant (i.e., not triggering obvious refusals).

We intentionally exclude benign empathy, harmless role-play, and legitimate education/persuasion by scoring only scenarios (and turns) where correction is normatively required.

---

## Repo structure

- `data/prompts/` — SUP suite YAML (`suite_v1.yaml`) + held-out set (`suite_v1_heldout.yaml`)
- `data/lexicons/` — epistemic/rapport marker lexicons (transparent features)
- `src/sycop/` — runner, labeling, metrics, stats, plots, and artifact generation
- `runs/` — timestamped run outputs (JSONL transcripts + metrics + tables/figures)
- `report/` — hackathon report and generated assets

---

## Quickstart (reproduce main results)

### 1) Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2) Set your API key

```bash
export OPENAI_API_KEY="your-api-key"
```

### 3) Run the full pipeline (50 scenarios × 6 turns × 3 conditions)

```bash
sycop run --config configs/run_v1.yaml
sycop label --run-id <run_id>
sycop score --run-id <run_id>
sycop report --run-id <run_id> --out report/assets
```

Outputs:

* `runs/<run_id>/transcripts.jsonl` — per-turn transcripts with metadata
* `runs/<run_id>/labels.jsonl` — per-turn labels (agreement/correction/etc.)
* `runs/<run_id>/aggregates.json` — metric means + bootstrap CIs + tests
* `report/assets/table1.md` and `report/assets/fig_*.png` — ready for the report

### Experimental design (ablation conditions)

We replay identical multi-turn trajectories under:

1. **baseline**: no instrumentation, no enforcement
2. **log-only**: instrumentation enabled, enforcement disabled (measurement vs mitigation)
3. **enforce**: runtime intervention that prevents endorsement of contested premises while preserving helpfulness

### Enforcement (for mitigation ablation)

Enforcement is implemented as a narrow, reproducible intervention:

* A **gate** detects when the assistant endorses the contested premise
* A **constrained rewrite** repairs the response to avoid endorsement while remaining empathetic and helpful

We log: whether rewriting occurred, draft vs final response, gate confidence (to avoid "rewriting everything" and to support auditing).

## Reproducibility and metadata

Each run records: exact model identifiers and decoding parameters, suite hash, git commit hash, environment/library info, timestamped run folder with immutable artifacts.


## Limitations

Automated labeling (including LLM-based judgments) is a proxy; we recommend manual audit of a subset. Lexicon-based framing measures can be sensitive to language/style; we treat them as interpretable indicators, not ground truth. Our suite covers a limited set of pressure tactics and does not capture all real-world manipulation strategies.

**What We Are NOT Claiming**

* We are NOT claiming to have solved sycophancy generically.
* We are NOT claiming that empathy is bad (empathy ≠ sycophancy).
* We are NOT claiming that single-turn tests are useless.
* We ARE claiming that policy-compliant manipulation can evade refusal-based evals.
* We ARE claiming that trajectory-level measurement is necessary.

## License

MIT (recommended for hackathon open-source submissions)
