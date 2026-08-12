"""cesdm.domain.model.analysis_validation — CESDM addon: resolving a
check beyond the entity itself

The generic, schema-agnostic core of analysis-profile validation lives
in `ear.model.analysis_validation.AnalysisValidationMixin` -- entities,
attributes, relations, and constraints are core EAR concepts, so that
part works for any EAR-based schema, not just CESDM, and already
covers the overwhelming majority of real checks: almost every
asset attribute/relation is declared directly on its class (see
`docs/schema_layout.md`), so `attribute` is normally found directly
on the entity without this mixin ever being consulted at all.

This mixin adds the CESDM-specific fallbacks the generic core
deliberately doesn't and shouldn't know about: resolving `attribute`
against something other than the checked entity's own direct data,
when it isn't found (or found but empty) there. Two kinds exist:

- **The technology-template cascade** (`hasTechnology` ->
  GeneratorType/StorageType/...), via `get_effective_attribute_value()`
  -- the same fallback a live read of `entity.dispatch.attribute`
  already goes through, so an analysis profile requiring e.g.
  `charging_efficiency` correctly recognises a StorageUnit whose value
  comes entirely from its linked StorageType template, not set
  directly on the instance.
- **`Result` entities** (`GenerationUnit.DispatchResult`, ...), linked
  via `reportsOn` -- discovered through `_discover_view_map()`.
  None of these declare a `view_family`, so this path is a
  no-op (kept for forward compatibility, in case a future schema
  addition ever declares one).
- **`Controller.AVR`/`.GOV`/`.PSS` entities**, linked via
  `hasAutomaticVoltageRegulator`/`hasTurbineGovernor`/
  `hasPowerSystemStabilizer` rather than `reportsOn` -- these
  *do* declare a `view_family` (`avr`/`governor`/`pss`), so they're
  handled through a small, explicit relation map instead of the
  `reportsOn`-keyed discovery mechanism, which structurally
  cannot see them (verified directly: `_discover_view_map()` never
  includes a `Controller.*` class for `GenerationUnit`, since that
  discovery is keyed on `reportsOn`).

It does this by overriding `_resolve_check_beyond_entity()`, the
generic mixin's one designed extension point -- called only when a
check's `attribute` isn't found among the entity's own direct
attributes/relations. This class must appear before `ear.model.Model`
in `CesdmModel`'s MRO (see `cesdm/domain/model/core.py`) for the
override to actually take effect; Python's normal method resolution
already guarantees this from the mixin declaration order.

See `docs/guide/10_analysis_validation.md` for the full design and
`analysis_profiles/optimal_dispatch.yaml` for a worked example.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


class CesdmAnalysisValidationMixin:
    """CESDM addon -- see module docstring."""

    #: family -> the relation on the *asset* that points at the
    #: standalone linked entity (a controller, or the dynamic machine
    #: model). These are linked this way, not via `reportsOn`, so
    #: `_discover_view_map()` (which is keyed on `reportsOn`) can
    #: never see them -- this explicit map is the only way to reach
    #: them from an analysis-profile check.
    _LINKED_ENTITY_FAMILY_RELATIONS: Dict[str, str] = {
        "avr": "hasAutomaticVoltageRegulator",
        "governor": "hasTurbineGovernor",
        "pss": "hasPowerSystemStabilizer",
        "dynamics": "usesDynamicModelType",
    }

    def _find_existing_view_for_family(self, entity_id: str, family: str) -> Optional[str]:
        """Read-only counterpart to EntityProxy._view() (cesdm/proxy.py):
        find an existing linked entity for the given view_family for
        entity_id, without creating one if missing. Unlike the proxy
        layer's `.dispatch` etc, which auto-creates a view on first
        access, validation must never have a side effect on the model
        it's checking -- a missing view should be reported as missing,
        not silently created to paper over the gap.

        Tries `reportsOn`-linked entities (Result) first,
        then falls back to the explicit linked-entity relation map for
        `avr`/`governor`/`pss`.
        """
        for vcls, vid in (self.views_for_asset(entity_id) or {}).items():
            cdef = self.classes.get(vcls)
            if (cdef is not None and getattr(cdef, "view_family", None) == family
                    and not getattr(cdef, "abstract", False)):
                return vid

        relation = self._LINKED_ENTITY_FAMILY_RELATIONS.get(family)
        if relation:
            targets = self.get_relation_targets(entity_id, relation) or []
            if targets:
                return str(targets[0])
        return None

    def _find_view_family_for_attribute(self, entity_class: str, attribute: str) -> Optional[str]:
        """Given an entity class and an attribute/relation id that isn't
        declared directly on the entity itself, find which single
        view_family (if any) declares it -- so a profile only has to
        say "GenerationUnit needs nominal_power_capacity", not which
        of its several possible linked entities that actually lives
        on. Returns None if the attribute isn't found anywhere, *or*
        if it's found on more than one distinct family (ambiguous; an
        explicit `view_family` in the check is the escape hatch for
        that rare case).

        Searches both `reportsOn`-linked classes (Result
        -- via `_discover_view_map()`) and, separately, whichever
        `Controller.AVR`/`.GOV`/`.PSS` concrete subclasses are actually
        reachable from `entity_class` through the controller-relation
        map above (only meaningful for `attribute`s that are genuinely
        controller-specific, e.g. `AVR_SEXS_Ka` -- ordinary
        dispatch/topology/power_flow/spatial/planning/technical/
        dynamics attributes are already found directly on the entity
        before this method is ever called at all).
        """
        families_found: set = set()

        candidates = (self._discover_view_map() or {}).get(entity_class, [])
        for vcls in candidates:
            cdef = self.classes.get(vcls)
            if cdef is None or getattr(cdef, "abstract", False):
                continue
            family = getattr(cdef, "view_family", None)
            if not family:
                continue
            if attribute in (self.class_attributes(vcls) or []) or \
                    attribute in (self.class_relations(vcls) or []):
                families_found.add(family)

        own_relations = self.class_relations(entity_class) or {}
        for family, relation in self._LINKED_ENTITY_FAMILY_RELATIONS.items():
            if relation not in own_relations:
                continue
            for vcls, cdef in self.classes.items():
                if getattr(cdef, "abstract", False) or getattr(cdef, "view_family", None) != family:
                    continue
                if attribute in (self.class_attributes(vcls) or []) or \
                        attribute in (self.class_relations(vcls) or []):
                    families_found.add(family)

        return families_found.pop() if len(families_found) == 1 else None

    def _resolve_check_beyond_entity(self, real_class: str, entity_id: str, attribute: str,
                                     check: Dict[str, Any]) -> Tuple[bool, Any, Optional[str], Optional[str]]:
        """Overrides the generic hook (ear.model.analysis_validation):
        before giving up, try resolving `attribute` two ways --

        1. Through the technology-template cascade (`hasTechnology` ->
           GeneratorType/StorageType/...), via the same
           `get_effective_attribute_value()` a live read of
           `entity.dispatch.attribute` already goes through. Confirmed
           directly: without this, an analysis profile requiring e.g.
           `charging_efficiency` flagged a StorageUnit as incomplete
           even when its linked StorageType template supplied a real
           value for it -- correct for `attribute` (a literal-value
           lookup, used by schema validation, deliberately never
           follows the cascade) but wrong for analysis-profile
           checks, whose whole point is "does this model have what
           the analysis needs", the same question `.dispatch.x` answers
           for a human reading the model by hand.
        2. Against one of the entity's linked Result/Controller
           entities -- explicit `view_family` in the check, or
           auto-detected.
        """
        tech_value = self.get_effective_attribute_value(entity_id, attribute)
        if tech_value not in (None, "", []):
            direct_value = self.get_attribute_value(entity_id, attribute)
            if direct_value in (None, "", []):
                # Only reached via the technology-template cascade (or
                # the attribute's own schema default) -- the direct
                # value itself was already tried and found empty by the
                # caller before this hook was ever consulted.
                return True, tech_value, f"{attribute} (from linked technology template)", None

        view_family = check.get("view_family")
        if view_family is None:
            view_family = self._find_view_family_for_attribute(real_class, attribute)
            if view_family is None:
                return False, None, None, (
                    f"'{attribute}' is not a known attribute or relation of {real_class!r}, "
                    f"or of any linked Result/Controller entity (or it's ambiguous across "
                    f"more than one -- add an explicit 'view_family' to this check to "
                    f"disambiguate)"
                )

        location = f"{attribute} (view: {view_family})"
        view_id = self._find_existing_view_for_family(entity_id, view_family)
        if view_id is None:
            required = bool(check.get("required", False))
            if required:
                return False, None, None, f"has no {view_family!r} view to check '{attribute}' on"
            # Not required and the view doesn't exist -- report as
            # "found, but empty", so the generic required-check (which
            # only fires when required=True anyway) correctly does
            # nothing here, exactly as if the attribute were merely unset.
            return True, None, location, None

        value = self.get_attribute_value(view_id, attribute)
        return True, value, location, None
