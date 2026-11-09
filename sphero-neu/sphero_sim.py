"""
Sphero BOLT Simulation Engine.

Simulates Sphero BOLT hardware (motors, locator tracking, 8x8 LED matrix,
accelerometer shake detection, front headlight, blue tail light, battery)
so all scripts, choreography, games, and web controls run flawlessly
without physical robots.
"""

import colorsys
import json
import math
import os
import re
import sys
import threading
import time
from pathlib import Path
from spherov2.commands.io import IO
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color

# Standard simulated robots (names, addresses, initial home coordinates in cm)
# 15 robots distributed across arena (rows of 3, 6, 6) so they never overlap in standby
DEFAULT_ROBOT_SPECS = [
    ("SB-3FF5", "D4:22:CD:00:3F:F5", -25.0, 30.0, Color(255, 59, 59)),    # 1 Red
    ("SB-034E", "D4:22:CD:00:03:4E", 0.0, 30.0, Color(46, 204, 113)),     # 2 Green
    ("SB-61A9", "D4:22:CD:00:61:A9", 25.0, 30.0, Color(52, 152, 219)),    # 3 Blue
    ("SB-1111", "D4:22:CD:00:11:11", -35.0, 0.0, Color(241, 196, 15)),    # 4 Yellow
    ("SB-2222", "D4:22:CD:00:22:22", -20.0, 0.0, Color(232, 67, 147)),    # 5 Pink
    ("SB-3333", "D4:22:CD:00:33:33", -5.0, 0.0, Color(0, 206, 201)),      # 6 Cyan
    ("SB-4444", "D4:22:CD:00:44:44", 10.0, 0.0, Color(230, 126, 34)),     # 7 Orange
    ("SB-5555", "D4:22:CD:00:55:55", 25.0, 0.0, Color(255, 255, 255)),    # 8 White
    ("SB-6666", "D4:22:CD:00:66:66", 40.0, 0.0, Color(155, 89, 182)),     # 9 Purple
    ("SB-7777", "D4:22:CD:00:77:77", -35.0, -30.0, Color(253, 121, 168)), # 10 Soft Pink
    ("SB-8888", "D4:22:CD:00:88:88", -20.0, -30.0, Color(9, 132, 227)),   # 11 Ocean Blue
    ("SB-9999", "D4:22:CD:00:99:99", -5.0, -30.0, Color(0, 184, 148)),    # 12 Mint Green
    ("SB-AAAA", "D4:22:CD:00:AA:AA", 10.0, -30.0, Color(255, 234, 167)),  # 13 Cream Yellow
    ("SB-BBBB", "D4:22:CD:00:BB:BB", 25.0, -30.0, Color(108, 92, 231)),   # 14 Violet
    ("SB-CCCC", "D4:22:CD:00:CC:CC", 40.0, -30.0, Color(214, 48, 49)),    # 15 Crimson
]

def hex_color(r, g, b):
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


class SimulatedToy:
    """Simulated Sphero BOLT toy object."""

    def __init__(self, name, address, home_x=0.0, home_y=0.0, default_color=None):
        self.name = name
        self.address = address
        self.home_x = home_x
        self.home_y = home_y
        self.x = home_x
        self.y = home_y
        self.locator_origin_x = home_x
        self.locator_origin_y = home_y
        self.locator_flags = True

        self.heading = 0.0         # 0 deg = forward / away from user (+y)
        self.speed = 0.0           # speed units (0-255)
        self.target_speed = 0.0
        self.spin_rate = 0.0       # deg/s
        self.stabilization = True

        self.front_led = Color(0, 0, 0)
        self.back_led = Color(0, 0, 0)
        self.main_led = default_color or Color(0, 0, 0)

        # 8x8 matrix (row 0 is top, col 0 is left) stored as [row][col] = (r, g, b)
        self.matrix = [[(0, 0, 0) for _ in range(8)] for _ in range(8)]
        self.matrix_lock = threading.Lock()
        self.scroll_cancel = threading.Event()

        # Accelerometer simulation
        self.shaking_until = 0.0
        self.shake_counter = 0

        self.is_connected = False
        self._api = None
        self._voltage = round(3.90 + (abs(hash(name)) % 25) * 0.01, 2)

    def wake(self):
        self.is_connected = True

    def get_battery_voltage(self):
        return self._voltage

    def get_battery_percentage(self):
        return max(5, min(100, int((self._voltage - 3.4) / (4.2 - 3.4) * 100)))

    def get_main_app_version(self):
        return "5.3"

    def set_locator_flags(self, flags):
        self.locator_flags = bool(flags)

    def reset_locator_x_and_y(self):
        self.locator_origin_x = self.x
        self.locator_origin_y = self.y

    @property
    def locator_x(self):
        return self.x - self.locator_origin_x

    @property
    def locator_y(self):
        return self.y - self.locator_origin_y

    def fill(self, x1, y1, x2, y2, r, g, b):
        with self.matrix_lock:
            x_min, x_max = max(0, min(x1, x2)), min(7, max(x1, x2))
            y_min, y_max = max(0, min(y1, y2)), min(7, max(y1, y2))
            for y in range(y_min, y_max + 1):
                for x in range(x_min, x_max + 1):
                    self.matrix[y][x] = (r, g, b)

    def pixel(self, x, y, r, g, b):
        with self.matrix_lock:
            if 0 <= x < 8 and 0 <= y < 8:
                self.matrix[y][x] = (r, g, b)

    def clear_matrix(self):
        self.scroll_cancel.set()
        with self.matrix_lock:
            for y in range(8):
                for x in range(8):
                    self.matrix[y][x] = (0, 0, 0)

    def set_compressed_frame_player_text_scrolling(self, text, r, g, b, fps=10, loop=True):
        self.scroll_cancel.set()
        self.scroll_cancel = threading.Event()
        cancel = self.scroll_cancel

        def scroll_worker():
            # Build 8xN bitmap from basic 5x7 / 8x8 font
            glyphs = {
                "n": ["..XXXX..", ".XX..XX.", ".XX..XX.", ".XX..XX.", ".XX..XX.", ".XX..XX.", ".XX..XX.", "........"],
                "e": ["........", "..XXXX..", ".XX..XX.", ".XXXXXX.", ".XX.....", "..XXXX..", "........", "........"],
                "u": ["........", ".XX..XX.", ".XX..XX.", ".XX..XX.", ".XX..XX.", "..XXXXX.", "........", "........"],
                "m": ["........", ".XXXXXX.", ".X.X.X..", ".X.X.X..", ".X.X.X..", ".X.X.X..", "........", "........"],
                "a": ["........", "..XXXX..", ".....XX.", "..XXXXX.", ".XX..XX.", "..XXXXX.", "........", "........"],
            }
            # Fallback for chars
            cols = []
            for ch in text.lower():
                pattern = glyphs.get(ch)
                if pattern:
                    for c in range(8):
                        cols.append([1 if pattern[r][c] == "X" else 0 for r in range(8)])
                else:
                    for _ in range(5):
                        cols.append([1, 0, 1, 0, 1, 0, 1, 0])
                cols.append([0] * 8) # spacing
            cols += [[0] * 8] * 8 # trailing blank

            offset = 0
            while not cancel.is_set():
                with self.matrix_lock:
                    for col_idx in range(8):
                        src_idx = (offset + col_idx) % len(cols) if loop else min(offset + col_idx, len(cols) - 1)
                        col_data = cols[src_idx]
                        for row_idx in range(8):
                            self.matrix[row_idx][col_idx] = (r, g, b) if col_data[row_idx] else (0, 0, 0)
                offset += 1
                if not loop and offset >= len(cols):
                    break
                time.sleep(1.0 / max(1, fps))

        threading.Thread(target=scroll_worker, daemon=True).start()

    def trigger_shake(self, duration=0.4):
        self.shaking_until = time.monotonic() + duration

    def __enter__(self):
        self.wake()
        return self

    def __exit__(self, *args):
        self.is_connected = False
        self.speed = 0.0
        self.target_speed = 0.0
        self.spin_rate = 0.0
        self.clear_matrix()


class SimulatedSpheroEduAPI:
    """Drop-in simulation for SpheroEduAPI."""

    def __init__(self, toy: SimulatedToy):
        self.__toy = toy
        self.toy = toy
        toy._api = self
        self._heading = 0.0
        self._speed = 0.0

    def __enter__(self):
        self.toy.__enter__()
        return self

    def __exit__(self, *args):
        self.toy.__exit__(*args)

    def set_front_led(self, color: Color):
        self.toy.front_led = color

    def set_back_led(self, color: Color):
        self.toy.back_led = color

    def set_main_led(self, color: Color):
        self.toy.main_led = color

    def clear_matrix(self):
        self.toy.clear_matrix()

    def set_matrix_character(self, char: str, color: Color):
        # Render single character/number (1-9, X, O, H, ?, etc.)
        from tictactoe import GLYPHS
        rows = GLYPHS.get(str(char))
        if rows:
            with self.toy.matrix_lock:
                for y in range(8):
                    for x in range(8):
                        self.toy.matrix[y][x] = (color.r, color.g, color.b) if rows[y][x] == "X" else (0, 0, 0)
        else:
            self.toy.fill(0, 0, 7, 7, color.r, color.g, color.b)

    def set_speed(self, speed: float):
        self._speed = float(speed)
        self.toy.target_speed = float(speed)
        self.toy.speed = float(speed)

    def get_speed(self):
        return self._speed

    def set_heading(self, heading: float):
        self._heading = float(heading) % 360
        self.toy.heading = float(heading) % 360

    def get_heading(self):
        return self._heading

    def roll(self, heading: float, speed: float, duration: float):
        self.set_heading(heading)
        self.set_speed(speed)
        time.sleep(duration)
        self.set_speed(0)

    def stop_roll(self, heading: float = None):
        if heading is not None:
            self.set_heading(heading)
        self.set_speed(0)

    def spin(self, angle: float, duration: float):
        if duration <= 0:
            self.set_heading(self._heading + angle)
            return
        rate = angle / duration
        self.toy.spin_rate = rate
        time.sleep(duration)
        self.toy.spin_rate = 0.0
        self.set_heading(self._heading + angle)

    def raw_motor(self, left: float, right: float, duration: float = None):
        if left != 0 and right == -left:
            # In-place spin: power ~220 gives ~360 deg/s
            self.toy.spin_rate = (left / 220.0) * 360.0
        elif left == 0 and right == 0:
            self.toy.spin_rate = 0.0
            self.toy.speed = 0.0
        if duration is not None:
            time.sleep(duration)
            self.toy.spin_rate = 0.0
            self.toy.speed = 0.0

    def set_stabilization(self, stabilization: bool):
        self.toy.stabilization = bool(stabilization)

    def reset_aim(self):
        self.set_heading(0)
        self.toy.heading = 0.0

    def get_location(self):
        return {"x": round(self.toy.locator_x, 1), "y": round(self.toy.locator_y, 1)}

    def get_acceleration(self):
        now = time.monotonic()
        if now < self.toy.shaking_until:
            # Generate shake peaks > 2.5g alternating
            self.toy.shake_counter += 1
            sign = 1 if (self.toy.shake_counter % 2 == 0) else -1
            return {"x": sign * 2.8, "y": 0.5, "z": 1.2}
        # Stationary 1g earth gravity downwards
        return {"x": 0.0, "y": 0.0, "z": 1.0}


class SimulatorManager:
    """Coordinates physics simulation, state broadcast, and toy registry."""

    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.toys = {}
        for idx, (name, addr, hx, hy, col) in enumerate(DEFAULT_ROBOT_SPECS, start=1):
            toy = SimulatedToy(name, addr, hx, hy, col)
            self.toys[name] = toy
            self.toys[f"BOLT-{idx}"] = toy
        self.active_toys = set()
        self.lock = threading.Lock()
        self.running = True

        prog = os.environ.get("SPHERO_PROGRAM", "")
        if not prog and sys.argv:
            for arg in sys.argv:
                base = Path(arg).stem.lower()
                if base in ("tictactoe", "neu", "dance", "big_dance", "roam", "drive_keys"):
                    prog = base
                    break
                if arg.lower() in ("simon", "mole", "potato", "rps", "lightshow"):
                    prog = arg.lower()
                    break
        if prog:
            self.apply_layout(prog)

        self.physics_thread = threading.Thread(target=self._physics_loop, daemon=True)
        self.physics_thread.start()

    def apply_layout(self, prog_name):
        prog = (prog_name or "").lower()
        if "tictactoe" in prog or "ttt" in prog:
            # 3x3 grid: 1..3 top, 4..6 middle, 7..9 bottom
            coords = [
                (-25.0, 50.0), (0.0, 50.0), (25.0, 50.0),
                (-25.0, 25.0), (0.0, 25.0), (25.0, 25.0),
                (-25.0, 0.0),  (0.0, 0.0),  (25.0, 0.0),
            ]
        elif "neu" in prog:
            # 7 robots in a row left to right (N-E-U-M-A-N-N)
            coords = [(-60.0 + i * 20.0, 25.0) for i in range(7)]
        elif "dance" in prog:
            # 15 robots in a line
            coords = [(-70.0 + i * 10.0, 15.0) for i in range(15)]
        elif "roam" in prog:
            # 15 robots distributed across arena
            coords = [(-50.0 + (i % 5) * 25.0, 10.0 + (i // 5) * 35.0) for i in range(15)]
        elif "simon" in prog or "mole" in prog:
            coords = [(-20.0, 40.0), (20.0, 40.0), (-20.0, 10.0), (20.0, 10.0)]
        elif "rps" in prog:
            coords = [(-20.0, 25.0), (20.0, 25.0)]
        elif "potato" in prog:
            coords = [(0.0, 25.0)]
        elif "drive" in prog:
            coords = [(-25.0, 30.0), (0.0, 30.0), (25.0, 30.0)]
        else:
            coords = [(spec[2], spec[3]) for spec in DEFAULT_ROBOT_SPECS]

        with self.lock:
            canonical_names = [spec[0] for spec in DEFAULT_ROBOT_SPECS]
            for idx, (hx, hy) in enumerate(coords):
                if idx < len(canonical_names):
                    cname = canonical_names[idx]
                    if cname in self.toys:
                        toy = self.toys[cname]
                        toy.home_x, toy.home_y = hx, hy
                        toy.x, toy.y = hx, hy
                        toy.locator_origin_x, toy.locator_origin_y = hx, hy
                        toy.heading = 0.0
                        toy.speed = 0.0
                        toy.target_speed = 0.0

    def get_toy(self, name):
        name_clean = (name or "BOLT-1").strip().upper()
        match = re.search(r"SB-[0-9A-F]+", name_clean)
        if match and match.group(0) in self.toys:
            name_clean = match.group(0)
        elif "(" in name_clean:
            name_clean = name_clean.split("(")[0].strip()

        with self.lock:
            if name_clean in self.toys:
                toy = self.toys[name_clean]
            elif name_clean.startswith("BOLT-") and name_clean[5:].isdigit():
                idx = int(name_clean[5:]) - 1
                if 0 <= idx < len(DEFAULT_ROBOT_SPECS):
                    cname = DEFAULT_ROBOT_SPECS[idx][0]
                    toy = self.toys[cname]
                    self.toys[name_clean] = toy
                else:
                    toy = SimulatedToy(name_clean, f"D4:22:CD:00:{abs(hash(name_clean)) % 0xFFFF:04X}")
                    self.toys[name_clean] = toy
            else:
                toy = SimulatedToy(name_clean, f"D4:22:CD:00:{abs(hash(name_clean)) % 0xFFFF:04X}")
                self.toys[name_clean] = toy

            # Always track by canonical toy name (SB-xxxx)
            self.active_toys.add(toy.name)
            if toy._api is None:
                SimulatedSpheroEduAPI(toy)
            return toy

    def scan_toys(self, count=15):
        res = []
        with self.lock:
            canonical_names = [spec[0] for spec in DEFAULT_ROBOT_SPECS]
            for name in canonical_names[:count]:
                if name in self.toys:
                    toy = self.toys[name]
                    res.append((name, toy.address, -50 - (len(res) * 3)))
        return res

    def _physics_loop(self):
        dt = 0.04  # 25 Hz
        last_emit = 0.0

        while self.running:
            t0 = time.monotonic()
            with self.lock:
                for name in list(self.active_toys):
                    toy = self.toys.get(name)
                    if not toy:
                        continue
                    # Update spin
                    if toy.spin_rate != 0:
                        toy.heading = (toy.heading + toy.spin_rate * dt) % 360

                    # Update position if rolling
                    if toy.speed > 0:
                        # 40 speed ~ 25 cm/s => speed * 0.625 cm/s
                        speed_cm_s = toy.speed * 0.625
                        dist = speed_cm_s * dt
                        rad = math.radians(toy.heading)
                        # heading 0 = North (+y), 90 = East (+x)
                        toy.x += dist * math.sin(rad)
                        toy.y += dist * math.cos(rad)

            # Telemetry broadcast every ~50ms
            now = time.monotonic()
            if now - last_emit >= 0.05 and self.active_toys:
                self._emit_telemetry()
                last_emit = now

            elapsed = time.monotonic() - t0
            sleep_time = max(0.005, dt - elapsed)
            time.sleep(sleep_time)

    def _emit_telemetry(self):
        telemetry = {"robots": []}
        with self.lock:
            order_map = {spec[0]: i for i, spec in enumerate(DEFAULT_ROBOT_SPECS)}
            sorted_names = sorted(self.active_toys, key=lambda n: order_map.get(n, 999))
            for name in sorted_names:
                toy = self.toys.get(name)
                if not toy:
                    continue
                with toy.matrix_lock:
                    mat_hex = [
                        [hex_color(r, g, b) for (r, g, b) in row]
                        for row in toy.matrix
                    ]
                telemetry["robots"].append({
                    "name": toy.name,
                    "x": round(toy.x, 1),
                    "y": round(toy.y, 1),
                    "heading": round(toy.heading, 1),
                    "speed": round(toy.speed, 1),
                    "front_led": hex_color(toy.front_led.r, toy.front_led.g, toy.front_led.b),
                    "back_led": hex_color(toy.back_led.r, toy.back_led.g, toy.back_led.b),
                    "matrix": mat_hex,
                })

        try:
            if not any("server" in arg.lower() for arg in sys.argv):
                line = "TELEMETRY " + json.dumps(telemetry)
                print(line, flush=True)
        except Exception:
            pass


# Monkey-patch spherov2 to seamlessly delegate to simulation
_patched = False

def enable_simulation():
    global _patched
    if _patched:
        return
    _patched = True

    # Patch IO fill
    orig_fill = IO.draw_compressed_frame_player_fill
    def sim_fill(toy, x1, y1, x2, y2, r, g, b, proc=None):
        if hasattr(toy, "fill"):
            toy.fill(x1, y1, x2, y2, r, g, b)
        else:
            orig_fill(toy, x1, y1, x2, y2, r, g, b, proc=proc)
    IO.draw_compressed_frame_player_fill = staticmethod(sim_fill)

    # Patch IO pixel
    orig_pixel = IO.set_compressed_frame_player_pixel
    def sim_pixel(toy, x, y, r, g, b, proc=None):
        if hasattr(toy, "pixel"):
            toy.pixel(x, y, r, g, b)
        else:
            orig_pixel(toy, x, y, r, g, b, proc=proc)
    IO.set_compressed_frame_player_pixel = staticmethod(sim_pixel)

    # Patch SpheroEduAPI
    orig_new = SpheroEduAPI.__new__
    def sim_new(cls, toy, *args, **kwargs):
        if isinstance(toy, SimulatedToy):
            if toy._api is None:
                SimulatedSpheroEduAPI(toy)
            return toy._api
        return orig_new(cls)
    SpheroEduAPI.__new__ = staticmethod(sim_new)

    os.environ["SPHERO_SIM"] = "1"
