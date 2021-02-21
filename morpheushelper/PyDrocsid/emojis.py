import json
import os
from typing import Dict


def _invert_dict(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        out.setdefault(v, []).append(k)
    return out


with open(os.path.join(os.path.dirname(__file__), "emoji_map.json"), encoding="utf-8") as map_file:
    name_to_emoji: Dict[str, str] = json.load(map_file)
    emoji_to_name: Dict[str, str] = _invert_dict(name_to_emoji)
