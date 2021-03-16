from pathlib import Path

from cogs.library.translations import visit_path

visit_path(Path(__file__).parent, prio=1)
