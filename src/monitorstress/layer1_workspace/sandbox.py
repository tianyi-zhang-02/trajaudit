"""Docker sandbox for Layer 1 trajectory replay.

A :class:`DockerSandbox` is a stateful isolated environment in which
an agent trajectory can be re-executed (or its workspace artifacts
re-mounted) to observe filesystem and process behavior without
trusting the agent's host environment.

We reuse SWE-bench's per-repo evaluation images for SWE-bench tasks
rather than building our own base images — this minimizes
environment-drift false positives when comparing the post-replay
workspace to the original.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class DockerSandbox:
    """Docker-backed sandbox. Default Layer 1 backend."""

    def __init__(
        self,
        *,
        network_disabled: bool = True,
        memory_limit_mb: int = 4096,
    ) -> None:
        self.network_disabled = network_disabled
        self.memory_limit_mb = memory_limit_mb

    def start(self, image: str, *, env: dict[str, str] | None = None) -> None:
        """Start the sandbox from a base image."""
        raise NotImplementedError("Phase 3: implement docker-py-based sandbox lifecycle.")

    def upload(self, local_path: Path, remote_path: Path) -> None:
        """Copy a file or directory into the sandbox."""
        raise NotImplementedError("Phase 3: implement tar-stream upload.")

    def exec(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Execute a command; return ``{exit_code, stdout, stderr}``."""
        raise NotImplementedError("Phase 3: implement docker exec wrapper.")

    def snapshot_fs(self, path: Path) -> dict[Path, bytes]:
        """Snapshot the contents of ``path`` (recursively) for diffing."""
        raise NotImplementedError("Phase 3: implement recursive snapshot.")

    def stop(self) -> None:
        """Tear down the sandbox and release its resources."""
        raise NotImplementedError("Phase 3: implement container teardown.")
