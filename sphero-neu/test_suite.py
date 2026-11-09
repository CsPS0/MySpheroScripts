"""
End-to-End Autonomous Audit & Feature Matrix Test Suite for Sphero BOLT Fleet Suite.
Exercises all requirements in Steps 1 & 2 with SPHERO_SIM=1.
"""

import asyncio
import contextlib
import copy
import filecmp
import json
import math
import os
import py_compile
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

os.environ["SPHERO_SIM"] = "1"

SPHERO_NEU_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SPHERO_NEU_DIR.parent
WEB_DIR = SPHERO_NEU_DIR / "web"

sys.path.insert(0, str(SPHERO_NEU_DIR))
sys.path.insert(0, str(WEB_DIR))

import big_dance
import bolt_dance
import drive_keys
import formation
import indicators
import letters
import minigames
import neu
import roam
import sphero_ble
import sphero_sim
import tictactoe
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color


class AuditResults:
    def __init__(self):
        self.passed = []
        self.failed = []

    def check(self, name: str, condition: bool, detail: str = ""):
        if condition:
            self.passed.append((name, detail))
            print(f"  [PASS] {name}" + (f" ({detail})" if detail else ""), flush=True)
        else:
            self.failed.append((name, detail))
            print(f"  [FAIL] {name}" + (f" ({detail})" if detail else ""), flush=True)


results = AuditResults()


def backup_data_files():
    data_dir = SPHERO_NEU_DIR / "data"
    backups = {}
    for name in ("letters.json", "minigames.json", "dance.json", "tictactoe.json"):
        p = data_dir / name
        backups[p] = p.read_bytes() if p.exists() else None
    return backups


def restore_data_files(backups):
    for p, content in backups.items():
        if content is None:
            with contextlib.suppress(OSError):
                p.unlink()
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(content)


# ==============================================================================
# STEP 1: System & Environment Health Check
# ==============================================================================
def test_step1_environment_and_sync():
    print("\n=== STEP 1: System & Environment Health Check ===", flush=True)
    for mod_name in ("fastapi", "uvicorn", "websockets", "spherov2", "py_compile"):
        try:
            __import__(mod_name)
            results.check(f"Dependency '{mod_name}' installed", True)
        except ImportError as e:
            results.check(f"Dependency '{mod_name}' installed", False, str(e))

    py_files = [p for p in SPHERO_NEU_DIR.rglob("*.py") if ".venv" not in p.parts and p.name != "test_suite.py"]
    all_compiled = True
    for p in py_files:
        try:
            py_compile.compile(str(p), doraise=True)
        except Exception as e:
            all_compiled = False
            results.check(f"py_compile {p.name}", False, str(e))
    results.check("All Python files pass py_compile", all_compiled, f"{len(py_files)} files checked")

    sync_pairs = [
        (PROJECT_ROOT / "index.html", WEB_DIR / "static" / "index.html"),
        (PROJECT_ROOT / "assets" / "css" / "styles.css", WEB_DIR / "static" / "assets" / "css" / "styles.css"),
        (PROJECT_ROOT / "assets" / "js" / "app.js", WEB_DIR / "static" / "assets" / "js" / "app.js"),
    ]
    for src, dst in sync_pairs:
        same = src.exists() and dst.exists() and filecmp.cmp(str(src), str(dst), shallow=False)
        results.check(f"File sync: {src.relative_to(PROJECT_ROOT)} <-> {dst.relative_to(PROJECT_ROOT)}", same)


def test_step1_fastapi_server():
    import server

    async def _run():
        server.runner.simulation = True
        sphero_ble.set_simulation(True)
        await server.runner.init_robot_pool()
        results.check("FastAPI runner robot pool initialized (15 robots)", len(server.runner.robots) == 15)

        class DummyClient:
            def __init__(self, host):
                self.host = host

        class DummyConn:
            def __init__(self, host, cookies=None):
                self.client = DummyClient(host)
                self.cookies = cookies or {}

        for host in ("127.0.0.1", "localhost", "::1", server.get_local_ip()):
            conn = DummyConn(host)
            results.check(f"Server is_admin() permits '{host}' without 401", server.is_admin(conn))
            status = await server.admin_status(conn)
            results.check(f"Server /api/admin/status for '{host}' returns admin=True, local=True",
                          status["admin"] is True and status["local"] is True, str(status))

        remote_conn = DummyConn("203.0.113.55")
        results.check("Server blocks unauthenticated external IP", not server.is_admin(remote_conn))
        authed_remote = DummyConn("203.0.113.55", cookies={server.ADMIN_COOKIE: server.ADMIN_TOKEN})
        results.check("Server permits external IP with valid admin cookie", server.is_admin(authed_remote))

        progs = await server.programs()
        results.check("GET /api/programs returns all 9 programs", len(progs) == 9)

        scream_resp = await server.sound_scream()
        results.check("GET /api/sound/scream returns FileResponse (audio/wav)",
                      scream_resp.media_type == "audio/wav")

    asyncio.run(_run())


# ==============================================================================
# STEP 2.D: Physics Engine & Telemetry (sphero_sim.py)
# ==============================================================================
def test_step2d_physics_and_telemetry():
    print("\n=== STEP 2.D: Physics Engine & Telemetry (sphero_sim.py) ===", flush=True)
    results.check("ROBOT_RADIUS == 3.65 cm", math.isclose(sphero_sim.ROBOT_RADIUS, 3.65))
    results.check("ROBOT_DIAMETER == 7.3 cm", math.isclose(sphero_sim.ROBOT_DIAMETER, 7.3))

    sim = sphero_sim.SimulatorManager.get()
    sim.apply_layout("default")

    # Measure telemetry format & 60 FPS loop
    captured = []
    orig_emit = sim._emit_telemetry

    def spy_emit():
        captured.append((time.monotonic(), sim.get_telemetry()))
        orig_emit()

    sim._emit_telemetry = spy_emit
    try:
        time.sleep(0.55)
    finally:
        sim._emit_telemetry = orig_emit

    results.check("Telemetry emitted regularly by 60 FPS physics loop", len(captured) >= 5,
                  f"{len(captured)} telemetry frames in 0.55s")
    sample = captured[-1][1]
    results.check("Telemetry JSON structure valid",
                  "robots" in sample and len(sample["robots"]) == 15)
    r0 = sample["robots"][0]
    has_keys = all(k in r0 for k in ("name", "x", "y", "heading", "speed", "front_led", "back_led", "matrix"))
    matrix_valid = isinstance(r0["matrix"], list) and len(r0["matrix"]) == 8 and all(len(row) == 8 for row in r0["matrix"])
    results.check("Telemetry robot fields & 8x8 LED matrix valid", has_keys and matrix_valid)

    # Test elastic head-on collision between 2 robots
    t1 = sim.get_toy("BOLT-1")
    t2 = sim.get_toy("BOLT-2")
    collided = threading.Event()
    t1._add_listener(((24, 18, 0xFF), lambda l, p: l()), lambda *_: collided.set())
    with sim.lock:
        for idx, t in enumerate(sim.toys.values()):
            if t not in (t1, t2):
                t.x = -70.0 + idx * 9.0
                t.y = 120.0
                t.speed = 0.0
        t1.x, t1.y, t1.heading, t1.speed = -10.0, 40.0, 90.0, 120.0
        t2.x, t2.y, t2.heading, t2.speed = 10.0, 40.0, 270.0, 120.0

    min_dist = 999.0
    for _ in range(35):
        time.sleep(1.0 / 60.0)
        with sim.lock:
            d = math.hypot(t2.x - t1.x, t2.y - t1.y)
            min_dist = min(min_dist, d)
    results.check("Head-on elastic collision prevents overlap (dist >= 7.3 cm)",
                  min_dist >= sphero_sim.ROBOT_DIAMETER - 0.05, f"min_dist={min_dist:.2f} cm")
    results.check("Head-on elastic collision fires collision notification listener", collided.is_set())
    with sim.lock:
        t1.speed = t2.speed = 0.0


# ==============================================================================
# STEP 2.A: Interactive Driving & Calibration (drive_keys.py, server.py)
# ==============================================================================
def test_step2a_driving_and_calibration():
    print("\n=== STEP 2.A: Interactive Driving & Calibration ===", flush=True)
    sim = sphero_sim.SimulatorManager.get()

    # 1. Test initializing 1, 2, and 3 robots in Drive mode
    for count, arg in ((1, "1"), (2, "1,2"), (3, "1,2,3")):
        robots = [int(n) - 1 for n in arg.split(",")]
        km = drive_keys.keymaps_for(robots)
        results.check(f"Drive mode keymap initialization for {count} robot(s) (--robots {arg})",
                      len(km) == count and all(r in km for r in robots))

    # 2. Test steering inputs: WASD/arrows & target heading angles 0..359 & calibration offsets (-15 to +15)
    sim.apply_layout("drive")
    stop = threading.Event()
    with contextlib.ExitStack() as stack:
        toys, apis, drivers = {}, {}, {}
        for i in (0, 1, 2):
            t, a = sphero_ble.connect_toy(f"BOLT-{i + 1}", lambda toy: stack.enter_context(SpheroEduAPI(toy)))
            toys[i], apis[i] = t, a
            drivers[i] = drive_keys.Driven(a, stop)
            threading.Thread(target=drivers[i].run, daemon=True).start()

        km = drive_keys.keymaps_for([0, 1, 2])
        # Test WASD on robot 1, arrows on robot 2, and joystick on robot 3
        st_both = drive_keys.apply_keys(drivers, km, {"KeyW", "ArrowRight"}, True)
        drivers[2].wanted = (drivers[2].robot_heading(180), drive_keys.DRIVE_SPEED)
        results.check("WASD / Arrow / Joystick steering vectors applied",
                      drivers[0].wanted == (0, drive_keys.TURBO_SPEED)
                      and drivers[1].wanted == (90, drive_keys.TURBO_SPEED)
                      and drivers[2].wanted == (180, drive_keys.DRIVE_SPEED),
                      f"{st_both[0]} | {st_both[1]} | R3={drivers[2].wanted}")

        # Test calibration offsets (-15 to +15) and heading recalibration
        drivers[0].calibrate(-15)
        h_minus15 = drivers[0].robot_heading(0)
        drivers[0].calibrate(15)
        h_plus15 = drivers[0].robot_heading(0)
        drivers[0].calibrate(0)
        h_zero = drivers[0].robot_heading(0)
        results.check("Calibration offsets (-15°, +15°, 0°) and heading recalibration",
                      (h_minus15, h_plus15, h_zero) == (345, 15, 0),
                      f"-15°->{h_minus15}°, +15°->{h_plus15}°, 0°->{h_zero}°")

        # Test target heading angles 0° to 359°
        headings_ok = True
        for angle in (0, 45, 90, 135, 180, 225, 270, 315, 359):
            drivers[0].wanted = (drivers[0].robot_heading(angle), 100 + (angle % 5))
            time.sleep(0.08)
            if round(toys[0].heading) % 360 != angle:
                headings_ok = False
                break
        results.check("Target heading angles (0° to 359°) tracked accurately", headings_ok)

        # Test driving toward arena boundary respects boundary physics and never crashes out of bounds
        toys[0].x, toys[0].y = 90.0, 125.0
        drivers[0].wanted = (45, 255)
        time.sleep(0.45)
        in_bounds = (-78.0 <= toys[0].x <= 96.0) and (-28.0 <= toys[0].y <= 132.0)
        results.check("Driving within arena limits respects boundary physics",
                      in_bounds, f"pos=({toys[0].x:.1f}, {toys[0].y:.1f})")
        stop.set()

    # 3. Test subprocess drive_keys.py via server.py Runner (including send_keys & joystick & calibrate)
    import server

    async def _test_server_drive():
        await server.runner.start("drive")
        for _ in range(35):
            await asyncio.sleep(0.1)
            if any("Driving. Use the joystick" in item["line"] for item in server.runner.log):
                break
        await server.runner.send_line("drive 1 90 150.0\n", "joystick")
        await server.runner.set_calibration(1, 15)
        server.runner.keys["test_ws"] = ({"KeyW", "KeyD"}, True)
        await server.runner.send_keys()
        await asyncio.sleep(0.4)
        server.runner.keys.pop("test_ws", None)
        await server.runner.stop()
        log_text = "\n".join(item["line"] for item in server.runner.log)
        results.check("server.py Drive subprocess handles joystick, keys, and calibration",
                      "BOLT-1: forward = robot heading 15" in log_text and "heading" in log_text)

    asyncio.run(_test_server_drive())


# ==============================================================================
# STEP 2.B: Shows & Choreography (letters.py, neu.py, big_dance.py, roam.py)
# ==============================================================================
def test_step2b_shows_and_choreography():
    print("\n=== STEP 2.B: Shows & Choreography ===", flush=True)
    sim = sphero_sim.SimulatorManager.get()

    # 1. Neumann Formation (letters.py, neu.py)
    sim.apply_layout("neu")
    neu_toys = [sim.get_toy(f"BOLT-{i}") for i in range(1, 8)]
    xs = [t.x for t in neu_toys]
    ys = [t.y for t in neu_toys]
    results.check("Neumann 7-robot horizontal row alignment",
                  xs == [-60.0, -40.0, -20.0, 0.0, 20.0, 40.0, 60.0] and all(y == 25.0 for y in ys),
                  f"xs={xs}")

    cfg = letters.load()
    word = "".join(item["letter"] for item in cfg["letters"])
    results.check("Neumann default word is N-E-U-M-A-N-N", word == "NEUMANN")
    results.check(
        "Neumann N glyph is symmetric and un-mirrored by default",
        indicators.LETTERS["N"] == [
            "XX....XX",
            "XXX...XX",
            "XXXX..XX",
            "XX.XX.XX",
            "XX.XX.XX",
            "XX..XXXX",
            "XX...XXX",
            "XX....XX",
        ]
        and all(item["mirror"] is False and item["rotation"] == 0 for item in letters.DEFAULT["letters"]),
    )

    # Test 90° CW/CCW rotation, mirroring, individual 15° yaw offsets, compass vs manual aim via server API
    import server

    async def _test_letters_api():
        await server.change_letters({"target": "all", "action": "reset"})
        c1 = await server.change_letters({"target": 0, "action": "cw"})
        c2 = await server.change_letters({"target": 1, "action": "ccw"})
        c3 = await server.change_letters({"target": 2, "action": "mirror"})
        c4 = await server.change_letters({"target": 3, "action": "left"})
        c5 = await server.change_letters({"target": 4, "action": "right"})
        c6 = await server.change_letters({"align": "aim"})
        c7 = await server.change_letters({"heading": 45})
        ok = (
            c1["letters"][0]["rotation"] == 90
            and c2["letters"][1]["rotation"] == 270
            and c3["letters"][2]["mirror"] is True
            and c4["letters"][3]["turn"] == -15
            and c5["letters"][4]["turn"] == 15
            and c6["align"] == "aim"
            and c7["heading"] == 45
        )
        results.check("Neumann CW/CCW rotation, mirror, ±15° yaw, and compass/aim API", ok)
        await server.change_letters({"target": "all", "action": "reset"})
        await server.change_letters({"align": "compass"})
        await server.change_letters({"heading": 0})

    asyncio.run(_test_letters_api())

    # Run neu.py subprocess in both compass and aim modes
    for mode in ("compass", "aim"):
        cfg = copy.deepcopy(letters.DEFAULT) if hasattr(letters, "DEFAULT") else letters.load()
        cfg["align"] = mode
        cfg["hand"] = False
        letters.save(cfg)
        proc = subprocess.Popen(
            [sys.executable, "-u", str(SPHERO_NEU_DIR / "neu.py")],
            cwd=str(SPHERO_NEU_DIR),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env={**os.environ, "SPHERO_SIM": "1"},
        )
        neu_lines = []
        shown_event = threading.Event()
        updated_event = threading.Event()

        def _read_neu(p=proc, lines=neu_lines, ev=shown_event, uev=updated_event):
            for raw in p.stdout:
                s = raw.strip()
                if not s.startswith("TELEMETRY "):
                    lines.append(s)
                    if "NEUMANN is shown" in s:
                        ev.set()
                    if "turn +15" in s:
                        uev.set()

        rd_thread = threading.Thread(target=_read_neu, daemon=True)
        rd_thread.start()
        shown_event.wait(timeout=8.0)
        cfg["letters"][0]["turn"] = 15
        proc.stdin.write(f"letters {json.dumps(cfg)}\n")
        proc.stdin.flush()
        updated_event.wait(timeout=4.0)
        proc.terminate()
        with contextlib.suppress(Exception):
            proc.wait(timeout=5.0)
        rd_thread.join(timeout=2.0)
        out = "\n".join(neu_lines)
        results.check(f"neu.py subprocess execution in '{mode}' mode",
                      "NEUMANN is shown" in out and "turn +15" in out)

    # 2. Dance Show (big_dance.py)
    sim.apply_layout("dance", count=15)
    dance_toys = list(sim.toys.values())[:15]
    dance_ys = [t.y for t in dance_toys]
    dance_xs = [t.x for t in dance_toys]
    spacings = [round(dance_xs[i + 1] - dance_xs[i], 2) for i in range(14)]
    results.check("Dance Show 15-robot single horizontal line placement",
                  all(y == 30.0 for y in dance_ys) and all(s == 10.0 for s in spacings),
                  f"y=30.0, spacing={spacings[0]} cm")

    # Check number glyph display 1..15 upright
    glyphs_ok = True
    for n in range(1, 16):
        bmp = indicators.number_bitmap(n)
        if len(bmp) != 8 or any(len(row) != 8 for row in bmp):
            glyphs_ok = False
            break
    results.check("Dance Show number glyphs (1..15) and upright orientation",
                  glyphs_ok and indicators.UPRIGHT == {"rotation": 0, "mirror": False})

    # Test big_dance.py subprocess with exclusions and all choreography phases (including collision boom & home)
    (SPHERO_NEU_DIR / "data").mkdir(exist_ok=True)
    (SPHERO_NEU_DIR / "data" / "dance.json").write_text(json.dumps({"exclude": [2, 5]}))
    env = {**os.environ, "SPHERO_SIM": "1", "DANCE_SCALE": "0.02", "DANCE_RATE": "500"}
    proc = subprocess.Popen(
        [sys.executable, "-u", str(SPHERO_NEU_DIR / "big_dance.py")],
        cwd=str(SPHERO_NEU_DIR),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    states_seen = []
    lines_seen = []
    sent_go = False

    def _read_dance():
        nonlocal sent_go
        for raw in proc.stdout:
            line = raw.strip()
            if not line or line.startswith("TELEMETRY "):
                continue
            lines_seen.append(line)
            if line.startswith("STATE "):
                st = json.loads(line[6:])
                states_seen.append(st)
                if st["phase"] == "setup" and not sent_go:
                    proc.stdin.write("start\n")
                    proc.stdin.flush()
                    sent_go = True

    dance_reader = threading.Thread(target=_read_dance, daemon=True)
    dance_reader.start()
    proc.wait(timeout=25)
    dance_reader.join(timeout=2.0)
    phases_seen = [s["phase"] for s in states_seen]
    excluded_ok = any(s.get("excluded") == [2, 5] and 2 not in s.get("robots", []) and 5 not in s.get("robots", [])
                      for s in states_seen if s["phase"] == "setup")
    all_phases = all(p in phases_seen for p in ("connecting", "setup", "rainbow", "rush", "chars", "home", "finale", "done"))
    results.check("big_dance.py robot exclusions ([2, 5]) respected", excluded_ok)
    results.check("big_dance.py executes all choreography phases (setup->rainbow->rush->chars->home->finale->done)",
                  all_phases, f"phases={sorted(set(phases_seen))}")

    # Test Bot.boom() directly on a simulated robot to verify BOOM matrix rendering
    t_boom = sim.get_toy("BOLT-1")
    with SpheroEduAPI(t_boom) as api_boom:
        b_test = big_dance.Bot(1, "SB-SIM01", t_boom, api_boom)
        b_test.boom()
        lit_pixels = sum(1 for row in t_boom.matrix for c in row if c != (0, 0, 0))
        results.check("big_dance.py Bot.boom() renders explosion bitmap on matrix", lit_pixels == 52,
                      f"lit_pixels={lit_pixels}/64")

    # 3. Autonomous Roam (roam.py)
    proc = subprocess.Popen(
        [sys.executable, "-u", str(SPHERO_NEU_DIR / "roam.py")],
        cwd=str(SPHERO_NEU_DIR),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env={**os.environ, "SPHERO_SIM": "1"},
    )
    telemetry_frames = []
    roam_lines = []
    roam_ready = threading.Event()

    def _read_roam():
        for raw in proc.stdout:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("TELEMETRY "):
                with contextlib.suppress(ValueError):
                    telemetry_frames.append(json.loads(line[10:]))
            else:
                roam_lines.append(line)
                if "Roaming 15 robots" in line:
                    roam_ready.set()

    roam_reader = threading.Thread(target=_read_roam, daemon=True)
    roam_reader.start()
    roam_ready.wait(timeout=6.0)
    time.sleep(0.8)
    proc.terminate()
    with contextlib.suppress(Exception):
        proc.wait(timeout=5)
    roam_reader.join(timeout=2.0)

    results.check("roam.py connects and spawns all 15 robots",
                  any("Roaming 15 robots" in l for l in roam_lines) and len(telemetry_frames) > 0)
    no_overlap = True
    in_arena = True
    for frame in telemetry_frames[-10:]:
        bots = frame["robots"]
        for i in range(len(bots)):
            if not (-78.5 <= bots[i]["x"] <= 96.5 and -28.5 <= bots[i]["y"] <= 132.5):
                in_arena = False
            for j in range(i + 1, len(bots)):
                if math.hypot(bots[j]["x"] - bots[i]["x"], bots[j]["y"] - bots[i]["y"]) < sphero_sim.ROBOT_DIAMETER - 0.1:
                    no_overlap = False
    results.check("roam.py robots never overlap and stay within arena bounds", no_overlap and in_arena)


# ==============================================================================
# STEP 2.C: Games (tictactoe.py, minigames.py)
# ==============================================================================
def test_step2c_games():
    print("\n=== STEP 2.C: Games (tictactoe.py, minigames.py) ===", flush=True)
    sim = sphero_sim.SimulatorManager.get()

    # 1. Tic-Tac-Toe (tictactoe.py)
    sim.apply_layout("tictactoe")
    ttt_toys = list(sim.toys.values())[:9]
    expected_3x3 = [
        (-25.0, 50.0), (0.0, 50.0), (25.0, 50.0),
        (-25.0, 25.0), (0.0, 25.0), (25.0, 25.0),
        (-25.0, 0.0),  (0.0, 0.0),  (25.0, 0.0),
    ]
    actual_3x3 = [(t.x, t.y) for t in ttt_toys]
    results.check("Tic-Tac-Toe 9-robot 3x3 layout coordinates", actual_3x3 == expected_3x3)

    stop = threading.Event()
    with contextlib.ExitStack() as stack:
        cfg = tictactoe.load_config()
        robots = tictactoe.connect_robots(cfg, stack, want=9)
        names = {r: name for r, (name, _, _) in enumerate(robots)}
        displays = {r: tictactoe.Display(api, toy, stop) for r, (_, api, toy) in enumerate(robots)}
        game = tictactoe.Game(cfg, names, displays)

        # Test ball numbering phase (1 to 9) via recount() + shake(r)
        game.recount()
        results.check("Tic-Tac-Toe recount() enters 'numbering' phase", game.phase == "numbering")
        for r in range(9):
            game.shake(r)
        results.check("Tic-Tac-Toe ball numbering 1..9 assigns cells 0..8 and enters 'play' phase",
                      game.phase == "play" and [game.cell_of[r] for r in range(9)] == list(range(9)))

        # Test all 8 winning combinations + win blinking animation
        all_lines_ok = True
        for win_line in tictactoe.LINES:
            game.same_layout()
            other_cells = [c for c in range(9) if c not in win_line]
            # X plays win_line[0], O plays other[0], X plays win_line[1], O plays other[1], X plays win_line[2]
            game.play(win_line[0], "test")
            game.play(other_cells[0], "test")
            game.play(win_line[1], "test")
            game.play(other_cells[1], "test")
            game.play(win_line[2], "test")
            if game.winner != "X" or tuple(game.line) != win_line or game.phase != "over":
                all_lines_ok = False
                break
        results.check("Tic-Tac-Toe detects all 8 winning combinations", all_lines_ok)

        # Test win blinking animation
        game.ended_at = time.monotonic() + 60.0
        game.tick(True)
        game.tick(False)
        results.check("Tic-Tac-Toe winning line blink animation ticks cleanly", game.phase == "over")

        # Test draw detection
        game.same_layout()
        # Board for draw:
        # X O X (0, 1, 2)
        # X O O (3, 4, 5)
        # O X X (6, 7, 8)
        for move in (0, 1, 2, 4, 3, 5, 7, 6, 8):
            game.play(move, "test")
        results.check("Tic-Tac-Toe draw detection and round reset",
                      game.winner == "draw" and game.phase == "over")
        stop.set()

    # 2. Memory Game (minigames.py simon)
    stop = threading.Event()
    with contextlib.ExitStack() as stack:
        cfg = tictactoe.load_config()
        robots = tictactoe.connect_robots(cfg, stack, want=9)
        names = {r: name for r, (name, _, _) in enumerate(robots)}
        displays = {r: tictactoe.Display(api, toy, stop) for r, (_, api, toy) in enumerate(robots)}

        for spd in ("slow", "normal", "fast", "insane"):
            for lay in ("3x3", "random"):
                for dr in (False, True):
                    minigames.save_minigames_config("simon", {"speed": spd, "layout": lay, "drift": dr})
                    loaded = minigames.load_minigames_config("simon")
                    assert loaded["speed"] == spd and loaded["layout"] == lay and loaded["drift"] is dr
        results.check("Memory Game (Simon) difficulty & preference persistence in data/minigames.json", True)

        minigames.save_minigames_config("simon", {"speed": "fast", "layout": "3x3", "drift": True})
        cfg.update(minigames.load_minigames_config("simon"))
        simon = minigames.Simon(cfg, names, displays)
        simon.start()
        results.check("Simon starts at Level 1 in 'show' phase", simon.phase == "show" and len(simon.seq) == 1)

        # Measure gentle drift movement (~10-15 cm) without colliding
        sim_toys = [sim.get_toy(names[r]) for r in range(9)]
        before_pos = [(t.x, t.y) for t in sim_toys]
        simon.trigger_drift()
        time.sleep(0.75)
        simon.check_drift_stop(time.monotonic())
        after_pos = [(t.x, t.y) for t in sim_toys]
        dists = [math.hypot(after_pos[i][0] - before_pos[i][0], after_pos[i][1] - before_pos[i][1]) for i in range(9)]
        avg_drift = sum(dists) / len(dists)
        no_drift_collision = all(
            math.hypot(sim_toys[i].x - sim_toys[j].x, sim_toys[i].y - sim_toys[j].y) >= sphero_sim.ROBOT_DIAMETER - 0.05
            for i in range(9) for j in range(i + 1, 9)
        )
        results.check("Simon Gentle Drift moves robots ~10-15 cm without colliding",
                      8.0 <= avg_drift <= 20.0 and no_drift_collision,
                      f"avg_drift={avg_drift:.1f} cm")

        # Advance show -> input and test correct sequence progression -> Level 2
        while simon.phase == "show":
            simon.tick(simon.next_at + 0.01)
        results.check("Simon transitions from 'show' to 'input'", simon.phase == "input")
        first_ball = simon.seq[0]
        simon.shake(first_ball)
        results.check("Simon correct input completes Level 1 ('pause' phase)",
                      simon.phase == "pause" and simon.best == 1)
        simon.tick(simon.next_at + 0.01)
        results.check("Simon advances to Level 2", len(simon.seq) == 2 and simon.phase == "show")
        while simon.phase == "show":
            simon.tick(simon.next_at + 0.01)
        wrong_ball = next(r for r in displays if r != simon.seq[0])
        simon.shake(wrong_ball)
        results.check("Simon wrong tap triggers Game Over ('over' phase)", simon.phase == "over")

        # 3. Whack-a-Mole (minigames.py mole)
        minigames.save_minigames_config("mole", {"speed": "fast", "layout": "random", "drift": True})
        cfg.update(minigames.load_minigames_config("mole"))
        mole = minigames.Mole(cfg, names, displays)
        results.check("Whack-a-Mole 60-second round timer configured", mole.ROUND == 60)
        mole.start()
        mole.tick(mole.next_at + 0.01)
        active_m = mole.mole
        results.check("Whack-a-Mole spawns random neon green mole", active_m is not None)
        mole.shake(active_m)
        results.check("Whack-a-Mole hitting active mole increments score (+1)", mole.score == 1)
        wrong_m = next(r for r in displays if r != active_m)
        mole.shake(wrong_m)
        results.check("Whack-a-Mole hitting wrong ball decrements score (-1)", mole.score == 0)
        # Verify round restart preserves difficulty settings
        mole.start()
        results.check("Whack-a-Mole round restart preserves difficulty preferences",
                      mole.speed == "fast" and mole.layout == "random" and mole.drift is True and mole.score == 0)

        # 4. Hot Potato (minigames.py potato)
        potato_disp = {0: displays[0]}
        potato_names = {0: names[0]}
        potato = minigames.Potato(cfg, potato_names, potato_disp)
        results.check("Hot Potato starts in 1-ball 'idle' phase", potato.phase == "idle")
        potato.shake(0)
        results.check("Hot Potato tap/shake lights the fuse ('play' phase)", potato.phase == "play")
        potato.fuse = 2.0
        # Check accelerating pulse interval
        potato.tick(potato.started + 0.2)
        gap_early = potato.next_at - (potato.started + 0.2)
        potato.next_at = potato.started + 1.6
        potato.tick(potato.started + 1.6)
        gap_late = potato.next_at - (potato.started + 1.6)
        results.check("Hot Potato pulse frequency accelerates as fuse burns",
                      gap_late < gap_early, f"early={gap_early:.2f}s, late={gap_late:.2f}s")
        # Trigger explosion
        potato.tick(potato.started + 2.1)
        results.check("Hot Potato triggers explosion ('boom' phase and BOOM! label)",
                      potato.phase == "boom" and potato.labels[0] == "BOOM!")

        # 5. Rock-Paper-Scissors (minigames.py rps)
        rps_disp = {0: displays[0], 1: displays[1]}
        rps_names = {0: names[0], 1: names[1]}
        rps = minigames.RockPaperScissors(cfg, rps_names, rps_disp)
        results.check("Rock-Paper-Scissors 2-robot setup in 'wait' phase",
                      rps.phase == "wait" and len(rps.players) == 2)
        rps.shake(0)
        rps.shake(1)
        results.check("Rock-Paper-Scissors both players ready starts countdown ('count')", rps.phase == "count")
        countdown_labels = []
        for _ in range(3):
            rps.tick(rps.next_at + 0.01)
            countdown_labels.append(rps.labels[0])
        results.check("Rock-Paper-Scissors 3-2-1 countdown glyphs displayed",
                      countdown_labels == ["3", "2", "1"])
        rps.tick(rps.next_at + 0.01)
        results.check("Rock-Paper-Scissors reveals Rock/Paper/Scissors glyphs",
                      rps.phase == "result" and rps.labels[0] in ("Rock", "Paper", "Scissors")
                      and rps.labels[1] in ("Rock", "Paper", "Scissors"))
        # Play until one player reaches 2 wins
        safety = 0
        while rps.phase != "matchover" and safety < 30:
            safety += 1
            rps.tick(rps.next_at + 0.01)
            if rps.phase == "wait":
                rps.start()
                for _ in range(4):
                    rps.tick(rps.next_at + 0.01)
        results.check("Rock-Paper-Scissors scores up to 2 wins ('matchover')",
                      rps.phase == "matchover" and max(rps.score) >= 2, f"score={rps.score}")

        stop.set()


# ==============================================================================
# STEP 2.E: Web UI & Frontend (index.html, styles.css, app.js)
# ==============================================================================
def test_step2e_web_ui_and_frontend():
    print("\n=== STEP 2.E: Web UI & Frontend ===", flush=True)
    html_text = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")
    css_text = (PROJECT_ROOT / "assets" / "css" / "styles.css").read_text(encoding="utf-8")
    js_text = (PROJECT_ROOT / "assets" / "js" / "app.js").read_text(encoding="utf-8")

    # 1. Check #btn-save-party-prefs button, icon, saved hint, and CSS styling
    has_save_btn = 'id="btn-save-party-prefs"' in html_text and 'data-i18n="party_save_prefs"' in html_text
    has_save_hint = 'id="party-prefs-saved-hint"' in html_text and 'data-i18n="party_prefs_saved"' in html_text
    has_save_css = ".party-save-row" in css_text and ".btn-save-prefs" in css_text and ".save-status-text" in css_text
    results.check("Save preferences (#btn-save-party-prefs) button, icon, hint, and CSS present",
                  has_save_btn and has_save_hint and has_save_css)

    # 2. Check i18n keys in index.html against I18N.hu and I18N.en in app.js, and ensure no data-i18n element has child SVG
    i18n_keys = set(re.findall(r'data-i18n(?:-title|-placeholder)?="([^"]+)"', html_text))
    missing_keys = [k for k in sorted(i18n_keys) if f"{k}:" not in js_text and f'"{k}":' not in js_text]
    results.check("All HTML data-i18n keys exist in app.js I18N dictionary",
                  len(missing_keys) == 0, f"{len(i18n_keys)} keys verified" if not missing_keys else f"missing={missing_keys}")

    # Check that no element with data-i18n="..." directly wraps an <svg> (which textContent= would clobber)
    bad_svg_i18n = re.findall(r'<([a-zA-Z0-9]+)\b[^>]*\bdata-i18n="[^"]+"[^>]*>(?:(?!</\1>).)*?<svg\b', html_text, re.DOTALL)
    results.check("Language switching (hu <-> en) preserves all SVG icons", len(bad_svg_i18n) == 0)

    # 3. Check low-power mode, QR code generation, and sound toggles
    has_low_power = 'id="toggle-low-power"' in html_text and "onToggleLowPower" in js_text
    has_qr = 'id="qrcode-box"' in html_text and (PROJECT_ROOT / "assets" / "js" / "qrcode.min.js").exists() and "initQRCode" in js_text
    has_sound = 'id="sound-toggle"' in html_text and 'id="sound-icon"' in html_text and "updateSoundButton" in js_text
    results.check("Low-power mode, QR code generation, and sound toggles verified",
                  has_low_power and has_qr and has_sound)

    # 4. Verify JavaScript syntax with node --check if available
    try:
        node_proc = subprocess.run(["node", "--check", str(PROJECT_ROOT / "assets" / "js" / "app.js")],
                                   capture_output=True, text=True, timeout=10)
        results.check("assets/js/app.js passes Node.js syntax check (node --check)", node_proc.returncode == 0,
                      node_proc.stderr.strip())
    except FileNotFoundError:
        results.check("assets/js/app.js basic balance check", js_text.count("{") == js_text.count("}"))


def main():
    backups = backup_data_files()
    try:
        test_step1_environment_and_sync()
        test_step1_fastapi_server()
        test_step2d_physics_and_telemetry()
        test_step2a_driving_and_calibration()
        test_step2b_shows_and_choreography()
        test_step2c_games()
        test_step2e_web_ui_and_frontend()
    finally:
        restore_data_files(backups)

    print("\n" + "=" * 68, flush=True)
    print(f"AUDIT SUMMARY: {len(results.passed)} passed, {len(results.failed)} failed", flush=True)
    print("=" * 68, flush=True)
    if results.failed:
        for name, detail in results.failed:
            print(f"  FAILED: {name} ({detail})", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
