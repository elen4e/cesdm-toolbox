"""ear.constraint

Constraint dataclass used by AttributeDef.

Auto-extracted from the legacy monolithic ``ear_toolbox.py``.
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



@dataclass
class Constraint:
    """
    Validation constraints for a single attribute.

    Parameters
    ----------
    enum :
        Optional list of allowed values for the attribute.
    minimum :
        Minimum allowed value for numeric attributes.
    maximum :
        Maximum allowed value for numeric attributes.
    pattern :
        Optional regular expression pattern the value must match.
    ref :
        Optional relation string for more complex/indirect constraints
        (currently used only in limited contexts).
    """
    enum: Optional[List[Any]] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    pattern: Optional[str] = None
    ref: Optional[str] = None

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Constraint":
        if not d:
            return Constraint()
        return Constraint(
            enum=d.get("enum"),
            minimum=d.get("minimum"),
            maximum=d.get("maximum"),
            pattern=d.get("pattern"),
            ref=d.get("ref"),
        )


