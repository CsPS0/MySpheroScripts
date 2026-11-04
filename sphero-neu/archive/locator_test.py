"""
Locator test for the follow and home parts of bolt_dance.py. The robots move.

Same setup and aim phase as bolt_dance.py. Then one robot after another:
  1. roll forward (heading 0) for 1 s, print the location   -> expect y > 0, x near 0
  2. roll right (heading 90) for 1 s, print the location    -> expect x > 0
  3. drive home to the start point and face forward
"""

import contextlib
import threading
import time

from spherov2.sphero_edu import SpheroEduAPI

import bolt_dance
import formation
import sphero_ble

SPEED = 40


def show(api, label):
    time.sleep(0.8)                   # let the robot settle and the sensors update
    loc = api.get_location()
    print(f"    {label:<14} x={loc['x']:6.1f}  y={loc['y']:6.1f} cm")
    return loc


def main():
    with contextlib.ExitStack() as stack:
        apis, toys = [], []
        for index, (name, _) in enumerate(bolt_dance.ROBOTS):
            print(f"Connecting robot {index + 1}: {name}...")
            toy, api = sphero_ble.connect_toy(
                name, lambda t: stack.enter_context(SpheroEduAPI(t)))
            toys.append(toy)
            apis.append(api)

        bolt_dance.aim(apis, toys)
        tracker = formation.Tracker()
        stop = threading.Event()

        for index, api in enumerate(apis):
            print(f"Robot {index + 1} ({toys[index].name}):")
            show(api, "start")
            api.roll(0, SPEED, 1.0)
            show(api, "after forward")
            api.roll(90, SPEED, 1.0)
            show(api, "after right")
            driver = formation.Driver(api, index, tracker, stop)
            arrived = driver.go_home(time.monotonic() + 10)
            loc = show(api, "after home")
            print(f"    home: {'arrived' if arrived else 'timeout'}, "
                  f"{(loc['x'] ** 2 + loc['y'] ** 2) ** 0.5:.1f} cm from start")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped.")
