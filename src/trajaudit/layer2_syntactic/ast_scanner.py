"""AST-based scanner that matches code edits against the exploit catalog.

The :class:`ASTScanner` is a stateless utility: given a list of
:class:`~trajaudit.layer2_syntactic.code_extractor.CodeEdit` instances
and the catalog from
:func:`~trajaudit.layer2_syntactic.exploit_signatures.get_all_signatures`,
it parses each edit's ``after_source`` and returns one
:class:`~trajaudit.core.verdict.SyntacticFinding` per matched
signature.
"""

from __future__ import annotations

from trajaudit.core.verdict import SyntacticFinding
from trajaudit.layer2_syntactic.code_extractor import CodeEdit
from trajaudit.layer2_syntactic.exploit_signatures import (
    ExploitSignature,
    get_all_signatures,
)


class ASTScanner:
    """Run the exploit catalog against a batch of code edits."""

    def __init__(self, signatures: list[ExploitSignature] | None = None) -> None:
        self.signatures: list[ExploitSignature] = signatures or get_all_signatures()

    def scan(self, edits: list[CodeEdit]) -> list[SyntacticFinding]:
        """Return every finding produced by the catalog on these edits."""
        raise NotImplementedError("Phase 2: implement AST scan loop.")
