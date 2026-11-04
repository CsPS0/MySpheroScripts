"""
LED test. Does not move the robots.

Connects to all 3 robots. The matrices show N, E, U (robot 1, 2, 3) in the
robot's color, the front LED is white and the tail light blue. Rotation and
mirroring come from data/letters.json and can be changed live on the web page.

Runs until Ctrl+C (or Stop on the web page), at most HOLD seconds.
"""

import contextlib
import queue
import time

from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color

import bolt_dance
import indicators
import letters
import sphero_ble

HOLD = 120


def main():
    with contextlib.ExitStack() as stack:
        apis, toys = [], []
        for index, (name, _) in enumerate(bolt_dance.ROBOTS):
            print(f"Connecting robot {index + 1}: {name}...", flush=True)
            try:
                toy, api = sphero_ble.connect_toy(
                    name, lambda t: stack.enter_context(SpheroEduAPI(t)))
            except ConnectionError as e:
                raise SystemExit(str(e))
            apis.append(api)
            toys.append(toy)

        def show(cfg, index):
            item = cfg["letters"][index]
            indicators.show_letter(apis[index], toys[index], item["letter"],
                                   bolt_dance.ROBOTS[index][1], item["rotation"], item["mirror"])

        cfg = letters.load()
        updates = queue.Queue()
        letters.listen(updates.put)
        try:
            for index, api in enumerate(apis):
                api.set_back_led(Color(0, 0, 255))
                api.set_front_led(indicators.FRONT_LED)
                show(cfg, index)
            print(f"Showing {', '.join(i['letter'] for i in cfg['letters'])}. "
                  f"Holding for up to {HOLD} s.", flush=True)
            end = time.monotonic() + HOLD
            while time.monotonic() < end:
                try:
                    new = updates.get(timeout=0.5)
                except queue.Empty:
                    continue
                while not updates.empty():
                    new = updates.get()
                for index in range(len(apis)):
                    if new["letters"][index] != cfg["letters"][index]:
                        item = new["letters"][index]
                        print(f"  {item['letter']}: rotation {item['rotation']}, "
                              f"mirror {'on' if item['mirror'] else 'off'}", flush=True)
                        show(new, index)
                cfg = new
        except KeyboardInterrupt:
            pass
        finally:
            for api, toy in zip(apis, toys):
                with contextlib.suppress(Exception):
                    api.set_back_led(Color(0, 0, 0))
                    indicators.clear(api, toy)
                    api.set_front_led(Color(0, 0, 0))
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped.")
