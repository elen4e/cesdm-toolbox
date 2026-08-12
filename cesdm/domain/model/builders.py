"""cesdm.domain.model.builders — Entity construction and proxy wrapping

**The one rule for what belongs in this file**: generic, class-agnostic
construction/query infrastructure -- `add_entity()`/`get_entity()`/
`get_entity_as()` (proxy wrapping), `ensure_entity()`/`ensure_carrier()`/
`ensure_resource()`/`ensure_technology()` (create-if-missing by class
name), topology wiring
(`connect_single_port()`/`connect_two_port()`), and profile-attaching
helpers. Not a per-asset-type domain convenience wrapper -- those were
removed entirely (see CHANGELOG.md): building any model uses core EAR
calls (`add_entity()`/`add_attribute()`/`add_relation()`) plus this
proxy layer for reading/writing afterward.

Auto-extracted from the legacy monolithic module as part of the
package-hierarchy refactor (see docs/architecture/package_layout.md).
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional, TypeVar, Union
import os
import pathlib
import re
import yaml

from cesdm.proxy import EntityProxy, _entity_proxy

_T = TypeVar("_T", bound=EntityProxy)


class BuildersMixin:
    """Mixin — see module docstring for the responsibility this covers."""

    # Legacy relation ids accepted on write/import (schema id → canonical).
    _RELATION_ID_ALIASES: ClassVar[Dict[str, str]] = {
        "representsAsset": "reportsOn",
        "drawsFromReservoir": "drawsFromHydraulicStorage",
        "dischargesToReservoir": "dischargesToHydraulicStorage",
        "hasRunOfRiverInflowProfile": "hasNaturalInflowProfile",
        "locatedIn": "belongsToGeographicalRegion",
    }

    def _canonical_relation_id(self, relation_id: str) -> str:
        """Map legacy relation ids to the current schema id."""
        return self._RELATION_ID_ALIASES.get(relation_id, relation_id)

    # Legacy attribute ids → canonical (HVDC capacity / technology dedupe;
    # hydro machine class rename).
    _ATTRIBUTE_ID_ALIASES: ClassVar[Dict[str, str]] = {
        "hvdc_technology_type": "converter_technology",
        "p_max_hvdc": "max_flow",
        "machine_role": "hydro_machine_kind",
    }

    # Legacy concrete class names → current concrete classes. Applied only
    # when creating/looking up entities — not when resolving schema parents
    # (ConversionUnit remains a valid abstract parent).
    _ENTITY_CLASS_ALIASES: ClassVar[Dict[str, str]] = {
        "ConversionUnit": "GenericConversionUnit",
        "Interconnector": "GenericInterconnector",
        "ReservoirStorageUnit": "HydraulicStorageUnit",
    }

    def _resolve_entity_class_alias(self, class_name: str) -> str:
        return self._ENTITY_CLASS_ALIASES.get(class_name, class_name)

    def _attribute_id_for_schema_lookup(self, attribute_id: str) -> str:
        """Canonical attribute id for import membership checks."""
        if attribute_id == "is_reversible":
            return "hydro_machine_kind"
        return self._ATTRIBUTE_ID_ALIASES.get(attribute_id, attribute_id)

    def _is_legacy_attribute_write(self, attribute_id: str) -> bool:
        """Attributes removed from entity schemas but still accepted on import."""
        return attribute_id in ("is_reversible", "is_reference_port")

    @staticmethod
    def _attr_raw_value(value: Any) -> Any:
        if isinstance(value, dict) and "value" in value:
            return value.get("value")
        return value

    @staticmethod
    def _attr_is_truthy(raw: Any) -> bool:
        return raw in (True, 1, "1", "true", "True", "yes", "YES")

    def _apply_legacy_reference_port(self, port_id: str) -> None:
        """Map legacy ConversionPort.is_reference_port=true → unit.referencePort."""
        units = []
        try:
            units = list(self.get_relation_targets(port_id, "belongsToUnit") or [])
        except Exception:
            units = []
        if units:
            self.add_relation(str(units[0]), "referencePort", port_id)
            pending = getattr(self, "_pending_reference_ports", None)
            if pending is not None:
                pending.discard(port_id)
            return
        pending = getattr(self, "_pending_reference_ports", None)
        if pending is None:
            self._pending_reference_ports = set()
            pending = self._pending_reference_ports
        pending.add(port_id)

    def _prepare_attribute_write(
        self, attribute_id: str, value: Any
    ) -> tuple[str, Any] | None:
        """Normalize legacy attribute writes. ``None`` means skip (no-op)."""
        if attribute_id == "is_reversible":
            raw = self._attr_raw_value(value)
            if not self._attr_is_truthy(raw):
                return None
            if isinstance(value, dict) and "value" in value:
                out = dict(value)
                out["value"] = "reversible"
                return "hydro_machine_kind", out
            return "hydro_machine_kind", "reversible"
        attribute_id = self._ATTRIBUTE_ID_ALIASES.get(attribute_id, attribute_id)
        return attribute_id, value

    def add_relation(
        self,
        entity_id: str,
        relation_id: str,
        target_entity_id: str,
        **kwargs,
    ):
        """Like EAR ``add_relation``, but remaps deprecated relation ids
        (e.g. ``representsAsset`` → ``reportsOn``) so older models/packages
        still import cleanly after the schema rename.
        """
        relation_id = self._canonical_relation_id(relation_id)
        result = super().add_relation(entity_id, relation_id, target_entity_id, **kwargs)
        if relation_id == "belongsToUnit":
            pending = getattr(self, "_pending_reference_ports", None)
            if pending and entity_id in pending:
                self.add_relation(str(target_entity_id), "referencePort", entity_id)
                pending.discard(entity_id)
        return result

    def get_relation_targets(self, entity_id: str, relation_id: str):
        """Like EAR ``get_relation_targets``, but accepts legacy relation ids."""
        return super().get_relation_targets(
            entity_id, self._canonical_relation_id(relation_id)
        )

    def add_relation_if_allowed(
        self,
        entity_id: str,
        relation_id: str,
        target_id: str,
        *,
        strict: bool = False,
    ):
        """Like EAR ``add_relation_if_allowed``, but remaps legacy relation ids
        before the class-membership check (so ``locatedIn`` still works)."""
        return super().add_relation_if_allowed(
            entity_id,
            self._canonical_relation_id(relation_id),
            target_id,
            strict=strict,
        )

    def add_attribute(self, entity_id: str, attribute_id: str, *args, **kwargs):
        """Remap deprecated attribute ids (e.g. ``machine_role`` → ``hydro_machine_kind``)."""
        value = args[0] if args else kwargs.get("value")
        if attribute_id == "is_reference_port":
            if self._attr_is_truthy(self._attr_raw_value(value)):
                self._apply_legacy_reference_port(str(entity_id))
            return None
        prepared = self._prepare_attribute_write(attribute_id, value)
        if prepared is None:
            return None
        attribute_id, value = prepared
        if args:
            args = (value,) + args[1:]
        else:
            kwargs = {**kwargs, "value": value}
        return super().add_attribute(entity_id, attribute_id, *args, **kwargs)

    def add_entity(self, entity_class: str, entity_id: str) -> EntityProxy:
        """Create a new entity and return it wrapped in its
        schema-specific typed proxy directly -- e.g.
        `gen = model.add_entity("GenerationUnit", "gen1")` gives back a
        `GenerationUnitProxy` you can immediately do
        `gen.dispatch.nominal_power_capacity = 400` on, both at runtime
        and (via `@overload`/`Literal` in the generated stub) in your
        editor's autocomplete/type-checking too -- no `get_entity_as()` cast
        needed for the common "just created it" case.

        Overrides `ear.model.Model.add_entity()` (still returns the
        bare `ear.entity.Entity` dataclass there, unchanged -- a plain
        EAR domain has no proxy registry to wrap with at all). Asked
        directly why this couldn't "just happen" on `add_entity()`
        itself instead of a separate method: it can, once the return
        value is overridden at the CESDM layer specifically rather
        than the shared EAR primitive underneath it, which stays
        exactly as it was. See CHANGELOG.md.
        """
        entity_class = self._resolve_entity_class_alias(entity_class)
        super().add_entity(entity_class, entity_id)
        return _entity_proxy(self, entity_id)

    def get_entity(self, entity_id: str) -> EntityProxy:
        """Wrap an existing entity id in its schema-specific generated proxy
        (e.g. `DemandUnitProxy` for a `DemandUnit`), so code that created it
        via the low-level `add_entity()`/`ensure_entity()` calls can still
        use `.dispatch`, `.connect()`, `.add_attribute(...)`, etc. Falls
        back to plain `EntityProxy` if the entity's class has no generated
        proxy (or doesn't exist at all yet). `EntityProxy` is a `str`
        subclass, so `model.get_entity(x) == x` for any entity id `x`
        regardless of which specific proxy subclass wraps it -- wrapping is
        purely additive.

        Statically typed as returning plain `EntityProxy` even though the
        *runtime* value is more specific -- a type checker can't know
        which subclass a string id resolves to. If you need `.dispatch`
        etc. to type-check too (not just work at runtime), use
        `get_entity_as(entity_id, DemandUnitProxy)` instead, or Python's own
        `typing.cast(DemandUnitProxy, model.get_entity(entity_id))`.
        """
        return _entity_proxy(self, entity_id)

    def get_entity_as(self, entity_id: str, cls: type[_T] | tuple[type[_T], ...]) -> _T:
        """Like `get_entity()`, but statically typed as `cls` -- so
        `model.get_entity_as("dem.ch", DemandUnitProxy).dispatch...` type-checks
        correctly, not just works at runtime. Also checked at runtime: raises
        `TypeError` if the entity's actual class doesn't match `cls`, rather
        than silently handing back the wrong type the way a bare
        `typing.cast(...)` would (`cast` is purely a type-checker hint --
        zero runtime effect, so a wrong cast stays wrong until it fails
        somewhere else, confusingly, later). Prefer this over `cast()`
        whenever you're not certain the id is what you expect.

        `cls` can also be a tuple of classes (matching `isinstance()`'s own
        convention) for the recurring case of an entity that's genuinely
        one of several known classes depending on runtime data -- e.g. a
        CSV importer's storage-capacity column covers both `StorageUnit`
        and `HydraulicStorageUnit` rows generically. `.dispatch` etc. on
        the result still type-checks (against whichever of the listed
        classes actually declares it), since all of them share the same
        `EntityProxy`-derived shape.
        """
        proxy = self.get_entity(entity_id)
        if not isinstance(proxy, cls):
            names = cls.__name__ if isinstance(cls, type) else " or ".join(c.__name__ for c in cls)
            raise TypeError(f"{entity_id!r} is a {type(proxy).__name__}, not a {names}")
        return proxy

    def ensure_entity(self, class_name: str, entity_id: str, **attributes) -> EntityProxy:
        """Create an entity if missing and set valid scalar attributes.
        Returns the entity's class-specific generated proxy (e.g.
        `GenericInterconnectorProxy` for `class_name="GenericInterconnector"`
        or the legacy alias `"Interconnector"`), same as `add_entity()`.
        """
        class_name = self._resolve_entity_class_alias(class_name)
        existing = self.entity_class(entity_id)
        if existing:
            if existing != self._canonicalize_class(class_name):
                raise ValueError(f"Entity {entity_id!r} already exists as {existing}, not {class_name}")
        else:
            self.add_entity(class_name, entity_id)
        for key, val in attributes.items():
            self.set_attribute_if_allowed(entity_id, key, val)
        return _entity_proxy(self, entity_id)

    def ensure_carrier(self, carrier_id: str, *, name: str | None = None,
                       carrier_type: str | None = None, carrier_group: str | None = None) -> EntityProxy:
        """Create or update a Carrier. Returns the typed
        `CarrierProxy`, same as `ensure_entity()` itself --
        previously discarded that in favour of the bare id string,
        the one thing that made this genuinely differ from just
        calling `ensure_entity("Carrier", ...)` directly."""
        proxy = self.ensure_entity("Carrier", carrier_id, name=name)
        self.set_attribute_if_allowed(carrier_id, "carrier_type", carrier_type)
        self.set_attribute_if_allowed(carrier_id, "carrier_group", carrier_group)
        return proxy

    def ensure_resource(self, resource_id: str, *, name: str | None = None,
                        resource_type: str | None = None, resource_group: str | None = None,
                        unit: str | None = None) -> EntityProxy:
        """Create or update a NaturalResource. Returns the typed
        `NaturalResourceProxy`, same as `ensure_entity()` itself."""
        proxy = self.ensure_entity("NaturalResource", resource_id, name=name)
        self.set_attribute_if_allowed(resource_id, "resource_type", resource_type)
        self.set_attribute_if_allowed(resource_id, "resource_group", resource_group)
        self.set_attribute_if_allowed(resource_id, "natural_resource_unit", unit)
        return proxy

    def ensure_technology(self, technology_id: str, *, class_name: str = "GeneratorType",
                          name: str | None = None, **attributes) -> EntityProxy:
        """Create or update an EnergyTechnologyType subclass. Returns
        the typed proxy (e.g. `GeneratorTypeProxy`), same as
        `ensure_entity()` itself."""
        proxy = self.ensure_entity(class_name, technology_id, name=name or technology_id)
        for key, val in attributes.items():
            self.set_attribute_if_allowed(technology_id, key, val)
        return proxy

    def set_technology(self, asset_id: str, technology_id: str,
                       *, technology_class: str = "GeneratorType", **technology_attrs) -> bool:
        """Ensure a technology entity and link an asset via hasTechnology."""
        self.ensure_technology(technology_id, class_name=technology_class, **technology_attrs)
        return self.add_relation_if_allowed(asset_id, "hasTechnology", technology_id)


    def connect_single_port(self, asset_id: str, node_id: str, *, view_id: str | None = None) -> str:
        """Attach a single-port asset directly to a network node."""
        self.add_relation_if_allowed(asset_id, "atNode", node_id, strict=True)
        return asset_id

    def connect_two_port(self, asset_id: str, from_node_id: str, to_node_id: str,
                         *, view_id: str | None = None) -> str:
        """Attach a two-port asset directly to two network nodes."""
        if not self.add_relation_if_allowed(asset_id, "fromNode", from_node_id):
            self.add_relation_if_allowed(asset_id, "node_from", from_node_id, strict=False)
        if not self.add_relation_if_allowed(asset_id, "toNode", to_node_id):
            self.add_relation_if_allowed(asset_id, "node_to", to_node_id, strict=False)
        return asset_id


    def attach_profile(self, view_or_asset_id: str, relation_id: str, profile_id: str,
                       *, timestamp_series_id: str | None = None, create: bool = False,
                       profile_type: str = "as_capacity_factor", profile_unit: str | None = None,
                       data_reference: str | None = None) -> EntityProxy:
        """Attach a Profile to a view or to the first view of an asset that supports the relation."""
        if create:
            if timestamp_series_id is None:
                raise ValueError("timestamp_series_id is required when create=True")
            self.ensure_entity("Profile", profile_id, profile_type=profile_type,
                               profile_unit=profile_unit, data_reference=data_reference)
            self.add_relation_if_allowed(profile_id, "hasTimestampSeries", timestamp_series_id, strict=True)
        self.add_relation_if_allowed(view_or_asset_id, relation_id, profile_id, strict=True)
        return _entity_proxy(self, profile_id)



    # ------------------------------------------------------------------
    # Importer-oriented domain helpers
    # ------------------------------------------------------------------


    def attach_availability_profile(self, asset_or_view_id: str, profile_id: str, **kwargs) -> EntityProxy:
        return self.attach_profile(asset_or_view_id, "hasAvailabilityProfile", profile_id, **kwargs)

    def attach_demand_profile(self, asset_or_view_id: str, profile_id: str, **kwargs) -> EntityProxy:
        return self.attach_profile(asset_or_view_id, "hasDemandProfile", profile_id, **kwargs)

    def attach_natural_inflow_profile(self, hydraulic_storage_id: str, profile_id: str, **kwargs) -> EntityProxy:
        """Attach natural water inflow profile to a HydraulicStorageUnit
        (reservoir / pondage / RoR water body), not to a HydroGenerationUnit."""
        return self.attach_profile(
            hydraulic_storage_id, "hasNaturalInflowProfile", profile_id, **kwargs
        )

