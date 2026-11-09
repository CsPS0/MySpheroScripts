"""
Web control for the Sphero programs. Runs one program at a time as a
subprocess, streams its output to the browser and forwards drive keys.

    uvicorn web.server:app --host 0.0.0.0 --port 8080     (from the project folder)
"""

import asyncio
import collections
import contextlib
import hashlib
import hmac
import json
import os
import secrets
import signal
import subprocess
import sys
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
import letters  # noqa: E402  (project module, shared with the robot programs)
import sphero_ble  # noqa: E402
import tictactoe  # noqa: E402

STATIC = PROJECT_ROOT if (PROJECT_ROOT / "index.html").exists() else Path(__file__).resolve().parent / "static"
ASSETS_DIR = PROJECT_ROOT / "assets" if (PROJECT_ROOT / "assets").exists() else STATIC / "assets"
ROBOT_NAMES = ["BOLT-1", "BOLT-2", "BOLT-3"]

PROGRAMS = {
    "dance": {
        "title": "Dance Show",
        "description": "All free robots (up to 15) in a numbered line: rainbow wave with "
                       "random turns, a rush with explosions on collisions, random "
                       "characters and little dances, then back home. About 4 minutes.",
        "args": ["big_dance.py"],
        "moves": True,
        "game": True,          # stdin "start": Go after the setup, then next part
    },
    "drive": {
        "title": "Joystick Drive",
        "description": "Smooth remote control driving with the virtual joystick! Zero lag, "
                       "real-time heading & speed steering.",
        "args": ["drive_keys.py", "--stdin", "--robots", "1,2,3"],   # set per start()
        "moves": True,
        "joystick": True,
    },
    "roam": {
        "title": "Autonomous Roam",
        "description": "All available robots (up to 15) wander around their own start spot "
                       "(25 cm circle) until you press Stop, then drive back home.",
        "args": ["roam.py", "--radius", "25"],
        "moves": True,
    },
    "neu": {
        "title": "Neumann Formation",
        "description": "Robots 1-7 in a row show N, E, U, M, A, N, N, one letter each. "
                       "After aiming they turn to the same heading. Holds until Stop.",
        "args": ["neu.py"],
        "moves": True,
        "letters": True,
    },
    "tictactoe": {
        "title": "Tic-tac-toe",
        "description": "Connects the 9 nearest free BOLTs. They show 1 to 9: put them in a "
                       "3x3 grid. Shake a ball to take that square, X always starts.",
        "args": ["tictactoe.py"],
        "moves": False,
        "game": True,
    },
    "simon": {
        "title": "Memory game",
        "description": "Balls light up in a sequence with musical tones: shake/tap them "
                       "back in the same order. One more step each level.",
        "args": ["minigames.py", "simon"],
        "moves": False,
        "game": True,
    },
    "mole": {
        "title": "Whack-a-mole",
        "description": "A random ball turns neon green: tap/shake it before it goes dark! "
                       "60 s reflex challenge with fast pop sounds.",
        "args": ["minigames.py", "mole"],
        "moves": False,
        "game": True,
    },
    "potato": {
        "title": "Hot potato",
        "description": "1 ball. Shake/tap to light the fuse and pass it around! It blinks "
                       "faster and faster, then EXPLODES with a loud boom & scream!",
        "args": ["minigames.py", "potato"],
        "moves": False,
        "game": True,
    },
    "rps": {
        "title": "Rock-paper-scissors",
        "description": "2 balls (Red vs Blue). 3-2-1 countdown, then each ball reveals "
                       "rock, paper or scissors on its matrix. First to 2 wins!",
        "args": ["minigames.py", "rps"],
        "moves": False,
        "game": True,
    },
}

DRIVE_KEYS = {"KeyW", "KeyA", "KeyS", "KeyD", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"}
STOP_GRACE = 30     # seconds after Ctrl+C before the program is terminated (9 robots need ~20 s to clean up)


def _color(r, g, b, hu, en):
    return {"r": r, "g": g, "b": b, "hex": f"#{r:02x}{g:02x}{b:02x}", "name": hu, "en": en}


# Robot number -> display color. 1-3 are the phone controller slots (red, green, blue).
ROBOT_COLORS = {
    1: _color(255, 59, 59, "Piros", "Red"),
    2: _color(46, 204, 113, "Zöld", "Green"),
    3: _color(52, 152, 219, "Kék", "Blue"),
    4: _color(241, 196, 15, "Sárga", "Yellow"),
    5: _color(232, 67, 147, "Rózsaszín", "Pink"),
    6: _color(0, 206, 201, "Türkiz", "Teal"),
    7: _color(230, 126, 34, "Narancs", "Orange"),
    8: _color(155, 89, 182, "Lila", "Purple"),
    9: _color(255, 255, 255, "Fehér", "White"),
    10: _color(163, 230, 53, "Lime", "Lime"),
    11: _color(250, 128, 114, "Lazac", "Salmon"),
    12: _color(99, 110, 250, "Indigó", "Indigo"),
    13: _color(253, 203, 110, "Barack", "Peach"),
    14: _color(85, 239, 196, "Menta", "Mint"),
    15: _color(214, 48, 49, "Bordó", "Crimson"),
}


def robot_color(number):
    if number in ROBOT_COLORS:
        return ROBOT_COLORS[number]
    keys = sorted(ROBOT_COLORS)
    return ROBOT_COLORS[keys[(number - 1) % len(keys)]]


def battery_percent(voltage):
    """Rough LiPo charge estimate for a BOLT: 3.5 V empty, 4.2 V full."""
    return max(0, min(100, round((voltage - 3.5) / 0.7 * 100)))


class Runner:
    def __init__(self):
        self.proc = None
        self.program = None
        self.started = None
        self.last_exit = None          # (program, exit code)
        self.log = collections.deque(maxlen=1500)
        self.clients = set()
        self.client_meta = {}          # ws -> {"id": cid, "ip": ip, "connected_at": t, "last_active": t, "role": role, "slot": None}
        self.client_counter = 0
        self.max_controllers = int(os.environ.get("MAX_CONTROLLERS", "3"))
        self.idle_timeout = int(os.environ.get("IDLE_TIMEOUT", "300"))        # 5 minutes default
        self.keys = {}                 # websocket -> (set of key codes, turbo)
        self.game = None               # latest tic-tac-toe state
        self.telemetry = None          # latest 2D arena telemetry
        self.robots = []               # list of robot dicts in pool
        self.auto_map_on_connect = True # auto switch/focus map on laptop screen when phone connects
        # real robots by default; SPHERO_SIM=1 forces simulation, no Bluetooth adapter implies it
        self.simulation = os.environ.get("SPHERO_SIM", "0").lower() in ("1", "true", "yes")
        if not sphero_ble.has_bluetooth_adapter():
            self.simulation = True
        self.low_spec = os.environ.get("LOW_SPEC", "0").lower() in ("1", "true", "yes")
        self.lock = asyncio.Lock()
        self.identify_lock = asyncio.Lock()
        # robot number -> forward heading (degrees) for Drive, see drive_keys.Driven.
        # Reset when Drive starts: the aim phase sets a new zero heading.
        self.calibration = {}

    def get_robot_pool(self):
        return self.robots

    async def broadcast_robot_pool(self):
        await self.broadcast({"type": "robot_pool", "robots": self.get_robot_pool()})

    def _robot_entry(self, number, raw_name, address, voltage=None):
        return {
            "id": number,
            "name": f"BOLT-{number} ({raw_name})",
            "raw_name": raw_name,
            "address": address,
            "battery": battery_percent(voltage) if voltage is not None else None,
            "voltage": round(voltage, 2) if voltage is not None else None,
            "status": "ready",
            "slot": None,
            "client_id": None,
            "color": robot_color(number),
        }

    async def init_robot_pool(self):
        """Scans for BOLTs and numbers them 1..N, nearest first. Keeps the phone
        assignments of robots that are still present."""
        previous = {r["address"]: r for r in self.robots}
        robots = []
        cache_map = {}
        try:
            if self.simulation:
                import sphero_sim
                sim = sphero_sim.SimulatorManager.get()
                for number, spec in enumerate(sphero_sim.DEFAULT_ROBOT_SPECS, start=1):
                    toy = sim.get_toy(spec[0])
                    robots.append(self._robot_entry(number, toy.name, toy.address,
                                                    toy.get_battery_voltage()))
            else:
                found = await asyncio.to_thread(sphero_ble.scan_bolts, 4.0)
                if sphero_ble.is_simulation():
                    self.simulation = True
                for number, item in enumerate(found, start=1):
                    robots.append(self._robot_entry(number, item[0], item[1]))
        except Exception as e:
            await self.add_line(f"Robot keresési hiba / scan error: {e}")
            if not self.simulation:
                self.simulation = True
                sphero_ble.set_simulation(True)
                with contextlib.suppress(Exception):
                    import sphero_sim
                    sim = sphero_sim.SimulatorManager.get()
                    for number, spec in enumerate(sphero_sim.DEFAULT_ROBOT_SPECS, start=1):
                        toy = sim.get_toy(spec[0])
                        robots.append(self._robot_entry(number, toy.name, toy.address,
                                                        toy.get_battery_voltage()))

        for r in robots:
            cache_map[r["raw_name"]] = r["address"]
            cache_map[f"BOLT-{r['id']}"] = r["address"]
            old = previous.get(r["address"])
            if old:
                for key in ("slot", "client_id", "status"):
                    r[key] = old[key]
                if r["battery"] is None:
                    r["battery"], r["voltage"] = old["battery"], old["voltage"]
        self.robots = robots
        sphero_ble.save_cached_bolts(cache_map)

        mode = " [szimuláció]" if self.simulation else ""
        if robots:
            await self.add_line(f"Robotok: {len(robots)} BOLT megtalálva{mode}.")
        else:
            await self.add_line("Nem található robot. Rázd fel a BOLT-okat, majd nyomd meg az Újrakeresés gombot.")
        await self.broadcast_robot_pool()

    async def assign_controller(self, ws, cid):
        """Gives the phone the lowest free slot. Slot n drives robot n, which shows
        the number n in the slot color on its matrix."""
        used = {m.get("slot") for w, m in self.client_meta.items()
                if w is not ws and m.get("role") == "controller"}
        slot_num = next(n for n in range(1, self.max_controllers + 2) if n not in used)
        self.client_meta[ws]["slot"] = slot_num
        col = robot_color(slot_num)

        robot = next((r for r in self.robots if r["id"] == slot_num), None)
        if robot:
            robot["slot"] = slot_num
            robot["client_id"] = cid
            robot["status"] = "assigned"
            if self.simulation:
                with contextlib.suppress(Exception):
                    import sphero_sim
                    from spherov2.types import Color
                    toy = sphero_sim.SimulatorManager.get().get_toy(robot["raw_name"])
                    c = Color(col["r"], col["g"], col["b"])
                    toy.set_matrix_character(str(slot_num), c)
                    toy.front_led = c

        await self.broadcast_robot_pool()
        await self.add_line(f"Telefon {slot_num} csatlakozott -> {slot_num}. robot ({col['name']}).")
        return {
            "slot": slot_num,
            "robot_name": robot["name"] if robot else f"BOLT-{slot_num}",
            "color": col,
        }

    async def release_controller(self, cid):
        released_slot = None
        for r in self.robots:
            if r.get("client_id") == cid:
                released_slot = r.get("slot")
                r["slot"] = None
                r["client_id"] = None
                r["status"] = "ready"
                if self.simulation:
                    with contextlib.suppress(Exception):
                        import sphero_sim
                        from spherov2.types import Color
                        toy = sphero_sim.SimulatorManager.get().get_toy(r["raw_name"])
                        toy.clear_matrix()
                        toy.front_led = Color(0, 0, 0)
                break
        await self.broadcast_robot_pool()
        if released_slot:
            await self.add_line(f"Telefon {released_slot} levált, a(z) {released_slot}. robot újra szabad.")

    async def identify_robot(self, robot_id: int):
        """Shows the robot's number in its color and turns the headlight white for a
        few seconds. On real hardware it also reads the battery voltage."""
        r = next((x for x in self.robots if x["id"] == robot_id), None)
        if r is None:
            return False
        col = r["color"]
        if self.simulation:
            with contextlib.suppress(Exception):
                import sphero_sim
                from spherov2.types import Color
                toy = sphero_sim.SimulatorManager.get().get_toy(r["raw_name"])
                toy.set_matrix_character(str(robot_id), Color(col["r"], col["g"], col["b"]))
                toy.front_led = Color(255, 255, 255)
            await self.add_line(f"Azonosítás: {robot_id}. robot ({col['name']}).")
            return True
        if self.proc is not None:
            await self.add_line(f"Azonosítás nem lehetséges, amíg program fut (robot {robot_id}). Előbb állítsd le.")
            return False
        async with self.identify_lock:
            await self.add_line(f"Azonosítás: {robot_id}. robot ({r['raw_name']}) csatlakozás...")
            try:
                voltage = await asyncio.to_thread(identify_bolt, r["raw_name"], robot_id, col)
            except Exception as e:
                await self.add_line(f"Azonosítás sikertelen ({r['raw_name']}): {type(e).__name__}: {e}")
                return False
        if voltage:
            r["voltage"] = round(voltage, 2)
            r["battery"] = battery_percent(voltage)
            await self.broadcast_robot_pool()
        await self.add_line(f"Azonosítás kész: {robot_id}. robot"
                            + (f", akku {r['battery']}% ({r['voltage']} V)." if voltage else "."))
        return True

    async def set_calibration(self, robot, offset):
        self.calibration[robot] = int(round(offset)) % 360
        await self.send_line(f"calib {robot} {self.calibration[robot]}\n", "joystick")
        await self.broadcast({"type": "calibration", "offsets": self.calibration})

    def get_controller_list(self):
        now = time.time()
        res = []
        for ws, meta in self.client_meta.items():
            if meta.get("role") == "controller":
                res.append({
                    "id": meta["id"],
                    "ip": meta["ip"],
                    "slot": meta.get("slot"),
                    "connected_at": meta["connected_at"],
                    "idle": int(now - meta["last_active"]),
                })
        return sorted(res, key=lambda c: c["slot"] or 99)

    async def broadcast_clients(self):
        msg = {
            "type": "clients",
            "clients": self.get_controller_list(),
            "max": self.max_controllers,
        }
        await self.broadcast(msg)

    async def kick_client(self, client_id: str):
        target_ws = None
        target_meta = None
        for ws, meta in list(self.client_meta.items()):
            if meta.get("id") == client_id:
                target_ws = ws
                target_meta = meta
                break
        if target_ws:
            with contextlib.suppress(Exception):
                await target_ws.send_json({
                    "type": "kicked",
                    "code": "KICKED",
                    "message": "A bemutató vezetője bontotta a kapcsolatot. / Disconnected by host.",
                })
                await target_ws.close(code=1000)
            self.clients.discard(target_ws)
            self.client_meta.pop(target_ws, None)
            self.keys.pop(target_ws, None)
            await self.release_controller(client_id)
            await self.send_keys()
            await self.broadcast_clients()
            await self.add_line(f"Eszköz lekapcsolva a gazda által: {target_meta.get('ip', client_id)}")
            return True
        return False

    async def watchdog(self):
        while True:
            await asyncio.sleep(5)
            now = time.time()
            to_kick = []
            for ws, meta in list(self.client_meta.items()):
                if meta.get("role") == "controller" and (now - meta.get("last_active", now)) > self.idle_timeout:
                    to_kick.append((ws, meta))
            for ws, meta in to_kick:
                with contextlib.suppress(Exception):
                    await ws.send_json({
                        "type": "timeout",
                        "code": "TIMEOUT",
                        "message": "5 perc inaktivitás miatt a kapcsolat bontva, hogy más is játszhasson! / Disconnected due to 5 min inactivity.",
                    })
                    await ws.close(code=1000)
                self.clients.discard(ws)
                self.client_meta.pop(ws, None)
                self.keys.pop(ws, None)
                await self.release_controller(meta["id"])
                await self.add_line(f"Eszköz lekapcsolva inaktivitás miatt (5 perc): {meta.get('ip')}")
            if to_kick:
                await self.send_keys()
                await self.broadcast_clients()

    def status(self):
        return {
            "type": "status",
            "running": self.program,
            "started": self.started,
            "last_exit": self.last_exit,
            "simulation": self.simulation,
            "low_spec": self.low_spec,
        }

    def get_current_telemetry(self):
        if self.telemetry is not None:
            return self.telemetry
        try:
            from sphero_sim import DEFAULT_ROBOT_SPECS, hex_color
            res = {"robots": []}
            for name, _, hx, hy, col in DEFAULT_ROBOT_SPECS[:3]:
                res["robots"].append({
                    "name": name, "x": hx, "y": hy, "heading": 0.0, "speed": 0.0,
                    "front_led": "#ffffff", "back_led": "#0000ff",
                    "matrix": [[hex_color(col.r, col.g, col.b) if (r in (0, 7) or c in (0, 7)) else "#000000"
                                for c in range(8)] for r in range(8)],
                })
            return res
        except Exception:
            return {"robots": []}

    async def broadcast(self, message):
        for ws in list(self.clients):
            try:
                await ws.send_json(message)
            except Exception:
                self.clients.discard(ws)

    async def add_line(self, line):
        entry = {"type": "log", "line": line, "t": time.time()}
        self.log.append(entry)
        await self.broadcast(entry)

    async def start(self, program_id):
        async with self.lock:
            await self._stop()
            spec = PROGRAMS[program_id]
            args = list(spec["args"])
            if program_id == "drive":
                count = max(1, min(3, self.max_controllers, len(self.robots) or 1))
                args = ["drive_keys.py", "--stdin", "--robots", ",".join(str(n) for n in range(1, count + 1))]
            mode_tag = " [SIMULATION]" if self.simulation else ""
            await self.add_line(f"=== Start: {spec['title']}{mode_tag} ===")
            await self._release()

            env = {**os.environ, "PYTHONUNBUFFERED": "1"}
            if self.simulation:
                env["SPHERO_SIM"] = "1"
                env["SPHERO_PROGRAM"] = program_id
                party_layout = load_minigames().get(program_id, {}).get("layout", "3x3") if program_id in ("simon", "mole") else "3x3"
                with contextlib.suppress(Exception):
                    import sphero_sim
                    sphero_sim.SimulatorManager.get().apply_layout(program_id, count=len(self.robots) or 9, layout=party_layout)

            venv_sub = "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
            if (ROOT / ".venv" / venv_sub).exists():
                python_exec = str(ROOT / ".venv" / venv_sub)
            elif (PROJECT_ROOT / ".venv" / venv_sub).exists():
                python_exec = str(PROJECT_ROOT / ".venv" / venv_sub)
            else:
                python_exec = sys.executable
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            start_new_session = (sys.platform != "win32")

            self.proc = await asyncio.create_subprocess_exec(
                python_exec, "-u", *args,
                cwd=ROOT,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                start_new_session=start_new_session,
                creationflags=creationflags,
                env=env,
            )
            self.program = program_id
            self.started = time.time()
            asyncio.create_task(self._read(self.proc, program_id))
            if program_id == "drive":
                self.calibration = {}
                await self.broadcast({"type": "calibration", "offsets": {}})
            await self.broadcast(self.status())

    async def stop(self):
        async with self.lock:
            await self._stop()

    async def _stop(self):
        proc = self.proc
        if proc is None or proc.returncode is not None:
            return
        await self.add_line("=== Stopping (Ctrl+C) ===")
        sig_kill = getattr(signal, "SIGKILL", signal.SIGTERM)
        for sig, wait in ((signal.SIGINT, STOP_GRACE), (signal.SIGTERM, 3), (sig_kill, 3)):
            try:
                if hasattr(os, "killpg") and sys.platform != "win32":
                    os.killpg(proc.pid, sig)
                elif sys.platform == "win32":
                    if sig == signal.SIGINT:
                        try:
                            proc.send_signal(signal.CTRL_BREAK_EVENT)
                        except Exception:
                            proc.terminate()
                    else:
                        proc.terminate()
                else:
                    proc.terminate()
            except ProcessLookupError:
                break
            except Exception:
                try:
                    proc.terminate()
                except Exception:
                    pass
                break
            try:
                await asyncio.wait_for(proc.wait(), wait)
                break
            except asyncio.TimeoutError:
                await self.add_line(f"=== No reaction to {getattr(sig, 'name', str(sig))} ===")
        await self._release()
        # _read() reports the exit

    async def _release(self):
        """Disconnects robots a killed program left connected (they block slots)."""
        lines = []
        with contextlib.suppress(Exception):
            await asyncio.to_thread(sphero_ble.release_stale, log=lines.append)
        for line in lines:
            await self.add_line(line)

    async def _read(self, proc, program_id):
        buffer = b""
        while True:
            chunk = await proc.stdout.read(1024)
            if not chunk:
                break
            buffer += chunk.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            *lines, buffer = buffer.split(b"\n")
            for line in lines:
                if line.startswith(b"STATE "):
                    try:
                        self.game = json.loads(line[6:])
                        await self.broadcast({"type": "game", "state": self.game})
                    except ValueError:
                        pass
                elif line.startswith(b"TELEMETRY "):
                    try:
                        self.telemetry = json.loads(line[10:])
                        await self.broadcast({"type": "telemetry", "data": self.telemetry})
                    except ValueError:
                        pass
                elif line.strip():
                    await self.add_line(line.decode(errors="replace"))
        if buffer.strip():
            await self.add_line(buffer.decode(errors="replace"))
        code = await proc.wait()
        await self.add_line(f"=== {PROGRAMS[program_id]['title']} ended, exit code {code} ===")
        if self.game is not None and self.proc is proc:
            self.game = None
            await self.broadcast({"type": "game", "state": None})
        if self.proc is proc:
            self.proc = None
            self.program = None
            self.started = None
            self.last_exit = (program_id, code)
            if self.simulation:
                with contextlib.suppress(Exception):
                    import sphero_sim
                    sphero_sim.SimulatorManager.get().apply_layout("default")
            await self.broadcast(self.status())

    async def send_line(self, line, flag):
        """Writes a line to the running program's stdin if it has `flag`."""
        proc = self.proc
        if proc is None or not PROGRAMS[self.program].get(flag) or proc.stdin.is_closing():
            return
        try:
            proc.stdin.write(line.encode())
            await proc.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            pass

    async def send_keys(self):
        """Sends the union of all browsers' pressed keys to the drive program."""
        proc = self.proc
        if proc is None or not PROGRAMS[self.program].get("pads") or proc.stdin.is_closing():
            return
        pressed = set().union(*(k for k, _ in self.keys.values())) if self.keys else set()
        turbo = any(t for _, t in self.keys.values())
        line = f"keys {','.join(sorted(pressed)) or '-'} {int(turbo)}\n"
        try:
            proc.stdin.write(line.encode())
            await proc.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            pass


def identify_bolt(raw_name, number, col, seconds=3.0):
    """Connects to one real BOLT, shows `number` in color `col`, white headlight,
    then clears. Returns the battery voltage or None. Blocking."""
    from spherov2.sphero_edu import SpheroEduAPI
    from spherov2.types import Color
    import indicators
    toy = sphero_ble.find_toy(raw_name, timeout=8.0)
    voltage = None
    with SpheroEduAPI(toy) as api:
        with contextlib.suppress(Exception):
            voltage = float(toy.get_battery_voltage())
        with contextlib.suppress(Exception):
            toy.sensor_control.disable_all()
        # drawn directly: spherov2's set_matrix_character does nothing on a BOLT
        indicators.show_bitmap(api, toy, indicators.number_bitmap(number),
                               Color(col["r"], col["g"], col["b"]), **indicators.UPRIGHT)
        api.set_front_led(Color(255, 255, 255))
        time.sleep(seconds)
        indicators.fill_all(toy, Color(0, 0, 0))
        api.set_front_led(Color(0, 0, 0))
    return voltage


def get_local_ip():
    env_ip = os.environ.get("SPHERO_HOST_IP")
    if env_ip:
        return env_ip
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127.") and not ip.startswith("169.254."):
                return ip
    except Exception:
        pass
    return "127.0.0.1"


# --- Admin access -----------------------------------------------------------
# The laptop itself (localhost) is always admin. Other devices (phones on the
# Wi-Fi) are joystick controllers unless they log in with ADMIN_PASSWORD. The
# login sets a cookie with an HMAC of the password and a random server secret
# (data/admin_secret), so it survives server restarts and stops working when the
# password changes. Note: plain HTTP on the local network, not internet-grade.
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin1234")
ADMIN_COOKIE = "sphero_admin"
LOCAL_IPS = ("127.0.0.1", "localhost", "::1")


def _admin_secret():
    path = ROOT / "data" / "admin_secret"
    try:
        return path.read_bytes()
    except OSError:
        secret = secrets.token_bytes(32)
        with contextlib.suppress(OSError):
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(secret)
            path.chmod(0o600)
        return secret


ADMIN_TOKEN = hmac.new(_admin_secret(), ADMIN_PASSWORD.encode(), hashlib.sha256).hexdigest()


def is_admin(conn):
    """conn: Request or WebSocket."""
    host = conn.client.host if conn.client else ""
    if host in LOCAL_IPS:
        return True
    return hmac.compare_digest(conn.cookies.get(ADMIN_COOKIE, ""), ADMIN_TOKEN)


def require_admin(request: Request):
    if not is_admin(request):
        raise HTTPException(401, "admin login required")


ADMIN = [Depends(require_admin)]

runner = Runner()


@contextlib.asynccontextmanager
async def lifespan(app):
    watchdog_task = asyncio.create_task(runner.watchdog())
    await runner.init_robot_pool()
    yield
    watchdog_task.cancel()
    await runner.stop()        # container stop: let the program stop the robots


app = FastAPI(lifespan=lifespan)

if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
    app.mount("/en/assets", StaticFiles(directory=ASSETS_DIR), name="en_assets")
    app.mount("/hu/assets", StaticFiles(directory=ASSETS_DIR), name="hu_assets")


def get_index_file():
    candidates = [
        PROJECT_ROOT / "index.html",
        STATIC / "index.html",
    ]
    for idx in candidates:
        if idx.exists():
            return idx
    return None


@app.get("/")
@app.get("/index.html")
async def index():
    idx = get_index_file()
    if idx:
        return FileResponse(idx)
    raise HTTPException(404, "index.html not found")


@app.get("/en")
@app.get("/en/")
async def redirect_en():
    return RedirectResponse(url="/?lang=en", status_code=302)


@app.get("/hu")
@app.get("/hu/")
async def redirect_hu():
    return RedirectResponse(url="/?lang=hu", status_code=302)


@app.get("/sw.js")
@app.get("/service-worker.js")
async def unregister_sw():
    content = (
        "self.addEventListener('install', () => self.skipWaiting());\n"
        "self.addEventListener('activate', (event) => {\n"
        "    event.waitUntil(\n"
        "        self.registration.unregister().then(() => self.clients.matchAll())\n"
        "        .then((clients) => { clients.forEach(c => c.navigate('/')); })\n"
        "    );\n"
        "});\n"
    )
    return Response(content=content, media_type="application/javascript")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@app.get("/api/programs")
async def programs():
    return [{"id": k, **{f: v[f] for f in ("title", "description", "moves")},
             "pads": v.get("pads", []), "letters": v.get("letters", False)}
            for k, v in PROGRAMS.items()]


@app.get("/api/letters")
async def get_letters():
    return letters.load()


@app.post("/api/letters", dependencies=ADMIN)
async def change_letters(change: dict):
    """change: {"target": 0..6|"all", "action": "cw"|"ccw"|"mirror"|"left"|"right"|"reset"},
    {"heading": <degrees>}, {"align": "compass"|"aim"} or {"hand": true|false} (hand-turn lock).
    cw/ccw turn the letter on the matrix by 90 degrees, left/right turn that robot by 15."""
    cfg = letters.load()
    if "heading" in change:
        cfg["heading"] = int(change["heading"]) % 360
    elif "hand" in change:
        cfg["hand"] = bool(change["hand"])
    elif "align" in change:
        if change["align"] not in ("compass", "aim"):
            raise HTTPException(400, "unknown align")
        cfg["align"] = change["align"]
    else:
        action, target = change.get("action"), change.get("target")
        indexes = range(len(cfg["letters"])) if target == "all" else [int(target)]
        for index in indexes:
            item = cfg["letters"][index]
            if action == "cw":
                item["rotation"] = (item["rotation"] + 90) % 360
            elif action == "ccw":
                item["rotation"] = (item["rotation"] - 90) % 360
            elif action == "mirror":
                item["mirror"] = not item["mirror"]
            elif action == "left":
                item["turn"] = item["turn"] - 15
            elif action == "right":
                item["turn"] = item["turn"] + 15
            elif action == "reset":                 # back to the default (upright) values
                default = letters.DEFAULT["letters"][index]
                item.update(rotation=default["rotation"], mirror=default["mirror"], turn=default["turn"])
            else:
                raise HTTPException(400, "unknown action")
    letters.save(cfg)
    cfg = letters.load()
    await runner.broadcast({"type": "letters", "config": cfg})
    await runner.send_line(f"letters {json.dumps(cfg)}\n", "letters")
    return cfg


@app.post("/api/start/{program_id}", dependencies=ADMIN)
async def start(program_id: str, request: Request):
    if program_id not in PROGRAMS:
        raise HTTPException(404, "unknown program")
    with contextlib.suppress(Exception):
        body = await request.json()
        if body and isinstance(body, dict) and program_id in ("simon", "mole"):
            cfg = load_minigames()
            cfg[program_id].update(body)
            MINIGAMES_CONFIG.parent.mkdir(exist_ok=True)
            MINIGAMES_CONFIG.write_text(json.dumps(cfg, indent=2))
    await runner.start(program_id)
    return runner.status()


@app.post("/api/stop", dependencies=ADMIN)
async def stop():
    await runner.stop()
    return runner.status()


@app.post("/api/game", dependencies=ADMIN)
async def game(action: dict):
    """{"action": "play", "cell": 1-9}, or "new" (same layout), "recount", "start".
    Party games: {"action": "tap", "cell": n} (like shaking ball n) and "start"."""
    if action.get("action") in ("play", "tap"):
        await runner.send_line(f"{action['action']} {int(action['cell'])}\n", "game")
    elif action.get("action") in ("new", "recount", "start"):
        cfg_update = action.get("config")
        if cfg_update and runner.program in ("simon", "mole"):
            cfg = load_minigames()
            cfg[runner.program].update(cfg_update)
            MINIGAMES_CONFIG.parent.mkdir(exist_ok=True)
            MINIGAMES_CONFIG.write_text(json.dumps(cfg, indent=2))
            await runner.send_line("config " + json.dumps(cfg[runner.program]) + "\n", "game")
        await runner.send_line(action["action"] + "\n", "game")
    else:
        raise HTTPException(400, "unknown action")
    return {"ok": True}


MINIGAMES_CONFIG = ROOT / "data" / "minigames.json"

DEFAULT_MINIGAMES_CONFIG = {
    "simon": {
        "speed": "normal",
        "layout": "3x3",
        "drift": False,
    },
    "mole": {
        "speed": "normal",
        "layout": "3x3",
        "drift": False,
    },
}


def load_minigames():
    try:
        if MINIGAMES_CONFIG.exists():
            data = json.loads(MINIGAMES_CONFIG.read_text())
            cfg = {k: dict(v) for k, v in DEFAULT_MINIGAMES_CONFIG.items()}
            for k, v in data.items():
                if k in cfg and isinstance(v, dict):
                    cfg[k].update(v)
            return cfg
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return {k: dict(v) for k, v in DEFAULT_MINIGAMES_CONFIG.items()}


@app.get("/api/minigames")
async def get_minigames():
    return load_minigames()


@app.post("/api/minigames", dependencies=ADMIN)
async def change_minigames(change: dict):
    """{"game": "simon"|"mole", "config": {"speed": "normal", "layout": "3x3", "drift": false}}"""
    cfg = load_minigames()
    game_id = change.get("game")
    if game_id in cfg and isinstance(change.get("config"), dict):
        cfg[game_id].update(change["config"])
        MINIGAMES_CONFIG.parent.mkdir(exist_ok=True)
        MINIGAMES_CONFIG.write_text(json.dumps(cfg, indent=2))
        await runner.broadcast({"type": "minigames", "config": cfg})
        if runner.program == game_id:
            await runner.send_line("config " + json.dumps(cfg[game_id]) + "\n", "game")
    return cfg


DANCE_CONFIG = ROOT / "data" / "dance.json"


def load_dance():
    try:
        return {"exclude": sorted({int(n) for n in json.loads(DANCE_CONFIG.read_text()).get("exclude", [])})}
    except (OSError, ValueError, TypeError, AttributeError):
        return {"exclude": []}


@app.get("/api/dance")
async def get_dance():
    return load_dance()


@app.post("/api/dance", dependencies=ADMIN)
async def change_dance(change: dict):
    """{"exclude": [robot numbers]} or {"toggle": n}: robots left out of the dance
    (used at the next start)."""
    cfg = load_dance()
    if "exclude" in change:
        cfg["exclude"] = sorted({int(n) for n in change["exclude"]})
    elif "toggle" in change:
        n = int(change["toggle"])
        cfg["exclude"] = sorted(set(cfg["exclude"]) ^ {n})
    DANCE_CONFIG.parent.mkdir(exist_ok=True)
    DANCE_CONFIG.write_text(json.dumps(cfg, indent=2))
    await runner.broadcast({"type": "dance", "config": cfg})
    return cfg


@app.get("/api/tictactoe")
async def get_tictactoe():
    return tictactoe.load_config()


@app.post("/api/tictactoe", dependencies=ADMIN)
async def change_tictactoe(change: dict):
    """{"robots": [9 names]} (used at the next start) or
    {"action": "cw"|"ccw"|"mirror"|"reset"} (applied live)."""
    cfg = tictactoe.load_config()
    if "auto" in change:
        cfg["auto"] = bool(change["auto"])
    elif "robots" in change:
        names = [str(n).strip().upper() for n in change["robots"]][:9]
        cfg["robots"] = names + [""] * (9 - len(names))
    else:
        action = change.get("action")
        if action == "cw":
            cfg["rotation"] = (cfg["rotation"] + 90) % 360
        elif action == "ccw":
            cfg["rotation"] = (cfg["rotation"] - 90) % 360
        elif action == "mirror":
            cfg["mirror"] = not cfg["mirror"]
        elif action == "reset":
            cfg["rotation"], cfg["mirror"] = 0, False
        else:
            raise HTTPException(400, "unknown action")
        await runner.send_line("config " + json.dumps(
            {"rotation": cfg["rotation"], "mirror": cfg["mirror"]}) + "\n", "game")
    tictactoe.CONFIG.parent.mkdir(exist_ok=True)
    tictactoe.CONFIG.write_text(json.dumps(cfg, indent=2))
    cfg = tictactoe.load_config()
    await runner.broadcast({"type": "tictactoe", "config": cfg})
    return cfg


@app.get("/api/sim")
async def get_sim():
    return {"simulation": runner.simulation}


@app.post("/api/sim", dependencies=ADMIN)
async def set_sim(req: dict):
    runner.simulation = bool(req.get("simulation", True))
    await runner.broadcast(runner.status())
    return {"simulation": runner.simulation}


@app.get("/api/sound/scream")
async def sound_scream():
    candidates = [
        ASSETS_DIR / "sounds" / "scream.wav",
        ROOT / "scream.wav",
        STATIC / "assets" / "sounds" / "scream.wav",
        PROJECT_ROOT / "assets" / "sounds" / "scream.wav",
    ]
    for wav in candidates:
        if wav.exists():
            return FileResponse(wav, media_type="audio/wav")
    raise HTTPException(404, "sound not found")


@app.post("/api/shake", dependencies=ADMIN)
async def shake(action: dict):
    """Triggers shake on a robot or cell: {"cell": 1-9} or {"robot": "SB-3FF5"}."""
    cell = action.get("cell")
    robot = action.get("robot")
    if cell is None and robot:
        match = re.search(r"\d+", str(robot))
        if match:
            cell = int(match.group(0))
        else:
            for r in runner.robots:
                if r.get("raw_name") == robot or r.get("name") == robot:
                    cell = r.get("id")
                    break
    if cell is not None:
        await runner.send_line(f"tap {int(cell)}\n", "game")

    if runner.simulation:
        try:
            import sphero_sim
            sim = sphero_sim.SimulatorManager.get()
            if robot:
                sim.get_toy(str(robot)).trigger_shake()
            elif cell is not None:
                all_toys = list(sim.toys.values())
                idx = int(cell) - 1
                if 0 <= idx < len(all_toys):
                    all_toys[idx].trigger_shake()
        except Exception:
            pass
    return {"ok": True}


@app.get("/api/info")
async def get_info(request: Request):
    ip = get_local_ip()
    proto = request.url.scheme
    port = request.url.port or (443 if proto == "https" else 80)
    return {
        "local_ip": ip,
        "port": port,
        "url": f"{proto}://{ip}:{port}",
        "controllers_connected": len(runner.get_controller_list()),
        "max_controllers": runner.max_controllers,
    }


@app.get("/api/clients")
async def get_clients():
    return {
        "clients": runner.get_controller_list(),
        "max": runner.max_controllers,
    }


@app.post("/api/clients/kick/{client_id}", dependencies=ADMIN)
async def kick_client_endpoint(client_id: str):
    kicked = await runner.kick_client(client_id)
    return {"ok": kicked}


@app.get("/api/robots")
async def get_robots_endpoint():
    return {"robots": runner.get_robot_pool()}


@app.post("/api/robots/refresh", dependencies=ADMIN)
async def refresh_robots_endpoint():
    if runner.proc is not None and not runner.simulation:
        # robots used by the running program do not advertise and would vanish
        await runner.add_line("Újrakeresés csak leállított program mellett lehetséges.")
        return {"ok": False, "robots": runner.get_robot_pool()}
    await runner.init_robot_pool()
    return {"ok": True, "robots": runner.get_robot_pool()}


@app.post("/api/robots/{robot_id}/identify", dependencies=ADMIN)
async def identify_robot_endpoint(robot_id: int):
    if not any(r["id"] == robot_id for r in runner.robots):
        raise HTTPException(404, "unknown robot")
    return {"ok": await runner.identify_robot(robot_id)}


@app.post("/api/settings/auto-map", dependencies=ADMIN)
async def set_auto_map_endpoint(data: dict):
    runner.auto_map_on_connect = bool(data.get("enabled", True))
    await runner.broadcast({"type": "settings", "auto_map": runner.auto_map_on_connect})
    return {"ok": True, "auto_map": runner.auto_map_on_connect}


@app.post("/api/settings/low-power", dependencies=ADMIN)
async def set_low_power_endpoint(data: dict):
    runner.low_spec = bool(data.get("enabled", True))
    await runner.broadcast({"type": "settings", "low_spec": runner.low_spec})
    return {"ok": True, "low_spec": runner.low_spec}


@app.get("/api/admin/status")
async def admin_status(request: Request):
    host = request.client.host if request.client else ""
    return {"admin": is_admin(request), "local": host in LOCAL_IPS}


@app.post("/api/admin/login")
async def admin_login(data: dict, response: Response):
    if not hmac.compare_digest(str(data.get("password", "")).encode(), ADMIN_PASSWORD.encode()):
        await asyncio.sleep(1.0)           # slows down guessing
        raise HTTPException(401, "wrong password")
    response.set_cookie(ADMIN_COOKIE, ADMIN_TOKEN, max_age=30 * 24 * 3600,
                        httponly=True, samesite="lax")
    return {"ok": True}


@app.post("/api/admin/logout")
async def admin_logout(response: Response):
    response.delete_cookie(ADMIN_COOKIE)
    return {"ok": True}


@app.websocket("/ws")
async def websocket(ws: WebSocket):
    client_ip = ws.client.host if ws.client else "unknown"
    # host = laptop or a phone logged in as admin (no joystick slot); others drive one robot
    role = "host" if is_admin(ws) else "controller"

    current_controllers = [m for m in runner.client_meta.values() if m.get("role") == "controller"]
    if role == "controller" and len(current_controllers) >= runner.max_controllers:
        await ws.accept()
        await ws.send_json({
            "type": "error",
            "code": "MAX_CLIENTS",
            "message": f"Már {runner.max_controllers} eszköz csatlakozott a robotokhoz. Kérlek várj egy kicsit! (Max {runner.max_controllers} controllers active)",
        })
        await asyncio.sleep(0.5)
        await ws.close(code=1008)
        return

    await ws.accept()
    runner.client_counter += 1
    cid = f"dev_{runner.client_counter}"
    runner.clients.add(ws)
    runner.client_meta[ws] = {
        "id": cid,
        "ip": client_ip,
        "role": role,
        "connected_at": time.time(),
        "last_active": time.time(),
        "slot": None,
    }

    slot_info = None
    if role == "controller":
        slot_info = await runner.assign_controller(ws, cid)

    await ws.send_json(runner.status())
    await ws.send_json({"type": "history", "lines": list(runner.log)})
    await ws.send_json({"type": "game", "state": runner.game})
    await ws.send_json({"type": "telemetry", "data": runner.get_current_telemetry()})
    await ws.send_json({"type": "robot_pool", "robots": runner.get_robot_pool()})
    await ws.send_json({
        "type": "self_info",
        "client_id": cid,
        "role": role,
        "slot": slot_info.get("slot") if slot_info else None,
        "color": slot_info.get("color") if slot_info else None,
        "robot_name": slot_info.get("robot_name") if slot_info else None,
        "remote_admin": role == "host" and client_ip not in LOCAL_IPS,
    })
    await ws.send_json({"type": "settings", "auto_map": runner.auto_map_on_connect, "low_spec": runner.low_spec})
    await ws.send_json({"type": "calibration", "offsets": runner.calibration})
    await ws.send_json({"type": "dance", "config": load_dance()})
    await ws.send_json({"type": "minigames", "config": load_minigames()})
    await runner.broadcast_clients()

    if role == "controller":
        await runner.broadcast({
            "type": "controller_connected",
            "client_id": cid,
            "slot": slot_info.get("slot") if slot_info else 1,
            "auto_map": runner.auto_map_on_connect,
        })

    try:
        while True:
            msg = await ws.receive_json()
            if ws in runner.client_meta:
                runner.client_meta[ws]["last_active"] = time.time()

            msg_type = msg.get("type")
            if msg_type == "ping":
                await ws.send_json({"type": "pong"})
            elif msg_type == "keys":
                keys = {k for k in msg.get("keys", []) if k in DRIVE_KEYS}
                runner.keys[ws] = (keys, bool(msg.get("turbo")))
                await runner.send_keys()
            elif msg_type == "joystick":
                h = int(msg.get("heading", 0)) % 360
                s = max(0.0, min(255.0, float(msg.get("speed", 0))))
                meta = runner.client_meta.get(ws, {})
                if meta.get("role") == "controller":
                    r = meta.get("slot") or 1      # phones only drive their own robot
                else:
                    r = int(msg.get("robot") or 1)
                await runner.send_line(f"drive {r} {h} {s:.1f}\n", "joystick")
            elif msg_type == "calibrate":
                meta = runner.client_meta.get(ws, {})
                if meta.get("role") == "controller":
                    r = meta.get("slot") or 1      # phones only calibrate their own robot
                else:
                    r = int(msg.get("robot") or 1)
                await runner.set_calibration(r, float(msg.get("offset", 0)))
            elif msg_type == "kick":
                target_id = msg.get("client_id")
                if target_id and role == "host":
                    await runner.kick_client(target_id)
    except WebSocketDisconnect:
        pass
    finally:
        runner.clients.discard(ws)
        meta = runner.client_meta.pop(ws, None)
        runner.keys.pop(ws, None)
        if meta and meta.get("role") == "controller":
            await runner.release_controller(meta["id"])
        await runner.send_keys()
        await runner.broadcast_clients()


@app.get("/{full_path:path}")
async def catch_all_spa(full_path: str):
    if full_path.startswith("api/") or full_path.startswith("assets/"):
        raise HTTPException(404, "Not Found")
    return RedirectResponse(url="/", status_code=302)


if __name__ == "__main__":
    import argparse
    import uvicorn

    certs_dir = Path(__file__).resolve().parent / "certs"
    default_cert = str(certs_dir / "cert.pem")
    default_key = str(certs_dir / "key.pem")

    parser = argparse.ArgumentParser(description="Sphero Web Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--sim", "--simulate", action="store_true", help="Force simulation mode without physical robots")
    parser.add_argument("--low-power", "--low-spec", action="store_true", help="Enable optimizations for low-level / low-spec hardware")
    parser.add_argument("--host-ip", help="Override local IP address reported to mobile clients")
    parser.add_argument("--max-controllers", type=int, default=3, help="Max simultaneous mobile controllers (default: 3)")
    parser.add_argument("--idle-timeout", type=int, default=300, help="Controller inactivity timeout in seconds (default: 300)")
    parser.add_argument("--ssl", action="store_true", help="Enable HTTPS using SSL certificates")
    parser.add_argument("--ssl-cert", default=default_cert, help="SSL certificate file path")
    parser.add_argument("--ssl-key", default=default_key, help="SSL key file path")
    args = parser.parse_args()

    if args.sim:
        runner.simulation = True
        sphero_ble.set_simulation(True)

    if args.low_power:
        runner.low_spec = True
        runner.log = collections.deque(maxlen=500)

    if args.host_ip:
        os.environ["SPHERO_HOST_IP"] = args.host_ip

    runner.max_controllers = args.max_controllers
    runner.idle_timeout = args.idle_timeout

    ssl_kwargs = {}
    if args.ssl:
        if not Path(args.ssl_cert).exists() or not Path(args.ssl_key).exists():
            print(f"[!] SSL certs not found at {args.ssl_cert}. Please generate them or run without --ssl.")
            sys.exit(1)
        ssl_kwargs["ssl_certfile"] = args.ssl_cert
        ssl_kwargs["ssl_keyfile"] = args.ssl_key
        print(f"[*] Running with HTTPS on https://{args.host}:{args.port}")
    else:
        print(f"[*] Running with HTTP on http://{args.host}:{args.port}")

    uvicorn.run(app, host=args.host, port=args.port, **ssl_kwargs)


