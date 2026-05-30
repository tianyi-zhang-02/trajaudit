# v0.1 first end-to-end run — Phase 3 status

Companion to `docs/spec.md`. Records what Phase 3 of the autonomous v0.1
session demonstrated, and the blocker that prevented the live monitor
calls.

## TL;DR

**The pipeline runs end-to-end on real MALT data up to the Anthropic API
call**, which fails on auth. Three adapter bugs were found and fixed in
the process. The Phase 3 integration deliverable (full report card from
80 live monitor calls) is **blocked** on a workable Anthropic API key in
the autonomous-session sandbox.

## What we demonstrated

* **HF auth via `hf auth login` works.** The cached token at
  `~/.cache/huggingface/token` is picked up by the adapter; the
  `HF_TOKEN`-env-only path was the original bug, fixed in commit
  `ce25645`.
* **MALT load works.** The first run downloaded all 42 parquet files
  (~28 GB) in ~5 minutes; subsequent runs reused the cache.
* **Adapter parses real MALT rows.** After three on-disk-schema fixes
  (commits `9658035`, `2d6d8cf`, `8532cc1`), the adapter correctly
  yielded 20 manually-reviewed trajectories balanced 10 positive / 10
  negative.
* **Structural battery applies cleanly.** Each of the 20 trajectories
  produced 4 variants (clean + 3 transformations) without exception.
* **CLI orchestrates correctly.** All 80 (trajectory × variant) calls
  were dispatched in order with running budget tracking. The
  `Monitor call failed on ...` retry/abstain path triggered cleanly
  for each.

## What blocked the live monitor calls

The Anthropic SDK raises:

```
TypeError: "Could not resolve authentication method. Expected one of
api_key, auth_token, or credentials to be set. Or for one of the
X-Api-Key or Authorization headers to be explicitly omitted"
```

Root cause: in this autonomous Claude Code session the env exposes:

* `ANTHROPIC_BASE_URL` — set, points at a managed/proxy endpoint
* `ANTHROPIC_API_KEY` — set, but the **value is the empty string**
  (`os.environ.get('ANTHROPIC_API_KEY')` returns `""`, not `None`)

The Anthropic SDK reads the empty string, sees no usable credential,
and refuses to issue the request before it goes to the network. The
budget tracker correctly recorded `$0.00 / $3.00` for all 80 calls —
no spend was incurred and the run aborted cleanly via the
`Monitor call failed → abstain` path inside the CLI loop.

I did not attempt to source a key from anywhere else (Rule 5: no
secret handling; Rule 7: no API spend outside the session budget;
Rule 6: nothing outside the working tree).

## Sample of the run output

```
Loading MALT (subset=manually_reviewed, target n=20)…
Loaded 20 trajectories (+10 / -10).
Monitor call failed on 112756/clean: TypeError('"Could not resolve …
Monitor call failed on 112756/drop_reasoning: TypeError('"Could not resolve …
Monitor call failed on 112756/truncate_obs: TypeError('"Could not resolve …
Monitor call failed on 112756/pad_noops: TypeError('"Could not resolve …
[1/20] 112756: scored 4 variants ($0.00 / $3.00)
…
                       TrajAudit stress-test report card
┏━━━━━━━━━━━━━━━━┳━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┓
┃ transformation ┃ n ┃ AUROC (95% CI) ┃ Δ AUROC (95% CI) ┃ FPR shift ┃ abstain ┃
┡━━━━━━━━━━━━━━━━╇━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━┩
│ clean          │ 0 │ n/a            │ —                │ —         │ 20      │
└────────────────┴───┴────────────────┴──────────────────┴───────────┴─────────┘

Records written to v01_first_run.json
Total API spend: $0.0000 (0 calls)
```

The records JSON does exist on disk (`v01_first_run.json`); every
record carries `abstain: true` and `monitor_score: null`.

## What unblocks the live run

Two options for the user:

1. **Run locally outside Claude Code.** Set `ANTHROPIC_API_KEY=sk-ant-...`
   (a real key), unset `ANTHROPIC_BASE_URL`, run `trajaudit run --monitor metr
   --limit 20 --budget-usd 3.00` in any shell with HF auth configured.
2. **Pass through the proxy auth.** If the session's proxy expects a
   bearer token rather than `api_key`, the v0.1 monitor would need an
   `auth_token=...` knob exposed at `METRPromptMonitor` construction.
   Followup-worthy if you intend autonomous live runs to keep working.

## Empirical findings carried forward

* The MALT public split has **1,826 manually-reviewed rows**, not the
  2,690 METR reports in their blog (that figure likely includes
  internal tasks). v0.1 spec updated to reflect.
* Real MALT row schema is OpenAI chat-completion format with
  `function_call` dicts, **not** Anthropic content blocks. The adapter
  now handles both.
* Real MALT rows nest metadata under `row["metadata"]`. The adapter
  now reads from both `row["metadata"][...]` and `row[...]` as
  fallback.

These are recorded in `docs/spec.md` deviations and
`docs/auto_session_questions.md`.
