from pathlib import Path

from cogs.library.translations import load_translations

load_translations(Path(__file__).parent, prio=1)
