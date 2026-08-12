"""ear.model.core

Assembles the public :class:`Model` class from the responsibility-scoped
mixins in this package. Each mixin covers one concern (schema loading,
entity CRUD, validation, persistence per format, ...); this module is
the only place they are combined, so the public API and MRO are defined
in exactly one location.

Auto-extracted from the legacy monolithic ``ear_toolbox.py`` as part of
the package-hierarchy refactor. Behaviour is unchanged.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional, Union, Tuple
from difflib import get_close_matches
import os, pathlib
import yaml
from pathlib import Path
import re


from ear.entity_class import EntityClass
from ear.entity import Entity

from ear.model.schema_loading import SchemaLoadingMixin
from ear.model.entity_ops import EntityOpsMixin
from ear.model.accessors import AccessorsMixin
from ear.model.validation import ValidationMixin
from ear.model.persistence_yaml_json import PersistenceYamlJsonMixin
from ear.model.persistence_csv import PersistenceCsvMixin
from ear.model.pydantic_export import PydanticExportMixin
from ear.model.frictionless import FrictionlessMixin
from ear.model.analysis_validation import AnalysisValidationMixin


@dataclass
class Model(
    SchemaLoadingMixin,
    EntityOpsMixin,
    AccessorsMixin,
    ValidationMixin,
    PersistenceYamlJsonMixin,
    PersistenceCsvMixin,
    PydanticExportMixin,
    FrictionlessMixin,
    AnalysisValidationMixin,
):
    """
    In-memory representation of a CESDM model.

    A ``Model`` holds:

    - class definitions loaded from YAML (:class:`EntityClass`),
    - entity instances (:class:`Entity`),
    - the inheritance graph between classes.

    It provides methods to:

    - load and resolve schema definitions,
    - create and modify entities,
    - validate attribute values and relations,
    - import/export data to various formats.

    The methods themselves live in the mixins listed above; this class
    only owns ``__init__`` and the combined MRO.
    """

    def __init__(self):
        self.classes: Dict[str, EntityClass] = {}
        self.entities: Dict[str, Dict[str, Entity]] = {}
        self.inheritance: Dict[str, Union[str, List[str], None]] = {}
        from ear.schema_manifest import SchemaManifest
        self.schema_manifest: SchemaManifest = SchemaManifest()
