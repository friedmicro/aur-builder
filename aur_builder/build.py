from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .srcinfo import Package


class BuildError(Exception):
    pass


class LocalRepo:
    def __init__(self, workdir: str | os.PathLike):
        self.root = Path(workdir)
        self.repo_dir = self.root / "repo"
        self.pkg_dir = self.root / "pkgs"
        self.src_dir = self.root / "src"
        self.build_dir = self.root / "build"
        self.log_dir = self.root / "log"
        self.pacman_conf = Path("/etc/pacman.conf")
        self.makepkg_conf = self.root / "makepkg.conf"
        self.db = self.repo_dir / "local.db.tar.gz"

        for d in (self.repo_dir, self.pkg_dir, self.src_dir,
                  self.build_dir, self.log_dir):
            d.mkdir(parents=True, exist_ok=True)

    def _sudo(self, argv: list[str], **kw) -> subprocess.CompletedProcess:
        return subprocess.run(["sudo", *argv], text=True, capture_output=True, **kw)

    def configure(self) -> None:
        makepkg_path = "/etc/makepkg.conf"
        if not self.pacman_conf.exists() or not Path(makepkg_path).exists():
            raise BuildError("/etc/pacman.conf or /etc/makepkg.conf missing (not an Arch build host?)")

        base_makepkg = Path(makepkg_path).read_text(encoding="utf-8")
        self.makepkg_conf.write_text(
            base_makepkg
            + f"\nPKGDEST={self.pkg_dir}\n"
            + f"SRCDEST={self.src_dir}\n"
            + f"BUILDDIR={self.build_dir}\n"
            + f"LOGDEST={self.log_dir}\n",
            encoding="utf-8",
        )

    def _run(self, argv: list[str], cwd: str | os.PathLike | None = None,
             **kw) -> subprocess.CompletedProcess:
        return subprocess.run(
            argv, cwd=cwd, text=True, capture_output=True, **kw
        )

    def build_package(self, pkg: Package, timeout: int | None = None) -> list[Path]:
        """Build one package with makepkg; return the new artifact paths."""
        if os.geteuid() == 0:
            raise BuildError(
                "makepkg refuses to run as root; run as an unprivileged build "
                "user (the Dockerfile creates `builduser`)"
            )
        for tool in ("makepkg", "repo-add", "pacman"):
            if shutil.which(tool) is None:
                raise BuildError(f"required tool not found: {tool}")

        before = {
            p.name: p.stat().st_mtime
            for p in self.pkg_dir.glob("*.pkg.tar.*")
            if not p.name.endswith(".sig")
        }
        argv = ["makepkg", "--config", str(self.makepkg_conf),
                "--noconfirm", "--syncdeps", "--force"]
        proc = self._run(argv, cwd=pkg.dir, timeout=timeout)
        if proc.returncode != 0:
            tail = (proc.stdout + proc.stderr)[-3000:]
            raise BuildError(f"makepkg {pkg.primary_name} failed:\n{tail}")

        artifacts = []
        for p in sorted(self.pkg_dir.glob("*.pkg.tar.*")):
            if p.name.endswith(".sig"):
                continue
            prev = before.get(p.name)
            if prev is None or p.stat().st_mtime > prev:
                artifacts.append(p)
        if not artifacts:
            raise BuildError(
                f"makepkg {pkg.primary_name} produced no .pkg.tar.* artifact"
            )
        return artifacts

    def repo_add(self, artifacts: list[Path]) -> None:
        if not artifacts:
            return
        argv = ["repo-add", str(self.db)] + [str(a) for a in artifacts]
        proc = self._run(argv)
        if proc.returncode != 0:
            raise BuildError("repo-add failed:\n" + (proc.stdout + proc.stderr)[:2000])
        proc = self._sudo(["pacman", "-U", "--noconfirm"] + [str(a) for a in artifacts])
        if proc.returncode != 0:
            raise BuildError("pacman -U install failed:\n" + (proc.stdout + proc.stderr)[:2000])
        proc = self._sudo(["pacman", "-Sy"])
        if proc.returncode != 0:
            raise BuildError("pacman -Sy failed:\n" + (proc.stdout + proc.stderr)[:2000])


def make_local_repo(workdir: str | os.PathLike) -> LocalRepo:
    repo = LocalRepo(workdir)
    repo.configure()
    return repo
