"""cesdm.domain.model.core

Assembles the public :class:`CesdmModel` class from the
responsibility-scoped mixins in this package (one file per concern:
discovery, per-format persistence, builders, accessors, statistics).
This module is the only place they are combined, so the public API and
MRO are defined in exactly one location.

Auto-extracted from the legacy monolithic ``cesdm_toolbox.py`` as part
of the package-hierarchy refactor. Behaviour is unchanged.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional, Union
import os
import pathlib
import re
import yaml


from ear.model import Model

from cesdm.domain.model.discovery import DiscoveryMixin
from cesdm.domain.model.hierarchical_yaml import HierarchicalYamlMixin
from cesdm.domain.model.csv import CsvMixin
from cesdm.domain.model.hdf5_parquet import Hdf5ParquetMixin
from cesdm.domain.model.excel import ExcelMixin
from cesdm.domain.model.frictionless import FrictionlessMixin
from cesdm.domain.model.library import LibraryMixin
from cesdm.domain.model.json_schema import JsonSchemaMixin
from cesdm.domain.model.rdf_export import RdfExportMixin
from cesdm.domain.model.accessors import AccessorsMixin
from cesdm.domain.model.builders import BuildersMixin
from cesdm.domain.model.statistics import StatisticsMixin
from cesdm.domain.model.analysis_validation import CesdmAnalysisValidationMixin


class CesdmModel(
    DiscoveryMixin,
    HierarchicalYamlMixin,
    CsvMixin,
    Hdf5ParquetMixin,
    ExcelMixin,
    FrictionlessMixin,
    LibraryMixin,
    JsonSchemaMixin,
    RdfExportMixin,
    AccessorsMixin,
    BuildersMixin,
    StatisticsMixin,
    CesdmAnalysisValidationMixin,
    Model,
):
    """
    Energy-system domain model.

    Inherits all generic EAR capabilities from :class:`ear.model.Model`
    and adds hierarchical import/export keyed to the CESDM schema, plus
    the high-level builder/accessor/statistics API.

    The methods themselves live in the mixins listed above; this class
    only owns the CESDM-specific class-level constants and the combined
    MRO. ``FrictionlessMixin`` here (CESDM-aware) intentionally comes
    before ``Model`` in the MRO so it overrides the generic
    ``ear.model.frictionless.FrictionlessMixin`` implementation.
    """

    # Authoritative mapping: which view classes are valid for each asset class.
    # Used to restrict column generation (export) and field resolution (import)
    # so that fields shared across view classes (e.g. nominal_power_capacity in
    # both GenerationUnit.DispatchResult and StorageUnit.DispatchResult) are
    # always assigned to the correct view for a given asset type.

    # Short abbreviations for Excel sheet names (Excel limit: 31 chars).
    # Used by export_excel and import_excel to encode "<AssetAbbr>.<ViewAbbr>".
    # Both dicts must be kept in sync; import uses the reverse mapping.

    _REPORTS_ON_REL: ClassVar[str] = "reportsOn"

    # Role is derived purely from the class structure — no hardcoded seed sets,
    # no role: YAML field needed.
    #
    # Rules (applied in order):
    #   "view"   — class declares reportsOn (directly or via inheritance)
    #   "asset"  — class IS or inherits from EnergyAssetInstance
    #   "domain" — everything else (NetworkNode, Carrier, abstract bases, ...)
    #
    # EnergyAssetInstance is the single structural root of the asset branch.
    # View roots are identified by the presence of the reportsOn relation.
