"""
Sphero BOLT Simulation Engine.

Simulates Sphero BOLT hardware (motors, locator tracking, 8x8 LED matrix,
accelerometer shake detection, front headlight, blue tail light, battery)
so all scripts, choreography, games, and web controls run flawlessly
without physical robots.
"""

import collections
import colorsys
import json
import math
import os
import random
import re
import sys
import threading
import time
from pathlib import Path
from spherov2.commands.io import IO
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color

# Physics and arena boundaries (cm)
# Physical Sphero BOLT dimensions: 73 mm diameter (7.3 cm), 36.5 mm radius (3.65 cm).
ROBOT_DIAMETER = 7.3
ROBOT_RADIUS = 3.65
ARENA_MIN_X = -80.0
ARENA_MAX_X = 98.0
ARENA_MIN_Y = -30.0
ARENA_MAX_Y = 135.0

# Standard simulated robots (names, addresses, initial home coordinates in cm)
# 15 robots distributed across arena with >= 18 cm spacing so they never overlap in standby
DEFAULT_ROBOT_SPECS = [
    ("SB-3FF5", "D4:22:CD:00:3F:F5", 0.0, 0.0, Color(255, 59, 59)),        # 1 Red
    ("SB-034E", "D4:22:CD:00:03:4E", 18.0, 0.0, Color(46, 204, 113)),     # 2 Green
    ("SB-61A9", "D4:22:CD:00:61:A9", 36.0, 0.0, Color(52, 152, 219)),     # 3 Blue
    ("SB-1111", "D4:22:CD:00:11:11", -50.0, 75.0, Color(241, 196, 15)),   # 4 Yellow
    ("SB-2222", "D4:22:CD:00:22:22", -25.0, 75.0, Color(232, 67, 147)),   # 5 Pink
    ("SB-3333", "D4:22:CD:00:33:33", 0.0, 75.0, Color(0, 206, 201)),      # 6 Cyan
    ("SB-4444", "D4:22:CD:00:44:44", 25.0, 75.0, Color(230, 126, 34)),    # 7 Orange
    ("SB-5555", "D4:22:CD:00:55:55", 50.0, 75.0, Color(255, 255, 255)),   # 8 White
    ("SB-6666", "D4:22:CD:00:66:66", -50.0, 105.0, Color(155, 89, 182)),  # 9 Purple
    ("SB-7777", "D4:22:CD:00:77:77", -25.0, 105.0, Color(253, 121, 168)), # 10 Soft Pink
    ("SB-8888", "D4:22:CD:00:88:88", 0.0, 105.0, Color(9, 132, 227)),    # 11 Ocean Blue
    ("SB-9999", "D4:22:CD:00:99:99", 25.0, 105.0, Color(0, 184, 148)),   # 12 Mint Green
    ("SB-AAAA", "D4:22:CD:00:AA:AA", 50.0, 105.0, Color(255, 234, 167)),  # 13 Cream Yellow
    ("SB-BBBB", "D4:22:CD:00:BB:BB", -25.0, 125.0, Color(108, 92, 231)),  # 14 Violet
    ("SB-CCCC", "D4:22:CD:00:CC:CC", 25.0, 125.0, Color(214, 48, 49)),    # 15 Crimson
]

def hex_color(r, g, b):
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


class SimulatedSensorControl:
    def disable(self, *args, **kwargs):
        pass

    def enable(self, *args, **kwargs):
        pass

    def disable_all(self):
        pass

    def enable_all(self):
        pass

    def set_interval(self, *args, **kwargs):
        pass

    def add_sensor_data_listener(self, *args, **kwargs):
        pass


class SimulatedDriveControl:
    def __init__(self, toy):
        self.toy = toy

    def roll_start(self, heading, speed):
        self.toy.heading = float(heading) % 360
        self.toy.speed = float(speed)
        self.toy.target_speed = float(speed)

    def roll_stop(self, heading=None):
        if heading is not None:
            self.toy.heading = float(heading) % 360
        self.toy.speed = 0.0
        self.toy.target_speed = 0.0


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

        # Subsystems and collision listeners
        self.sensor_control = SimulatedSensorControl()
        self.drive_control = SimulatedDriveControl(self)
        self._Toy__listeners = collections.defaultdict(list)
        self._north_listeners = []
        self.collision_detection_enabled = False
        self.last_collision_time = 0.0

        self.is_connected = False
        self._api = None
        self._voltage = round(3.90 + (abs(hash(name)) % 25) * 0.01, 2)

    def add_magnetometer_north_yaw_notify_listener(self, listener):
        self._north_listeners.append(listener)

    def magnetometer_calibrate_to_north(self):
        self.heading = 0.0
        for cb in list(self._north_listeners):
            try:
                cb(0)
            except Exception:
                pass

    def configure_collision_detection(self, *args, **kwargs):
        self.collision_detection_enabled = True

    def _add_listener(self, key_and_wrapper, callback):
        key, wrapper = key_and_wrapper
        self._Toy__listeners[key].append((wrapper, callback))

    def _notify_collision(self):
        now = time.monotonic()
        if now - self.last_collision_time < 0.15:
            return
        self.last_collision_time = now
        for key in list(self._Toy__listeners.keys()):
            for wrapper, callback in list(self._Toy__listeners[key]):
                try:
                    wrapper(callback, None)
                except Exception:
                    try:
                        callback()
                    except Exception:
                        pass

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

    def set_matrix_character(self, char: str, color: Color):
        s = str(char).strip()
        rows = None
        if s.isdigit() and len(s) >= 2:
            try:
                import indicators
                rows = indicators.number_bitmap(int(s))
            except Exception:
                pass
        if rows is None:
            try:
                from tictactoe import GLYPHS
                rows = GLYPHS.get(s)
            except Exception:
                pass
        if rows is None:
            try:
                import indicators
                rows = indicators.LETTERS.get(s.upper()) or indicators.EXTRA_GLYPHS.get(s.upper())
                if rows is None and s.isdigit():
                    rows = indicators.number_bitmap(int(s))
            except Exception:
                pass
        if rows:
            with self.matrix_lock:
                for y in range(8):
                    for x in range(8):
                        self.matrix[y][x] = (color.r, color.g, color.b) if rows[y][x] == "X" else (0, 0, 0)
        else:
            self.fill(0, 0, 7, 7, color.r, color.g, color.b)

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
        self.toy.set_matrix_character(char, color)

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
        self.aliases = {}
        for idx, (name, addr, hx, hy, col) in enumerate(DEFAULT_ROBOT_SPECS, start=1):
            toy = SimulatedToy(name, addr, hx, hy, col)
            self.toys[name] = toy
            self.aliases[f"BOLT-{idx}"] = name
        self.active_toys = set()
        self.lock = threading.RLock()
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
        layout = os.environ.get("SPHERO_LAYOUT", "3x3")
        if prog:
            self.apply_layout(prog, layout=layout)

        self.physics_thread = threading.Thread(target=self._physics_loop, daemon=True)
        self.physics_thread.start()

    def apply_layout(self, prog_name, count=None, layout="3x3"):
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
            # All robots in ONE single horizontal line, left to right by number
            n = count if (count and count > 0) else (len(self.active_toys) if self.active_toys else 9)
            n = max(1, min(15, n))
            spacing = min(15.0, 140.0 / max(1, n - 1))
            start_x = - (n - 1) * spacing / 2.0
            coords = [(start_x + i * spacing, 30.0) for i in range(n)]
        elif "roam" in prog:
            # 15 robots distributed across arena (5 cols x 3 rows)
            coords = [(-50.0 + (i % 5) * 25.0, 15.0 + (i // 5) * 35.0) for i in range(15)]
        elif "simon" in prog or "mole" in prog:
            n = count if (count and count > 0) else (len(self.active_toys) if self.active_toys else 9)
            n = max(1, min(15, n))
            with self.lock:
                self.active_toys.update([spec[0] for spec in DEFAULT_ROBOT_SPECS[:n]])
            if str(layout).lower() == "random":
                coords = []
                for idx in range(n):
                    placed = False
                    for _ in range(120):
                        rx = round(random.uniform(-52.0, 52.0), 1)
                        ry = round(random.uniform(12.0, 72.0), 1)
                        if all(math.hypot(rx - ox, ry - oy) >= 22.0 for ox, oy in coords):
                            coords.append((rx, ry))
                            placed = True
                            break
                    if not placed:
                        coords.append((-45.0 + (idx % 5) * 22.0, 15.0 + (idx // 5) * 25.0))
            else:
                if n <= 4:
                    coords = [(-18.0, 50.0), (18.0, 50.0), (-18.0, 22.0), (18.0, 22.0)]
                else:
                    xs = [-28.0, 0.0, 28.0]
                    ys = [66.0, 40.0, 14.0]
                    coords = [(x, y) for y in ys for x in xs]
                    if n > 9:
                        for extra in range(n - 9):
                            coords.append((-50.0 + extra * 20.0, -5.0))
        elif "rps" in prog:
            coords = [(-20.0, 25.0), (20.0, 25.0)]
        elif "potato" in prog:
            coords = [(0.0, 25.0)]
        elif "drive" in prog:
            coords = [(0.0, 0.0), (18.0, 0.0), (36.0, 0.0)]
        else:
            coords = [(spec[2], spec[3]) for spec in DEFAULT_ROBOT_SPECS]

        with self.lock:
            canonical_names = [spec[0] for spec in DEFAULT_ROBOT_SPECS]
            for idx, cname in enumerate(canonical_names):
                if idx < len(coords):
                    hx, hy = coords[idx]
                else:
                    hx, hy = DEFAULT_ROBOT_SPECS[idx][2], DEFAULT_ROBOT_SPECS[idx][3]
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
            elif name_clean in self.aliases:
                toy = self.toys[self.aliases[name_clean]]
            elif name_clean.startswith("BOLT-") and name_clean[5:].isdigit():
                idx = int(name_clean[5:]) - 1
                if 0 <= idx < len(DEFAULT_ROBOT_SPECS):
                    cname = DEFAULT_ROBOT_SPECS[idx][0]
                    toy = self.toys[cname]
                    self.aliases[name_clean] = cname
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
        dt = 1.0 / 60.0  # 60 FPS physics loop for responsive collision response
        last_emit = 0.0

        min_x = ARENA_MIN_X + ROBOT_RADIUS
        max_x = ARENA_MAX_X - ROBOT_RADIUS
        min_y = ARENA_MIN_Y + ROBOT_RADIUS
        max_y = ARENA_MAX_Y - ROBOT_RADIUS

        while self.running:
            t0 = time.monotonic()
            with self.lock:
                active_list = [self.toys[name] for name in list(self.active_toys) if name in self.toys]

                for toy in active_list:
                    # Update spin
                    if toy.spin_rate != 0:
                        toy.heading = (toy.heading + toy.spin_rate * dt) % 360

                    # Update position if rolling
                    if toy.speed > 0:
                        speed_cm_s = toy.speed * 0.625
                        dist = speed_cm_s * dt
                        rad = math.radians(toy.heading)
                        toy.x += dist * math.sin(rad)
                        toy.y += dist * math.cos(rad)

                    # Arena boundary collision & reflection
                    bounced_x = False
                    bounced_y = False
                    if toy.x <= min_x:
                        toy.x = min_x
                        bounced_x = True
                    elif toy.x >= max_x:
                        toy.x = max_x
                        bounced_x = True

                    if toy.y <= min_y:
                        toy.y = min_y
                        bounced_y = True
                    elif toy.y >= max_y:
                        toy.y = max_y
                        bounced_y = True

                    if (bounced_x or bounced_y) and toy.speed > 3:
                        rad = math.radians(toy.heading)
                        vx = math.sin(rad)
                        vy = math.cos(rad)
                        if bounced_x:
                            vx = -vx
                        if bounced_y:
                            vy = -vy
                        # Add slight jitter to prevent infinite dead-on bouncing
                        jitter = math.radians((random.random() - 0.5) * 20)
                        cos_j, sin_j = math.cos(jitter), math.sin(jitter)
                        new_vx = vx * cos_j - vy * sin_j
                        new_vy = vx * sin_j + vy * cos_j
                        toy.heading = math.degrees(math.atan2(new_vx, new_vy)) % 360
                        toy.trigger_shake(0.3)
                        toy._notify_collision()

                # Robot-robot pairwise collisions (prevent overlapping / hovering)
                min_dist = ROBOT_DIAMETER
                for iter_idx in range(3):
                    for i in range(len(active_list)):
                        toy_a = active_list[i]
                        for j in range(i + 1, len(active_list)):
                            toy_b = active_list[j]

                            dx = toy_b.x - toy_a.x
                            dy = toy_b.y - toy_a.y
                            dist = math.hypot(dx, dy)

                            if dist < min_dist:
                                overlap = min_dist - dist
                                if dist > 0.001:
                                    nx = dx / dist
                                    ny = dy / dist
                                else:
                                    angle = (i * 1.33 + j * 0.77)
                                    nx = math.cos(angle)
                                    ny = math.sin(angle)

                                # Immediately separate so they cannot hover or overlap
                                toy_a.x -= nx * overlap * 0.5
                                toy_a.y -= ny * overlap * 0.5
                                toy_b.x += nx * overlap * 0.5
                                toy_b.y += ny * overlap * 0.5

                                # Keep strictly inside arena bounds after separation
                                toy_a.x = max(min_x, min(max_x, toy_a.x))
                                toy_a.y = max(min_y, min(max_y, toy_a.y))
                                toy_b.x = max(min_x, min(max_x, toy_b.x))
                                toy_b.y = max(min_y, min(max_y, toy_b.y))

                                if iter_idx == 0:
                                    va_x = toy_a.speed * 0.625 * math.sin(math.radians(toy_a.heading))
                                    va_y = toy_a.speed * 0.625 * math.cos(math.radians(toy_a.heading))
                                    vb_x = toy_b.speed * 0.625 * math.sin(math.radians(toy_b.heading))
                                    vb_y = toy_b.speed * 0.625 * math.cos(math.radians(toy_b.heading))

                                    v_rel = (vb_x - va_x) * nx + (vb_y - va_y) * ny
                                    if v_rel < 0:
                                        # Approaching: elastic collision response
                                        restitution = 0.90
                                        impulse = -(1.0 + restitution) * v_rel * 0.5
                                        va_x -= impulse * nx
                                        va_y -= impulse * ny
                                        vb_x += impulse * nx
                                        vb_y += impulse * ny

                                        sp_a = math.hypot(va_x, va_y) / 0.625
                                        sp_b = math.hypot(vb_x, vb_y) / 0.625
                                        if sp_a > 1:
                                            toy_a.heading = math.degrees(math.atan2(va_x, va_y)) % 360
                                            toy_a.speed = sp_a
                                        if sp_b > 1:
                                            toy_b.heading = math.degrees(math.atan2(vb_x, vb_y)) % 360
                                            toy_b.speed = sp_b
                                    else:
                                        if toy_a.speed > 0:
                                            toy_a.heading = (math.degrees(math.atan2(-nx, -ny)) + (random.random() - 0.5) * 30) % 360
                                        if toy_b.speed > 0:
                                            toy_b.heading = (math.degrees(math.atan2(nx, ny)) + (random.random() - 0.5) * 30) % 360

                                    toy_a.trigger_shake(0.3)
                                    toy_b.trigger_shake(0.3)
                                    toy_a._notify_collision()
                                    toy_b._notify_collision()

            # Telemetry broadcast at ~30 Hz for smooth streaming
            now = time.monotonic()
            if now - last_emit >= 0.033 and self.active_toys:
                self._emit_telemetry()
                last_emit = now

            elapsed = time.monotonic() - t0
            sleep_time = max(0.001, dt - elapsed)
            time.sleep(sleep_time)

    def get_telemetry(self):
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
        return telemetry

    def _emit_telemetry(self):
        telemetry = self.get_telemetry()
        try:
            if not any(k in arg.lower() for arg in sys.argv for k in ("server", "test_suite")):
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
