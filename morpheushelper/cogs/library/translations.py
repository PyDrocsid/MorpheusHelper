from pathlib import Path

from PyDrocsid.translations import t

t.register_namespace("g", Path(__file__).parent.joinpath("_translations"))

for cogdir in Path(__file__).parent.iterdir():
    if not cogdir.is_dir() or cogdir.name.startswith("_"):
        continue

    path = cogdir.joinpath("translations")
    if path.is_dir():
        t.register_namespace(cogdir.name, path)
