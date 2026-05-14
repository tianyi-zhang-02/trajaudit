# Security Policy

## Reporting a vulnerability

If you discover a security issue in TrajAudit — for example, a path through
the Docker sandbox that could be abused, a credential-leak vector in the
Layer 3 providers, or a way to coerce the LLM judge into emitting unsafe
output — please **do not open a public GitHub issue**.

Instead, [report it privately via GitHub's Private Vulnerability Reporting](https://github.com/tianyi-zhang-02/trajaudit/security/advisories/new). This routes directly to repo maintainers and creates a private advisory thread.

Please include:

- A description of the issue and its potential impact.
- Reproduction steps or a proof of concept.
- Your suggested fix or mitigation, if any.

We aim to acknowledge reports within 72 hours and to ship a fix or an
advisory within 30 days for high-severity issues.

## Scope

In scope:

- Code in `src/trajaudit/`.
- The Layer 1 sandbox configuration (Docker image, container settings).
- The Layer 3 provider implementations and prompt templates.

Out of scope:

- Vulnerabilities in upstream dependencies (please report those upstream;
  link the upstream advisory here once filed).
- Issues in third-party benchmarks TrajAudit audits.
- Theoretical attacks requiring untrusted input we explicitly do not accept
  (e.g. attacker-controlled `pyproject.toml` in the project root).

## Disclosure

We follow coordinated disclosure: we will work with you on a timeline before
public disclosure of a confirmed vulnerability, and we will credit you in
the security advisory unless you prefer otherwise.
