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
    args = parser.parse_args()
    radius = min(30.0, max(15.0, args.radius))

    with contextlib.ExitStack() as stack:
        apis, toys = [], []
        for index, (name, _) in enumerate(bolt_dance.ROBOTS):
            print(f"Connecting robot {index + 1}: {name}...", flush=True)
            try:
                toy, api = sphero_ble.connect_toy(
                    name, lambda t: stack.enter_context(SpheroEduAPI(t)))
            except ConnectionError as e:
                raise SystemExit(str(e))
            toys.append(toy)
            apis.append(api)

        bolt_dance.aim(apis, toys)

        tracker = formation.Tracker()
        roam_stop = threading.Event()      # ends roaming
        home_stop = threading.Event()      # ends driving home early
        arrow_stop = threading.Event()     # ends the direction arrows
        drivers = [formation.Driver(api, i, tracker, home_stop) for i, api in enumerate(apis)]
        arrows = [indicators.NorthArrow(apis[i], toys[i], bolt_dance.ROBOTS[i][1],
                                        lambda d=d: d._heading or 0, arrow_stop).start()
                  for i, d in enumerate(drivers)]
        threads = [threading.Thread(target=roam, args=(d, radius, roam_stop), daemon=True)
                   for d in drivers]
        for th in threads:
            th.start()
        print(f"Roaming in a {radius:.0f} cm circle around each start spot. "
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
                print(f"  {bolt_dance.ROBOTS[i][0]}: "
                      f"{'home' if results.get(i) else 'not home (time up)'}", flush=True)
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped.")
