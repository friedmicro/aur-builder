from pathlib import Path

def parse_only(args, order, graph):
    keep = {p.strip() for p in args.only.split(",") if p.strip()}
    by_name = {Path(p.dir).name: p.dir for p in order}
    selected: set[str] = set()

    def add(dirname: str) -> None:
        if dirname in selected:
            return
        for dep in graph.in_repo_deps.get(dirname, set()):
            add(dep)
        selected.add(dirname)

    for k in keep:
        target = by_name.get(k)
        if target is None:
            print(f"warning: --only '{k}' matches no package dir", file=sys.stderr)
            continue
        add(target)
    order = [p for p in order if p.dir in selected]
    print(f"[plan] restricted to --only {sorted(keep)} "
          f"(incl. in-repo deps): {len(order)} package(s)")
    return order
