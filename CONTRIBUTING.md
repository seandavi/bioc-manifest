# Contributing

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
Contributions are accepted under the [Apache License 2.0](LICENSE).

This repo is the trust root for [bioc-build](https://github.com/seandavi/bioc-build):
the build system will only build a package listed here, under the policy
recorded here. Nothing in this repo runs code except `scripts/validate.py`,
which checks that every `packages/*.yaml` entry is well formed. All changes
are human pull requests, reviewed before merge — there is no automated writer.

- **Add a package:** open a PR adding `packages/<name>.yaml`. See the format
  in [README.md](README.md#entry-format). `scripts/import.py` is how the
  initial ~460 entries were generated from Bioconductor's own
  `admin/manifest`; a package not on that list is added by hand, following
  the same shape.
- **Deprecate a package:** open a PR setting `state: deprecated` on its file
  and say why in the PR description.
- **Change policy:** edit `policy.yaml` by PR; bump `policy_version`.

Every PR must pass `.github/workflows/validate.yml`.
