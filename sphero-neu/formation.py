"""
Follow the leader and drive home, based on each robot's locator.

Every robot measures its own position (cm) from its start point. The start
points are known (a line, SPACING cm apart), so all positions can be put in one
shared floor frame:

    x: to the right, y: forward (away from you), robot 1 starts at (0, 0).

This only works if the locator axes follow the aim. Call prepare_locator()
right after reset_aim().

Right of way: a robot waits while a lower-numbered robot is closer than
MIN_GAP. Robot 1 never waits, so the robots cannot block each other forever.
"""

import collections
import math
import threading
import time

SPACING = 15        # cm between the start points (robots stand close together)
TICK = 0.15         # s, control loop period (sensor data arrives every 150 ms)
MIN_GAP = 12        # cm, center to center, wait while a robot with right of way is closer
DELAY = 1.5         # s, a follower drives to where the robot ahead was DELAY ago
MAX_SPEED = 60
MIN_SPEED = 20
GAIN = 1.2          # speed per cm of distance to the target
ARRIVED = 6         # cm, close enough to a target point

HOME_ZONE = 20      # cm, near its own start point a robot does not wait for others

# Leader path in the floor frame (cm). A loop in front of the line,
# centered on the middle robot.
LEADER_PATH = [(SPACING + dx, y) for dx, y in ((-80, 80), (0, 160), (80, 80), (0, 40))]


def prepare_locator(toy):
    """Locator axes follow the aim, and the current position becomes (0, 0)."""
    toy.set_locator_flags(True)
    toy.reset_locator_x_and_y()


class Tracker:
    """Shared positions of all robots in the floor frame, with a short history."""

    def __init__(self):
        self._lock = threading.Lock()
        self._history = collections.defaultdict(lambda: collections.deque(maxlen=200))

    def update(self, index, api):
        loc = api.get_location()
        if loc is None:
            return None
        pos = (loc["x"] + index * SPACING, loc["y"])
        with self._lock:
            self._history[index].append((time.monotonic(), pos))
        return pos

    def now(self, index):
        with self._lock:
            h = self._history.get(index)
            return h[-1][1] if h else None

    def ago(self, index, seconds):
        """Position of robot `index` about `seconds` ago (oldest known if earlier)."""
        cutoff = time.monotonic() - seconds
        with self._lock:
            h = self._history.get(index)
            if not h:
                return None
            pos = h[0][1]
            for t, p in h:
                if t > cutoff:
                    break
                pos = p
            return pos

    def blocked(self, index, pos):
        """True if a robot with right of way (lower number) is too close."""
        for other in range(index):
            p = self.now(other)
            if p is not None and math.dist(p, pos) < MIN_GAP:
                return True
        return False


class Driver:
    """Closed-loop driving of one robot towards points in the floor frame."""

    def __init__(self, api, index, tracker, stop):
        self.api = api
        self.index = index
        self.tracker = tracker
        self.stop = stop
        self._heading = None
        self._speed = 0

    def home(self):
        return (self.index * SPACING, 0)

    def _send(self, heading, speed):
        if self._heading is None or abs((heading - self._heading + 180) % 360 - 180) > 4:
            self.api.set_heading(heading)
            self._heading = heading
        if speed != self._speed:
            self.api.set_speed(speed)
            self._speed = speed

    def halt(self):
        self.api.stop_roll()
        self._speed = 0

    def step(self, target, slow_down=True, yield_way=True):
        """One control step towards target. Returns the distance left, or None."""
        pos = self.tracker.update(self.index, self.api)
        if pos is None:
            return None
        dx, dy = target[0] - pos[0], target[1] - pos[1]
        dist = math.hypot(dx, dy)
        if dist < ARRIVED or (yield_way and self.tracker.blocked(self.index, pos)):
            if self._speed:
                self.api.set_speed(0)
                self._speed = 0
            return dist
        heading = round(math.degrees(math.atan2(dx, dy))) % 360
        speed = MAX_SPEED
        if slow_down:
            speed = max(MIN_SPEED, min(MAX_SPEED, round(dist * GAIN)))
        self._send(heading, speed)
        return dist

    def _running(self, until):
        return not self.stop.is_set() and time.monotonic() < until

    def lead(self, until, laps=2):
        """Robot 1: drive the leader path `laps` times, or until the deadline."""
        path = LEADER_PATH * laps
        i = 0
        while self._running(until) and i < len(path):
            dist = self.step(path[i], slow_down=(i == len(path) - 1))
            if dist is not None and dist < 15:
                i += 1
            time.sleep(TICK)
        self.halt()

    def follow(self, ahead, until):
        """Drive to where robot `ahead` was DELAY seconds ago, until the deadline."""
        while self._running(until):
            target = self.tracker.ago(ahead, DELAY)
            if target is None:
                self.tracker.update(self.index, self.api)
            else:
                self.step(target)          # waits while `ahead` is too close
            time.sleep(TICK)
        self.halt()

    def go_home(self, until):
        """Drive back to the start point and face forward. True if it arrived."""
        arrived = False
        while self._running(until):
            pos = self.tracker.now(self.index)
            near = pos is not None and math.dist(pos, self.home()) < HOME_ZONE
            dist = self.step(self.home(), yield_way=not near)
            if dist is not None and dist < ARRIVED:
                arrived = True
                break
            time.sleep(TICK)
        self.halt()
        self.api.set_heading(0)
        self._heading = 0
        return arrived
