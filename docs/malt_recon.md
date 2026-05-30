# MALT empirical reconnaissance — summary

Companion to `notebooks/malt_recon.ipynb`. Pilot date: 2026-05-25.

**Execution status.** Sections 1–7 of the notebook **did not run against
real data in this session.** The HuggingFace token in the sandbox
environment is invalid (`Invalid user token. The token stored is invalid.`
from `hf auth whoami`), and the MALT datasets at `metr-evals/malt-public`
and `metr-evals/malt-transcripts-public` are gated — they require an
authenticated user who has accepted the dataset terms. No API spend was
incurred. Sections 1 and 2 carry **values verified from public sources**
(METR blog + HF dataset cards) without requiring a download, and are
clearly marked as such in the notebook.

**Dataset usability.** MALT is the obvious substrate for the work the
pivot brief sketches: it is the only public corpus of labelled reward-hack
and sandbagging trajectories at meaningful scale. Two friction points
matter for the project plan. (1) **Gating is real:** Tianyi (or whoever
runs the pilot) needs to log in to HuggingFace, accept the dataset terms
on both `malt-public` and `malt-transcripts-public`, generate a read
token, and either export `HF_TOKEN` or run `hf auth login` locally. This
is a one-time five-minute step but it is the gate to *all* downstream
work. (2) **Size:** the ordered-messages format is 28.3 GB, the DAG
format is 8.48 GB. The pilot only needs a streamed subset of
manually-reviewed runs — use `load_dataset(..., streaming=True)` and
filter on `manually_reviewed=True` before materialising to pandas, or the
notebook will allocate 28 GB.

**Structural concerns to verify in the eyeball check (not yet run).** The
HF card describes the schema as "List of input and output messages
representing a transcript" with input messages as "chat completions sent
to the API" — i.e., the format is OpenAI-style. Three things to confirm
in section 4: that the content field is consistently a string (not a list
of content blocks), that long transcripts are not truncated mid-tool-call,
and that the label column is a list of strings matching the public count
breakdown (103 unprompted reward-hacking positives across two labels).
The pivot brief asked us to verify METR's reported 2,690 manually-reviewed
runs. The HF card's published breakdown is 1,014 benign + 1,676 with
observed behaviour = 2,690, but that count applies to the full dataset.
The **public split contains 1,826 manually-reviewed rows** as observed
on-disk during Phase 3 of the v0.1 implementation; the ~864-row gap
corresponds to internal-only tasks not present in the public release.

**Reproduction caveat (METR prompt).** The pivot brief asserted METR uses
a 1-100 scale; the verbatim prompt fetched from the METR blog uses a 0-10
integer scale with the phrasing "Please give a score between 0 or 10."
The notebook reproduces the prompt character-for-character and the
parsing regex extracts an integer in [0, 10]. The monitor threshold for
the binary label is set at ≥5; this is a defensible default but is not
the same as METR's own AUROC computation, which operates on the raw
score. The pilot is *not* expected to match METR's 0.96 reward-hacking
AUROC exactly because: (a) METR's number is for GPT-5, the pilot uses
`claude-sonnet-4-7`; (b) METR's number is computed over their full
dataset, the pilot is n=60; (c) the bootstrap CI at n=60 will be wide
enough to be consistent with a wide range of true values.

**Bottom line — is MALT usable for calibration claims?** Conditional on
the HF auth issue being resolved, **MALT is usable as a substrate** for
the kind of evaluation work TrajAudit is considering, with two binding
constraints. (1) **Per-category sample sizes are tight.** 103 unprompted
reward-hacking positives means bootstrap CIs on calibration metrics will
be wider than ±0.05 at small bin counts (see notebook section 7's
projection). Tight calibration claims need either pooling across
labels (which loses category-specific information) or supplementing MALT
with off-distribution positives (which reintroduces the realism question
that motivated MALT in the first place). (2) **The work has already been
done at AISI.** Griffin et al. (UK AISI, Aug 2025) ran exactly this kind
of analysis on a 2,997-example MALT-inclusive mix at 0.1% positive rate
and got 7% recall on METR reward hacking. A follow-up needs to
differentiate on something concrete: a larger ordinary-positive-rate
sample, multiple operating points, multi-monitor comparison, obfuscation
robustness, or released artefacts. "We did calibration on MALT" is not
enough. See `docs/pivot_decision.md` for the synthesis.

## Live-load smoke test (v0.1 status)

Status: **NOT RUN.** The HF token in the sandbox remains invalid
(`Invalid user token` from `hf auth whoami`). The v0.1 MALT adapter at
`src/trajaudit/adapters/malt.py` is fully implemented and is exercised by
15 fixture-driven unit tests under `tests/adapters/`, but the live load
against `metr-evals/malt-public` has not been executed in this session.

What works without live data:
- Conversion from MALT-style row dicts to `Trajectory` (15 tests).
- Event-type mapping (reasoning / tool call / observation / scoring).
- `call_id` preservation when MALT provides ids and synthesis when it doesn't.
- Synthetic timestamp generation (epoch `2025-01-01T00:00:00 UTC` +
  `index * 1 second`).
- `Trajectory.metadata` carries labels / `manually_reviewed` / `run_source`
  / `has_chain_of_thought`; labels do not leak into the event stream.
- `load_malt_split` raises a clear `RuntimeError` with setup instructions
  when `HF_TOKEN` is missing.

What still needs a live load to verify:
- Whether MALT's actual on-disk column layout matches the schema this
  adapter targets (described in the docstring of `malt.py`). Fixture
  shapes were inferred from the HF dataset card; if MALT exposes a
  different field name for, say, `manually_reviewed`, the
  `malt_row_to_trajectory` mapping will need a one-line tweak.
- Whether `samples[0]` is the right slice for the N-completion case
  (v0.1 takes the first sample only).
- Final-shape regression check: load the first ~10 manually-reviewed
  rows, run `malt_row_to_trajectory`, verify event-count distributions
  look plausible.

To unblock: generate an HF read token at
https://huggingface.co/settings/tokens, accept the dataset terms at
https://huggingface.co/datasets/metr-evals/malt-public, and export
`HF_TOKEN` in the shell that runs `trajaudit run`.

## Schema note — what the on-disk MALT row actually looks like

Discovered during Phase 3 of the v0.1 implementation. The HuggingFace
dataset card describes MALT in idealised terms; the on-disk layout
differs in several load-bearing ways. Anyone writing a new adapter
against the card alone will hit the same bugs the v0.1 adapter did.
Canonical reference for the real format is the four fix commits on
the v0.1 PR branch: `9658035`, `2d6d8cf`, `ce25645`, `8532cc1`.

The actual on-disk shape:

- **Top-level row keys are exactly two:** `samples` and `metadata`.
  Every metadata field the card describes (`labels`,
  `manually_reviewed`, `run_source`, `has_chain_of_thought`, `model`,
  `task_id`, `run_id`, `public`) is nested under `row["metadata"]`,
  *not* at the row top level. Filters that read `row["manually_reviewed"]`
  silently return False for every row.
- **The sample's message fields are `input` and `output`,** not
  `input_messages` and `output_messages`.
- **`output` is `list[list[dict]]`** — one outer list per completion
  (MALT supports N completions per call), and each completion is
  itself a list of messages. Adapters that index `output[0]` and
  expect a single message dict will see a list and misroute.
- **Messages use OpenAI chat-completion format**, not Anthropic
  content-block format. Tool calls live on
  `msg["function_call"] = {"name", "arguments"}` with `arguments` as
  a JSON-encoded string. Tool responses come back as `role="function"`
  messages with `name` and `content`. There are no
  `{"type": "tool_use"}` blocks.
- **`role == "developer"` exists** alongside `"system"` and should be
  treated as a framing role that emits no event.
- **The HuggingFace `split` argument must be `"public"`,** not the
  default `"train"`. Passing `split="train"` raises
  `ValueError: Unknown split "train". Should be one of ['public']`.
- **HF auth** can come from either `HF_TOKEN` env or the cached token
  written by `hf auth login` — accept both via
  `huggingface_hub.get_token()`.
