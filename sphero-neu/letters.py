"""
Letter settings for NEU and the LED test, shared with the web page.

data/letters.json holds, for each robot (left to right), the letter, its
rotation on the matrix (0, 90, 180, 270, clockwise) and whether it is
mirrored, plus the heading the robots turn to in NEU. The web page changes the
file and sends the new settings to a running program as a stdin line:

    letters {"heading": 270, "letters": [{"letter": "N", "rotation": 0, "mirror": false}, ...]}
"""

import copy
import json
import sys
import threading
from pathlib import Path

CONFIG = Path(__file__).resolve().parent / "data" / "letters.json"

DEFAULT = {
    "heading": 270,     # NEU: all robots turn to this heading (0 away from you, 90 right, 270 left)
    "letters": [
        {"letter": "N", "rotation": 0, "mirror": False},
        {"letter": "E", "rotation": 0, "mirror": False},
        {"letter": "U", "rotation": 0, "mirror": False},
    ],
}


def valid(cfg):
    """Returns a clean copy of cfg, falling back to DEFAULT for bad values."""
    out = copy.deepcopy(DEFAULT)
    try:
        out["heading"] = int(cfg.get("heading", out["heading"])) % 360
        for i, item in enumerate(cfg.get("letters", [])[:len(out["letters"])]):
            out["letters"][i]["rotation"] = int(item.get("rotation", 0)) // 90 * 90 % 360
            out["letters"][i]["mirror"] = bool(item.get("mirror", False))
    except (AttributeError, TypeError, ValueError):
        pass
    return out


def load():
    try:
        return valid(json.loads(CONFIG.read_text()))
    except (OSError, ValueError):
        return copy.deepcopy(DEFAULT)


def save(cfg):
    CONFIG.parent.mkdir(exist_ok=True)
    tmp = CONFIG.with_suffix(".tmp")
    tmp.write_text(json.dumps(valid(cfg), indent=2))
    tmp.replace(CONFIG)


def listen(on_change):
    """Calls on_change(cfg) for every "letters ..." line on stdin (own thread)."""
    def reader():
        for line in sys.stdin:
            if line.startswith("letters "):
                try:
                    on_change(valid(json.loads(line[len("letters "):])))
                except ValueError:
                    pass
    threading.Thread(target=reader, daemon=True).start()
