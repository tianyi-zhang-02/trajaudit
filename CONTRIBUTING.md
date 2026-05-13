# Contributing to TrajAudit

Thanks for considering a contribution. TrajAudit is in Phase 0 (scaffold)
and the codebase is still in motion — most of the surface raises
`NotImplementedError` today. Filing issues and exploit-signature proposals is
the most useful thing you can do right now.

## Filing an issue

Use the issue templates (coming alongside Phase 1) once they exist. Until
then, open a regular issue describing:

- What you observed (or, for a feature request: what you want).
- Which benchmark / agent / trajectory triggered it, if applicable.
- Minimal reproduction steps.

## Proposing a new exploit signature

The Layer 2 exploit catalog lives in
[docs/exploit-taxonomy.md](docs/exploit-taxonomy.md) and the matchers in
`src/trajaudit/layer2_syntactic/exploit_signatures.py`. To propose a new
signature, open an issue with:

1. A short name and a description of the exploit shape.
2. A real (or convincingly synthetic) example trajectory that triggers it.
3. A clean trajectory that should *not* trigger it — false-positive control
   is as important as recall.
4. A sketch of the detection approach (AST shape, FS pattern, prompt cue).

We will incorporate it into the taxonomy with a stable `EX-NNN-` id.

## Code contributions

Code PRs are welcome but please open an issue first so we can align on the
approach. The repo enforces `ruff`, `mypy`, and `pytest` in CI; please run
them locally before opening a PR:

```bash
uv sync --all-extras --dev
uv run ruff check .
uv run mypy src/trajaudit
uv run pytest
```

## Code of Conduct

We default to the [Contributor Covenant](https://www.contributor-covenant.org/);
a project-specific code of conduct will land alongside Phase 1.
