"""cesdm.helpers

Free-function helpers for the CESDM domain layer.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional, Sequence, Union
import os
import pathlib
import re
import yaml

from cesdm.domain.model import CesdmModel


def build_model_from_yaml(schema_path: Union[str, pathlib.Path, Sequence[Union[str, pathlib.Path]]]) -> CesdmModel:
    """Build a CesdmModel from one schema tree, or an ordered list of
    them -- a later path's classes can extend/reference an earlier
    one's, e.g. build_model_from_yaml(["schemas/cesdm", "schemas/agentbased"])."""
    m = CesdmModel()
    m.load_classes_from_yaml(schema_path)
    return m
