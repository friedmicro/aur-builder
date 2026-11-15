from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from .build import BuildError, make_local_repo
from .gitea import UploadError, ensure_token, parse_artifact, upload_artifact
from .graph import DepGraph, DependencyError
from .srcinfo import discover_packages
from .params import parse_only


DEFAULT_AUR_BUILDS = "http://git.friedmicro-lab.org/Homelab_Infra_Public/aur-builds"


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="aur_builder",
        description="Build a repo of AUR package PKGBUILD/SRCINFO in order of dependencies and publish to local Gitea instance.",
    )
    p.add_argument("--repo", default=None,
                   help="path to the aur-builds checkout (default: workspace/aur-builds)")
    p.add_argument("--clone", default=DEFAULT_AUR_BUILDS, metavar="URL",
                   help="clone aur-builds from this URL if --repo is missing "
                        f"(default: {DEFAULT_AUR_BUILDS})")
    p.add_argument("--gitea", default="http://git.friedmicro-lab.org",
                   help="Gitea base URL")
    p.add_argument("--owner", default="Homelab_Infra_Public",
                   help="Gitea org/user owning the Arch registry")
    p.add_argument("--token", default=None,
                   help="Gitea API token (defaults to GITEA_TOKEN env)")
    p.add_argument("--dry-run", action="store_true",
                   help="resolve and print the build order, then exit")
    p.add_argument("--no-upload", action="store_true",
                   help="build only; do not upload to Gitea")
    p.add_argument("--force-upload", action="store_true",
                   help="on HTTP 409, delete the existing file then re-upload")
    p.add_argument("--only", default=None, metavar="PKGS",
                   help="comma-separated package dirs to build (in dep order); "
                        "dependencies are still built first")
    return p.parse_args(argv)


def ensure_checkout(args) -> Path:
    """Return the aur-builds checkout, cloning it if absent."""
    repo = Path(args.repo) if args.repo else Path(tempfile.gettempdir()) / "aur-builds"
    if repo.exists():
        return repo
    if not args.clone:
        raise SystemExit("no checkout at %s and no --clone URL given" % repo)
    print(f"[clone] {args.clone} -> {repo}")
    proc = subprocess.run(["git", "clone", args.clone, str(repo)],
                          text=True, capture_output=True)
    if proc.returncode != 0:
        raise SystemExit("git clone failed:\n" + (proc.stdout + proc.stderr)[:2000])
    return repo


def build(args, order) -> list[Path]:
    try:
        workdir = Path(tempfile.mkdtemp(prefix="aur-build-"))
        repo_obj = make_local_repo(workdir)
        artifacts: list[Path] = []
        for p in order:
            print(f"[build] {p.primary_name} {p.version} ...")
            new = repo_obj.build_package(p)
            repo_obj.repo_add(new)
            artifacts.extend(new)
            for a in new:
                print(f"  built {a.name}")
    except BuildError as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit("Fatal build exeception")
    return artifacts


def upload_artifacts(args, artifacts):
    if args.no_upload:
        print(f"[done] built {len(artifacts)} artifact(s); upload skipped (--no-upload)")
        return 0
    try:
        token = ensure_token(args.token)
    except UploadError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    failures = 0
    for a in artifacts:
        try:
            name = parse_artifact(a.name)
            print(f"[upload] {upload_artifact(
                a, gitea_base=args.gitea, owner=args.owner,
                name=name, token=token, force=args.force_upload)}")
        except UploadError as e:
            print(f"error: {e}", file=sys.stderr)
            failures += 1

    if failures:
        raise SystemExit("Failed upload build artifacts")
    print(f"[done] built + uploaded {len(artifacts)} artifact(s)")


def main(argv=None) -> int:
    args = parse_args(argv)

    repo = ensure_checkout(args)
    pkgs = discover_packages(repo)
    if not pkgs:
        print("no packages found under", repo, file=sys.stderr)
        return 2

    graph = DepGraph.build(pkgs)
    try:
        order = graph.build_order()
    except DependencyError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    print(f"[plan] {len(order)} packages in build order:")
    for p in order:
        deps = sorted(graph.in_repo_deps[p.dir])
        suffix = f"  (needs: {', '.join(Path(d).name for d in deps)})" if deps else ""
        print(f"  {p.primary_name} {p.version}{suffix}")

    if args.only:
        order = parse_only(args, order, graph)

    if args.dry_run:
        return 0

    artifacts = build(args, order)
    upload_artifacts(args, artifacts)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
