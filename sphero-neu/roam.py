"""
Roam: all 3 robots wander around their own start spot until you stop them.

Each robot picks a random point inside a circle (RADIUS cm) around its start
spot, drives there slowly, pauses, and picks the next point. Positions come
from the robots' locators (see formation.py), so aim them as usual.
A robot waits while a lower-numbered robot is closer than formation.MIN_GAP.
If a point is not reached within TARGET_TIMEOUT seconds, it picks a new one.

On Ctrl+C (Stop on the web page) all robots drive back to their start spots
(at most HOME_TIMEOUT seconds), face forward, and disconnect.

    .venv/bin/python roam.py              radius 25 cm
    .venv/bin/python roam.py --radius 15  any value from 15 to 30 cm
"""

import argparse
import contextlib
import math
import random
import threading
import time

from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color

import bolt_dance
import formation
import indicators
import sphero_ble

RADIUS = 25              # cm, default size of each robot's area
MIN_HOP = 8              # cm, a new point is at least this far from the robot
TARGET_TIMEOUT = 5.0     # s, give up on a point after this time
PAUSE = (0.3, 1.5)       # s, random pause at each point
HOME_TIMEOUT = 8.0       # s, time to drive back home after Stop


def random_point(home, radius, near):
    """Random point in the circle around home, at least MIN_HOP from `near`."""
    for _ in range(20):
        angle = random.uniform(0, 2 * math.pi)
        r = radius * math.sqrt(random.random())       # uniform over the area
        p = (home[0] + r * math.sin(angle), home[1] + r * math.cos(angle))
        if near is None or math.dist(p, near) >= MIN_HOP:
            return p
    return p


def roam(driver, radius, stop):
    home = driver.home()
    while not stop.is_set():
        target = random_point(home, radius, driver.tracker.now(driver.index))
        deadline = time.monotonic() + TARGET_TIMEOUT
        while not stop.is_set() and time.monotonic() < deadline:
            dist = driver.step(target)
            if dist is not None and dist < formation.ARRIVED:
                break
            time.sleep(formation.TICK)
        driver.halt()
        stop.wait(random.uniform(*PAUSE))
        driver.tracker.update(driver.index, driver.api)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--radius", type=float, default=RADIUS)
    parser.add_argument("--robots", type=int, default=15)
    args = parser.parse_args()
    radius = min(30.0, max(15.0, args.radius))

    is_sim = sphero_ble.is_simulation()
    if is_sim:
        import sphero_sim
        sphero_sim.SimulatorManager.get().apply_layout("roam")
        robots_to_run = [(spec[0], spec[4]) for spec in sphero_sim.DEFAULT_ROBOT_SPECS]
    else:
        cache = sphero_ble.load_cached_bolts()
        pool_items = []
        for key, addr in cache.items():
            if key.startswith("BOLT-") and key[5:].isdigit():
                bt = next((k for k, v in cache.items() if v == addr and k.startswith("SB-")), None)
                if bt:
                    pool_items.append((int(key[5:]), bt))
        pool_items.sort(key=lambda x: x[0])
        colors = [
            Color(255, 59, 59), Color(46, 204, 113), Color(52, 152, 219),
            Color(241, 196, 15), Color(232, 67, 147), Color(0, 206, 201),
            Color(230, 126, 34), Color(255, 255, 255), Color(155, 89, 182),
            Color(253, 121, 168), Color(9, 132, 227), Color(0, 184, 148),
            Color(255, 234, 167), Color(108, 92, 231), Color(214, 48, 49),
        ]
        if pool_items:
            robots_to_run = [(bt, colors[(idx - 1) % len(colors)]) for idx, bt in pool_items]
        else:
            robots_to_run = list(bolt_dance.ROBOTS)

    robots_to_run = robots_to_run[:max(1, min(15, args.robots))]

    with contextlib.ExitStack() as stack:
        apis, toys = [], []
        for index, (name, _) in enumerate(robots_to_run):
            print(f"Connecting robot {index + 1}: {name}...", flush=True)
            try:
                toy, api = sphero_ble.connect_toy(
                    name, lambda t: stack.enter_context(SpheroEduAPI(t)))
            except ConnectionError as e:
                raise SystemExit(str(e))
            toys.append(toy)
            apis.append(api)

        bolt_dance.aim(apis, toys, [c for _, c in robots_to_run])

        tracker = formation.Tracker()
        roam_stop = threading.Event()      # ends roaming
        home_stop = threading.Event()      # ends driving home early
        arrow_stop = threading.Event()     # ends the direction arrows
        drivers = [formation.Driver(api, i, tracker, home_stop) for i, api in enumerate(apis)]
        arrows = [indicators.NorthArrow(apis[i], toys[i], robots_to_run[i][1],
                                        lambda d=d: d._heading or 0, arrow_stop).start()
                  for i, d in enumerate(drivers)]
        threads = [threading.Thread(target=roam, args=(d, radius, roam_stop), daemon=True)
                   for d in drivers]
        for th in threads:
            th.start()
        print(f"Roaming {len(drivers)} robots in a {radius:.0f} cm circle around each start spot. "
              "Stop to bring them home.", flush=True)

        try:
            while any(th.is_alive() for th in threads):
                time.sleep(0.2)
        except KeyboardInterrupt:
            pass
        finally:
            roam_stop.set()
            for th in threads:
                th.join(timeout=3)
            print("Driving home...", flush=True)
            results = {}
            deadline = time.monotonic() + HOME_TIMEOUT
            homers = [threading.Thread(
                target=lambda d=d: results.__setitem__(d.index, d.go_home(deadline)), daemon=True)
                for d in drivers]
            try:
                for th in homers:
                    th.start()
                for th in homers:
                    th.join(HOME_TIMEOUT + 2)
            except KeyboardInterrupt:
                home_stop.set()
            arrow_stop.set()
            for a in arrows:
                a.thread.join(timeout=2)
            for i, api in enumerate(apis):
                with contextlib.suppress(Exception):
                    api.stop_roll()
                    indicators.clear(api, toys[i])
                    api.set_front_led(Color(0, 0, 0))
                print(f"  {robots_to_run[i][0]}: "
                      f"{'home' if results.get(i) else 'not home (time up)'}", flush=True)
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped.")
