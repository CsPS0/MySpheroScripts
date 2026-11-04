"""
Sphero BOLT dance for 3 robots on 1 laptop (spherov2)

Setup on the floor (seen from behind, you stand here):

    [1] SB-3FF5      [2] SB-034E      [3] SB-61A9
     <------ 80 cm ------><------ 80 cm ------>

                         YOU

Program flow:
1. Connects to all 3 robots, one after another.
2. Aim phase: each matrix shows its number, the blue tail light turns on.
   Turn every robot by hand so its blue tail light points at you.
3. The dance starts for all 3 robots at the same moment:
   countdown, wave, circles around, shuffle, one solo per robot, finale.

Stop any time with Ctrl+C.
"""

import colorsys
import contextlib
import shutil
import subprocess
import threading
import time

import bleak
from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color

CONNECT_TIMEOUT = 25     # seconds per connection attempt (spherov2 uses 5)
CONNECT_ATTEMPTS = 3


# spherov2 connects with a fixed 5 s timeout. With many robots nearby,
# BlueZ needs longer to read the robot's services, so the connection
# times out. This raises the timeout for every connection.
_BleakClient = bleak.BleakClient


class _PatientBleakClient(_BleakClient):
    def __init__(self, address, **kwargs):
        kwargs["timeout"] = CONNECT_TIMEOUT
        super().__init__(address, **kwargs)


bleak.BleakClient = _PatientBleakClient

# Robots, left to right. Name, own color.
ROBOTS = [
    ("SB-3FF5", Color(255, 0, 0)),     # 1: red
    ("SB-034E", Color(0, 255, 0)),     # 2: green
    ("SB-61A9", Color(0, 80, 255)),    # 3: blue
]

SCAN_TIMEOUT = 15        # seconds, longer scan helps in a room with many robots
AIM_TIME = 10            # seconds to turn the robots by hand before the dance
COUNT_COLOR = Color(255, 80, 0)
SOLO_COLOR = Color(255, 255, 0)
FINAL_TEXT = "neumann"
SCROLL_FPS = 10

CIRCLE_SPEED = 35        # speed while circling, higher = bigger circle
SHUFFLE_SPEED = 60
SPIN_POWER = 220         # raw motor power for the finale spin, max 255


class StopDance(Exception):
    pass


class Dancer:
    """One robot. All timing is relative to the shared start time t0."""

    def __init__(self, api, toy, index, color, t0, stop):
        self.api = api
        self.toy = toy
        self.index = index            # 0, 1, 2
        self.number = str(index + 1)  # "1", "2", "3"
        self.color = color
        self.t0 = t0
        self.stop = stop

    def at(self, t):
        """Waits until t seconds after the shared start."""
        while True:
            if self.stop.is_set():
                raise StopDance
            left = self.t0 + t - time.monotonic()
            if left <= 0:
                return
            time.sleep(min(left, 0.05))

    def show(self, char, color):
        self.api.clear_matrix()
        self.api.set_matrix_character(char, color)

    def scroll(self, text, color):
        self.api.clear_matrix()
        self.toy.set_compressed_frame_player_text_scrolling(
            text, color.r, color.g, color.b, SCROLL_FPS, True
        )

    def face_front(self):
        self.api.set_speed(0)
        self.api.set_heading(0)

    def rainbow(self, seconds, steps_per_second=10):
        steps = int(seconds * steps_per_second)
        for s in range(steps):
            hue = (s / 20 + self.index / 3) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            self.api.set_front_led(Color(int(r * 255), int(g * 255), int(b * 255)))
            time.sleep(1 / steps_per_second)

    def fast_spin(self, seconds, direction=1):
        power = SPIN_POWER * direction
        self.api.raw_motor(power, -power, seconds)   # blocks, then stops
        self.api.set_stabilization(True)


def choreography(d):
    """The dance. Every robot runs this, d.index picks its own part."""
    i = d.index
    mirror = -1 if i == 1 else 1   # the middle robot moves the other way

    # 0-3 s: countdown on every matrix
    for n, t in (("3", 0), ("2", 1), ("1", 2)):
        d.at(t)
        d.show(n, COUNT_COLOR)

    # 3 s: own number and own color
    d.at(3)
    d.show(d.number, d.color)
    d.api.set_front_led(d.color)

    # 3.5-7 s: wave, one spin after the other from left to right
    d.at(3.5 + i * 1.0)
    d.api.spin(360, 0.8)

    # 7-9 s: all spin together, the middle one the other way
    d.at(7)
    d.api.spin(720 * mirror, 1.5)

    # 9.5-15.5 s: dance around, each robot drives a circle
    d.at(9.5)
    d.face_front()
    d.api.set_speed(CIRCLE_SPEED)
    d.api.spin(360 * mirror, 5)
    d.api.stop_roll()

    # 16-22 s: shuffle forward and back, the middle one in opposite phase
    d.at(16)
    d.face_front()
    for step in range(3):
        d.at(16.5 + step * 2)
        first, second = (0, 180) if mirror == 1 else (180, 0)
        d.api.roll(first, SHUFFLE_SPEED, 0.5)
        d.api.roll(second, SHUFFLE_SPEED, 0.5)
    d.at(22)
    d.face_front()

    # 23-35 s: solos, 4 s each. The others sway and wait.
    for soloist in range(3):
        start = 23 + soloist * 4
        d.at(start)
        if soloist == i:
            d.show(d.number, SOLO_COLOR)
            solo(d)
            d.face_front()
            d.show(d.number, d.color)
        else:
            d.api.set_front_led(Color(d.color.r // 6, d.color.g // 6, d.color.b // 6))
            for k, h in enumerate((30, 330, 30, 330, 0)):
                d.at(start + 0.3 + k * 0.7)
                d.api.set_heading(h)
            d.api.set_front_led(d.color)

    # 36-40 s: finale, rainbow and fast spin together
    d.at(36)
    d.face_front()
    d.rainbow(1.5)
    d.at(38)
    d.fast_spin(2.0, mirror)

    # 41 s: bow and show the text
    d.at(41)
    d.face_front()
    d.scroll(FINAL_TEXT, d.color)
    d.api.set_front_led(d.color)
    d.at(47)


def solo(d):
    """Each robot has its own solo move."""
    if d.index == 0:
        # Robot 1: spin burst with flashing light
        for _ in range(3):
            d.api.set_front_led(SOLO_COLOR)
            d.fast_spin(0.4)
            d.api.set_front_led(d.color)
            time.sleep(0.2)
    elif d.index == 1:
        # Robot 2: figure eight
        d.face_front()
        d.api.set_speed(40)
        d.api.spin(360, 1.5)
        d.api.spin(-360, 1.5)
        d.api.stop_roll()
    else:
        # Robot 3: small triangle
        for h in (0, 120, 240):
            d.api.roll(h, 50, 0.6)
            time.sleep(0.2)


def run_dancer(d, errors):
    try:
        choreography(d)
    except StopDance:
        pass
    except Exception as e:           # one robot failed, stop everyone
        errors.append(f"Robot {d.number}: {e!r}")
        d.stop.set()
    finally:
        with contextlib.suppress(Exception):
            d.api.raw_motor(0, 0, None)
            d.api.set_stabilization(True)
            d.api.stop_roll()


def scan_bolts():
    toys = scanner.find_toys(timeout=SCAN_TIMEOUT, toy_types=[scanner.BOLT])
    return {t.name.upper(): t for t in toys}


def forget_device(address):
    # Clears BlueZ's cached data for the robot, a common fix for timeouts
    if shutil.which("bluetoothctl"):
        subprocess.run(["bluetoothctl", "remove", address],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def connect_robot(stack, index, name):
    """Scans for one robot and connects, with retries."""
    label = f"Robot {index + 1} ({name})"
    last_error = None

    for attempt in range(1, CONNECT_ATTEMPTS + 1):
        print(f"{label}: scanning, attempt {attempt}/{CONNECT_ATTEMPTS}...")
        found = scan_bolts()
        toy = found.get(name)
        if toy is None:
            in_range = ", ".join(sorted(found)) or "none"
            print(f"  not found. BOLTs in range: {in_range}")
            last_error = "not found"
            time.sleep(2)
            continue

        print(f"  found {toy.name}, connecting...")
        try:
            api = stack.enter_context(SpheroEduAPI(toy))
            print("  connected.")
            return api, toy
        except Exception as e:
            last_error = repr(e) or type(e).__name__
            print(f"  connection failed: {type(e).__name__}. Clearing cache, retrying.")
            forget_device(toy.address)
            time.sleep(3)

    raise SystemExit(
        f"{label}: could not connect ({last_error}).\n"
        "Check: robot awake (put it on the charger), no tablet or browser "
        "connected to it, and try again closer to the laptop."
    )


def aim(apis):
    """Tail lights on, stabilization off, so you turn the robots by hand."""
    for index, api in enumerate(apis):
        api.set_stabilization(False)
        api.set_back_led(Color(0, 0, 255))
        api.set_matrix_character(str(index + 1), ROBOTS[index][1])

    print(f"Aim: turn each robot so its blue tail light points at you. "
          f"{AIM_TIME} seconds.")
    for left in range(AIM_TIME, 0, -1):
        print(f"  {left}...", end="\r", flush=True)
        time.sleep(1)
    print()

    for api in apis:
        api.reset_aim()
        api.set_stabilization(True)
        api.set_back_led(Color(0, 0, 0))


def main():
    with contextlib.ExitStack() as stack:
        apis, toys = [], []
        for index, (name, _) in enumerate(ROBOTS):
            api, toy = connect_robot(stack, index, name.upper())
            apis.append(api)
            toys.append(toy)
            time.sleep(1)   # give the adapter a moment before the next robot

        aim(apis)

        stop = threading.Event()
        errors = []
        t0 = time.monotonic() + 1.0          # shared start for everyone
        threads = []
        for index, (api, toy) in enumerate(zip(apis, toys)):
            d = Dancer(api, toy, index, ROBOTS[index][1], t0, stop)
            th = threading.Thread(target=run_dancer, args=(d, errors), daemon=True)
            threads.append(th)
            th.start()

        print("Dancing. Press Ctrl+C to stop.")
        try:
            while any(th.is_alive() for th in threads):
                time.sleep(0.2)
        except KeyboardInterrupt:
            stop.set()
            for th in threads:
                th.join(timeout=3)

        for e in errors:
            print("Error:", e)

        for api in apis:
            with contextlib.suppress(Exception):
                api.clear_matrix()
                api.set_front_led(Color(0, 0, 0))

    print("Done.")


if __name__ == "__main__":
    main()
