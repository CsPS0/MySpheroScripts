"""
NEUMANN: one letter per robot. Robots 1-7 show N, E, U, M, A, N, N.

Setup: robots 1 to 7 of the web page's robot pool get the letters; if one does
not connect, the next spare robot (8, 9, ...) takes its letter. Put them in a
line by the letter they show, left to right, about 10 cm apart.

Alignment (data/letters.json "align", switch on the web page):
  compass  every robot calibrates its compass (it spins in place for a few
           seconds) and turns to magnetic north + the heading. All robots face
           the same way, however they were put down. No aim phase.
  aim      the usual aim phase (blue tail lights towards you), heading 0 is
           away from you.
Each letter can be turned on the matrix in 90 degree steps (rotation), and each
robot can be turned by itself in 15 degree steps (turn) to straighten it.
Hand mode ("hand", the lock on the web page): stabilization off and no
automatic turning, so the robots can be turned by hand. When it is switched
off they keep the directions they were given.
Changes on the web page are applied while this program runs.

Holds until Ctrl+C (Stop on the web page).
"""

import contextlib
import queue
import threading
import time

from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color

import bolt_dance
import indicators
import letters
import sphero_ble

LETTER_COLOR = Color(0, 140, 255)   # same color on every robot, so the word reads as one
COMPASS_TIMEOUT = 15                # s, all robots calibrate at the same time (about 4 s each)
DRAW_AT_ONCE = 3                    # robots drawing at the same time (Bluetooth load)

_draw_slots = threading.BoundedSemaphore(DRAW_AT_ONCE)
LOST = set()            # robot indexes whose connection dropped: skipped, so they cannot stall the rest


def on_robots(apis, action, timeout=10):
    """Runs action(index) for every connected robot at the same time. A robot
    whose command fails is marked lost (and logged once)."""
    def run(index):
        try:
            action(index)
        except Exception as e:
            if index not in LOST:
                LOST.add(index)
                print(f"  robot {index + 1}: lost its connection ({type(e).__name__}), skipped "
                      "from now on. Restart the show to reconnect it.", flush=True)
    threads = [threading.Thread(target=run, args=(i,), daemon=True)
               for i in range(len(apis)) if i not in LOST]
    for th in threads:
        th.start()
    deadline = time.monotonic() + timeout
    for th in threads:
        th.join(timeout=max(0.0, deadline - time.monotonic()))


def show(api, toy, item):
    with _draw_slots:
        indicators.show_letter(api, toy, item["letter"], LETTER_COLOR, item["rotation"], item["mirror"])


def calibrate_compasses(toys, names):
    """Calibrates all compasses at the same time (each robot spins briefly).
    Returns, per robot, the robot heading that points to magnetic north, or None
    if the compass did not answer.

    The command is sent directly: spherov2 0.12.1's SpheroEduAPI.calibrate_compass()
    never sends it for the BOLT (its capability check fails) and then waits forever."""
    print("Compass: the robots spin in place to find north...", flush=True)
    north = [None] * len(toys)
    done = threading.Event()
    real = [i for i, toy in enumerate(toys) if hasattr(toy, "magnetometer_calibrate_to_north")]

    def listener(index):
        def on_north(yaw):
            north[index] = int(yaw) % 360
            if all(north[i] is not None for i in real):
                done.set()
        return on_north

    for index in real:                                    # simulated robots have no compass
        toy = toys[index]
        toy.add_magnetometer_north_yaw_notify_listener(listener(index))
        with contextlib.suppress(Exception):
            toy.magnetometer_calibrate_to_north()
    if real:
        done.wait(COMPASS_TIMEOUT)

    for index, name in enumerate(names):
        if north[index] is None:
            print(f"  {name}: compass did not answer, using its aim direction instead "
                  "(straighten it with the turn buttons)", flush=True)
    found = sum(n is not None for n in north)
    print(f"Compass: north found on {found} of {len(toys)} robots.", flush=True)
    return north


def compass_base(cfg, north, count):
    """Per robot: the robot heading that counts as direction 0."""
    if cfg["align"] == "compass" and north:
        return [n if n is not None else 0 for n in north]
    return [0] * count


def robot_heading(cfg, base, index):
    return round(base[index] + cfg["heading"] + cfg["letters"][index]["turn"]) % 360


def set_hand_mode(apis, on):
    """on: stabilization off, so each robot can be turned by hand and stays
    there; the blue tail light shows its back."""
    def one(index):
        apis[index].set_stabilization(not on)
        apis[index].set_back_led(Color(0, 0, 255) if on else Color(0, 0, 0))
    on_robots(apis, one)


def keep_hand_directions(apis, cfg):
    """Leaving hand mode: every robot keeps the direction it was turned to.
    Its current direction becomes the new zero, and the base is chosen so the
    current heading + turn settings point exactly there."""
    on_robots(apis, lambda index: apis[index].reset_aim())
    return [(-(cfg["heading"] + item["turn"])) % 360 for item in cfg["letters"]]


def place_all(apis, toys, cfg, base, sent, old=None):
    """Turns every robot to its heading (not in hand mode) and draws its letter,
    in parallel. sent[i] is the heading robot i was last turned to; with `old`,
    letters are only redrawn when they changed."""
    def one(index):
        api, toy, item = apis[index], toys[index], cfg["letters"][index]
        heading = robot_heading(cfg, base, index)
        turned = False
        if not cfg["hand"] and heading != sent[index]:
            api.stop_roll(heading)                    # turn in place, no driving
            sent[index] = heading
            turned = True
        redraw = old is None or {k: item[k] for k in ("rotation", "mirror")} != \
            {k: old["letters"][index][k] for k in ("rotation", "mirror")}
        if redraw:
            show(api, toy, item)
            api.set_front_led(indicators.FRONT_LED)
        if turned or redraw:
            where = "turn by hand" if cfg["hand"] else f"heading {heading}"
            print(f"  robot {index + 1} {item['letter']}: {where}, letter rotation "
                  f"{item['rotation']}, turn {item['turn']:+d}, mirror "
                  f"{'on' if item['mirror'] else 'off'}", flush=True)
    on_robots(apis, one, timeout=20)


def main():
    cfg = letters.load()
    count = len(cfg["letters"])
    names = [f"BOLT-{i + 1}" for i in range(count)]
    with contextlib.ExitStack() as stack:
        apis, toys, robot_stacks = [], [], []

        def disconnect_all():                       # all robots at once, so Stop is quick
            threads = [threading.Thread(target=st.close, daemon=True) for st in robot_stacks]
            for th in threads:
                th.start()
            for th in threads:
                th.join(timeout=10)
        stack.callback(disconnect_all)

        # Robots 1..7 of the pool, and spares (8, 9, ...) for any that fail to connect.
        pool = sorted(int(k.split("-")[1]) for k in sphero_ble.load_cached_bolts()
                      if k.startswith("BOLT-") and k.split("-")[1].isdigit())
        candidates = [f"BOLT-{n}" for n in pool] or list(names)
        for index in range(count):
            letter = cfg["letters"][index]["letter"]
            while True:
                if not candidates:
                    raise SystemExit(f"Not enough robots: no robot left for letter {index + 1} ({letter}).")
                name = candidates.pop(0)
                print(f"Connecting letter {index + 1} of {count} ({letter}) to {name}...", flush=True)
                own = contextlib.ExitStack()
                try:
                    toy, api = sphero_ble.connect_toy(
                        name, lambda t: own.enter_context(SpheroEduAPI(t)), attempts=2)
                    break
                except ConnectionError as e:
                    print(f"  {e}. Trying the next robot for {letter}.", flush=True)
            names[index] = f"{name} ({letter})"
            robot_stacks.append(own)
            toys.append(toy)
            apis.append(api)
            with contextlib.suppress(Exception):     # no sensors needed: keep Bluetooth quiet
                toy.sensor_control.disable_all()

        north = None
        if cfg["hand"]:
            print("Hand mode: turn the robots by hand, they stay where you put them.", flush=True)
            set_hand_mode(apis, True)
        elif cfg["align"] == "compass":
            north = calibrate_compasses(toys, names)
        else:
            bolt_dance.aim(apis, toys, [LETTER_COLOR] * count)
        base = compass_base(cfg, north, count)
        sent = [None] * count

        updates = queue.Queue()
        letters.listen(updates.put)
        try:
            place_all(apis, toys, cfg, base, sent)
            print(f"{''.join(i['letter'] for i in cfg['letters'])} is shown, one letter per robot. "
                  "Stop to end.", flush=True)

            while True:
                try:
                    new = updates.get(timeout=0.5)
                except queue.Empty:
                    continue
                while not updates.empty():          # only the latest settings matter
                    new = updates.get()
                if new["hand"] and not cfg["hand"]:
                    print("Hand mode on: turn the robots by hand.", flush=True)
                    set_hand_mode(apis, True)
                elif cfg["hand"] and not new["hand"]:
                    base = keep_hand_directions(apis, new)
                    sent = [robot_heading(new, base, i) for i in range(count)]   # = where they are now
                    set_hand_mode(apis, False)
                    print("Hand mode off: the robots keep the directions you gave them.", flush=True)
                elif new["align"] != cfg["align"] and not new["hand"]:
                    if new["align"] == "compass" and north is None:
                        north = calibrate_compasses(toys, names)
                    base = compass_base(new, north, count)
                place_all(apis, toys, new, base, sent, old=cfg)
                cfg = new
        except KeyboardInterrupt:
            pass
        finally:
            def reset(api, toy):
                with contextlib.suppress(Exception):
                    api.stop_roll()
                    indicators.fill_all(toy, Color(0, 0, 0))
                    api.set_front_led(Color(0, 0, 0))
                    api.set_back_led(Color(0, 0, 0))
                    api.set_stabilization(True)
            threads = [threading.Thread(target=reset, args=(a, t), daemon=True) for a, t in zip(apis, toys)]
            for th in threads:
                th.start()
            for th in threads:
                th.join(timeout=6)
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped.")
