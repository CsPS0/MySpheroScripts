"""
Tic-tac-toe with up to 9 BOLTs on the floor. The robots never drive.

Robots: by default ("auto") the game scans and connects the 9 nearest free
BOLTs (strongest signal first; if one fails, the next one is tried). Or it uses
the fixed robot names in data/tictactoe.json (edit on the web page, auto off).

Numbering (at the start and again after every game): all balls show "?". Put
them in a 3x3 grid and shake them in reading order, top left first:

    1 2 3
    4 5 6
    7 8 9

The first ball shaken becomes square 1, the next square 2, and so on. So the
numbers always match where the balls really are. 6 and 9 are underlined.
With fewer than 9 robots, the remaining squares are played on the web page.
"Same layout" on the web page skips the numbering when nothing was moved.

Play: X always starts. Shake a ball to take its square for the player whose
turn it is. The front LEDs of the free squares show whose turn it is (red X,
blue O). Three in a row: the winning squares turn green and blink. After
RECOUNT_AFTER seconds the numbering starts again, the robots stay connected.

Talks to the web page: prints "STATE {json}" lines, reads stdin lines:
"play <1-9>", "new" (same layout), "recount", "start" (end numbering early),
"config {json}" (orientation). Ends on Ctrl+C.
"""

import contextlib
import json
import math
import queue
import sys
import threading
import time
from pathlib import Path

from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color

import indicators
import sphero_ble

CONFIG = Path(__file__).resolve().parent / "data" / "tictactoe.json"
DEFAULT_CONFIG = {
    "auto": True,       # True: the 9 nearest BOLTs, False: the names below
    "robots": ["SB-3FF5", "SB-034E", "SB-61A9", "", "", "", "", "", ""],
    "rotation": 0,      # glyph rotation on the matrix, like the Letters panel
    "mirror": False,
}

SCAN_TIME = 10           # s, auto mode scan
PER_ADAPTER = 20         # robots per Bluetooth adapter (10 at once are proven)
MAX_TIMEOUTS = 3         # timeouts in a row before an adapter counts as full
SHAKE_G = 2.2            # g, a sample above this is a shake peak
SHAKE_PEAKS = 2          # peaks needed ...
SHAKE_WINDOW = 1.0       # ... within this many seconds
SHAKE_COOLDOWN = 1.5     # s, ignore a robot after it was shaken
RECOUNT_AFTER = 6.0      # s after a game ends before the numbering starts again
BLINK = 0.35             # s, blink period of the winning squares
STREAM_MS = 200          # ms, accelerometer streaming interval (shake detection)
DRAW_AT_ONCE = 3         # robots drawing their matrix at the same time

# One Bluetooth adapter carries all 9 robots. By default spherov2 streams 9
# sensors from every BOLT, and redrawing all 9 matrices at once sends about 90
# commands in a burst: together they corrupted the Bluetooth data (bad
# checksums, garbled matrices). Only the accelerometer is needed here, and the
# drawing is spread out.
UNUSED_SENSORS = ("accel_one", "ambient_light", "attitude", "core_time",
                  "gyroscope", "locator", "quaternion", "velocity")
_draw_slots = threading.BoundedSemaphore(DRAW_AT_ONCE)

NUMBER_COLOR = Color(200, 200, 200)
WAIT_COLOR = Color(255, 160, 0)          # "?" while waiting to be numbered
PLAYER_COLOR = {"X": Color(255, 30, 30), "O": Color(30, 110, 255)}
WIN_COLOR = Color(0, 255, 60)
DRAW_COLOR = Color(255, 180, 0)
OFF = Color(0, 0, 0)

LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]

GLYPHS = {
    "1": ["...XX...", "..XXX...", ".XXXX...", "...XX...", "...XX...", "...XX...", "...XX...", ".XXXXXX."],
    "2": ["..XXXX..", ".XX..XX.", ".....XX.", "....XX..", "...XX...", "..XX....", ".XX.....", ".XXXXXX."],
    "3": ["..XXXX..", ".XX..XX.", ".....XX.", "...XXX..", ".....XX.", ".....XX.", ".XX..XX.", "..XXXX.."],
    "4": ["....XX..", "...XXX..", "..XXXX..", ".XX.XX..", "XX..XX..", "XXXXXXX.", "....XX..", "....XX.."],
    "5": [".XXXXXX.", ".XX.....", ".XX.....", ".XXXXX..", ".....XX.", ".....XX.", ".XX..XX.", "..XXXX.."],
    # 6 and 9 are shorter and underlined, so they cannot be mixed up
    "6": ["..XXXX..", ".XX.....", ".XXXXX..", ".XX..XX.", ".XX..XX.", "..XXXX..", "........", ".XXXXXX."],
    "7": [".XXXXXX.", ".....XX.", "....XX..", "....XX..", "...XX...", "...XX...", "..XX....", "..XX...."],
    "8": ["..XXXX..", ".XX..XX.", ".XX..XX.", "..XXXX..", ".XX..XX.", ".XX..XX.", ".XX..XX.", "..XXXX.."],
    "9": ["..XXXX..", ".XX..XX.", ".XX..XX.", "..XXXXX.", ".....XX.", "..XXXX..", "........", ".XXXXXX."],
    "X": ["XX....XX", "XXX..XXX", ".XXXXXX.", "..XXXX..", "..XXXX..", ".XXXXXX.", "XXX..XXX", "XX....XX"],
    "O": ["..XXXX..", ".XXXXXX.", "XXX..XXX", "XX....XX", "XX....XX", "XXX..XXX", ".XXXXXX.", "..XXXX.."],
    "?": ["..XXXX..", ".XX..XX.", ".....XX.", "....XX..", "...XX...", "...XX...", "........", "...XX..."],
}


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        cfg.update(json.loads(CONFIG.read_text()))
    except (OSError, ValueError):
        pass
    robots = [str(n).strip().upper() for n in cfg.get("robots", [])][:9]
    cfg["robots"] = robots + [""] * (9 - len(robots))
    cfg["rotation"] = int(cfg.get("rotation", 0)) // 90 * 90 % 360
    cfg["mirror"] = bool(cfg.get("mirror", False))
    cfg["auto"] = bool(cfg.get("auto", True))
    return cfg


def connect_robots(cfg, stack, want=9):
    """Connects up to `want` robots, at most PER_ADAPTER per Bluetooth adapter.
    Returns a list of (name, api, toy).

    Each robot gets its own ExitStack, and on exit all robots disconnect at the
    same time: one after another, 9 robots took longer than the web server's
    stop grace time, so the program got killed with the robots still connected."""
    robots = []
    robot_stacks = []

    def disconnect_all():
        threads = [threading.Thread(target=st.close, daemon=True) for st in robot_stacks]
        for th in threads:
            th.start()
        for th in threads:
            th.join(timeout=10)
    stack.callback(disconnect_all)
    adapters = sphero_ble.list_adapters() or ["default"]
    load = {a: 0 for a in adapters}
    full = set()
    timeouts = {a: 0 for a in adapters}
    sphero_ble.release_stale(log=lambda m: print(m, flush=True))
    print(f"Bluetooth adapters: {', '.join(a for a in adapters)} "
          f"(up to {PER_ADAPTER} robots each).", flush=True)

    def free_adapter():
        for a in adapters:
            if a not in full and load[a] < PER_ADAPTER:
                return a
        return None

    def connect(name, attempts):
        adapter = free_adapter()
        if adapter is None:
            return False
        print(f"Robot {len(robots) + 1}: connecting {name}...", flush=True)
        own = contextlib.ExitStack()
        try:
            toy, api = sphero_ble.connect_toy(
                name, lambda t: own.enter_context(SpheroEduAPI(t)),
                attempts=attempts, adapter=adapter if len(adapters) > 1 and adapter != "default" else None)
            robots.append((name, api, toy))
            robot_stacks.append(own)
            load[adapter] += 1
            timeouts[adapter] = 0
        except ConnectionError as e:
            print(f"  {e}", flush=True)
            if isinstance(e.__cause__, TimeoutError):
                timeouts[adapter] += 1
            if timeouts[adapter] >= MAX_TIMEOUTS:
                full.add(adapter)       # this adapter holds no more connections
                print(f"  {adapter or 'Bluetooth adapter'} is full with {load[adapter]} robots.",
                      flush=True)
        return True

    if cfg["auto"]:
        print(f"Scanning {SCAN_TIME} s for free BOLTs nearby...", flush=True)
        candidates = sphero_ble.scan_bolts(SCAN_TIME)
        print(f"  {len(candidates)} found: " + ", ".join(
            f"{n} ({rssi} dBm)" for n, _, rssi in candidates), flush=True)
        for name, _, _ in candidates:
            if len(robots) == want or not connect(name, attempts=1):   # spares left: no retry
                break
    else:
        for name in [n for n in cfg["robots"] if n][:want]:
            if not connect(name, attempts=2):
                break
    print(f"{len(robots)} robots connected.", flush=True)
    if len(robots) < want and free_adapter() is None:
        print("The Bluetooth adapter is full. For more robots, plug in a USB Bluetooth "
              "adapter and start the game again.", flush=True)
    return robots


class Display:
    """Drawing for one robot in its own thread. Only the latest glyph and the
    latest front LED color are sent, older requests are dropped."""

    def __init__(self, api, toy, stop):
        self.api, self.toy, self.stop = api, toy, stop
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._glyph = None          # (rows, color, rotation, mirror)
        self._led = None
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def glyph(self, rows, color, rotation, mirror):
        with self._lock:
            self._glyph = (rows, color, rotation, mirror)
        self._wake.set()

    def solid(self, color):
        """Whole matrix in one color (fast)."""
        with self._lock:
            self._glyph = (None, color, 0, False)
        self._wake.set()

    def led(self, color):
        with self._lock:
            self._led = color
        self._wake.set()

    def _run(self):
        while not self.stop.is_set():
            self._wake.wait(0.2)
            self._wake.clear()
            with self._lock:
                glyph, led = self._glyph, self._led
                self._glyph = self._led = None
            try:
                if led is not None:
                    self.api.set_front_led(led)
                if glyph is not None:
                    with _draw_slots:
                        if glyph[0] is None:
                            indicators.fill_all(self.toy, glyph[1])
                        else:
                            indicators.show_bitmap(self.api, self.toy, *glyph)
            except Exception as e:
                print(f"  display: {type(e).__name__}", flush=True)


class ShakeDetector:
    """Detects a shake from the streamed accelerometer data (no extra commands)."""

    def __init__(self, api):
        self.api = api
        self.peaks = []
        self.last_sample = None
        self.quiet_until = 0.0

    def shaken(self):
        sample = self.api.get_acceleration()
        if sample is None or sample is self.last_sample:
            return False
        self.last_sample = sample
        now = time.monotonic()
        if now < self.quiet_until:
            return False
        g = math.sqrt(sample["x"] ** 2 + sample["y"] ** 2 + sample["z"] ** 2)
        if g < SHAKE_G:
            return False
        self.peaks = [t for t in self.peaks if now - t < SHAKE_WINDOW] + [now]
        if len(self.peaks) >= SHAKE_PEAKS:
            self.peaks = []
            self.quiet_until = now + SHAKE_COOLDOWN
            return True
        return False


class Game:
    """
    Robots are numbered by connection order (0..n-1). cell_of maps robot ->
    square (0..8), it is set in the numbering phase. Phases:
    "numbering" -> "play" -> "over" -> (after RECOUNT_AFTER) "numbering" ...
    """

    def __init__(self, cfg, names, displays):
        self.cfg = cfg
        self.names = names              # robot -> name
        self.displays = displays        # robot -> Display
        self.cell_of = {}
        self.previous = {}              # last complete numbering, for "Same layout"
        self.recount()

    # --- numbering ---------------------------------------------------------
    def recount(self):
        if self.cell_of:
            self.previous = dict(self.cell_of)
        self.phase = "numbering"
        self.cell_of = {}
        self.board, self.winner, self.line, self.ended_at = [None] * 9, None, None, None
        for r, d in self.displays.items():
            d.glyph(GLYPHS["?"], WAIT_COLOR, self.cfg["rotation"], self.cfg["mirror"])
            d.led(WAIT_COLOR)
        print("Numbering: shake the balls in reading order, top left first.", flush=True)
        if not self.displays:
            self.new()

    def number(self, r):
        if r in self.cell_of:
            return False
        cell = len(self.cell_of)
        self.cell_of[r] = cell
        print(f"  {self.names[r]} is square {cell + 1}", flush=True)
        self.draw(r)
        self.displays[r].led(OFF)
        if len(self.cell_of) == len(self.displays):
            self.new()
        return True

    def robot_at(self, cell):
        for r, c in self.cell_of.items():
            if c == cell:
                return r
        return None

    # --- game --------------------------------------------------------------
    def same_layout(self):
        """New game without numbering again (nothing was moved)."""
        if not self.cell_of:
            self.cell_of = dict(self.previous)
        self.new()

    def new(self):
        """New game with the current numbering."""
        for r in list(self.displays):                 # unnumbered robots sit out
            if r not in self.cell_of:
                self.displays[r].glyph(GLYPHS["?"], OFF, 0, False)
                self.displays[r].led(OFF)
        self.phase = "play"
        self.board = [None] * 9
        self.turn = "X"
        self.winner, self.line, self.ended_at = None, None, None
        for r in self.cell_of:
            self.draw(r)
        self.turn_leds()
        web = [str(c + 1) for c in range(9) if self.robot_at(c) is None]
        print("New game. X starts." + (f" Squares {', '.join(web)} are on the web page." if web else ""),
              flush=True)

    def draw(self, r, color=None):
        cell = self.cell_of[r]
        mark = self.board[cell] if self.phase != "numbering" else None
        rows = GLYPHS[mark or str(cell + 1)]
        color = color or (PLAYER_COLOR[mark] if mark else NUMBER_COLOR)
        self.displays[r].glyph(rows, color, self.cfg["rotation"], self.cfg["mirror"])

    def turn_leds(self):
        for r, cell in self.cell_of.items():
            self.displays[r].led(PLAYER_COLOR[self.turn] if self.board[cell] is None else OFF)

    def play(self, cell, source):
        if self.phase != "play" or not 0 <= cell < 9 or self.board[cell]:
            return False
        self.board[cell] = self.turn
        print(f"{self.turn} takes square {cell + 1} ({source})", flush=True)
        r = self.robot_at(cell)
        if r is not None:
            self.draw(r)
        for line in LINES:
            if all(self.board[c] == self.turn for c in line):
                self.winner, self.line = self.turn, list(line)
                for c in line:
                    if self.robot_at(c) is not None:
                        self.draw(self.robot_at(c), WIN_COLOR)
                print(f"{self.turn} wins: squares {', '.join(str(c + 1) for c in line)}", flush=True)
                break
        else:
            if all(self.board):
                self.winner = "draw"
                print("Draw.", flush=True)
            else:
                self.turn = "O" if self.turn == "X" else "X"
        if self.winner:
            self.phase = "over"
            self.ended_at = time.monotonic()
            print(f"Numbering starts again in {RECOUNT_AFTER:.0f} s "
                  "(or press Same layout on the web page).", flush=True)
        else:
            self.turn_leds()
        return True

    def shake(self, r):
        if self.phase == "numbering":
            return self.number(r)
        if self.phase == "play" and r in self.cell_of:
            return self.play(self.cell_of[r], f"shake {self.names[r]}")
        return False

    def tick(self, blink_on):
        """Called regularly. Blinks the result, starts the numbering again."""
        if self.phase != "over":
            return False
        if time.monotonic() - self.ended_at >= RECOUNT_AFTER:
            self.recount()
            return True
        cells, color = (range(9), DRAW_COLOR) if self.winner == "draw" else (self.line, WIN_COLOR)
        for c in cells:
            r = self.robot_at(c)
            if r is not None:
                self.displays[r].led(color if blink_on else OFF)
        return False

    def reorient(self, rotation, mirror):
        self.cfg["rotation"], self.cfg["mirror"] = rotation, mirror
        for r, d in self.displays.items():
            if r in self.cell_of:
                win = self.line and self.cell_of[r] in self.line
                self.draw(r, WIN_COLOR if win else None)
            elif self.phase == "numbering":
                d.glyph(GLYPHS["?"], WAIT_COLOR, rotation, mirror)

    def state(self):
        cells = []
        for c in range(9):
            r = self.robot_at(c)
            cells.append({"robot": self.names[r] if r is not None else "", "connected": r is not None})
        return {
            "phase": self.phase, "next": len(self.cell_of) + 1,
            "robots": len(self.displays), "numbered": len(self.cell_of),
            "board": self.board, "turn": getattr(self, "turn", "X"),
            "winner": self.winner, "line": self.line, "cells": cells,
            "rotation": self.cfg["rotation"], "mirror": self.cfg["mirror"],
        }


def read_stdin(commands):
    for line in sys.stdin:
        commands.put(line.strip())
    commands.put("eof")


def main():
    cfg = load_config()
    with contextlib.ExitStack() as stack:
        robots = connect_robots(cfg, stack)

        stop = threading.Event()
        ready = []
        for name, api, toy in robots:
            try:
                for attempt in range(2):
                    try:
                        api.set_stabilization(False)        # no motor work when a ball is lifted
                        api.set_back_led(OFF)
                        if hasattr(toy, "sensor_control"):  # accelerometer only, see UNUSED_SENSORS
                            toy.sensor_control.disable(*UNUSED_SENSORS)
                            toy.sensor_control.set_interval(STREAM_MS)
                        break
                    except Exception:
                        if attempt == 1:
                            raise
                ready.append((name, api, toy))
            except Exception as e:
                print(f"  {name}: not responding ({type(e).__name__}), left out of the game", flush=True)
        robots = ready
        print(f"{len(robots)} robots ready.", flush=True)
        names = {r: name for r, (name, _, _) in enumerate(robots)}
        displays = {r: Display(api, toy, stop) for r, (_, api, toy) in enumerate(robots)}
        detectors = {r: ShakeDetector(api) for r, (_, api, _) in enumerate(robots)}
        game = Game(cfg, names, displays)

        commands = queue.Queue()
        threading.Thread(target=read_stdin, args=(commands,), daemon=True).start()

        def emit():
            print("STATE " + json.dumps(game.state()), flush=True)

        emit()
        blink_on, next_blink = False, 0.0
        try:
            while True:
                changed = False
                for r, det in detectors.items():
                    if det.shaken():
                        changed |= game.shake(r)
                try:
                    cmd = commands.get_nowait()
                except queue.Empty:
                    cmd = None
                if cmd == "eof":
                    break
                if cmd == "new":
                    game.same_layout()
                    changed = True
                elif cmd == "recount":
                    game.recount()
                    changed = True
                elif cmd == "start":
                    if game.phase == "numbering":
                        game.new()
                        changed = True
                elif cmd and cmd.startswith("play "):
                    with contextlib.suppress(ValueError):
                        changed |= game.play(int(cmd.split()[1]) - 1, "web page")
                elif cmd and cmd.startswith("config "):
                    with contextlib.suppress(ValueError, KeyError):
                        new = json.loads(cmd[len("config "):])
                        game.reorient(int(new["rotation"]) // 90 * 90 % 360, bool(new["mirror"]))
                        changed = True
                if time.monotonic() >= next_blink:
                    blink_on = not blink_on
                    changed |= game.tick(blink_on)
                    next_blink = time.monotonic() + BLINK
                if changed:
                    emit()
                time.sleep(0.03)
        except KeyboardInterrupt:
            pass
        finally:
            print("Stopping: clearing the robots...", flush=True)
            stop.set()
            deadline = time.monotonic() + 3
            for d in displays.values():
                d.thread.join(timeout=max(0.0, deadline - time.monotonic()))

            def reset(api, toy):                # 3 commands: matrix off, LED off, stabilization on
                with contextlib.suppress(Exception):
                    indicators.fill_all(toy, OFF)
                with contextlib.suppress(Exception):
                    api.set_front_led(OFF)
                with contextlib.suppress(Exception):
                    api.set_stabilization(True)
            threads = [threading.Thread(target=reset, args=(api, toy), daemon=True)
                       for _, api, toy in robots]
            for th in threads:
                th.start()
            for th in threads:
                th.join(timeout=6)
            print("Disconnecting...", flush=True)
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped.")
