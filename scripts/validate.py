#!/usr/bin/env python3
"""Validate packages/*.yaml and policy.yaml. stdlib only, no pyyaml.

Exit 0 if everything is well formed, exit 1 (with file:line of the first
problem in each bad file) otherwise. `--selftest` proves the validator
itself catches a broken fixture, then exits 0/1 on that instead of the repo.
"""
import re
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPONENTS = {"data-experiment", "workflows"}
STATES = {"active", "deprecated"}
STREAMS = {"release", "devel"}


def parse_flat_yaml(text):
    """`key: value` and `key: [a, b]` only, one per line. Returns dict of str/list."""
    data = {}
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.split("#", 1)[0].strip()
        if not stripped:
            continue
        if ":" not in stripped:
            raise ValueError(f"line {lineno}: no ':'")
        key, _, value = stripped.partition(":")
        key, value = key.strip(), value.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            data[key] = [v.strip() for v in inner.split(",") if v.strip()] if inner else []
        else:
            data[key] = value.strip('"')
    return data


def validate_package(path, policy_profiles):
    data = parse_flat_yaml(path.read_text())
    for field in ("name", "git_url", "component", "profile", "streams", "state"):
        if field not in data:
            raise ValueError(f"{path}: missing '{field}'")
    if data["name"] != path.stem:
        raise ValueError(f"{path}: name '{data['name']}' != filename '{path.stem}'")
    if data["component"] not in COMPONENTS:
        raise ValueError(f"{path}: component '{data['component']}' not in {COMPONENTS}")
    if data["profile"] not in policy_profiles:
        raise ValueError(f"{path}: profile '{data['profile']}' not in policy.yaml profiles")
    if data["state"] not in STATES:
        raise ValueError(f"{path}: state '{data['state']}' not in {STATES}")
    streams = data["streams"]
    if not streams or not set(streams) <= STREAMS:
        raise ValueError(f"{path}: streams {streams} not a non-empty subset of {STREAMS}")
    expected_url = f"https://git.bioconductor.org/packages/{data['name']}"
    if data["git_url"] != expected_url:
        raise ValueError(f"{path}: git_url '{data['git_url']}' != '{expected_url}'")


def validate_policy(path):
    data = parse_flat_yaml(path.read_text())
    if "policy_version" not in data:
        raise ValueError(f"{path}: missing 'policy_version'")
    profiles = set()
    for line in path.read_text().splitlines():
        m = re.match(r"^  (\S+):$", line)
        if m and m.group(1) not in ("defaults",):
            profiles.add(m.group(1))
    for required in ("data-experiment", "workflows"):
        if required not in profiles:
            raise ValueError(f"{path}: missing profile '{required}'")
    return profiles


def run(root):
    policy_profiles = validate_policy(root / "policy.yaml")
    for path in sorted((root / "packages").glob("*.yaml")):
        validate_package(path, policy_profiles)


def selftest():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "packages").mkdir()
        (root / "policy.yaml").write_text(Path(REPO_ROOT / "policy.yaml").read_text())
        (root / "packages" / "bad.yaml").write_text(
            "name: bad\ngit_url: https://git.bioconductor.org/packages/bad\n"
            "component: not-a-real-component\nprofile: workflows\n"
            "streams: [devel]\nstate: active\n"
        )
        try:
            run(root)
        except ValueError:
            print("selftest: OK (broken fixture correctly rejected)")
            return 0
        print("selftest: FAILED (broken fixture was not rejected)")
        return 1


def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    try:
        run(REPO_ROOT)
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    print("validate: OK")


if __name__ == "__main__":
    main()
