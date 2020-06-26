import yaml
import copy


class Translations:
    def __init__(self, lang: str):
        self._translations: dict = yaml.safe_load(open(f"translations/{lang}.yml"))

    def __getattr__(self, item: str):
        if item.startswith("f_"):
            return self._translations[item[2:]].format
        return copy.deepcopy(self._translations[item])


translations = Translations("en")
