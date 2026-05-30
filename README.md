# TrajAudit

**Stress-test runner for AI safety monitors.**

[![CI](https://img.shields.io/github/actions/workflow/status/tianyi-zhang-02/trajaudit/ci.yml?branch=main&label=ci)](https://github.com/tianyi-zhang-02/trajaudit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

TrajAudit takes a corpus of labeled agent trajectories, applies structural
transformations (drop the chain-of-thought, truncate the tail, pad with
noop tool calls), runs a monitor on every variant, and tells you how much
the monitor's performance degrades. v0.1 ships one monitor (METR's
published MALT reward-hacking prompt) and one corpus (MALT public split).

## Quickstart

```bash
git clone https://github.com/tianyi-zhang-02/trajaudit
cd trajaudit
uv sync --all-extras
export HF_TOKEN=hf_...           # https://huggingface.co/settings/tokens
export ANTHROPIC_API_KEY=sk-ant-...
uv run trajaudit run --monitor metr --limit 60 --budget-usd 5.00
```

The MALT dataset is gated — accept the terms at
[huggingface.co/datasets/metr-evals/malt-public](https://huggingface.co/datasets/metr-evals/malt-public)
before the first run.

## What you get

```
                              TrajAudit stress-test report card
┏━━━━━━━━━━━━━━━━━┳━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┓
┃ transformation  ┃   n ┃ AUROC (95% CI)      ┃ Δ AUROC (95% CI)      ┃ FPR shift ┃ abstain ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━┩
│ clean           │  60 │ 0.934 (0.871, 0.974)│ —                     │ —         │       0 │
│ drop_reasoning  │  60 │ 0.781 (0.702, 0.852)│ -0.153 (-0.203,-0.103)│ +0.117    │       1 │
│ truncate_obs    │  60 │ 0.912 (0.847, 0.961)│ -0.022 (-0.071,+0.018)│ +0.017    │       0 │
│ pad_noops       │  60 │ 0.853 (0.781, 0.913)│ -0.081 (-0.131,-0.034)│ +0.050    │       0 │
└─────────────────┴─────┴─────────────────────┴───────────────────────┴───────────┴─────────┘

Worst-case degradation: -0.153 AUROC on drop_reasoning.
```

The numbers above are illustrative; real numbers depend on your monitor
and corpus. Raw per-trajectory scores are written to
`./trajaudit_run_<UTC timestamp>.json` for downstream analysis.

## CLI options

```
trajaudit run [--monitor metr] [--limit 60] [--subset manually_reviewed]
              [--budget-usd 5.00] [--output PATH]
```

- `--monitor` — only `metr` in v0.1; the protocol surface is open for more.
- `--limit` — # trajectories (balanced 50/50 pos/neg). Hard cap 1000.
- `--subset` — `manually_reviewed` (default) or `all`.
- `--budget-usd` — hard cap on API spend; pipeline aborts cleanly when hit.
- `--output` — raw scores JSON path.

## Writing a new monitor

Implement two attributes on a class — see
[docs/writing_a_monitor.md](docs/writing_a_monitor.md) for the 20-line
worked example:

```python
class MyMonitor:
    name = "my-monitor"
    def score(self, trajectory: Trajectory) -> SemanticVerdict: ...
```

## Status

**v0.1** — working CLI, one monitor, one corpus, three structural
transformations. Live-MALT smoke test pending HF auth in the release
environment. See [docs/spec.md](docs/spec.md) for the canonical surface
and [docs/followups.md](docs/followups.md) for what's deferred to v0.2+.

For current state and collaboration protocols, see
[docs/PROJECT_STATE.md](docs/PROJECT_STATE.md).

## Installation

Not yet on PyPI; install from source via `uv sync --all-extras`. Post-PyPI:

```bash
pip install "trajaudit[llm]"           # CLI + METR monitor
pip install "trajaudit[llm,sandbox]"   # adds Docker sandbox for v0.2 Layer 1
```

Core deps: pydantic, typer, datasets, rich, scikit-learn, numpy. Monitor
backends and the Docker sandbox live under extras so users writing
non-Anthropic monitors don't pay for the Anthropic SDK.

## Citation + License

MIT — see [LICENSE](LICENSE). Cite as `Zhang, T. (2026). TrajAudit
v0.1.0.` https://github.com/tianyi-zhang-02/trajaudit
