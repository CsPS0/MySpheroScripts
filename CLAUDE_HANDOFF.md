# Sphero BOLT Web Dashboard – Handoff

## 1. Project Context & Environment
- **Repository Root**: Cross-platform (e.g. `d:\Projects\PROJECTS\MySpheroScripts` on Windows, `/home/csps/REPOS/MySpheroScripts` on Linux)
- **Environment**: Cross-platform (Windows 10/11, macOS Intel & Apple Silicon, Linux with BlueZ, Raspberry Pi OS). Python 3.10+ virtual environment (`sphero-neu/.venv`).
- **Server Startup**:
  - Linux / macOS: `./start.sh` (or `python3 web/server.py --host 0.0.0.0 --port 8080`)
  - Windows: `start.bat` or `.\start.ps1`
  - Real robots by default. `--sim` (or `SPHERO_SIM=1`) forces simulation (9 simulated BOLTs); without a Bluetooth adapter it simulates automatically.
  - `--low-power` (or `LOW_SPEC=1`) enables optimizations for low-level / low-spec school hardware.
- **Frontend Files**: `index.html`, `assets/css/styles.css`, `assets/js/app.js`.
  Any change to these root files must be copied to `sphero-neu/web/static/` (the copies must stay identical).
- **Hardware**: 15 physical Sphero BOLT robots.

---

## 2. Current UI (decluttering done)

Two columns plus overlays, no emojis (inline SVG icons only):

| Area | Content |
|------|---------|
| Top bar | Status pill (shows the running program), robot count + low-battery count, phone count, Log button with unread badge, HU/EN, sound, settings, red **Stop** (always visible). |
| Running strip | Appears under the top bar while a program runs: name, elapsed time, Stop. |
| Left column | **Arena** canvas, then the collapsible **Phone control** panel (QR code, 3 steps, connected phones with Disconnect, "Start Drive" hint when phones are waiting). |
| Right column | **Control panel** with three tabs: *Vezetés / Drive* (joystick, HUD, robot 1–3 selector, Start), *Műsorok / Shows* (option cards + Neumann heading slider and letter rotation), *Játékok / Games* (option cards, Start, live tic-tac-toe board or party-game balls). Below it the **Robots** fleet grid. |
| Log | Slide-over drawer from the right (Log button, Esc or backdrop closes). |

**Fleet grid**: one compact badge per robot (works for 15+): number in the robot's color, battery pill
(green ≥ 70 %, amber ≥ 30 %, red < 30 %, `–` = unknown), short BLE name, phone badge when a phone drives it.
Tap a badge to identify that robot. Toolbar: *Újrakeresés / Rescan*, *Mind azonosítása / Identify all*.

**Phone (controller) view**: a phone that opens the QR link gets a minimal page: colored banner
"Te irányítod: N. robot", a large joystick and the HUD. Host tools (arena, fleet, stop, settings) are hidden.
Until the host starts *Drive*, the phone shows "wait for the host to start Drive".

Role detection: the server treats `127.0.0.1` / `::1` as the host; every other IP is a phone controller.
Open the dashboard on the laptop via `http://localhost:8080`, not via the LAN IP.

Preserved: Hungarian default with EN toggle, slot colors (Phone 1 → robot 1, red `#ff3b3b`;
Phone 2 → robot 2, green `#2ecc71`; Phone 3 → robot 3, blue `#3498db`), auto-map focus toggle in Settings,
5 min idle timeout, max 3 phones, offline/Vercel client-side simulation.

---

## 3. Fixes made in this pass

- **Phone joystick never reached the robots**: the server forwarded `drive` lines with the wrong program flag. Fixed (`"joystick"`).
- **Joystick commands were cancelled within 50 ms** by `drive_keys.py`'s keyboard loop. Joystick input now has priority per robot; a robot stops 1 s after its last command. The browser repeats a held joystick or key every 300 ms.
- **Drive connected only robot 1**: Drive now connects robots 1–3 (one per phone slot).
- **Drive picked random robots**: it now uses `BOLT-1..3` from the pool's address cache, so phone N drives the robot showing the number N.
- **Slot collisions**: after a phone left, the next phone could get a slot already in use. Phones now get the lowest free slot.
- **Phones could drive any robot**: the server now forces a phone to its own slot. The phone UI also now selects its own robot (it previously always drove robot 1).
- **Kicked or timed-out phones reconnected immediately**: auto-reconnect is suppressed after a kick, timeout or "all slots taken".
- **Robot pool capped at 3** on real hardware: all BOLTs found are listed, numbered nearest first. Colors are defined for 1–15.
- **Fake battery numbers** on real hardware were removed. Battery shows `–` until the robot is identified (see below).
- **Identify did nothing on real robots**: it now connects to the robot, shows its number in its color, turns the headlight white for 3 s, reads the battery voltage and updates the badge. Identify requests are serialized. It refuses while a program is running, because the program holds the BLE connections.
- **Rescan during a running program** would drop the busy robots from the pool. It is now refused with a log message.
- **Neumann heading slider was not wired up**; it now updates the heading live. Letter rotate/mirror controls are back under "Betűk forgatása".
- Emojis were removed from the UI and from the server log messages.
- **Programs connected to random robots**: `find_toy("BOLT-n")` passed the cached address as a toy *name*, which never matched, then grabbed any free BOLT after a 15 s scan. It now resolves `BOLT-n` to the robot's `SB-xxxx` name from the cache and scans for exactly that robot. Neumann connect time went from 64 s to 23 s, on the right robots.
- **`./start.sh` always ran in simulation** (server default `SPHERO_SIM=1`). Real hardware is now the default.
- **Cross-platform support (Windows & macOS)**:
  - Added `start.bat` for Windows CMD and `start.ps1` for Windows PowerShell; made `start.sh` POSIX-compatible for Linux/macOS.
  - Replaced hardcoded `/tmp` with `tempfile.gettempdir()` for `sphero_bolts_cache.json`.
  - Updated `sphero_ble.list_adapters()` and `has_bluetooth_adapter()` so Windows and macOS are recognized as having the system BLE adapter rather than returning `[]` and forcing simulation.
  - Guarded BlueZ-specific keyword arguments in `BleakAdapter` so they aren't passed to Bleak on Windows or macOS.
  - Updated `requirements.txt` with environment marker `dbus-fast; sys_platform == 'linux'` so dependencies install smoothly on Windows and macOS.
  - Multi-interface local IP detection so QR codes display the correct Wi-Fi LAN IP even on offline school access points without internet.
- **Low-level hardware & low-spec optimizations (Raspberry Pi & older school laptops)**:
  - Added `--low-power` / `--low-spec` CLI flag (and `LOW_SPEC=1` env var).
  - Reduced memory footprint of the server log deque in low-spec mode.
  - Added "Kímélő mód (alacsony teljesítményű gépekhez)" / "Eco mode" switch to Admin Settings.
  - Canvas rendering automatically suspends when hidden or offscreen.
  - In Eco mode, expensive HTML5 canvas `shadowBlur` filters are bypassed, frame rate is capped to 25 FPS, and trail history is reduced.

---

## 4. How to Test with the Physical Robots

### Step 1: Start the server
```bash
./start.sh
```
On boot the server scans for BOLTs (4 s), numbers them nearest first and writes the address cache
`sphero_bolts_cache.json` in the system temporary directory (`tempfile.gettempdir()`, e.g. `/tmp` or `%TEMP%`, mapping `BOLT-n` → address), which the programs use for fast connects.

### Step 2: Check discovery
```bash
curl -s http://127.0.0.1:8080/api/robots | python3 -m json.tool
curl -s -X POST http://127.0.0.1:8080/api/robots/refresh      # rescan (no program may be running)
```
Robots connected to another device do not advertise and will not be listed.

### Step 3: Identify a robot (also reads its battery)
```bash
curl -s -X POST http://127.0.0.1:8080/api/robots/8/identify
```
Robot 8 shows "8" in its color with a white headlight for 3 seconds; its badge gets a battery value.
For numbers ≥ 10 the matrix shows the last digit.

### Step 4: Programs
```bash
curl -s -X POST http://127.0.0.1:8080/api/start/tictactoe   # 9 nearest robots show 1-9
curl -s -X POST http://127.0.0.1:8080/api/start/neu         # robots 1-7 show N E U M A N N, one letter each
curl -s -X POST http://127.0.0.1:8080/api/stop
```

### Step 5: Phone driving
1. Open `http://localhost:8080` on the laptop.
2. Scan the QR code with a phone. The phone shows "Te irányítod: 1. robot" and robot 1 shows "1" in red (simulation; see open items).
3. On the laptop press *Vezetés indítása / Start Drive* (or the hint button in the Phone panel). Drive connects robots 1–3 and runs a 10 s aim phase.
4. Drag the joystick on the phone: only that phone's robot moves.
5. **Calibration** (slider under the joystick, phone and laptop): stand behind the robot and move the slider (or the ±15° buttons)
   until the arrow and the white front light point straight away from you. The robot turns in place while you move it, and its matrix
   arrow always points to this "forward" direction. Pushing the joystick up then drives forward, never sideways or towards you.
   Calibration is per robot and lasts one Drive session (reset when Drive starts, because the aim phase sets a new zero).
   Implementation: browser `{"type": "calibrate", robot, offset}` -> server `calib <robot> <offset>` on drive_keys stdin ->
   `Driven.offset`, robot heading = joystick direction + offset; `NorthArrow(get_target=offset)`.

---

### Neumann alignment (2026-11-05)
- **Compass mode** (default, `letters.json` `"align": "compass"`): after connecting, all 7 robots calibrate the compass at once (about 5 s, they spin in place) and turn to magnetic north + the heading slider. No manual aim phase; startup about 48 s instead of 108 s. Hardware test: north found on 7 of 7.
  spherov2 0.12.1 bug: `SpheroEduAPI.calibrate_compass()` never sends the command for the BOLT (`BOLT.implements(Sensor.magnetometer_calibrate_to_north)` is False) and then waits forever. `neu.py` sends `toy.magnetometer_calibrate_to_north()` directly and listens for the north-yaw notification itself.
  Metal furniture or magnets near a robot can bend its compass; straighten it with the turn buttons.
- **Manual aim mode**: the old 10 s aim phase.
- **Hand-turn lock** (Shows, Neumann, "Kézi forgatás" button; `letters.json` `"hand"`): ON = stabilization off, blue tail light on, no automatic turning (heading slider, alignment and robot-turn buttons are disabled; letter rotation still works), so each robot can be turned by hand and stays. OFF = every robot keeps the direction it was given (its aim is reset there); the heading slider and turn buttons then work relative to that. Starting the show with the lock ON skips the compass. Hardware: lock on instant, off about 1 s (4.5 s with a dropped robot), heading changes reach the robots in 0.2 s.
- **Spare robots**: if one of robots 1-7 does not connect, the next pool robot (8, 9, ...) takes its letter, instead of the show exiting.
- **Dropped robots** are marked lost once and skipped, so they cannot stall the others (before: about 25 s per change). Restart the show to reconnect them.
- Seen at 14:40 after over an hour of testing: SB-DBF8 no longer connects (service discovery fails), and two other robots dropped their connection during the compass spin or the hand lock. Probably low batteries or a stuck robot: charge them, or switch the robot off and on.
- **Per robot** (Shows, Neumann, "Betűk egyenként" rows): *Betű* turns the letter on the matrix by 90°, *Robot* turns that one robot by 15° (`turn`), plus mirror and reset (back to rotation 180, no turn). All apply live.

### Tic-tac-toe (fixed 2026-11-05)
Symptom: all balls purple / glitched. Causes found in the logs, all fixed:
- `connect_toy` switched to **simulation** as soon as one robot failed, so every robot after it was fake. It now falls back only when there is no Bluetooth adapter; otherwise it raises and tic-tac-toe tries the next spare robot.
- **Bluetooth overload** with 9 connections on one adapter: spherov2 streams 9 sensors per BOLT, and all 9 matrices were redrawn at once (about 90 commands). This gave bad checksums and garbled matrices. Now only the accelerometer streams (200 ms), and at most 3 robots draw at the same time (`DRAW_AT_ONCE`). `neu.py` turns streaming off.
- **Stop always overran** the 15 s grace, so the program was killed with the matrices half drawn and the robots still connected. Cleanup and disconnect now run in parallel (stop takes about 4 s); server `STOP_GRACE` is 30 s.
- A robot that doesn't answer during setup is left out of the game instead of crashing the program.
- Still seen: an occasional `GATT Protocol Error: Unlikely Error` (about one per minute with 9 robots). It doesn't stop the game; a second USB Bluetooth adapter would spread the load (`PER_ADAPTER` in tictactoe.py).

### Dance show for all robots (`big_dance.py`, 2026-11-05)
- Replaces the 3-robot dance (`bolt_dance.py` stays; its aim phase is used by Drive and Neumann). Setup: every free pool robot shows its number (2-digit font `indicators.number_bitmap`) and its blue tail light; line them up left to right by number, then press **Go** (Shows, Szinkrontánc). Parts: rainbow wave with random turns (120 s), rush as out-and-back dashes with an explosion flash on collisions (60 s), random characters with wiggles and a small square dance (45 s), rainbow finale. **Next part** skips ahead. `DANCE_SCALE=0.05` shortens everything for testing.
- Left out: numbers tapped off on the web page (`data/dance.json` "exclude", `/api/dance`), and busy robots (not advertising: connected elsewhere or switched off).
- **Bluetooth limit: one adapter holds 10 robots.** Robots 1-10 connected, every further one timed out (40-50 s each). The dance stops at 10 per adapter (or after 2 timeouts in a row) and puts robots 11-15 on a second USB adapter automatically.
- **Hardware runs (10 robots, Intel 8087:0a2b adapter):**
  1. First version (about 15 commands/s plus position streaming): stalled 35 s into the rainbow; every command of every robot timed out at once and all robots dropped out.
  2. Reworked: no sensor streaming, all robots share a limit of 8 commands/s (`RATE`), everyone pauses 3 s after a timeout, robots only drop out when really disconnected. Result: full dance, all 10 through rainbow and rush, 1 real disconnect (SB-47A2) in the characters part, finale with 9, exit 0.
- **Collisions**: spherov2 0.12.1 decodes the BOLT's collision message with the wrong layout (`struct.error: unpack requires a buffer of 18 bytes`, 14 times in run 2 = 7 bumps), so nothing was reported. `listen_for_collisions()` replaces its listener with one that ignores the payload (tested on a real robot). The explosion flash has not been seen on hardware yet.
- spherov2 also skips collision detection setup and `set_matrix_character` for the BOLT (same capability-check bug as the compass); both are sent directly. So **Identify** never showed the number before; it now draws the 2-digit number.

### Admin login for phones, arena (2026-11-05)
- **Phone admin login**: the phone view has an **Admin** button; with the password the phone gets the full dashboard (like the laptop) and does not use a joystick slot. Default password `admin1234`, set another with the `ADMIN_PASSWORD` environment variable. Logout: Settings, "Kijelentkezés (ez a telefon)".
- Enforced by the server, not only hidden in the page: every control endpoint (start, stop, game, letters, dance, tictactoe, sim, shake, kick, rescan, identify, auto-map) answers 401 unless the request comes from the laptop (localhost) or carries the admin cookie. Read-only endpoints stay open. The cookie is an HMAC of the password with a random secret in `sphero-neu/data/admin_secret` (git-ignored, mode 600): it survives restarts and stops working when the password changes. A wrong password waits 1 s. Plain HTTP on the local network: fine for a classroom, not for the internet.
- **Arena**: it draws robot positions, which only the simulation reports (real robots would have to stream positions, which overloads the Bluetooth adapter, see the dance). It is now hidden with real robots and shown in simulation and the offline demo. The "phone connected" highlight goes to the Phone panel instead.

## 5. Open Items
- **Aim / Célzás button**: not implemented; there is no standalone aim API. Drive, Dance and Neumann run their own aim phase at start.
- **Battery at boot**: reading voltage needs a BLE connection per robot (slow for 15 robots), so it is read on identify instead. A background "identify all" at boot could fill it in.
- **Slot number on the matrix for real robots**: the server only writes the slot number to simulated robots when a phone connects; real robots show it once Drive connects them (arrow indicator) or on identify.
- Status texts inside the **client-side simulated games** (offline/Vercel mode) are still English.
- Hardware test (2026-11-05, 15 BOLTs): the scan found all 15; identify succeeded on all 15 (11–17 s each, batteries 61–94 %); Neumann connected robots 1–3 and scrolled NEUMANN. Drive and the games were not tested on hardware yet; phone driving was tested in simulation only.
- **Neumann is now one letter per robot**: robots 1-7 show N, E, U, M, A, N, N in one color (`neu.py`, `LETTER_COLOR`); line them up by the letter they show. M and A were added to `indicators.LETTERS`; `data/letters.json` has 7 entries, all rotation 180 at heading 0 (upright when the robots face away from you). Hardware run: 7 simultaneous connections OK, about 46 s to connect, 18 s aim setup, 10 s aim, then about 4 s per robot to draw its letter (108 s in total). Drawing the letters in parallel would shorten the end.
