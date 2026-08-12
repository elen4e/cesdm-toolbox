# Building the Documentation Locally

Preview the CESDM documentation site before publishing to [GitHub Pages](https://cesdm.github.io/cesdm-toolbox/).

## Requirements

- Python 3.11+
- Git

## Setup

From the **repository root** (where `mkdocs.yml` lives):

```bash
python -m venv .venv-docs
source .venv-docs/bin/activate   # Windows: .venv-docs\Scripts\activate

python -m pip install --upgrade pip
pip install -e .                 # local package (examples / API snippets may import ear/cesdm)
pip install -r docs-requirements.txt
```

If you do not have a local clone, install from GitHub instead:

```bash
pip install "git+https://github.com/cesdm/cesdm-toolbox.git@main"
pip install -r docs-requirements.txt
```

## Preview

```bash
mkdocs serve
```

Open the URL shown in the terminal (usually `http://127.0.0.1:8000/cesdm-toolbox/`).  
Stop the server with `Ctrl+C`.

## Production build

```bash
mkdocs build --strict
```

Output is written to `site/`. The GitHub Actions workflow in `.github/workflows/docs.yml` runs the same strict build and deploys to GitHub Pages on pushes to `main` (or via manual `workflow_dispatch`).

## What the site includes

| Content | Source |
|---------|--------|
| Markdown guides & tutorials | `docs/**/*.md` |
| CESDM Schema Reference | static `docs/reference/schema-reference.html` |
| EAR API Reference | `docs/reference/api-reference.md` |
| Theme / nav | `mkdocs.yml` (Material for MkDocs, redirects, Mermaid) |

The schema HTML companion is regenerated from the YAML schemas when needed:

```bash
python -m tools.update_generated
# or the schema HTML generator used by your release process
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ConfigError: The 'redirects' plugin is not installed` | Run `pip install -r docs-requirements.txt` |
| Mermaid diagrams show as code | Ensure `pymdownx.superfences` includes the `mermaid` custom fence in `mkdocs.yml` |
| Broken image paths | Run `mkdocs serve` from the repo root; use relative paths in Markdown |
| `ModuleNotFoundError: ear` during local experiments | Install the package first (`pip install -e .`) |

→ [Contributing](contributing.md)
