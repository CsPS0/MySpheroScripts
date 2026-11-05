"""
Web control for the Sphero programs. Runs one program at a time as a
subprocess, streams its output to the browser and forwards drive keys.

    uvicorn web.server:app --host 0.0.0.0 --port 8080     (from the project folder)
"""

import asyncio
import collections
import contextlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
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
        "description": "Synchronized dance for all 3 robots: spins, circles, shuffle, "
                       "solos, follow the leader, back home, finale. About 85 s.",
        "args": ["bolt_dance.py"],
        "moves": True,
    },
    "drive": {
        "title": "Joystick Drive",
        "description": "Smooth remote control driving with the virtual joystick! Zero lag, "
                       "real-time heading & speed steering.",
        "args": ["drive_keys.py", "--stdin", "--robots", "1"],
        "moves": True,
        "joystick": True,
    },
    "roam": {
        "title": "Autonomous Roam",
        "description": "All 3 robots wander around their own start spot "
                       "(25 cm circle) until you press Stop, then drive back home.",
        "args": ["roam.py", "--radius", "25"],
        "moves": True,
    },
    "neu": {
        "title": "Neumann Formation",
        "description": "After aiming, the robots turn in place and scroll the full NEUMANN "
                       "school name across their 8x8 matrix displays with glowing LEDs. "
                       "Holds until Stop.",
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
        "title": "Simon Says",
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
STOP_GRACE = 15     # seconds after Ctrl+C before the program is terminated


ROBOT_COLORS = {
    1: {"r": 255, "g": 59, "b": 59, "hex": "#ff3b3b", "name": "Piros", "en": "Red"},
    2: {"r": 46, "g": 204, "b": 113, "hex": "#2ecc71", "name": "Zöld", "en": "Green"},
    3: {"r": 52, "g": 152, "b": 219, "hex": "#3498db", "name": "Kék", "en": "Blue"},
    4: {"r": 241, "g": 196, "b": 15, "hex": "#f1c40f", "name": "Sárga", "en": "Yellow"},
}


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
        self.simulation = os.environ.get("SPHERO_SIM", "1").lower() in ("1", "true", "yes")
        if not sphero_ble.list_adapters():
            self.simulation = True
        self.lock = asyncio.Lock()

    def get_robot_pool(self):
        return self.robots

    async def broadcast_robot_pool(self):
        await self.broadcast({"type": "robot_pool", "robots": self.get_robot_pool()})

    async def init_robot_pool(self):
        self.robots = []
        if self.simulation:
            try:
                import sphero_sim
                sim = sphero_sim.SimulatorManager.get()
                specs = [
                    ("BOLT-1", "SB-3FF5", 1),
                    ("BOLT-2", "SB-034E", 2),
                    ("BOLT-3", "SB-61A9", 3),
                ]
                cache_map = {}
                for name, alias, slot_idx in specs:
                    toy = sim.get_toy(alias)
                    v = toy.get_battery_voltage() if hasattr(toy, "get_battery_voltage") else 4.02
                    pct = toy.get_battery_percentage() if hasattr(toy, "get_battery_percentage") else 95
                    col = ROBOT_COLORS.get(slot_idx, ROBOT_COLORS[1])
                    cache_map[name] = toy.address
                    cache_map[alias] = toy.address
                    self.robots.append({
                        "id": slot_idx,
                        "name": f"{name} ({alias})",
                        "raw_name": alias,
                        "address": toy.address,
                        "battery": pct,
                        "voltage": round(v, 2),
                        "status": "ready",
                        "slot": None,
                        "client_id": None,
                        "color": col,
                    })
                sphero_ble.save_cached_bolts(cache_map)
                await self.add_line(f"Robot pool kész: {len(self.robots)} robot készen áll [Szimuláció].")
            except Exception as e:
                await self.add_line(f"Szimulált robot pool hiba: {e}")
        else:
            try:
                found = sphero_ble.scan_bolts(timeout=3.0)
                cache_map = {}
                if not found:
                    found = [("SB-3FF5", "D4:22:CD:00:3F:F5", -60), ("SB-034E", "D4:22:CD:00:03:4E", -65), ("SB-61A9", "D4:22:CD:00:61:A9", -70)]
                for idx, item in enumerate(found[:max(3, self.max_controllers)]):
                    name, addr = item[0], item[1]
                    slot_idx = idx + 1
                    col = ROBOT_COLORS.get(slot_idx, ROBOT_COLORS[1])
                    cache_map[name] = addr
                    cache_map[f"BOLT-{slot_idx}"] = addr
                    self.robots.append({
                        "id": slot_idx,
                        "name": f"BOLT-{slot_idx} ({name})",
                        "raw_name": name,
                        "address": addr,
                        "battery": max(15, 96 - idx * 5),
                        "voltage": round(4.14 - idx * 0.08, 2),
                        "status": "ready",
                        "slot": None,
                        "client_id": None,
                        "color": col,
                    })
                sphero_ble.save_cached_bolts(cache_map)
                await self.add_line(f"Robot pool kész: {len(self.robots)} Sphero robot felderítve és gyorsítótárazva.")
            except Exception as e:
                await self.add_line(f"Bluetooth scan notice ({e}).")
        await self.broadcast_robot_pool()

    async def assign_controller(self, ws, cid):
        active = [m for m in self.client_meta.values() if m.get("role") == "controller"]
        slot_num = len(active)
        self.client_meta[ws]["slot"] = slot_num
        col = ROBOT_COLORS.get(slot_num, ROBOT_COLORS[1])

        robot = None
        if slot_num <= len(self.robots):
            robot = self.robots[slot_num - 1]
            robot["slot"] = slot_num
            robot["client_id"] = cid
            robot["status"] = "assigned"

            if self.simulation:
                try:
                    import sphero_sim
                    from spherov2.types import Color
                    sim = sphero_sim.SimulatorManager.get()
                    c = Color(col["r"], col["g"], col["b"])
                    toy = sim.get_toy(robot.get("raw_name", robot["name"]))
                    toy.set_matrix_character(str(slot_num), c)
                    toy.front_led = c
                except Exception:
                    pass

        await self.broadcast_robot_pool()
        await self.add_line(f"📱 Telefon csatlakozott (Slot #{slot_num}) -> Robot #{slot_num} ({col['name']}) hozzárendelve.")
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
                    try:
                        import sphero_sim
                        from spherov2.types import Color
                        sim = sphero_sim.SimulatorManager.get()
                        toy = sim.get_toy(r.get("raw_name", r["name"]))
                        toy.clear_matrix()
                        toy.front_led = Color(0, 0, 0)
                    except Exception:
                        pass
                break
        await self.broadcast_robot_pool()
        if released_slot:
            await self.add_line(f"📱 Telefon levált (Slot #{released_slot}) -> Robot #{released_slot} mátrix visszaállítva.")

    async def identify_robot(self, robot_id: int):
        r = next((x for x in self.robots if x["id"] == robot_id), None)
        if r:
            col = r["color"]
            if self.simulation:
                try:
                    import sphero_sim
                    from spherov2.types import Color
                    sim = sphero_sim.SimulatorManager.get()
                    toy = sim.get_toy(r.get("raw_name", r["name"]))
                    c = Color(col["r"], col["g"], col["b"])
                    toy.set_matrix_character(str(robot_id), c)
                    toy.front_led = c
                except Exception:
                    pass
            await self.add_line(f"💡 Robot #{robot_id} azonosítás: villogás {col['name']} fénnyel.")

    def get_controller_list(self):
        now = time.time()
        res = []
        for ws, meta in self.client_meta.items():
            if meta.get("role") == "controller":
                res.append({
                    "id": meta["id"],
                    "ip": meta["ip"],
                    "connected_at": meta["connected_at"],
                    "idle": int(now - meta["last_active"]),
                })
        return res

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
            mode_tag = " [SIMULATION]" if self.simulation else ""
            await self.add_line(f"=== Start: {spec['title']}{mode_tag} ===")
            await self._release()

            env = {**os.environ, "PYTHONUNBUFFERED": "1"}
            if self.simulation:
                env["SPHERO_SIM"] = "1"

            venv_py = ROOT / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
            python_exec = str(venv_py) if venv_py.exists() else sys.executable
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            start_new_session = (sys.platform != "win32")

            self.proc = await asyncio.create_subprocess_exec(
                python_exec, "-u", *spec["args"],
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
                await self.add_line(f"=== No reaction, sending {getattr(sig, 'name', str(sig))} ===")
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


def get_local_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


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


@app.get("/")
async def index():
    candidates = [
        PROJECT_ROOT / "index.html",
        STATIC / "index.html",
    ]
    for idx in candidates:
        if idx.exists():
            return FileResponse(idx)
    raise HTTPException(404, "index.html not found")


@app.get("/api/programs")
async def programs():
    return [{"id": k, **{f: v[f] for f in ("title", "description", "moves")},
             "pads": v.get("pads", []), "letters": v.get("letters", False)}
            for k, v in PROGRAMS.items()]


@app.get("/api/letters")
async def get_letters():
    return letters.load()


@app.post("/api/letters")
async def change_letters(change: dict):
    """change: {"target": 0|1|2|"all", "action": "cw"|"ccw"|"mirror"|"reset"}
    or {"heading": <degrees>}."""
    cfg = letters.load()
    if "heading" in change:
        cfg["heading"] = int(change["heading"]) % 360
    else:
        action, target = change.get("action"), change.get("target")
        items = cfg["letters"] if target == "all" else [cfg["letters"][int(target)]]
        for item in items:
            if action == "cw":
                item["rotation"] = (item["rotation"] + 90) % 360
            elif action == "ccw":
                item["rotation"] = (item["rotation"] - 90) % 360
            elif action == "mirror":
                item["mirror"] = not item["mirror"]
            elif action == "reset":
                item["rotation"], item["mirror"] = 0, False
            else:
                raise HTTPException(400, "unknown action")
    letters.save(cfg)
    cfg = letters.load()
    await runner.broadcast({"type": "letters", "config": cfg})
    await runner.send_line(f"letters {json.dumps(cfg)}\n", "letters")
    return cfg


@app.post("/api/start/{program_id}")
async def start(program_id: str):
    if program_id not in PROGRAMS:
        raise HTTPException(404, "unknown program")
    await runner.start(program_id)
    return runner.status()


@app.post("/api/stop")
async def stop():
    await runner.stop()
    return runner.status()


@app.post("/api/game")
async def game(action: dict):
    """{"action": "play", "cell": 1-9}, or "new" (same layout), "recount", "start".
    Party games: {"action": "tap", "cell": n} (like shaking ball n) and "start"."""
    if action.get("action") in ("play", "tap"):
        await runner.send_line(f"{action['action']} {int(action['cell'])}\n", "game")
    elif action.get("action") in ("new", "recount", "start"):
        await runner.send_line(action["action"] + "\n", "game")
    else:
        raise HTTPException(400, "unknown action")
    return {"ok": True}


@app.get("/api/tictactoe")
async def get_tictactoe():
    return tictactoe.load_config()


@app.post("/api/tictactoe")
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


@app.post("/api/sim")
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


@app.post("/api/shake")
async def shake(action: dict):
    """Triggers shake on a robot or cell: {"cell": 1-9} or {"robot": "SB-3FF5"}."""
    cell = action.get("cell")
    robot = action.get("robot")
    if cell is not None:
        await runner.send_line(f"tap {int(cell)}\n", "game")

    if runner.simulation:
        try:
            import sphero_sim
            sim = sphero_sim.SimulatorManager.get()
            if robot:
                sim.get_toy(robot).trigger_shake()
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


@app.post("/api/clients/kick/{client_id}")
async def kick_client_endpoint(client_id: str):
    kicked = await runner.kick_client(client_id)
    return {"ok": kicked}


@app.get("/api/robots")
async def get_robots_endpoint():
    return {"robots": runner.get_robot_pool()}


@app.post("/api/robots/refresh")
async def refresh_robots_endpoint():
    await runner.init_robot_pool()
    return {"ok": True, "robots": runner.get_robot_pool()}


@app.post("/api/robots/{robot_id}/identify")
async def identify_robot_endpoint(robot_id: int):
    await runner.identify_robot(robot_id)
    return {"ok": True}


@app.post("/api/settings/auto-map")
async def set_auto_map_endpoint(data: dict):
    runner.auto_map_on_connect = bool(data.get("enabled", True))
    await runner.broadcast({"type": "settings", "auto_map": runner.auto_map_on_connect})
    return {"ok": True, "auto_map": runner.auto_map_on_connect}


@app.websocket("/ws")
async def websocket(ws: WebSocket):
    client_ip = ws.client.host if ws.client else "unknown"
    role = "host" if client_ip in ("127.0.0.1", "localhost", "::1") else "controller"

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
    })
    await ws.send_json({"type": "settings", "auto_map": runner.auto_map_on_connect})
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
                assigned_slot = runner.client_meta.get(ws, {}).get("slot", 1)
                r = int(msg.get("robot") or assigned_slot)
                await runner.send_line(f"drive {r} {h} {s:.1f}\n", "drive")
            elif msg_type == "kick":
                target_id = msg.get("client_id")
                if target_id:
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


if __name__ == "__main__":
    import argparse
    import uvicorn

    certs_dir = Path(__file__).resolve().parent / "certs"
    default_cert = str(certs_dir / "cert.pem")
    default_key = str(certs_dir / "key.pem")

    parser = argparse.ArgumentParser(description="Sphero Web Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--max-controllers", type=int, default=3, help="Max simultaneous mobile controllers (default: 3)")
    parser.add_argument("--idle-timeout", type=int, default=300, help="Controller inactivity timeout in seconds (default: 300)")
    parser.add_argument("--ssl", action="store_true", help="Enable HTTPS using SSL certificates")
    parser.add_argument("--ssl-cert", default=default_cert, help="SSL certificate file path")
    parser.add_argument("--ssl-key", default=default_key, help="SSL key file path")
    args = parser.parse_args()

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


