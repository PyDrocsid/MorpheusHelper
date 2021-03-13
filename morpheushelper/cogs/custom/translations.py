from pathlib import Path

from PyDrocsid.translations import t

for cogdir in Path(__file__).parent.iterdir():
    if not cogdir.is_dir() or cogdir.name.startswith("_"):
        continue

    path = cogdir.joinpath("translations")
    if path.is_dir():
        t.register_namespace(cogdir.name, path, prio=1)
