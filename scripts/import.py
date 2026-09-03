#!/usr/bin/env python3
"""Generate packages/<name>.yaml from Bioconductor's admin/manifest repo.

Fetches data-experiment.txt and workflows.txt from the `devel` and
`RELEASE_<X_Y>` branches of https://git.bioconductor.org/admin/manifest,
and writes one flat YAML file per package under packages/. Idempotent:
rerunning with no upstream change writes nothing; `state` and `since` on
an existing file are never touched, only `streams` is refreshed.

Never talks to bioconductor.org: the release/devel version pair comes from
versions.yaml in this repo (human-PRed at each release roll).

stdlib only.
"""
import re
import subprocess
import tempfile
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGES_DIR = REPO_ROOT / "packages"
MANIFEST_REPO = "https://git.bioconductor.org/admin/manifest"
COMPONENTS = ("data-experiment", "workflows")  # filename stem == component == profile


def get_versions():
    versions_file = REPO_ROOT / "versions.yaml"
    return existing_field(versions_file, "release_version"), existing_field(versions_file, "devel_version")


def clone_branch(branch, dest):
    subprocess.run(
        ["git", "clone", "--depth", "1", "--quiet", "--branch", branch, MANIFEST_REPO, str(dest)],
        check=True,
    )


def parse_names(path):
    """`Package: name` lines, blank-line separated, first line a comment."""
    names = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith("Package:"):
            names.append(line.split(":", 1)[1].strip())
    return names


def existing_field(path, field):
    """Pull a single `field: value` out of an existing entry, or None."""
    if not path.exists():
        return None
    m = re.search(rf'^{field}:\s*"?([^"\n]+?)"?\s*$', path.read_text(), re.M)
    return m.group(1) if m else None


def write_entry(name, component, streams):
    path = PACKAGES_DIR / f"{name}.yaml"
    state = existing_field(path, "state") or "active"
    since = existing_field(path, "since") or date.today().isoformat()
    stream_list = ", ".join(s for s in ("release", "devel") if s in streams)
    path.write_text(
        f"name: {name}\n"
        f"git_url: https://git.bioconductor.org/packages/{name}\n"
        f"component: {component}\n"
        f"profile: {component}\n"
        f"streams: [{stream_list}]\n"
        f"state: {state}\n"
        f'since: "{since}"\n'
    )


def main():
    release_version, _devel_version = get_versions()
    release_branch = "RELEASE_" + release_version.replace(".", "_")
    branches = {"release": release_branch, "devel": "devel"}

    # component -> package -> set of streams
    found = {c: {} for c in COMPONENTS}
    with tempfile.TemporaryDirectory() as tmp:
        for stream, branch in branches.items():
            dest = Path(tmp) / stream
            clone_branch(branch, dest)
            for component in COMPONENTS:
                for name in parse_names(dest / f"{component}.txt"):
                    found[component].setdefault(name, set()).add(stream)

    PACKAGES_DIR.mkdir(exist_ok=True)
    counts = {}
    single_stream = {}
    for component, packages in found.items():
        counts[component] = len(packages)
        single_stream[component] = sorted(n for n, s in packages.items() if len(s) == 1)
        for name, streams in sorted(packages.items()):
            write_entry(name, component, streams)

    total = sum(counts.values())
    print(f"wrote {total} package entries ({release_branch} + devel)")
    for component in COMPONENTS:
        print(f"  {component}: {counts[component]}")
    for component in COMPONENTS:
        only = single_stream[component]
        if only:
            print(f"  {component} in only one stream ({len(only)}): {', '.join(only)}")


if __name__ == "__main__":
    main()
