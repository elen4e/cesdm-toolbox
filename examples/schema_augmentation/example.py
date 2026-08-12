#!/usr/bin/env python3
"""Executable CESDM schema-augmentation example.

Run from the repository root:

    python examples/schema_augmentation/example.py

The extension defines its own Agent class, attribute registry, and relation
registry.  It augments the existing EnergyAssetInstance class without editing
schemas/cesdm, so GenerationUnit inherits the new ``agent`` group.
"""
from __future__ import annotations

from pathlib import Path
import sys


def repository_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in [*here.parents, Path.cwd(), *Path.cwd().parents]:
        if (candidate / "schemas" / "cesdm").exists():
            return candidate
    raise FileNotFoundError("Could not locate the CESDM repository root.")


ROOT = repository_root()
sys.path.insert(0, str(ROOT))

from cesdm_toolbox import build_model_from_yaml


BASE_SCHEMA = ROOT / "schemas" / "cesdm"
EXTENSION_SCHEMA = ROOT / "examples" / "schema_augmentation" / "schema_extension"

model = build_model_from_yaml([BASE_SCHEMA, EXTENSION_SCHEMA])

agent = model.add_entity("Agent", "agent.utility.ch")
agent.name = "Swiss Utility Agent"

generator = model.add_entity("GenerationUnit", "gen.ch.wind")
generator.name = "CH Wind"
generator.agent.bidding_strategy = "strategic"
generator.agent.ownedByAgent = agent

print("Schema roots:")
print(f"  base:      {BASE_SCHEMA}")
print(f"  extension: {EXTENSION_SCHEMA}")
print()
print("Augmented GenerationUnit fields:")
print("  group:             agent")
print(f"  bidding_strategy:  {generator.agent.bidding_strategy}")
print(f"  ownedByAgent:      {generator.agent.ownedByAgent}")
print()

assert generator.agent.bidding_strategy == "strategic"
assert str(generator.agent.ownedByAgent) == "agent.utility.ch"
assert "bidding_strategy" in model.classes["GenerationUnit"].attributes
assert "ownedByAgent" in model.classes["GenerationUnit"].relations
assert model.classes["GenerationUnit"].attributes["bidding_strategy"].belongsToGroup == ["agent"]
assert model.classes["GenerationUnit"].relations["ownedByAgent"].belongsToGroup == ["agent"]

errors = model.validate()
if errors:
    print("Validation issues unrelated to the augmentation example:")
    for error in errors[:10]:
        print(" -", error)
else:
    print("Model validation succeeded.")

print("\nSchema augmentation test succeeded.")
