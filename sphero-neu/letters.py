"""
Letter settings for NEUMANN (one letter per robot) and the LED test, shared with the web page.

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

WORD = "NEUMANN"     # one letter per robot, robot 1 on the left

DEFAULT = {
    # "compass": every robot finds magnetic north and heading 0 = north, so all
    # robots face the same way whatever their hand aim was.
    # "aim": heading 0 = the direction set in the aim phase (blue tail light to you).
    "align": "compass",
    # True: hand mode. Stabilization off and no automatic turning, so the robots
    # can be turned by hand and stay put. Back to False: they keep that direction.
    "hand": False,
    "heading": 0,       # all robots turn to this heading (compass: 0 north, 90 east; aim: 0 away from you)
    # rotation: letter on the matrix (90 degree steps); turn: extra turn of that
    # one robot in degrees, to straighten a robot that is a bit off
    "letters": [{"letter": ch, "rotation": 0, "mirror": False, "turn": 0} for ch in WORD],
}


def valid(cfg):
    """Returns a clean copy of cfg, falling back to DEFAULT for bad values."""
    out = copy.deepcopy(DEFAULT)
    try:
        out["heading"] = int(cfg.get("heading", out["heading"])) % 360
        if cfg.get("align") in ("compass", "aim"):
            out["align"] = cfg["align"]
        out["hand"] = bool(cfg.get("hand", False))
        for i, item in enumerate(cfg.get("letters", [])[:len(out["letters"])]):
            out["letters"][i]["rotation"] = int(item.get("rotation", 0)) // 90 * 90 % 360
            out["letters"][i]["mirror"] = bool(item.get("mirror", False))
            out["letters"][i]["turn"] = (int(item.get("turn", 0)) + 180) % 360 - 180
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
