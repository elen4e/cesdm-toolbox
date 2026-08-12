# Contributing

CESDM is an open collaborative project. Contributions to the **toolbox**, **schemas**, and **documentation** are welcome.

## Where to contribute

| Area | Repository | Typical changes |
|------|------------|-----------------|
| Python toolbox, schemas, examples | [cesdm/cesdm-toolbox](https://github.com/cesdm/cesdm-toolbox) | Bug fixes, import/export tools, validation |
| Documentation (this site) | Same repo, `docs/` folder | Tutorials, guides, glossary |

## Quick start for contributors

1. Fork and clone [cesdm-toolbox](https://github.com/cesdm/cesdm-toolbox).
2. Create a branch from `main`.
3. Install in editable mode: `pip install -e ".[dev]"` (see [Installation](../getting-started/installation.md)).
4. For documentation changes, also run [Building the Documentation](building-docs.md) locally.
5. Open a pull request with a short description of **why** the change helps modellers or integrators.

Detailed guidelines: [`CONTRIBUTING.md`](https://github.com/cesdm/cesdm-toolbox/blob/main/CONTRIBUTING.md) in the repository.

## Documentation contributions

Energy system modellers can improve the docs without touching Python internals:

- Fix unclear tutorial steps or wrong API examples
- Add FAQ entries from questions you hit in practice
- Improve diagrams and workflow descriptions

Build locally with `mkdocs serve` before submitting. Use `mkdocs build --strict` to catch broken links.

## Reporting issues

Use [GitHub Issues](https://github.com/cesdm/cesdm-toolbox/issues) for bugs, documentation gaps, and feature requests. Include:

- CESDM / toolbox version or commit
- Minimal code or model snippet to reproduce
- Expected vs actual behaviour

## License

Contributions are accepted under the project [MIT License](https://github.com/cesdm/cesdm-toolbox/blob/main/LICENSE).

→ [How to cite CESDM](citation.md) · [Building docs locally](building-docs.md)
