"""ear.schema_manifest

Optional, domain-agnostic schema-versioning support for the EAR engine.

Any schema directory loaded via :func:`ear.model.schema_loading
.SchemaLoadingMixin.load_classes_from_yaml` may contain a
``SCHEMA_MANIFEST.yaml`` file at its root declaring:

* a semantic version for the schema tree as a whole,
* a *stability tier* per schema "family" (a top-level subdirectory, or
  any other grouping key the domain layer chooses to use),
* zero or more other schema trees this one ``extends`` (depends on and
  builds on top of) — see ``load_classes_from_yaml``, which resolves
  and auto-loads these before the declaring tree's own classes,
* free-form provenance (description, changelog location).

This lives in the generic ``ear`` package — not ``cesdm`` — because
"a schema is a versioned, governed artifact" is a property of the EAR
approach in general, not something energy-specific. CESDM (or any other
domain built on ``ear``) supplies the actual manifest content; this
module only knows how to read and represent it.

If no manifest file is present, :meth:`SchemaManifest.load` returns a
manifest with ``version="0.0.0-unversioned"`` and no stability data
rather than failing — schema versioning is opt-in, so existing/foreign
schema trees (and ad-hoc test fixtures) keep working unmodified.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass, field
from typing import Dict, Optional, Union

import yaml

UNVERSIONED = "0.0.0-unversioned"

#: Recognised stability tiers, most to least safe to build a long-lived
#: integration against.
STABILITY_TIERS = ("stable", "experimental", "deprecated")

MANIFEST_FILENAME = "SCHEMA_MANIFEST.yaml"


@dataclass
class SchemaManifest:
    """Version and governance metadata for a loaded schema tree."""

    version: str = UNVERSIONED
    description: str = ""
    changelog: Optional[str] = None
    #: family name (e.g. a top-level schema subdirectory) -> stability tier
    stability: Dict[str, str] = field(default_factory=dict)
    #: absolute paths of other schema trees this one depends on and
    #: extends (e.g. a domain extension built on the core schema tree).
    #: Populated with *resolved* absolute paths by load(); the raw
    #: manifest field is a list of paths relative to the manifest file.
    extends: list = field(default_factory=list)
    #: absolute path the manifest was loaded from, or None if unversioned
    source_path: Optional[str] = None

    @property
    def is_versioned(self) -> bool:
        return self.version != UNVERSIONED

    @property
    def major(self) -> Optional[int]:
        """Leading numeral before the first dot, or None if unversioned/non-semver."""
        if not self.is_versioned:
            return None
        head = self.version.split(".", 1)[0]
        return int(head) if head.isdigit() else None

    def stability_for(self, family: str) -> str:
        """
        Stability tier for a schema family (e.g. a top-level schema
        subdirectory name like ``"controllers"`` or ``"assets"``).

        Returns ``"unknown"`` if the manifest does not declare a tier
        for that family — this is informational, never a hard error.
        """
        return self.stability.get(family, "unknown")

    def is_compatible_with(self, other_version: str) -> bool:
        """
        Semver-style compatibility check: same major version is
        considered compatible. Used to warn (not fail) when importing
        a model exported against a different schema major version.
        """
        if not self.is_versioned or other_version in (None, "", UNVERSIONED):
            # Can't meaningfully compare — don't block the import.
            return True
        other_head = str(other_version).split(".", 1)[0]
        if not other_head.isdigit():
            return True
        return self.major == int(other_head)

    @classmethod
    def load(cls, schema_dir: Union[str, "pathlib.Path"]) -> "SchemaManifest":
        """
        Read ``SCHEMA_MANIFEST.yaml`` from *schema_dir* if present.

        Never raises: a missing or malformed manifest yields an
        unversioned :class:`SchemaManifest` rather than blocking model
        construction, since schema versioning is opt-in.
        """
        p = pathlib.Path(schema_dir) / MANIFEST_FILENAME
        if not p.is_file():
            return cls()
        try:
            raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            return cls()
        if not isinstance(raw, dict):
            return cls()
        stability_raw = raw.get("stability") or {}
        if not isinstance(stability_raw, dict):
            stability_raw = {}
        for tier in stability_raw.values():
            if tier not in STABILITY_TIERS:
                # Unknown tier value: keep it (forward-compatible with
                # future tiers) rather than dropping information.
                pass

        extends_raw = raw.get("extends") or []
        if isinstance(extends_raw, str):
            extends_raw = [extends_raw]
        if not isinstance(extends_raw, list):
            extends_raw = []
        resolved_extends = []
        for rel in extends_raw:
            ext_path = (p.parent / str(rel)).resolve()
            if not ext_path.is_dir():
                raise FileNotFoundError(
                    f"{p}: 'extends' references {rel!r}, which resolves to "
                    f"{ext_path}, but that directory does not exist."
                )
            resolved_extends.append(ext_path)

        return cls(
            version=str(raw.get("version") or UNVERSIONED),
            description=str(raw.get("description") or ""),
            changelog=raw.get("changelog"),
            stability={str(k): str(v) for k, v in stability_raw.items()},
            extends=resolved_extends,
            source_path=str(p),
        )
