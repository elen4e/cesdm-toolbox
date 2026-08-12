"""cesdm.domain.model.hdf5_parquet — HDF5 / Parquet persistence

Binary tabular export/import, primarily used for large profile /
time-series data.

Auto-extracted from the legacy monolithic module as part of the
package-hierarchy refactor (see docs/architecture/package_layout.md).
Behaviour is unchanged; only module boundaries moved.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional, Union
import os
import pathlib
import re
import yaml


class Hdf5ParquetMixin:
    """Mixin — see module docstring for the responsibility this covers."""

    def export_hdf5(
        self,
        path: Union[str, pathlib.Path],
        *,
        values_map: Optional[Dict[str, "np.ndarray"]] = None,
    ) -> None:
        """
        Export all ``TimestampSeries`` and ``Profile`` entities to an HDF5
        file.

        HDF5 layout
        -----------
        ::

            <file>.h5
            ├── timestamps/
            │   └── <timestamp_series_id>/
            │       attrs: start_datetime, resolution, length, timezone, name
            │       dataset "values": int64[length]  (Unix epoch seconds,
            │                         written only if present in values_map)
            └── profiles/
                └── <profile_id>/
                    attrs: profile_type, profile_unit, timestamp_series_id, name
                    dataset "values": float64[length]
                                      (written only if present in values_map)

        Every attribute stored on the HDF5 group mirrors the corresponding
        EAR attribute on the entity, so the HDF5 file is self-describing
        without needing the YAML model alongside it.

        Parameters
        ----------
        path :
            Output ``.h5`` file path. Parent directories are created if absent.
        values_map :
            Optional dict mapping entity id → numpy array of numeric values.
            Keys for ``TimestampSeries`` entities should map to int64 epoch
            arrays; keys for ``Profile`` entities should map to float64 value
            arrays.  If an entity id is not present in the map, only the
            metadata group and attributes are written — no ``values`` dataset.
        """
        try:
            import h5py
            import numpy as np
        except ImportError:
            raise ImportError(
                "h5py and numpy are required for HDF5 export. "
                "Install with: pip install h5py numpy"
            )

        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        values_map = values_map or {}

        def _attr_val(raw) -> str:
            """Unwrap AttributeValue dict to a plain scalar for HDF5 storage."""
            if isinstance(raw, dict) and "value" in raw:
                v = raw["value"]
                return "" if v is None else str(v)
            return "" if raw is None else str(raw)

        def _write_entity_attrs(grp, ent, cname: str) -> None:
            """Write all EAR attributes of one entity as HDF5 group attributes."""
            cdef = self.classes.get(cname)
            if not cdef:
                return
            attrs_def, refs_def = self._collect_inherited_fields(cdef)
            data = getattr(ent, "data", {}) or {}

            for aname in attrs_def:
                if aname in data and data[aname] not in ("", None):
                    grp.attrs[aname] = _attr_val(data[aname])

            # Store relations as semicolon-joined id strings
            for rname in refs_def:
                if rname in data and data[rname] not in ("", None):
                    val = data[rname]
                    if isinstance(val, (list, tuple)):
                        targets = [str(v) for v in val if v not in ("", None)]
                    else:
                        targets = [str(val)]
                    grp.attrs[rname] = ";".join(targets)

        with h5py.File(str(p), "w") as hf:
            ts_grp = hf.require_group("timestamps")
            pr_grp = hf.require_group("profiles")

            # ── TimestampSeries ──────────────────────────────────────
            for eid, ent in (self.entities.get("TimestampSeries") or {}).items():
                grp = ts_grp.require_group(eid)
                _write_entity_attrs(grp, ent, "TimestampSeries")

                if eid in values_map:
                    arr = np.asarray(values_map[eid], dtype=np.int64)
                    if "values" in grp:
                        del grp["values"]
                    grp.create_dataset("values", data=arr,
                                       compression="gzip", compression_opts=4)

            # ── Profile ──────────────────────────────────────────────
            for eid, ent in (self.entities.get("Profile") or {}).items():
                grp = pr_grp.require_group(eid)
                _write_entity_attrs(grp, ent, "Profile")

                if eid in values_map:
                    arr = np.asarray(values_map[eid], dtype=np.float64)
                    if "values" in grp:
                        del grp["values"]
                    grp.create_dataset("values", data=arr,
                                       compression="gzip", compression_opts=4)

    def import_hdf5(
        self,
        path: Union[str, pathlib.Path],
        *,
        load_values: bool = True,
        strict_unknown: bool = False,
    ) -> Dict[str, Any]:
        """
        Import ``TimestampSeries`` and ``Profile`` entities from an HDF5 file
        produced by :meth:`export_hdf5`.

        Entity metadata (attributes and relations) is read from HDF5 group
        attributes and loaded into the EAR model exactly as if they had come
        from a YAML import.  Numeric payloads (``values`` datasets) are
        returned separately so the caller can store them as needed without
        the model holding large arrays in memory.

        Parameters
        ----------
        path :
            Input ``.h5`` file path.
        load_values :
            If True (default), read ``values`` datasets and include them in
            the returned ``values_map``.  Set to False to load only metadata
            (fast, low-memory).
        strict_unknown :
            If True, unrecognised attribute or relation names are added to the
            ``unknowns`` list.

        Returns
        -------
        dict with keys:

        ``created_entities`` : int
            Number of new entity instances created.
        ``set_attributes`` : int
            Number of attribute values set.
        ``set_relations`` : int
            Number of relation values set.
        ``unknowns`` : list
            Unrecognised field names encountered (empty unless strict_unknown).
        ``values_map`` : dict[str, np.ndarray]
            Maps entity id → numpy array for every entity whose HDF5 group
            contained a ``values`` dataset.  Empty if load_values is False.
        """
        try:
            import h5py
            import numpy as np
        except ImportError:
            raise ImportError(
                "h5py and numpy are required for HDF5 import. "
                "Install with: pip install h5py numpy"
            )

        p = pathlib.Path(path)
        created = set_attr = set_ref = 0
        unknowns: List[tuple] = []
        values_map: Dict[str, Any] = {}

        # Pre-collect known fields per class
        _known_attrs: Dict[str, set] = {}
        _known_refs:  Dict[str, set] = {}
        for cname, cdef in self.classes.items():
            a, r = self._collect_inherited_fields(cdef)
            _known_attrs[cname] = set(a.keys())
            _known_refs[cname]  = set(r.keys())

        def _ensure(cls: str, eid: str) -> None:
            nonlocal created
            if cls not in self.entities:
                self.entities[cls] = {}
            if eid not in self.entities[cls]:
                self.add_entity(cls, eid)
                created += 1

        def _ingest_group(grp, cls: str, eid: str) -> None:
            nonlocal set_attr, set_ref
            known_a = _known_attrs.get(cls, set())
            known_r = _known_refs.get(cls, set())

            for key, raw in grp.attrs.items():
                val = str(raw).strip() if raw is not None else ""
                if not val:
                    continue
                if key in known_a:
                    coerced = self._coerce_for_attr(cls, key, val)
                    self.add_attribute(eid, key, coerced)
                    set_attr += 1
                elif key in known_r:
                    # Relations stored as semicolon-joined ids
                    targets = [t.strip() for t in val.split(";") if t.strip()]
                    for tgt in targets:
                        self.add_relation(eid, key, tgt)
                        set_ref += 1
                else:
                    if strict_unknown:
                        unknowns.append((cls, eid, f"unknown field: {key}"))

        with h5py.File(str(p), "r") as hf:

            # ── TimestampSeries ──────────────────────────────────────
            ts_root = hf.get("timestamps")
            if ts_root is not None:
                for eid in ts_root:
                    grp = ts_root[eid]
                    _ensure("TimestampSeries", eid)
                    _ingest_group(grp, "TimestampSeries", eid)
                    if load_values and "values" in grp:
                        values_map[eid] = grp["values"][:]

            # ── Profile ──────────────────────────────────────────────
            pr_root = hf.get("profiles")
            if pr_root is not None:
                for eid in pr_root:
                    grp = pr_root[eid]
                    _ensure("Profile", eid)
                    _ingest_group(grp, "Profile", eid)
                    if load_values and "values" in grp:
                        values_map[eid] = grp["values"][:]

        return {
            "created_entities": created,
            "set_attributes":   set_attr,
            "set_relations":    set_ref,
            "unknowns":         unknowns,
            "values_map":       values_map,
        }

    # ================================================================== #
    #  import_excel_flat                                                   #
    # ================================================================== #

    def export_parquet(
        self,
        path: Union[str, pathlib.Path],
        *,
        values_map: Optional[Dict[str, "np.ndarray"]] = None,
        wide: bool = False,
    ) -> None:
        """
        Export ``TimestampSeries`` and ``Profile`` entities to a Parquet file.

        Parquet layout — long format (default, ``wide=False``)
        -------------------------------------------------------
        One Parquet file with columns::

            entity_class   str    "TimestampSeries" or "Profile"
            entity_id      str    e.g. "profile.onwind.ch0"
            attribute      str    attribute / relation name
            value          str    attribute value as string
            values         list   numeric array (only for rows where
                                  entity_id is in values_map; otherwise null)

        Parquet layout — wide format (``wide=True``)
        --------------------------------------------
        One Parquet file per logical group:

        ``<stem>_profiles.parquet``
            Columns: ``timestamp_index`` (int64), then one column per
            profile id (float64).  Only profiles present in values_map
            are included.

        ``<stem>_metadata.parquet``
            One row per entity attribute:
            ``entity_class``, ``entity_id``, ``attribute``, ``value``

        Parameters
        ----------
        path :
            Output ``.parquet`` file path.  Parent directories are created.
        values_map :
            Optional dict mapping entity id → 1-D numpy float64 array.
        wide :
            If True, write the wide split format (profiles + metadata).
            If False (default), write a single long-format file.
        """
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
            import numpy as np
        except ImportError:
            raise ImportError(
                "pyarrow is required for Parquet export. "
                "Install with: pip install pyarrow"
            )

        p_out = pathlib.Path(path)
        p_out.parent.mkdir(parents=True, exist_ok=True)
        values_map = values_map or {}

        def _scalar(raw) -> str:
            if isinstance(raw, dict) and "value" in raw:
                v = raw["value"]
                return "" if v is None else str(v)
            return "" if raw is None else str(raw)

        def _entity_rows(cls: str) -> list:
            rows = []
            for eid, ent in (self.entities.get(cls) or {}).items():
                cdef = self.classes.get(cls)
                if not cdef:
                    continue
                attrs_def, rels_def = self._collect_inherited_fields(cdef)
                data = getattr(ent, "data", {}) or {}
                for aname in attrs_def:
                    if aname in data and data[aname] not in ("", None):
                        rows.append((cls, eid, aname, _scalar(data[aname])))
                for rname in rels_def:
                    if rname in data and data[rname] not in ("", None):
                        val = data[rname]
                        if isinstance(val, (list, tuple)):
                            joined = ";".join(str(v) for v in val if v not in ("", None))
                        else:
                            joined = str(val)
                        rows.append((cls, eid, rname, joined))
            return rows

        meta_rows = _entity_rows("TimestampSeries") + _entity_rows("Profile")

        if wide:
            # ── Wide format: two files ─────────────────────────────────────
            stem = p_out.with_suffix("")
            meta_path    = pathlib.Path(str(stem) + "_metadata.parquet")
            profile_path = pathlib.Path(str(stem) + "_profiles.parquet")

            # metadata table
            meta_table = pa.table({
                "entity_class": pa.array([r[0] for r in meta_rows], pa.string()),
                "entity_id":    pa.array([r[1] for r in meta_rows], pa.string()),
                "attribute":    pa.array([r[2] for r in meta_rows], pa.string()),
                "value":        pa.array([r[3] for r in meta_rows], pa.string()),
            })
            pq.write_table(meta_table, str(meta_path), compression="snappy")

            # profiles table (wide: one column per profile)
            profile_ids = [
                eid for eid in (self.entities.get("Profile") or {})
                if eid in values_map
            ]
            if profile_ids:
                T = len(values_map[profile_ids[0]])
                cols = {"timestamp_index": pa.array(np.arange(T, dtype=np.int64))}
                for pid in profile_ids:
                    cols[pid] = pa.array(
                        np.asarray(values_map[pid], dtype=np.float64)
                    )
                pq.write_table(pa.table(cols), str(profile_path), compression="snappy")

        else:
            # ── Long format: single file ───────────────────────────────────
            # Each profile's values array is stored as a nested list column.
            entity_classes, entity_ids, attributes, values, arrays = [], [], [], [], []
            for row in meta_rows:
                entity_classes.append(row[0])
                entity_ids.append(row[1])
                attributes.append(row[2])
                values.append(row[3])
                arrays.append(None)

            # Add one extra row per profile that has values
            for pid, arr in values_map.items():
                entity_classes.append("Profile")
                entity_ids.append(pid)
                attributes.append("__values__")
                values.append("")
                arrays.append(np.asarray(arr, dtype=np.float64).tolist())

            table = pa.table({
                "entity_class": pa.array(entity_classes, pa.string()),
                "entity_id":    pa.array(entity_ids,     pa.string()),
                "attribute":    pa.array(attributes,     pa.string()),
                "value":        pa.array(values,         pa.string()),
                "values":       pa.array(arrays,         pa.list_(pa.float64())),
            })
            pq.write_table(table, str(p_out), compression="snappy")

    def import_parquet(
        self,
        path: Union[str, pathlib.Path],
        *,
        load_values: bool = True,
        wide: bool = False,
    ) -> Dict[str, Any]:
        """
        Import ``TimestampSeries`` and ``Profile`` entities from a Parquet
        file produced by :meth:`export_parquet`.

        Parameters
        ----------
        path :
            Input ``.parquet`` file path.  For wide format, pass the metadata
            file (``<stem>_metadata.parquet``); the profiles file is found
            automatically.
        load_values :
            If True (default), load numeric profile arrays into the returned
            ``values_map``.
        wide :
            Must match the ``wide`` parameter used during export.

        Returns
        -------
        Same dict structure as :meth:`import_hdf5`:
        ``created_entities``, ``set_attributes``, ``set_relations``,
        ``unknowns``, ``values_map``.
        """
        try:
            import pyarrow.parquet as pq
            import numpy as np
        except ImportError:
            raise ImportError(
                "pyarrow is required for Parquet import. "
                "Install with: pip install pyarrow"
            )

        p_in = pathlib.Path(path)
        created = set_attr = set_ref = 0
        unknowns: List[tuple] = []
        values_map: Dict[str, Any] = {}

        _known_attrs: Dict[str, set] = {}
        _known_refs:  Dict[str, set] = {}
        for cname, cdef in self.classes.items():
            a, r = self._collect_inherited_fields(cdef)
            _known_attrs[cname] = set(a.keys())
            _known_refs[cname]  = set(r.keys())

        def _ensure(cls: str, eid: str) -> None:
            nonlocal created
            if cls not in self.entities:
                self.entities[cls] = {}
            if eid not in self.entities[cls]:
                self.add_entity(cls, eid)
                created += 1

        def _ingest_row(cls: str, eid: str, attr: str, val: str) -> None:
            nonlocal set_attr, set_ref
            if not val:
                return
            known_a = _known_attrs.get(cls, set())
            known_r = _known_refs.get(cls, set())
            if attr in known_a:
                coerced = self._coerce_for_attr(cls, attr, val)
                self.add_attribute(eid, attr, coerced)
                set_attr += 1
            elif attr in known_r:
                for tgt in (t.strip() for t in val.split(";") if t.strip()):
                    self.add_relation(eid, attr, tgt)
                    set_ref += 1

        if wide:
            meta_path    = p_in  # caller passes metadata file directly
            stem         = str(p_in.with_suffix("")).removesuffix("_metadata")
            profile_path = pathlib.Path(stem + "_profiles.parquet")

            # Ingest metadata
            tbl = pq.read_table(str(meta_path)).to_pydict()
            for cls, eid, attr, val in zip(
                tbl["entity_class"], tbl["entity_id"],
                tbl["attribute"],    tbl["value"],
            ):
                _ensure(cls, eid)
                _ingest_row(cls, eid, attr, val)

            # Ingest values
            if load_values and profile_path.exists():
                ptbl = pq.read_table(str(profile_path)).to_pydict()
                for col, arr in ptbl.items():
                    if col == "timestamp_index":
                        continue
                    values_map[col] = np.asarray(arr, dtype=np.float64)

        else:
            tbl = pq.read_table(str(p_in)).to_pydict()
            for cls, eid, attr, val, arr in zip(
                tbl["entity_class"], tbl["entity_id"],
                tbl["attribute"],    tbl["value"],
                tbl.get("values", [None] * len(tbl["entity_id"])),
            ):
                if attr == "__values__":
                    if load_values and arr is not None:
                        values_map[eid] = np.asarray(arr, dtype=np.float64)
                    continue
                _ensure(cls, eid)
                _ingest_row(cls, eid, attr, val)

        return {
            "created_entities": created,
            "set_attributes":   set_attr,
            "set_relations":    set_ref,
            "unknowns":         unknowns,
            "values_map":       values_map,
        }


    # ------------------------------------------------------------------ #
    #  User-facing domain API helpers                                      #
    # ------------------------------------------------------------------ #
