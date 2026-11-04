"""
Stationary party games with BOLTs. The robots never drive.

    .venv/bin/python minigames.py simon | mole | potato | rps

simon   Simon Says (2 to 9 balls). Every ball has its own color. The balls
        light up in a sequence; shake them back in the same order. The
        sequence grows by one each level. A wrong ball ends the game.
mole    Whack-a-mole (1 to 9 balls). A random ball turns green; shake it
        before it goes dark. Wrong ball: -1. One round lasts 60 s and the
        moles get faster.
potato  Hot potato (1 ball). Shake it to light the fuse, then pass it around.
        It blinks faster and turns from green to red. After a secret
        15 to 35 s it explodes: whoever holds it is out.
lightshow  Light show (1 to 15 balls). Shake the balls in order along your
        line to set the order (or press Start for connection order). Then
        effects run in sync: rainbow, comet, breathing, police, sparkle,
        wave. Start skips to the next effect, a shake makes that ball flash.
rps     Rock-paper-scissors (2 balls, player 1 red, player 2 blue). Both
        players shake their ball, a 3-2-1 countdown runs (red, yellow, green),
        then every ball shows a random rock, paper or scissors. First to 2
        wins the match.

Robots are chosen like in tic-tac-toe (data/tictactoe.json: the nearest free
BOLTs in auto mode, or the fixed names), the symbol orientation too.

Talks to the web page: prints "STATE {json}" lines, reads stdin lines:
"tap <n>" (like shaking ball n, 1-based), "start", "config {json}".
Ends on Ctrl+C.
"""

import argparse
import colorsys
import contextlib
import math
import json
import queue
import random
import threading
import time

from spherov2.types import Color

import indicators
import tictactoe
from tictactoe import OFF, Display, ShakeDetector

WHITE = Color(255, 255, 255)
RED = Color(255, 0, 0)
GREEN = Color(0, 255, 0)
YELLOW = Color(255, 200, 0)
GOLD = Color(255, 150, 0)
PLAYER = [Color(255, 30, 30), Color(30, 110, 255)]
PALETTE = [Color(255, 0, 0), Color(0, 255, 0), Color(0, 60, 255), Color(255, 200, 0),
           Color(255, 0, 200), Color(0, 230, 230), Color(255, 90, 0), Color(255, 255, 255),
           Color(130, 0, 255)]

GLYPHS = dict(tictactoe.GLYPHS)
GLYPHS.update({
    "Rock": ["..XXXX..", ".XXXXXX.", "XXXXXXXX", "XXXXXXXX", "XXXXXXXX", "XXXXXXXX", ".XXXXXX.", "..XXXX.."],
    "Paper": ["XXXXXX..", "X....XX.", "X.....XX", "X.XXX..X", "X......X", "X.XXXX.X", "X......X", "XXXXXXXX"],
    "Scissors": ["X.....X.", ".X...X..", "..X.X...", "...X....", "..X.X...", "XXX.XXX.", "X.X.X.X.", "XXX.XXX."],
})
BEATS = {"Rock": "Scissors", "Paper": "Rock", "Scissors": "Paper"}


def dim(color, factor):
    return Color(int(color.r * factor), int(color.g * factor), int(color.b * factor))


def mix(a, b, f):
    return Color(*(int(x + (y - x) * f) for x, y in ((a.r, b.r), (a.g, b.g), (a.b, b.b))))


def hexcolor(c):
    return f"#{c.r:02x}{c.g:02x}{c.b:02x}"


class Party:
    """Base for the games. Robots are numbered 0..n-1 in connection order."""

    id = title = ""
    want = 9            # robots to connect
    need = 1            # fewest robots the game works with

    def __init__(self, cfg, names, displays):
        self.cfg, self.names, self.displays = cfg, names, displays
        self.shown = {r: OFF for r in displays}     # for the web page
        self.labels = {r: "" for r in displays}
        self.status = self.info = ""
        self.phase = "idle"

    def solid(self, r, color, led=None, label=""):
        self.shown[r], self.labels[r] = color, label
        self.displays[r].solid(color)
        self.displays[r].led(color if led is None else led)

    def glyph(self, r, key, color, led=None, label=None):
        self.shown[r], self.labels[r] = color, key if label is None else label
        self.displays[r].glyph(GLYPHS[key], color, self.cfg["rotation"], self.cfg["mirror"])
        self.displays[r].led(color if led is None else led)

    def say(self, text):
        self.status = text
        print(text, flush=True)

    def start(self):
        pass

    def shake(self, r):
        return False

    def tick(self, now):
        return False

    def state(self):
        return {
            "kind": "party", "game": self.id, "title": self.title, "phase": self.phase,
            "status": self.status, "info": self.info,
            "cells": [{"robot": self.names[r], "color": hexcolor(self.shown[r]), "label": self.labels[r]}
                      for r in sorted(self.displays)],
        }


class Simon(Party):
    id, title, want, need = "simon", "Simon Says", 9, 2
    GAP = 0.25          # s dark between two steps of the sequence
    INPUT_TIMEOUT = 12  # s without a shake ends the game

    def __init__(self, *args):
        super().__init__(*args)
        self.color = {r: PALETTE[r % len(PALETTE)] for r in self.displays}
        self.best, self.seq, self.flash = 0, [], {}
        self.idle("Simon Says: shake any ball or press Start.")

    def rest(self, r):
        self.solid(r, dim(self.color[r], 0.12), OFF)

    def idle(self, text):
        self.phase = "idle"
        for r in self.displays:
            self.rest(r)
        self.say(text)

    def start(self):
        self.seq = []
        self.extend(time.monotonic())
        return True

    def extend(self, now):
        choices = [r for r in self.displays if not self.seq or r != self.seq[-1]]
        self.seq.append(random.choice(choices))
        self.phase, self.step, self.lit, self.next_at = "show", 0, None, now + 1.0
        self.info = f"Level {len(self.seq)}. Best {self.best}."
        self.say(f"Level {len(self.seq)}: watch the balls.")

    def on_time(self):
        return max(0.35, 0.8 - 0.04 * len(self.seq))

    def shake(self, r):
        now = time.monotonic()
        if self.phase == "idle":
            return self.start()
        if self.phase != "input":
            return False
        if r != self.seq[self.pos]:
            self.best = max(self.best, len(self.seq) - 1)
            for q in self.displays:
                self.solid(q, RED)
            self.phase, self.next_at = "over", now + 3.0
            self.info = f"Reached level {len(self.seq) - 1}. Best {self.best}."
            self.say(f"Wrong ball ({self.names[r]}). Game over at level {len(self.seq)}.")
            return True
        self.solid(r, self.color[r], WHITE)
        self.flash[r] = now + 0.4
        self.pos += 1
        self.input_until = now + self.INPUT_TIMEOUT
        if self.pos == len(self.seq):
            self.best = max(self.best, len(self.seq))
            self.phase, self.next_at = "pause", now + 1.3
            self.say(f"Level {len(self.seq)} done.")
        return True

    def tick(self, now):
        changed = False
        for r, until in list(self.flash.items()):
            if now >= until:
                del self.flash[r]
                if self.phase in ("input", "pause"):
                    self.rest(r)
                changed = True
        if self.phase == "show" and now >= self.next_at:
            if self.lit is not None:
                self.rest(self.lit)
                self.lit, self.step = None, self.step + 1
                self.next_at = now + self.GAP
                if self.step == len(self.seq):
                    self.phase, self.pos = "input", 0
                    self.input_until = now + self.INPUT_TIMEOUT
                    self.say(f"Your turn: shake the {len(self.seq)} balls in the same order.")
            else:
                self.lit = self.seq[self.step]
                self.solid(self.lit, self.color[self.lit], WHITE)
                self.next_at = now + self.on_time()
            return True
        if self.phase == "input" and now >= self.input_until:
            self.best = max(self.best, len(self.seq) - 1)
            for q in self.displays:
                self.solid(q, RED)
            self.phase, self.next_at = "over", now + 3.0
            self.say("Too slow. Game over.")
            return True
        if self.phase == "pause" and now >= self.next_at:
            self.extend(now)
            return True
        if self.phase == "over" and now >= self.next_at:
            self.idle("Shake any ball or press Start to play again.")
            return True
        return changed


class Mole(Party):
    id, title, want, need = "mole", "Whack-a-mole", 9, 1
    ROUND = 60          # s
    MOLE = GREEN
    IDLE = Color(0, 0, 40)

    def __init__(self, *args):
        super().__init__(*args)
        self.best, self.score, self.flash = 0, 0, {}
        self.idle("Whack-a-mole: shake any ball or press Start.")

    def idle(self, text):
        self.phase = "idle"
        for r in self.displays:
            self.solid(r, self.IDLE, OFF)
        self.say(text)

    def start(self):
        now = time.monotonic()
        self.phase, self.score, self.misses = "play", 0, 0
        self.started, self.mole, self.last, self.next_at = now, None, None, now + 1.5
        self.second = None
        for r in self.displays:
            self.solid(r, OFF)
        self.say(f"Go! {self.ROUND} s. Shake the green ball.")
        return True

    def window(self, now):
        return max(1.2, 2.4 - 1.2 * (now - self.started) / self.ROUND)

    def gap(self):
        return 1.7 if len(self.displays) == 1 else random.uniform(0.3, 0.9)

    def shake(self, r):
        now = time.monotonic()
        if self.phase == "idle":
            return self.start()
        if self.phase != "play":
            return False
        if r == self.mole:
            self.score += 1
            self.solid(r, Color(0, 80, 255))
            self.mole, self.next_at = None, now + self.gap()
        else:
            self.score -= 1
            self.solid(r, RED)
        self.flash[r] = now + 0.35
        return True

    def tick(self, now):
        if self.phase == "play":
            changed = False
            for r, until in list(self.flash.items()):
                if now >= until:
                    del self.flash[r]
                    if r != self.mole:
                        self.solid(r, OFF)
                    changed = True
            left = self.ROUND - (now - self.started)
            if left <= 0:
                self.best = max(self.best, self.score)
                for r in self.displays:
                    self.solid(r, GOLD)
                self.phase, self.next_at = "over", now + 4.0
                self.info = f"Score {self.score}, missed {self.misses}. Best {self.best}."
                self.say(f"Time! Score {self.score}.")
                return True
            if self.mole is not None and now >= self.mole_until:
                self.solid(self.mole, OFF)
                self.mole, self.misses, self.next_at = None, self.misses + 1, now + self.gap()
                changed = True
            if self.mole is None and now >= self.next_at:
                choices = [r for r in self.displays if r != self.last and r not in self.flash]
                if choices:
                    self.mole = self.last = random.choice(choices)
                    self.mole_until = now + self.window(now)
                    self.solid(self.mole, self.MOLE)
                    changed = True
            if int(left) != self.second:
                self.second = int(left)
                self.info = f"Score {self.score}. Missed {self.misses}. {self.second} s left."
                changed = True
            return changed
        if self.phase == "over" and now >= self.next_at:
            self.idle("Shake any ball or press Start to play again.")
            return True
        return False


class Potato(Party):
    id, title, want, need = "potato", "Hot potato", 1, 1
    FUSE = (15.0, 35.0)     # s, secret random length
    BOOM = 3.0              # s of explosion flashing
    READY_AFTER = 3.0       # s after the explosion before a shake starts again

    def __init__(self, *args):
        super().__init__(*args)
        self.rounds = 0
        self.idle("Hot potato: shake the ball or press Start, then pass it on.")

    def idle(self, text):
        self.phase = "idle"
        for r in self.displays:
            self.glyph(r, "?", GOLD)
        self.say(text)

    def start(self):
        now = time.monotonic()
        self.phase, self.started = "play", now
        self.fuse = random.uniform(*self.FUSE)
        self.on, self.next_at = True, now
        self.rounds += 1
        self.info = f"Round {self.rounds}."
        self.say("The fuse is lit. Pass it on!")
        return True

    def shake(self, r):
        if self.phase == "idle" or (self.phase == "out" and time.monotonic() >= self.ready_at):
            return self.start()
        return False             # passing it around shakes it: ignored while playing

    def tick(self, now):
        if self.phase == "play":
            f = (now - self.started) / self.fuse
            if f >= 1:
                self.phase, self.until, self.on, self.next_at = "boom", now + self.BOOM, True, now
                self.say("BOOM! Whoever holds the ball is out.")
                return True
            if now >= self.next_at:
                self.on = not self.on
                color = mix(GREEN, RED, min(1.0, f * 1.15))
                for r in self.displays:
                    self.solid(r, color if self.on else OFF)
                self.next_at = now + (0.5 - 0.42 * f)
                return True
            return False
        if self.phase == "boom":
            if now >= self.until:
                for r in self.displays:
                    self.glyph(r, "X", RED)
                self.phase, self.ready_at = "out", now + self.READY_AFTER
                self.say("Shake the ball or press Start for the next round.")
                return True
            if now >= self.next_at:
                self.on = not self.on
                for r in self.displays:
                    self.solid(r, RED if self.on else WHITE)
                self.next_at = now + 0.12
                return True
        return False


class RockPaperScissors(Party):
    id, title, want, need = "rps", "Rock-paper-scissors", 2, 2
    TO_WIN = 2

    def __init__(self, *args):
        super().__init__(*args)
        self.players = sorted(self.displays)[:2]
        self.score = [0, 0]
        for r in list(self.displays)[2:]:
            self.solid(r, OFF)
        self.wait()

    def wait(self):
        self.phase, self.ready = "wait", set()
        for i, r in enumerate(self.players):
            self.glyph(r, "?", PLAYER[i], label=f"Player {i + 1}")
        self.info = f"Player 1 (red) {self.score[0]} : {self.score[1]} Player 2 (blue). First to {self.TO_WIN}."
        self.say("Both players: shake your ball when ready.")

    def start(self):
        if self.phase in ("wait", "matchover"):
            if self.phase == "matchover":
                self.score = [0, 0]
            self.ready = set(self.players)
            self.count(time.monotonic())
            return True
        return False

    def count(self, now):
        self.phase, self.step, self.next_at = "count", 0, now + 0.3

    def shake(self, r):
        if self.phase == "matchover":
            self.score = [0, 0]
            self.wait()
            return True
        if self.phase != "wait" or r not in self.players or r in self.ready:
            return False
        self.ready.add(r)
        self.solid(r, WHITE, PLAYER[self.players.index(r)], label="Ready")
        print(f"  Player {self.players.index(r) + 1} is ready.", flush=True)
        if len(self.ready) == 2:
            self.count(time.monotonic())
        return True

    def tick(self, now):
        if self.phase == "count" and now >= self.next_at:
            if self.step < 3:
                color = (RED, YELLOW, GREEN)[self.step]
                for r in self.players:
                    self.solid(r, color, label=str(3 - self.step))
                self.say(f"{3 - self.step}...")
                self.step += 1
                self.next_at = now + 0.9
                return True
            self.reveal(now)
            return True
        if self.phase == "result" and now >= self.next_at:
            if max(self.score) >= self.TO_WIN:
                winner = self.score.index(max(self.score))
                self.phase, self.next_at = "matchover", now + 8.0
                for i, r in enumerate(self.players):
                    self.solid(r, GREEN if i == winner else RED)
                self.say(f"Player {winner + 1} wins the match {self.score[winner]} : "
                         f"{self.score[1 - winner]}! Shake a ball or press Start for a new match.")
            else:
                self.wait()
            return True
        if self.phase == "matchover" and now >= self.next_at:
            self.score = [0, 0]
            self.wait()
            return True
        return False

    def reveal(self, now):
        picks = [random.choice(list(BEATS)) for _ in self.players]
        if picks[0] == picks[1]:
            leds, text = [YELLOW, YELLOW], "Draw"
        else:
            winner = 0 if BEATS[picks[0]] == picks[1] else 1
            self.score[winner] += 1
            leds = [GREEN if i == winner else RED for i in range(2)]
            text = f"Player {winner + 1} wins the round"
        for i, r in enumerate(self.players):
            self.glyph(r, picks[i], PLAYER[i], leds[i])
        self.info = f"Player 1 (red) {self.score[0]} : {self.score[1]} Player 2 (blue). First to {self.TO_WIN}."
        self.say(f"{picks[0]} against {picks[1]}: {text}.")
        self.phase, self.next_at = "result", now + 4.0


def hue(h, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, 1.0, v)
    return Color(int(r * 255), int(g * 255), int(b * 255))


def fx_rainbow(i, n, t):
    return hue(round((i / n + t * 0.2) * 24) / 24)


def fx_comet(i, n, t):
    head = (t * 6) % (n + 3)
    behind = head - i
    return dim(Color(0, 220, 255), 1.0 - behind / 3.5) if 0 <= behind < 3.5 else OFF


def fx_breathe(i, n, t):
    v = 0.1 + 0.9 * math.sin(t * 1.6) ** 2
    return hue(t * 0.05, round(v * 8) / 8)


def fx_police(i, n, t):
    flip = int(t / 0.4) % 2
    return RED if (i + flip) % 2 else Color(0, 40, 255)


def fx_sparkle(i, n, t):
    frame = int(t / 0.3)
    return WHITE if random.Random(frame * 97 + i).random() < 0.2 else Color(0, 0, 60)


def fx_wave(i, n, t):
    v = 0.5 + 0.5 * math.sin(t * 3 - i * 0.9)
    return mix(Color(120, 0, 255), Color(255, 90, 0), round(v * 6) / 6)


class LightShow(Party):
    id, title, want, need = "lightshow", "Light show", 15, 1
    EFFECTS = [("Rainbow", fx_rainbow), ("Comet", fx_comet), ("Breathing", fx_breathe),
               ("Police", fx_police), ("Sparkle", fx_sparkle), ("Wave", fx_wave)]
    EFFECT_TIME = 15    # s per effect
    FRAME = 0.12        # s between frames; only changed colors are sent

    def __init__(self, *args):
        super().__init__(*args)
        self.order, self.flash = [], {}
        self.phase = "order"
        for r in self.displays:
            self.solid(r, Color(40, 40, 40), OFF)
        self.info = f"{len(self.displays)} balls connected."
        self.say("Shake the balls in order along your line, or press Start.")

    def start(self):
        now = time.monotonic()
        if self.phase == "order":
            self.order += [r for r in sorted(self.displays) if r not in self.order]
            self.phase, self.effect = "show", -1
        self.next_effect(now)
        return True

    def next_effect(self, now):
        self.effect = (self.effect + 1) % len(self.EFFECTS)
        self.effect_until, self.next_frame, self.t0 = now + self.EFFECT_TIME, now, now
        self.say(f"Effect: {self.EFFECTS[self.effect][0]}")

    def shake(self, r):
        if self.phase == "order":
            if r in self.order:
                return False
            self.order.append(r)
            self.solid(r, hue(len(self.order) / 15), OFF, label=str(len(self.order)))
            print(f"  {self.names[r]} is ball {len(self.order)}", flush=True)
            if len(self.order) == len(self.displays):
                self.start()
            return True
        self.flash[r] = time.monotonic() + 0.5
        self.solid(r, WHITE, WHITE)
        return True

    def tick(self, now):
        if self.phase != "show" or now < self.next_frame:
            return False
        if now >= self.effect_until:
            self.next_effect(now)
        self.next_frame = now + self.FRAME
        name, fx = self.EFFECTS[self.effect]
        n, t, changed = len(self.order), now - self.t0, False
        for i, r in enumerate(self.order):
            if self.flash.get(r, 0) > now:
                continue
            self.flash.pop(r, None)
            color = fx(i, n, t)
            if hexcolor(color) != hexcolor(self.shown[r]):
                self.solid(r, color, label=str(i + 1))
                changed = True
        return changed


GAMES = {g.id: g for g in (Simon, Mole, Potato, RockPaperScissors, LightShow)}


def read_stdin(commands):
    import sys
    for line in sys.stdin:
        commands.put(line.strip())
    commands.put("eof")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("game", choices=GAMES)
    game_class = GAMES[parser.parse_args().game]
    cfg = tictactoe.load_config()
    with contextlib.ExitStack() as stack:
        robots = tictactoe.connect_robots(cfg, stack, want=game_class.want)
        if len(robots) < game_class.need:
            raise SystemExit(f"{game_class.title} needs at least {game_class.need} robots, "
                             f"{len(robots)} connected.")

        stop = threading.Event()
        for _, api, _ in robots:
            api.set_stabilization(False)        # no motor work when a ball is lifted
            api.set_back_led(OFF)
        names = {r: name for r, (name, _, _) in enumerate(robots)}
        displays = {r: Display(api, toy, stop) for r, (_, api, toy) in enumerate(robots)}
        detectors = {r: ShakeDetector(api) for r, (_, api, _) in enumerate(robots)}
        game = game_class(cfg, names, displays)

        commands = queue.Queue()
        threading.Thread(target=read_stdin, args=(commands,), daemon=True).start()

        def emit():
            print("STATE " + json.dumps(game.state()), flush=True)

        emit()
        try:
            while True:
                changed = False
                for r, det in detectors.items():
                    if det.shaken():
                        changed |= bool(game.shake(r))
                try:
                    cmd = commands.get_nowait()
                except queue.Empty:
                    cmd = None
                if cmd == "eof":
                    break
                if cmd == "start":
                    changed |= bool(game.start())
                elif cmd and cmd.startswith("tap "):
                    with contextlib.suppress(ValueError):
                        r = int(cmd.split()[1]) - 1
                        if r in displays:
                            changed |= bool(game.shake(r))
                elif cmd and cmd.startswith("config "):
                    with contextlib.suppress(ValueError, KeyError):
                        new = json.loads(cmd[len("config "):])
                        cfg["rotation"] = int(new["rotation"]) // 90 * 90 % 360
                        cfg["mirror"] = bool(new["mirror"])
                changed |= bool(game.tick(time.monotonic()))
                if changed:
                    emit()
                time.sleep(0.03)
        except KeyboardInterrupt:
            pass
        finally:
            stop.set()
            for d in displays.values():
                d.thread.join(timeout=3)
            for _, api, toy in robots:
                with contextlib.suppress(Exception):
                    indicators.clear(api, toy)
                    api.set_front_led(OFF)
                    api.set_stabilization(True)
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped.")
