"""
Connection test. Does not move the robot and does not change its lights.

Connects, prints name, address, battery voltage and firmware version,
then disconnects.

    .venv/bin/python connect_test.py SB-3FF5
    .venv/bin/python connect_test.py SB-3FF5 SB-034E SB-61A9   # in a row
    .venv/bin/python connect_test.py --hold SB-3FF5 SB-034E SB-61A9
        (keeps all connections open at the same time, like bolt_dance.py)
"""

import contextlib
import logging
import sys
import time

import sphero_ble


def read_info(toy):
    voltage = toy.get_battery_voltage()
    firmware = toy.get_main_app_version()
    print(f"  {toy.name} ({toy.address})")
    print(f"    battery:  {voltage:.2f} V")
    print(f"    firmware: {firmware}")


def main():
    args = sys.argv[1:]
    hold = "--hold" in args
    if "-v" in args:
        logging.basicConfig(level=logging.DEBUG)
    names = [a.upper() for a in args if not a.startswith("-")]
    if not names:
        raise SystemExit(__doc__)

    results = {}
    with contextlib.ExitStack() as held:
        for name in names:
            print(f"{name}:")
            t = time.monotonic()
            try:
                with contextlib.ExitStack() as stack:
                    toy, _ = sphero_ble.connect_toy(name, stack.enter_context)
                    read_info(toy)
                    if hold:
                        held.enter_context(stack.pop_all())
                results[name] = f"OK ({time.monotonic() - t:.1f} s)"
            except Exception as e:
                results[name] = f"FAILED: {e}"
                print(f"  {results[name]}")
        if hold:
            print(f"Holding {len(held._exit_callbacks)} connection(s) for 3 s...")
            time.sleep(3)

    print("\nSummary:")
    for name, result in results.items():
        print(f"  {name}: {result}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped.")
