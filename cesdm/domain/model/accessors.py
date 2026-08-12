"""cesdm.domain.model.accessors — CESDM-specific read accessors

Everything here needs actual CESDM domain concepts (belongsToGroup
groups, the technology-template default cascade, hydro/reservoir
pairing) -- the class-/entity-generic accessors that used to live here
too (entity_class, entity_data, has_entity, class_attributes,
class_relations, field_allowed, get_attribute_value,
get_relation_targets, set_attribute_if_allowed,
add_relation_if_allowed) moved to ear/model/accessors.py after
checking each one's actual implementation needed nothing CESDM-
specific at all, rather than assuming their file location already
reflected that. See CHANGELOG.md.

Auto-extracted from the legacy monolithic module as part of the
package-hierarchy refactor (see docs/architecture/package_layout.md).
Behaviour is unchanged; only module boundaries moved.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class AccessorsMixin:
    """Mixin — see module docstring for the responsibility this covers."""

    def get_effective_attribute_value(self, view_id: str, attribute_id: str,
                                      default: Any = None,
                                      technology_relation: str = "hasTechnology") -> Any:
        """Return `attribute_id`'s value on `view_id` if explicitly set there;
        otherwise fall back, in order:

        1. The same-named attribute on the represented asset's technology
           template (view -> reportsOn -> asset -> hasTechnology ->
           GeneratorType/StorageType/...) -- implements the "instance
           overrides technology-template default" cascade that
           GeneratorType/StorageType's own schema descriptions already
           promise ("Each GenerationUnit then sets only instance-specific
           overrides...").
        2. The attribute's own schema-declared default, for
           `belongsToGroup`-tagged attributes specifically -- these
           deliberately don't get their default auto-applied at
           entity-creation time (see `ear/model/entity_ops.py`'s
           `add_entity()`), since doing so unconditionally would activate
           that group's conditional-requiredness on every instance
           regardless of intent (e.g. the dynamic machine model's
           attributes on `DynamicMachineModelType.Synchronous`). Resolving the default
           here instead keeps `dyn.dynamics.d_axis_synchronous_reactance` returning the same
           value as before without ever writing it into the entity's own
           data.

        `get_attribute_value()` deliberately does none of this on its own
        -- that stays a pure direct lookup (used by validation and
        anything that needs to know exactly what was literally set, not
        what the effective value resolves to).

        tools/import_flexeco.py had already reinvented fallback 1 locally
        (its `_sv()` closure: "Get from reservoir/storage dispatch data,
        fall back to StorageType") before this existed as a shared,
        reusable method -- see CHANGELOG.md.

        Fallback 1 has no effect on validation: none of the ~22
        attributes it legitimately applies to (the GeneratorType/
        GenerationUnit and StorageType/StorageUnit overlaps) are declared
        `required: true`. Fallback 2 doesn't change what validate()
        enforces either -- only what a *read* returns when nothing was
        set; the conditional-requiredness itself is still driven by
        whether something from that group is actually present in the
        entity's own data.
        """
        val = self.get_attribute_value(view_id, attribute_id)
        if val is not None:
            return val
        asset_targets = self.get_relation_targets(view_id, "reportsOn")
        # Flattened pattern: view_id has no separate reportsOn
        # relation because it IS the asset itself (its dispatch/etc.
        # attributes live directly on it, not a separate view entity --
        # see CHANGELOG.md). Treat it as its own asset for the cascade.
        asset_id = asset_targets[0] if asset_targets else view_id
        tech_targets = self.get_relation_targets(asset_id, technology_relation)
        if tech_targets and self.has_entity(tech_targets[0]):
            # has_entity() check deliberately added: a hasTechnology
            # relation can point at an id that was never actually
            # created as a real entity (a typo, or referencing a
            # library technology that was never imported) -- found
            # directly, this crashed with an unhelpful KeyError from
            # deep inside get_attribute_value() instead of just
            # treating "nothing to fall back to" the same as "no
            # technology linked at all".
            tech_val = self.get_attribute_value(tech_targets[0], attribute_id)
            if tech_val is not None:
                return tech_val

        # Final fallback: the attribute's own schema-declared default.
        # belongsToGroup-tagged attributes deliberately don't get their
        # default auto-applied at entity-creation time any more (see
        # ear/model/entity_ops.py's add_entity()) -- doing so
        # unconditionally would activate that group's conditional-
        # requiredness on every single instance regardless of whether
        # the group was ever actually intended (e.g. the dynamic machine
        # model's attributes on DynamicMachineModelType.Synchronous,
        # which all have real IEEE-typical defaults).
        # Resolving the default here instead, on read, keeps
        # `dyn.dynamics.d_axis_synchronous_reactance` returning the same value as before
        # without ever writing it into the entity's own data.
        cname = self.entity_class(asset_id)
        adef = (self.classes.get(cname).attributes.get(attribute_id)
                if cname and cname in self.classes else None)
        if adef is not None and getattr(adef, "default", None) is not None:
            return adef.default
        return default

    # -----------------------------------------------------------------
    # Representation-view lookups -- read-only queries over an asset's
    # existing views. Moved here from builders.py: these don't build
    # anything, they read existing structure, so they belong with the
    # rest of the read-only accessors, not mixed in among the
    # multi-step composite constructors builders.py is for. See
    # docs/architecture/package_layout.md.
    # -----------------------------------------------------------------

    def views_for_asset(self, asset_id: str) -> Dict[str, str]:
        """Return {view_class: view_id} for representations of an asset."""
        result: Dict[str, str] = {}
        for vcls in self._discover_view_classes():
            for vid, ent in (self.entities.get(vcls) or {}).items():
                raw = (getattr(ent, "data", {}) or {}).get(self._REPORTS_ON_REL)
                targets = raw if isinstance(raw, list) else [raw]
                if asset_id in targets:
                    result[vcls] = vid
        return result

    def reservoir_for_hydro(self, hydro_id: str) -> str | None:
        """The reservoir a HydroGenerationUnit draws from, if any."""
        targets = self.get_relation_targets(hydro_id, "drawsFromHydraulicStorage")
        return targets[0] if targets else None

    def hydro_units_for_reservoir(self, reservoir_id: str) -> list[str]:
        """Every HydroGenerationUnit that draws from this reservoir."""
        result: list[str] = []
        for hid in (self.entities.get("HydroGenerationUnit") or {}):
            if reservoir_id in self.get_relation_targets(hid, "drawsFromHydraulicStorage"):
                result.append(hid)
        return result
