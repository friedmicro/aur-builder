from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .srcinfo import Package


class DependencyError(Exception):
    pass


@dataclass
class DepGraph:
    packages: list[Package] = field(default_factory=list)
    provider_of: dict[str, str] = field(default_factory=dict)
    in_repo_deps: dict[str, set[str]] = field(default_factory=dict)

    @classmethod
    def build(cls, packages: Iterable[Package]) -> "DepGraph":
        pkgs = list(packages)
        g = cls(packages=pkgs)

        for p in pkgs:
            for name in p.names:
                g.provider_of.setdefault(name, p.dir)
            for prov in p.provides:
                g.provider_of.setdefault(prov, p.dir)

        for p in pkgs:
            intern: set[str] = set()
            for dep in list(p.depends) + list(p.makedepends):
                provider = g.provider_of.get(dep)
                if provider is not None and provider != p.dir:
                    intern.add(provider)
            g.in_repo_deps[p.dir] = intern
        return g

    def build_order(self) -> list[Package]:
        pending = [p.dir for p in self.packages]
        done: set[str] = set()
        order: list[str] = []

        while pending:
            progressed = False
            for pkg_dir in list(pending):
                if self.in_repo_deps[pkg_dir] <= done:
                    order.append(pkg_dir)
                    done.add(pkg_dir)
                    pending.remove(pkg_dir)
                    progressed = True
            if not progressed:
                raise DependencyError("unsatisfiable in-repo dependency cycle among: " + ", ".join(sorted(pending)))

        by_dir = {p.dir: p for p in self.packages}
        return [by_dir[d] for d in order]
