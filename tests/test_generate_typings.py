"""
tools/generate_typings.py: generates editor-friendly .pyi stubs from
the schema tree + BuildersMixin's AST. Contributed and integrated —
see CHANGELOG.md for the full assessment, including a real
non-determinism/correctness bug found and fixed (candidate selection
for a view family with multiple valid concrete classes, e.g.
Generation.DispatchView vs GenerationUnit.DispatchResult both
being view_family: dispatch, used to pick whichever Python's set
iteration happened to produce first).

These tests validate the generator runs cleanly against the real repo
and that its output is both syntactically valid and, for the specific
bug found, semantically correct -- not just "doesn't crash".
"""

import ast
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def generated_typings(tmp_path_factory):
    out = tmp_path_factory.mktemp("typings")
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "generate_typings.py"),
         "--schemas", str(REPO_ROOT / "schemas/cesdm"),
         "--source-root", str(REPO_ROOT),
         "--output", str(out)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    return out


def test_generator_produces_expected_files(generated_typings):
    expected = [
        "cesdm/__init__.pyi",
        "cesdm/domain/__init__.pyi",
        "cesdm/domain/model/__init__.pyi",
        "cesdm/domain/model/core.pyi",
        "cesdm/helpers.pyi",
        "cesdm/proxy.pyi",
        "cesdm/generated_proxies.pyi",
        "cesdm_toolbox.pyi",
    ]
    for rel in expected:
        assert (generated_typings / rel).is_file(), rel


def test_every_generated_stub_is_syntactically_valid_python(generated_typings):
    for f in generated_typings.rglob("*.pyi"):
        try:
            ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError as e:
            pytest.fail(f"{f}: {e}")


def test_dispatch_family_resolves_to_plan_view_not_result_view(generated_typings):
    """GenerationUnitProxy.dispatch must resolve to GenerationUnitDispatchProxy
    (the belongsToGroup-tagged fields flattened directly onto the asset --
    see CHANGELOG.md), never anything Result-related: results
    (GenerationUnit.DispatchResult) are entirely separate standalone
    entities now, sharing no group name with the asset's own flattened
    dispatch data at all, so there's no more ambiguity to resolve here."""
    text = (generated_typings / "cesdm" / "generated_proxies.pyi").read_text()
    start = text.index("class GenerationUnitProxy(EntityProxy):")
    block = text[start:text.index("\n\n", start)]
    assert "dispatch: GenerationUnitDispatchProxy" in block
    assert "Result" not in block.split("dispatch:")[1].split("\n")[0]


def test_core_stub_covers_builder_methods(generated_typings):
    text = (generated_typings / "cesdm" / "domain" / "model" / "core.pyi").read_text()
    for method in ("get_entity", "get_entity_as", "ensure_entity", "ensure_carrier",
                   "connect_single_port", "connect_two_port", "attach_profile"):
        assert f"def {method}(" in text


def test_core_stub_covers_every_public_runtime_method(tmp_path):
    """The actual point of extending extract_methods() beyond
    BuildersMixin: every real, public, callable method CesdmModel has
    at runtime must appear in the generated stub. Regression test for
    the gap found by running Pyright against real usage (~60% of the
    public surface was invisible to editors, including summary(),
    get_effective_attribute_value(), import_library(), and the raw EAR
    primitives add_entity/add_attribute/add_relation -- all of which
    the README's own recommended quick-start example uses)."""
    import re
    import subprocess
    import sys as _sys

    from cesdm_toolbox import build_model_from_yaml

    model = build_model_from_yaml("schemas/cesdm")
    runtime_methods = {
        m for m in dir(model) if not m.startswith("_") and callable(getattr(model, m))
    }

    out = tmp_path / "typings_coverage_check"
    subprocess.run(
        [_sys.executable, str(REPO_ROOT / "tools" / "generate_typings.py"),
         "--schemas", str(REPO_ROOT / "schemas/cesdm"),
         "--source-root", str(REPO_ROOT),
         "--output", str(out)],
        check=True, capture_output=True,
    )
    text = (out / "cesdm" / "domain" / "model" / "core.pyi").read_text()
    stub_methods = {m.group(1) for m in re.finditer(r"    def (\w+)\(", text)}

    missing = sorted(runtime_methods - stub_methods)
    assert not missing, f"Methods missing from the generated stub: {missing}"


def test_generated_stubs_type_check_the_readme_quickstart_example(generated_typings):
    """Best-effort: if pyright is installed, actually run it against a
    snippet mirroring the README's recommended quick-start example, and
    assert the parts that ARE in BuildersMixin type-check cleanly.
    Skips gracefully if pyright isn't available (it's a dev-only tool,
    not a runtime dependency of this repo)."""
    pyright = None
    for candidate in ("pyright", sys.executable + " -m pyright"):
        try:
            subprocess.run(candidate.split() + ["--version"], capture_output=True, check=True)
            pyright = candidate
            break
        except Exception:
            continue
    if pyright is None:
        pytest.skip("pyright not installed")

    snippet = generated_typings.parent / "quickstart_snippet.py"
    snippet.write_text(
        "from cesdm_toolbox import build_model_from_yaml\n"
        "from cesdm.generated_proxies import GenerationUnitProxy\n"
        "model = build_model_from_yaml('schemas/cesdm')\n"
        "model.import_library('library/default_library')\n"
        "model.add_entity('EnergySystemModel', 'sys1')\n"
        "model.add_entity('ElectricalBus', 'bus.1')\n"
        "model.add_attribute('bus.1', 'nominal_voltage', 380)\n"
        "bus = model.get_entity('bus.1')\n"
        "model.add_entity('GenerationUnit', 'gen1')\n"
        "model.set_technology('gen1', 'Generation.Nuclear.LWR', technology_class='GeneratorType')\n"
        "model.add_relation('gen1', 'atNode', bus)\n"
        "gen = model.get_entity_as('gen1', GenerationUnitProxy)\n"
        "gen.dispatch.nominal_power_capacity = 1600\n"
        "gen.connect(bus)\n"
        "print(gen.dispatch.energy_conversion_efficiency)\n"
        "print(model.summary())\n"
        "model.validate_or_raise()\n"
    )
    pyrightconfig = generated_typings.parent / "pyrightconfig.json"
    pyrightconfig.write_text(
        '{"stubPath": "' + str(generated_typings).replace("\\", "\\\\") + '"}'
    )
    result = subprocess.run(
        pyright.split() + [str(snippet)],
        capture_output=True, text=True, cwd=str(generated_typings.parent),
    )
    assert "0 errors" in result.stdout, result.stdout


def test_timestamp_series_proxy_is_in_the_generated_stub(generated_typings):
    proxy_stub = (generated_typings / "cesdm" / "generated_proxies.pyi").read_text(encoding="utf-8")
    assert "class TimestampSeriesProxy(EntityProxy):" in proxy_stub


def test_relation_members_use_target_proxy_types(generated_typings):
    proxy_stub = (generated_typings / "cesdm" / "generated_proxies.pyi").read_text(encoding="utf-8")
    start = proxy_stub.index("class ElectricalBusProxy(EntityProxy):")
    block = proxy_stub[start:proxy_stub.index("\n\n", start)]
    assert "def belongsToGeographicalRegion(self) -> GeographicalRegionProxy | None: ..." in block
    assert "def belongsToGeographicalRegion(self, value: GeographicalRegionProxy | str) -> None: ..." in block
    assert "def belongsToCarrierDomain(self) -> CarrierDomainProxy: ..." in block
    assert "def belongsToCarrierDomain(self, value: CarrierDomainProxy | CarrierDomainId) -> None: ..." in block


def test_runtime_relation_getter_returns_concrete_proxy():
    from cesdm.generated_proxies import GeographicalRegionProxy
    from cesdm_toolbox import build_model_from_yaml

    model = build_model_from_yaml("schemas/cesdm")
    model.add_entity("GeographicalRegion", "region.typed")
    region = model.get_entity("region.typed")
    model.ensure_carrier("carrier.electricity", name="Electricity", carrier_group="electricity")
    model.add_entity("CarrierDomain", "domain.electricity")
    model.add_relation("domain.electricity", "hasCarrier", "carrier.electricity")
    model.add_entity("ElectricalBus", "bus.typed")
    model.add_relation("bus.typed", "belongsToGeographicalRegion", region)
    model.add_relation("bus.typed", "belongsToCarrierDomain", "domain.electricity")
    bus = model.get_entity("bus.typed")

    assert isinstance(bus.belongsToGeographicalRegion, GeographicalRegionProxy)
    assert bus.belongsToGeographicalRegion.id == "region.typed"


def test_core_stub_declares_model_storage_attributes(generated_typings):
    text = (generated_typings / "cesdm" / "domain" / "model" / "core.pyi").read_text(encoding="utf-8")
    assert "classes: Dict[str, EntityClass]" in text
    assert "entities: Dict[str, Dict[str, Entity]]" in text
    assert "inheritance: Dict[str, Union[str, List[str], None]]" in text
    assert "schema_manifest: SchemaManifest" in text


# ---------------------------------------------------------------------
# generated_proxies.pyi vs proxy.pyi split -- found while investigating
# a real Pyright report on reference_energy_system_model.py: "Cannot access
# attribute dispatch for class EntityProxy". Root cause: every per-
# entity proxy subclass (DemandUnitProxy, etc.) was declared in
# proxy.pyi, but the *real* classes live in cesdm/generated_proxies.py
# -- a separate runtime module. Anyone importing the correct way (`from
# cesdm.generated_proxies import DemandUnitProxy`, the same path
# cesdm.proxy._entity_proxy() itself uses) got the real, type-
# annotation-free class instead of any enriched stub, silently losing
# all `.dispatch` etc. typing.
#
# (A second, related bug -- RETURN_OVERRIDES mapping a tuple-returning
# composite builder to a single bare type, and the import-collection
# code then choking on the resulting compound-type string -- was found
# and fixed the same way, in the generated_builders.py-based
# add_reservoir_hydro()/add_phs_open_loop()/add_phs_closed_loop().
# Those functions, and RETURN_OVERRIDES' entries for them, no longer
# exist at all -- generated_builders.py was removed entirely, see
# CHANGELOG.md -- so the two tests that pinned down that specific bug
# were removed along with it rather than kept as dead assertions.)
# ---------------------------------------------------------------------

def test_demand_unit_proxy_stub_lives_in_generated_proxies_not_proxy_pyi(generated_typings):
    proxy_stub = (generated_typings / "cesdm" / "proxy.pyi").read_text(encoding="utf-8")
    generated_stub = (generated_typings / "cesdm" / "generated_proxies.pyi").read_text(encoding="utf-8")
    assert "class DemandUnitProxy" not in proxy_stub
    assert "class DemandUnitProxy(EntityProxy):" in generated_stub
    assert "dispatch: DemandUnitDispatchProxy" in generated_stub


def test_get_entity_as_and_dispatch_type_check_together_with_pyright(generated_typings):
    """The actual end-to-end regression: model.get_entity_as(id, DemandUnitProxy)
    followed by .dispatch.<real attribute> must type-check with 0
    errors, and the same with a deliberate typo must be flagged --
    exercising both the _T TypeVar declaration in core.pyi and the
    generated_proxies.pyi split together, the same way asking "does
    .dispatch type-check too?" on real example code caught this."""
    pyright = None
    for candidate in ("pyright", sys.executable + " -m pyright"):
        try:
            subprocess.run(candidate.split() + ["--version"], capture_output=True, check=True)
            pyright = candidate
            break
        except Exception:
            continue
    if pyright is None:
        pytest.skip("pyright not installed")

    good = generated_typings.parent / "get_entity_as_good.py"
    good.write_text(
        "from cesdm_toolbox import build_model_from_yaml\n"
        "from cesdm.generated_proxies import DemandUnitProxy\n"
        "model = build_model_from_yaml('schemas/cesdm')\n"
        "model.add_entity('DemandUnit', 'dem.1')\n"
        "d = model.get_entity_as('dem.1', DemandUnitProxy)\n"
        "d.dispatch.annual_energy_demand = 1000\n"
    )
    bad = generated_typings.parent / "get_entity_as_bad.py"
    bad.write_text(
        "from cesdm_toolbox import build_model_from_yaml\n"
        "from cesdm.generated_proxies import DemandUnitProxy\n"
        "model = build_model_from_yaml('schemas/cesdm')\n"
        "model.add_entity('DemandUnit', 'dem.1')\n"
        "d = model.get_entity_as('dem.1', DemandUnitProxy)\n"
        "d.dispatch.anual_energy_demand = 1000\n"  # typo
    )
    pyrightconfig = generated_typings.parent / "pyrightconfig.json"
    pyrightconfig.write_text('{"stubPath": "' + str(generated_typings).replace("\\", "\\\\") + '"}')

    good_result = subprocess.run(pyright.split() + [str(good)], capture_output=True, text=True,
                                 cwd=str(generated_typings.parent))
    assert "0 errors" in good_result.stdout, good_result.stdout

    bad_result = subprocess.run(pyright.split() + [str(bad)], capture_output=True, text=True,
                                cwd=str(generated_typings.parent))
    assert "anual_energy_demand" in bad_result.stdout, bad_result.stdout


def test_add_entity_infers_the_specific_proxy_type_from_the_class_literal(generated_typings):
    """model.add_entity("GenerationUnit", id) must type-check as
    GenerationUnitProxy directly (via the per-class @overload
    declarations in core.pyi), with .dispatch/.power_flow/etc. usable
    immediately -- no get_entity_as() cast needed for the common
    "just created it" case. Asked directly why this couldn't "just
    happen" on add_entity() itself: it can, once CesdmModel overrides
    it to return the wrapped proxy directly (see CHANGELOG.md) and the
    stub declares one overload per concrete class."""
    pyright = None
    for candidate in ("pyright", sys.executable + " -m pyright"):
        try:
            subprocess.run(candidate.split() + ["--version"], capture_output=True, check=True)
            pyright = candidate
            break
        except Exception:
            continue
    if pyright is None:
        pytest.skip("pyright not installed")

    good = generated_typings.parent / "add_entity_good.py"
    good.write_text(
        "from cesdm_toolbox import build_model_from_yaml\n"
        "model = build_model_from_yaml('schemas/cesdm')\n"
        "gen = model.add_entity('GenerationUnit', 'gen.1')\n"
        "gen.nominal_power_capacity = 800\n"
        "gen.dispatch.nominal_power_capacity = 800\n"
        "dyn = model.add_entity('DynamicMachineModelType.Synchronous', 'dyn.1')\n"
        "dyn.dynamics.inertia_constant = 6.5\n"
    )
    bad = generated_typings.parent / "add_entity_bad.py"
    bad.write_text(
        "from cesdm_toolbox import build_model_from_yaml\n"
        "model = build_model_from_yaml('schemas/cesdm')\n"
        "gen = model.add_entity('GenerationUnit', 'gen.1')\n"
        "gen.dispatch.nomial_power_capacity = 800\n"  # typo
    )
    pyrightconfig = generated_typings.parent / "pyrightconfig.json"
    pyrightconfig.write_text('{"stubPath": "' + str(generated_typings).replace("\\", "\\\\") + '"}')

    good_result = subprocess.run(pyright.split() + [str(good)], capture_output=True, text=True,
                                 cwd=str(generated_typings.parent))
    assert "0 errors" in good_result.stdout, good_result.stdout

    bad_result = subprocess.run(pyright.split() + [str(bad)], capture_output=True, text=True,
                                cwd=str(generated_typings.parent))
    assert "nomial_power_capacity" in bad_result.stdout, bad_result.stdout



