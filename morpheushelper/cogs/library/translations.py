from pathlib import Path

from PyDrocsid.translations import t


def visit_path(path: Path, prio: int = 0):
    if (p := path.joinpath("translations")).is_dir():
        t.register_namespace(path.name, p, prio=prio)
        return

    for p in path.iterdir():
        if p.is_dir() and not p.name.startswith("_"):
            visit_path(p, prio)


visit_path(Path(__file__).parent)
