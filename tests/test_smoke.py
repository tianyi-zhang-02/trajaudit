"""Phase 0 smoke test.

The package imports and exposes a version. Layer-specific tests land
under ``tests/core/``, ``tests/layer1/``, ``tests/layer2/``, and
``tests/layer3/`` as those layers acquire implementations.
"""

from __future__ import annotations

import trajaudit


def test_version_exposed() -> None:
    assert isinstance(trajaudit.__version__, str)
    assert trajaudit.__version__
