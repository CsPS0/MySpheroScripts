"""
Big dance: every free BOLT of the robot pool (up to 15) dances together.

1. Setup: each robot shows its pool number (1-15) and its blue tail light. Put
   them in a line, left to right by number, tail lights towards you, about
   10 cm apart. Then press Go on the web page (stdin line "start").
2. Rainbow (RAINBOW_TIME): a rainbow wave runs along the line, the robots turn
   in place to random directions.
3. Rush (RUSH_TIME): the robots race around in out-and-back dashes of about
   40 cm, so they stay near their spots. A collision flashes an explosion on the
   matrix; the robot keeps going.
4. Characters (CHARS_TIME): they stop, random characters appear, they wiggle
   and dance a small square.
5. A short rainbow finale, done.

Robots left out: the numbers in data/dance.json "exclude" (set on the web
page), and robots that are busy (connected elsewhere, so not advertising) or
do not connect.

Bluetooth: one adapter holds 10 robots (PER_ADAPTER), a second adapter takes
the rest. Traffic is kept low: no sensor streaming, single "fill" / "character"
/ "roll" commands, and a shared limit of RATE commands per second.

Talks to the web page: prints "STATE {json}" lines; stdin "start" = Go in the
setup, later "start" skips to the next part. Ends after the finale or on Ctrl+C.
"""

import colorsys
import contextlib
import json
import random
import sys
import threading
import time
from pathlib import Path

from spherov2.commands.sensor import CollisionDetectionMethods
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color

import indicators
import sphero_ble

CONFIG = Path(__file__).resolve().parent / "data" / "dance.json"
MAX_ROBOTS = 15
PER_ADAPTER = 10         # one Bluetooth adapter holds 10 robots (the 11th times out, tested)
MAX_TIMEOUTS = 2         # connection timeouts in a row before an adapter counts as full
SCAN_TIME = 6            # s, which robots are free (advertising)

RAINBOW_TIME = 120       # s
RUSH_TIME = 60
CHARS_TIME = 45

_scale = float(__import__("os").environ.get("DANCE_SCALE", "1"))   # testing: 0.05 = 20x shorter
RAINBOW_TIME, RUSH_TIME, CHARS_TIME = (t * _scale for t in (RAINBOW_TIME, RUSH_TIME, CHARS_TIME))

RUSH_SPEED = (45, 75)    # out-and-back dashes: about 40 cm out, so the area stays about 1 m
DASH_TIME = (0.7, 1.0)   # s per dash direction
WAVE_SPEED = 0.05        # rainbow turns per second
COLOR_EVERY = 2.5        # s between color changes of one robot
BOOM_COOLDOWN = 3.0      # s between two explosions of one robot

# Bluetooth budget. The first hardware run (10 robots on one Intel 8087:0a2b
# adapter, about 15 commands/s plus locator streaming) stalled after 35 s: every
# command of every robot timed out at once. So: no sensor streaming at all, and
# all robots together send at most RATE commands per second; after a timeout
# everyone pauses PAUSE_AFTER_TIMEOUT seconds so the adapter can catch up.
RATE = 8
PAUSE_AFTER_TIMEOUT = 3.0
MAX_FAILURES = 8         # failures in a row (with the link still up) before a robot sits out
CHARS = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789!?+#"
OFF = Color(0, 0, 0)


class RateLimit:
    """Shared by all robots: spaces commands out to RATE per second."""

    def __init__(self, rate):
        self.gap = 1.0 / rate
        self.lock = threading.Lock()
        self.next_slot = 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            slot = max(now, self.next_slot)
            self.next_slot = slot + self.gap
        if slot > now:
            time.sleep(slot - now)

    def pause(self, seconds):
        with self.lock:
            self.next_slot = max(self.next_slot, time.monotonic() + seconds)


LIMIT = RateLimit(RATE)

_draw_slots = threading.BoundedSemaphore(3)     # bitmap drawing, the heaviest traffic
_print_lock = threading.Lock()


def say(text):
    with _print_lock:
        print(text, flush=True)


def load_config():
    try:
        cfg = json.loads(CONFIG.read_text())
        return {"exclude": sorted({int(n) for n in cfg.get("exclude", [])})}
    except (OSError, ValueError, TypeError):
        return {"exclude": []}


def hue_color(hue, value=1.0):
    r, g, b = colorsys.hsv_to_rgb(hue % 1.0, 1.0, value)
    return Color(int(r * 255), int(g * 255), int(b * 255))


class Bot:
    """One robot. Commands that keep failing mark it lost, then it sits out."""

    def __init__(self, number, name, toy, api):
        self.number, self.name, self.toy, self.api = number, name, toy, api
        self.rank = 0                   # position in the line, 0 = left
        self.lost = False
        self.failures = 0
        self.collided = threading.Event()
        self.last_boom = 0.0
        self.heading, self.speed = 0, 0

    def connected(self):
        adapter = getattr(self.toy, "_Toy__adapter", None)
        client = getattr(adapter, "_client", None)
        return client is None or client.is_connected      # simulated robots: always

    def do(self, command):
        if self.lost:
            return False
        LIMIT.wait()
        try:
            command()
            self.failures = 0
            return True
        except Exception as e:
            self.failures += 1
            if isinstance(e, TimeoutError):
                LIMIT.pause(PAUSE_AFTER_TIMEOUT)            # let the adapter catch up
            if not self.connected() or self.failures >= MAX_FAILURES:
                self.lost = True
                why = "disconnected" if not self.connected() else f"{self.failures} failures"
                say(f"  robot {self.number} ({self.name}): lost ({why}), it sits out.")
            return False

    # --- effects --------------------------------------------------------
    def fill(self, color):
        return self.do(lambda: indicators.fill_all(self.toy, color))

    def char(self, ch, color):
        if hasattr(self.toy, "set_compressed_frame_player_single_character"):
            # sent directly: spherov2's SpheroEduAPI.set_matrix_character does nothing on a BOLT
            return self.do(lambda: self.toy.set_compressed_frame_player_single_character(
                color.r, color.g, color.b, ch))
        return self.do(lambda: self.api.set_matrix_character(ch, color))

    def show_number(self):
        def draw():
            with _draw_slots:
                indicators.show_bitmap(self.api, self.toy, indicators.number_bitmap(self.number),
                                       Color(255, 255, 255), **indicators.UPRIGHT)
        return self.do(draw)

    def boom(self):
        self.fill(Color(255, 230, 0))          # flash ...
        time.sleep(0.1)
        self.fill(Color(255, 30, 0))           # ... fire

    # --- motion ---------------------------------------------------------
    def drive(self, heading, speed):
        """One roll command for heading and speed together."""
        heading, speed = round(heading) % 360, round(speed)
        if (heading, speed) == (self.heading, self.speed):
            return True
        self.heading, self.speed = heading, speed
        if hasattr(self.toy, "drive_control"):
            return self.do(lambda: self.toy.drive_control.roll_start(heading, speed))
        return self.do(lambda: (self.api.set_heading(heading), self.api.set_speed(speed)))

    def halt(self, heading=None):
        if heading is not None:
            self.heading = round(heading) % 360
        self.speed = 0
        return self.do(lambda: self.api.stop_roll(self.heading))

    def on_collision(self, *_):
        self.collided.set()


COLLISION_KEY = (24, 18, 0xFF)    # sensor device, "collision detected" notification


def listen_for_collisions(toy, callback):
    """Calls callback() on every collision message of this robot.

    spherov2 0.12.1 decodes the BOLT's collision message with the wrong layout
    (struct.error "unpack requires a buffer of 18 bytes"), so its own listener
    (registered by SpheroEduAPI) crashes and nothing is reported. This replaces
    it with one that only needs to know that the message arrived."""
    listeners = toy._Toy__listeners[COLLISION_KEY]
    listeners.clear()
    toy._add_listener((COLLISION_KEY, lambda listener, packet: listener()), callback)


# --- parts of the dance (one thread per robot) ---------------------------

def rainbow(bot, done, count):
    start = time.monotonic()
    done.wait(bot.rank * COLOR_EVERY / max(1, count))      # spread the commands out
    next_turn = time.monotonic() + random.uniform(2, 6)
    while not done.is_set() and not bot.lost:
        t = time.monotonic() - start
        bot.fill(hue_color(t * WAVE_SPEED - bot.rank / max(1, count)))   # wave runs left to right
        if time.monotonic() >= next_turn:
            bot.halt(random.randint(0, 359))                             # turn in place
            next_turn = time.monotonic() + random.uniform(5, 9)
        done.wait(COLOR_EVERY)
    bot.halt()


def rush(bot, done, count):
    """Out-and-back dashes in random directions: each robot returns near its
    start spot without needing position data (no sensor streaming)."""
    color = hue_color(bot.rank / max(1, count))
    bot.fill(color)
    bot.collided.clear()
    done.wait(random.uniform(0, 1.5))
    while not done.is_set() and not bot.lost:
        heading, speed = random.randint(0, 359), random.randint(*RUSH_SPEED)
        dash = random.uniform(*DASH_TIME)
        for direction in (heading, heading + 180):             # out, then back
            bot.drive(direction, speed)
            end = time.monotonic() + dash
            while time.monotonic() < end and not done.is_set():
                if bot.collided.is_set():
                    bot.collided.clear()
                    now = time.monotonic()
                    if now - bot.last_boom > BOOM_COOLDOWN:
                        bot.last_boom = now
                        say(f"  robot {bot.number}: collision!")
                        bot.boom()
                        bot.fill(color)
                done.wait(0.1)
        bot.halt()
        done.wait(random.uniform(0.3, 0.8))
    bot.halt()


def characters(bot, done, count):
    bot.halt()
    done.wait(random.uniform(0, 1.5))
    while not done.is_set() and not bot.lost:
        bot.char(random.choice(CHARS), hue_color(random.random()))
        base = random.randint(0, 359)
        for turn in (45, -45, 45, -45):                  # wiggle in place
            bot.halt(base + turn)
            if done.wait(0.4):
                break
        for k in range(4):                               # small square dance, back to the spot
            bot.drive(base + k * 90, 40)
            if done.wait(0.45):
                break
        bot.halt()
        done.wait(random.uniform(0.6, 1.2))
    bot.halt()


# --- program ---------------------------------------------------------------

def on_bots(bots, action, timeout=15):
    threads = [threading.Thread(target=action, args=(b,), daemon=True) for b in bots if not b.lost]
    for th in threads:
        th.start()
    deadline = time.monotonic() + timeout
    for th in threads:
        th.join(timeout=max(0.0, deadline - time.monotonic()))


def main():
    cfg = load_config()
    excluded = set(cfg["exclude"])
    cache = sphero_ble.load_cached_bolts()
    pool = {}                                            # number -> Bluetooth name
    for key, addr in cache.items():
        if key.startswith("BOLT-") and key[5:].isdigit():
            bt = next((k for k, v in cache.items() if v == addr and k.startswith("SB-")), None)
            if bt:
                pool[int(key[5:])] = bt
    if not pool:
        raise SystemExit("No robot pool: start the web server and let it scan first.")

    say(f"Looking {SCAN_TIME} s for free robots...")
    free = {name for name, _, _ in sphero_ble.scan_bolts(SCAN_TIME)}
    plan, busy = [], []
    for number in sorted(pool):
        if number in excluded:
            continue
        (plan if pool[number] in free else busy).append(number)
    plan = plan[:MAX_ROBOTS]
    if excluded:
        say(f"Left out on the web page: {', '.join(map(str, sorted(excluded)))}")
    if busy:
        say(f"Busy or switched off (skipped): {', '.join(map(str, busy))}")

    stop = threading.Event()
    go = threading.Event()
    next_part = threading.Event()

    def read_stdin():
        for line in sys.stdin:
            if line.strip() == "start":
                (next_part if go.is_set() else go).set()
        stop.set()
    threading.Thread(target=read_stdin, daemon=True).start()

    bots, stacks = [], []
    state = {"phase": "connecting", "left": None}

    def emit():
        say("STATE " + json.dumps({
            "kind": "dance", "phase": state["phase"], "left": state["left"],
            "robots": [b.number for b in bots if not b.lost],
            "lost": [b.number for b in bots if b.lost],
            "skipped": busy, "excluded": sorted(excluded)}))

    try:
        emit()
        adapters = sphero_ble.list_adapters() or [None]
        load = {a: 0 for a in adapters}
        timeouts = {a: 0 for a in adapters}
        full = set()
        for number in plan:
            adapter = next((a for a in adapters if a not in full and load[a] < PER_ADAPTER), None)
            if adapter is None:
                rest = plan[plan.index(number):]
                say(f"The Bluetooth adapter{'s are' if len(adapters) > 1 else ' is'} full "
                    f"({sum(load.values())} robots). Left out: {', '.join(map(str, rest))}. "
                    "Plug in another USB Bluetooth adapter for more robots.")
                busy.extend(rest)
                break
            name = pool[number]
            say(f"Robot {number}: connecting {name}...")
            own = contextlib.ExitStack()
            try:
                toy, api = sphero_ble.connect_toy(
                    name, lambda t: own.enter_context(SpheroEduAPI(t)), attempts=1,
                    adapter=adapter if len(adapters) > 1 else None)
                load[adapter] += 1
                timeouts[adapter] = 0
            except ConnectionError as e:
                say(f"  {e}: skipped")
                if isinstance(e.__cause__, TimeoutError):
                    timeouts[adapter] += 1
                    if timeouts[adapter] >= MAX_TIMEOUTS:
                        full.add(adapter)
                continue
            stacks.append(own)
            bot = Bot(number, name, toy, api)
            bots.append(bot)
        if not bots:
            raise SystemExit("No robot connected.")
        say(f"{len(bots)} robots connected: {', '.join(str(b.number) for b in bots)}")

        def setup(bot):
            bot.do(lambda: bot.api.set_stabilization(True))
            if hasattr(bot.toy, "sensor_control"):
                bot.do(lambda: bot.toy.sensor_control.disable_all())    # no streaming: Bluetooth budget
            if hasattr(bot.toy, "configure_collision_detection"):
                # sent directly: spherov2's own setup skips the BOLT (capability check)
                bot.do(lambda: bot.toy.configure_collision_detection(
                    CollisionDetectionMethods.ACCELEROMETER_BASED_DETECTION, 90, 130, 90, 130, 100))
                listen_for_collisions(bot.toy, bot.on_collision)
            bot.do(lambda: bot.api.set_back_led(Color(0, 0, 255)))
            bot.do(lambda: bot.api.set_front_led(Color(255, 255, 255)))
            bot.show_number()
        on_bots(bots, setup, timeout=40)

        for rank, bot in enumerate(sorted(bots, key=lambda b: b.number)):
            bot.rank = rank
        state["phase"] = "setup"
        emit()
        say("Put the robots in a line, left to right by the number they show, blue tail "
            "lights towards you, about 10 cm apart. Then press Go on the web page.")
        while not go.wait(1):
            if stop.is_set():
                return

        on_bots(bots, lambda bot: bot.do(lambda: bot.api.set_back_led(OFF)))

        for phase, seconds, part, text in (
                ("rainbow", RAINBOW_TIME, rainbow, "Rainbow wave"),
                ("rush", RUSH_TIME, rush, "Rush"),
                ("chars", CHARS_TIME, characters, "Characters")):
            say(f"=== {text} ===")
            state["phase"] = phase
            done = threading.Event()
            next_part.clear()
            count = len(bots)
            threads = [threading.Thread(target=part, args=(b, done, count), daemon=True)
                       for b in bots if not b.lost]
            for th in threads:
                th.start()
            end = time.monotonic() + seconds
            while time.monotonic() < end and not stop.is_set() and not next_part.is_set():
                state["left"] = round(end - time.monotonic())
                emit()
                next_part.wait(min(5.0, max(0.1, end - time.monotonic())))
            done.set()
            for th in threads:
                th.join(timeout=5)
            if stop.is_set():
                return

        say("=== Finale ===")
        state["phase"], state["left"] = "finale", None
        emit()
        for step in range(4):
            color = hue_color(step / 4)
            on_bots(bots, lambda b, c=color: b.fill(c), timeout=3)
            time.sleep(0.3)
        state["phase"] = "done"
        emit()
        say("Dance complete!")
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()

        def reset(bot):
            with contextlib.suppress(Exception):
                bot.api.stop_roll()
            with contextlib.suppress(Exception):
                indicators.fill_all(bot.toy, OFF)
            with contextlib.suppress(Exception):
                bot.api.set_back_led(OFF)
                bot.api.set_front_led(OFF)
        on_bots(bots, reset, timeout=8)
        threads = [threading.Thread(target=st.close, daemon=True) for st in stacks]
        for th in threads:
            th.start()
        for th in threads:
            th.join(timeout=10)
    say("Done.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        say("Stopped.")
