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
import sys
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import letters  # noqa: E402  (project module, shared with the robot programs)
import sphero_ble  # noqa: E402
import tictactoe  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
ROBOT_NAMES = ["SB-3FF5", "SB-034E", "SB-61A9"]

PROGRAMS = {
    "dance": {
        "title": "Dance",
        "description": "Synchronized dance for all 3 robots: spins, circles, shuffle, "
                       "solos, follow the leader, back home, finale. About 85 s.",
        "args": ["bolt_dance.py"],
        "moves": True,
    },
    "drive1": {
        "title": "Drive 1 robot",
        "description": "Drive SB-3FF5 with W A S D or the arrow keys. "
                       "Shift for more speed. Only this robot is connected.",
        "args": ["drive_keys.py", "--stdin", "--robots", "1"],
        "moves": True,
        "pads": [{"robot": "SB-3FF5", "color": "r1", "keys": "both"}],
    },
    "drive2": {
        "title": "Drive 2 robots",
        "description": "SB-3FF5 with W A S D, SB-61A9 with the arrow keys. "
                       "Shift for more speed.",
        "args": ["drive_keys.py", "--stdin", "--robots", "1,3"],
        "moves": True,
        "pads": [{"robot": "SB-3FF5", "color": "r1", "keys": "wasd"},
                 {"robot": "SB-61A9", "color": "r3", "keys": "arrows"}],
    },
    "roam": {
        "title": "Roam",
        "description": "All 3 robots wander around their own start spot "
                       "(25 cm circle) until you press Stop, then drive back home.",
        "args": ["roam.py", "--radius", "25"],
        "moves": True,
    },
    "neu": {
        "title": "NEU",
        "description": "After aiming, the robots turn in place one by one and show "
                       "N, E, U with the tops of the letters pointing west (left). "
                       "Holds until Stop.",
        "args": ["neu.py"],
        "moves": True,
        "letters": True,
    },
    "tictactoe": {
        "title": "Tic-tac-toe",
        "description": "Connects the 9 nearest free BOLTs (or the names in Setup). They "
                       "show 1 to 9: put them in a 3x3 grid. Shake a ball to take that "
                       "square, X always starts. The robots never drive.",
        "args": ["tictactoe.py"],
        "moves": False,
        "game": True,
    },
    "simon": {
        "title": "Simon Says",
        "description": "2 to 9 balls, each in its own color. They light up in a sequence: "
                       "shake them back in the same order. One more step each level.",
        "args": ["minigames.py", "simon"],
        "moves": False,
        "game": True,
    },
    "mole": {
        "title": "Whack-a-mole",
        "description": "A random ball turns green: shake it before it goes dark. "
                       "Wrong ball -1. 60 s rounds, the moles get faster.",
        "args": ["minigames.py", "mole"],
        "moves": False,
        "game": True,
    },
    "potato": {
        "title": "Hot potato",
        "description": "1 ball. Shake it to light the fuse and pass it around. It blinks "
                       "faster, green to red, and explodes after a secret 15 to 35 s.",
        "args": ["minigames.py", "potato"],
        "moves": False,
        "game": True,
    },
    "rps": {
        "title": "Rock-paper-scissors",
        "description": "2 balls, player 1 red, player 2 blue. Both shake, 3-2-1 countdown, "
                       "then each ball shows rock, paper or scissors. First to 2 wins.",
        "args": ["minigames.py", "rps"],
        "moves": False,
        "game": True,
    },
    "lightshow": {
        "title": "Light show",
        "description": "Connects up to 15 balls. Shake them in order along your line, then "
                       "synced effects run: rainbow, comet, breathing, police, sparkle, wave. "
                       "Start skips to the next effect.",
        "args": ["minigames.py", "lightshow"],
        "moves": False,
        "game": True,
    },
    "front": {
        "title": "LED test",
        "description": "Shows N, E, U on the matrices, white front light and blue "
                       "tail light on all 3 robots. No movement.",
        "args": ["front_test.py"],
        "moves": False,
        "letters": True,
    },
    "locator": {
        "title": "Locator test",
        "description": "One robot after another: short roll forward and right, "
                       "then back home. Checks the position tracking.",
        "args": ["locator_test.py"],
        "moves": True,
    },
    "connect": {
        "title": "Connection test",
        "description": "Connects to all 3 robots, reads battery and firmware. No movement.",
        "args": ["connect_test.py", "--hold", *ROBOT_NAMES],
        "moves": False,
    },
}

DRIVE_KEYS = {"KeyW", "KeyA", "KeyS", "KeyD", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"}
STOP_GRACE = 15     # seconds after Ctrl+C before the program is terminated


class Runner:
    def __init__(self):
        self.proc = None
        self.program = None
        self.started = None
        self.last_exit = None          # (program, exit code)
        self.log = collections.deque(maxlen=1500)
        self.clients = set()
        self.keys = {}                 # websocket -> (set of key codes, turbo)
        self.game = None               # latest tic-tac-toe state
        self.lock = asyncio.Lock()

    def status(self):
        return {
            "type": "status",
            "running": self.program,
            "started": self.started,
            "last_exit": self.last_exit,
        }

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
            await self.add_line(f"=== Start: {spec['title']} ===")
            await self._release()
            self.proc = await asyncio.create_subprocess_exec(
                sys.executable, "-u", *spec["args"],
                cwd=ROOT,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                start_new_session=True,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
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
        for sig, wait in ((signal.SIGINT, STOP_GRACE), (signal.SIGTERM, 3), (signal.SIGKILL, 3)):
            try:
                os.killpg(proc.pid, sig)
            except ProcessLookupError:
                break
            try:
                await asyncio.wait_for(proc.wait(), wait)
                break
            except asyncio.TimeoutError:
                await self.add_line(f"=== No reaction, sending {sig.name} ===")
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


runner = Runner()


@contextlib.asynccontextmanager
async def lifespan(app):
    yield
    await runner.stop()        # container stop: let the program stop the robots


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


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


@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws.accept()
    runner.clients.add(ws)
    await ws.send_json(runner.status())
    await ws.send_json({"type": "history", "lines": list(runner.log)})
    await ws.send_json({"type": "game", "state": runner.game})
    try:
        while True:
            msg = await ws.receive_json()
            if msg.get("type") == "keys":
                keys = {k for k in msg.get("keys", []) if k in DRIVE_KEYS}
                runner.keys[ws] = (keys, bool(msg.get("turbo")))
                await runner.send_keys()
    except WebSocketDisconnect:
        pass
    finally:
        runner.clients.discard(ws)
        runner.keys.pop(ws, None)
        await runner.send_keys()
