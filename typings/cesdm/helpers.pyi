from pathlib import Path
from typing import Sequence, Union
from cesdm.domain.model import CesdmModel

def build_model_from_yaml(schema_path: Union[str, Path, Sequence[Union[str, Path]]]) -> CesdmModel: ...
