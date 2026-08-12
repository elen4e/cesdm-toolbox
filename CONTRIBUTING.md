# Contributing to CESDM

Thanks for your interest in the Common Energy System Domain Model. This is a research prototype developed within the SWEET-CoSi project (see [`docs/guide/00_disclaimer.md`](docs/guide/00_disclaimer.md)) — feedback, issues, and contributions from the energy-system modelling community are genuinely welcome.

## Before you start

For anything beyond a small fix (a new schema class, a new importer/exporter, a change to an existing class's attributes/relations, a new analysis profile), please open an issue first describing the proposed approach. CESDM's schemas are shared across every tool in the toolbox, so a change that looks local can have wider consequences — an issue lets that get discussed before any code is written.

Small, self-contained fixes (a typo, a broken link, a bug with an obvious fix) can go straight to a pull request.

## Development setup

```bash
git clone https://github.com/cesdm/cesdm-toolbox.git
cd cesdm-toolbox

python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -e ".[all]"
```

`.[all]` installs every optional dependency group (PyPSA/pandapower/MATPOWER import, HDF5/Parquet profiles, Excel, dev tools) — the safest default while developing, even if your change only touches one of them.

## Running the tests

```bash
pytest tests/ -q
```

The test suite is the actual specification of correct behaviour — a change that isn't covered by an existing or new test isn't considered done. If you're fixing a bug, add a regression test that fails before your fix and passes after it.

## Working with schemas

Adding or changing an entity class means editing (or adding) a YAML file under `schemas/cesdm/entities/` — never hard-coding energy-domain knowledge in Python (see [`docs/guide/03_schemas.md`](docs/guide/03_schemas.md) for why that split exists). After any schema change, regenerate the derived files before committing:

```bash
python -m tools.update_generated
```

This regenerates `cesdm/generated_proxies.py`, the type stubs under `typings/`, and `docs/reference/schema-reference.html` (plus alias `schema_reference.html`). All three are committed artifacts, kept in sync with the schema — a PR that changes a schema file without regenerating these will fail review.

## Documentation changes

Every code example in `docs/` and the READMEs is expected to actually run — copy it into a script and execute it, or check it against the toolbox directly, before submitting. A documentation PR that adds code which doesn't work will be asked to fix it before merge. If you're touching `mkdocs.yml` navigation or adding a new page, run:

```bash
mkdocs build --strict
```

to catch broken internal links and navigation issues locally.

## Pull requests

- Keep PRs focused on one change; a schema change and an unrelated refactor are two PRs.
- Write a clear, descriptive title and summary — what changed and why, not just what files were touched.
- Make sure `pytest tests/ -q` passes locally before opening the PR.
- Link the issue it addresses, if there is one.

## Where to go for more context

- [`README.md`](README.md) — quick start and repository overview.
- [`docs/architecture/architecture_overview.md`](docs/architecture/architecture_overview.md) — how the EAR engine and CESDM layer fit together.
- [`docs/architecture/schema_governance.md`](docs/architecture/schema_governance.md) — the schema extension mechanism, for anything beyond a small class addition.
- [`CHANGELOG.md`](CHANGELOG.md) — what has already changed and why, useful context before proposing something that touches the same area.
