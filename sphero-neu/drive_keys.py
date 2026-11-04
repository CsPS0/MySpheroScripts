"""
Drive BOLTs with the keyboard.

    --robots 1      one robot: SB-3FF5, with W A S D or the arrow keys
    --robots 1,3    two robots: SB-3FF5 with W A S D, SB-61A9 with the arrow keys
                    (numbers are the positions in bolt_dance.ROBOTS, 1 = left)

Only the robots that are driven get connected.
Directions are seen from you, after the aim phase: W / Up drives away from you,
S / Down towards you, A / Left to the left, D / Right to the right. Two keys at
once drive diagonally. Hold Shift for more speed. Release to stop.
The matrix arrow always points west (to your left, indicators.ARROW_POINTS), also
while the robot drives left or right. The white front LED marks the robot's front.

Two ways to run it:

    .venv/bin/python drive_keys.py --robots 1,3
        Opens a small window (pygame). It must have keyboard focus. If it loses
        focus, the robots stop. Esc or closing the window quits.

    python drive_keys.py --stdin --robots 1,3
        Used by the web page. Reads lines "keys <code>,<code>,... <turbo 0|1>"
        with browser key codes (KeyW, ArrowUp, ...). If no line arrives for
        STDIN_TIMEOUT seconds, the robots stop. Ends on Ctrl+C or end of input.
"""

import argparse
import contextlib
import math
import sys
import threading
import time

from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color

import bolt_dance
import indicators
import sphero_ble

DRIVE_SPEED = 70
TURBO_SPEED = 140
TICK = 0.05                 # seconds, command loop period of a driven robot
STDIN_TIMEOUT = 1.0         # seconds without input before the robots stop

WASD = {"KeyW": (0, 1), "KeyS": (0, -1), "KeyA": (-1, 0), "KeyD": (1, 0)}
ARROWS = {"ArrowUp": (0, 1), "ArrowDown": (0, -1), "ArrowLeft": (-1, 0), "ArrowRight": (1, 0)}
ALL_KEYS = set(WASD) | set(ARROWS)


def keymaps_for(robots):
    """Robot index -> key code -> direction (x right, y away from you)."""
    if len(robots) == 1:
        return {robots[0]: {**WASD, **ARROWS}}
    if len(robots) == 2:
        return {robots[0]: WASD, robots[1]: ARROWS}
    raise SystemExit("--robots takes one or two robot numbers, for example 1 or 1,3")


class Driven:
    """Sends the wanted heading and speed to one robot, only when they change."""

    def __init__(self, api, stop):
        self.api = api
        self.stop = stop
        self.wanted = (0, 0)        # heading, speed
        self._sent = (0, 0)

    def run(self):
        while not self.stop.is_set():
            heading, speed = self.wanted
            if (heading, speed) != self._sent:
                if speed == 0:
                    self.api.stop_roll()
                else:
                    self.api.set_heading(heading)
                    self.api.set_speed(speed)
                self._sent = (heading, speed)
            time.sleep(TICK)
        self.api.stop_roll()


def wanted_move(pressed, keymap, turbo):
    """pressed: set of key codes. Returns (heading, speed) or None."""
    dx = sum(v[0] for k, v in keymap.items() if k in pressed)
    dy = sum(v[1] for k, v in keymap.items() if k in pressed)
    if dx == 0 and dy == 0:
        return None
    heading = round(math.degrees(math.atan2(dx, dy))) % 360
    return heading, TURBO_SPEED if turbo else DRIVE_SPEED


def apply_keys(drivers, keymaps, pressed, turbo):
    """Updates every driven robot. Returns a status text per robot index."""
    status = {}
    for i, keymap in keymaps.items():
        move = wanted_move(pressed, keymap, turbo)
        drivers[i].wanted = move if move else (drivers[i].wanted[0], 0)
        status[i] = f"heading {move[0]:3d}, speed {move[1]}" if move else "stopped"
    return status


def status_line(status):
    return "   ".join(f"{bolt_dance.ROBOTS[i][0]}: {text:<22}" for i, text in status.items())


def run_window(drivers, keymaps):
    import pygame

    codes = {
        pygame.K_w: "KeyW", pygame.K_a: "KeyA", pygame.K_s: "KeyS", pygame.K_d: "KeyD",
        pygame.K_UP: "ArrowUp", pygame.K_DOWN: "ArrowDown",
        pygame.K_LEFT: "ArrowLeft", pygame.K_RIGHT: "ArrowRight",
    }
    pygame.init()
    screen = pygame.display.set_mode((620, 200))
    pygame.display.set_caption("Sphero keys")
    font = pygame.font.Font(None, 30)
    clock = pygame.time.Clock()
    print("Drive in the window. Esc quits.")
    try:
        while True:
            if any(e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE)
                   for e in pygame.event.get()):
                break
            focused = pygame.key.get_focused()
            state = pygame.key.get_pressed()
            pressed = {code for key, code in codes.items() if state[key]} if focused else set()
            turbo = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
            status = apply_keys(drivers, keymaps, pressed, turbo)
            screen.fill((20, 20, 28))
            lines = [(f"{bolt_dance.ROBOTS[i][0]}  {status[i]}", (230, 230, 230)) for i in keymaps]
            lines += [("", (0, 0, 0)), ("Shift = faster.  Esc = stop and quit.", (200, 200, 200)),
                      ("" if focused else "Window not focused: driving paused.", (255, 200, 0))]
            for n, (text, color) in enumerate(lines):
                screen.blit(font.render(text, True, color), (20, 20 + n * 34))
            pygame.display.flip()
            clock.tick(30)
    finally:
        pygame.quit()


def run_stdin(drivers, keymaps):
    latest = {"pressed": set(), "turbo": False, "time": 0.0, "eof": False}
    lock = threading.Lock()

    def reader():
        for line in sys.stdin:
            parts = line.split()
            if len(parts) >= 1 and parts[0] == "keys":
                codes = set(parts[1].split(",")) if len(parts) > 1 and parts[1] != "-" else set()
                with lock:
                    latest["pressed"] = codes & ALL_KEYS
                    latest["turbo"] = len(parts) > 2 and parts[2] == "1"
                    latest["time"] = time.monotonic()
            elif len(parts) >= 4 and parts[0] == "drive":
                # drive <bot_idx_1_based> <heading_deg> <speed_0_to_255>
                try:
                    bot_idx = int(parts[1]) - 1
                    h = float(parts[2]) % 360
                    s = max(0.0, min(255.0, float(parts[3])))
                    if bot_idx in drivers:
                        drivers[bot_idx].wanted = (h, s)
                except ValueError:
                    pass
        latest["eof"] = True

    threading.Thread(target=reader, daemon=True).start()
    print("Driving. Use the keys on the web page.", flush=True)
    last_status = None
    while not latest["eof"]:
        with lock:
            fresh = time.monotonic() - latest["time"] < STDIN_TIMEOUT
            pressed = latest["pressed"] if fresh else set()
            turbo = latest["turbo"]
        status = apply_keys(drivers, keymaps, pressed, turbo)
        if status != last_status:
            print("  " + status_line(status), flush=True)
            last_status = status
        time.sleep(TICK)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--robots", default="1,3")
    args = parser.parse_args()
    robots = [int(n) - 1 for n in args.robots.split(",")]
    keymaps = keymaps_for(robots)

    with contextlib.ExitStack() as stack:
        apis, toys = {}, {}
        discovered = bolt_dance.get_robots(max(robots) + 1)
        for i in robots:
            name = discovered[i][0]
            print(f"Connecting robot {i + 1}: {name}...", flush=True)
            try:
                toys[i], apis[i] = sphero_ble.connect_toy(
                    name, lambda t: stack.enter_context(SpheroEduAPI(t)))
            except ConnectionError as e:
                raise SystemExit(str(e))

        bolt_dance.aim([apis[i] for i in robots], [toys[i] for i in robots],
                       [discovered[i][1] for i in robots])

        stop = threading.Event()
        drivers = {i: Driven(apis[i], stop) for i in robots}
        threads = [threading.Thread(target=d.run, daemon=True) for d in drivers.values()]
        for i, d in drivers.items():       # matrix arrow keeps pointing west (indicators.ARROW_POINTS)
            threads.append(indicators.NorthArrow(
                apis[i], toys[i], bolt_dance.ROBOTS[i][1],
                lambda d=d: d.wanted[0], stop).thread)
        for th in threads:
            th.start()

        try:
            if args.stdin:
                run_stdin(drivers, keymaps)
            else:
                run_window(drivers, keymaps)
        except KeyboardInterrupt:
            pass
        finally:
            stop.set()
            for th in threads:
                th.join(timeout=3)
            for i, api in apis.items():
                with contextlib.suppress(Exception):
                    api.stop_roll()
                    indicators.clear(api, toys[i])
                    api.set_front_led(Color(0, 0, 0))
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped.")
