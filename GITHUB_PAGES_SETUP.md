# GitHub Pages setup

The repository includes `.github/workflows/docs.yml`. It builds the MkDocs site
with `mkdocs build --strict` and deploys from `main`.

## Triggers

- Push to `main` when `docs/**`, `mkdocs.yml`, `docs-requirements.txt`, or the
  workflow file change
- Manual run via **Actions → Documentation → Run workflow** (`workflow_dispatch`)

Pull requests do not deploy Pages. Run `mkdocs build --strict` locally (or in CI
tests) to validate docs before merge.

## One-time repository setting

1. Open **Settings → Pages**.
2. Under **Build and deployment**, select **GitHub Actions** as the source.
3. Push to `main`, or run the **Documentation** workflow manually.

The published site URL is configured in `mkdocs.yml` as
`https://cesdm.github.io/cesdm-toolbox/`.
