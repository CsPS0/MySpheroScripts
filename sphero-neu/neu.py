"""
NEU: the robots line up and show N, E, U.

Setup as for the dance: a line, left to right SB-3FF5, SB-034E, SB-61A9.
After the aim phase (blue tail lights towards you) the robots, one after
another, turn in place to the same heading and show their letters.

The heading and each letter's rotation and mirroring come from
data/letters.json (see letters.py). Change them on the web page, in the
Letters panel: the robots update while this program runs.

Holds until Ctrl+C (Stop on the web page).
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

STAGGER = 0.8            # s between the robots turning


def show(apis, toys, cfg, index):
    item = cfg["letters"][index]
    indicators.show_letter(apis[index], toys[index], item["letter"],
                           bolt_dance.ROBOTS[index][1], item["rotation"], item["mirror"])


def main():
    cfg = letters.load()
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

        updates = queue.Queue()
        letters.listen(updates.put)
        try:
            for index, api in enumerate(apis):
                item = cfg["letters"][index]
                print(f"  {bolt_dance.ROBOTS[index][0]}: turning to {cfg['heading']}, "
                      f"showing {item['letter']} (rotation {item['rotation']}, "
                      f"mirror {'on' if item['mirror'] else 'off'})", flush=True)
                api.stop_roll(cfg["heading"])          # turn in place, no driving
                show(apis, toys, cfg, index)
                api.set_front_led(indicators.FRONT_LED)
                time.sleep(STAGGER)
            print("NEU is shown. Rotate letters on the web page. Stop to end.", flush=True)

            while True:
                try:
                    new = updates.get(timeout=0.5)
                except queue.Empty:
                    continue
                while not updates.empty():          # only the latest settings matter
                    new = updates.get()
                if new["heading"] != cfg["heading"]:
                    print(f"  heading {new['heading']}", flush=True)
                    for api in apis:
                        api.stop_roll(new["heading"])
                for index in range(len(apis)):
                    if new["letters"][index] != cfg["letters"][index]:
                        item = new["letters"][index]
                        print(f"  {item['letter']}: rotation {item['rotation']}, "
                              f"mirror {'on' if item['mirror'] else 'off'}", flush=True)
                        show(apis, toys, new, index)
                cfg = new
        except KeyboardInterrupt:
            pass
        finally:
            for api, toy in zip(apis, toys):
                with contextlib.suppress(Exception):
                    api.stop_roll()
                    indicators.clear(api, toy)
                    api.set_front_led(Color(0, 0, 0))
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped.")
