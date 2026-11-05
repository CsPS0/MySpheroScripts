"""
Arrow on the BOLT matrix and the white front LED.

show_front():  arrow points to the front of the robot (used while aiming).
NorthArrow:    keeps the arrow pointing to one floor direction (ARROW_POINTS,
               default west = to your left) while the robot turns. Directions
               are seen from you after aiming: 0 away from you, 90 right,
               180 towards you, 270 left. The matrix turns with the
               robot, so the arrow is redrawn turned the other way. The 8x8
               matrix allows 8 directions, in 45 degree steps. It is redrawn
               only after the direction stayed the same for SETTLE seconds.

Clearing: the "whole matrix one color" command does not erase shapes drawn with
fill commands, so the matrix is cleared with a black fill over all 8x8 LEDs.
The front LED is fixed to the robot and always marks its real front.

The arrow is drawn row by row with a few fill commands (not 64 pixel commands).
spherov2 0.12.1 does not declare the fill command for the BOLT, so it is sent
directly. Each command is retried (a lost Bluetooth reply makes it time out);
if the robot refuses a fill, that row is drawn pixel by pixel.

Settings to check on the real robots:
  ARROW_TO    if the front arrow points the wrong way.
  NORTH_TURN  if the north arrow turns the wrong way (1 or -1).
"""

import threading
import time

from spherov2.commands.io import IO
from spherov2.controls.v2 import Processors
from spherov2.types import Color

FRONT_LED = Color(255, 255, 255)
ARROW_TO = "bottom"  # matrix side that faces the front LED: top, bottom, left, right
NORTH_TURN = 1       # 1 or -1: direction the arrow turns against the robot's turn
ARROW_POINTS = 270   # floor direction of the NorthArrow: 0 away from you, 90 right, 270 left (west)
SETTLE = 0.25        # s, the heading must stay this long before the arrow is redrawn

# Arrow pointing to the top of the matrix. X = LED on.
ARROW = [
    "...XX...",
    "..XXXX..",
    ".XXXXXX.",
    "XXXXXXXX",
    "...XX...",
    "...XX...",
    "...XX...",
    "...XX...",
]

# Arrow pointing to the top right corner.
ARROW_DIAGONAL = [
    "...XXXXX",
    "....XXXX",
    ".....XXX",
    "....XXXX",
    "...XXX.X",
    "..XXX...",
    ".XXX....",
    "XXX.....",
]

# Letters, top of the letter at the top of the matrix. X = LED on.
LETTERS = {
    "N": ["XX....XX",
          "XXX...XX",
          "XXXX..XX",
          "XX.XX.XX",
          "XX..XXXX",
          "XX...XXX",
          "XX....XX",
          "XX....XX"],
    "E": ["XXXXXXXX",
          "XXXXXXXX",
          "XX......",
          "XXXXXX..",
          "XXXXXX..",
          "XX......",
          "XXXXXXXX",
          "XXXXXXXX"],
    "U": ["XX....XX",
          "XX....XX",
          "XX....XX",
          "XX....XX",
          "XX....XX",
          "XX....XX",
          "XXXXXXXX",
          ".XXXXXX."],
    "M": ["XX....XX",
          "XXX..XXX",
          "XXXXXXXX",
          "XX.XX.XX",
          "XX....XX",
          "XX....XX",
          "XX....XX",
          "XX....XX"],
    "A": ["..XXXX..",
          ".XXXXXX.",
          "XX....XX",
          "XX....XX",
          "XXXXXXXX",
          "XXXXXXXX",
          "XX....XX",
          "XX....XX"],
}
LETTER_MIRROR = False   # True if N and E show mirrored

# Small 3x5 digits, so numbers up to 99 fit on the 8x8 matrix (see number_bitmap).
DIGITS = {
    "0": ["XXX", "X.X", "X.X", "X.X", "XXX"],
    "1": [".X.", "XX.", ".X.", ".X.", "XXX"],
    "2": ["XXX", "..X", "XXX", "X..", "XXX"],
    "3": ["XXX", "..X", ".XX", "..X", "XXX"],
    "4": ["X.X", "X.X", "XXX", "..X", "..X"],
    "5": ["XXX", "X..", "XXX", "..X", "XXX"],
    "6": ["XXX", "X..", "XXX", "X.X", "XXX"],
    "7": ["XXX", "..X", ".X.", ".X.", ".X."],
    "8": ["XXX", "X.X", "XXX", "X.X", "XXX"],
    "9": ["XXX", "X.X", "XXX", "..X", "XXX"],
}

# The BOLT matrix shows bitmaps mirrored, and upright for someone standing
# behind the robot (blue tail light towards them) needs a half turn. Seen on the
# real robots: N needed rotation 180 + mirror.
UPRIGHT = {"rotation": 180, "mirror": True}


def number_bitmap(number):
    """8x8 bitmap (8 strings) of a 1 or 2 digit number, centered."""
    digits = str(number)[-2:]
    rows = ["........"] * 8
    if len(digits) == 1:
        glyphs, starts = [DIGITS[digits]], [2]
    else:
        glyphs, starts = [DIGITS[d] for d in digits], [0, 4]
    rows = [list(r) for r in rows]
    for glyph, x0 in zip(glyphs, starts):
        for y, line in enumerate(glyph):
            for x, ch in enumerate(line):
                rows[y + 1][x0 + x] = ch
    return ["".join(r) for r in rows]

SIDE_ANGLE = {"top": 0, "right": 90, "bottom": 180, "left": 270}


def _turn(grid, quarter_turns):
    """Rotates a grid by quarter_turns x 90 degrees clockwise."""
    grid = [list(r) for r in grid]
    for _ in range(quarter_turns % 4):
        grid = [list(row) for row in zip(*grid[::-1])]
    return grid


def _grid_for(matrix_angle):
    """Arrow grid pointing to matrix_angle (degrees clockwise from the top)."""
    step = round(matrix_angle / 45) % 8
    base = ARROW if step % 2 == 0 else ARROW_DIAGONAL
    return _turn(base, step // 2)


def _rotated(rows, side):
    return _turn(rows, SIDE_ANGLE[side] // 90)


def _runs(grid):
    """Yields (x1, x2, y) for each horizontal run of lit pixels."""
    for y, row in enumerate(grid):
        x = 0
        while x < len(row):
            if row[x] == "X":
                start = x
                while x < len(row) and row[x] == "X":
                    x += 1
                yield start, x - 1, y
            else:
                x += 1


def _fill(toy, x1, y1, x2, y2, color):
    IO.draw_compressed_frame_player_fill(
        toy, x1, y1, x2, y2, color.r, color.g, color.b, proc=Processors.SECONDARY)


def clear(api, toy=None):
    """Matrix off."""
    api.clear_matrix()
    api.set_main_led(Color(0, 0, 0))
    if toy is not None:
        _retry(lambda: _fill(toy, 0, 0, 7, 7, Color(0, 0, 0)))


def _pixel(toy, x, y, color):
    IO.set_compressed_frame_player_pixel(
        toy, x, y, color.r, color.g, color.b, proc=Processors.SECONDARY)


def _retry(command, tries=3):
    """Runs command(); a lost Bluetooth reply makes single commands time out."""
    for attempt in range(tries):
        try:
            return command()
        except Exception:
            if attempt == tries - 1:
                raise


def fill_all(toy, color):
    """Whole matrix in one color: a single command, much faster than a shape."""
    _retry(lambda: _fill(toy, 0, 0, 7, 7, color))


def _draw(api, toy, color, grid):
    _retry(lambda: _fill(toy, 0, 0, 7, 7, Color(0, 0, 0)))
    for x1, x2, y in _runs(grid):
        try:
            _retry(lambda: _fill(toy, x1, y, x2, y, color))
        except Exception:                      # fill refused: pixel by pixel
            for x in range(x1, x2 + 1):
                _retry(lambda: _pixel(toy, x, y, color))


def north_matrix_angle(heading, target=None):
    """Matrix angle of floor direction `target` (default ARROW_POINTS) when the
    robot drives at `heading`. 0 = away from you."""
    target = ARROW_POINTS if target is None else target
    return SIDE_ANGLE[ARROW_TO] + NORTH_TURN * (target - heading)


def show_bitmap(api, toy, rows, color, rotation=0, mirror=False):
    """Draws an 8x8 bitmap (8 strings, X = on). Without rotation its top is at
    the top of the matrix (the robot's tail side, see ARROW_TO). mirror flips it
    left-right, then it is turned by rotation degrees (0, 90, 180, 270)
    clockwise on the matrix."""
    if mirror != LETTER_MIRROR:
        rows = [r[::-1] for r in rows]
    api.clear_matrix()
    _draw(api, toy, color, _turn(rows, rotation // 90))


def show_letter(api, toy, letter, color, rotation=0, mirror=False):
    """Draws a letter from LETTERS, see show_bitmap()."""
    show_bitmap(api, toy, LETTERS[letter], color, rotation, mirror)


def show_front(api, toy, color):
    """Arrow in `color` pointing to the front, front LED white."""
    api.clear_matrix()
    _draw(api, toy, color, _rotated(ARROW, ARROW_TO))
    api.set_front_led(FRONT_LED)


class NorthArrow:
    """
    Keeps the arrow pointing to get_target() (default ARROW_POINTS, west). get_heading() returns the robot's current
    heading. Runs in its own thread, so driving commands are not held up, and
    redraws only after the heading stayed the same for SETTLE seconds.
    """

    def __init__(self, api, toy, color, get_heading, stop, tick=0.05, get_target=None):
        self.api, self.toy, self.color = api, toy, color
        self.get_heading = get_heading
        self.get_target = get_target or (lambda: ARROW_POINTS)   # floor direction to point at
        self.stop = stop
        self.tick = tick
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()
        return self

    def _run(self):
        self.api.clear_matrix()
        self.api.set_front_led(FRONT_LED)
        shown, candidate, since = None, None, 0.0
        while not self.stop.is_set():
            step = round(north_matrix_angle(self.get_heading(), self.get_target()) / 45) % 8
            now = time.monotonic()
            if step != candidate:
                candidate, since = step, now
            if step != shown and (shown is None or now - since >= SETTLE):
                try:
                    _draw(self.api, self.toy, self.color, _grid_for(step * 45))
                    shown = step
                except Exception as e:
                    print(f"  arrow: {type(e).__name__}, retrying", flush=True)
            self.stop.wait(self.tick)
