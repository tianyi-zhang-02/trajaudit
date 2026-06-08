"""Phase 0 smoke test.

The package imports and exposes a version. Layer-specific tests land
under ``tests/core/``, ``tests/layer1/``, ``tests/layer2/``, and
``tests/layer3/`` as those layers acquire implementations.
"""

from __future__ import annotations

import monitorstress


def test_version_exposed() -> None:
    assert isinstance(monitorstress.__version__, str)
    assert monitorstress.__version__
