from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Package:
    dir: str
    base: str
    pkgver: str
    pkgrel: str
    names: list[str] = field(default_factory=list)
    depends: list[str] = field(default_factory=list)
    makedepends: list[str] = field(default_factory=list)
    optdepends: list[str] = field(default_factory=list)
    provides: list[str] = field(default_factory=list)

    @property
    def version(self) -> str:
        return f"{self.pkgver}-{self.pkgrel}"

    @property
    def primary_name(self) -> str:
        return self.names[0] if self.names else self.base


def _split_dep(spec: str) -> str:
    spec = spec.strip()
    for cut in ("<=", ">=", "=", "<", ">"):
        idx = spec.find(cut)
        if idx != -1:
            return spec[:idx].strip()
    return spec


MULTI_FIELDS = {
    "pkgname", "arch", "license", "depends", "makedepends", "optdepends",
    "provides", "conflicts", "replaces", "source", "sha256sums", "md5sums",
    "backup", "groups", "options",
}
SCALAR_FIELDS = {
    "pkgbase", "pkgver", "pkgrel", "epoch", "pkgdesc", "url", "install",
}


def parse_srcinfo(text: str) -> dict:
    from collections import defaultdict
    raw: dict[str, list[str]] = defaultdict(list)
    for line in text.splitlines():
        if not line.strip():
            continue
        key, _, value = line.strip().partition("=")
        raw[key.strip()].append(value.strip())

    fields: dict[str, str | list[str]] = {}
    for key, values in raw.items():
        if key in MULTI_FIELDS:
            fields[f"list:{key}"] = values
        elif key in SCALAR_FIELDS:
            fields[key] = values[-1]
        else:
            if len(values) == 1:
                fields[key] = values[0]
            else:
                fields[f"list:{key}"] = values
    return fields


def load_package(pkg_dir: str | os.PathLike) -> Package:
    d = Path(pkg_dir)
    srcinfo = d / ".SRCINFO"
    if not srcinfo.exists():
        raise FileNotFoundError(f"no .SRCINFO in {d} (run makepkg --printsrcinfo)")
    fields = parse_srcinfo(srcinfo.read_text(encoding="utf-8", errors="replace"))

    names = list(fields.get("list:pkgname") or [fields.get("pkgname") or d.name])
    base = fields.get("pkgbase") or d.name

    return Package(
        dir=str(d),
        base=base,
        pkgver=fields.get("pkgver", ""),
        pkgrel=fields.get("pkgrel", "1"),
        names=[n.strip() for n in names if n and n.strip()],
        depends=[_split_dep(x) for x in fields.get("list:depends", [])],
        makedepends=[_split_dep(x) for x in fields.get("list:makedepends", [])],
        optdepends=fields.get("list:optdepends", []),
        provides=[_split_dep(x) for x in fields.get("list:provides", [])],
    )


def discover_packages(repo_root: str | os.PathLike) -> list[Package]:
    root = Path(repo_root)
    out: list[Package] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name in ("infra", "tools") or entry.name.startswith("."):
            continue
        if (entry / ".SRCINFO").exists() or (entry / "PKGBUILD").exists():
            out.append(load_package(entry))
    return out
