"""Version-upgrade tooling.

Lets an already-generated project pull in improvements from a newer template
version via a 3-way merge (see docs/guides/version-upgrade.md). This
subpackage keeps all upgrade logic out of generated projects — they carry only
the manifest (``.fastapi-fullstack.json``) plus a thin Makefile shim.
"""

from .manifest import (
    MANIFEST_FILENAME,
    build_manifest,
    compute_context_hash,
    read_manifest,
    redact_secrets,
    write_manifest,
)

__all__ = [
    "MANIFEST_FILENAME",
    "build_manifest",
    "compute_context_hash",
    "read_manifest",
    "redact_secrets",
    "write_manifest",
]
